import asyncio
from decimal import Decimal
import gc
import types
import weakref

import pytest
from ijson import common

from .support.async_ import AsyncReader


DATA = b'{"first":"value","second":2}'
CASES = [
    ("basic_parse_async", (), [
        ("start_map", None), ("map_key", "first"), ("string", "value"),
        ("map_key", "second"), ("number", 2), ("end_map", None),
    ]),
    ("parse_async", (), [
        ("", "start_map", None), ("", "map_key", "first"),
        ("first", "string", "value"), ("", "map_key", "second"),
        ("second", "number", 2), ("", "end_map", None),
    ]),
    ("items_async", ("",), [{"first": "value", "second": 2}]),
    ("kvitems_async", ("",), [("first", "value"), ("second", 2)]),
]
INVALID_THROW_ARGUMENTS = [(), (42,), (ValueError(), "value"),
                           (ValueError, None, 42), (ValueError, None, None, None)]


class WaitingReader:
    def __init__(self, phase):
        self.phase = phase
        self.waiting = asyncio.Event()
        self.probe_ready = asyncio.Event()
        self.chunks = asyncio.Queue()
        self.cancelled_reads = 0
        if phase == "partial":
            self.chunks.put_nowait(b'{"first":')

    async def read(self, n):
        try:
            if n == 0:
                if self.phase == "probe":
                    self.waiting.set()
                    await self.probe_ready.wait()
                return b""
            if self.chunks.empty():
                self.waiting.set()
            return await self.chunks.get()
        except asyncio.CancelledError:
            self.cancelled_reads += 1
            raise

    def finish(self):
        self.probe_ready.set()
        remaining = DATA[len(b'{"first":'):] if self.phase == "partial" else DATA
        self.chunks.put_nowait(remaining)
        self.chunks.put_nowait(b"")


class GeneratorWaitingReader(WaitingReader):
    @types.coroutine
    def read(self, n):
        return (yield from super().read(n).__await__())


@pytest.mark.parametrize("routine_name,args,expected", CASES)
@pytest.mark.parametrize("phase", ["probe", "empty", "partial"])
@pytest.mark.parametrize("reader_type", [WaitingReader, GeneratorWaitingReader])
def test_async_cancellation(backend, routine_name, args, expected, phase, reader_type):
    async def run():
        reader = reader_type(phase)
        stream = getattr(backend, routine_name)(reader, *args)
        results = []

        async def consume():
            async for value in stream:
                results.append(value)

        task = asyncio.create_task(consume())
        await asyncio.wait_for(reader.waiting.wait(), timeout=5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert reader.cancelled_reads == 1
        reader.finish()
        await asyncio.wait_for(consume(), timeout=5)
        assert results == expected

    asyncio.run(asyncio.wait_for(run(), timeout=10))


def test_async_cancellation_awaits_reader_cleanup(backend):
    async def run():
        cleaning = asyncio.Event()
        released = asyncio.Event()

        class Reader(WaitingReader):
            async def read(self, n):
                try:
                    return await super().read(n)
                except asyncio.CancelledError:
                    cleaning.set()
                    await released.wait()
                    raise

        reader = Reader("empty")
        stream = backend.items_async(reader, "")

        async def read_item():
            return await anext(stream)

        task = asyncio.create_task(read_item())
        try:
            await asyncio.wait_for(reader.waiting.wait(), timeout=5)
            task.cancel()
            await asyncio.wait_for(cleaning.wait(), timeout=5)
            assert not task.done()
            released.set()
            with pytest.raises(asyncio.CancelledError):
                await task
        finally:
            released.set()
            task.cancel()
            await asyncio.wait_for(asyncio.gather(task, return_exceptions=True), timeout=5)
        reader.finish()
        assert await anext(stream) == {"first": "value", "second": 2}
        assert [item async for item in stream] == []

    asyncio.run(asyncio.wait_for(run(), timeout=10))


@pytest.mark.parametrize("delayed", [False, True])
def test_async_reader_handles_cancellation(backend, delayed):
    async def run():
        waiting = asyncio.Event()
        handled = asyncio.Event()
        released = asyncio.Event()

        class Reader:
            returned = False

            async def read(self, n):
                if n == 0 or self.returned:
                    return b""
                waiting.set()
                try:
                    await asyncio.Future()
                except asyncio.CancelledError:
                    handled.set()
                    if delayed:
                        await released.wait()
                    self.returned = True
                    return DATA

        stream = backend.items_async(Reader(), "")

        async def consume():
            return [item async for item in stream]

        task = asyncio.create_task(consume())
        try:
            await asyncio.wait_for(waiting.wait(), timeout=5)
            task.cancel()
            await asyncio.wait_for(handled.wait(), timeout=5)
            if delayed:
                assert not task.done()
                released.set()
            assert await asyncio.wait_for(task, timeout=5) == [{"first": "value", "second": 2}]
        finally:
            released.set()
            task.cancel()
            await asyncio.wait_for(asyncio.gather(task, return_exceptions=True), timeout=5)

    asyncio.run(asyncio.wait_for(run(), timeout=10))


@pytest.mark.parametrize("failure", ["probe", "factory", "immediate", "suspended", "cleanup"])
def test_async_reader_error_can_be_retried(backend, failure):
    async def run():
        waiting = asyncio.Event()
        error = OSError("read failed")

        class Reader:
            failed = False
            returned = False

            def read(self, n):
                if failure == "factory" and n and not self.failed:
                    self.failed = True
                    raise error
                return self.read_async(n)

            async def read_async(self, n):
                if n == 0 and failure == "probe" and not self.failed:
                    self.failed = True
                    raise error
                if n == 0 or self.returned:
                    return b""
                if not self.failed:
                    self.failed = True
                    if failure in ("suspended", "cleanup"):
                        waiting.set()
                        self.pending = asyncio.Future()
                        try:
                            await self.pending
                        except asyncio.CancelledError:
                            raise error
                    raise error
                self.returned = True
                return DATA

        reader = Reader()
        stream = backend.items_async(reader, "")

        async def read_item():
            return await anext(stream)

        task = asyncio.create_task(read_item())
        if failure in ("suspended", "cleanup"):
            await asyncio.wait_for(waiting.wait(), timeout=5)
            if failure == "suspended":
                reader.pending.set_exception(error)
            else:
                task.cancel()
        with pytest.raises(OSError) as raised:
            await task
        assert raised.value is error
        assert await anext(stream) == {"first": "value", "second": 2}
        assert [item async for item in stream] == []

    asyncio.run(asyncio.wait_for(run(), timeout=10))


@pytest.mark.skipif(not hasattr(asyncio, "timeout"), reason="requires asyncio.timeout")
def test_async_cancellation_from_timeout(backend):
    async def run():
        reader = WaitingReader("empty")
        stream = backend.items_async(reader, "")
        initial_cancellations = asyncio.current_task().cancelling()
        with pytest.raises(TimeoutError):
            async with asyncio.timeout(None) as deadline:
                async def expire():
                    await reader.waiting.wait()
                    deadline.reschedule(asyncio.get_running_loop().time())

                expiry = asyncio.create_task(expire())
                await anext(stream)
        await expiry
        assert asyncio.current_task().cancelling() == initial_cancellations
        assert reader.cancelled_reads == 1
        reader.finish()
        assert await anext(stream) == {"first": "value", "second": 2}
        assert [item async for item in stream] == []

    asyncio.run(asyncio.wait_for(run(), timeout=10))


@pytest.mark.parametrize("arguments", INVALID_THROW_ARGUMENTS)
@pytest.mark.filterwarnings("ignore:.*signature of throw.*deprecated:DeprecationWarning")
def test_invalid_throw_preserves_buffered_events(backend, arguments):
    async def run():
        stream = backend.items_async(AsyncReader(b'[1,2,3]'), "item")
        assert await anext(stream) == 1
        operation = anext(stream)
        with pytest.raises(TypeError):
            operation.throw(*arguments)
        assert await operation == 2
        assert await anext(stream) == 3
        assert [item async for item in stream] == []

    asyncio.run(asyncio.wait_for(run(), timeout=10))


def test_throw_preserves_buffered_events_and_exception(backend):
    async def run():
        stream = backend.items_async(AsyncReader(b'[1,2,3]'), "item")
        assert await anext(stream) == 1
        error = ValueError("injected")
        with pytest.raises(ValueError) as raised:
            anext(stream).throw(error)
        assert raised.value is error
        assert [item async for item in stream] == [2, 3]

    asyncio.run(asyncio.wait_for(run(), timeout=10))


@pytest.mark.parametrize("prefix,suffix,expected", [
    (b'[1,"a\\u00', b'62"]', [1, "ab"]),
    (b'[1,"\xf0\x9f', b'\x98\x80"]', [1, "\U0001f600"]),
    (b'[1,1.2', b'e2]', [1, Decimal("120")]),
    (b'[1,"a\\', b'n"]', [1, "a\n"]),
])
def test_async_cancellation_preserves_partial_items(backend, prefix, suffix, expected):
    async def run():
        reader = WaitingReader("empty")
        reader.chunks.put_nowait(prefix)
        stream = backend.items_async(reader, "item")
        results = []

        async def consume():
            async for item in stream:
                results.append(item)

        task = asyncio.create_task(consume())
        await asyncio.wait_for(reader.waiting.wait(), timeout=5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert results == [1]
        reader.chunks.put_nowait(suffix)
        reader.chunks.put_nowait(b"")
        await consume()
        assert results == expected

    asyncio.run(asyncio.wait_for(run(), timeout=10))


@pytest.mark.parametrize("phase", ["probe", "empty"])
def test_async_cancellation_with_text_reader(backend, phase):
    async def run():
        class TextReader(WaitingReader):
            async def read(self, n):
                return (await super().read(n)).decode()

        reader = TextReader(phase)
        stream = backend.items_async(reader, "")

        async def read_item():
            return await anext(stream)

        task = asyncio.create_task(read_item())
        await asyncio.wait_for(reader.waiting.wait(), timeout=5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert reader.cancelled_reads == 1
        reader.finish()
        assert await anext(stream) == {"first": "value", "second": 2}
        assert [item async for item in stream] == []

    with pytest.deprecated_call():
        asyncio.run(asyncio.wait_for(run(), timeout=10))


@pytest.mark.parametrize("mode", ["missing", "lookup", "method"])
def test_async_cancellation_custom_await_iterator(backend, mode):
    async def run():
        waiting = asyncio.Event()
        error = OSError("custom throw failed")

        class AwaitIterator:
            def __init__(self):
                self.inner = iter(asyncio.Future().__await__())

            def __iter__(self):
                return self

            def __next__(self):
                waiting.set()
                return next(self.inner)

            def __getattr__(self, name):
                if name != "throw" or mode == "missing":
                    raise AttributeError(name)
                if mode == "lookup":
                    raise error

                def throw(*args):
                    raise error

                return throw

        class Awaitable:
            def __await__(self):
                return AwaitIterator()

        class Reader:
            failed = False
            returned = False

            def read(self, n):
                async def complete(value):
                    return value

                if n == 0 or self.returned:
                    return complete(b"")
                if not self.failed:
                    self.failed = True
                    return Awaitable()
                self.returned = True
                return complete(DATA)

        stream = backend.items_async(Reader(), "")

        async def read_item():
            return await anext(stream)

        task = asyncio.create_task(read_item())
        await asyncio.wait_for(waiting.wait(), timeout=5)
        task.cancel()
        exception = asyncio.CancelledError if mode == "missing" else OSError
        with pytest.raises(exception) as raised:
            await task
        if mode != "missing":
            assert raised.value is error
        assert await anext(stream) == {"first": "value", "second": 2}
        assert [item async for item in stream] == []

    asyncio.run(asyncio.wait_for(run(), timeout=10))


@pytest.mark.parametrize("iterator", [False, True])
def test_invalid_async_read_result(backend, iterator):
    class EmptyAwaitable:
        def __await__(self):
            return iter(())

    class Reader:
        returned = False

        def read(self, n):
            async def complete(value):
                return value

            if n == 0:
                return complete(b"")
            if not self.returned:
                self.returned = True
                return complete(DATA)
            return EmptyAwaitable() if iterator else complete(None)

    async def run():
        stream = backend.items_async(Reader(), "")
        assert await anext(stream) == {"first": "value", "second": 2}
        with pytest.raises(TypeError):
            await anext(stream)

    asyncio.run(asyncio.wait_for(run(), timeout=10))


def test_repeated_async_cancellation(backend):
    async def run():
        reader = WaitingReader("empty")
        stream = backend.items_async(reader, "")

        async def read_item():
            return await anext(stream)

        async def cancel_and_get_arguments(reader, coroutine, message):
            reader.waiting.clear()
            task = asyncio.create_task(coroutine)
            await asyncio.wait_for(reader.waiting.wait(), timeout=5)
            task.cancel(message)
            with pytest.raises(asyncio.CancelledError) as raised:
                await task
            return raised.value.args

        control = WaitingReader("empty")
        for i in range(5):
            message = "cancel " + str(i)
            expected = await cancel_and_get_arguments(control, control.read(1), message)
            actual = await cancel_and_get_arguments(reader, read_item(), message)
            assert actual == expected
            assert reader.cancelled_reads == i + 1
        reader.finish()
        assert await anext(stream) == {"first": "value", "second": 2}
        assert [item async for item in stream] == []

    asyncio.run(asyncio.wait_for(run(), timeout=10))


@pytest.mark.parametrize("form", ["instance", "class", "value", "traceback"])
@pytest.mark.filterwarnings("ignore:.*signature of throw.*deprecated:DeprecationWarning")
def test_throw_exception_arguments(backend, form):
    async def run():
        stream = backend.items_async(AsyncReader(DATA), "")
        error = ValueError("injected")
        try:
            raise error
        except ValueError:
            traceback = error.__traceback__
        arguments = {
            "instance": (error,), "class": (ValueError,),
            "value": (ValueError, error), "traceback": (ValueError, error, traceback),
        }[form]
        with pytest.raises(ValueError) as raised:
            anext(stream).throw(*arguments)
        if form == "class":
            assert raised.value.args == ()
        else:
            assert raised.value is error
            if form in ("instance", "traceback"):
                current = raised.value.__traceback__
                while current is not None and current is not traceback:
                    current = current.tb_next
                assert current is traceback
        assert [item async for item in stream] == [{"first": "value", "second": 2}]

    asyncio.run(asyncio.wait_for(run(), timeout=10))


class RecordingReader:
    def __init__(self):
        self.arguments = None
        self.waiting = False
        self.returned = False
        self.read_calls = 0

    def read(self, n):
        async def complete():
            return b""

        if n == 0 or self.returned:
            return complete()
        self.read_calls += 1
        return RecordingRead(self)


class RecordingRead:
    def __init__(self, reader):
        self.reader = reader

    def __iter__(self):
        return self

    __await__ = __iter__

    def __next__(self):
        self.reader.waiting = True
        return None

    def throw(self, *arguments):
        self.reader.arguments = arguments
        self.reader.returned = True
        raise StopIteration(DATA)


def pending_recording_read(backend, reader):
    stream = backend.items_async(reader, "")
    operation = anext(stream).__await__()
    for _ in range(3):
        next(operation)
        if reader.waiting:
            return stream, operation
    pytest.fail("read did not suspend")


@pytest.mark.parametrize("form", ["instance", "class", "value", "traceback",
                                 "class_none", "class_none_none", "instance_none",
                                 "instance_none_none"])
@pytest.mark.filterwarnings("ignore:.*signature of throw.*deprecated:DeprecationWarning")
def test_throw_forwards_original_arguments_to_active_read(backend, form):
    async def run():
        reader = RecordingReader()
        stream, operation = pending_recording_read(backend, reader)
        error = ValueError("injected")
        try:
            raise error
        except ValueError:
            traceback = error.__traceback__
        arguments = {
            "instance": (error,), "class": (ValueError,),
            "value": (ValueError, error), "traceback": (ValueError, error, traceback),
            "class_none": (ValueError, None), "class_none_none": (ValueError, None, None),
            "instance_none": (error, None), "instance_none_none": (error, None, None),
        }[form]
        with pytest.raises(StopIteration) as raised:
            operation.throw(*arguments)
        assert raised.value.value == {"first": "value", "second": 2}
        assert len(reader.arguments) == len(arguments)
        assert all(actual is expected for actual, expected in zip(reader.arguments, arguments))
        assert [item async for item in stream] == []

    asyncio.run(asyncio.wait_for(run(), timeout=10))


def test_invalid_throw_preserves_active_c_read(backend):
    if backend.backend_name != "yajl2_c":
        pytest.skip("checks the shared C await iterator's validation")

    async def run():
        reader = RecordingReader()
        stream, operation = pending_recording_read(backend, reader)
        for arguments in INVALID_THROW_ARGUMENTS:
            with pytest.raises(TypeError):
                operation.throw(*arguments)
            assert reader.arguments is None
            assert next(operation) is None
            assert reader.read_calls == 1
        with pytest.raises(StopIteration) as raised:
            operation.throw(ValueError("handled"))
        assert raised.value.value == {"first": "value", "second": 2}
        assert [item async for item in stream] == []

    asyncio.run(asyncio.wait_for(run(), timeout=10))


@pytest.mark.parametrize("cancelled", [False, True])
def test_async_parse_failure_releases_buffer_view(backend, cancelled):
    async def run():
        buffer = bytearray(b'{"broken":}')
        waiting = asyncio.Event()

        class Reader:
            async def read(self, n):
                if n == 0:
                    return b""
                if cancelled:
                    waiting.set()
                    try:
                        await asyncio.Future()
                    except asyncio.CancelledError:
                        pass
                return buffer

        stream = backend.items_async(Reader(), "")

        async def read_item():
            return await anext(stream)

        task = asyncio.create_task(read_item())
        if cancelled:
            await asyncio.wait_for(waiting.wait(), timeout=5)
            task.cancel()
        with pytest.raises(common.JSONError):
            await task
        buffer.extend(b" ")

    asyncio.run(asyncio.wait_for(run(), timeout=10))


@pytest.mark.parametrize("reader_type", [WaitingReader, GeneratorWaitingReader])
def test_async_cancellation_releases_ended_read(backend, reader_type):
    async def run():
        references = []

        class Reader(reader_type):
            def read(self, n):
                coroutine = super().read(n)
                references.append(weakref.ref(coroutine))
                return coroutine

        reader = Reader("empty")
        stream = backend.items_async(reader, "")

        async def cancel_read():
            async def read_item():
                return await anext(stream)

            task = asyncio.create_task(read_item())
            await asyncio.wait_for(reader.waiting.wait(), timeout=5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        await cancel_read()
        gc.collect()
        assert all(reference() is None for reference in references)
        reader.finish()
        assert await anext(stream) == {"first": "value", "second": 2}
        assert [item async for item in stream] == []

    asyncio.run(asyncio.wait_for(run(), timeout=10))
