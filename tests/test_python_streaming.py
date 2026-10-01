"""Python-backend buffer and explicit float-conversion regressions."""

import io
import json
import subprocess
import sys

import pytest

from ijson import common
from ijson.backends import python as backend


@pytest.mark.parametrize('chunk_size', [1, 7, 65536])
def test_compaction_preserves_partial_tokens_and_exact_string_values(chunk_size):
    value = {
        'padding': 'x' * 70000,
        'escaped': '\\\\"' * 8 + '\ud800?\udc00\U0001f600',
        'number': 2 ** 100,
        'fraction': 1.25e-10,
    }
    payload = json.dumps(value).encode()
    assert list(backend.items(io.BytesIO(payload), '', buf_size=chunk_size, use_float=True)) == [value]


def test_compaction_preserves_absolute_error_offsets():
    prefix = '[' + json.dumps('x' * 70000) + ','
    with pytest.raises(backend.UnexpectedSymbol) as raised:
        list(backend.basic_parse(io.BytesIO((prefix + 'bad]').encode()), buf_size=1024))
    assert str(raised.value).endswith('at %d' % len(prefix))


@pytest.mark.parametrize('literal', ['1e400', '1e9223372036854775808'])
def test_positive_float_overflow_remains_an_error_by_default(literal):
    with pytest.raises(common.JSONError):
        list(backend.basic_parse(io.BytesIO(literal.encode()), use_float=True))


@pytest.mark.parametrize('literal', [
    '1e400', '-1e400', '1e9223372036854775808',
    '-1e9223372036854775808', '1e-9223372036854775808', str(2 ** 100),
])
def test_explicit_float_overflow_matches_stdlib_conversion(literal):
    actual = list(backend.basic_parse(
        io.BytesIO(literal.encode()), use_float=True, allow_float_overflow=True
    ))
    assert actual == [('number', json.loads(literal))]
    assert type(actual[0][1]) is type(json.loads(literal))


def test_float_overflow_option_requires_float_conversion():
    with pytest.raises(ValueError, match='requires use_float=True'):
        list(backend.basic_parse(io.BytesIO(b'1'), allow_float_overflow=True))


@pytest.mark.parametrize('payload', [
    b'{"a":1 "b":2}', b'[1 2]', b'[1,]', b'{"a":1,}', b'{"a":"\t"}',
    b'{"a":"\x00"}', b'{"a":NaN}', b'{"a":Infinity}', b'{} null', b'{"a":"\xff"}',
])
def test_compaction_and_float_option_do_not_relax_json_syntax(payload):
    with pytest.raises((ValueError, common.JSONError)):
        list(backend.basic_parse(
            io.BytesIO(payload), use_float=True, allow_float_overflow=True
        ))


def test_compact_long_string_array_has_bounded_peak_memory(tmp_path):
    code = '''
import json, resource, sys
from ijson.backends import python as backend
with open(sys.argv[1], 'rb') as stream:
    count = sum(1 for _ in backend.basic_parse(stream, buf_size=65536))
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
print(json.dumps({'events': count, 'rss_mib': peak / (1024*1024 if sys.platform=='darwin' else 1024)}))
'''
    measurements = []
    for size in (16, 256):
        path = tmp_path / ('strings-%d.json' % size)
        payload = b'x' * (size * 1024 * 1024 // 256)
        with path.open('wb') as stream:
            stream.write(b'[')
            for index in range(256):
                if index:
                    stream.write(b',')
                stream.write(b'"' + payload + b'"')
            stream.write(b']')
        result = subprocess.run(
            [sys.executable, '-c', code, str(path)], check=True,
            text=True, capture_output=True,
        )
        measurements.append(json.loads(result.stdout))
    assert all(value['events'] == 258 for value in measurements)
    assert measurements[1]['rss_mib'] - measurements[0]['rss_mib'] <= 48



@pytest.mark.parametrize('literal', ['+1', '+.1', '-.1', '1.e2', '-1.e2', '+01', '0.e+0'])
def test_number_conversion_never_accepts_invalid_json_number_syntax(literal):
    for kwargs in ({}, {'use_float': True}, {'use_float': True, 'allow_float_overflow': True}):
        with pytest.raises(common.JSONError):
            list(backend.basic_parse(io.BytesIO(literal.encode()), **kwargs))


@pytest.mark.parametrize('literal', ['0', '-0', '0.1', '1e+2', '1e-2', '-0.0'])
def test_valid_json_number_edges_preserve_conversion(literal):
    assert list(backend.basic_parse(
        io.BytesIO(literal.encode()), use_float=True, allow_float_overflow=True
    )) == [('number', json.loads(literal))]


@pytest.mark.parametrize('keyword', ['n', 'nu', 'nul', 't', 'tr', 'tru', 'f', 'fa', 'fal', 'fals'])
def test_partial_keywords_remain_incomplete_json(keyword):
    with pytest.raises(common.IncompleteJSONError):
        list(backend.basic_parse(io.BytesIO(keyword.encode())))



@pytest.mark.parametrize('payload', [
    '{"discarded":1}\u00a0', '{"discarded"\u2028:1}', '{\u2003"discarded":1}',
    '{"discarded":\u0661}', '{\v"discarded":1}', '{"discarded":\f1}',
])
def test_only_ascii_json_whitespace_and_digits_are_accepted(payload):
    with pytest.raises(common.JSONError):
        list(backend.basic_parse(io.BytesIO(payload.encode())))


def test_unicode_inside_quoted_strings_is_preserved():
    value = {'unicode': '\u00a0\u2028\u2003\u0661'}
    assert list(backend.items(io.BytesIO(json.dumps(value, ensure_ascii=False).encode()), '')) == [value]
