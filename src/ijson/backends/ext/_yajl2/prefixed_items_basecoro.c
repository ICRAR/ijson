/*
 * prefixed_items_basecoro coroutine implementation for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#include "common.h"
#include "prefixed_items_basecoro.h"

/*
 * __init__, destructor, __iter__ and __next__
 */
static int prefixed_items_basecoro_init(PrefixedItemsBasecoro *self, PyObject *args, PyObject *kwargs)
{
	self->target_send = NULL;
	self->prefix = NULL;
	self->object_depth = 0;
	self->pending_builder_reset = 0;
	M1_N(self->module_state = get_state_from_imported_module());
	builder_create(&self->builder);

	PyObject *map_type;
	M1_Z(PyArg_ParseTuple(args, "OOO", &(self->target_send), &(self->prefix), &map_type));
	Py_INCREF(self->target_send);
	Py_INCREF(self->prefix);
	M1_M1(builder_init(&self->builder, map_type));

	return 0;
}

static void prefixed_items_basecoro_dealloc(PrefixedItemsBasecoro *self)
{
	Py_XDECREF(self->prefix);
	Py_XDECREF(self->target_send);
	builder_destroy(&self->builder);
	Py_TYPE(self)->tp_free((PyObject*)self);
}

PyObject* prefixed_items_basecoro_send_impl(PyObject *self, PyObject *path, PyObject *event, PyObject *value)
{
	PrefixedItemsBasecoro *coro = (PrefixedItemsBasecoro *)self;

	PyObject *retval;
	N_N(retval = items_common_send_top(self, path, event, value));
	if (retval == Py_None)
		Py_RETURN_NONE;
	PyObject *tuple = PyTuple_Pack(2, path, retval);
	CORO_SEND(coro->target_send, tuple);
	Py_DECREF(tuple);
	items_common_send_bottom(self, retval);
	Py_RETURN_NONE;
}

static PyObject* prefixed_items_basecoro_send(PyObject *self, PyObject *tuple)
{
	PyObject *path  = PyTuple_GetItem(tuple, 0);
	PyObject *event = PyTuple_GetItem(tuple, 1);
	PyObject *value = PyTuple_GetItem(tuple, 2);
	return prefixed_items_basecoro_send_impl(self, path, event, value);
}

static PyMethodDef prefixed_items_basecoro_methods[] = {
	{"send", prefixed_items_basecoro_send, METH_O, "coroutine's send method"},
	{NULL, NULL, 0, NULL}
};

/*
 * items generator object type
 */
PyTypeObject PrefixedItemsBasecoro_Type = {
	PyVarObject_HEAD_INIT(NULL, 0)
	.tp_basicsize = sizeof(PrefixedItemsBasecoro),
	.tp_name = "_yajl2.prefixed_items_basecoro",
	.tp_doc = "Coroutine dispatching fully-built objects for the given prefix",
	.tp_init = (initproc)prefixed_items_basecoro_init,
	.tp_dealloc = (destructor)prefixed_items_basecoro_dealloc,
	.tp_flags = Py_TPFLAGS_DEFAULT,
	.tp_iter = ijson_return_self,
	.tp_iternext = ijson_return_none,
	.tp_methods = prefixed_items_basecoro_methods
};
