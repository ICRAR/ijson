# -*- coding:utf-8 -*-
from functools import wraps


def coroutine(func):
    '''
    Wraps a generator which is intended to be used as a pure coroutine by
    .send()ing it values. The only thing that the wrapper does is calling
    .next() for the first time which is required by Python generator protocol.
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        g = func(*args, **kwargs)
        next(g)
        return g
    return wrapper


def chain(sink, *coro_pipeline):
    '''
    Chains together a sink and a number of coroutines to form a coroutine
    pipeline. The pipeline works by calling send() on the coroutine created with
    the information in `coro_pipeline[-1]`, which sends its results to the
    coroutine created from `coro_pipeline[-2]`, and so on, until the final
    result is sent to `sink`.
    '''
    f = sink
    for coro_func, coro_args, coro_kwargs in coro_pipeline:
        f = coro_func(f, *coro_args, **coro_kwargs)
    return f


class sendable_list(list):
    '''
    A list that mimics a coroutine receiving values.

    Coroutine are sent values via their send() method. This class defines such a
    method so that values sent into it are appended into the list, which can be
    inspected later. As such, this type can be used as an "accumulating sink" in
    a pipeline consisting on many coroutines.
    '''
    send = list.append


class _StopParsing(Exception):
    """Internal signal that the requested portion of the input is complete."""


@coroutine
def _stop_on_completion(coro):
    """Translate intentional pipeline completion into coroutine exhaustion."""
    try:
        while True:
            try:
                value = yield
            except GeneratorExit:
                coro.close()
                return
            coro.send(value)
    except (StopIteration, _StopParsing):
        return


def coros2gen(source, *coro_pipeline):
    '''
    A utility function that returns a generator yielding values dispatched by a
    coroutine pipeline after *it* has received values coming from `source`.
    '''
    events = sendable_list()
    f = chain(events, *coro_pipeline)
    try:
        for value in source:
            try:
                f.send(value)
            except Exception as ex:
                for event in events:
                    yield event
                if isinstance(ex, (StopIteration, _StopParsing)):
                    return
                raise
            for event in events:
                yield event
            del events[:]
    except GeneratorExit:
        try:
            f.close()
        except:
            pass
