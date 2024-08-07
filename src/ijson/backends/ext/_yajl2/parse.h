/*
 * parse generator for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#ifndef PARSE_H
#define PARSE_H

#include "reading_generator.h"

/**
 * parse generator object structure
 */
typedef struct {
    PyObject_HEAD
    reading_generator_t reading_gen;
} ParseGen;

/**
 * parse generator object type
 */
extern PyTypeObject ParseGen_Type;

#endif // PARSE_H