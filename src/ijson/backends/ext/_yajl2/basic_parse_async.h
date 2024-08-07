/*
 * basic_parse_async asynchronous iterable for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#ifndef BASIC_PARSE_ASYNC_H
#define BASIC_PARSE_ASYNC_H

#define PY_SSIZE_T_CLEAN
#include <Python.h>

/**
 * basic_parse_async asynchronous iterable object type
 */
extern PyTypeObject BasicParseAsync_Type;

#endif // BASIC_PARSE_H