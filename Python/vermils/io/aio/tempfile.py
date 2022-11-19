from tempfile import NamedTemporaryFile as NTF
from typing import overload
from .wrappers import AsyncIOStream, TEXTMODE, BINARYMODE


@overload
def NamedTemporaryFile(mode: TEXTMODE, *args, **kw) -> AsyncIOStream[str]: ...


@overload
def NamedTemporaryFile(mode: BINARYMODE, *args, **kw) -> AsyncIOStream[bytes]: ...


@overload
def NamedTemporaryFile() -> AsyncIOStream[str]: ...


def NamedTemporaryFile(mode: TEXTMODE | BINARYMODE = "w+", *args, **kw
                       ) -> AsyncIOStream:
    hdlr = NTF(mode, *args, **kw)
    return AsyncIOStream(hdlr)
