'''
Backend independent higher level interfaces, common exceptions.
'''
import decimal
from ijson import compat, utils


class JSONError(Exception):
    '''
    Base exception for all parsing errors.
    '''
    pass


class IncompleteJSONError(JSONError):
    '''
    Raised when the parser can't read expected data from a stream.
    '''
    pass


@utils.coroutine
def parse_basecoro(target):
    '''
    A coroutine dispatching parsing events with the information about their
    location with the JSON object tree. Events are tuples
    ``(prefix, type, value)``.

    Available types and values are:

    ('null', None)
    ('boolean', <True or False>)
    ('number', <int or Decimal>)
    ('string', <unicode>)
    ('map_key', <str>)
    ('start_map', None)
    ('end_map', None)
    ('start_array', None)
    ('end_array', None)

    Prefixes represent the path to the nested elements from the root of the JSON
    document. For example, given this document::

        {
          "array": [1, 2],
          "map": {
            "key": "value"
          }
        }

    the parser would yield events:

      ('', 'start_map', None)
      ('', 'map_key', 'array')
      ('array', 'start_array', None)
      ('array.item', 'number', 1)
      ('array.item', 'number', 2)
      ('array', 'end_array', None)
      ('', 'map_key', 'map')
      ('map', 'start_map', None)
      ('map', 'map_key', 'key')
      ('map.key', 'string', u'value')
      ('map', 'end_map', None)
      ('', 'end_map', None)

    '''
    path = []
    while True:
        event, value = yield
        if event == 'map_key':
            prefix = '.'.join(path[:-1])
            path[-1] = value
        elif event == 'start_map':
            prefix = '.'.join(path)
            path.append(None)
        elif event == 'end_map':
            path.pop()
            prefix = '.'.join(path)
        elif event == 'start_array':
            prefix = '.'.join(path)
            path.append('item')
        elif event == 'end_array':
            path.pop()
            prefix = '.'.join(path)
        else: # any scalar value
            prefix = '.'.join(path)
        target.send((prefix, event, value))


class ObjectBuilder(object):
    '''
    Incrementally builds an object from JSON parser events. Events are passed
    into the `event` function that accepts two parameters: event type and
    value. The object being built is available at any time from the `value`
    attribute.

    Example::

        >>> from ijson import basic_parse
        >>> from ijson.common import ObjectBuilder
        >>> from ijson.compat import BytesIO

        >>> builder = ObjectBuilder()
        >>> f = BytesIO(b'{"key": "value"}')
        >>> for event, value in basic_parse(f):
        ...     builder.event(event, value)
        >>> builder.value == {'key': 'value'}
        True

    '''
    def __init__(self, map_type=None):
        def initial_set(value):
            self.value = value
        self.containers = [initial_set]
        self.map_type = map_type or dict

    def event(self, event, value):
        if event == 'map_key':
            self.key = value
        elif event == 'start_map':
            mappable = self.map_type()
            self.containers[-1](mappable)
            def setter(value):
                mappable[self.key] = value
            self.containers.append(setter)
        elif event == 'start_array':
            array = []
            self.containers[-1](array)
            self.containers.append(array.append)
        elif event == 'end_array' or event == 'end_map':
            self.containers.pop()
        else:
            self.containers[-1](value)


@utils.coroutine
def items_basecoro(target, prefix, map_type=None):
    '''
    An couroutine dispatching native Python objects constructed from the events
    under a given prefix.
    '''
    while True:
        current, event, value = (yield)
        if current == prefix:
            if event in ('start_map', 'start_array'):
                builder = ObjectBuilder(map_type=map_type)
                end_event = event.replace('start', 'end')
                while (current, event) != (prefix, end_event):
                    builder.event(event, value)
                    current, event, value = (yield)
                del builder.containers[:]
                target.send(builder.value)
            else:
                target.send(value)


@utils.coroutine
def kvitems_basecoro(target, prefix, map_type=None):
    '''
    An coroutine dispatching (key, value) pairs constructed from the events
    under a given prefix. The prefix should point to JSON objects
    '''
    builder = None
    while True:
        path, event, value = (yield)
        while path == prefix and event == 'map_key':
            key = value
            builder = ObjectBuilder(map_type=map_type)
            path, event, value = (yield)
            while path != prefix:
                builder.event(event, value)
                path, event, value = (yield)
            del builder.containers[:]
            target.send((key, builder.value))


def number(str_value):
    '''
    Converts string with a numeric value into an int or a Decimal.
    Used in different backends for consistent number representation.
    '''
    for character in str_value:
        if character == '.' or character == 'e' or character == 'E':
            return decimal.Decimal(str_value)
    return int(str_value)


def file_source(f, use_string_reader, buf_size=64*1024):
    '''A generator that yields data from a file-like object'''
    if use_string_reader:
        f = compat.string_reader(f)
    else:
        f = compat.bytes_reader(f)
    while True:
        data = f.read(buf_size)
        yield data
        if not data:
            break


def _basic_parse_pipeline(backend, config):
    return (
        (backend['basic_parse_basecoro'], [], config),
    )


def _parse_pipeline(backend, config):
    return (
        (backend['parse_basecoro'], [], {}),
        (backend['basic_parse_basecoro'], [], config)
    )


def _items_pipeline(backend, prefix, map_type, config):
    return (
        (backend['items_basecoro'], (prefix,), {'map_type': map_type}),
        (backend['parse_basecoro'], [], {}),
        (backend['basic_parse_basecoro'], [], config)
    )


def _kvitems_pipeline(backend, prefix, map_type, config):
    return (
        (backend['kvitems_basecoro'], (prefix,), {'map_type': map_type}),
        (backend['parse_basecoro'], [], {}),
        (backend['basic_parse_basecoro'], [], config)
    )


def _make_basic_parse_coro(backend):
    def basic_parse_coro(target, **config):
        return utils.chain(
            target,
            *_basic_parse_pipeline(backend, config)
        )
    return utils.coroutine(basic_parse_coro)


def _make_parse_coro(backend):
    def parse_coro(target, **config):
        return utils.chain(
            target,
            *_parse_pipeline(backend, config)
        )
    return utils.coroutine(parse_coro)


def _make_items_coro(backend):
    def items_coro(target, prefix, map_type=None, **config):
        return utils.chain(
            target,
            *_items_pipeline(backend, prefix, map_type, config)
        )
    return utils.coroutine(items_coro)


def _make_kvitems_coro(backend):
    def kvitems(target, prefix, map_type=None, **config):
        return utils.chain(
            target,
            *_items_pipeline(backend, prefix, map_type, config)
        )
    return utils.coroutine(kvitems)


def _make_basic_parse(backend, use_string_reader):
    def basic_parse(f, buf_size=64*1024, **config):
        return utils.coros2gen(
            file_source(f, use_string_reader, buf_size=buf_size),
            *_basic_parse_pipeline(backend, config)
        )
    return basic_parse


def _make_parse(backend, use_string_reader):
    def parse(f, buf_size=64*1024, **config):
        return utils.coros2gen(
            file_source(f, use_string_reader, buf_size=buf_size),
            *_parse_pipeline(backend, config)
        )
    return parse


def _make_items(backend, use_string_reader):
    def items(f, prefix, map_type=None, buf_size=64*1024, **config):
        return utils.coros2gen(
            file_source(f, use_string_reader, buf_size=buf_size),
            *_items_pipeline(backend, prefix, map_type, config)
        )
    return items


def _make_kvitems(backend, use_string_reader):
    def kvitems(f, prefix, map_type=None, buf_size=64*1024, **config):
        return utils.coros2gen(
            file_source(f, use_string_reader, buf_size=buf_size),
            *_kvitems_pipeline(backend, prefix, map_type, config)
        )
    return kvitems


def enrich_backend(backend, use_string_reader=False):
    '''
    Provides a backend with any missing coroutines/generators/async-generators
    it might be missing by using the generic ones written in python.
    '''
    for gen_name in ('basic_parse', 'parse', 'items', 'kvitems'):
        basecoro_name = gen_name + '_basecoro'
        if basecoro_name not in backend:
            backend[basecoro_name] = globals()[basecoro_name]
        coro_name = gen_name + '_coro'
        if coro_name not in backend:
            factory = globals()['_make_' + coro_name]
            backend[coro_name] = factory(backend)
        if gen_name not in backend:
            factory = globals()['_make_' + gen_name]
            backend[gen_name] = factory(backend, use_string_reader)
        if compat.IS_PY35:
            from . import utils35
            async_name = gen_name + '_async'
            factory = getattr(utils35, '_make_' + async_name)
            backend[async_name] = factory(backend)
