#ifndef ITEMS_COMMON_H
#define ITEMS_COMMON_H

#include "builder.h"
#include "module_state.h"

/**
 * common items/prefixed_items_basecoro coroutine object structure
 */
typedef struct {
	PyObject_HEAD
	builder_t builder;
	int pending_builder_reset;
	PyObject *target_send;
	PyObject *prefix;
	int object_depth;
	yajl2_state *module_state;
} ItemsCommonBasecoro;

static inline
PyObject* items_common_send_top(PyObject *self, PyObject *path, PyObject *event, PyObject *value)
{
	ItemsCommonBasecoro *coro = (ItemsCommonBasecoro *)self;
	enames_t enames = coro->module_state->enames;

	if (builder_isactive(&coro->builder)) {
		coro->object_depth += (event == enames.start_map_ename || event == enames.start_array_ename);
		coro->object_depth -= (event == enames.end_map_ename || event == enames.end_array_ename);
		if (coro->object_depth > 0) {
			N_M1( builder_event(&coro->builder, enames, event, value) );
		}
		else {
			PyObject *retval = builder_value(&coro->builder);
			coro->pending_builder_reset = 1;
			return retval;
		}
	}
	else {
		int cmp = PySet_Contains(coro->prefix, path);
		N_M1(cmp);
		if (cmp) {
			if (event == enames.start_map_ename || event == enames.start_array_ename) {
				coro->object_depth = 1;
				N_M1(builder_event(&coro->builder, enames, event, value));
			}
			else {
				Py_INCREF(value);
				return value;
			}
		}
	}

	Py_RETURN_NONE;
}

static inline
void items_common_send_bottom(PyObject *self, PyObject *retval)
{
	ItemsCommonBasecoro *coro = (ItemsCommonBasecoro *)self;

	Py_DECREF(retval);
	if (coro->pending_builder_reset) {
		builder_reset(&coro->builder);
		coro->pending_builder_reset = 0;
	}
}

#endif // ITEMS_COMMON_H
