__all__ = ("DummyFileStream", "DummyAioFileStream", )


class DummyAioFileStream:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        ...

    async def write(self, data):
        ...

    async def read(self):
        ...

    async def seek(self, offset, whence=0):
        ...

    async def flush(self):
        ...

    async def close(self):
        ...


class DummyFileStream:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        ...

    def write(self, data):
        ...

    def read(self):
        ...

    def seek(self, offset, whence=0):
        ...

    def flush(self):
        ...

    def close(self):
        ...
