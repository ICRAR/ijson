/*
 * basic_parse_basecoro coroutine implementation for ijson's C backend
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
#include "parse_basecoro.h"


/*
 * The YAJL callbacks, they add (evt,value) to a list
 */
static inline
int add_event_and_value(void *ctx, PyObject *evt_name, PyObject *val) {
	PyObject *target_send = (PyObject *)ctx;
	if (ParseBasecoro_Check(target_send)) {
		Z_N(parse_basecoro_send_impl(target_send, evt_name, val));
		Py_DECREF(val);
		return 1;
	}
	PyObject *tuple;
	Z_N(tuple = PyTuple_New(2));
	Py_INCREF(evt_name); // this is an element of our static enames var
	PyTuple_SET_ITEM(tuple, 0, evt_name);
	PyTuple_SET_ITEM(tuple, 1, val);
	CORO_SEND(target_send, tuple);
	Py_DECREF(tuple);
	return 1;
}

static int null(void * ctx) {
	Py_INCREF(Py_None);
	return add_event_and_value(ctx, enames.null_ename, Py_None);
}

static int boolean(void * ctx, int val) {
	PyObject *bval = val == 0 ? Py_False : Py_True;
	Py_INCREF(bval);
	return add_event_and_value(ctx, enames.boolean_ename, bval);
}

static int yajl_integer(void *ctx, long long val)
{
	PyObject *ival;
#if PY_MAJOR_VERSION < 3
	if (val <= 0xFFFFFFFF) {
		Z_N(ival = PyInt_FromLong((long)val));
	}
	else
#endif
	{
		Z_N(ival = PyLong_FromLongLong(val))
	}
	return add_event_and_value(ctx, enames.number_ename, ival);
}

static int yajl_double(void *ctx, double val)
{
	PyObject *dval;
	Z_N(dval = PyFloat_FromDouble(val))
	return add_event_and_value(ctx, enames.number_ename, dval);
}

static int number(void * ctx, const char *numberVal, size_t numberLen) {

	// If original string has a dot or an "e/E" we return a Decimal
	// just like in the common module
	int is_decimal = 0;
	const char *iter = numberVal;
	size_t i;
	for(i=0; i!=numberLen; i++) {
		char c = *iter++;
		if( c == '.' || c == 'e' || c == 'E' ) {
			is_decimal = 1;
			break;
		}
	}

	PyObject *val;
	if( !is_decimal ) {
		char *nval = (char *)malloc(numberLen + 1);
		memcpy(nval, numberVal, numberLen);
		nval[numberLen] = 0;
		char *endptr;
#if PY_MAJOR_VERSION >= 3
		val = PyLong_FromString(nval, &endptr, 10);
#else
		// returns either PyLong or PyInt
		val = PyInt_FromString(nval, &endptr, 10);
#endif
		free(nval);
		assert(("string provided by yajl is not an integer",
		        val != NULL && endptr != nval));
	}
	else {
		Z_N(val = PyObject_CallFunction(Decimal, "s#", numberVal, numberLen));
	}

	return add_event_and_value(ctx, enames.number_ename, val);
}

static int string_cb(void * ctx, const unsigned char *stringVal, size_t stringLen) {
	PyObject *val;
	Z_N(val = PyUnicode_FromStringAndSize((char *)stringVal, stringLen))
	return add_event_and_value(ctx, enames.string_ename, val);
}

static int start_map(void *ctx) {
	Py_INCREF(Py_None);
	return add_event_and_value(ctx, enames.start_map_ename, Py_None);
}

static int map_key(void *ctx, const unsigned char *key, size_t stringLen) {
	PyObject *val;
	Z_N(val = STRING_FROM_UTF8(key, stringLen))
	return add_event_and_value(ctx, enames.map_key_ename, val);
}

static int end_map(void *ctx) {
	Py_INCREF(Py_None);
	return add_event_and_value(ctx, enames.end_map_ename, Py_None);
}

static int start_array(void *ctx) {
	Py_INCREF(Py_None);
	return add_event_and_value(ctx, enames.start_array_ename, Py_None);
}

static int end_array(void *ctx) {
	Py_INCREF(Py_None);
	return add_event_and_value(ctx, enames.end_array_ename, Py_None);
}

static yajl_callbacks decimal_callbacks = {
	null, boolean, NULL, NULL, number, string_cb,
	start_map, map_key, end_map, start_array, end_array
};

static yajl_callbacks float_callbacks = {
	null, boolean, yajl_integer, yajl_double, NULL, string_cb,
	start_map, map_key, end_map, start_array, end_array
};


PyObject* ijson_yajl_parse(yajl_handle handle, char *buffer, size_t length)
{
	yajl_status status;
	if (length == 0) {
		status = yajl_complete_parse(handle);
	}
	else {
		status = yajl_parse(handle, (unsigned char *)buffer, length);
	}
	if (status != yajl_status_ok) {
		// An actual problem with the JSON data (otherwise a user error)
		if (status != yajl_status_client_canceled) {
			unsigned char *perror = yajl_get_error(handle, 1, (unsigned char *)buffer, length);
			PyErr_SetString(IncompleteJSONError, (char *)perror);
			yajl_free_error(handle, perror);
		}
		return NULL;
	}

	Py_RETURN_NONE;
}


/*
 * __init__, destructor, __iter__ and __next__
 */
static int basic_parse_basecoro_init(BasicParseBasecoro *self, PyObject *args, PyObject *kwargs)
{
	PyObject *allow_comments = Py_False;
	PyObject *multiple_values = Py_False;
	PyObject *use_float = Py_False;

	self->h = NULL;
	self->target_send = NULL;

	char *kwlist[] = {"target_send", "allow_comments", "multiple_values",
	                  "use_float", NULL};
	if( !PyArg_ParseTupleAndKeywords(args, kwargs, "O|OOO", kwlist,
	                                 &self->target_send, &allow_comments,
	                                 &multiple_values, &use_float) ) {
		return -1;
	}
	Py_INCREF(self->target_send);

	/*
	 * Prepare yajl handle and configure it
	 * The context given to yajl is the coroutine's target, so the callbacks
	 * directly send values to the target
	 */
	yajl_callbacks *callbacks;
	if (PyObject_IsTrue(use_float)) {
		callbacks = &float_callbacks;
	}
	else {
		callbacks = &decimal_callbacks;
	}
	M1_N(self->h = yajl_alloc(callbacks, NULL, (void *)self->target_send));
	if (PyObject_IsTrue(allow_comments)) {
		yajl_config(self->h, yajl_allow_comments, 1);
	}
	if (PyObject_IsTrue(multiple_values)) {
		yajl_config(self->h, yajl_allow_multiple_values, 1);
	}

	return 0;
}

static void basic_parse_basecoro_dealloc(BasicParseBasecoro *self)
{
	if (self->h) {
		yajl_free(self->h);
	}
	Py_XDECREF(self->target_send);
	Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject* basic_parse_basecoro_send(PyObject *self, PyObject *arg)
{
	/* Preempt our execution, which might be very long */
//	N_M1(PyErr_CheckSignals());

	Py_buffer bufview;
	N_M1(PyObject_GetBuffer(arg, &bufview, PyBUF_SIMPLE));
	BasicParseBasecoro *gen = (BasicParseBasecoro *)self;
	PyObject *ret = ijson_yajl_parse(gen->h, bufview.buf, bufview.len);
	if (ret != NULL && bufview.len == 0) {
		// This was the last one, let's end now
		PyErr_SetNone(PyExc_StopIteration);
		ret = NULL;
	}
	PyBuffer_Release(&bufview);
	return ret;
}

static PyObject* basic_parse_basecoro_close(PyObject *self, PyObject *args)
{
	BasicParseBasecoro *gen = (BasicParseBasecoro *)self;
	N_N(ijson_yajl_parse(gen->h, NULL, 0));
	Py_RETURN_NONE;
}

static PyMethodDef basic_parse_basecoro_methods[] = {
	{"send", basic_parse_basecoro_send, METH_O, "coroutine's send method"},
	{"close", basic_parse_basecoro_close, METH_NOARGS, "coroutine's close method"},
	{NULL, NULL, 0, NULL}
};

PyTypeObject BasicParseBasecoro_Type = {
#if PY_MAJOR_VERSION >= 3
	PyVarObject_HEAD_INIT(NULL, 0)
#else
	PyObject_HEAD_INIT(NULL)
#endif
	.tp_basicsize = sizeof(BasicParseBasecoro),
	.tp_name = "_yajl2.basic_parse_basecoro",
	.tp_doc = "Coroutine dispatching (evt,value) pairs",
	.tp_init = (initproc)basic_parse_basecoro_init,
	.tp_dealloc = (destructor)basic_parse_basecoro_dealloc,
	.tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_ITER,
	.tp_iter = ijson_return_self,
	.tp_iternext = ijson_return_none,
	.tp_methods = basic_parse_basecoro_methods
};
