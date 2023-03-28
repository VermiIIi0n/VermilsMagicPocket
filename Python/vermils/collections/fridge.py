"""
Fridge is a module that provides a way to freeze objects and make them hashable.
"""

from __future__ import annotations
from typing import Mapping, TypeVar, Iterable, overload

K = TypeVar("K")
V = TypeVar("V")
K_co = TypeVar("K_co", covariant=True)
V_co = TypeVar("V_co", covariant=True)

__all__ = ("freeze", "FrozenDict", "FrozenList")


class FrozenDict(Mapping[K_co, V_co]):  # type: ignore[type-var]
    """
    An immutable dictionary.

    This is used to generate stable hashes for queries that contain dicts.
    Usually, Python dicts are not hashable because they are mutable. This
    class removes the mutability and implements the ``__hash__`` method.
    """

    def __new__(cls, *args, **kw):
        if len(args) == 1 and isinstance(args[0], FrozenDict) and not kw:
            return args[0]
        return super().__new__(cls)

    @overload
    def __init__(self): ...
    @overload
    def __init__(self: FrozenDict[str, V_co], **kw: V_co): ...
    @overload
    def __init__(self, _map: Mapping[K_co, V_co]): ...

    @overload
    def __init__(self: FrozenDict[str, V_co],
                 _map: Mapping[str, V_co], **kw: V_co): ...

    @overload
    def __init__(self, _iter: Iterable[tuple[K_co, V_co]]): ...

    @overload
    def __init__(self: FrozenDict[str, V_co],
                 _: Iterable[tuple[str, V_co]], **kw: V_co): ...

    @overload
    def __init__(self: FrozenDict[str, str], _iter: Iterable[list[str]]): ...

    def __init__(self, *args, **kw):
        if hasattr(self, "_dict"):
            return
        super().__init__()
        self._dict = dict[K, V](*args, **kw)
        self._hash = None

    def __repr__(self):
        return f"FrozenDict{self._dict}"

    def __hash__(self):
        if self._hash is None:
            # Calculate the hash of a tuple of sorted hashes of k/v pairs
            self._hash = hash(tuple(sorted(hash((k, v))
                              for k, v in self.items())))
        return self._hash

    def __getitem__(self, key):
        return self._dict[key]

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self._dict)

    def __contains__(self, __o: object) -> bool:
        return __o in self._dict

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, FrozenDict):
            return self._dict == __o._dict
        return self._dict == __o

    def get(self, key, default=None):
        return self._dict.get(key, default)

    def items(self):
        return self._dict.items()

    def keys(self):
        return self._dict.keys()

    def values(self):
        return self._dict.values()


class FrozenList(tuple[V_co]):
    """
    # FrozenList Class
    Basically just a tuple, but is able to be compared with lists.
    """

    def __new__(cls, value: Iterable[V_co]):
        if isinstance(value, FrozenList):
            return value
        return tuple.__new__(cls, value)

    def __eq__(self, other) -> bool:
        if isinstance(other, list):
            return self == tuple(other)
        return super().__eq__(other)

    def __ne__(self, other) -> bool:
        return not self == other

    def __gt__(self, other) -> bool:
        if isinstance(other, list):
            return self > tuple(other)
        return super().__gt__(other)

    def __ge__(self, other) -> bool:
        if isinstance(other, list):
            return self >= tuple(other)
        return super().__ge__(other)

    def __lt__(self, other) -> bool:
        return not self >= other

    def __le__(self, other) -> bool:
        if isinstance(other, list):
            return self <= tuple(other)
        return super().__le__(other)

    def __hash__(self) -> int:
        return tuple.__hash__(self)

    def __repr__(self) -> str:
        return f"FrozenList{super().__repr__()}"


@overload
def freeze(obj: dict, ensure_hashable=False,  # type: ignore[misc]
           *, memo: set[int] | None = None) -> FrozenDict: ...


@overload
def freeze(obj: list, ensure_hashable=False,  # type: ignore[misc]
           *, memo: set[int] | None = None) -> FrozenList: ...


@overload
def freeze(obj: set, ensure_hashable=False,  # type: ignore[misc]
           *, memo: set[int] | None = None) -> frozenset: ...


@overload
def freeze(obj: V, ensure_hashable=False, *, memo: set[int] | None = None) -> V: ...


def freeze(obj, ensure_hashable=False, *, memo=None):
    """
    Freeze an object by making it immutable and thus hashable.

    **Conservative approach, freezes elements of
    (`list` | `tuple` | `dict` | `FrozenDict` | `set` | `frozenset`)**

    * `obj` is the object to freeze.
    * `ensure_hashable` If `True`, raise `TypeError` when unable to freeze
    """

    if memo is None:
        memo = set()
    if id(obj) in memo:
        raise TypeError("Cannot freeze recursive data structures")
    memo.add(id(obj))
    if hasattr(obj, "__freeze__"):
        obj = obj.__freeze__(memo=memo.copy())
    elif isinstance(obj, dict | FrozenDict):
        # Transform dicts into ``FrozenDict``s
        return FrozenDict((k, freeze(v, ensure_hashable, memo=memo.copy()))
                          for k, v in obj.items())
    elif isinstance(obj, list | tuple):
        # Transform sequences into FrozenLists
        return FrozenList(freeze(el, ensure_hashable, memo=memo.copy())
                          for el in obj)
    elif isinstance(obj, set | frozenset):
        # Transform sets into ``frozenset``s
        return frozenset(freeze(item, ensure_hashable, memo=memo.copy())
                         for item in obj)
    if ensure_hashable:
        hash(obj)
    return obj
