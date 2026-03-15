'''Dumping command-line utility'''

import argparse
import sys

import ijson


METHODS_WITH_COLUMN_HEADERS = {
    'basic_parse': 'name, value',
    'parse': 'path, name, value',
    'kvitems': 'key, value',
    'items': 'value',
}

def to_string(o):
    if isinstance(o, bytes):
        return o.decode("utf-8")
    return str(o)

def dump():
    description = '''
    Read JSON data from standard input, and dump
    ijson events (using methods basic_parse or parse),
    or content (using methods kvitems or items).'''
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-m', '--method', choices=METHODS_WITH_COLUMN_HEADERS,
                        help='The method to use for dumping. Defaults to %(default)s', default='basic_parse')
    parser.add_argument('-p', '--prefix', help='Prefix (used with -m items|kvitems)', default='')
    parser.add_argument('-M', '--multiple-values', help='Allow multiple values', action='store_true')
    args = parser.parse_args()

    method = getattr(ijson, args.method)
    method_args = ()
    method_kwargs = {}
    if args.method in ('items', 'kvitems'):
        method_args = args.prefix,
    if args.multiple_values:
        method_kwargs['multiple_values'] = True
    header = '#: ' + METHODS_WITH_COLUMN_HEADERS[args.method]
    print(header)
    print('-' * len(header))

    # Use the raw bytes stream in stdin if possible
    stdin = sys.stdin
    if hasattr(stdin, 'buffer'):
        stdin = stdin.buffer

    enumerated_results = enumerate(method(stdin, *method_args, **method_kwargs))
    if args.method == 'items':
        for i, result in enumerated_results:
            print('%i: %s' % (i, result))
    else:
        for i, result in enumerated_results:
            print('%i: %s' % (i, ', '.join(to_string(bit) for bit in result)))

if __name__ == '__main__':
    dump()