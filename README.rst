.. image:: https://travis-ci.com/ICRAR/ijson.svg?branch=master
    :target: https://travis-ci.com/ICRAR/ijson

.. image:: https://ci.appveyor.com/api/projects/status/32wiho6ojw3eakp8/branch/master?svg=true
    :target: https://ci.appveyor.com/project/rtobar/ijson/branch/master

.. image:: https://coveralls.io/repos/github/ICRAR/ijson/badge.svg?branch=master
    :target: https://coveralls.io/github/ICRAR/ijson?branch=master

.. image:: https://badge.fury.io/py/ijson.svg
    :target: https://badge.fury.io/py/ijson

.. image:: https://img.shields.io/pypi/pyversions/ijson.svg
    :target: https://pypi.python.org/pypi/ijson

.. image:: https://img.shields.io/pypi/dd/ijson.svg
    :target: https://pypi.python.org/pypi/ijson

.. image:: https://img.shields.io/pypi/dw/ijson.svg
    :target: https://pypi.python.org/pypi/ijson

.. image:: https://img.shields.io/pypi/dm/ijson.svg
    :target: https://pypi.python.org/pypi/ijson


=====
ijson
=====

Ijson is an iterative JSON parser with standard Python iterator interfaces.

.. contents::
   :local:


Usage
=====

All usage example will be using a JSON document describing geographical
objects:

.. code-block:: json

    {
      "earth": {
        "europe": [
          {"name": "Paris", "type": "city", "info": { ... }},
          {"name": "Thames", "type": "river", "info": { ... }},
          // ...
        ],
        "america": [
          {"name": "Texas", "type": "state", "info": { ... }},
          // ...
        ]
      }
    }


High-level interfaces
---------------------

Most common usage is having ijson yield native Python objects out of a JSON
stream located under a prefix.
This is done using the ``items`` function.
Here's how to process all European cities:

.. code-block::  python

    import ijson

    f = urlopen('http://.../')
    objects = ijson.items(f, 'earth.europe.item')
    cities = (o for o in objects if o['type'] == 'city')
    for city in cities:
        do_something_with(city)

For how to build a prefix see the prefix_ section below.

Other times it might be useful to iterate over object members
rather than objects themselves (e.g., when objects are too big).
In that case one can use the ``kvitems`` function instead:

.. code-block::  python

    import ijson

    f = urlopen('http://.../')
    european_places = ijson.kvitems(f, 'earth.europe.item')
    names = (v for k, v in european_places if k == 'name')
    for name in names:
        do_something_with(name)


Lower-level interfaces
----------------------

Sometimes when dealing with a particularly large JSON payload it may worth to
not even construct individual Python objects and react on individual events
immediately producing some result.
This is achieved using the ``parse`` function:

.. code-block::  python

    import ijson

    parser = ijson.parse(urlopen('http://.../'))
    stream.write('<geo>')
    for prefix, event, value in parser:
        if (prefix, event) == ('earth', 'map_key'):
            stream.write('<%s>' % value)
            continent = value
        elif prefix.endswith('.name'):
            stream.write('<object name="%s"/>' % value)
        elif (prefix, event) == ('earth.%s' % continent, 'end_map'):
            stream.write('</%s>' % continent)
    stream.write('</geo>')

Even more bare-bones is the ability to react on individual events
without even calculating a prefix
using the ``basic_parse`` function:

.. code-block:: python

    import ijson

    events = ijson.basic_parse(urlopen('http://.../'))
    num_names = sum(1 for event, value in events
                    if event == 'map_key' and value == 'name')


``asyncio`` support
-------------------

In python 3.5+ all of the methods above
have an ``*_async`` counterpart
that works on file-like asynchronous objects,
and that can be iterated asynchronously.
In other words, something like this:

.. code-block:: python

   import asyncio
   import ijson

   async def run():
      f = await async_urlopen('http://..../')
      async for object in ijson.items_async(f, 'earth.europe.item'):
         if object['type'] == 'city':
            do_something_with(city)
   asyncio.run(run())


Push interfaces
---------------

All examples above use a file-like object as the data input
(both the normal case, and for ``asyncio`` support),
and hence are "pull" interfaces,
with the library reading data as necessary.
If for whatever reason it's not possible to use such method,
you can still **push** data
through yet a different interface: `coroutines <https://www.python.org/dev/peps/pep-0342/>`_
(via generators, not ``asyncio`` coroutines).
Coroutines effectively allow users
to send data to them at any point in time,
with a final *target* coroutine-like object
receiving the results.

In the following example
the user is doing the reading
instead of letting the library do it:

.. code-block:: python

   import ijson

   @ijson.coroutine
   def print_cities():
      while True:
         obj = (yield)
         if obj['type'] != 'city':
            continue
         print(obj)

   coro = ijson.items_coro(print_cities(), 'earth.europe.item')
   f = urlopen('http://.../')
   for chunk in iter(functools.partial(f.read, buf_size)):
      coro.send(chunk)
   coro.close()

All four ijson iterators
have a ``*_coro`` counterpart
that work by pushing data into them.
Instead of receiving a file-like object
and option buffer size as arguments,
they receive a single ``target`` argument,
which should be a coroutine-like object
(anything implementing a ``send`` method)
through which results will be published.

An alternative to providing a coroutine
is to use ``ijson.sendable_list`` to accumulate results,
providing the list is cleared after each parsing iteration,
like this:

.. code-block:: python

   import ijson

   events = ijson.sendable_list()
   coro = ijson.items_coro(events, 'earth.europe.item')
   f = urlopen('http://.../')
   for chunk in iter(functools.partial(f.read, buf_size)):
      coro.send(chunk)
      process_accumulated_events(events)
      del events[:]
   coro.close()
   process_accumulated_events(events)


.. _options:

Options
=======

Additional options are supported by **all** ijson functions
to give users more fine-grained control over certain operations:

- The ``use_float`` option (defaults to ``False``)
  controls how non-integer values are returned to the user.
  If set to ``True`` users receive ``float()`` values;
  otherwise ``Decimal`` values are constructed.
  Note that building ``float`` values is usually faster,
  but on the other hand there might be loss of precision
  (which most applications will not care about)
  and will raise an exception when overflow occurs
  (e.g., if ``1e400`` is encountered).
  Future versions of ijson
  might change the default value of this option
  to ``True``.
- The ``multiple_values`` option (defaults to ``False``)
  controls whether multiple top-level values are supported.
  JSON content should contain a single top-level value
  (see `the JSON Grammar <https://tools.ietf.org/html/rfc7159#section-2>`_).
  However there are plenty of JSON files out in the wild
  that contain multiple top-level values,
  often separated by newlines.
  By default ijson will fail to process these
  with a ``parse error: trailing garbage`` error
  unless ``multiple_values=True`` is specified.
- Similarly the ``allow_comments`` option (defaults to ``False``)
  controls whether C-style comments (e.g., ``/* a comment */``),
  which are not supported by the JSON standard,
  are allowed in the content or not.
- For functions taking a file-like object,
  an additional ``buf_size`` option (defaults to ``65536`` or 64KB)
  specifies the amount of bytes the library
  should attempt to read each time.
- The ``items`` and ``kvitems`` functions, and all their variants,
  have an optional ``map_type`` argument (defaults to ``dict``)
  used to construct objects from the JSON stream.
  This should be a dict-like type supporting item assignment.


Events
======

When using the lower-level ``ijson.parse`` function,
three-element tuples are generated
containing a prefix, an event name, and a value.
Events will be one of the following:

- ``start_map`` and ``end_map`` indicate
  the beginning and end of a JSON object, respectively.
  They carry a ``None`` as their value.
- ``start_array`` and ``end_array`` indicate
  the beginning and end of a JSON array, respectively.
  They also carry a ``None`` as their value.
- ``map_key`` indicates the name of a field in a JSON object.
  Its associated value is the name itself.
- ``null``, ``boolean``, ``integer``, ``double``, ``number`` and ``string``
  all indicate actual content, which is stored in the associated value.


.. _prefix:

Prefix
======

A prefix represents the context within a JSON document
where an event originates at.
It works as follows:

- It starts as an empty string.
- A ``<name>`` part is appended when the parser starts parsing the contents
  of a JSON object member called ``name``,
  and removed once the content finishes.
- A literal ``item`` part is appended when the parser is parsing
  elements of a JSON array,
  and removed when the array ends.
- Parts are separated by ``.``.

When using the ``ijson.items`` function,
the prefix works as the selection
for which objects should be automatically built and returned by ijson.


Backends
========

Ijson provides several implementations of the actual parsing in the form of
backends located in ijson/backends:

- ``yajl2_c``: a C extension using `YAJL <http://lloyd.github.com/yajl/>`_ 2.x.
  This is the fastest, but *might* require a compiler and the YAJL development files
  to be present when installing this package.
  Binary wheel distributions exist for major platforms/architectures to spare users
  from having to compile the package.
- ``yajl2_cffi``: wrapper around `YAJL <http://lloyd.github.com/yajl/>`_ 2.x
  using CFFI.
- ``yajl2``: wrapper around YAJL 2.x using ctypes, for when you can't use CFFI
  for some reason.
- ``yajl``: deprecated YAJL 1.x + ctypes wrapper, for even older systems.
- ``python``: pure Python parser, good to use with PyPy

You can import a specific backend and use it in the same way as the top level
library:

.. code-block::  python

    import ijson.backends.yajl2_cffi as ijson

    for item in ijson.items(...):
        # ...

Importing the top level library as ``import ijson``
uses the first available backend in the same order of the list above.
Its name is recorded under ``ijson.backend``.


FAQ
===

#. **Q**: Does ijson work with ``bytes`` or ``str`` objects?

   **A**: In short: both are accepted as input, outputs are only ``str``.

   All ijson functions expecting a file-like object
   should ideally be given one
   that is opened in binary mode
   (i.e., its ``read`` function returns ``bytes`` objects, not ``str``).
   However if a text-mode file object is given
   then the library will automatically
   encode the strings into UTF-8 bytes.
   A warning is currently issued (but not visible by default)
   alerting users about this automatic conversion.

   On the other hand ijson always returns text data
   (JSON string values, object member names, event names, etc)
   as ``str`` objects in python 3,
   and ``unicode`` objects in python 2.7.
   This mimics the behavior of the system ``json`` module.

#. **Q**: How are numbers dealt with?

   **A**: ijson returns ``int`` values for integers
   and ``decimal.Decimal`` values for floating-point numbers.
   This is mostly because of historical reasons.
   Since 3.1 a new ``use_float`` option (defaults to ``False``)
   is available to return ``float`` values instead.
   See the options_ section for details.

#. **Q**: I'm getting an ``UnicodeDecodeError``, or an ``IncompleteJSONError`` with no message

   **A**: This error is caused by byte sequences that are not valid in UTF-8.
   In other words, the data given to ijson is not *really* UTF-8 encoded,
   or at least not properly.

   Depending on where the data comes from you have different options:

   * If you have control over the source of the data, fix it.

   * If you have a way to intercept the data flow,
     do so and pass it through a "byte corrector".
     For instance, if you have a shell pipeline
     feeding data through ``stdin`` into your process
     you can add something like ``... | iconv -f utf8 -t utf8 -c | ...``
     in between to correct invalid byte sequences.

   * If you are working purely in python,
     you can create a UTF-8 decoder
     using codecs' `incrementaldecoder <https://docs.python.org/3/library/codecs.html#codecs.getincrementaldecoder>`_
     to leniently decode your bytes into strings,
     and feed those strings (using a file-like class) into ijson
     (see our `string_reader_async internal class <https://github.com/ICRAR/ijson/blob/0157f3c65a7986970030d3faa75979ee205d3806/ijson/utils35.py#L19>`_
     for some inspiration).

   In the future ijson might offer something out of the box
   to deal with invalid UTF-8 byte sequences.

#. **Q**: I'm getting ``parse error: trailing garbage`` or ``Additional data found`` errors

   **A**: This error signals that the input
   contains more data than the top-level JSON value it's meant to contain.
   This is *usually* caused by JSON data sources
   containing multiple values, and is *usually* solved
   by passing the ``multiple_values=True`` to the ijson function in use.
   See the options_ section for details.

#. Are there any differences between the backends?

   Apart from their performance,
   all backends are designed to support the same capabilities.
   There are however some small known differences:

   * The ``yajl`` backend doesn't support ``multiple_values=True``.
     It also doesn't complain about additional data
     found after the end of the top-level JSON object.

   * The ``python`` backend doesn't support ``allow_comments=True``
     It also internally works with ``str`` objects, not ``bytes``,
     but this is an internal detail that users shouldn't need to worry about,
     and might change in the future.


Acknowledgements
================

ijson was originally developed and actively maintained until 2016
by `Ivan Sagalaev <http://softwaremaniacs.org/>`_.
In 2019 he
`handed over <https://github.com/isagalaev/ijson/pull/58#issuecomment-500596815>`_
the maintenance of the project and the PyPI ownership.

Python parser in ijson is relatively simple thanks to `Douglas Crockford
<http://www.crockford.com/>`_ who invented a strict, easy to parse syntax.

The `YAJL <http://lloyd.github.com/yajl/>`_ library by `Lloyd Hilaiel
<http://lloyd.io/>`_ is the most popular and efficient way to parse JSON in an
iterative fashion.

Ijson was inspired by `yajl-py <http://pykler.github.com/yajl-py/>`_ wrapper by
`Hatem Nassrat <http://www.nassrat.ca/>`_. Though ijson borrows almost nothing
from the actual yajl-py code it was used as an example of integration with yajl
using ctypes.
