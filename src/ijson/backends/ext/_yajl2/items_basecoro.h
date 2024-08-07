/*
 * items_basecoro coroutine for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#ifndef ITEMS_BASECORO_H
#define ITEMS_BASECORO_H

#include "builder.h"

/**
 * items_basecoro coroutine object structure
 */
typedef struct {
    PyObject_HEAD
    builder_t builder;
    PyObject *target_send;
    PyObject *prefix;
    int object_depth;
} ItemsBasecoro;

/**
 * items_basecoro coroutine object type
 */
extern PyTypeObject ItemsBasecoro_Type;

/**
 * Utility function to check if an object is an items_basecoro coroutine or not
 */
#define ItemsBasecoro_Check(o) (Py_TYPE(o) == &ItemsBasecoro_Type)

/**
 * The implementation of the items_basecoro.send() method accepting an unpacked
 * event
 * @param self An items_basecoro coroutine
 * @param path The path of this event
 * @param event The event name
 * @param value The value of this event
 * @return None, or NULL in case of an error
 */
PyObject* items_basecoro_send_impl(PyObject *self, PyObject *path, PyObject *event, PyObject *value);

#endif // ITEMS_BASECORO_H