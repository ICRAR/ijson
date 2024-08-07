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
#include "items_basecoro.h"
#include "common.h"
#include "coro_utils.h"

/**
 * items_async asynchronous iterable object structure
 */
typedef struct {
	PyObject_HEAD
	async_reading_generator *reading_generator;
} ItemsAsync;

/*
 * __init__, destructor and __anext__
 */
static int itemsasync_init(ItemsAsync *self, PyObject *args, PyObject *kwargs)
{
	PyObject *reading_args = PySequence_GetSlice(args, 0, 2);
	PyObject *items_args = PySequence_GetSlice(args, 2, 4);
	pipeline_node coro_pipeline[] = {
		{&ItemsBasecoro_Type, items_args, NULL},
		{&ParseBasecoro_Type, NULL, NULL},
		{&BasicParseBasecoro_Type, NULL, kwargs},
		{NULL}
	};
	M1_N(self->reading_generator = (async_reading_generator *)PyObject_CallObject((PyObject *)&AsyncReadingGeneratorType, reading_args));
	async_reading_generator_add_coro(self->reading_generator, coro_pipeline);
	Py_DECREF(items_args);
	Py_DECREF(reading_args);
	return 0;
}

static void itemsasync_dealloc(ItemsAsync *self) {
	Py_XDECREF(self->reading_generator);
	Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject *itemsasync_anext(PyObject *self)
{
	ItemsAsync *gen = (ItemsAsync *)self;
	Py_INCREF(gen->reading_generator);
	return (PyObject *)gen->reading_generator;
}

static PyAsyncMethods itemsasync_methods = {
	.am_await = ijson_return_self,
	.am_aiter = ijson_return_self,
	.am_anext = itemsasync_anext
};

PyTypeObject ItemsAsync_Type = {
	PyVarObject_HEAD_INIT(NULL, 0)
	.tp_basicsize = sizeof(ItemsAsync),
	.tp_name = "_yajl2._items_async",
	.tp_doc = "Asynchronous iterable yielding fully-built items",
	.tp_init = (initproc)itemsasync_init,
	.tp_dealloc = (destructor)itemsasync_dealloc,
	.tp_flags = Py_TPFLAGS_DEFAULT,
	.tp_as_async = &itemsasync_methods
};