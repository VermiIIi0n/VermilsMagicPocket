"""
Utility functions.
"""

from __future__ import annotations
import http.cookiejar as hjar
import sys
import os
import re
import pathlib
import contextlib
from typing import Mapping, Sequence, TypeVar, Iterable, Callable, Any

C = TypeVar("C", bound=Callable)

__all__ = ("stringify_keys", "supports_in", "mimics", "sort_class",
           "str_to_object", "real_dir", "real_path", "version_cmp",
           "to_ordinal", "selenium_cookies_to_jar")


def mimics(_: C) -> Callable[[Callable], C]:
    """
    Type trick. This decorator is used to make a function mimic the signature
    of another function.
    """
    def decorator(wrapper: Callable) -> C:
        return wrapper  # type: ignore

    return decorator


def supports_in(obj) -> bool:
    """
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
    """Sort classes by inheritance. From child to parent."""
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
    return getattr(sys.modules[module], object_name)


def real_dir(path: str = None) -> pathlib.Path:
    path = path or getattr(sys.modules["__main__"], "__file__", '') or ''
    path = os.path.dirname(real_path(path))
    return pathlib.Path(path)


def real_path(path: str) -> pathlib.Path:
    path = os.path.expanduser(path)
    path = os.path.expandvars(path)
    path = os.path.normpath(path)
    path = os.path.realpath(path)
    return pathlib.Path(path)


def version_cmp(v1: str, v2: str) -> int:
    """
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
    if num % 100 in [11, 12, 13]:
        return f"{num}th"
    return f"{num}{['th', 'st', 'nd', 'rd'][num % 10 if num % 10 < 4 else 0]}"


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
