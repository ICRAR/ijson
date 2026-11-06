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
 * State of each open container, used to validate the incoming events
 */
enum container_state {
	CONTAINER_ARRAY,
	CONTAINER_MAP_KEY,   /* map expecting a map_key or end_map */
	CONTAINER_MAP_VALUE  /* map expecting a value after a map_key */
};

static const char *container_names[] = {
	"array",
	"map expecting a key",
	"map expecting a value"
};

/*
 * __init__, destructor, __iter__ and __next__
 */
static int parse_basecoro_init(ParseBasecoro *self, PyObject *args, PyObject *kwargs)
{
	M1_Z(PyArg_ParseTuple(args, "O", &self->target_send));
	Py_INCREF(self->target_send);
	M1_N(self->path = PyList_New(0));
	M1_N(self->module_state = get_state_from_imported_module());
	self->containers = NULL;
	self->ncontainers = 0;
	self->containers_size = 0;

	PyObject *empty;
	M1_N(empty = PyUnicode_FromString(""));
	int res = PyList_Append(self->path, empty);
	Py_DECREF(empty);
	M1_M1(res);

	return 0;
}

static void parse_basecoro_dealloc(ParseBasecoro *self)
{
	PyMem_Free(self->containers);
	Py_XDECREF(self->path);
	Py_XDECREF(self->target_send);
	Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject *malformed_event(ParseBasecoro *gen, PyObject *event)
{
	const char *where = "top level";
	if (gen->ncontainers > 0) {
		where = container_names[(int)gen->containers[gen->ncontainers - 1]];
	}
	PyErr_Format(gen->module_state->MalformedEventsError,
	             "unexpected %R event in %s", event, where);
	return NULL;
}

static int push_container(ParseBasecoro *gen, enum container_state state)
{
	if (gen->ncontainers == gen->containers_size) {
		Py_ssize_t new_size = gen->containers_size ? gen->containers_size * 2 : 16;
		char *containers = PyMem_Realloc(gen->containers, new_size);
		if (!containers) {
			PyErr_NoMemory();
			return -1;
		}
		gen->containers = containers;
		gen->containers_size = new_size;
	}
	gen->containers[gen->ncontainers++] = (char)state;
	return 0;
}

static inline int is_scalar_event(enames_t *enames, PyObject *event)
{
	return event == enames->null_ename || event == enames->boolean_ename ||
	       event == enames->integer_ename || event == enames->double_ename ||
	       event == enames->number_ename || event == enames->string_ename;
}

PyObject* parse_basecoro_send_impl(PyObject *self, PyObject *event, PyObject *value)
{
	ParseBasecoro *gen = (ParseBasecoro *)self;
	Py_ssize_t npaths = PyList_GET_SIZE(gen->path);
	enames_t enames = gen->module_state->enames;
	PyObject *dot = gen->module_state->dot;
	PyObject *dotitem = gen->module_state->dotitem;
	PyObject *item = gen->module_state->item;
	char *container = gen->ncontainers > 0 ? &gen->containers[gen->ncontainers - 1] : NULL;

	// Validate the event against the current container, and
	// calculate current prefix
	PyObject *prefix;
	if (event == enames.map_key_ename) {
		if (!container || *container != CONTAINER_MAP_KEY) {
			return malformed_event(gen, event);
		}

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
		Py_XDECREF(last_path_dot);
		N_N(new_path);
		PyList_SetItem(gen->path, npaths - 1, new_path);
		*container = CONTAINER_MAP_VALUE;

		prefix = PyList_GET_ITEM(gen->path, npaths - 2);
	}
	else if (event == enames.end_array_ename || event == enames.end_map_ename) {
		char expected = event == enames.end_map_ename ? CONTAINER_MAP_KEY : CONTAINER_ARRAY;
		if (!container || *container != expected) {
			return malformed_event(gen, event);
		}
		// pop
		N_M1(PyList_SetSlice(gen->path, npaths - 1, npaths, NULL));
		npaths--;
		gen->ncontainers--;
		if (gen->ncontainers > 0 && gen->containers[gen->ncontainers - 1] == CONTAINER_MAP_VALUE) {
			gen->containers[gen->ncontainers - 1] = CONTAINER_MAP_KEY;
		}
		prefix = PyList_GET_ITEM(gen->path, npaths - 1);
	}
	else if (container && *container == CONTAINER_MAP_KEY) {
		// anything else needs a preceding map_key
		return malformed_event(gen, event);
	}
	else if (event == enames.start_array_ename) {
		prefix = PyList_GET_ITEM(gen->path, npaths - 1);

		// to_append = '.item' if path_stack[-1] else 'item'
		// path_stack.append(path_stack[-1] + to_append)
		PyObject *new_path;
		if (PyUnicode_GET_LENGTH(prefix) > 0) {
			N_N(new_path = PyUnicode_Concat(prefix, dotitem));
		}
		else {
			new_path = item;
			Py_INCREF(new_path);
		}
		int res = PyList_Append(gen->path, new_path);
		Py_DECREF(new_path);
		N_M1(res);
		if (push_container(gen, CONTAINER_ARRAY) == -1) {
			PyList_SetSlice(gen->path, npaths, npaths + 1, NULL);
			return NULL;
		}
	}
	else if (event == enames.start_map_ename) {
		prefix = PyList_GET_ITEM(gen->path, npaths - 1);
		N_M1(PyList_Append(gen->path, Py_None));
		if (push_container(gen, CONTAINER_MAP_KEY) == -1) {
			PyList_SetSlice(gen->path, npaths, npaths + 1, NULL);
			return NULL;
		}
	}
	else if (is_scalar_event(&enames, event)) {
		prefix = PyList_GET_ITEM(gen->path, npaths - 1);
		if (container && *container == CONTAINER_MAP_VALUE) {
			*container = CONTAINER_MAP_KEY;
		}
	}
	else {
		return malformed_event(gen, event);
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
