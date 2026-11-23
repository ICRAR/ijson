"""Async event interception uses the same event contracts as sync pipelines."""
import asyncio
from collections import OrderedDict

import pytest

from ijson import utils35
from .support.async_ import AsyncReader


def collect(iterator):
    async def run():
        return [value async for value in iterator]
    return asyncio.run(run())


async def events(values):
    for value in values:
        await asyncio.sleep(0)
        yield value


@pytest.mark.parametrize('explicit', [True, False])
def test_basic_parse_to_parse_to_items(backend, explicit):
    suffix = '_async' if explicit else ''
    parse = getattr(backend, 'parse' + suffix)
    items = getattr(backend, 'items' + suffix)
    basic = backend.basic_parse_async(AsyncReader(b'{"rows":[1,{"value":2},[]]}'))
    assert collect(items(parse(basic), 'rows.item')) == [1, {'value': 2}, []]


@pytest.mark.parametrize('explicit', [True, False])
def test_kvitems_and_custom_map_type(backend, explicit):
    suffix = '_async' if explicit else ''
    stream = backend.parse_async(AsyncReader(b'{"one":{"a":1},"two":[]}'))
    values = collect(getattr(backend, 'kvitems' + suffix)(stream, '', map_type=OrderedDict))
    assert values == [('one', OrderedDict(a=1)), ('two', [])]
    assert isinstance(values[0][1], OrderedDict)


def test_intercept_after_advancing_parse_iterator(backend):
    async def run():
        stream = backend.parse_async(AsyncReader(b'["skip",1,2,3]'), buf_size=1)
        async for prefix, event, value in stream:
            if event == 'string' and value == 'skip':
                break
        return [value async for value in backend.items_async(stream, 'item')]
    assert asyncio.run(run()) == [1, 2, 3]


def test_user_provided_and_filtered_events(backend):
    async def modified():
        async for prefix, event, value in backend.parse_async(AsyncReader(b'[1,2,3]')):
            if event == 'number':
                value *= 10
            yield prefix, event, value
    assert collect(backend.items_async(modified(), 'item')) == [10, 20, 30]
    assert collect(backend.parse_async(events([('number', 42)]))) == [('', 'number', 42)]


def test_empty_async_event_stream(backend):
    assert collect(backend.parse_async(events([]))) == []
    assert collect(backend.items_async(events([]), '')) == []
    assert collect(backend.kvitems_async(events([]), '')) == []


def test_event_errors_propagate(backend):
    with pytest.raises(ValueError):
        collect(backend.parse_async(events([('number', 1, 'extra')])))
    with pytest.raises(ValueError):
        collect(backend.items_async(events([('number', 1)]), ''))


def test_source_is_consumed_lazily_and_errors_are_preserved(backend):
    consumed = []
    async def source():
        consumed.append(1)
        yield '', 'number', 1
        raise RuntimeError('source failed')
    async def run():
        iterator = backend.items_async(source(), '')
        assert consumed == []
        assert await anext(iterator) == 1
        assert consumed == [1]
        with pytest.raises(RuntimeError, match='source failed'):
            await anext(iterator)
    asyncio.run(run())


def test_async_file_protocol_takes_precedence(backend):
    class FileWithIterator(AsyncReader):
        def __aiter__(self):
            raise AssertionError('File must be read through read()')
    assert collect(backend.items_async(FileWithIterator(b'[1,2]'), 'item')) == [1, 2]


def test_adapter_closes_coroutine_without_owning_source():
    closed = []
    source_closed = []
    def pipeline(target):
        try:
            while True:
                target.send((yield))
        finally:
            closed.append(True)
    def primed(target):
        coroutine = pipeline(target)
        next(coroutine)
        return coroutine
    async def source():
        try:
            yield 1
            yield 2
        finally:
            source_closed.append(True)
    async def run():
        stream = source()
        iterator = utils35.coros2gen(stream, (primed, (), {}))
        assert await anext(iterator) == 1
        await iterator.aclose()
        assert closed == [True]
        assert source_closed == []
        assert await anext(stream) == 2
        await stream.aclose()
    asyncio.run(run())


def test_adapter_drains_emissions_before_reporting_pipeline_error():
    class Broken:
        def __init__(self, target):
            self.target = target
        def send(self, value):
            self.target.send(value)
            self.target.send(value + 1)
            raise RuntimeError('pipeline failed')
    async def run():
        iterator = utils35.coros2gen(events([1]), (Broken, (), {}))
        assert await anext(iterator) == 1
        assert await anext(iterator) == 2
        with pytest.raises(RuntimeError, match='pipeline failed'):
            await anext(iterator)
    asyncio.run(run())
