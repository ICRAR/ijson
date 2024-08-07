/*
 * Coroutine utilities implementation for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#include "common.h"
#include "coro_utils.h"

PyObject *chain(PyObject *sink, pipeline_node *coro_pipeline)
{
	PyObject *coro = sink;
	Py_INCREF(coro);
	int element = 0;
	while (1) {
		pipeline_node node = coro_pipeline[element++];
		if (node.type == NULL) {
			break;
		}
		PyObject *coro_args;
		if (node.args) {
			int nargs = PyTuple_Size(node.args);
			N_N(coro_args = PyTuple_New(nargs + 1));
			Py_INCREF(coro);
			PyTuple_SET_ITEM(coro_args, 0, coro);
			int i;
			for (i = 0; i != nargs; i++) {
				PyTuple_SET_ITEM(coro_args, i + 1, PySequence_GetItem(node.args, i));
			}
		}
		else {
			N_N(coro_args = PyTuple_Pack(1, coro));
		}
		Py_DECREF(coro);
		N_N(coro = PyObject_Call((PyObject *)node.type, coro_args, node.kwargs));
		Py_DECREF(coro_args);
	}
	return coro;
}