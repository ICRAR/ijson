/*
 * parse_basecoro coroutine for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#ifndef PARSE_BASECORO_H
#define PARSE_BASECORO_H

#define PY_SSIZE_T_CLEAN
#include <Python.h>

/**
 * parse_basecoro coroutine object structure
 */
typedef struct {
    PyObject_HEAD
    PyObject *target_send;
    PyObject *path;
} ParseBasecoro;

/**
 * parse_basecoro coroutine object type
 */
extern PyTypeObject ParseBasecoro_Type;

/**
 * Utility function to check if an object is a parse_basecoro coroutine or not
 */
#define ParseBasecoro_Check(o) (Py_TYPE(o) == &ParseBasecoro_Type)

/**
 * The implementation of the parse_basecoro.send() method accepting an unpacked
 * event
 * @param self A parse_basecoro coroutine
 * @param path The path of this event
 * @param event The event name
 * @param value The value of this event
 * @return None, or NULL in case of an error
 */
PyObject* parse_basecoro_send_impl(PyObject *self, PyObject *event, PyObject *value);

#endif // PARSE_BASECORO_H