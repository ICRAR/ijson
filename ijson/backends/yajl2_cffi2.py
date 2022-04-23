"""
CFFI-Wrapper for YAJL C library version 2.x.
"""

import functools

from ijson import common, utils
from ijson.compat import b2s

import _yajl2_cffi

ffi = _yajl2_cffi.ffi
yajl = _yajl2_cffi.lib

YAJL_OK = 0
YAJL_CANCELLED = 1
YAJL_INSUFFICIENT_DATA = 2
YAJL_ERROR = 3

# constants defined in yajl_parse.h
YAJL_ALLOW_COMMENTS = 1
YAJL_MULTIPLE_VALUES = 8


def append_event_to_ctx(event):
    def wrapper(func):
        @functools.wraps(func)
        def wrapped(ctx, *args, **kwargs):
            value = func(*args, **kwargs)
            send = ffi.from_handle(ctx)
            send((event, value))
            return 1

        return wrapped

    return wrapper


# exception handling on these callbacks may need attention, see
# https://cffi.readthedocs.io/en/latest/using.html#def-extern


@ffi.def_extern("yajl_null")
@append_event_to_ctx("null")
def null():
    return None


@ffi.def_extern("yajl_boolean")
@append_event_to_ctx("boolean")
def boolean(val):
    return bool(val)


@ffi.def_extern("yajl_integer")
@append_event_to_ctx("number")
def integer(val):
    return int(val)


@ffi.def_extern("yajl_boolean")
@append_event_to_ctx("number")
def double(val):
    return val


@ffi.def_extern("yajl_number")
@append_event_to_ctx("number")
def number(val, length):
    return common.integer_or_decimal(b2s(ffi.string(val, maxlen=length)))


@ffi.def_extern("yajl_string")
@append_event_to_ctx("string")
def string(val, length):
    return ffi.string(val, maxlen=length).decode("utf-8")


@ffi.def_extern("yajl_start_map")
@append_event_to_ctx("start_map")
def start_map():
    return None


@ffi.def_extern("yajl_map_key")
@append_event_to_ctx("map_key")
def map_key(key, length):
    return ffi.string(key, maxlen=length).decode("utf-8")


@ffi.def_extern("yajl_end_map")
@append_event_to_ctx("end_map")
def end_map():
    return None


@ffi.def_extern("yajl_start_array")
@append_event_to_ctx("start_array")
def start_array():
    return None


@ffi.def_extern("yajl_end_array")
@append_event_to_ctx("end_array")
def end_array():
    return None


_decimal_callback_data = (
    yajl.yajl_null,
    yajl.yajl_boolean,
    ffi.NULL,
    ffi.NULL,
    yajl.yajl_number,
    yajl.yajl_string,
    yajl.yajl_start_map,
    yajl.yajl_map_key,
    yajl.yajl_end_map,
    yajl.yajl_start_array,
    yajl.yajl_end_array,
)

_float_callback_data = (
    yajl.yajl_null,
    yajl.yajl_boolean,
    yajl.yajl_integer,
    yajl.yajl_double,
    ffi.NULL,
    yajl.yajl_string,
    yajl.yajl_start_map,
    yajl.yajl_map_key,
    yajl.yajl_end_map,
    yajl.yajl_start_array,
    yajl.yajl_end_array,
)


def yajl_init(
    scope, send, allow_comments=False, multiple_values=False, use_float=False
):
    scope.ctx = ffi.new_handle(send)
    if use_float:
        scope.callbacks = ffi.new("yajl_callbacks*", _float_callback_data)
    else:
        scope.callbacks = ffi.new("yajl_callbacks*", _decimal_callback_data)
    handle = yajl.yajl_alloc(scope.callbacks, ffi.NULL, scope.ctx)

    if allow_comments:
        yajl.yajl_config(handle, YAJL_ALLOW_COMMENTS, ffi.cast("int", 1))
    if multiple_values:
        yajl.yajl_config(handle, YAJL_MULTIPLE_VALUES, ffi.cast("int", 1))

    return handle


def yajl_parse(handle, buffer):
    if buffer:
        result = yajl.yajl_parse(handle, buffer, len(buffer))
    else:
        result = yajl.yajl_complete_parse(handle)

    if result != YAJL_OK:
        perror = yajl.yajl_get_error(handle, 1, buffer, len(buffer))
        error = ffi.string(perror)
        try:
            error = error.decode("utf8")
        except UnicodeDecodeError:
            pass
        yajl.yajl_free_error(handle, perror)
        exception = (
            common.IncompleteJSONError
            if result == YAJL_INSUFFICIENT_DATA
            else common.JSONError
        )
        raise exception(error)


class Container(object):
    pass


@utils.coroutine
def basic_parse_basecoro(target, **config):
    """
    Coroutine dispatching unprefixed events.

    Parameters:

    - allow_comments: tells parser to allow comments in JSON input
    - multiple_values: allows the parser to parse multiple JSON objects
    """

    # the scope objects makes sure the C objects allocated in _yajl.init
    # are kept alive until this function is done
    scope = Container()

    handle = yajl_init(scope, target.send, **config)
    try:
        while True:
            try:
                buffer = yield
            except GeneratorExit:
                buffer = b""
            yajl_parse(handle, buffer)
            if not buffer:
                break
    finally:
        yajl.yajl_free(handle)


common.enrich_backend(globals())

if __name__ == "__main__":
    import json

    # parse added by enrich_backend()
    for event in parse(json.dumps({"foo": ["bar", "baz"]})):
        print(event)

