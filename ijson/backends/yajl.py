'''
Wrapper for YAJL C library version 1.x.
'''

from ctypes import Structure, c_uint, byref

from ijson import common, utils
from ijson.backends import _yajl2_ctypes_common


yajl = _yajl2_ctypes_common.get_yajl(1)

class Config(Structure):
    _fields_ = [
        ("allowComments", c_uint),
        ("checkUTF8", c_uint)
    ]


@utils.coroutine
def basic_parse_basecoro(target, allow_comments=False, check_utf8=False,
                         use_float=False):
    '''
    Iterator yielding unprefixed events.

    Parameters:

    - f: a readable file-like object with JSON input
    - allow_comments: tells parser to allow comments in JSON input
    - check_utf8: if True, parser will cause an error if input is invalid utf-8
    - buf_size: a size of an input buffer
    '''
    callbacks = _yajl2_ctypes_common.make_callbaks(target.send, use_float)
    config = Config(allow_comments, check_utf8)
    handle = yajl.yajl_alloc(byref(callbacks), byref(config), None, None)
    try:
        while True:
            try:
                buffer = (yield)
            except GeneratorExit:
                buffer = b''
            if buffer:
                result = yajl.yajl_parse(handle, buffer, len(buffer))
            else:
                result = yajl.yajl_parse_complete(handle)
            if result == _yajl2_ctypes_common.YAJL_ERROR:
                error = _yajl2_ctypes_common.yajl_get_error(yajl, handle, buffer)
                raise common.JSONError(error.decode('utf-8'))
            elif not buffer:
                if result == _yajl2_ctypes_common.YAJL_INSUFFICIENT_DATA:
                    raise common.IncompleteJSONError('Incomplete JSON data')
                break
    finally:
        yajl.yajl_free(handle)


common.enrich_backend(globals())
