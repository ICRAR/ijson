/*
 * kvitems generator for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#ifndef KVITEMS_H
#define KVITEMS_H

#include "reading_generator.h"

/**
 * kvitems generator object structure
 */
typedef struct {
	PyObject_HEAD
	reading_generator_t reading_gen;
} KVItemsGen;

/**
 * kvitems generator object type
 */
extern PyTypeObject KVItemsGen_Type;

#endif /* KVITEMS_H */