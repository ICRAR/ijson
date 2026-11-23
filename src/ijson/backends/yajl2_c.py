#
# Contributed by Rodrigo Tobar <rtobar@icrar.org>
#
# ICRAR - International Centre for Radio Astronomy Research
# (c) UWA - The University of Western Australia, 2016
# Copyright by UWA (in the framework of the ICRAR)
#
'''
Wrapper for _yajl2 C extension module
'''

from ijson import common, compat, utils, utils35
from . import _yajl2


_get_buf_size = lambda kwargs: kwargs.pop('buf_size', 64 * 1024)

@utils.coroutine
def basic_parse_basecoro(target, **kwargs):
    return _yajl2.basic_parse_basecoro(target.send, **kwargs)

def basic_parse_gen(file, **kwargs):
    f = compat.bytes_reader(file)
    buf_size = _get_buf_size(kwargs)
    return _yajl2.basic_parse(f, buf_size, **kwargs)

def basic_parse_async(file, **kwargs):
    buf_size = _get_buf_size(kwargs)
    return _yajl2.basic_parse_async(file, buf_size, **kwargs)

@utils.coroutine
def parse_basecoro(target, **kwargs):
    path_config, kwargs = common._split_path_config(kwargs)
    if any(path_config.values()):
        return common.parse_basecoro.__wrapped__(target, **path_config, **kwargs)
    return _yajl2.parse_basecoro(target.send, **kwargs)

def parse_gen(file, **kwargs):
    path_config, kwargs = common._split_path_config(kwargs)
    if any(path_config.values()):
        return common._make_parse_gen(globals())(file, **path_config, **kwargs)
    f = compat.bytes_reader(file)
    buf_size = _get_buf_size(kwargs)
    return _yajl2.parse(f, buf_size, **kwargs)

def parse_async(file, **kwargs):
    path_config, kwargs = common._split_path_config(kwargs)
    if any(path_config.values()):
        return utils35._make_parse_async(globals())(file, **path_config, **kwargs)
    buf_size = _get_buf_size(kwargs)
    return _yajl2.parse_async(file, buf_size, **kwargs)

@utils.coroutine
def kvitems_basecoro(target, prefix, map_type=None, **kwargs):
    prefix = common._normalize_prefix(prefix)
    if isinstance(prefix, tuple):
        return common.kvitems_basecoro.__wrapped__(target, prefix, map_type, **kwargs)
    return _yajl2.kvitems_basecoro(target.send, prefix, map_type, **kwargs)

def kvitems_gen(file, prefix, map_type=None, **kwargs):
    prefix, path_config, kwargs = common._prepare_prefix(prefix, kwargs)
    if any(path_config.values()):
        return common._make_kvitems_gen(globals())(
            file, prefix, map_type=map_type, **path_config, **kwargs
        )
    f = compat.bytes_reader(file)
    buf_size = _get_buf_size(kwargs)
    return _yajl2.kvitems(f, buf_size, prefix, map_type, **kwargs)

def kvitems_async(file, prefix, map_type=None, **kwargs):
    prefix, path_config, kwargs = common._prepare_prefix(prefix, kwargs)
    if any(path_config.values()):
        return utils35._make_kvitems_async(globals())(
            file, prefix, map_type=map_type, **path_config, **kwargs
        )
    buf_size = _get_buf_size(kwargs)
    return _yajl2.kvitems_async(file, buf_size, prefix, map_type, **kwargs)

@utils.coroutine
def items_basecoro(target, prefix, map_type=None, **kwargs):
    prefix = common._normalize_prefix(prefix)
    if isinstance(prefix, tuple):
        return common.items_basecoro.__wrapped__(target, prefix, map_type, **kwargs)
    return _yajl2.items_basecoro(target.send, prefix, map_type, **kwargs)

def items_gen(file, prefix, map_type=None, **kwargs):
    prefix, path_config, kwargs = common._prepare_prefix(prefix, kwargs)
    if any(path_config.values()):
        return common._make_items_gen(globals())(
            file, prefix, map_type=map_type, **path_config, **kwargs
        )
    f = compat.bytes_reader(file)
    buf_size = _get_buf_size(kwargs)
    return _yajl2.items(f, buf_size, prefix, map_type, **kwargs)

def items_async(file, prefix, map_type=None, **kwargs):
    prefix, path_config, kwargs = common._prepare_prefix(prefix, kwargs)
    if any(path_config.values()):
        return utils35._make_items_async(globals())(
            file, prefix, map_type=map_type, **path_config, **kwargs
        )
    buf_size = _get_buf_size(kwargs)
    return _yajl2.items_async(file, buf_size, prefix, map_type, **kwargs)

common.enrich_backend(globals())
