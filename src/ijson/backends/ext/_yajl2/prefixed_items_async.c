/*
 * items_async asynchronous iterable implementation for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */


#include "async_reading_generator.h"
#include "basic_parse_basecoro.h"
#include "parse_basecoro.h"
#include "prefixed_items_basecoro.h"
#include "common.h"
#include "coro_utils.h"

/**
 * items_async asynchronous iterable object structure
 */
typedef struct {
	PyObject_HEAD
	async_reading_generator *reading_generator;
} PrefixedItemsAsync;

/*
 * __init__, destructor and __anext__
 */
static int prefixed_itemsasync_init(PrefixedItemsAsync *self, PyObject *args, PyObject *kwargs)
{
	PyObject *reading_args = PySequence_GetSlice(args, 0, 2);
	PyObject *items_args = PySequence_GetSlice(args, 2, 4);
	pipeline_node coro_pipeline[] = {
		{&PrefixedItemsBasecoro_Type, items_args, NULL},
		{&ParseBasecoro_Type, NULL, NULL},
		{&BasicParseBasecoro_Type, NULL, kwargs},
		{NULL}
	};
	M1_N(self->reading_generator = (async_reading_generator *)PyObject_CallObject((PyObject *)&AsyncReadingGeneratorType, reading_args));
	int ret = async_reading_generator_add_coro(self->reading_generator, coro_pipeline);
	Py_DECREF(items_args);
	Py_DECREF(reading_args);
	return ret;
}

static void prefixed_itemsasync_dealloc(PrefixedItemsAsync *self) {
	Py_XDECREF(self->reading_generator);
	Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject *prefixed_itemsasync_anext(PyObject *self)
{
	PrefixedItemsAsync *gen = (PrefixedItemsAsync *)self;
	Py_INCREF(gen->reading_generator);
	return (PyObject *)gen->reading_generator;
}

static PyAsyncMethods prefixed_itemsasync_methods = {
	.am_await = ijson_return_self,
	.am_aiter = ijson_return_self,
	.am_anext = prefixed_itemsasync_anext
};

PyTypeObject PrefixedItemsAsync_Type = {
	PyVarObject_HEAD_INIT(NULL, 0)
	.tp_basicsize = sizeof(PrefixedItemsAsync),
	.tp_name = "_yajl2._prefixed_items_async",
	.tp_doc = "Asynchronous iterable yielding fully-built items",
	.tp_init = (initproc)prefixed_itemsasync_init,
	.tp_dealloc = (destructor)prefixed_itemsasync_dealloc,
	.tp_flags = Py_TPFLAGS_DEFAULT,
	.tp_as_async = &prefixed_itemsasync_methods
};
