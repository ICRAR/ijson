/*
 * parse_basecoro coroutine implementation for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#include "common.h"
#include "items_basecoro.h"
#include "kvitems_basecoro.h"
#include "parse_basecoro.h"

/*
 * __init__, destructor, __iter__ and __next__
 */
static int parse_basecoro_init(ParseBasecoro *self, PyObject *args, PyObject *kwargs)
{
	M1_Z(PyArg_ParseTuple(args, "O", &self->target_send));
	Py_INCREF(self->target_send);
	M1_N(self->path = PyList_New(0));
	M1_N(self->module_state = get_state_from_imported_module());

	PyObject *empty;
	M1_N(empty = PyUnicode_FromString(""));
	int res = PyList_Append(self->path, empty);
	Py_DECREF(empty);
	M1_M1(res);

	return 0;
}

static void parse_basecoro_dealloc(ParseBasecoro *self)
{
	Py_XDECREF(self->path);
	Py_XDECREF(self->target_send);
	Py_TYPE(self)->tp_free((PyObject*)self);
}

PyObject* parse_basecoro_send_impl(PyObject *self, PyObject *event, PyObject *value)
{
	ParseBasecoro *gen = (ParseBasecoro *)self;
	Py_ssize_t npaths = PyList_GET_SIZE(gen->path);
	enames_t enames = gen->module_state->enames;
	PyObject *dot = gen->module_state->dot;
	PyObject *dotitem = gen->module_state->dotitem;
	PyObject *item = gen->module_state->item;

	// Calculate current prefix
	PyObject *prefix;
	if ((event == enames.end_array_ename || event == enames.end_map_ename ||
	     event == enames.map_key_ename) && npaths < 2) {
		// unbalanced user-provided events, path[0] is the root and stays
		PyErr_Format(PyExc_IndexError, "%U event without an enclosing container", event);
		return NULL;
	}
	if (event == enames.end_array_ename || event == enames.end_map_ename) {
		// pop
		N_M1(PyList_SetSlice(gen->path, npaths - 1, npaths, NULL));
		npaths--;
		prefix = PyList_GET_ITEM(gen->path, npaths - 1);
	}
	else if (event == enames.map_key_ename) {

		// last_path = path_stack[-2]
		// to_append = '.' + value if len(path_stack) > 1 else value
		// new_path = path_stack[-2] + to_append
		PyObject *last_path = PyList_GET_ITEM(gen->path, npaths - 2);
		PyObject *last_path_dot = NULL;
		if (npaths > 2) {
			last_path_dot = PyUnicode_Concat(last_path, dot);
			N_N(last_path_dot);
			last_path = last_path_dot;
		}
		PyObject *new_path = PyUnicode_Concat(last_path, value);
		N_N(new_path);
		Py_XDECREF(last_path_dot);
		PyList_SetItem(gen->path, npaths - 1, new_path);

		prefix = PyList_GET_ITEM(gen->path, npaths - 2);
	}
	else {
		prefix = PyList_GET_ITEM(gen->path, npaths - 1);
	}

	// If entering a map/array, append name to path
	if (event == enames.start_array_ename) {

		// to_append = '.item' if path_stack[-1] else 'item'
		// path_stack.append(path_stack[-1] + to_append)
		PyObject *last_path = PyList_GET_ITEM(gen->path, npaths - 1);
		if (!PyUnicode_Check(last_path)) {
			// start_array right after start_map, without a map_key
			PyErr_SetString(PyExc_TypeError, "start_array event in map without a preceding map_key");
			return NULL;
		}
		if (PyUnicode_GET_LENGTH(last_path) > 0) {
			PyObject *new_path = PyUnicode_Concat(last_path, dotitem);
			N_N(new_path);
			N_M1(PyList_Append(gen->path, new_path));
			Py_DECREF(new_path);
		}
		else {
			N_M1(PyList_Append(gen->path, item));
		}
	}
	else if (event == enames.start_map_ename) {
		Py_INCREF(Py_None);
		N_M1(PyList_Append(gen->path, Py_None));
	}

	if (KVItemsBasecoro_Check(gen->target_send)) {
		kvitems_basecoro_send_impl(gen->target_send, prefix, event, value);
	}
	else if (ItemsBasecoro_Check(gen->target_send)) {
		items_basecoro_send_impl(gen->target_send, prefix, event, value);
	}
	else {
		PyObject *res;
		N_N(res = PyTuple_Pack(3, prefix, event, value));
		CORO_SEND(gen->target_send, res);
		Py_DECREF(res);
	}
	Py_RETURN_NONE;
}

static PyObject* parse_basecoro_send(PyObject *self, PyObject *tuple)
{
	PyObject *event = NULL;
	PyObject *value = NULL;
	PyObject *result = NULL;
	if(!ijson_unpack(tuple, 2, &event, &value)) {
		event = get_builtin_ename(&((ParseBasecoro *)self)->module_state->enames, event);
		result = parse_basecoro_send_impl(self, event, value);
	}
	Py_XDECREF(value);
	Py_XDECREF(event);
	return result;
}

static PyMethodDef parse_basecoro_methods[] = {
	{"send", parse_basecoro_send, METH_O, "coroutine's send method"},
	{NULL, NULL, 0, NULL}
};


PyTypeObject ParseBasecoro_Type = {
	PyVarObject_HEAD_INIT(NULL, 0)
	.tp_basicsize = sizeof(ParseBasecoro),
	.tp_name = "_yajl2.parse_basecoro",
	.tp_doc = "Coroutine dispatching (path,evt,value) tuples",
	.tp_init = (initproc)parse_basecoro_init,
	.tp_dealloc = (destructor)parse_basecoro_dealloc,
	.tp_flags = Py_TPFLAGS_DEFAULT,
	.tp_iter = ijson_return_self,
	.tp_iternext = ijson_return_none,
	.tp_methods = parse_basecoro_methods
};
