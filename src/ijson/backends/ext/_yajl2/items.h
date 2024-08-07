/*
 * items generator for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2020
 * Copyright by UWA (in the framework of the ICRAR)
 */

#ifndef ITEMS_H
#define ITEMS_H

#include "reading_generator.h"

/**
 * items generator object structure
 */
typedef struct {
	PyObject_HEAD
	reading_generator_t reading_gen;
} ItemsGen;


/**
 * items generator object type
 */
extern PyTypeObject ItemsGen_Type;

#endif /* ITEMS_H */