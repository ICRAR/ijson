"""Lossless key paths and opt-in array positions across every input API."""
from collections import OrderedDict

import pytest


def test_tuple_paths_preserve_dots_and_empty_keys(adaptor):
    parsed = adaptor.parse(b'{"a.b":1,"a":{"b":2},"":3}', tuple_paths=True)
    assert parsed == [
        ((), 'start_map', None), ((), 'map_key', 'a.b'),
        (('a.b',), 'number', 1), ((), 'map_key', 'a'),
        (('a',), 'start_map', None), (('a',), 'map_key', 'b'),
        (('a', 'b'), 'number', 2), (('a',), 'end_map', None),
        ((), 'map_key', ''), (('',), 'number', 3), ((), 'end_map', None),
    ]


def test_tuple_items_and_kvitems(adaptor):
    source = b'{"a.b":{"value":1},"a":{"b":{"value":2}}}'
    assert adaptor.items(source, ('a.b',)) == [{'value': 1}]
    assert adaptor.items(source, ['a', 'b']) == [{'value': 2}]
    assert adaptor.kvitems(source, ('a.b',)) == [('value', 1)]
    assert adaptor.kvitems(source, iter(['a', 'b'])) == [('value', 2)]
    assert adaptor.items(b'42', ()) == [42]


def test_tuple_array_wildcards(adaptor):
    source = b'{"a.b":[{"x":1},{"x":2}]}'
    assert adaptor.items(source, ('a.b', 'item', 'x')) == [1, 2]
    assert adaptor.parse(b'[0]', tuple_paths=True) == [
        ((), 'start_array', None), (('item',), 'number', 0),
        ((), 'end_array', None),
    ]


def test_default_paths_and_false_options_are_unchanged(adaptor):
    expected = [('', 'start_array', None), ('item', 'number', 1), ('', 'end_array', None)]
    assert adaptor.parse(b'[1]') == expected
    assert adaptor.parse(b'[1]', tuple_paths=False, array_indices=False) == expected
    assert adaptor.items(b'{"0":1,"item":2}', '0') == [1]
    assert adaptor.items(b'{"0":1,"item":2}', 'item') == [2]


def test_array_indices_count_scalars_and_complete_containers(adaptor):
    parsed = adaptor.parse(b'[0,[],{},[1,2],{"x":3},4]', tuple_paths=True, array_indices=True)
    assert parsed == [
        ((), 'start_array', None), ((0,), 'number', 0),
        ((1,), 'start_array', None), ((1,), 'end_array', None),
        ((2,), 'start_map', None), ((2,), 'end_map', None),
        ((3,), 'start_array', None), ((3, 0), 'number', 1),
        ((3, 1), 'number', 2), ((3,), 'end_array', None),
        ((4,), 'start_map', None), ((4,), 'map_key', 'x'),
        ((4, 'x'), 'number', 3), ((4,), 'end_map', None),
        ((5,), 'number', 4), ((), 'end_array', None),
    ]


def test_select_array_positions_and_mixed_wildcards(adaptor):
    source = b'{"A":[{"B":[{"C":1},{"C":2}]},{"B":[{"C":3},{"C":4}]}]}'
    assert adaptor.items(source, ('A', 1, 'B', 0, 'C')) == [3]
    assert adaptor.items(source, ('A', 'item', 'B', 1, 'C')) == [2, 4]
    assert adaptor.items(source, ('A', 0, 'B', 'item', 'C')) == [1, 2]
    assert adaptor.items(source, ('A', 20)) == []
    assert adaptor.kvitems(source, ('A', 1, 'B', 0)) == [('C', 3)]


def test_numeric_keys_are_distinct_from_indices(adaptor):
    source = b'{"0":{"0":7},"a":[8,9]}'
    assert adaptor.items(source, ('0', '0')) == [7]
    assert adaptor.items(source, ('a', 0)) == [8]
    assert adaptor.items(source, ('a', '0')) == []
    assert adaptor.items(b'[1]', ('item',)) == [1]


def test_explicit_string_index_mode(adaptor):
    assert adaptor.parse(b'[1]', array_indices=True) == [
        ('', 'start_array', None), ('0', 'number', 1), ('', 'end_array', None),
    ]
    assert adaptor.items(b'{"a":[{"b":1},{"b":2}]}', 'a.1.b', array_indices=True) == [2]
    assert adaptor.items(b'{"a":[1,2]}', 'a.item', array_indices=True) == [1, 2]


def test_custom_maps_and_empty_keys(adaptor):
    values = adaptor.items(b'{"":[{"x":1}]}', ('', 0), map_type=OrderedDict)
    assert values == [OrderedDict(x=1)]
    assert type(values[0]) is OrderedDict
    assert adaptor.kvitems(b'{"":{"":1}}', ('',)) == [('', 1)]


@pytest.mark.parametrize('prefix', [(None,), (-1,), (True,), (1.5,)])
def test_invalid_path_components_are_rejected(adaptor, prefix):
    with pytest.raises((TypeError, ValueError)):
        adaptor.items(b'[1,2]', prefix)
    with pytest.raises((TypeError, ValueError)):
        adaptor.kvitems(b'[1,2]', prefix)


def test_multiple_roots_reset_array_indices(adaptor):
    parsed = adaptor.parse(b'[1,2] [3]', tuple_paths=True, array_indices=True, multiple_values=True)
    assert [(path, value) for path, event, value in parsed if event == 'number'] == [
        ((0,), 1), ((1,), 2), ((0,), 3),
    ]


def test_options_work_with_intercepted_sync_events(backend):
    basic = backend.basic_parse(b'{"a.b":[1,2]}')
    parsed = backend.parse(basic, tuple_paths=True, array_indices=True)
    assert list(backend.items(parsed, ('a.b', 1))) == [2]
    parsed = backend.parse(b'{"a":{"x":1}}', tuple_paths=True)
    assert list(backend.kvitems(parsed, ('a',))) == [('x', 1)]


@pytest.mark.pull_only
def test_short_reads_and_unicode_paths(adaptor):
    source = '{"\u03bb.x":[1,2]}'.encode('utf-8')
    assert adaptor.items(source, ('\u03bb.x', 1), buf_size=1) == [2]
