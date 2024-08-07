/*
 * parse_async asynchronous iterable implementation for ijson's C backend
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
#include "common.h"
#include "coro_utils.h"

/**
 * parse_async asynchronous iterable object structure
 */
typedef struct {
	PyObject_HEAD
	async_reading_generator *reading_generator;
} ParseAsync;

/*
 * __init__, destructor and __anext__
 */
static int parseasync_init(ParseAsync *self, PyObject *args, PyObject *kwargs)
{
	pipeline_node coro_pipeline[] = {
		{&ParseBasecoro_Type, NULL, NULL},
		{&BasicParseBasecoro_Type, NULL, kwargs},
		{NULL}
	};
	M1_N(self->reading_generator = (async_reading_generator *)PyObject_CallObject((PyObject *)&AsyncReadingGeneratorType, args));
	async_reading_generator_add_coro(self->reading_generator, coro_pipeline);
	return 0;
}

static void parseasync_dealloc(ParseAsync *self) {
	Py_XDECREF(self->reading_generator);
	Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject *parseasync_anext(PyObject *self)
{
	ParseAsync *gen = (ParseAsync *)self;
	Py_INCREF(gen->reading_generator);
	return (PyObject *)gen->reading_generator;
}

static PyAsyncMethods parseasync_methods = {
	.am_await = ijson_return_self,
	.am_aiter = ijson_return_self,
	.am_anext = parseasync_anext
};

PyTypeObject ParseAsync_Type = {
	PyVarObject_HEAD_INIT(NULL, 0)
	.tp_basicsize = sizeof(ParseAsync),
	.tp_name = "_yajl2._parse_async",
	.tp_doc = "Asynchronous iterable yielding (path,evt,value) tuples",
	.tp_init = (initproc)parseasync_init,
	.tp_dealloc = (destructor)parseasync_dealloc,
	.tp_flags = Py_TPFLAGS_DEFAULT,
	.tp_as_async = &parseasync_methods
};