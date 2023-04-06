"""
Utility functions.
"""

from __future__ import annotations
import http.cookiejar as hjar
import sys
import re
import inspect
import importlib
import contextlib
from pathlib import Path
from typing import Mapping, NoReturn, Sequence, TypeVar, Iterable, Callable, Any, cast
from typing import Literal, overload

C = TypeVar("C", bound=Callable)

__all__ = ("stringify_keys", "supports_in", "mimics", "sort_class",
           "str_to_object", "real_dir", "real_path", "version_cmp",
           "to_ordinal", "selenium_cookies_to_jar", "DummyLogger",
           "load_module", "check", "relative_to")


def mimics(_: C) -> Callable[[Callable], C]:
    """
    ### `mimics()`
    Type trick. This decorator is used to make a function mimic the signature
    of another function.
    """
    def decorator(wrapper: Callable) -> C:
        return wrapper  # type: ignore

    return decorator


def supports_in(obj) -> bool:
    """
    ### `supports_in()`
    Check if an object supports the ``in`` operator.

    Be careful: When a `Generator` be evaluated when using ``in``
    and the desired value never appears, the statement could never end.
    """
    return any(hasattr(obj, attr)
               for attr in ("__contains__", "__iter__", "__getitem__"))


def stringify_keys(data, memo: dict = None):
    if memo is None:
        memo = {}
    if isinstance(data, Mapping):
        if id(data) in memo:
            return memo[id(data)]
        memo[id(data)] = {}  # Placeholder in case of loop references
        memo[id(data)].update((str(k), stringify_keys(v, memo))
                              for k, v in data.items())
        return memo[id(data)]
    if isinstance(data, list | tuple):
        return [stringify_keys(v, memo) for v in data]
    return data


def sort_class(cls: Iterable[type]) -> list[type]:
    """
    ### `sort_class()`
    Sort classes by inheritance. From child to parent.
    """
    ls: list[type] = []
    for c in cls:
        it = iter(enumerate(ls))
        try:
            while True:
                i, p = next(it)
                if issubclass(c, p):
                    ls.insert(i, c)
                    break
        except StopIteration:
            ls.append(c)
    return ls


def str_to_object(object_name: str, module: str = "__main__") -> Any:
    """
    ### `str_to_object()`
    Get object by its name and module(default to main module)
    """
    return getattr(sys.modules[module], object_name)


def load_module(module_name: str,
                module_path: str | Path | None = None):
    """
    ### `load_module()`
    Load a module from a path.
    """
    if module_name in sys.modules:
        return sys.modules[module_name]
    if module_path is not None:
        module_path = Path(module_path)
        module_path = module_path.resolve()
        if module_path not in sys.path:
            sys.path.append(str(module_path))
    module = importlib.import_module(module_name)
    return module


def real_dir(path: str | Path | None = None) -> Path:
    """
    ### `real_dir()`
    Get the real path of the directory of the given file.

    When `path` is `None`, the directory of the main module will be returned.

    If main module is not a file, the current working directory will be returned.
    """
    path = path or getattr(sys.modules["__main__"], "__file__", '.')
    path = Path(cast(str, path)).resolve()
    return path.parent


def real_path(path: str | Path) -> Path:
    """
    ### `real_path()`
    Get the real path of the given file.

    *This helper function was written before I knew about `pathlib.Path.resolve()`...
    Just leave it here for compatibility.
    """
    # path = os.path.expanduser(path)
    # path = os.path.expandvars(path)
    # path = os.path.normpath(path)
    # path = os.path.realpath(path)
    return Path(path).resolve()


def relative_to(path: Path | str, anchor: Path | str | None = None) -> Path:
    """
    ### `relative_to()` 
    Expand relative path based on the anchor
    Default to the main file.

    >>> relative_to("foo/bar", "dir/baz") == Path("dir/foo/bar")

    >>> relative_to("../", "foo/bar") == Path("foo/")
    """
    anchor = anchor or getattr(sys.modules["__main__"], "__file__", '.')
    anchor = anchor if isinstance(anchor, Path) else Path(anchor or '.')
    path = path if isinstance(path, Path) else Path(path)
    if path.is_absolute():
        return path
    return anchor.parent / path


def version_cmp(v1: str, v2: str) -> int:
    """
    ### `version_cmp()`
    Compare two version strings.
    Versions must be valid SemVer strings or 'v'/'V' prefixed SemVer strings,
    or a `ValueError` will be raised.

    Returns positive `int` if v1 > v2, `0` if v1 == v2, negative `int` if v1 < v2.
    """
    v1s: dict[str, Sequence] = {}
    v2s: dict[str, Sequence] = {}
    for v, vs in ((v1, v1s), (v2, v2s)):
        v = v.strip()
        if v.startswith('v') or v.startswith('V'):
            v = v[1:]

        matches = re.match(
            r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
            r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
            r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))"
            r"?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$",
            v)
        if not matches:
            raise ValueError(f"Invalid version string: {v}")

        groups = matches.groups()
        vs["core"] = [int(i) for i in groups[:3]]
        vs["pre"] = groups[3] and groups[3].split('.') or []
        with contextlib.suppress(ValueError):
            vs["pre"] = [int(i) for i in vs["pre"]]

    for k in ("core", "pre"):
        for v1, v2 in zip(v1s[k], v2s[k]):
            # Strings are always greater than numbers
            diff = isinstance(v1, str) - isinstance(v2, str)
            diff = diff or (v1 > v2) - (v1 < v2)
            if diff:
                return diff

    if len(v1s["pre"]) and len(v2s["pre"]):
        # Larger set of pre-release identifiers is greater
        return len(v1s["pre"]) - len(v2s["pre"])

    # Pre-release versions are always lower than release versions
    return len(v2s["pre"]) - len(v1s["pre"])


def to_ordinal(num: int) -> str:
    """
    ### `to_ordinal()`
    Convert a number to its ordinal representation.
    """
    abs_num = abs(num)
    if abs_num % 100 in [11, 12, 13]:
        return f"{num}th"
    return f"{num}{['th', 'st', 'nd', 'rd'][abs_num % 10 if abs_num % 10 < 4 else 0]}"


@overload
def check(cond: Literal[False, 0, b'', '', None], msg: str = None,
          exc: type[Exception] = AssertionError,) -> NoReturn:
    ...


@overload
def check(cond: Any, msg: str = None,
          exc: type[Exception] = AssertionError,) -> None | NoReturn:
    ...


def check(cond: Any, msg: str = None,
          exc: type[Exception] = AssertionError,) -> None | NoReturn:
    """
    ### `check()`
    Raise an exception if the condition is not met.

    `assert` may be unavailable in some cases, so this function is provided.
    """
    if not cond:
        if msg is None:  # pragma: no branch
            curframe = inspect.currentframe()
            if curframe:  # pragma: no branch
                calframe = inspect.getouterframes(curframe, 2)
                ctx = calframe[1].code_context
                if ctx:  # pragma: no branch
                    msg = f"Assertion failed: {ctx[-1].strip()}"
        raise exc(msg)

    return None


def selenium_cookies_to_jar(raws: list[dict[str, str]]) -> hjar.CookieJar:
    """Converts selenium cookies to `http.cookiejar.CookieJar`"""
    jar = hjar.CookieJar()
    for r in raws:
        cookie = hjar.Cookie(**{  # type: ignore
            "version": 0,
            "name": r["name"],
            "value": r["value"],
            "port": None,
            "port_specified": False,
            "domain": r["domain"],
            "domain_specified": bool(r["domain"]),
            "domain_initial_dot": r["domain"].startswith("."),
            "path": r["path"],
            "path_specified": bool(r["path"]),
            "secure": r["secure"],
            "expires": r["expiry"],
            "discard": True,
            "comment": None,
            "comment_url": None,
            "rest": {"HttpOnly": None},
            "rfc2109": False,
        })
        jar.set_cookie(cookie)
    return jar


class DummyLogger:  # pragma: no cover
    """A logger that does nothing"""

    def __init__(self, *args, **kwargs):
        pass

    def debug(self, msg: object, *args, **kw) -> None:
        pass

    def info(self, msg: object, *args, **kw) -> None:
        pass

    def warning(self, msg: object, *args, **kw) -> None:
        pass

    def error(self, msg: object, *args, **kw) -> None:
        pass

    def critical(self, msg: object, *args, **kw) -> None:
        pass

    def exception(self, msg: object, *args, **kw) -> None:
        pass

    def log(self, level: int, msg: object, *args, **kw) -> None:
        pass
