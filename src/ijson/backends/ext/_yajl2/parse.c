/*
 * parse generator implementation for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#include "basic_parse_basecoro.h"
#include "common.h"
#include "parse.h"
#include "parse_basecoro.h"

/*
 * __init__, destructor, __iter__ and __next__
 */
static int parsegen_init(ParseGen *self, PyObject *args, PyObject *kwargs)
{
	pipeline_node coro_pipeline[] = {
		{&ParseBasecoro_Type, NULL, NULL},
		{&BasicParseBasecoro_Type, NULL, kwargs},
		{NULL}
	};
	M1_M1(reading_generator_init(&self->reading_gen, args, coro_pipeline));
	return 0;
}

static void parsegen_dealloc(ParseGen *self) {
	reading_generator_dealloc(&self->reading_gen);
	Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject* parsegen_iternext(PyObject *self)
{
	ParseGen *gen = (ParseGen *)self;
	return reading_generator_next(&gen->reading_gen);
}

PyTypeObject ParseGen_Type = {
	PyVarObject_HEAD_INIT(NULL, 0)
	.tp_basicsize = sizeof(ParseGen),
	.tp_name = "_yajl2.parse",
	.tp_doc = "Generates (path,evt,value)",
	.tp_init = (initproc)parsegen_init,
	.tp_dealloc = (destructor)parsegen_dealloc,
	.tp_flags = Py_TPFLAGS_DEFAULT,
	.tp_iter = ijson_return_self,
	.tp_iternext = parsegen_iternext
};
