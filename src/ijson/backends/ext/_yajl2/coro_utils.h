/*
 * Coroutine utilities for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#ifndef CORO_UTILS_H
#define CORO_UTILS_H

#define PY_SSIZE_T_CLEAN
#include <Python.h>

/**
 * A tuple defining how to create an object
 */
typedef struct _pipeline_node {
	PyTypeObject *type;
	PyObject *args;
	PyObject *kwargs;
} pipeline_node;

/**
 * Creates coroutines as described in coro_pipeline, with a final sink
 *
 * @param sink the final coroutine-like object that will receive the result of
 * the pipeline
 * @param coro_pipeline the description of all elements to create in a coroutine
 * pipeline
 * @return The head of the coroutine pipeline (i.e., the coroutine where users
 * will send elements to)
 */
PyObject *chain(PyObject *sink, pipeline_node *coro_pipeline);

#endif // CORO_UTILS_H