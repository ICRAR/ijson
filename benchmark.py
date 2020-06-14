#
# Contributed by Rodrigo Tobar <rtobar@icrar.org>
#
# ICRAR - International Centre for Radio Astronomy Research
# (c) UWA - The University of Western Australia, 2019
# Copyright by UWA (in the framework of the ICRAR)
#
'''
Benchmarking utility for ijson
'''
import argparse
import collections
import importlib
import io
import os
import sys
import time


from ijson import compat

_benchmarks = collections.OrderedDict()
def benchmark(f):
    _benchmarks[f.__name__] = f
    return f

@benchmark
def long_list(n):
    return b'[' + b','.join([b'1' for _ in range(n)]) + b']'

@benchmark
def big_int_object(n):
    return b'{' + b',\n'.join([b'"key_%d": %d' % (i, i) for i in range(n)]) + b'}'

@benchmark
def big_decimal_object(n):
    return b'{' + b',\n'.join([b'"key_%d": %d.0' % (i, i) for i in range(n)]) + b'}'

@benchmark
def big_null_object(n):
    return b'{' + b',\n'.join([b'"key_%d": null' % (i,) for i in range(n)]) + b'}'

@benchmark
def big_bool_object(n):
    return b'{' + b',\n'.join([
        b'"key_%d": %s' % (i, b"true" if i % 2 == 0 else b"false")
        for i in range(n)]) + b'}'

@benchmark
def big_str_object(n):
    return b'{' + b',\n'.join([b'"key_%d": "value_%d"' % (i, i) for i in range(n)]) + b'}'

@benchmark
def big_longstr_object(n):
    str_template = b"value that is very long and should cause a bit less of JSON parsing"
    return b'{' + b',\n'.join([b'"key_%d": "%s"' % (i, str_template) for i in range(n)]) + b'}'

@benchmark
def object_with_10_keys(n):
    template = b'{' + b',\n'.join([b'"key_%d": "value_%d"' % (i, i) for i in range(10)]) + b'}'
    return b'[' + b',\n'.join(
        template
        for _ in range(n)) + b']'

@benchmark
def empty_lists(n):
    return b'[' + b', '.join(b'[]' for _ in range(n)) + b']'

@benchmark
def empty_objects(n):
    return b'[' + b', '.join(b'{}' for _ in range(n)) + b']'

def parse_benchmarks(s):
    return [_benchmarks[name] for name in s.split(',')]


BACKEND_NAMES = 'python', 'yajl', 'yajl2', 'yajl2_cffi', 'yajl2_c'

def load_backends():
    backends = collections.OrderedDict()
    for backend_name in BACKEND_NAMES:
        try:
            backends[backend_name] = importlib.import_module('ijson.backends.' + backend_name)
        except ImportError:
            continue
    return backends
_backends = load_backends()

def parse_backends(s):
    backends = collections.OrderedDict()
    for name in s.split(','):
        backends[name] = _backends[name]
    return backends


def _stdout_tty_write_flush(message):
    stdout = sys.stdout
    if stdout.isatty():
        stdout.write(message)
        stdout.flush()


class progress_message(object):

    def __init__(self, message):
        self.message = message

    def __enter__(self):
        _stdout_tty_write_flush(self.message)
        return self

    def __exit__(self, *args):
        _stdout_tty_write_flush('\r\033[K')


if compat.IS_PY35:
    exec('''
class AsyncReader(object):
    def __init__(self, data):
        self.data = io.BytesIO(data)

    async def read(self, n=-1):
        return self.data.read(n)

    def close(self):
        self.data.close()

async def _run_async(method, reader, *method_args, **method_kwargs):
    async for _ in method(reader, *method_args, **method_kwargs):
        pass
    ''')

def run_benchmarks(args, benchmark_func=None, fname=None):
    if bool(benchmark_func) == bool(fname):
        raise ValueError("Either benchmark_func or fname must be given")
    if benchmark_func:
        bname = benchmark_func.__name__
        with progress_message('Generating data for benchmark %s...' % (bname,)):
            data = benchmark_func(args.size)
            size = len(data)
    else:
        bname = fname
        size = os.stat(args.input).st_size

    for backend_name, backend in args.backends.items():

        # Get correct method and prepare its arguments
        method = args.method
        if args.run_async:
            method += '_async'
        elif args.run_coro:
            method += '_coro'
        method = getattr(backend, method)
        method_args = ()
        if args.method in ('items', 'kvitems'):
            method_args = args.prefix,
        method_kwargs = {
            'multiple_values': args.multiple_values,
            'use_float': args.use_float
        }
        if not args.run_coro:
            method_kwargs['buf_size'] = args.bufsize

        # Prepare reader
        reader = None
        if not benchmark_func:
            reader = open(fname, 'rb')
        else:
            reader = AsyncReader(data) if args.run_async else io.BytesIO(data)

        # Prepare function that will run the benchmark
        if args.run_async:
            import asyncio
            loop = asyncio.new_event_loop()
            def run():
                try:
                    loop.run_until_complete(_run_async(method, reader, *method_args, **method_kwargs))
                finally:
                    loop.close()
        elif args.run_coro:
            def run():
                from ijson.utils import sendable_list
                events = sendable_list()
                coro = method(events, *method_args, **method_kwargs)
                if reader:
                    chunks = iter(lambda: reader.read(args.bufsize), b'')
                else:
                    chunks = (data[pos:pos + args.bufsize]
                              for pos in range(0, len(data), args.bufsize))
                for chunk in chunks:
                    coro.send(chunk)
                    del events[:]
                coro.close()
        else:
            def run():
                for _ in method(reader, *method_args, **method_kwargs):
                    pass

        # Go, go, go!
        start = time.time()
        run()
        duration = time.time() - start
        megabytes = size / 1024. / 1024.
        print("%.3f, %s, %s, %s, %.3f, %.3f" %
              (megabytes, args.method, bname, backend_name, duration,
               megabytes / duration))
        reader.close()


def main():
    DEFAULT_N = 100000
    DEFAULT_BUFSIZE = 64 * 1024
    ALL_BENCHMARKS = ','.join(_benchmarks)
    ALL_BACKENDS = ','.join(_backends)
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--size', type=int,
        help='Size of JSON content; actual size in bytes might differ, defaults to %d' % DEFAULT_N,
        default=DEFAULT_N)
    parser.add_argument('-S', '--bufsize', type=int,
        help='Buffer size used during parsing; defaults to %d' % DEFAULT_BUFSIZE,
        default=DEFAULT_BUFSIZE)
    parser.add_argument('-b', '--benchmarks', type=parse_benchmarks,
        help='Comma-separated list of benchmarks to include, defaults to %s' % ALL_BENCHMARKS,
        default=ALL_BENCHMARKS)
    parser.add_argument('-B', '--backends', type=parse_backends,
        help='Comma-separated list of backends to include, defaults to %s' % ALL_BACKENDS,
        default=ALL_BACKENDS)
    parser.add_argument('-l', '--list', action='store_true',
        help='List available benchmarks and backends')
    parser.add_argument('-i', '--input',
        help='File to use for benchmarks rather than built-in benchmarking functions')
    parser.add_argument('-m', '--multiple-values', action='store_true', default=False,
        help='Content has multiple JSON values, useful when used with -i')
    parser.add_argument('-f', '--use-float', action='store_true', default=False,
        help='Parse non-integer numbers as float instead of Decimal')
    parser.add_argument('-M', '--method', choices=['basic_parse', 'parse', 'kvitems', 'items'],
                        help='The method to benchmark', default='basic_parse')
    parser.add_argument('-c', '--coro', action='store_true', default=False,
                        dest='run_coro', help='Benchmark coroutine methods')
    if compat.IS_PY35:
        parser.add_argument('-a', '--async', action='store_true', default=False,
                            dest='run_async', help='Benchmark asyncio-enabled methods')
    parser.add_argument('-p', '--prefix', help='Prefix (used with -M items|kvitems)', default='')

    args = parser.parse_args()
    if args.list:
        msg = 'Backends:\n'
        msg += '\n'.join(' - %s' % name for name in _backends)
        msg += '\nBenchmarks:\n'
        msg += '\n'.join(' - %s' % name for name in _benchmarks)
        print(msg)
        return

    print("#mbytes,method,test_case,backend,time,mb_per_sec")
    if args.input:
        run_benchmarks(args, fname=args.input)
    else:
        for benchmark in args.benchmarks:
            run_benchmarks(args, benchmark)

if __name__ == '__main__':
    main()
