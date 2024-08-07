/*
 * reading_generator_t object and methods implementation for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#include <assert.h>

#include "basic_parse_basecoro.h"
#include "common.h"
#include "reading_generator.h"


int reading_generator_init(reading_generator_t *self, PyObject *args, pipeline_node *coro_pipeline)
{
	PyObject *file;
	Py_ssize_t buf_size = 64 * 1024;
	M1_Z(PyArg_ParseTuple(args, "On", &file, &buf_size));

	// Handle both "read" and "readinto" functions.
	// The latter allocates a bytearray, which is how we distinguish between
	// the two cases later
	if (PyObject_HasAttrString(file, "readinto")) {
		M1_N(self->read_func = PyObject_GetAttrString(file, "readinto"));
		PyObject *pbuf_size = Py_BuildValue("n", buf_size);
		self->buffer = PyObject_CallFunctionObjArgs((PyObject *)&PyByteArray_Type, pbuf_size, NULL);
		M1_N(self->buffer);
		Py_DECREF(pbuf_size);
	}
	else {
		M1_N(self->read_func = PyObject_GetAttrString(file, "read"));
		self->buf_size = PyLong_FromSsize_t(buf_size);
		self->buffer = NULL;
	}

	M1_N(self->events = PyList_New(0));
	self->pos = 0;
	self->finished = 0;

	M1_N(self->coro = chain(self->events, coro_pipeline));
	assert(("reading_generator works only with basic_parse_basecoro",
	        BasicParseBasecoro_Check(self->coro)));
	return 0;
}

void reading_generator_dealloc(reading_generator_t *self)
{
	Py_XDECREF(self->read_func);
	Py_XDECREF(self->events);
	Py_XDECREF(self->buffer);
	Py_XDECREF(self->buf_size);
	Py_XDECREF(self->coro);
}

PyObject *reading_generator_next(reading_generator_t *self)
{
	PyObject *events = self->events;
	Py_ssize_t nevents = PyList_Size(events);
	BasicParseBasecoro *basic_parse_basecoro = (BasicParseBasecoro *)self->coro;
	while (nevents == 0) {

		/* Read data and pass it down to the co-routine */
		Py_buffer view;
		Py_ssize_t length;
		if (self->buffer == NULL) {
			// read_func is "read"
			PyObject *pbuffer = PyObject_CallFunctionObjArgs(self->read_func, self->buf_size, NULL);
			N_N(pbuffer);
			N_M1(PyObject_GetBuffer(pbuffer, &view, PyBUF_SIMPLE));
			length = view.len;
			PyObject *send_res = ijson_yajl_parse(basic_parse_basecoro->h, view.buf, view.len);
			Py_DECREF(pbuffer);
			PyBuffer_Release(&view);
			N_N(send_res);
		}
		else {
			// read_func is "readinto"
			PyObject *plength = PyObject_CallFunctionObjArgs(self->read_func, self->buffer, NULL);
			N_N(plength);
			length = PyLong_AsLong(plength);
			N_M1(length);
			Py_DECREF(plength);
			N_M1(PyObject_GetBuffer(self->buffer, &view, PyBUF_SIMPLE));
			PyObject *send_res = ijson_yajl_parse(basic_parse_basecoro->h, view.buf, length);
			PyBuffer_Release(&view);
			N_N(send_res);
		}
		nevents = PyList_Size(events);

		if (length == 0) {
			break;
		}
	}

	// events are now probably available
	if (nevents > 0) {
		PyObject *val = PyList_GetItem(events, self->pos++);
		Py_INCREF(val);

		/* empty the list if fully iterated over */
		if (self->pos == nevents) {
			self->pos = 0;
			N_M1(PySequence_DelSlice(events, 0, nevents));
		}
		return val;
	}

	// no events, let's end the show
	PyErr_SetNone(PyExc_StopIteration);
	return NULL;
}