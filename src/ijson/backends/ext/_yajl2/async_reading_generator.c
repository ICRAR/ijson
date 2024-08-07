/*
 * asynchronous reading generator implementation for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */


#include <assert.h>

#include "async_reading_generator.h"
#include "basic_parse_basecoro.h"
#include "common.h"

static int async_reading_generator_init(async_reading_generator *self, PyObject *args, PyObject *kwargs)
{
	self->coro = NULL;
	self->file = NULL;
	self->read_func = NULL;
	self->buf_size = NULL;
	self->awaitable = NULL;
	self->events = NULL;
	self->index = 0;
	self->file_exhausted = 0;

	M1_Z(PyArg_ParseTuple(args, "OO", &self->file, &self->buf_size));
	M1_Z(PyNumber_Check(self->buf_size));

	Py_INCREF(self->file);
	Py_INCREF(self->buf_size);
	M1_N(self->events = PyList_New(0));
	return 0;
}

void async_reading_generator_add_coro(async_reading_generator *self, pipeline_node *coro_pipeline)
{
	self->coro = chain(self->events, coro_pipeline);
	assert(("async_reading_generator works only with basic_parse_basecoro",
		        BasicParseBasecoro_Check(self->coro)));
}

static void async_reading_generator_dealloc(async_reading_generator *self)
{
	Py_XDECREF(self->events);
	Py_XDECREF(self->awaitable);
	Py_XDECREF(self->buf_size);
	Py_XDECREF(self->read_func);
	Py_XDECREF(self->file);
	Py_XDECREF(self->coro);
	Py_TYPE(self)->tp_free((PyObject*)self);
}

static void raise_stopiteration(PyObject *value)
{
#if defined(PYPY_VERSION)
	// PyPy doesn't seem to support normalised exceptions for coroutines,
	// see https://foss.heptapod.net/pypy/pypy/-/issues/3965
	PyObject *ex_value = PyObject_CallFunctionObjArgs(PyExc_StopIteration, value, NULL);
	PyErr_SetObject(PyExc_StopIteration, ex_value);
	Py_DECREF(ex_value);
#else
	PyObject *stop_iteration_args = PyTuple_New(1);
	PyTuple_SET_ITEM(stop_iteration_args, 0, value);
	PyErr_SetObject(PyExc_StopIteration, stop_iteration_args);
	Py_DECREF(stop_iteration_args);
#endif
}

static PyObject *maybe_pop_event(async_reading_generator *self)
{
	PyObject *events = self->events;
	Py_ssize_t nevents = PyList_Size(events);
	if (nevents == 0) {
		return NULL;
	}
	PyObject *event = PyList_GET_ITEM(events, self->index++);
	Py_INCREF(event);
	if (self->index == nevents) {
		if (PySequence_DelSlice(events, 0, self->index) == -1) {
			Py_RETURN_NONE;
		}
		self->index = 0;
	}
	raise_stopiteration(event);
	return event;
}

static int is_gen_coroutine(PyObject *o)
{
	if (PyGen_CheckExact(o)) {
		PyCodeObject *code = (PyCodeObject *)PyObject_GetAttrString(o, "gi_code");
		return code->co_flags & CO_ITERABLE_COROUTINE;
	}
	return 0;
}

static PyObject* value_from_stopiteration()
{
	PyObject *ptype, *pvalue, *ptraceback, *return_value;
	PyErr_Fetch(&ptype, &pvalue, &ptraceback);
	if (PyErr_GivenExceptionMatches(pvalue, PyExc_StopIteration)) {
		return_value = PyObject_GetAttrString(pvalue, "value");
		Py_XDECREF(pvalue);
	}
	else {
		return_value = pvalue;
	}
	Py_XDECREF(ptype);
	Py_XDECREF(ptraceback);
	return return_value;
}

static PyObject *async_reading_generator_next(PyObject *self)
{
	async_reading_generator *gen = (async_reading_generator *)self;

	// values are returned via StopIteration exception values
	if (maybe_pop_event(gen)) {
		return NULL;
	}
	// No events available and nothing else to read, we are done
	if (gen->file_exhausted) {
		PyErr_SetNone(PyExc_StopAsyncIteration);
		return NULL;
	}

	// prepare corresponding awaitable
	if (gen->awaitable == NULL) {
		if (gen->read_func == NULL) {
			PyObject *utils35, *get_read_func, *get_read_coro;
			N_N(utils35 = PyImport_ImportModule("ijson.utils35"));
			N_N(get_read_func = PyObject_GetAttrString(utils35, "_get_read"));
			N_N(get_read_coro = PyObject_CallFunctionObjArgs(get_read_func, gen->file, NULL));
			N_N(gen->awaitable = PyObject_CallMethod(get_read_coro, "__await__", NULL));
			assert(PyIter_Check(gen->awaitable));
			Py_DECREF(get_read_coro);
			Py_DECREF(get_read_func);
			Py_DECREF(utils35);
			Py_CLEAR(gen->file);
		}
		else {
			PyObject *read_coro;
			N_N(read_coro = PyObject_CallFunctionObjArgs(gen->read_func, gen->buf_size, NULL));
			// this can be a "normal" awaitable (has an __await__ method)
			// or a function decorated with types.coroutine (a generator)
			if (is_gen_coroutine(read_coro)) {
				gen->awaitable = read_coro;
				Py_INCREF(gen->awaitable);
			}
			else {
				N_N(gen->awaitable = PyObject_CallMethod(read_coro, "__await__", NULL));
			}
			assert(PyIter_Check(gen->awaitable));
			Py_DECREF(read_coro);
		}
	}

	// Propagate values/errors that are not StopIteration
	PyObject *value = Py_TYPE(gen->awaitable)->tp_iternext(gen->awaitable);
	if (value) {
		return value;
	}
	else if (!PyErr_ExceptionMatches(PyExc_StopIteration)) {
		return NULL;
	}
	Py_CLEAR(gen->awaitable);

	// We await on two things: getting the correct read function (only once),
	// and reading from it (many times, self->read_func is set)
	if (gen->read_func == NULL) {
		gen->read_func = value_from_stopiteration();
		Py_RETURN_NONE;
	}

	// Finished awaiting on read() result, parse it
	PyObject *buffer = value_from_stopiteration();

	Py_buffer view;
	N_M1(PyObject_GetBuffer(buffer, &view, PyBUF_SIMPLE));
	gen->file_exhausted = (view.len == 0);
	BasicParseBasecoro *basic_parse_basecoro = (BasicParseBasecoro *)gen->coro;
	PyObject *res = ijson_yajl_parse(basic_parse_basecoro->h, view.buf, view.len);
	N_N(res);
	Py_DECREF(res);

	PyBuffer_Release(&view);
	Py_DECREF(buffer);

	// values are returned via StopIteration exception values
	if (maybe_pop_event(gen)) {
		return NULL;
	}

	// Keep trying
	Py_RETURN_NONE;
}

static PyAsyncMethods async_reading_generator_methods = {
	.am_await = ijson_return_self,
};

PyTypeObject AsyncReadingGeneratorType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	.tp_basicsize = sizeof(async_reading_generator),
	.tp_name = "_yajl2.async_reading_generator",
	.tp_doc = "The awaitable yielded by the asynchronous iterables",
	.tp_init = (initproc)async_reading_generator_init,
	.tp_dealloc = (destructor)async_reading_generator_dealloc,
	.tp_flags = Py_TPFLAGS_DEFAULT,
	.tp_as_async = &async_reading_generator_methods,
	.tp_iter = ijson_return_self,
	.tp_iternext = async_reading_generator_next,
};