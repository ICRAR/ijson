"""Stop kvitems after the first complete matching object."""

import asyncio
from collections import OrderedDict
from decimal import Decimal
import io

import pytest

from ijson import common, utils


@pytest.mark.pull_only
@pytest.mark.parametrize("document,prefix,first,all_pairs", [
    (b'[{"a": 1, "b": 2}, {"c": 3}]', 'item',
     [('a', 1), ('b', 2)], [('a', 1), ('b', 2), ('c', 3)]),
    (b'{"a": {"x": 1}, "a": {"x": 2}}', 'a',
     [('x', 1)], [('x', 1), ('x', 2)]),
    (b'[{},{"x": 2}]', 'item', [], [('x', 2)]),
    (b'{"a": [{"value": {}}], "b": 2}', 'a.item',
     [('value', {})], [('value', {})]),
    (b'[null, [], 1, {"x": [1, {"y": 2}]}]', 'item',
     [('x', [1, {'y': 2}])], [('x', [1, {'y': 2}])]),
    (b'{"a": {"": {}, "next": 1}, "a": {"last": 2}}', 'a',
     [('', {}), ('next', 1)], [('', {}), ('next', 1), ('last', 2)]),
    (b'{"a": {"x": 1}}', 'missing', [], []),
    (b'{"a": [1, {}]}', '', [('a', [1, {}])], [('a', [1, {}])]),
])
@pytest.mark.parametrize("stop_after_first", [True, False])
def test_first_object(adaptor, document, prefix, first, all_pairs, stop_after_first):
    expected = first if stop_after_first else all_pairs
    assert adaptor.kvitems(document, prefix, stop_after_first=stop_after_first) == expected


@pytest.mark.pull_only
@pytest.mark.parametrize("document", [
    b'{"a": {"x": 1}, "tail": INVALID',
    b'{"a": {"x": 1}',
])
def test_stop_before_invalid_tail(adaptor, document):
    assert adaptor.kvitems(document, 'a', stop_after_first=True) == [('x', 1)]
    with pytest.raises(common.JSONError):
        adaptor.kvitems(document, 'a', stop_after_first=False)


@pytest.mark.pull_only
@pytest.mark.parametrize("document", [b'{"a": {"x":', b'{"a": {"x": INVALID}}'])
def test_error_before_first_object_ends(adaptor, document):
    with pytest.raises(common.JSONError):
        adaptor.kvitems(document, 'a', stop_after_first=True)


@pytest.mark.pull_only
def test_map_type_and_number_mode(adaptor):
    document = b'[{"nested": {"value": 1.5}}, {"later": 2}]'
    pairs = adaptor.kvitems(document, 'item', stop_after_first=True, map_type=OrderedDict)
    assert pairs == [('nested', OrderedDict([('value', Decimal('1.5'))]))]
    assert isinstance(pairs[0][1], OrderedDict)
    pairs = adaptor.kvitems(document, 'item', stop_after_first=True, use_float=True)
    assert type(pairs[0][1]['value']) is float


class OneRead:
    def __init__(self, document):
        self.document = document
        self.reads = 0

    def read(self, n):
        if n == 0:
            return b''
        self.reads += 1
        assert self.reads == 1, 'read beyond the first matching object'
        return self.document


class AsyncOneRead(OneRead):
    async def read(self, n):
        await asyncio.sleep(0)
        return super().read(n)


@pytest.mark.parametrize("document,expected", [
    (b'{"a": {"x": 1, "y": 2}', [('x', 1), ('y', 2)]),
    (b'{"a": {}', []),
])
def test_no_reads_after_completion(backend, document, expected):
    for routine in (backend.kvitems, backend.kvitems_gen):
        source = OneRead(document)
        events = routine(source, 'a', stop_after_first=True)
        assert list(events) == expected
        assert list(events) == []
        assert source.reads == 1

    async def run():
        for routine in (backend.kvitems, backend.kvitems_async):
            source = AsyncOneRead(document)
            events = routine(source, 'a', stop_after_first=True)
            assert [event async for event in events] == expected
            assert [event async for event in events] == []
            assert source.reads == 1
    asyncio.run(run())


def test_public_sources_and_chunk_boundaries(backend):
    document = b'{"a": {"unicode": "\xe2\x82\xac", "nested": [{}, [1]]}, "a": {"later": 2}}'
    expected = [('unicode', '\u20ac'), ('nested', [{}, [1]])]
    for source in (document, io.BytesIO(document)):
        assert list(backend.kvitems(source, 'a', stop_after_first=True, buf_size=1)) == expected
    with pytest.warns(DeprecationWarning):
        assert list(backend.kvitems(document.decode(), 'a', stop_after_first=True, buf_size=1)) == expected


def test_event_input_stops_at_matching_end(backend):
    first = list(backend.parse(b'{"a": {"x": 1}}'))[:-1]
    consumed = []

    def events():
        for event in first:
            consumed.append(event)
            yield event
        raise AssertionError('consumed events after the matching object')

    assert list(backend.kvitems(events(), 'a', stop_after_first=True)) == [('x', 1)]
    assert consumed == first


@pytest.mark.parametrize("chunk_size", [1, 1000])
@pytest.mark.parametrize("document,expected,end", [
    (b'{"a":{"x":1},"tail":INVALID', [('x', 1)], len(b'{"a":{"x":1}')),
    (b'{"a":{},"tail":INVALID', [], len(b'{"a":{}')),
])
def test_push_completion(backend, chunk_size, document, expected, end):
    pairs = utils.sendable_list()
    coro = backend.kvitems_coro(pairs, 'a', stop_after_first=True)
    for offset in range(0, len(document), chunk_size):
        chunk = document[offset:offset + chunk_size]
        if offset + len(chunk) < end:
            coro.send(chunk)
        else:
            with pytest.raises(StopIteration):
                coro.send(chunk)
            break
    assert pairs == expected
    coro.close()
    with pytest.raises(StopIteration):
        coro.send(b'ignored')


def test_push_close_before_completion(backend):
    coro = backend.kvitems_coro(utils.sendable_list(), 'a', stop_after_first=True)
    coro.send(b'{"a":{"x":')
    with pytest.raises(common.JSONError):
        coro.close()


def test_push_eof_without_match(backend):
    for close in (True, False):
        coro = backend.kvitems_coro(utils.sendable_list(), 'missing', stop_after_first=True)
        coro.send(b'{"a": 1}')
        if close:
            coro.close()
        else:
            with pytest.raises(StopIteration):
                coro.send(b'')
        coro.close()


@pytest.mark.pull_only
def test_multiple_top_level_values(adaptor):
    if not adaptor.backend.capabilities.multiple_values:
        pytest.skip('multiple values not supported')
    assert adaptor.kvitems(b'{"a": 1} {"b": 2}', '', stop_after_first=True,
                           multiple_values=True) == [('a', 1)]
    assert adaptor.kvitems(b'{"a": 1} {"b": 2}', '', stop_after_first=False,
                           multiple_values=True) == [('a', 1), ('b', 2)]


def test_sink_exception_is_not_completion(backend):
    error = RuntimeError('sink failed')

    class Sink:
        def send(self, event):
            raise error

    coro = backend.kvitems_coro(Sink(), 'a', stop_after_first=True)
    with pytest.raises(RuntimeError) as exc:
        coro.send(b'{"a":{"x":1}}')
    assert exc.value is error


@pytest.mark.pull_only
def test_map_type_exception_is_not_completion(adaptor):
    error = RuntimeError('map failed')

    def map_type():
        raise error

    with pytest.raises(RuntimeError) as exc:
        adaptor.kvitems(b'{"a":{"x":{}}}', 'a', stop_after_first=True, map_type=map_type)
    assert exc.value is error
