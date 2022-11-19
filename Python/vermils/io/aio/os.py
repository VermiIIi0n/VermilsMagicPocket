import os as _os
from ...asynctools import to_async

__all__ = (
    "fsync",
    "listdir",
    "mkdir",
    "makedirs",
    "link",
    "symlink",
    "stat",
    "remove",
    "removedirs",
    "replace",
)

fsync = to_async(_os.fsync)

listdir = to_async(_os.listdir)

mkdir = to_async(_os.mkdir)

makedirs = to_async(_os.makedirs)

link = to_async(_os.link)

symlink = to_async(_os.symlink)

stat = to_async(_os.stat)

remove = to_async(_os.remove)

removedirs = to_async(_os.removedirs)

replace = to_async(_os.replace)
