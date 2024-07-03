import importlib.util
import io

import pytest

from ijson import common

from .test_base import warning_catcher
from tests.test_base import JSON, JSON_EVENTS, JSON_PARSE_EVENTS, JSON_OBJECT,\
    generate_backend_specific_tests, JSON_KVITEMS


class Misc:
    """Miscellaneous unit tests"""

    def test_common_number_is_deprecated(self):
        with warning_catcher() as warns:
            common.number("1")
        assert 1 == len(warns)
        assert DeprecationWarning, warns[0].category

    def test_yajl2_c_loadable(self):
        spec = importlib.util.find_spec("ijson.backends._yajl2")
        if spec is None:
            self.skipTest("yajl2_c is not built")
        importlib.util.module_from_spec(spec)


class MainEntryPoints:

    def _assert_invalid_type(self, routine, *args, **kwargs):
        # Functions are not valid inputs
        with pytest.raises(ValueError):
            routine(lambda _: JSON, *args, **kwargs)

    def _assert_bytes(self, expected_results, routine, *args, **kwargs):
        results = list(routine(JSON, *args, **kwargs))
        assert expected_results == results

    def _assert_str(self, expected_results, routine, *args, **kwargs):
        with warning_catcher() as warns:
            results = list(routine(JSON.decode("utf-8"), *args, **kwargs))
        assert expected_results == results
        assert 1 == len(warns)

    def _assert_file(self, expected_results, routine, *args, **kwargs):
        results = list(routine(io.BytesIO(JSON), *args, **kwargs))
        assert expected_results == results

    def _assert_async_file(self, expected_results, routine, *args, **kwargs):
        from ._test_async import get_all
        results = get_all(routine, JSON, *args, **kwargs)
        expected_results == results

    def _assert_async_types_coroutine(self, expected_results, routine, *args, **kwargs):
        from ._test_async_types_coroutine import get_all
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

    def test_rich_basic_parse(self):
        self._assert_entry_point(JSON_EVENTS, None, self.basic_parse)

    def test_rich_parse(self):
        self._assert_entry_point(JSON_PARSE_EVENTS, self.basic_parse, self.parse)

    def test_rich_items(self):
        self._assert_entry_point([JSON_OBJECT], self.parse, self.items, '')

    def test_rich_kvitems(self):
        self._assert_entry_point(JSON_KVITEMS, self.parse, self.kvitems, 'docs.item')

generate_backend_specific_tests(globals(), 'MainEntryPoints', '', MainEntryPoints)