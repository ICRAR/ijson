# Changelog

## Development version

* A new ``use_float`` option has been added to all backends
  to control whether ``float`` values should be returned
  for non-integer numbers instead of ``Decimal`` objects.
  Using this option trades loss of precision
  (which most applications probably don't care)
  for performance (which most application do care about).
  Historically ijson has returned ``Decimal`` objects,
  and therefore the option defaults to ``False``
  for backwards compatibility,
  but in later releases this default could change to ``True``.
* ``ijson.common.number`` is marked as deprecated,
  and will be removed on some later release.

## [3.0.4]

* Fixed errors triggered by JSON documents
  where the top-level value is an object containing
  an empty-named member (e.g., ``{"": 1}``).
  Although such documents are valid JSON,
  they broke basic assumptions made
  by the ``kvitems`` and ``items`` functions
  (and all their variants)
  in all backends,
  producing different types of unexpected failures,
  including segmentation faults, raising unexpected exceptions,
  and producing wrong results.

## [3.0.3]

* Fixed segmentation fault in ``yajl2_c`` backend's ``parse``
  caused by the previous fix introduced in 3.0.2 (#29).

## [3.0.2]

* Fixed memory leak in ``yajl2_c`` backend's ``parse`` functionality (#28).

## [3.0.1]

* Adding back the ``parse``, ``kvitems`` and ``items`` functions
  under the ``ijson.common`` module (#27).
  These functions take an events iterable instead of a file
  and are backend-independent (which is not great for performance).
  They were accidentaly removed in the redesign of ijson 3.0,
  which is why they are coming back.
  In the future they will slowly transition into being
  backend-specific rather than independent.

## [3.0]

* Exposing backend's name under ``<backend>.backend``,
  and default backend's name under ``ijson.backend``.
* Exposing ``ijson.sendable_list`` to users in case it comes in handy.

## [3.0rc3]

* Implemented all asynchronous iterables (i.e., ``*_async`` functions)
  in C for the ``yajl2_c`` backend for increased performance.
* Adding Windows builds via AppVeyor, generating binary wheels
  for Python 3.5+.

## [3.0rc2]

* Fixed known problem with 3.0rc1,
  namely checking that asynchronous files are opened
  in the correct mode (i.e., binary).
* Improved the protocol for user-facing coroutines,
  where instead of having to send a final, empty bytes string
  to finish the parsing process
  users can simply call ``.close()`` on the coroutine.
* Greatly increased testing of user-facing coroutines,
  which in turn uncovered problems that were fixed.
* Adding ability to benchmark coroutines
  with ``benchmark.py``.
* Including C code in coverage measurements,
  and increased overall code coverage up to 99%.

## [3.0rc1]

* Full re-design of ijson:
  instead of working with generators on a "pull" model,
  it now uses coroutines on a "push" model.
  The current set of generators
  (``basic_parse``, ``parse``, ``kvitems`` and ``items``)
  are implemented on top of these coroutines,
  and are fully backward compatible.
  Some text comparing the old a new designs
  can be found [here](notes/design_notes.rst).
* Initial support for ``asyncio`` in python 3.5+
  in the for of ``async for``-enabled asynchronous iterators.
  These are named ``*_async``, and take a file-like object
  whose ``read()`` method can be ``awaited`` on.
* Exposure of underlying infrastructure implementing the push model.
  These are named ``*_coro``,
  and take a coroutine-like object
  (i.e., implementing a ``send`` method)
  instead of file-like objects.
  In this scheme, users are in charge
  of sending chunks of data into the coroutines
  using ``coro.send(chunk)``.
* C backend performance improved
  by avoiding memory copies when possible
  when reading data off a file (i.e., using ``readinto`` when possible)
  and by avoiding tuple packing/unpacking in certain situations.
* C extension broken down into separate source files
  for easier understanding and maintenance.

## [2.6.1]

* Fixed a deprecation warning in the C backend
  present in python 3.8 when parsing Decimal values.

## [2.6.0]

* New `kvitems` method in all backends.
  Like `items`, it takes a prefix,
  and iterates over the key/value pairs of matching objects
  (instead of iterating over objects themselves, like in `items`).
  This is useful for iterating over big objects
  that would otherwise consume too much memory.
* When using python 2, all backends now return
  `map_key` values as `unicode` objects, not `str`
  (until now only the Python backend did so).
  This is what the `json` built-in module does,
  and allows for correctly handling non-ascii key names.
  Comparison between `unicode` and `str` objects is possible,
  so most client code should be unaffected.
* Improving error handling in yajl2 backend (ctypes-based)
  so exceptions caught in callbacks interrupt the parsing process.
* Including more files in source distributions (#14).
* Adjusting python backend to avoid reading off the input stream
  too eagerly (#15).

## [2.5.1]

* Fixing backwards compatibility, allowing
  string readers in all backends (#12, #13).

## [2.5]

* Default backend changed (#5).
  Instead of using the python backend,
  now the fastest available backend is selected by default.
* Added support for new `map_type` option (#7).
* Fixed bug in `multiple_values` support in C backend (#8).
* Added support for ``multiple_values`` flag in python backend (#9).
* Forwarding `**kwargs` from `ijson.items` to `ijson.parse` and
  `ijson.basic_parse` (#10).
* Fixing support for yajl versions < 1.0.12.
* Improving `common.number` implementation.
* Documenting how events and the prefix work (#4).

## [2.4]

- New `ijson.backends.yajl2_c` backend written in C
  and based on the yajl2 library.
  It performs ~10x faster than cffi backend.
- Adding more builds to Travis matrix.
- Preventing memory leaks in `ijson.items`
- Parse numbers consistent with stdlib json
- Correct JSON string parsing in python backend
- Publishing package version in __init__.py
- Various small fixes in cffi backend

[2.4]: https://github.com/ICRAR/ijson/releases/tag/2.4
[2.5]: https://github.com/ICRAR/ijson/releases/tag/v2.5
[2.5.1]: https://github.com/ICRAR/ijson/releases/tag/v2.5.1
[2.6.0]: https://github.com/ICRAR/ijson/releases/tag/v2.6.0
[2.6.1]: https://github.com/ICRAR/ijson/releases/tag/v2.6.1
[3.0rc1]: https://github.com/ICRAR/ijson/releases/tag/v3.0rc1
[3.0rc2]: https://github.com/ICRAR/ijson/releases/tag/v3.0rc2
[3.0rc3]: https://github.com/ICRAR/ijson/releases/tag/v3.0rc3
[3.0]: https://github.com/ICRAR/ijson/releases/tag/v3.0
[3.0.1]: https://github.com/ICRAR/ijson/releases/tag/v3.0.1
[3.0.2]: https://github.com/ICRAR/ijson/releases/tag/v3.0.2
[3.0.3]: https://github.com/ICRAR/ijson/releases/tag/v3.0.3
[3.0.4]: https://github.com/ICRAR/ijson/releases/tag/v3.0.4
