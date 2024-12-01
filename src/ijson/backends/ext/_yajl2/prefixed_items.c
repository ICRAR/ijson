/*
 * items generator implementation for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#include "common.h"
#include "prefixed_items.h"
#include "prefixed_items_basecoro.h"
#include "parse_basecoro.h"
#include "basic_parse_basecoro.h"

/*
 * __init__, destructor, __iter__ and __next__
 */
static int prefixed_itemsgen_init(PrefixedItemsGen *self, PyObject *args, PyObject *kwargs)
{
	PyObject *reading_args = PySequence_GetSlice(args, 0, 2);
	PyObject *items_args = PySequence_GetSlice(args, 2, 4);
	pipeline_node coro_pipeline[] = {
		{&PrefixedItemsBasecoro_Type, items_args, NULL},
		{&ParseBasecoro_Type, NULL, NULL},
		{&BasicParseBasecoro_Type, NULL, kwargs},
		{NULL}
	};
	int res = reading_generator_init(&self->reading_gen, reading_args, coro_pipeline);
	Py_DECREF(items_args);
	Py_DECREF(reading_args);
	return res;
}

static void prefixed_itemsgen_dealloc(PrefixedItemsGen *self)
{
	reading_generator_dealloc(&self->reading_gen);
	Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject* prefixed_itemsgen_iternext(PyObject *self)
{
	PrefixedItemsGen *gen = (PrefixedItemsGen *)self;
	return reading_generator_next(&gen->reading_gen);
}

/*
 * items generator object type
 */
PyTypeObject PrefixedItemsGen_Type = {
	PyVarObject_HEAD_INIT(NULL, 0)
	.tp_basicsize = sizeof(PrefixedItemsGen),
	.tp_name = "_yajl2.prefixed_items",
	.tp_doc = "Generates items",
	.tp_init = (initproc)prefixed_itemsgen_init,
	.tp_dealloc = (destructor)prefixed_itemsgen_dealloc,
	.tp_flags = Py_TPFLAGS_DEFAULT,
	.tp_iter = ijson_return_self,
	.tp_iternext = prefixed_itemsgen_iternext
};
