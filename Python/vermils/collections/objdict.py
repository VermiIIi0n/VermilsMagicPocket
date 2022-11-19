# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, Optional, TypeVar
from copy import deepcopy, copy

_T = TypeVar("_T")


class ObjDict(dict[str, _T]):
    """
    ## ObjDict is a subclass of dict that allows for object-like access
    #### Preserved:
    these preserved names are not allowed to be set using dot access,
    but you can access your version using `['name']` or `get`
    * `NotExist`: default value for missing key, will raise KeyError
    * `update`: just like dict.update(), but recursively converts nested dicts
    * `copy`: returns a shallow copy
    * Any attribute of the dict class
    * Any name starts with `_`

    #### Precedence:
    * `.` : Attribute > Key > Default
    * `[]` & `get` : Key > Default
    """

    @property
    def NotExist(self):  # for default value
        return ObjDict.NotExist

    def __init__(self, d: dict[str, _T] = None, recursive=True, default=NotExist, *, antiloop_map=None):
        """
        #### Params:
        * `d`: dict
        * `default`: default value to return if key is not found,
        reset to ObjDict.NotExist to raise KeyError
        * `recursive`: recursively try to convert all sub-objects in `d`
        * `antiloop_map`: a dict to store the loop-detection,
        if you want to use the same ObjDict object in multiple places,
        you can pass a dict to `antiloop_map` to avoid infinite loop
        """

        super().__init__()
        self.__dict__["_antiloop_map"] = {
        } if antiloop_map is None else antiloop_map  # for reference loop safety
        self.__dict__["_default"] = default
        self.__dict__["_recursive"] = recursive
        d = d or {}
        self._antiloop_map[id(d)] = self
        self.update(d)

    def update(self, d=None, **kw):
        try:
            if not isinstance(d, dict) and d is not None or kw:
                d = () if d is None else d
                d = dict(d, **kw)
            else:
                # create a dummy if not exist yet, prevent infinite-loop
                self._convert(d)
            for k, v in d.items():
                self[k] = self._convert(v)
        finally:
            self.__dict__["_antiloop_map"] = {}  # reset the map

    def _convert(self, v: Any, recursive: Optional[bool] = None) -> Any:
        recursive = recursive if recursive is not None else self._recursive
        if not recursive:
            return v
        if isinstance(v, dict):
            if id(v) in self._antiloop_map:
                return self._antiloop_map[id(v)]
            if isinstance(v, ObjDict):
                if v.default is not self.default:
                    v.default = self.default
                return v
            return ObjDict(v, default=self.default, antiloop_map=self._antiloop_map)
        if isinstance(v, list):
            return [self._convert(i) for i in v]
        if isinstance(v, tuple):
            return tuple(self._convert(i) for i in v)
        if isinstance(v, set):
            return {self._convert(i) for i in v}
        return v

    @property
    def default(self):
        return self.__dict__["_default"]

    @default.setter
    def default(self, value):
        """
        ### default property
        NOTICE: will also set default value for all sub-dicts
        * set value to return when key is not found
        * set to `ObjDict.NotExist` to raise KeyError when key is not found
        * when set to a mutable object, it will be deep-copied before being set
        """
        self.__dict__["_default"] = value
        self.update(self)

    def copy(self) -> ObjDict:
        """### returns a shallow copy"""
        return ObjDict(self, recursive=False, default=self.default)

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"{name} not found in {self}")

    def __setattr__(self, name: str, value):
        if name in {"NotExist", "update", "copy"} or name.startswith("_"):
            raise AttributeError(
                f"set '{name}' with dot access is not allowed, consider using ['{name}']")
        # cannot just call setattr(self, name, value), recursion error
        if hasattr(getattr(type(self), name, None), "__set__"):
            getattr(type(self), name).__set__(self, value)
        else:
            self[name] = value

    def __getitem__(self, name: str) -> _T:
        if name in self:
            return self.get(name)  # type: ignore
        if self.default is ObjDict.NotExist:
            raise KeyError(f"{name} not found in {self}")
        self[name] = copy(self.default)
        return self[name]

    def __deepcopy__(self, memo: Dict[int, Any]):
        copy: ObjDict[_T] = ObjDict({}, recursive=self.__dict__[
                                    "_recursive"], default=self.default)
        memo[id(self)] = copy
        dummy = deepcopy(dict(self), memo)
        copy.update(dummy)
        return copy

    __hash__ = None
