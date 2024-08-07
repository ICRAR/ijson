/*
 * kvitems_async asynchronous iterable implementation for ijson's C backend
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
#include "kvitems_basecoro.h"
#include "common.h"
#include "coro_utils.h"

/**
 * kvitems_async asynchronous iterable object structure
 */
typedef struct {
	PyObject_HEAD
	async_reading_generator *reading_generator;
} KVItemsAsync;

/*
 * __init__, destructor and __anext__
 */
static int kvitemsasync_init(KVItemsAsync *self, PyObject *args, PyObject *kwargs)
{
	PyObject *reading_args = PySequence_GetSlice(args, 0, 2);
	PyObject *kvitems_args = PySequence_GetSlice(args, 2, 4);
	pipeline_node coro_pipeline[] = {
		{&KVItemsBasecoro_Type, kvitems_args, NULL},
		{&ParseBasecoro_Type, NULL, NULL},
		{&BasicParseBasecoro_Type, NULL, kwargs},
		{NULL}
	};
	M1_N(self->reading_generator = (async_reading_generator *)PyObject_CallObject((PyObject *)&AsyncReadingGeneratorType, reading_args));
	async_reading_generator_add_coro(self->reading_generator, coro_pipeline);
	Py_DECREF(kvitems_args);
	Py_DECREF(reading_args);
	return 0;
}

static void kvitemsasync_dealloc(KVItemsAsync *self) {
	Py_XDECREF(self->reading_generator);
	Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject *kvitemsasync_anext(PyObject *self)
{
	KVItemsAsync *gen = (KVItemsAsync *)self;
	Py_INCREF(gen->reading_generator);
	return (PyObject *)gen->reading_generator;
}

static PyAsyncMethods kvitemsasync_methods = {
	.am_await = ijson_return_self,
	.am_aiter = ijson_return_self,
	.am_anext = kvitemsasync_anext
};

PyTypeObject KVItemsAsync_Type = {
	PyVarObject_HEAD_INIT(NULL, 0)
	.tp_basicsize = sizeof(KVItemsAsync),
	.tp_name = "_yajl2._kvitems_async",
	.tp_doc = "Asynchronous iterable yielding key/value pairs",
	.tp_init = (initproc)kvitemsasync_init,
	.tp_dealloc = (destructor)kvitemsasync_dealloc,
	.tp_flags = Py_TPFLAGS_DEFAULT,
	.tp_as_async = &kvitemsasync_methods
};