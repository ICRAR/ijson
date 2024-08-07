/*
 * basic_parse generator for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#ifndef BASIC_PARSE_H
#define BASIC_PARSE_H

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "reading_generator.h"

/**
 * basic_parse generator object structure
 */
typedef struct {
    PyObject_HEAD
    reading_generator_t reading_gen;
} BasicParseGen;

/**
 * basic_parse generator object type
 */
extern PyTypeObject BasicParseGen_Type;

#endif // BASIC_PARSE_H