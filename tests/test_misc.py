import collections
import gc
import importlib.util
import io
import sys
import weakref

import pytest

from ijson import common
from ijson.common import ObjectBuilder

from tests.test_base import JSON, JSON_EVENTS, JSON_PARSE_EVENTS, JSON_OBJECT,\
    JSON_KVITEMS


class TestMisc:
    """Miscellaneous unit tests"""

    def test_common_number_is_deprecated(self):
        with pytest.deprecated_call():
            common.number("1")

    def test_yajl2_c_loadable(self):
        spec = importlib.util.find_spec("ijson.backends._yajl2")
        if spec is None:
            pytest.skip("yajl2_c is not built")
        importlib.util.module_from_spec(spec)


class TestObjectBuilder:
    """Unit tests for the pure-python ObjectBuilder class"""

    def test_initial_value_is_none(self):
        assert ObjectBuilder().value is None

    def test_builds_expected_value(self):
        builder = ObjectBuilder()
        for event, value in JSON_EVENTS:
            builder.event(event, value)
        assert builder.value == JSON_OBJECT

    def test_custom_map_type(self):
        builder = ObjectBuilder(map_type=collections.OrderedDict)
        events = [
            ('start_map', None),
            ('map_key', 'a'),
            ('start_map', None),
            ('map_key', 'b'),
            ('number', 1),
            ('end_map', None),
            ('map_key', 'c'),
            ('start_array', None),
            ('number', 2),
            ('end_array', None),
            ('end_map', None),
        ]
        for event, value in events:
            builder.event(event, value)
        assert builder.value == {'a': {'b': 1}, 'c': [2]}
        assert type(builder.value) is collections.OrderedDict
        assert type(builder.value['a']) is collections.OrderedDict

    @pytest.mark.skipif(sys.implementation.name != "cpython",
                        reason="deterministic refcounting is CPython-only")
    # Each case guards a distinct cycle in the old implementation: nested_map
    # and nested_array covered the per-container setter closures, scalar_only
    # the initial_set closure created in __init__
    @pytest.mark.parametrize("events", [
        pytest.param([
            ('start_map', None),
            ('map_key', 'key'),
            ('start_map', None),
            ('map_key', 'inner'),
            ('string', 'value'),
            ('end_map', None),
            ('end_map', None),
        ], id="nested_map"),
        pytest.param([
            ('start_array', None),
            ('number', 1),
            ('start_array', None),
            ('number', 2),
            ('end_array', None),
            ('end_array', None),
        ], id="nested_array"),
        pytest.param([
            ('string', 'scalar'),
        ], id="scalar_only"),
    ])
    def test_builder_freed_without_cyclic_gc(self, events):
        """A discarded builder must be freed by refcounting alone.

        The previous implementation stored setter closures in
        self.containers; each closure referenced the builder, creating a
        reference cycle that kept the builder (and the value being built)
        alive until a cyclic GC pass."""
        builder = ObjectBuilder()
        for event, value in events:
            builder.event(event, value)
        ref = weakref.ref(builder)
        gc_was_enabled = gc.isenabled()
        gc.disable()
        try:
            del builder
            assert ref() is None
        finally:
            if gc_was_enabled:
                gc.enable()


class TestMainEntryPoints:
    """Tests that main API entry points work against different types of inputs automatically"""

    def _assert_invalid_type(self, routine, *args, **kwargs):
        # Functions are not valid inputs
        with pytest.raises(ValueError):
            routine(lambda _: JSON, *args, **kwargs)

    def _assert_bytes(self, expected_results, routine, *args, **kwargs):
        results = list(routine(JSON, *args, **kwargs))
        assert expected_results == results

    def _assert_str(self, expected_results, routine, *args, **kwargs):
        with pytest.deprecated_call():
            results = list(routine(JSON.decode("utf-8"), *args, **kwargs))

    def _assert_file(self, expected_results, routine, *args, **kwargs):
        results = list(routine(io.BytesIO(JSON), *args, **kwargs))
        assert expected_results == results

    def _assert_async_file(self, expected_results, routine, *args, **kwargs):
        from .support.async_ import get_all
        results = get_all(routine, JSON, *args, **kwargs)
        expected_results == results

    def _assert_async_types_coroutine(self, expected_results, routine, *args, **kwargs):
        from .support.async_types_coroutines import get_all
        results = get_all(routine, JSON, *args, **kwargs)
        assert expected_results == results

    def _assert_events(self, expected_results, previous_routine, routine, *args, **kwargs):
        events = previous_routine(io.BytesIO(JSON))
        # Using a different generator to make the point that we can chain
        # user-provided code
        def event_yielder():
            for evt in events:
                yield evt
        results = list(routine(event_yielder(), *args, **kwargs))
        assert expected_results == results

    def _assert_entry_point(self, expected_results, previous_routine, routine,
                            *args, **kwargs):
        self._assert_invalid_type(routine, *args, **kwargs)
        self._assert_bytes(expected_results, routine, *args, **kwargs)
        self._assert_str(expected_results, routine, *args, **kwargs)
        self._assert_file(expected_results, routine, *args, **kwargs)
        self._assert_async_file(expected_results, routine, *args, **kwargs)
        self._assert_async_types_coroutine(expected_results, routine, *args, **kwargs)
        if previous_routine:
            self._assert_events(expected_results, previous_routine, routine, *args, **kwargs)

    def test_rich_basic_parse(self, backend):
        self._assert_entry_point(JSON_EVENTS, None, backend.basic_parse)

    def test_rich_parse(self, backend):
        self._assert_entry_point(JSON_PARSE_EVENTS, backend.basic_parse, backend.parse)

    def test_rich_items(self, backend):
        self._assert_entry_point([JSON_OBJECT], backend.parse, backend.items, '')

    def test_rich_kvitems(self, backend):
        self._assert_entry_point(JSON_KVITEMS, backend.parse, backend.kvitems, 'docs.item')