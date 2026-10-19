import asyncio
from contextlib import nullcontext
import ijson
import pytest


def test_from_iter_read0_does_not_consume():
    chunks = [b'{"key":', b'"value"}']
    file_obj = ijson.from_iter(iter(chunks))
    assert file_obj.read(0) == b""
    assert file_obj.read(1) == b'{"key":'
    assert file_obj.read(1) == b'"value"}'
    assert file_obj.read(1) == b""


@pytest.mark.parametrize(
    "chunks_factory",
    [list, tuple, iter, lambda chunks: (chunk for chunk in chunks)],
    ids=["list", "tuple", "iter", "generator"],
)
def test_from_iter_accepts_iterable(chunks_factory):
    chunks = chunks_factory([b'{"key":', b'"value"}'])
    file_obj = ijson.from_iter(chunks)
    assert file_obj.read(1) == b'{"key":'
    assert file_obj.read(1) == b'"value"}'
    assert file_obj.read(1) == b""


@pytest.mark.parametrize(
    "chunks_factory",
    [list, tuple, iter, lambda chunks: (chunk for chunk in chunks)],
    ids=["list", "tuple", "iter", "generator"],
)
def test_from_iter_accepts_string_and_warns(chunks_factory):
    chunks = chunks_factory(['{"key":', '"value"}'])
    file_obj = ijson.from_iter(chunks)
    with pytest.deprecated_call():
        assert file_obj.read(1) == b'{"key":'
    assert file_obj.read(1) == b'"value"}'
    assert file_obj.read(1) == b""


def test_from_iter_accepts_aiterable():
    async def chunks():
        yield b'{"key":'
        yield b'"value"}'

    async def main():
        file_obj = ijson.from_iter(chunks())
        assert await file_obj.read(0) == b""
        assert await file_obj.read(1) == b'{"key":'
        assert await file_obj.read(1) == b'"value"}'
        assert await file_obj.read(1) == b""

    asyncio.run(main())


def test_from_iter_accepts_async_string_chunks_and_warns():
    async def chunks():
        yield '{"key":'
        yield '"value"}'

    async def main():
        file_obj = ijson.from_iter(chunks())
        with pytest.deprecated_call():
            assert await file_obj.read(1) == b'{"key":'
        assert await file_obj.read(1) == b'"value"}'
        assert await file_obj.read(1) == b""

    asyncio.run(main())


@pytest.mark.parametrize(
    "chunks",
    [
        [b"", b"", b'[{"id": 1},', b'{"id": 2}]'],
        [b'[{"id": 1},', b"", b"", b'{"id": 2}]'],
        [b'[{"id":', b"", b"", b' 1},', b'{"id": 2}]'],
    ],
    ids=["leading", "between-records", "inside-record"],
)
@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("text", [False, True])
def test_from_iter_empty_chunks_preserve_records(backend, chunks, asynchronous, text):
    """Empty chunks must not end the stream or hide subsequent JSON records."""
    if text:
        chunks = [chunk.decode("utf-8") for chunk in chunks]
    with pytest.deprecated_call() if text else nullcontext():
        if asynchronous:
            async def source():
                for chunk in chunks:
                    yield chunk

            async def main():
                return [record async for record in backend.items_async(
                    ijson.from_iter(source()), "item")]

            records = asyncio.run(main())
        else:
            records = list(backend.items(
                ijson.from_iter(chunks), "item"))
    assert records == [{"id": 1}, {"id": 2}]


@pytest.mark.parametrize("chunks", [[], [b"", b""]])
@pytest.mark.parametrize("asynchronous", [False, True])
def test_from_iter_empty_source_reaches_eof(chunks, asynchronous):
    """An exhausted iterator still returns EOF repeatedly, even after empty chunks."""
    if asynchronous:
        async def source():
            for chunk in chunks:
                yield chunk

        async def main():
            reader = ijson.from_iter(source())
            return [await reader.read(size) for size in (0, 1, 1)]

        results = asyncio.run(main())
    else:
        reader = ijson.from_iter(chunks)
        results = [reader.read(size) for size in (0, 1, 1)]
    assert results == [b"", b"", b""]
