/*
 * kvitems_basecoro coroutine for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#ifndef KVITEMS_BASECORO_H
#define KVITEMS_BASECORO_H

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "builder.h"

/**
 * kvitems_basecoro coroutine object structure
 */
typedef struct {
    PyObject_HEAD
    builder_t builder;
    PyObject *target_send;
    PyObject *prefix;
    PyObject *key;
    int object_depth;
} KVItemsBasecoro;

/**
 * kvitems_basecoro coroutine object type
 */
extern PyTypeObject KVItemsBasecoro_Type;

/**
 * Utility function to check if an object is a kvitems_basecoro coroutine or not
 */
#define KVItemsBasecoro_Check(o) (Py_TYPE(o) == &KVItemsBasecoro_Type)

/**
 * The implementation of the kvitems_basecoro.send() method accepting an unpacked
 * event
 * @param self A kvitems_basecoro coroutine
 * @param path The path of this event
 * @param event The event name
 * @param value The value of this event
 * @return None, or NULL in case of an error
 */
PyObject* kvitems_basecoro_send_impl(PyObject *self, PyObject *path, PyObject *event, PyObject *value);

#endif /* KVITEMS_BASECORO_H */