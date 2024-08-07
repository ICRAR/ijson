/*
 * basic_parse generator implementation for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#include "basic_parse.h"
#include "basic_parse_basecoro.h"
#include "common.h"

/*
 * __init__, destructor, __iter__ and __next__
 */
static int basicparsegen_init(BasicParseGen *self, PyObject *args, PyObject *kwargs)
{
	pipeline_node coro_pipeline[] = {
		{&BasicParseBasecoro_Type, NULL, kwargs},
		{NULL}
	};
	M1_M1(reading_generator_init(&self->reading_gen, args, coro_pipeline));
	return 0;
}

static void basicparsegen_dealloc(BasicParseGen *self) {
	reading_generator_dealloc(&self->reading_gen);
	Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject* basicparsegen_iternext(PyObject *self)
{
	BasicParseGen *gen = (BasicParseGen *)self;
	return reading_generator_next(&gen->reading_gen);
}


PyTypeObject BasicParseGen_Type = {
	PyVarObject_HEAD_INIT(NULL, 0)
	.tp_basicsize = sizeof(BasicParseGen),
	.tp_name = "_yajl2.basic_parse",
	.tp_doc = "Generator of (evt,value)",
	.tp_init = (initproc)basicparsegen_init,
	.tp_dealloc = (destructor)basicparsegen_dealloc,
	.tp_flags = Py_TPFLAGS_DEFAULT,
	.tp_iter = ijson_return_self,
	.tp_iternext = basicparsegen_iternext
};
