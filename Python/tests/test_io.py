import os
import pytest
import http.server
import threading
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from vermils.io import DummyAioFileStream, DummyFileStream
from vermils.io import aio
from vermils.io.puller import AsyncPuller, Modifier, MaxRetryReached

PORT = 18000


@pytest.fixture
def http_server():
    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        class MyHdlr(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kw):
                kw["directory"] = str(tmpdir)
                super().__init__(*args, **kw)

        with open(tmpdir / "file", 'w') as f:
            f.write("hello")

        with http.server.HTTPServer(('', PORT), MyHdlr) as httpd:
            thread = threading.Thread(target=httpd.serve_forever)
            thread.start()
            yield httpd
            httpd.shutdown()
            thread.join()


def test_dummy_file_stream():
    with DummyFileStream() as f:
        f.write("hello")
        f.flush()
        f.seek(0)
        f.read()
        f.close()


async def test_dummy_aio_file_stream():
    async with DummyAioFileStream() as f:
        await f.write("hello")
        await f.flush()
        await f.seek(0)
        await f.read()
        await f.close()


async def test_aio_os():
    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        await aio.os.mkdir(tmpdir/"test")
        await aio.os.makedirs(tmpdir / "a" / "b" / "c")
        with open(tmpdir / "file", 'w') as f:
            f.write("hello")
            f.flush()
            await aio.os.fsync(f.fileno())
        await aio.os.replace(tmpdir / "file", tmpdir / "file2")
        assert set(os.listdir(tmpdir)) == {"a", "file2", "test"}
        assert set(await aio.os.listdir(tmpdir)) == {"a", "file2", "test"}
        assert await aio.os.listdir(tmpdir/"a") == ["b"]
        assert await aio.os.listdir(tmpdir/"a"/"b") == ["c"]
        await aio.os.removedirs(tmpdir/'a'/'b'/'c')
        assert set(await aio.os.listdir(tmpdir)) == {"file2", "test"}
        await aio.os.link(tmpdir / "file2", tmpdir / "file3")
        assert set(await aio.os.listdir(tmpdir)) == {"file2", "file3", "test"}
        assert os.stat(tmpdir / "file2") == await aio.os.stat(tmpdir / "file2")
        await aio.os.remove(tmpdir/"file2")
        await aio.os.remove(tmpdir/"file3")
        assert await aio.os.listdir(tmpdir) == ["test"]


async def test_aio_path():
    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        await aio.os.mkdir(tmpdir/"test")
        await aio.os.makedirs(tmpdir / "a" / "b" / "c")
        assert os.path.exists(tmpdir / "test")
        assert await aio.path.exists(tmpdir / "test")
        assert await aio.path.exists(tmpdir / "a" / "b" / "c")
        assert not await aio.path.exists(tmpdir / "a" / "b" / "d")
        assert await aio.path.isdir(tmpdir / "a" / "b")
        with open(tmpdir / "file", 'w') as f:
            f.write("hello")
            f.flush()
            await aio.os.fsync(f.fileno())
        assert await aio.path.isfile(tmpdir / "file")
        assert not await aio.path.isfile(tmpdir / "test")
        assert not await aio.path.isdir(tmpdir / "file")
        await aio.os.link(tmpdir / "file", tmpdir / "file2")
        await aio.os.symlink(tmpdir / "file", tmpdir / "file3")
        assert not await aio.path.islink(tmpdir / "file2")
        assert await aio.path.islink(tmpdir / "file3")
        assert await aio.path.samefile(tmpdir / "file", tmpdir / "file2")
        assert await aio.path.getsize(tmpdir / "file") == 5
        assert isinstance(await aio.path.getmtime(tmpdir / "file"), float)
        assert isinstance(await aio.path.getatime(tmpdir / "file"), float)
        assert isinstance(await aio.path.getctime(tmpdir / "file"), float)


async def test_aio_wrappers():
    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        async with aio.open(tmpdir / "file", 'w+') as f:
            await f.write("hello")
            await f.flush()
            await aio.os.fsync(f.fileno())
            assert f.readable()
            assert f.writable()
            assert f.seekable()
            assert not f.isatty()
            await f.seek(0)
            assert 0 == await f.tell()
            assert await f.read() == "hello"
            await f.seek(0)
            assert await f.readline() == "hello"
            await f.seek(0)
            assert await f.readlines() == ["hello"]
            await f.seek(0)
            assert await f.read(2) == "he"
            await f.seek(0)
            await f.writelines(["hello", "world"])
            await f.seek(0)
            assert await f.read() == "helloworld"
            await f.seek(0)
            await f.truncate(3)
            await f.seek(0)
            assert await f.read() == "hel"
            assert f.name == str(tmpdir / "file")
            assert f.mode == 'w+'
            assert f.closed == False
            await f.seek(0)
            async for line in f:
                assert line == "hel"


async def test_aio_tempfile():
    async with aio.tempfile.NamedTemporaryFile() as f:
        await f.write("hello")
        await f.flush()
        await aio.os.fsync(f.fileno())
        await f.seek(0)
        assert await f.read() == "hello"
        assert f.name
        assert f.mode
        assert f.closed == False
        await f.seek(0)
        async for line in f:
            assert line == "hello"


async def test_aio_puller(http_server):
    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        puller = AsyncPuller()
        Modifier.raise_for_status(puller)
        Modifier.show_progress(puller)
        Modifier.add_logging(puller, logging)
        Modifier.on_every_event(puller, lambda *args, **kw: None)

        url = f"http://localhost:{PORT}"
        batch = 4
        for i in range(batch):
            await puller.pull(url, tmpdir / f"file{i}")
        await puller.join()
        assert set(os.listdir(tmpdir)) == {f"file{i}" for i in range(batch)}

        with pytest.raises(FileExistsError):
            await puller.pull(url, tmpdir / "file0")
            await puller.join()

        Modifier.ignore_file_exists(puller)
        await puller.pull(url, tmpdir / "file0")
        await puller.join()

        with pytest.raises(MaxRetryReached):
            await puller.pull(url + "/404", tmpdir / "file0", overwrite=True, retry=0)
            await puller.join()

        Modifier.ignore_failure(puller)
        await puller.pull(url + "/404", tmpdir / "file0", overwrite=True, retry=0)

        await puller.aclose()

        async with AsyncPuller() as puller:
            await puller.pull(url, tmpdir / "file-1", overwrite=True)
            await puller.join()
