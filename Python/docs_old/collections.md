# Collections

## `ObjDict`

`ObjDict` is a dictionary that allows you to access its keys as attributes.

It can recursively convert dictionaries to `ObjDict`s.

```Python
from vermils.collections import ObjDict

d = {
    "a": 1,
    0: 123,
    "b": {
        "c": 2,
        "d": 3
    }
}

obj_dict = ObjDict(d)

obj_dict.b.c == 2  # True

obj_dict[0] == 123  # True, because it's a dictionary subclass
```

## `StrChain`

Easy way to create strings.
