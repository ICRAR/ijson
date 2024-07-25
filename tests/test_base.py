# -*- coding:utf-8 -*-
from __future__ import unicode_literals
import collections
import ctypes
from decimal import Decimal
import itertools
import threading

import pytest

import ijson
from ijson import common
import warnings


JSON = b'''
{
  "docs": [
    {
      "null": null,
      "boolean": false,
      "true": true,
      "integer": 0,
      "double": 0.5,
      "exponent": 1.0e+2,
      "long": 10000000000,
      "string": "\\u0441\\u0442\\u0440\\u043e\\u043a\\u0430 - \xd1\x82\xd0\xb5\xd1\x81\xd1\x82",
      "\xc3\xb1and\xc3\xba": null
    },
    {
      "meta": [[1], {}]
    },
    {
      "meta": {"key": "value"}
    },
    {
      "meta": null
    },
    {
      "meta": []
    }
  ]
}
'''
JSON_OBJECT = {
    "docs": [
        {
            "null": None,
            "boolean": False,
            "true": True,
            "integer": 0,
            "double": Decimal("0.5"),
            "exponent": 1e+2,
            "long": 10000000000,
            "string": "строка - тест",
            "ñandú": None
        },
        {
            "meta": [[1], {}]
        },
        {
            "meta": {
                "key": "value"
            }
        },
        {
            "meta": None
        },
        {
            "meta": []
        }
    ]
}
JSON_PARSE_EVENTS = [
    ('', 'start_map', None),
    ('', 'map_key', 'docs'),
    ('docs', 'start_array', None),
    ('docs.item', 'start_map', None),
    ('docs.item', 'map_key', 'null'),
    ('docs.item.null', 'null', None),
    ('docs.item', 'map_key', 'boolean'),
    ('docs.item.boolean', 'boolean', False),
    ('docs.item', 'map_key', 'true'),
    ('docs.item.true', 'boolean', True),
    ('docs.item', 'map_key', 'integer'),
    ('docs.item.integer', 'number', 0),
    ('docs.item', 'map_key', 'double'),
    ('docs.item.double', 'number', Decimal('0.5')),
    ('docs.item', 'map_key', 'exponent'),
    ('docs.item.exponent', 'number', Decimal('1.0E+2')),
    ('docs.item', 'map_key', 'long'),
    ('docs.item.long', 'number', 10000000000),
    ('docs.item', 'map_key', 'string'),
    ('docs.item.string', 'string', 'строка - тест'),
    ('docs.item', 'map_key', 'ñandú'),
    ('docs.item.ñandú', 'null', None),
    ('docs.item', 'end_map', None),
    ('docs.item', 'start_map', None),
    ('docs.item', 'map_key', 'meta'),
    ('docs.item.meta', 'start_array', None),
    ('docs.item.meta.item', 'start_array', None),
    ('docs.item.meta.item.item', 'number', 1),
    ('docs.item.meta.item', 'end_array', None),
    ('docs.item.meta.item', 'start_map', None),
    ('docs.item.meta.item', 'end_map', None),
    ('docs.item.meta', 'end_array', None),
    ('docs.item', 'end_map', None),
    ('docs.item', 'start_map', None),
    ('docs.item', 'map_key', 'meta'),
    ('docs.item.meta', 'start_map', None),
    ('docs.item.meta', 'map_key', 'key'),
    ('docs.item.meta.key', 'string', 'value'),
    ('docs.item.meta', 'end_map', None),
    ('docs.item', 'end_map', None),
    ('docs.item', 'start_map', None),
    ('docs.item', 'map_key', 'meta'),
    ('docs.item.meta', 'null', None),
    ('docs.item', 'end_map', None),
    ('docs.item', 'start_map', None),
    ('docs.item', 'map_key', 'meta'),
    ('docs.item.meta', 'start_array', None),
    ('docs.item.meta', 'end_array', None),
    ('docs.item', 'end_map', None),
    ('docs', 'end_array', None),
    ('', 'end_map', None)
]
JSON_KVITEMS = [
    ("null", None),
    ("boolean", False),
    ("true", True),
    ("integer", 0),
    ("double", Decimal("0.5")),
    ("exponent", 1e+2),
    ("long", 10000000000),
    ("string", "строка - тест"),
    ("ñandú", None),
    ("meta", [[1], {}]),
    ("meta", {"key": "value"}),
    ("meta", None),
    ("meta", [])
]
JSON_KVITEMS_META = [
    ('key', 'value')
]
JSON_EVENTS = [
    ('start_map', None),
        ('map_key', 'docs'),
        ('start_array', None),
            ('start_map', None),
                ('map_key', 'null'),
                ('null', None),
                ('map_key', 'boolean'),
                ('boolean', False),
                ('map_key', 'true'),
                ('boolean', True),
                ('map_key', 'integer'),
                ('number', 0),
                ('map_key', 'double'),
                ('number', Decimal('0.5')),
                ('map_key', 'exponent'),
                ('number', 100),
                ('map_key', 'long'),
                ('number', 10000000000),
                ('map_key', 'string'),
                ('string', 'строка - тест'),
                ('map_key', 'ñandú'),
                ('null', None),
            ('end_map', None),
            ('start_map', None),
                ('map_key', 'meta'),
                ('start_array', None),
                    ('start_array', None),
                        ('number', 1),
                    ('end_array', None),
                    ('start_map', None),
                    ('end_map', None),
                ('end_array', None),
            ('end_map', None),
            ('start_map', None),
                ('map_key', 'meta'),
                ('start_map', None),
                    ('map_key', 'key'),
                    ('string', 'value'),
                ('end_map', None),
            ('end_map', None),
            ('start_map', None),
                ('map_key', 'meta'),
                ('null', None),
            ('end_map', None),
            ('start_map', None),
                ('map_key', 'meta'),
                ('start_array', None),
                ('end_array', None),
            ('end_map', None),
        ('end_array', None),
    ('end_map', None),
]

# Like JSON, but with an additional top-level array structure
ARRAY_JSON = b'[' + JSON + b']'
ARRAY_JSON_EVENTS = (
    [('start_array', None)] +
    JSON_EVENTS +
    [('end_array', None)]
)
ARRAY_JSON_PARSE_EVENTS = (
    [('', 'start_array', None)] +
    [('.'.join(filter(None, ('item', p))), t, e) for p, t, e in JSON_PARSE_EVENTS] +
    [('', 'end_array', None)]
)
ARRAY_JSON_OBJECT = [JSON_OBJECT]



SCALAR_JSON = b'0'
INVALID_JSONS = [
    b'["key", "value",]',      # trailing comma
    b'["key"  "value"]',       # no comma
    b'{"key": "value",}',      # trailing comma
    b'{"key": "value" "key"}', # no comma
    b'{"key"  "value"}',       # no colon
    b'invalid',                # unknown lexeme
    b'[1, 2] dangling junk',   # dangling junk
    b'}',                      # no corresponding opening token
    b']',                      # no corresponding opening token
    b'"\xa8"'                  # invalid UTF-8 byte sequence
]
INVALID_JSON_WITH_DANGLING_JUNK = INVALID_JSONS[6]
INCOMPLETE_JSONS = [
    b'',
    b'"test',
    b'[',
    b'[1',
    b'[1,',
    b'{',
    b'{"key"',
    b'{"key":',
    b'{"key": "value"',
    b'{"key": "value",',
]
INCOMPLETE_JSON_TOKENS = [
    b'n',
    b'nu',
    b'nul',
    b't',
    b'tr',
    b'tru',
    b'f',
    b'fa',
    b'fal',
    b'fals',
    b'[f',
    b'[fa',
    b'[fal',
    b'[fals',
    b'[t',
    b'[tr',
    b'[tru',
    b'[n',
    b'[nu',
    b'[nul',
    b'{"key": t',
    b'{"key": tr',
    b'{"key": tru',
    b'{"key": f',
    b'{"key": fa',
    b'{"key": fal',
    b'{"key": fals',
    b'{"key": n',
    b'{"key": nu',
    b'{"key": nul',
]
STRINGS_JSON = br'''
{
    "str1": "",
    "str2": "\"",
    "str3": "\\",
    "str4": "\\\\",
    "special\t": "\b\f\n\r\t"
}
'''
SURROGATE_PAIRS_JSON = br'"\uD83D\uDCA9"'
PARTIAL_ARRAY_JSONS = [
    (b'[1,', 1),
    (b'[1, 2 ', 1, 2),
    (b'[1, "abc"', 1, 'abc'),
    (b'[{"abc": [0, 1]}', {'abc': [0, 1]}),
    (b'[{"abc": [0, 1]},', {'abc': [0, 1]}),
]

items_test_case = collections.namedtuple('items_test_case', 'json, prefix, kvitems, items')
EMPTY_MEMBER_TEST_CASES = {
    'simple': items_test_case(
        b'{"a": {"": {"b": 1, "c": 2}}}',
        'a.',
        [("b", 1), ("c", 2)],
        [{"b": 1, "c": 2}]
    ),
    'embedded': items_test_case(
        b'{"a": {"": {"": {"b": 1, "c": 2}}}}',
        'a..',
        [("b", 1), ("c", 2)],
        [{"b": 1, "c": 2}]
    ),
    'top_level': items_test_case(
        b'{"": 1, "a": 2}',
        '',
        [("", 1), ("a", 2)],
        [{"": 1, "a": 2}]
    ),
    'top_level_embedded': items_test_case(
        b'{"": {"": 1}, "a": 2}',
        '',
        [("", {"": 1}), ("a", 2)],
        [{"": {"": 1}, "a": 2}]
    )
}


class warning_catcher:
    '''Encapsulates proper warning catch-all logic in python 2.7 and 3'''

    def __init__(self):
        self.catcher = warnings.catch_warnings(record=True)

    def __enter__(self):
        ret = self.catcher.__enter__()
        return ret

    def __exit__(self, *args):
        self.catcher.__exit__(*args)


class BackendSpecificTestCase:
    '''
    Base class for backend-specific tests, gives ability to easily and
    generically reference different methods on the backend. It requires
    subclasses to define a `backend` member with the backend module, and a
    `suffix` attribute indicating the method flavour to obtain.
    '''

    def __getattr__(self, name):
        return getattr(self.backend, name + self.method_suffix)


class IJsonTestsBase:
    '''
    Base class with common tests for all iteration methods.
    Subclasses implement `all()` and `first()` to collect events coming from
    a particuliar method.
    '''

    def _raises_json_error(self, json, **kwargs):
        with pytest.raises(common.JSONError):
            self.get_all(self.basic_parse, json, **kwargs)

    def _raises_incomplete_json_error(self, json):
        with pytest.raises(common.IncompleteJSONError):
            self.get_all(self.basic_parse, json)

    def test_basic_parse(self):
        events = self.get_all(self.basic_parse, JSON)
        assert JSON_EVENTS == events

    def test_basic_parse_threaded(self):
        thread = threading.Thread(target=self.test_basic_parse)
        thread.start()
        thread.join()

    def test_parse(self):
        events = self.get_all(self.parse, JSON)
        assert JSON_PARSE_EVENTS == events

    def test_items(self):
        events = self.get_all(self.items, JSON, '')
        assert [JSON_OBJECT] == events

    def test_items_twodictlevels(self):
        json = b'{"meta":{"view":{"columns":[{"id": -1}, {"id": -2}]}}}'
        ids = self.get_all(self.items, json, 'meta.view.columns.item.id')
        assert 2 == len(ids)
        assert [-2,-1], sorted(ids)

    @pytest.mark.parametrize(
        "json, prefix, expected_items",
        (
            (b'{"0.1": 0}', '0.1', [0]),
            (b'{"0.1": [{"a.b": 0}]}', '0.1.item.a.b', [0]),
            (b'{"0.1": 0, "0": {"1": 1}}', '0.1', [0, 1]),
            (b'{"abc.def": 0}', 'abc.def', [0]),
            (b'{"abc.def": 0}', 'abc', []),
            (b'{"abc.def": 0}', 'def', []),
        )
    )
    def test_items_with_dotted_name(self, json, prefix, expected_items):
        assert expected_items == self.get_all(self.items, json, prefix)

    def test_map_type(self):
        obj = self.get_first(self.items, JSON, '')
        assert isinstance(obj, dict)
        obj = self.get_first(self.items, JSON, '', map_type=collections.OrderedDict)
        assert isinstance(obj, collections.OrderedDict)

    def test_kvitems(self):
        kvitems = self.get_all(self.kvitems, JSON, 'docs.item')
        assert JSON_KVITEMS == kvitems

    def test_kvitems_toplevel(self):
        kvitems = self.get_all(self.kvitems, JSON, '')
        assert 1 == len(kvitems)
        key, value = kvitems[0]
        assert 'docs' == key
        assert JSON_OBJECT['docs'] == value

    def test_kvitems_empty(self):
        kvitems = self.get_all(self.kvitems, JSON, 'docs')
        assert [] == kvitems

    def test_kvitems_twodictlevels(self):
        json = b'{"meta":{"view":{"columns":[{"id": -1}, {"id": -2}]}}}'
        view = self.get_all(self.kvitems, json, 'meta.view')
        assert 1 == len(view)
        key, value = view[0]
        assert 'columns' == key
        assert [{'id': -1}, {'id': -2}] == value

    def test_kvitems_different_underlying_types(self):
        kvitems = self.get_all(self.kvitems, JSON, 'docs.item.meta')
        assert JSON_KVITEMS_META == kvitems

    def test_basic_parse_array(self):
        events = self.get_all(self.basic_parse, ARRAY_JSON)
        assert ARRAY_JSON_EVENTS == events

    def test_basic_parse_array_threaded(self):
        thread = threading.Thread(target=self.test_basic_parse_array)
        thread.start()
        thread.join()

    def test_parse_array(self):
        events = self.get_all(self.parse, ARRAY_JSON)
        assert ARRAY_JSON_PARSE_EVENTS == events

    def test_items_array(self):
        events = self.get_all(self.items, ARRAY_JSON, '')
        assert [ARRAY_JSON_OBJECT] == events

    def test_kvitems_array(self):
        kvitems = self.get_all(self.kvitems, ARRAY_JSON, 'item.docs.item')
        assert JSON_KVITEMS == kvitems

    def test_scalar(self):
        events = self.get_all(self.basic_parse, SCALAR_JSON)
        assert [('number', 0)] == events

    def test_strings(self):
        events = self.get_all(self.basic_parse, STRINGS_JSON)
        strings = [value for event, value in events if event == 'string']
        assert ['', '"', '\\', '\\\\', '\b\f\n\r\t'] == strings
        assert ('map_key', 'special\t') in events

    def test_surrogate_pairs(self):
        event = self.get_first(self.basic_parse, SURROGATE_PAIRS_JSON)
        parsed_string = event[1]
        assert '💩' == parsed_string

    def _get_numbers(self, json, use_float):
        events = self.get_all(self.basic_parse, json, use_float=use_float)
        return [value for event, value in events if event == 'number']


    @pytest.mark.parametrize(
        "json, expected_float_type, expected_numbers, use_float",
        (
            (b'[1, 1.0, 1E2]', Decimal, [1, Decimal("1.0"), Decimal("1e2")], False),
            (b'[1, 1.0, 1E2]', float, [1, 1., 100.], True),
            (b'1e400', Decimal, [Decimal('1e400')], False),
            (b'1e-400', Decimal, [Decimal('1e-400')], False),
            (b'1e-400', float, [0], True),
        )
    )
    def test_numbers(self, json, expected_float_type, expected_numbers, use_float):
        """Check that numbers are correctly parsed"""
        numbers = self._get_numbers(json, use_float=use_float)
        float_types = set(type(number) for number in numbers)
        float_types -= {int}
        assert 1 == len(float_types)
        assert expected_float_type == next(iter(float_types))
        assert expected_numbers == numbers


    def test_32bit_ints(self):
        """Test for 64-bit integers support when using use_float=true"""
        past32bits = 2 ** 32 + 1
        past32bits_as_json = ('%d' % past32bits).encode('utf8')
        if self.backend.capabilities.int64:
            parsed_number = self._get_numbers(past32bits_as_json, use_float=True)[0]
            assert past32bits == parsed_number
        else:
            self._raises_json_error(past32bits_as_json, use_float=True)

    def test_max_double(self):
        """Check that numbers bigger than MAX_DOUBLE (usually ~1e308) cannot be represented"""
        self._raises_json_error(b'1e400', use_float=True)

    @pytest.mark.parametrize(
        "json", [
            sign + prefix + suffix
            for sign, prefix, suffix in itertools.product(
                (b'', b'-'),
                (b'00', b'01', b'001'),
                (b'', b'.0', b'e0', b'E0')
            )
        ]
    )
    def test_invalid_leading_zeros(self, json):
        """Check leading zeros are invalid"""
        if not self.backend.capabilities.invalid_leading_zeros_detection:
            return
        self._raises_json_error(json)

    @pytest.mark.parametrize("json", (b'1e', b'0.1e', b'0E'))
    def test_incomplete_exponents(self, json):
        """incomplete exponents are invalid JSON"""
        self._raises_json_error(json)

    @pytest.mark.parametrize("json", (b'1.', b'.1'))
    def test_incomplete_fractions(self, json):
        """incomplete fractions are invalid JSON"""
        self._raises_json_error(json)

    def test_incomplete(self):
        for json in INCOMPLETE_JSONS:
            self._raises_incomplete_json_error(json)

    def test_incomplete_tokens(self):
        if not self.backend.capabilities.incomplete_json_tokens_detection:
            return
        for json in INCOMPLETE_JSON_TOKENS:
            self._raises_incomplete_json_error(json)

    def test_invalid(self):
        for json in INVALID_JSONS:
            if not self.backend.capabilities.incomplete_json_tokens_detection and json == INVALID_JSON_WITH_DANGLING_JUNK:
                continue
            self._raises_json_error(json)

    def test_multiple_values(self):
        """Test that the multiple_values flag works"""
        if not self.backend.capabilities.multiple_values:
            with pytest.raises(ValueError):
                self.get_all(self.basic_parse, "", multiple_values=True)
            return
        multiple_json = JSON + JSON + JSON
        items = lambda x, **kwargs: self.items(x, '', **kwargs)
        for func in (self.basic_parse, items):
            with pytest.raises(common.JSONError):
                self.get_all(func, multiple_json)
            with pytest.raises(common.JSONError):
                self.get_all(func, multiple_json, multiple_values=False)
            result = self.get_all(func, multiple_json, multiple_values=True)
            if func == items:
                assert [JSON_OBJECT, JSON_OBJECT, JSON_OBJECT] == result
            else:
                assert result, JSON_EVENTS + JSON_EVENTS + JSON_EVENTS == result

    def test_comments(self):
        json = b'{"a": 2 /* a comment */}'
        if self.backend.capabilities.c_comments:
            events = self.get_all(self.basic_parse, json, allow_comments=True)
            assert events is not None
        else:
            with pytest.raises(ValueError):
                self.get_all(self.basic_parse, json, allow_comments=True)

    @pytest.mark.parametrize("test_case", [
        pytest.param(value, id=name) for name, value in EMPTY_MEMBER_TEST_CASES.items()
    ])
    def test_kvitems_empty_member(self, test_case):
        pairs = self.get_all(self.kvitems, test_case.json, test_case.prefix)
        assert test_case.kvitems == pairs

    @pytest.mark.parametrize("test_case", [
        pytest.param(value, id=name) for name, value in EMPTY_MEMBER_TEST_CASES.items()
    ])
    def test_items_empty_member(self, test_case):
        objects = self.get_all(self.items, test_case.json, test_case.prefix)
        assert test_case.items == objects


class FileBasedTests:

    def test_string_stream(self):
        with warning_catcher() as warns:
            events = self.get_all(self.basic_parse, JSON.decode('utf-8'))
            assert JSON_EVENTS == events
        assert 1 == len(warns)
        assert DeprecationWarning, warns[0].category

    def test_different_buf_sizes(self):
        for buf_size in (1, 4, 16, 64, 256, 1024, 4098):
            events = self.get_all(self.basic_parse, JSON, buf_size=buf_size)
            assert JSON_EVENTS == events


def generate_backend_specific_tests(module, classname_prefix, method_suffix,
                                    *bases, **kwargs):
    for backend in ijson.ALL_BACKENDS:
        try:
            classname = 'Test%s%s' % (
                ''.join(p.capitalize() for p in backend.split('_')),
                classname_prefix
            )

            _bases = bases + (BackendSpecificTestCase,)
            _members = {
                'backend': ijson.get_backend(backend),
                'method_suffix': method_suffix,
            }
            members = kwargs.get('members', lambda _: {})
            _members.update(members(backend))
            module[classname] = type(classname, _bases, _members)
        except ImportError:
            pass


def generate_test_cases(module, classname, method_suffix, *bases):
        _bases = bases + (IJsonTestsBase,)
        members = lambda name: {
            'get_all': lambda self, *args, **kwargs: module['get_all'](*args, **kwargs),
            'get_first': lambda self, *args, **kwargs: module['get_first'](*args, **kwargs),
        }
        return generate_backend_specific_tests(module, classname, method_suffix,
                                               members=members, *_bases)