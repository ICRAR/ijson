/*
 * Module state definitions for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2024
 * Copyright by UWA (in the framework of the ICRAR)
 */

#ifndef MODULE_STATE_H
#define MODULE_STATE_H

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "event_names.h"

/*
 * Structure holding the full yajl2_c module state,
 * thus avoiding static global variables that would end up being shared
 * across sub-interpreters.
 */
typedef struct _yajl2_state {
	enames_t enames;
	PyObject *dot;
	PyObject *item;
	PyObject *dotitem;
	PyObject *JSONError;
	PyObject *IncompleteJSONError;
	PyObject *MalformedEventsError;
	PyObject *Decimal;
} yajl2_state;

/**
 * Gets the (typed) state from this module, internally import it.
 * Usable only after the module has been imported.
 */
yajl2_state *get_state_from_imported_module();

#endif /* MODULE_STATE_H */