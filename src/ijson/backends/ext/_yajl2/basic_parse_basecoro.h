/*
 * basic_parse_basecoro coroutine for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#ifndef BASIC_PARSE_BASECORO_H
#define BASIC_PARSE_BASECORO_H

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <yajl/yajl_common.h>
#include <yajl/yajl_parse.h>


/**
 * basic_parse_basecoro coroutine object structure
 */
typedef struct {
    PyObject_HEAD
    yajl_handle h;
    PyObject *target_send;
} BasicParseBasecoro;

/**
 * basic_parse_basecoro coroutine object type
 */
extern PyTypeObject BasicParseBasecoro_Type;

/**
 * Utility function to check if an object is an basic_parse_basecoro coroutine or not
 */
#define BasicParseBasecoro_Check(o) (Py_TYPE(o) == &BasicParseBasecoro_Type)

/**
 * yajl parsing routine wrapper that turns yajl errors into exceptions
 */
PyObject* ijson_yajl_parse(yajl_handle handle, char *buffer, size_t length);

#endif // BASIC_PARSE_BASECORO_H