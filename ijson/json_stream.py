# -*- coding:utf-8 -*-

from ijson import basic_parse
from ijson.common import ObjectBuilder
from ijson.constants import END_ARRAY, END_MAP, MAP_KEY, START_ARRAY, START_MAP


class StreamObjectsBase(object):
    def __init__(self, stream_object, deep=1):
        self.stream = stream_object
        self.builder = ObjectBuilder()
        self.current_deep = 0
        self.keys = []
        self.deep = deep

    def _build_dict(self, event_value, result_func):
        event, value = event_value
        if event in [START_MAP, START_ARRAY]:
            self.current_deep += 1
            if self.current_deep <= self.deep:
                return

        elif event == MAP_KEY:
            if self.current_deep <= self.deep:
                len_keys = len(self.keys)
                if len_keys > self.current_deep:
                    self.keys = [value]
                elif len_keys == self.current_deep:
                    self.keys[self.current_deep - 1] = value
                else:
                    self.keys.append(value)
                return

        elif event in [END_MAP, END_ARRAY]:
            self.current_deep -= 1
            if self.current_deep == self.deep:
                result_func((self.keys, self.builder.value))

                def initial_set(v):
                    self.builder.value = v

                self.builder.value = {}
                self.builder.containers = [initial_set]
                return
            elif not self.builder.value:
                return

        self.builder.event(event, value)


class StreamObjects(StreamObjectsBase):
    def __init__(self, stream_object, deep=1):
        super(StreamObjects, self).__init__(stream_object, deep)
        self.stream = basic_parse(self.stream)

    def _build(self):
        self.result = None

        def result_func(res):
            self.result = res

        for event, value in self.stream:
            self._build_dict((event, value), result_func)
            if self.result:
                break

        if not self.result:
            raise StopIteration
        return self.result

    def __iter__(self):
        return self

    # Python 3 compatibility
    def __next__(self):
        return self.next()

    def next(self):
        return self._build()
