import asyncio
import ijson
import pytest

from .test_base import JSON, JSON_EVENTS, JSON_PARSE_EVENTS, JSON_OBJECT

CHUNK_SIZE = 10


@pytest.fixture
def chunks():
    return [JSON[i : i + CHUNK_SIZE] for i in range(0, len(JSON), CHUNK_SIZE)]


@pytest.fixture
def async_chunks():
    async def chunks():
        for i in range(0, len(JSON), CHUNK_SIZE):
            yield JSON[i : i + CHUNK_SIZE]

    return chunks()


def test_from_iter_read0_does_not_consume():
    chunks = [b'{"key":', b'"value"}']
    file_obj = ijson.from_iter(iter(chunks))
    assert file_obj.read(0) == b""
    assert file_obj.read(1) == b'{"key":'
    assert file_obj.read(1) == b'"value"}'
    assert file_obj.read(1) == b""


def test_from_iter_accepts_iterable():
    chunks = [b'{"key":', b'"value"}']
    file_obj = ijson.from_iter(chunks)  # no iter(...)
    assert file_obj.read(1) == b'{"key":'
    assert file_obj.read(1) == b'"value"}'
    assert file_obj.read(1) == b""


def test_from_iter_basic_parse(backend, chunks):
    file_obj = ijson.from_iter(iter(chunks))
    assert JSON_EVENTS == list(backend.basic_parse(file_obj))


def test_from_iter_parse(backend, chunks):
    file_obj = ijson.from_iter(iter(chunks))
    assert JSON_PARSE_EVENTS == list(backend.parse(file_obj))


def test_from_iter_items(backend, chunks):
    file_obj = ijson.from_iter(iter(chunks))
    assert [JSON_OBJECT] == list(backend.items(file_obj, ""))


def test_from_iter_kvitems(backend, chunks):
    file_obj = ijson.from_iter(iter(chunks))
    kv = list(backend.kvitems(file_obj, ""))
    assert len(kv) == 1
    key, value = kv[0]
    assert key == "docs"
    assert value == JSON_OBJECT["docs"]


def test_from_aiter_read0_does_not_consume():
    async def chunks():
        yield b'{"key":'
        yield b'"value"}'

    async def main():
        file_obj = ijson.from_aiter(chunks())
        assert await file_obj.read(0) == b""
        assert await file_obj.read(1) == b'{"key":'
        assert await file_obj.read(1) == b'"value"}'
        assert await file_obj.read(1) == b""

    asyncio.run(main())


def test_from_aiter_basic_parse(backend, async_chunks):
    async def main():
        file_obj = ijson.from_aiter(async_chunks)
        events = [e async for e in backend.basic_parse(file_obj)]
        assert JSON_EVENTS == events

    asyncio.run(main())


def test_from_aiter_parse(backend, async_chunks):
    async def main():
        file_obj = ijson.from_aiter(async_chunks)
        events = [e async for e in backend.parse(file_obj)]
        assert JSON_PARSE_EVENTS == events

    asyncio.run(main())


def test_from_aiter_items(backend, async_chunks):
    async def main():
        file_obj = ijson.from_aiter(async_chunks)
        items = [obj async for obj in backend.items(file_obj, "")]
        assert [JSON_OBJECT] == items

    asyncio.run(main())


def test_from_aiter_kvitems(backend, async_chunks):
    async def main():
        file_obj = ijson.from_aiter(async_chunks)
        kv = [kv async for kv in backend.kvitems(file_obj, "")]
        assert len(kv) == 1
        key, value = kv[0]
        assert key == "docs"
        assert value == JSON_OBJECT["docs"]

    asyncio.run(main())
