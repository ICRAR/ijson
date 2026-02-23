import asyncio
import ijson


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

