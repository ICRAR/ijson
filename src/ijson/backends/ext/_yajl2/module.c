/*
 * _yajl2 backend for ijson
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2016
 * Copyright by UWA (in the framework of the ICRAR)
 */
#include <assert.h>
#include <stdarg.h>

#include "common.h"
#include "async_reading_generator.h"
#include "basic_parse.h"
#include "basic_parse_async.h"
#include "basic_parse_basecoro.h"
#include "parse.h"
#include "parse_async.h"
#include "parse_basecoro.h"
#include "items.h"
#include "items_async.h"
#include "items_basecoro.h"
#include "kvitems.h"
#include "kvitems_async.h"
#include "kvitems_basecoro.h"

#define MODULE_NAME "_yajl2"

static PyMethodDef yajl2_methods[] = {
	{NULL, NULL, 0, NULL}        /* Sentinel */
};

static int _yajl2_mod_exec(PyObject *m);
static void _yajl2_mod_free(void *m);

static PyModuleDef_Slot yajl2_slots[] = {
	{Py_mod_exec, _yajl2_mod_exec},
#if PY_VERSION_HEX >= 0x030C0000
	{Py_mod_multiple_interpreters, Py_MOD_PER_INTERPRETER_GIL_SUPPORTED},
#endif
#ifdef Py_GIL_DISABLED
	{Py_mod_gil, Py_MOD_GIL_NOT_USED},
#endif
	{0, NULL},
};

PyObject* ijson_return_self(PyObject *self)
{
	Py_INCREF(self);
	return self;
}

PyObject* ijson_return_none(PyObject *self)
{
	Py_RETURN_NONE;
}

int ijson_unpack(PyObject *o, Py_ssize_t expected, ...)
{
	va_list args;
	va_start(args, expected);
	PyObject *iter = PyObject_GetIter(o);
	if (!iter) {
		PyErr_Format(PyExc_TypeError, "cannot unpack non-iterable %s object", Py_TYPE(o)->tp_name);
		return -1;
	}
	Py_ssize_t count = 0;
	for (PyObject *o; (o = PyIter_Next(iter)); count++) {
		if (count >= expected) {
			continue;
		}
		PyObject **target = va_arg(args, PyObject **);
		*target = o;
	}
	Py_DECREF(iter);
	if (PyErr_Occurred()) {
		return -1;
	}
	if (count > expected) {
		PyErr_Format(PyExc_ValueError, "too many values to unpack (excepted %d, got %zd)", expected, count);
		return -1;
	}
	else if (count < expected) {
		PyErr_Format(PyExc_ValueError, "not enough values to unpack (excepted %d, got %zd)", expected, count);
		return -1;
	}
	return 0;
}

/* Module initialization */

/* Support for Python 2/3 */
static struct PyModuleDef moduledef = {
	.m_base = PyModuleDef_HEAD_INIT,
	.m_name = MODULE_NAME,
	.m_doc = "wrapper for yajl2 methods",
	.m_size = sizeof(yajl2_state),
	.m_methods = yajl2_methods,
	.m_slots = yajl2_slots,
	.m_free = _yajl2_mod_free,
};

static yajl2_state *get_state(PyObject *module)
{
	yajl2_state *module_state = PyModule_GetState(module);
	if (!module_state) {
		PyErr_SetString(PyExc_RuntimeError, "No module state :(");
	}
	return module_state;
}

yajl2_state *get_state_from_imported_module()
{
#if defined(PYPY_VERSION_NUM) && PYPY_VERSION_NUM <= 0x07031100
	// Until 7.3.17 PyPy didn't correctly export PyImport_ImportModuleLevel
	// see https://github.com/pypy/pypy/issues/5013
	PyObject *module = PyImport_ImportModule("ijson.backends." MODULE_NAME);
#else
	PyObject *module = PyImport_ImportModuleLevel(
	    MODULE_NAME, PyEval_GetGlobals(), Py_None, NULL, 1
	);
#endif
	N_N(module);
	yajl2_state *module_state = get_state(module);
	Py_DECREF(module);
	return module_state;
}

PyMODINIT_FUNC PyInit__yajl2(void)
{
	return PyModuleDef_Init(&moduledef);
}

static int _yajl2_mod_exec(PyObject *m)
{
#define ADD_TYPE(name, type) \
	{ \
		type.tp_new = PyType_GenericNew; \
		M1_M1(PyType_Ready(&type)); \
		Py_INCREF(&type); \
		PyModule_AddObject(m, name, (PyObject *)&type); \
	}
	ADD_TYPE("basic_parse_basecoro", BasicParseBasecoro_Type);
	ADD_TYPE("basic_parse", BasicParseGen_Type);
	ADD_TYPE("parse_basecoro", ParseBasecoro_Type);
	ADD_TYPE("parse", ParseGen_Type);
	ADD_TYPE("kvitems_basecoro", KVItemsBasecoro_Type);
	ADD_TYPE("kvitems", KVItemsGen_Type);
	ADD_TYPE("items_basecoro", ItemsBasecoro_Type);
	ADD_TYPE("items", ItemsGen_Type);
	ADD_TYPE("_async_reading_iterator", AsyncReadingGeneratorType);
	ADD_TYPE("basic_parse_async", BasicParseAsync_Type);
	ADD_TYPE("parse_async", ParseAsync_Type);
	ADD_TYPE("kvitems_async", KVItemsAsync_Type);
	ADD_TYPE("items_async", ItemsAsync_Type);

	yajl2_state *state;
	M1_N(state = get_state(m));
	M1_N(state->dot = PyUnicode_FromString("."));
	M1_N(state->item = PyUnicode_FromString("item"));
	M1_N(state->dotitem = PyUnicode_FromString(".item"));

#define INIT_ENAME(i, member, value)                                \
  {                                                                 \
    M1_N(state->enames.member = PyUnicode_FromString(value));       \
    state->enames.hashes[i] = PyObject_Hash(state->enames.member);  \
  }
	FOR_EACH_EVENT(INIT_ENAME);
#undef INIT_ENAME

	// Import globally-used names
	PyObject *ijson_common = PyImport_ImportModule("ijson.common");
	M1_N(ijson_common);
	state->JSONError = PyObject_GetAttrString(ijson_common, "JSONError");
	state->IncompleteJSONError = PyObject_GetAttrString(ijson_common, "IncompleteJSONError");
	state->MalformedEventsError = PyObject_GetAttrString(ijson_common, "MalformedEventsError");
	Py_DECREF(ijson_common);
	M1_N(state->JSONError);
	M1_N(state->IncompleteJSONError);
	M1_N(state->MalformedEventsError);

	PyObject *decimal_module = PyImport_ImportModule("decimal");
	M1_N(decimal_module);
	state->Decimal = PyObject_GetAttrString(decimal_module, "Decimal");
	Py_DECREF(decimal_module);
	M1_N(state->Decimal);

	return 0;
}

void _yajl2_mod_free(void *self)
{
	yajl2_state *state = PyModule_GetState((PyObject *)self);
	if (!state) {
		// module could have been initialised but not executed.
		// We saw this in 3.8 when importing with importlib.module_from_spec
		// and *not* executing the resulting module with spec.loader.exec_module.
		return;
	}
	Py_XDECREF(state->Decimal);
	Py_XDECREF(state->MalformedEventsError);
	Py_XDECREF(state->IncompleteJSONError);
	Py_XDECREF(state->JSONError);
	Py_XDECREF(state->dotitem);
	Py_XDECREF(state->item);
	Py_XDECREF(state->dot);
#define DECREF(_i, member, _value) Py_XDECREF(state->enames.member)
	FOR_EACH_EVENT(DECREF)
#undef DECREF
}