from typing import AsyncIterable, AsyncIterator, Iterable, Iterator


class IterReader:
    """File-like object backed by a byte iterator."""

    def __init__(self, byte_iter: Iterator[bytes]):
        self._iter = byte_iter

    def read(self, n: int) -> bytes:
        if n == 0:
            return b""
        return next(self._iter, b"")


class AiterReader:
    """Async file-like object backed by an async byte iterator."""

    def __init__(self, byte_aiter: AsyncIterator[bytes]):
        self._aiter = byte_aiter

    async def read(self, n: int) -> bytes:
        if n == 0:
            return b""
        return await anext(self._aiter, b"")


def from_iter(byte_iter: Iterable[bytes]) -> IterReader:
    """Convert a synchronous byte iterable to a file-like object."""
    return IterReader(iter(byte_iter))


def from_aiter(byte_aiter: AsyncIterable[bytes]) -> AiterReader:
    """Convert an asynchronous byte iterable to an async file-like object."""
    return AiterReader(aiter(byte_aiter))
