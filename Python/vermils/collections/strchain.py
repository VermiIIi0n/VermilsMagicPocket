"""
Utility functions.
"""

from __future__ import annotations
from typing import Iterator, TypeVar, Iterable, Any, Callable, Sequence, overload

S = TypeVar("S", bound="StrChain")
C = TypeVar("C", bound=Callable)


class StrChain(Sequence[str]):
    """
    # StrChain Class
    ## More than a convenient way to create strings.
    **It is NOT a subclass of `str`, use `str()` to convert it to str.**

    By default `callback` is `str`, so simply calling the instance will 
    return the string.

    StrChain is immutable. Hash is the same as the string it represents.

    ### Usage:
    ```Python
    str_chain = StrChain()
    str_chain.hello.world() == "hello.world"
    ```

    **String can't start with '_' when using __getattr__ , 
    use __getitem__ instead**
    ```Python
    str_chain.["hello"]["_world"]() is "hello._world"

    path = StrChain(['/'], joint="/") # Init with a list and set a custom joint
    path.home.user() is "/home/user"
    str(path + "home" + "user") == "/home/user" # Comparing with str
    ```
    ### callback
    Used when calling StrChain, default is `str`
    First argument is the StrChain itself followed by args and kwargs
    ```Python
    string = StrChain(callback=lambda x: '!'.join([i.lower() for i in x]))
    string.Hello.World() == "hello!world"
    ```
    And much more...
    """

    def __init__(
            self: S,
            it: str | Iterable[str] | None = None,
            joint: str = '.',
            callback=str,
            **kw):
        """
        * `it`: Iterable[str], the initial string chain
        * `joint`: str, the joint between strings
        * `callback`: Callable[[StrChain, ...], Any], 
        used when calling the StrChain instance
        """
        self._joint = joint
        self._callback = callback
        self._kw = kw
        it = [it] if isinstance(it, str) else it
        self._list: list[str] = list(it or [])

    def __call__(self: S, *args: Any, **kw: Any):
        return self._callback(self, *args, **kw)

    def __create(self: S, it: Iterable[str]) -> S:
        return type(self)(it=it, joint=self._joint,
                          callback=self._callback, **self._kw)

    def __len__(self: S) -> int:
        return len(self._list)

    def __getattr__(self: S, name: str) -> S:
        if name.startswith('_'):
            raise AttributeError(
                f"{name} : String can't start with '_' when using __getattr__"
                " , use __getitem__ instead")
        return self.__create(self._list + [name])

    @overload
    def __getitem__(self: S, index: int) -> str:
        ...

    @overload
    def __getitem__(self: S, s: slice) -> S:
        ...

    @overload
    def __getitem__(self: S, string: str) -> S:
        ...

    def __getitem__(self: S, value: int | slice | str) -> str | S:
        if isinstance(value, int):
            return self._list[value]
        if isinstance(value, slice):
            return self.__create(self._list[value])
        if isinstance(value, str):
            return self.__create(self._list + [value])
        raise TypeError(f"Invalid type {type(value)}")

    def __eq__(self, other) -> bool:
        if isinstance(other, StrChain):
            return self._list == other._list and self._joint == other._joint
        return False

    def __hash__(self: S) -> int:
        return hash(str(self))

    def __bool__(self: S) -> bool:
        return bool(self._list)

    def __add__(self: S, other: Iterable[str] | str) -> S:
        other = [other] if isinstance(other, str) else list(other)
        return self.__create(self._list + other)

    def __radd__(self: S, other: Iterable[str] | str) -> S:
        other = [other] if isinstance(other, str) else list(other)
        return self.__create(other + self._list)

    def __iadd__(self: S, other: Iterable[str] | str) -> S:
        return self + other

    def __mul__(self: S, other: int) -> S:
        if not isinstance(other, int):
            return NotImplemented
        return self.__create(self._list * other)

    def __rmul__(self: S, other: int) -> S:
        return self * other

    def __imul__(self: S, other: int) -> S:
        return self * other

    def __iter__(self: S) -> Iterator[str]:
        return iter(self._list)

    def __reversed__(self: S) -> Iterator[str]:
        return reversed(self._list)

    def __contains__(self: S, item: object) -> bool:
        return item in self._list

    def __str__(self: S) -> str:
        return self._joint.join(self._list)

    def __repr__(self: S) -> str:
        return (f"{type(self).__name__}({self._list!r}, "
                f"joint={self._joint!r}, "
                f"callback={self._callback!r}, **{self._kw!r})")
