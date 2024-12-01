/*
 * items generator for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#ifndef PREFIXED_ITEMS_H
#define PREFIXED_ITEMS_H

#include "reading_generator.h"

/**
 * items generator object structure
 */
typedef struct {
	PyObject_HEAD
	reading_generator_t reading_gen;
} PrefixedItemsGen;


/**
 * items generator object type
 */
extern PyTypeObject PrefixedItemsGen_Type;

#endif /* PREFIXED_ITEMS_H */
