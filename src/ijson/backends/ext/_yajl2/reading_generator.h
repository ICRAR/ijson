/*
 * reading_generator_t type and methods for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2019
 * Copyright by UWA (in the framework of the ICRAR)
 */

#ifndef READING_GENERATOR_H
#define READING_GENERATOR_H

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "coro_utils.h"

/**
 * reading_generator_t type definition
 */
typedef struct _reading_generator {
    PyObject *coro;
    PyObject *read_func;
    PyObject *buf_size;
    PyObject *buffer;
    PyObject *events;
    Py_ssize_t pos;
    int finished;
} reading_generator_t;

/**
 * Initialises a reading_generator_t object from the given arguments, which
 * should contain a file-like object and a buffer size (optional).
 *
 * @param self A reading_generator_t object
 * @param args A tuple containing a file-like object and a buffer size (optional)
 * @param coro_pipeline A description of the coroutine pipeline to create internally
 *  in this reading generator, where data will be pushed to, and which will send
 *  events to the events list
 * @return 0 if successful, -1 in case of an error
 */
int reading_generator_init(reading_generator_t *self, PyObject *args, pipeline_node *coro_pipeline);

/**
 * Deallocates all resources associated to the given reading_generator_t object.
 * @param self A reading_generator_t object
 */
void reading_generator_dealloc(reading_generator_t *self);

/**
 * Advances the reading_generator_t object by reading data off the underlying
 * file-like object, feeding it into its coro, with results ending
 * up in self->events, from which they are returned.
 * @param self A reading_generator_t object
 * @return The next event generated from this iterative process
 */
PyObject *reading_generator_next(reading_generator_t *self);

#endif // READING_GENERATOR_H