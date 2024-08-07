/*
 * items_basecoro coroutine implementation for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#include "common.h"
#include "items_basecoro.h"

/*
 * __init__, destructor, __iter__ and __next__
 */
static int items_basecoro_init(ItemsBasecoro *self, PyObject *args, PyObject *kwargs)
{
	self->target_send = NULL;
	self->prefix = NULL;
	self->object_depth = 0;
	builder_create(&self->builder);

	PyObject *map_type;
	M1_Z(PyArg_ParseTuple(args, "OOO", &(self->target_send), &(self->prefix), &map_type));
	Py_INCREF(self->target_send);
	Py_INCREF(self->prefix);
	M1_M1(builder_init(&self->builder, map_type));

	return 0;
}

static void items_basecoro_dealloc(ItemsBasecoro *self)
{
	Py_XDECREF(self->prefix);
	Py_XDECREF(self->target_send);
	builder_destroy(&self->builder);
	Py_TYPE(self)->tp_free((PyObject*)self);
}

PyObject* items_basecoro_send_impl(PyObject *self, PyObject *path, PyObject *event, PyObject *value)
{
	ItemsBasecoro *coro = (ItemsBasecoro *)self;

	if (builder_isactive(&coro->builder)) {
		coro->object_depth += (event == enames.start_map_ename || event == enames.start_array_ename);
		coro->object_depth -= (event == enames.end_map_ename || event == enames.end_array_ename);
		if (coro->object_depth > 0) {
			N_M1( builder_event(&coro->builder, event, value) );
		}
		else {
			PyObject *retval = builder_value(&coro->builder);
			CORO_SEND(coro->target_send, retval);
			Py_DECREF(retval);
			N_M1(builder_reset(&coro->builder));
		}
	}
	else {
		int cmp = PyObject_RichCompareBool(path, coro->prefix, Py_EQ);
		N_M1(cmp);
		if (cmp) {
			if (event == enames.start_map_ename || event == enames.start_array_ename) {
				coro->object_depth = 1;
				N_M1(builder_event(&coro->builder, event, value));
			}
			else {
				CORO_SEND(coro->target_send, value);
			}
		}
	}

	Py_RETURN_NONE;
}

static PyObject* items_basecoro_send(PyObject *self, PyObject *tuple)
{
	PyObject *path  = PyTuple_GetItem(tuple, 0);
	PyObject *event = PyTuple_GetItem(tuple, 1);
	PyObject *value = PyTuple_GetItem(tuple, 2);
	return items_basecoro_send_impl(self, path, event, value);
}

static PyMethodDef items_basecoro_methods[] = {
	{"send", items_basecoro_send, METH_O, "coroutine's send method"},
	{NULL, NULL, 0, NULL}
};

/*
 * items generator object type
 */
PyTypeObject ItemsBasecoro_Type = {
	PyVarObject_HEAD_INIT(NULL, 0)
	.tp_basicsize = sizeof(ItemsBasecoro),
	.tp_name = "_yajl2.items_basecoro",
	.tp_doc = "Coroutine dispatching fully-built objects for the given prefix",
	.tp_init = (initproc)items_basecoro_init,
	.tp_dealloc = (destructor)items_basecoro_dealloc,
	.tp_flags = Py_TPFLAGS_DEFAULT,
	.tp_iter = ijson_return_self,
	.tp_iternext = ijson_return_none,
	.tp_methods = items_basecoro_methods
};
