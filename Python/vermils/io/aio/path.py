import os.path
from ...asynctools import to_async

__all__ = (
    "exists",
    "isdir",
    "isfile",
    "islink",
    "samefile",
    "getsize",
    "getmtime",
    "getatime",
    "getctime",
)

exists = to_async(os.path.exists)

isdir = to_async(os.path.isdir)

isfile = to_async(os.path.isfile)

islink = to_async(os.path.islink)

samefile = to_async(os.path.samefile)

getsize = to_async(os.path.getsize)

getmtime = to_async(os.path.getmtime)

getatime = to_async(os.path.getatime)

getctime = to_async(os.path.getctime)
