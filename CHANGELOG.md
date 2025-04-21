# Changelog

## Development

* Introdued `tox` for common task execution.

## [3.4.0]

* Added support for PEP 489 multi-phase initialisation
  and per-module state for our C extension,
  allowing us to support sub-interpreters with per-interpreter GIL.
* Advertise support for free-threading python mode.
* Removed support for Python < 3.9.
* Enhanced generators so they yield all possible results to users
  before errors are raised (#123).
* Added `ijson.ALL_BACKENDS` constant
  listing all supported backends
  (which might or not be available at runtime).
* Added a `capabilities` constant to each backend
  describing which capabilities it supports.
* Exposing backend's name under ``<backend>.backend_name``,
  and default backend's name under ``ijson.backend_name``.
  This is similar to the already existing ``name`` constant,
  only slightly better named to hopefully avoid confusion.
* Restructured source code so all code lives under `src/`,
  and the `ijson.backends._yajl2` extension under `src/ijson/backends/ext/_yajl2`.
  This allows C backend tests to actually run on cibuildwheel.
* Improved performance of `parse` routine in C backend by ~4%.
* Fixed several potential stability issues in C backend
  around correct error handling.
* Fixed corner-case wrong behaviour of `yajl2_c` backend,
  which didn't work correctly with user-provided event names.
* Pointing to our own fork of yajl (for when we build it ourselves)
  that contains fixes for all known CVEs (#126).
* Removed leftover compatibility bits in the C backend.
* Fixed potential issue with `yajl` and `yajl2` backends
  where crashes could occur at interpreter shutdown.
* Removed tox.
* Moved static project metadata to `pyproject.toml`.

## [3.3.0]

* Removed support for Python 2.7 and 3.4,
  3.5+ is still supported.
* Distribute the existing `benchmark.py` script
  as ``ijson.benchmark``.
  The module is an improved version of the script,
  supporting #iterations for a given function invocation,
  multiple input files,
  and more.

## [3.2.3]

* Fixed several issues in the ``yajl2_c`` backend
  and its async generators
  that were only made apparent
  when running it with PyPy
  and/or a CPython debug build (#101).
  As part of that,
  an issue was found and fixed in PyPy itself
  affecting all versions up to 7.3.12,
  so users will need to wait until the next version is released
  to be able to use async generators
  (https://foss.heptapod.net/pypy/pypy/-/issues/3956).
* Adapted ``yajl2_c`` async generators
  to work against PyPy shortcomings
  (https://foss.heptapod.net/pypy/pypy/-/issues/3965).

## [3.2.2]

* Fixed compilation and ``async`` support
  of the ``yajl2_c`` backend in pyhthon 3.12 (#98).
* Check ``IJSON_BUILD_YAJL2C`` environment variable
  when building ijson
  to force/skip building the ``yajl2_c`` backend (#102).

## [3.2.1]

* Added support for Python 3.12.
* Fixed a memory leak in the ``yajl2_c`` backend
  triggered only when the underlying ``yajl`` functions
  reported a failure (#97).

## [3.2.0.post0]

* Fixed minor README rendering issues
  that prevented upload of 3.2.0 distributions
  to PyPI.

## [3.2.0]

* New ``ijson.dump`` command-line utility
  for simple inspection of the ijson iteration process.
  This tool should be useful for new users
  who are usually confused with how to use the library,
  and the prefix in particular.
* Fixed bug in ``yajl2_c`` backend introduced in 3.1.2
  where random crashes could occur
  due to an unsafe reference decrement
  when constructing the parse/items/kvitems generators (#66).
* Mark Python 3.10 and 3.11 as explicitly supported.

## [3.1.4]

* Fixed bug in ``yajl2_c`` backend introduced in 3.1.0
  where ``ijson.items`` didn't work correctly
  against member names containing ``.`` (#41).
* Python backend raises errors on incomplete JSON content
  that previously wasn't recognised as such,
  aligning itself with the rest of the backends (#42).

## [3.1.3]

* Python backed correctly raises errors
  when JSON numbers with leading zeros
  are found in the stream (#40).
* Likewise, JSON numbers with fractions
  where the decimal point is not surrounded
  by at least one digit on both sides
  also produce an error now
  on the python backend.
* Fixed detection of file objects
  with generator-based ``read`` coroutines
  (i.e., a ``read`` generator decorated with ``@types.coroutine``)
  for the purpose of automatically routing user calls
  done through the main entry points.
  For example, when using ``aiofiles`` objects
  users could invoke ``async for item in ijson.parse_async(f)``
  but not ``async for item in ijson.parse(f)``,
  while the latter has been possible since 3.1
  for native coroutines.

## [3.1.2.post0]

* Moved binary wheel generation
  from GitHub Actions to Travis.
  This gained us binary ARM wheels,
  which are becoming increasingly popular (#35)

## [3.1.2]

* Fixed minor memory leaks
  in the initialization methods
  of the generators of the ``yajl2_c`` backend.
  All generators
  (i.e., ``basic_parse``, ``parse``, ``kvitems`` and ``items``)
  in both their sync and async versions,
  were affected.

## [3.1.1]

* Fixed two problems in the ``yajl2_c`` backend
  related to `asyncio` support,
  which prevented some objects
  like those from ``aiofiles``
  from working properly (#32).
* Ironing out and documenting some corner cases
  related to the use of ``use_float=True``
  and its side-effect on integer number parsing.

## [3.1.post0]

* Removed ``test`` package from binary distributions.

## [3.1]

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
* Improved the performance
  of the ``items`` and ``kvitems`` methods
  of the ``yajl2_c`` backend
  (by internally avoiding unnecessary string concatenations).
  Local tests show a performance improvement of up to ~15%,
  but mileage might vary depending on your use case and system.
* The "raw" functions ``basic_parse``, ``parse``, ``items`` and ``kvitems``
  can now be used with different types of inputs.
  In particular they accept not only file-like objects,
  but also asynchronous file-like objects,
  behaving like their ``*_async`` counterparts.
  They also accept ``bytes`` and ``str`` objects directly
  (and ``unicode`` objects in python 2.7).
  Finally, they also accept iterables,
  in which case they behave like the ``ijson.common.*`` functions,
  allowing users to tap into the event pipeline.
* ``ijson.common`` routines ``parse``, ``items`` and ``kvitems``
  are marked as deprecated.
  Users should use the ``ijson.*`` routines instead,
  which now accept event iterables.
* New ``ijson.get_backend`` function
  for users to import a backend programmatically
  (without having to manually use importlib).
* New ``IJSON_BACKEND`` environment variable
  can be used to choose the default backend to be exposed by ijson.
* Unicode decoding errors are now reported
  more clearly to users.
  In the past there was a mix
  of empty messages and error types.
  Now the error type is always the same
  and there should always be an error messages
  indicating the offending byte sequence.
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
  They were accidentally removed in the redesign of ijson 3.0,
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
[3.1]: https://github.com/ICRAR/ijson/releases/tag/v3.1
[3.1.post0]: https://github.com/ICRAR/ijson/releases/tag/v3.1.post0
[3.1.1]: https://github.com/ICRAR/ijson/releases/tag/v3.1.1
[3.1.2]: https://github.com/ICRAR/ijson/releases/tag/v3.1.2
[3.1.2.post0]: https://github.com/ICRAR/ijson/releases/tag/v3.1.2.post0
[3.1.3]: https://github.com/ICRAR/ijson/releases/tag/v3.1.3
[3.1.4]: https://github.com/ICRAR/ijson/releases/tag/v3.1.4
[3.2.0]: https://github.com/ICRAR/ijson/releases/tag/v3.2.0
[3.2.0.post0]: https://github.com/ICRAR/ijson/releases/tag/v3.2.0.post0
[3.2.1]: https://github.com/ICRAR/ijson/releases/tag/v3.2.1
[3.2.2]: https://github.com/ICRAR/ijson/releases/tag/v3.2.2
[3.2.3]: https://github.com/ICRAR/ijson/releases/tag/v3.2.3
[3.3.0]: https://github.com/ICRAR/ijson/releases/tag/v3.3.0
[3.4.0]: https://github.com/ICRAR/ijson/releases/tag/v3.4.0
