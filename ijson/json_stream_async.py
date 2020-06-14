import asyncio
import queue

from ijson import basic_parse_coro
from ijson.json_stream import StreamObjectsBase


class AsyncStreamObjects(StreamObjectsBase):
    def __init__(self, stream_object, deep=1):
        super().__init__(stream_object, deep)
        self.q = queue.Queue()

    def send(self, event_value):
        def result_func(result):
            self.q.put(result)

        self._build_dict(event_value, result_func)

    async def run_stream(self):
        def bytesiter(x):
            for b in x:
                yield b.decode('utf8')

        coro = basic_parse_coro(self)
        for datum in bytesiter(self.stream):
            coro.send(datum)
        raise StopAsyncIteration

    def __aiter__(self):
        return self

    async def __anext__(self):
        await asyncio.gather(self.run_stream())

        while True:
            return self.q.get()
