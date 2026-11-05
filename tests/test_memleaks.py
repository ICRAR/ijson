import asyncio
import contextlib
import ijson
import io

import pytest

from .support.async_ import AsyncReader


def _memusage():
    """memory usage in MB. getrusage defaults to KB on Linux."""
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def _exhaust(it):
    sum(1 for _ in it)


async def _async_exhaust(it):
    async for _ in it:
        pass


def _repeat(n, f, *args, exhaust=False, **kwargs):
    for _ in range(n):
        obj = f(*args, **kwargs)
        if exhaust:
            _exhaust(obj)


@pytest.fixture(autouse=True)
def _memory_leak_detection():
    THRESHOLD = 0.1
    memusage_start = _memusage()
    yield
    memusage_end = _memusage()
    assert (memusage_end - memusage_start) / memusage_start <= THRESHOLD



@pytest.mark.parametrize("exhaust", (True, False))
@pytest.mark.parametrize("n", (100000,))
@pytest.mark.parametrize("function",
    [
        pytest.param(construction, id=name) for name, construction in
        {
            "basic_parse": lambda backend: backend.basic_parse_gen(io.BytesIO(b'[1, 2, 3, 4, 5]')),
            "parse": lambda backend: backend.parse_gen(io.BytesIO(b'[1, 2, 3, 4, 5]')),
            "items": lambda backend: backend.items_gen(io.BytesIO(b'[1, 2, 3, 4, 5]'), 'item'),
            "kvitems": lambda backend: backend.kvitems_gen(io.BytesIO(b'{"a": 0, "b": 1, "c": 2}'), ''),
        }.items()
    ]
)
def test_generator(backend, function, n, exhaust):
    """Tests that running parse doesn't leak"""
    _repeat(n, function, backend, exhaust=exhaust)


@pytest.mark.parametrize("n", (100000,))
@pytest.mark.parametrize("invalid_construction",
    [
        pytest.param(construction, id=name) for name, construction in
        {
            "basic_parse": lambda backend: next(backend.basic_parse_gen(io.BytesIO(b'[1, 2, 3, 4, 5]'), not_a_kwarg=0)),
            "parse": lambda backend: next(backend.parse_gen(io.BytesIO(b'[1, 2, 3, 4, 5]'), not_a_kwarg=0)),
            "items": lambda backend: next(backend.items_gen(io.BytesIO(b'[1, 2, 3, 4, 5]'), 'item', not_a_kwarg=0)),
            "kvitems": lambda backend: next(backend.kvitems_gen(io.BytesIO(b'{"a": 0, "b": 1, "c": 2}'), '', not_a_kwarg=0)),
        }.items()
    ]
)
def test_erroneous_generator_construction(backend, invalid_construction, n):
    """Tests that running parse doesn't leak"""
    def erroneous_generator_construction():
        with pytest.raises(TypeError):
            invalid_construction(backend)
    _repeat(n, erroneous_generator_construction)


@pytest.mark.parametrize("n", (100000,))
@pytest.mark.parametrize("invalid_construction",
    [
        pytest.param(construction, id=name) for name, construction in
        {
            "basic_parse": lambda backend: backend.basic_parse_async(b'[1, 2, 3, 4, 5]', not_a_kwarg=0),
            "parse": lambda backend: backend.parse_async(b'[1, 2, 3, 4, 5]', not_a_kwarg=0),
            "items": lambda backend: backend.items_async(b'[1, 2, 3, 4, 5]', 'item', not_a_kwarg=0),
            "kvitems": lambda backend: backend.kvitems_async(b'{"a": 0, "b": 1, "c": 2}', '', not_a_kwarg=0),
        }.items()
    ]
)
def test_erroneous_async_construction(backend, n ,invalid_construction):
    def erroneous_async_construction():
        with pytest.raises(TypeError):
            invalid_construction(backend)
    _repeat(n, erroneous_async_construction)


@pytest.mark.parametrize("n", (100000,))
def test_async_gen_on_failed_basic_parse(backend, n):
    """Tests that basic_parse_gen doesn't leak after a failure during parsing."""

    def invalid_parsing(loop):
        async def run():
            # len(data) > buf_size forces a new slice to be created on each read(buf_size),
            # hence making it easier to memory leak
            buf_size = 100
            data = b'x' * (buf_size + 1)
            basic_parse_async = backend.basic_parse_async(AsyncReader(data), buf_size=buf_size)
            with pytest.raises(Exception):
                await _async_exhaust(basic_parse_async)
        loop.run_until_complete(run())

    with contextlib.closing(asyncio.new_event_loop()) as loop:
        _repeat(n, invalid_parsing, loop)


class _BadReader:
    def _read(self, n):
        if n == 0:
            return b''
        not_bytes_at_all = {1, 2, 3}
        return not_bytes_at_all


@pytest.mark.parametrize("n", (100000,))
def test_reader_returning_objects_that_dont_expose_memory(backend, n):
    """Checks for no memleaks when read() returns not bytes-like objects."""

    class BadReader(_BadReader):
        read = _BadReader._read

    def use_bad_reader():
        with pytest.raises(Exception):
            _exhaust(backend.basic_parse_gen(BadReader()))

    _repeat(n, use_bad_reader)
