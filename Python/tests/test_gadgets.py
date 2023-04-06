import http.cookiejar
import pytest
import os
import platform
import logging
from tempfile import TemporaryDirectory, NamedTemporaryFile
from pathlib import Path
from vermils.gadgets import mimics, supports_in, sort_class
from vermils.gadgets import stringify_keys, str_to_object, real_dir
from vermils.gadgets import real_path, version_cmp, load_module
from vermils.gadgets import to_ordinal, selenium_cookies_to_jar
from vermils.gadgets import SideLogger, MonoLogger, check, relative_to


def test_inspects():
    assert supports_in([1, 2, 3])
    assert supports_in({1, 2, 3})
    assert supports_in({1: 2, 3: 4})
    assert not supports_in(1)


def test_mimics():

    @mimics(dict.__init__)
    def init(*args, **kw):
        dict(*args, **kw)

    # init(123)

    assert init.__name__ == "init"


def test_sort_class():
    class A:
        ...

    class B(A):
        ...

    class C(B):
        ...

    class D(A):
        ...

    class E:
        ...

    assert sort_class([B, D, C, object, A, E]) == [C, B, D, A, E, object]


def test_stringify_keys():
    assert stringify_keys({1: 2, 3: 4}) == {"1": 2, "3": 4}
    assert stringify_keys({1: {2: 3}}) == {"1": {"2": 3}}
    assert stringify_keys({1: {2: {3: 4}}}) == {"1": {"2": {"3": 4}}}
    assert stringify_keys({1: {2: {3: {4: 5}}}}) == {"1": {"2": {"3": {"4": 5}}}}

    d = {
        "list": [{1: 2}, {3: 4}],
        "tuple": ({1: 2}, {3: 4}),
    }
    d['d'] = d

    sd = stringify_keys(d)
    assert sd['list'][0]['1'] == 2
    assert sd['list'][1]['3'] == 4
    assert sd['tuple'][0]['1'] == 2
    assert sd['tuple'][1]['3'] == 4
    assert sd['d'] is sd


def test_str_to_object():
    assert str_to_object("mimics", "vermils.gadgets") is mimics


def test_real_dir():
    path = "/dir1/dir2/file"
    assert real_dir(path) == Path(os.path.dirname(os.path.realpath("/dir1/dir2/file")))


def test_real_path():
    path = "/dir1/dir2/file"
    assert real_path(path) == Path(os.path.realpath("/dir1/dir2/file"))


def test_version_cmp():
    assert version_cmp("1.0.0", "1.0.0") == 0
    assert version_cmp("1.0.0", "v1.0.0") == 0
    assert version_cmp("1.0.0", "V1.0.0") == 0
    assert version_cmp("1.0.0", "1.0.1") < 0
    assert version_cmp("1.0.1", "1.0.0") > 0
    assert version_cmp("1.0.0", "1.0.0-alpha") > 0
    assert version_cmp("1.0.0-alpha", "1.0.0") < 0
    assert version_cmp("1.0.0-alpha", "1.0.0-beta") < 0
    assert version_cmp("1.0.0-beta", "1.0.0-alpha") > 0
    assert version_cmp("1.0.0-beta", "1.0.0-beta") == 0
    assert version_cmp("1.0.0-beta", "1.0.0-beta.1") < 0
    assert version_cmp("1.0.0-beta.1", "1.0.0-beta") > 0
    assert version_cmp("1.0.0-beta.1", "1.0.0-beta.12") < 0
    assert version_cmp("1.0.0-alpha.beta", "1.0.0-alpha") > 0
    assert version_cmp("1.0.0-alpha.1", "1.0.0-alpha.12") < 0
    assert version_cmp("1.0.0-alpha.alpha", "1.0.0-alpha.1") > 0
    assert version_cmp("1.0.0-alpha.1", "1.0.0-alpha.alpha") < 0
    assert version_cmp("1.0.0-alpha.2-a", "1.0.0-alpha.12-a") > 0

    assert version_cmp("1.0.0+3213", "1.0.0-alpha+12332") > 0
    with pytest.raises(ValueError):
        version_cmp("1.0.0", "1.0.0.alpha")
    with pytest.raises(ValueError):
        version_cmp("1.0.0", "1.0")


def test_to_ordinal():
    assert to_ordinal(1) == "1st"
    assert to_ordinal(2) == "2nd"
    assert to_ordinal(3) == "3rd"
    assert to_ordinal(4) == "4th"
    assert to_ordinal(11) == "11th"
    assert to_ordinal(12) == "12th"
    assert to_ordinal(13) == "13th"
    assert to_ordinal(21) == "21st"
    assert to_ordinal(22) == "22nd"
    assert to_ordinal(23) == "23rd"
    assert to_ordinal(31) == "31st"
    assert to_ordinal(32) == "32nd"
    assert to_ordinal(33) == "33rd"
    assert to_ordinal(45) == "45th"
    assert to_ordinal(46) == "46th"
    assert to_ordinal(113) == "113th"


def test_selenium_cookies_to_jar():
    cookies = [
        {
            "domain": ".www.pixiv.net",
            "expiry": 1674644458,
            "httpOnly": False,
            "name": "_44124",
            "path": "/",
            "sameSite": "None",
            "secure": True,
            "value": "5313141"
        },
        {
            "domain": ".www.pixiv.net",
            "expiry": 1669470457,
            "httpOnly": False,
            "name": "_43134",
            "path": "/",
            "sameSite": "Lax",
            "secure": False,
            "value": "1322141"
        },
    ]
    jar = selenium_cookies_to_jar(cookies)
    assert isinstance(jar, http.cookiejar.CookieJar)
    assert len(jar) == 2
    assert jar._cookies[".www.pixiv.net"]["/"]["_44124"].value == "5313141"


def test_monologger():
    if platform.system() == "Windows":
        return

    with TemporaryDirectory() as tempdir:
        logger = MonoLogger(path=tempdir, level="DEBUG")
        assert MonoLogger.getLogger("root")
        assert MonoLogger.getLogger("not_root") is None
        assert logger.name == "root"
        assert logger.level == "DEBUG"
        assert logger.path == tempdir
        logger.debug("test_debug")
        logger.info("test_info")
        logger.warning("test_warning")
        logger.error("test_error")
        logger.critical("test_critical")
        logger.exception(Exception("test_exception"))

        hdlr = logging.StreamHandler()
        logger.addHandler(hdlr)
        logger.removeHandler(hdlr)
        logger.formatter = "%(message)s"
        logger.formatter = logger.formatter

        tempdir = Path(tempdir)
        fnames = os.listdir(tempdir)
        assert len(fnames) == 5
        for fname in fnames:
            assert fname.endswith(".log")
        for fname in (
            "debug.log",
            "info.log",
            "warning.log",
            "error.log",
            "critical.log",
        ):
            assert (tempdir / fname).exists()
            with open(tempdir / fname) as f:
                assert f"test_{fname[:-4]}" in f.read()

        logger.log(logging.DEBUG, "test_log")
        logger.log(logging.INFO, "test_log")
        logger.log(logging.WARNING, "test_log")
        logger.log(logging.ERROR, "test_log")
        logger.log(logging.CRITICAL, "test_log")
        with pytest.raises(ValueError):
            logger.log(0, "test_log")

        for fname in fnames:
            with open(tempdir / fname) as f:
                assert "test_log" in f.read()

        logger.level = "INFO"
        assert logger.level == "INFO"
        logger.debug("test_abc")
        with open(tempdir / "debug.log") as f:
            assert "test_abc" not in f.read()

        MonoLogger(path=tempdir/"test11", level="DEBUG")

        with pytest.raises(ValueError, match="log path"):
            MonoLogger(path=str(tempdir/"debug.log"), formatter="abc")


def test_sidelogger():
    raw_logger = logging.getLogger("test")
    raw_logger.setLevel(logging.DEBUG)

    with NamedTemporaryFile('r+') as f:
        raw_logger.addHandler(logging.StreamHandler(f))
        logger = SideLogger(raw_logger)
        assert logger.logger is raw_logger
        logger.debug("test_debug")
        logger.info("test_info")
        logger.warning("test_warning")
        logger.error("test_error")
        logger.critical("test_critical")
        logger.exception(Exception("test_exception"))
        logger.exception(Exception("test_exception"), exc_info=True)
        logger.log(logging.DEBUG, "test_log")

        logger.join()
        f.flush()
        f.seek(0)

        content = f.read()
        check_list = [
            "test_debug",
            "test_info",
            "test_warning",
            "test_error",
            "test_critical",
            "test_exception",
            "test_log",
        ]
        assert all([c in content for c in check_list])

        logger.debug("test_debug")
        logger.join()

def test_load_module():
    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        mod_name = "dummy"
        fname = tmpdir / f"{mod_name}.py"
        with open(fname, "w") as f:
            f.write("imported = True")
        mod = load_module(mod_name, tmpdir)
        assert mod.imported

        # Load again
        mod = load_module(mod_name, tmpdir)
        assert mod.imported

def test_load_module_with_submodule():
    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        mod_name = "dummyB"
        name = tmpdir / f"{mod_name}"
        name.mkdir()
        fname = name / "__init__.py"
        with open(fname, "w") as f:
            f.write("from . import submodule\n")
            f.write("imported = submodule.imported_sub\n")
        fname = name / "submodule.py"
        with open(fname, "w") as f:
            f.write("imported_sub = True")
        
        mod = load_module(mod_name, tmpdir)
        assert mod.imported
        assert mod.submodule.imported_sub

def test_check():
    check(True)

    with pytest.raises(AssertionError, match=r"Assertion failed: check\(False\)"):
        check(False)
    
    with pytest.raises(ValueError, match=r"Assertion failed: check\(False,.*\)"):
        check(False, exc=ValueError)
    
    with pytest.raises(AssertionError, match="abc"):
        check(False, msg="abc")
    
    with pytest.raises(AssertionError, match=''):
        check(False, msg='')
    

def test_relative_to():
    absp = Path("/some/file")
    assert relative_to(absp, absp) == absp
    assert relative_to(absp) == absp

    relp = Path("some2/file2")
    assert relative_to(relp, absp) == "/some"/relp
