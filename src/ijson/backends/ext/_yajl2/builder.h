/*
 * builder_t type and associated methods
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2019
 * Copyright by UWA (in the framework of the ICRAR)
 */

#ifndef BUILDER_H
#define BUILDER_H

#include <assert.h>
#include "common.h"

#define PY_SSIZE_T_CLEAN
#include <Python.h>

/**
 * builder_t structure.
 *
 * This is the parallel of the ObjectBuilder class from the ijson.common module,
 * only a bit more complicated since it's all C
 */
typedef struct _builder {
	PyObject *value;
	int active;
	PyObject *key;
	PyObject *value_stack;
	PyObject *map_type;
} builder_t;

/**
 * Initializes an empty builder which can be safely destroyed.
 *
 * @param builder the builder to empty-initialize
 */
static inline
void builder_create(builder_t *builder)
{
	builder->value = NULL;
	builder->map_type = NULL;
	builder->value_stack = NULL;
}

/**
 * Initialilzes a builder capable of assembling Python objects out of prefixed
 * events.
 *
 * @param builder the builder to initialize
 * @param map_type The mapping type to use for constructing objects out of
 *  (key, value) pairs. If None then dict is used.
 */
static inline
int builder_init(builder_t *builder, PyObject *map_type)
{
	M1_N(builder->value_stack = PyList_New(0));
	if (map_type != Py_None) {
		builder->map_type = map_type;
		Py_INCREF(map_type);
	}
	return 0;
}

/**
 * Destroys a builder and all its associated contents
 * @param builder The builder to destroy
 */
static inline
void builder_destroy(builder_t *builder)
{
	Py_DECREF(builder->value_stack);
	Py_XDECREF(builder->map_type);
	Py_XDECREF(builder->value);
}

/**
 * Returns whether the builder is currently active or not.
 * @param builder A builder
 * @return whether the builder is active (1) or not (0)
 */
static inline
int builder_isactive(builder_t *builder)
{
	return builder->active;
}

/**
 * Returns a new reference to the current value constructed by the builder.
 *
 * @param builder The builder
 * @return The value as currently constructed by this builder
 */
static inline
PyObject *builder_value(builder_t *builder)
{
	Py_INCREF(builder->value);
	return builder->value;
}

/**
 * Resets a builder to a pristine state so it can be used to build a new value.
 * @param builder The builder to reset
 * @return 0 if successful, -1 in case of an error
 */
static inline
int builder_reset(builder_t *builder)
{
	builder->active = 0;
	Py_CLEAR(builder->value);
	Py_CLEAR(builder->key);

	Py_ssize_t nvals = PyList_Size(builder->value_stack);
	M1_M1(PyList_SetSlice(builder->value_stack, 0, nvals, NULL));

	return 0;
}

static inline
int _builder_add(builder_t *builder, PyObject *value)
{
	Py_ssize_t nvals = PyList_Size(builder->value_stack);
	if (nvals == 0) {
		Py_INCREF(value);
		builder->value = value;
	}
	else {
		PyObject *last;
		M1_N(last = PyList_GetItem(builder->value_stack, nvals-1));
		assert(("stack element not list or dict-like",
		        PyList_Check(last) || PyMapping_Check(last)));
		if (PyList_Check(last)) {
			M1_M1(PyList_Append(last, value));
		}
		else { // it's a dict-like object
			M1_M1(PyObject_SetItem(last, builder->key, value));
		}
	}

	return 0;
}

/**
 * Feed an (event, value) pair to the builder for further constructing the
 * underlying value
 * @param builder A builder
 * @param ename The event name
 * @param value The value associated to this event
 * @return 0 if successful, -1 in case of an error
 */
static inline
int builder_event(builder_t *builder, PyObject *ename, PyObject *value)
{
	builder->active = 1;

	if (ename == enames.map_key_ename) {
		Py_XDECREF(builder->key);
		builder->key = value;
		Py_INCREF(builder->key);
	}
	else if (ename == enames.start_map_ename) {
		PyObject *mappable;
		if (builder->map_type) {
			mappable = PyObject_CallFunctionObjArgs(builder->map_type, NULL);
		}
		else {
			mappable = PyDict_New();
		}
		M1_N(mappable);
		M1_M1(_builder_add(builder, mappable));
		M1_M1(PyList_Append(builder->value_stack, mappable));
		Py_DECREF(mappable);
	}
	else if (ename == enames.start_array_ename) {
		PyObject *list;
		M1_N(list = PyList_New(0));
		M1_M1(_builder_add(builder, list));
		M1_M1(PyList_Append(builder->value_stack, list));
		Py_DECREF(list);
	}
	else if (ename == enames.end_array_ename || ename == enames.end_map_ename) {
		// pop
		Py_ssize_t nvals = PyList_Size(builder->value_stack);
		M1_M1(PyList_SetSlice(builder->value_stack, nvals-1, nvals, NULL));
	}
	else {
		M1_M1(_builder_add(builder, value));
	}

	return 0;
}

#endif /* BUILDER_H */