from typing import AsyncIterable, AsyncIterator, Iterable, Iterator

from ijson import compat


def _to_bytes(chunk, warned: bool):
    if isinstance(chunk, bytes):
        return chunk, warned
    if isinstance(chunk, str):
        if not warned:
            compat._warn_and_return(None)
            warned = True
        return chunk.encode("utf-8"), warned
    raise TypeError("from_iter expects an iterable of bytes or str")


class IterReader:
    """File-like object backed by a byte iterator."""

    def __init__(self, byte_iter: Iterator[bytes]):
        self._iter = byte_iter
        self._warned = False

    def read(self, n: int) -> bytes:
        if n == 0:
            return b""
        chunk, self._warned = _to_bytes(next(self._iter, b""), self._warned)
        return chunk


class AiterReader:
    """Async file-like object backed by an async byte iterator."""

    def __init__(self, byte_aiter: AsyncIterator[bytes]):
        self._aiter = byte_aiter
        self._warned = False

    async def read(self, n: int) -> bytes:
        if n == 0:
            return b""
        chunk, self._warned = _to_bytes(await anext(self._aiter, b""), self._warned)
        return chunk


def from_iter(byte_iter: Iterable[bytes]) -> IterReader:
    """Convert a synchronous byte iterable to a file-like object."""
    return IterReader(iter(byte_iter))


def from_aiter(byte_aiter: AsyncIterable[bytes]) -> AiterReader:
    """Convert an asynchronous byte iterable to an async file-like object."""
    return AiterReader(aiter(byte_aiter))
