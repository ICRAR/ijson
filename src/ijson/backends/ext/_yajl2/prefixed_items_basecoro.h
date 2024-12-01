/*
 * prefixed_items_basecoro coroutine for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#ifndef PREFIXED_ITEMS_BASECORO_H
#define PREFIXED_ITEMS_BASECORO_H

#include "items_common.h"

/**
 * prefixed_items_basecoro coroutine object structure
 */
typedef ItemsCommonBasecoro PrefixedItemsBasecoro;

/**
 * prefixed_items_basecoro coroutine object type
 */
extern PyTypeObject PrefixedItemsBasecoro_Type;

/**
 * Utility function to check if an object is an prefixed_items_basecoro coroutine or not
 */
#define PrefixedItemsBasecoro_Check(o) (Py_TYPE(o) == &PrefixedItemsBasecoro_Type)

/**
 * The implementation of the prefixed_items_basecoro.send() method accepting an unpacked
 * event
 * @param self An prefixed_items_basecoro coroutine
 * @param path The path of this event
 * @param event The event name
 * @param value The value of this event
 * @return None, or NULL in case of an error
 */
PyObject* prefixed_items_basecoro_send_impl(PyObject *self, PyObject *path, PyObject *event, PyObject *value);

#endif // PREFIXED_ITEMS_BASECORO_H
