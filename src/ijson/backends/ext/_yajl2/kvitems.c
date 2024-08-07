/*
 * kvitems generator implementation for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#include "basic_parse_basecoro.h"
#include "common.h"
#include "kvitems.h"
#include "kvitems_basecoro.h"
#include "parse_basecoro.h"

/*
 * __init__, destructor, __iter__ and __next__
 */
static int kvitemsgen_init(KVItemsGen *self, PyObject *args, PyObject *kwargs)
{
	PyObject *reading_args = PySequence_GetSlice(args, 0, 2);
	PyObject *kvitems_args = PySequence_GetSlice(args, 2, 4);
	pipeline_node coro_pipeline[] = {
		{&KVItemsBasecoro_Type, kvitems_args, NULL},
		{&ParseBasecoro_Type, NULL, NULL},
		{&BasicParseBasecoro_Type, NULL, kwargs},
		{NULL}
	};
	M1_M1(reading_generator_init(&self->reading_gen, reading_args, coro_pipeline));
	Py_DECREF(kvitems_args);
	Py_DECREF(reading_args);
	return 0;
}

static void kvitemsgen_dealloc(KVItemsGen *self)
{
	reading_generator_dealloc(&self->reading_gen);
	Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject* kvitemsgen_iternext(PyObject *self)
{
	KVItemsGen *gen = (KVItemsGen *)self;
	return reading_generator_next(&gen->reading_gen);
}

/*
 * kvitems generator object type
 */
PyTypeObject KVItemsGen_Type = {
	PyVarObject_HEAD_INIT(NULL, 0)
	.tp_basicsize = sizeof(KVItemsGen),
	.tp_name = "_yajl2.kvitems",
	.tp_doc = "Generates key/value pairs",
	.tp_init = (initproc)kvitemsgen_init,
	.tp_dealloc = (destructor)kvitemsgen_dealloc,
	.tp_flags = Py_TPFLAGS_DEFAULT,
	.tp_iter = ijson_return_self,
	.tp_iternext = kvitemsgen_iternext
};
