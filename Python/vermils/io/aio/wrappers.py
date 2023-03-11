from __future__ import annotations
from typing import Iterable, Literal, overload, TypeVar, IO, Generic
from io import TextIOWrapper
from ...asynctools import AsinkRunner

__all__ = ("AsyncIOStream", "open")
_T = TypeVar("_T", str, bytes)
StreamType = TypeVar("StreamType", bound="AsyncIOStream")
TEXTMODE = Literal['r+', '+r', 'rt+', 'r+t', '+rt', 'tr+', 't+r', '+tr', 'w+',
                   '+w', 'wt+', 'w+t', '+wt', 'tw+', 't+w', '+tw', 'a+', '+a',
                   'at+', 'a+t', '+at', 'ta+', 't+a', '+ta', 'x+', '+x', 'xt+',
                   'x+t', '+xt', 'tx+', 't+x', '+tx', 'w', 'wt', 'tw', 'a',
                   'at', 'ta', 'x', 'xt', 'tx', 'r', 'rt', 'tr', 'U', 'rU',
                   'Ur', 'rtU', 'rUt', 'Urt', 'trU', 'tUr', 'Utr']
BINARYMODE = Literal['rb+', 'r+b', '+rb', 'br+', 'b+r', '+br', 'wb+', 'w+b',
                     '+wb', 'bw+', 'b+w', '+bw', 'ab+', 'a+b', '+ab', 'ba+',
                     'b+a', '+ba', 'xb+', 'x+b', '+xb', 'bx+', 'b+x', '+bx',
                     'rb', 'br', 'rbU', 'rUb', 'Urb', 'brU', 'bUr', 'Ubr',
                     'wb', 'bw', 'ab', 'ba', 'xb', 'bx']


class AsyncIOStream(Generic[_T]):
    """
    # AsyncIOStream Class

    A wrapper around file-like objects that provides asynchronous
    reading and writing.
    """

    @overload
    def __init__(self: AsyncIOStream[str], file: TextIOWrapper,
                 sink: AsinkRunner | None = None) -> None: ...

    @overload
    def __init__(self: AsyncIOStream[bytes], file: IO,
                 sink: AsinkRunner | None = None) -> None: ...

    def __init__(self, file: IO, sink: AsinkRunner | None = None) -> None:
        self._sink = sink or AsinkRunner()
        self._file = file

    async def close(self) -> None:
        await self._sink.run(self._file.close)

    async def __aenter__(self: StreamType) -> StreamType:
        return self

    async def __aexit__(self, exc_t, exc_v, exc_tb) -> bool:
        await self.close()
        return False

    async def read(self, size: int = -1) -> _T:
        return await self._sink.run(self._file.read, size)

    async def readline(self, size: int = -1) -> _T:
        return await self._sink.run(self._file.readline, size)

    async def readlines(self, size: int = -1) -> list[_T]:
        return await self._sink.run(self._file.readlines, size)

    async def write(self, data: _T) -> int:
        return await self._sink.run(self._file.write, data)

    async def writelines(self, lines: Iterable[_T]) -> None:
        await self._sink.run(self._file.writelines, lines)

    async def flush(self) -> None:
        await self._sink.run(self._file.flush)

    async def seek(self, offset: int, whence: int = 0) -> int:
        return await self._sink.run(self._file.seek, offset, whence)

    async def tell(self) -> int:
        return await self._sink.run(self._file.tell)

    async def truncate(self, size: int | None = None) -> int:
        return await self._sink.run(self._file.truncate, size)

    @property
    def closed(self) -> bool:
        return self._file.closed

    @property
    def name(self) -> str:
        return self._file.name

    @property
    def mode(self) -> str:
        return self._file.mode

    def fileno(self) -> int:
        return self._file.fileno()

    def isatty(self) -> bool:
        return self._file.isatty()

    def readable(self) -> bool:
        return self._file.readable()

    def writable(self) -> bool:
        return self._file.writable()

    def seekable(self) -> bool:
        return self._file.seekable()

    def __aiter__(self: StreamType) -> StreamType:
        return self

    async def __anext__(self) -> _T:
        line = await self._sink.run(self._file.readline)
        if not line:
            raise StopAsyncIteration
        return line


_open = open


@overload
def open(file, mode: TEXTMODE, *args, **kw) -> AsyncIOStream[str]: ...


@overload
def open(file, mode: BINARYMODE, *args, **kw) -> AsyncIOStream[bytes]: ...


def open(file, mode: TEXTMODE | BINARYMODE = 'r', *args, **kw) -> AsyncIOStream:
    """
    Async open function
    """
    hdlr: IO = _open(file, mode, *args, **kw)  # type: ignore
    return AsyncIOStream(hdlr)
