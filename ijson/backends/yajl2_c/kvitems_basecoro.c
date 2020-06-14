/*
 * kvitems_basecoro coroutine implementation for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#include "common.h"
#include "kvitems_basecoro.h"

/*
 * __init__, destructor, __iter__ and __next__
 */
static int kvitems_basecoro_init(KVItemsBasecoro *self, PyObject *args, PyObject *kwargs)
{
	self->target_send = NULL;
	self->builder = NULL;
	self->prefix = NULL;
	self->key = NULL;

	PyObject *map_type;
	M1_Z(PyArg_ParseTuple(args, "OOO", &(self->target_send), &(self->prefix), &map_type));
	Py_INCREF(self->target_send);
	Py_INCREF(self->prefix);
	M1_N(self->builder = builder_create(map_type));

	return 0;
}

static void kvitems_basecoro_dealloc(KVItemsBasecoro *self)
{
	Py_XDECREF(self->prefix);
	Py_XDECREF(self->key);
	Py_XDECREF(self->target_send);
	if (self->builder) {
		builder_destroy(self->builder);
	}
	Py_TYPE(self)->tp_free((PyObject*)self);
}

static int kvitems_basecoro_start_new_member(KVItemsBasecoro *coro, PyObject *key)
{
	coro->object_depth = 0;
	Py_XDECREF(coro->key);
	coro->key = key;
	Py_INCREF(coro->key);
	M1_M1(builder_reset(coro->builder));
	coro->builder->active = 1;
	return 0;
}

PyObject* kvitems_basecoro_send_impl(PyObject *self, PyObject *path, PyObject *event, PyObject *value)
{
	KVItemsBasecoro *coro = (KVItemsBasecoro *)self;

	PyObject *retval = NULL;
	PyObject *retkey = NULL;
	if (builder_isactive(coro->builder)) {
		coro->object_depth += (event == enames.start_map_ename);
		coro->object_depth -= (event == enames.end_map_ename);
		if ((event != enames.map_key_ename || coro->object_depth != 0) &&
		    (event != enames.end_map_ename || coro->object_depth != -1)) {
			N_M1(builder_event(coro->builder, event, value));
		}
		else {
			retval = builder_value(coro->builder);
			retkey = coro->key;
			Py_INCREF(retkey);
			if (event == enames.map_key_ename) {
				N_M1(kvitems_basecoro_start_new_member(coro, value));
			}
			else {
				Py_CLEAR(coro->key);
				coro->builder->active = 0;
			}
		}
	}
	else {
		int cmp = PyObject_RichCompareBool(path, coro->prefix, Py_EQ);
		N_M1(cmp);
		if (cmp == 1 && event == enames.map_key_ename) {
			N_M1(kvitems_basecoro_start_new_member(coro, value));
		}
	}

	if (retval) {
		PyObject *tuple = PyTuple_Pack(2, retkey, retval);
		Py_XDECREF(retkey);
		Py_XDECREF(retval);
		CORO_SEND(coro->target_send, tuple);
		Py_DECREF(tuple);
	}

	Py_RETURN_NONE;
}

static PyObject* kvitems_basecoro_send(PyObject *self, PyObject *tuple)
{
	PyObject *path  = PyTuple_GetItem(tuple, 0);
	PyObject *event = PyTuple_GetItem(tuple, 1);
	PyObject *value = PyTuple_GetItem(tuple, 2);
	return kvitems_basecoro_send_impl(self, path, event, value);
}

static PyMethodDef kvitems_basecoro_methods[] = {
	{"send", kvitems_basecoro_send, METH_O, "coroutine's send method"},
	{NULL, NULL, 0, NULL}
};

/*
 * kvitems generator object type
 */
PyTypeObject KVItemsBasecoro_Type = {
#if PY_MAJOR_VERSION >= 3
	PyVarObject_HEAD_INIT(NULL, 0)
#else
	PyObject_HEAD_INIT(NULL)
#endif
	.tp_basicsize = sizeof(KVItemsBasecoro),
	.tp_name = "_yajl2.kvitems_basecoro",
	.tp_doc = "Coroutine dispathing (key, value) tuples",
	.tp_init = (initproc)kvitems_basecoro_init,
	.tp_dealloc = (destructor)kvitems_basecoro_dealloc,
	.tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_ITER,
	.tp_iter = ijson_return_self,
	.tp_iternext = ijson_return_none,
	.tp_methods = kvitems_basecoro_methods
};
