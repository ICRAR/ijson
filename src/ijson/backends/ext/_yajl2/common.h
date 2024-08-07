/*
 * Common definitions for ijson's C backend
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2019
 * Copyright by UWA (in the framework of the ICRAR)
 */

#ifndef COMMON_H
#define COMMON_H

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#define STRING_FROM_UTF8(val, len) PyUnicode_FromStringAndSize((const char *)val, len)

/*
 * Error-handling macros to help reducing clutter in the code.
 * N: NULL, M1: -1, Z: zero, NZ: not-zero, LZ: less-than-zero
 * */
#define RETURN_X_IF_COND(statement, X, cond) \
	do { \
		if ((statement) cond) { \
			return X; \
		} \
	} while(0);
#define M1_M1(stmt)   RETURN_X_IF_COND(stmt,   -1, == -1)
#define M1_N(stmt)    RETURN_X_IF_COND(stmt,   -1, == NULL)
#define M1_NZ(stmt)   RETURN_X_IF_COND(stmt,   -1, != 0)
#define M1_Z(stmt)    RETURN_X_IF_COND(stmt,   -1, == 0)
#define N_M1(stmt)    RETURN_X_IF_COND(stmt, NULL, == -1)
#define N_N(stmt)     RETURN_X_IF_COND(stmt, NULL, == NULL)
#define N_Z(stmt)     RETURN_X_IF_COND(stmt, NULL, == 0)
#define N_NZ(stmt)    RETURN_X_IF_COND(stmt, NULL, != 0)
#define Z_M1(stmt)    RETURN_X_IF_COND(stmt,    0, == -1)
#define Z_N(stmt)     RETURN_X_IF_COND(stmt,    0, == NULL)
#define Z_NZ(stmt)    RETURN_X_IF_COND(stmt,    0, != 0)
#define X_LZ(stmt, X) RETURN_X_IF_COND(stmt,    X, < 0)
#define X_N(stmt, X)  RETURN_X_IF_COND(stmt,    X, == NULL)

/*
 * A structure (and variable) holding utf-8 strings with the event names
 * This way we avoid calculating them every time, and we can compare them
 * via direct equality comparison instead of via strcmp.
 */
typedef struct _event_names {
	PyObject *null_ename;
	PyObject *boolean_ename;
	PyObject *integer_ename;
	PyObject *double_ename;
	PyObject *number_ename;
	PyObject *string_ename;
	PyObject *start_map_ename;
	PyObject *map_key_ename;
	PyObject *end_map_ename;
	PyObject *start_array_ename;
	PyObject *end_array_ename;
} enames_t;

extern enames_t enames;
extern PyObject *dot, *item, *dotitem;

extern PyObject *JSONError;
extern PyObject *IncompleteJSONError;
extern PyObject *Decimal;

#define CORO_SEND(target_send, event) \
	{ \
		if (PyList_Check(target_send)) { \
			Z_M1(PyList_Append(target_send, event)); \
		} \
		else { \
			Z_N( PyObject_CallFunctionObjArgs(target_send, event, NULL) ); \
		} \
	}

/* Common function used by __iter__ method in coroutines/generators */
PyObject* ijson_return_self(PyObject *self);

/* Common function used by empty methods in coroutines/generators */
PyObject* ijson_return_none(PyObject *self);

#endif /* COMMON_H */