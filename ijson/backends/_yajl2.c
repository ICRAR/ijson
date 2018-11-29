/*
 * C extension to bind yajl to ijson
 *
 * Contributed by Rodrigo Tobar <rtobar@icrar.org>
 *
 * ICRAR - International Centre for Radio Astronomy Research
 * (c) UWA - The University of Western Australia, 2016
 * Copyright by UWA (in the framework of the ICRAR)
 */

#include <errno.h>

#include <Python.h>
#include <yajl/yajl_common.h>
#include <yajl/yajl_parse.h>

#define STRING_FROM_UTF8(val, len) PyUnicode_FromStringAndSize((const char *)val, len)


/*
 * Error-handling macros to help reducing clutter in the code.
 * N: NULL, M1: -1, Z: zero, NZ: not-zero, LZ: less-than-zero
 * */
#define RETURN_X_IF_COND(statement, X, cond) \
	do { \
		if( (statement) cond ) { \
			return X; \
		} \
	} while(0);
#define M1_M1(stmt)   RETURN_X_IF_COND(stmt,   -1, == -1)
#define M1_N(stmt)    RETURN_X_IF_COND(stmt,   -1, == NULL)
#define M1_NZ(stmt)   RETURN_X_IF_COND(stmt,   -1, != 0)
#define M1_Z(stmt)    RETURN_X_IF_COND(stmt,   -1, == 0)
#define N_M1(stmt)    RETURN_X_IF_COND(stmt, NULL, == -1)
#define N_N(stmt)     RETURN_X_IF_COND(stmt, NULL, == NULL)
#define Z_M1(stmt)    RETURN_X_IF_COND(stmt,    0, == -1)
#define Z_N(stmt)     RETURN_X_IF_COND(stmt,    0, == NULL)
#define Z_NZ(stmt)    RETURN_X_IF_COND(stmt,    0, != 0)
#define X_LZ(stmt, X) RETURN_X_IF_COND(stmt,    X, < 0)
#define X_N(stmt, X)  RETURN_X_IF_COND(stmt,    X, == NULL)

/*
 * A structure (and variable) holding utf-8 strings with the event names
 * This was we avoid calculating them every time
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
static enames_t enames;

/*
 * The YAJL callbacks, they add (evt,value) to a list
 */
static inline
int add_event_and_value(void *ctx, PyObject *evt_name, PyObject *val) {
	PyObject *tuple;
	Z_N(tuple = PyTuple_New(2));
	Py_INCREF(evt_name); // this is an element of our static enames var
	Z_NZ( PyTuple_SetItem(tuple, 0, evt_name) );
	Z_NZ( PyTuple_SetItem(tuple, 1, val) );
	PyObject *events = (PyObject *)((void **)ctx)[0];
	Z_M1( PyList_Append(events, tuple) );
	Py_DECREF(tuple);
	return 1;
}

static int null(void * ctx) {
	Py_INCREF(Py_None);
	return add_event_and_value(ctx, enames.null_ename, Py_None);
}

static int boolean(void * ctx, int val) {
	PyObject *bval = val == 0 ? Py_False : Py_True;
	Py_INCREF(bval);
	return add_event_and_value(ctx, enames.boolean_ename, bval);
}

static int integer(void * ctx, long long integerVal) {
	PyObject *val;
	Z_N(val = PyLong_FromLongLong(integerVal));
	return add_event_and_value(ctx, enames.integer_ename, val);
}

static int double_cb(void * ctx, double doubleVal) {
	PyObject *val;
	Z_N(val = PyFloat_FromDouble(doubleVal));
	return add_event_and_value(ctx, enames.double_ename, val);
}

static int number(void * ctx, const char *numberVal, size_t numberLen) {

	// If original string has a dot or an "e/E" we return a Decimal
	// just like in the common module
	int is_decimal = 0;
	const char *iter = numberVal;
	size_t i;
	for(i=0; i!=numberLen; i++) {
		char c = *iter++;
		if( c == '.' || c == 'e' || c == 'E' ) {
			is_decimal = 1;
			break;
		}
	}

	PyObject *val;
	if( !is_decimal ) {
		char *nval = (char *)malloc(numberLen + 1);
		memcpy(nval, numberVal, numberLen);
		nval[numberLen] = 0;
		char *endptr;
#if PY_MAJOR_VERSION >= 3
		Z_N(val = PyLong_FromString(nval, &endptr, 10));
#else
		// returns either PyLong or PyInt
		Z_N(val = PyInt_FromString(nval, &endptr, 10));
#endif
		free(nval);
		if( endptr == nval ) {
			// not properly parsed (improbable, the parser should give us good stuff)
			PyErr_SetString(PyExc_ValueError, "cannot convert string to double");
			return 0;
		}
	}
	else {
		PyObject *args;
		Z_N(args = Py_BuildValue("(s#)", numberVal, numberLen));
		PyObject *decimal = (PyObject *)((void **)(ctx))[1];
		Z_N(val = PyObject_Call(decimal, args, NULL));
		Py_DECREF(args);
	}

	return add_event_and_value(ctx, enames.number_ename, val);
}

static int string_cb(void * ctx, const unsigned char *stringVal, size_t stringLen) {
	PyObject *val;
	Z_N(val = PyUnicode_FromStringAndSize((char *)stringVal, stringLen))
	return add_event_and_value(ctx, enames.string_ename, val);
}

static int start_map(void *ctx) {
	Py_INCREF(Py_None);
	return add_event_and_value(ctx, enames.start_map_ename, Py_None);
}

static int map_key(void *ctx, const unsigned char *key, size_t stringLen) {
	PyObject *val;
	Z_N(val = STRING_FROM_UTF8(key, stringLen))
	return add_event_and_value(ctx, enames.map_key_ename, val);
}

static int end_map(void *ctx) {
	Py_INCREF(Py_None);
	return add_event_and_value(ctx, enames.end_map_ename, Py_None);
}

static int start_array(void *ctx) {
	Py_INCREF(Py_None);
	return add_event_and_value(ctx, enames.start_array_ename, Py_None);
}

static int end_array(void *ctx) {
	Py_INCREF(Py_None);
	return add_event_and_value(ctx, enames.end_array_ename, Py_None);
}

static yajl_callbacks callbacks = {
	null, boolean, integer, double_cb, number, string_cb,
	start_map, map_key, end_map, start_array, end_array
};


/*
 * basic_parse generator object structure
 */
typedef struct {
	PyObject_HEAD
	yajl_handle h;
	void *ctx;
	PyObject *JSONError;
	PyObject *IncompleteJSONError;
	PyObject *read;
	Py_ssize_t buf_size;
	Py_ssize_t pos;
	int finished;
} BasicParseGen;


/*
 * __init__, destructor, __iter__ and __next__
 */
static int basicparse_init(BasicParseGen *self, PyObject *args, PyObject *kwargs) {

	Py_ssize_t buf_size = 64*1024;
	PyObject *read = NULL; /* the read method */
	PyObject *decimal = NULL; /* The decimal.Decimal constructor */
	PyObject *allow_comments = Py_False;
	PyObject *multiple_values = Py_False;

	self->h = NULL;
	self->JSONError = NULL;
	self->IncompleteJSONError = NULL;
	self->read = NULL;
	self->buf_size = 0;
	self->pos = 0;
	self->finished = 0;

	char *kwlist[] = {"read", "decimal", "jsonerror", "incompletejsonerror",
					  "buf_size", "allow_comments", "multiple_values",
					  NULL};
	if( !PyArg_ParseTupleAndKeywords(args, kwargs, "OOOO|nOO", kwlist,
									 &read,
									 &decimal,
									 &(self->JSONError),
									 &(self->IncompleteJSONError),
									 &buf_size,
									 &allow_comments,
									 &multiple_values) ) {
		return -1;
	}

	/*
	 * Prepare yajl handle and configure it
	 * In the context we put a two-element pointer array containing
	 * the list of events and a reference to the decimal.Decimal class
	 * (used by the numeric callback)
	 */
	PyObject *events;
	yajl_handle handle;
	M1_N(events = PyList_New(0));

	void **ctx = (void **)malloc(2 * sizeof(void *));
	if( ctx == NULL ) {
		PyErr_SetString(PyExc_MemoryError, "Not enough memory to create context");
		return -1;
	}
	ctx[0] = (void *)events;
	ctx[1] = (void *)decimal;
	self->ctx = ctx;

	M1_N(handle = yajl_alloc(&callbacks, NULL, ctx));
	if( PyObject_IsTrue(allow_comments) ) {
		yajl_config(handle, yajl_allow_comments, 1);
	}
	if (PyObject_IsTrue(multiple_values)) {
		yajl_config(handle, yajl_allow_multiple_values, 1);
	}

	Py_INCREF(decimal);
	Py_INCREF(read);
	Py_INCREF(self->JSONError);
	Py_INCREF(self->IncompleteJSONError);
	self->h = handle;
	self->buf_size = buf_size;
	self->read = read;

	return 0;
}

static void basicparsegen_dealloc(BasicParseGen *self) {
	if( self->h ) {
		yajl_free(self->h);
	}
	Py_XDECREF(self->JSONError);
	Py_XDECREF(self->IncompleteJSONError);
	Py_XDECREF(self->read);
	if( self->ctx ) {
		PyObject *events = (PyObject *)((void **)self->ctx)[0];
		PyObject *decimal = (PyObject *)((void **)(self->ctx))[1];
		Py_XDECREF(events);
		Py_XDECREF(decimal);
		free(self->ctx);
	}
	Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject* basicparsegen_iter(PyObject *self) {
	Py_INCREF(self);
	return self;
}

static inline
yajl_status parse(BasicParseGen *gen, char *buf, Py_ssize_t buflen) {
	if( buflen == 0 ) {
		gen->finished = 1;
		return yajl_complete_parse(gen->h);
	}
	return yajl_parse(gen->h, (unsigned char *)buf, buflen);
}

static int basicparsegen_fill_events(BasicParseGen *gen) {

	char *buf;
	Py_ssize_t buflen;

	PyObject *args = Py_BuildValue("(n)", gen->buf_size);
	PyObject *pbuffer = PyObject_Call(gen->read, args, NULL);
	Py_DECREF(args);
	M1_N(pbuffer);

	int conv = PyBytes_AsStringAndSize(pbuffer, &buf, &buflen);
	if( conv < 0 ) {
		Py_DECREF(pbuffer);
		return -1;
	}

	yajl_status status = parse(gen, buf, buflen);
	Py_DECREF(pbuffer);

	if( status != yajl_status_ok ) {
		// Python-related error on the callbacks?
		if( status == yajl_status_client_canceled ) {
			return -1;
		}
		// naaah, it was truly a JSON problem
		unsigned char *perror = yajl_get_error(gen->h, 1, (unsigned char *)buf, buflen);
		PyErr_SetString(gen->IncompleteJSONError, (char *)perror);
		yajl_free_error(gen->h, perror);
		return -1;
	}

	return 0;
}

static PyObject* basicparsegen_iternext(PyObject *self) {

	/* Preempt our execution, which might be very long */
	N_M1(PyErr_CheckSignals());

	BasicParseGen *gen = (BasicParseGen *)self;

	/* Fill the events list if needed */
	PyObject *events = (PyObject *)((void **)gen->ctx)[0];
	Py_ssize_t nevents = PyList_Size(events);
	while( !gen->finished && nevents == 0 ) {
		N_M1(basicparsegen_fill_events(gen));
		nevents = PyList_Size(events);
		if( nevents != 0 ) {
			break;
		}
	}

	// events are now probably available
	if( nevents > 0 ) {
		PyObject *val = PyList_GetItem(events, gen->pos++);
		Py_INCREF(val);

		/* empty the list if fully iterated over */
		if( gen->pos == nevents ) {
			gen->pos = 0;
			N_M1(PySequence_DelSlice(events, 0, nevents));
		}
		return val;
	}

	// no events, let's end the show
	PyErr_SetNone(PyExc_StopIteration);
	return NULL;
}

/*
 * basic_parse generator object type
 */
static PyTypeObject BasicParseGen_Type = {
#if PY_MAJOR_VERSION >= 3
	PyVarObject_HEAD_INIT(NULL, 0)
#else
	PyObject_HEAD_INIT(NULL)
	0,                            /*ob_size*/
#endif
	"_yajl2.basic_parse",         /*tp_name*/
	sizeof(BasicParseGen),        /*tp_basicsize*/
	0,                            /*tp_itemsize*/
	(destructor)basicparsegen_dealloc, /*tp_dealloc*/
	0,                            /*tp_print*/
	0,                            /*tp_getattr*/
	0,                            /*tp_setattr*/
	0,                            /*tp_compare*/
	0,                            /*tp_repr*/
	0,                            /*tp_as_number*/
	0,                            /*tp_as_sequence*/
	0,                            /*tp_as_mapping*/
	0,                            /*tp_hash */
	0,                            /*tp_call*/
	0,                            /*tp_str*/
	0,                            /*tp_getattro*/
	0,                            /*tp_setattro*/
	0,                            /*tp_as_buffer*/
#if PY_MAJOR_VERSION >= 3
#define Py_TPFLAGS_HAVE_ITER 0
#endif
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_ITER, /*tp_flags*/
	"Generator of (evt,value)",   /*tp_doc*/
	0,                            /*tp_traverse*/
	0,                            /*tp_clear*/
	0,                            /*tp_richcompare*/
	0,                            /*tp_weaklistoffset*/
	basicparsegen_iter,           /*tp_iter: __iter__() method*/
	basicparsegen_iternext,       /*tp_iternext: next() method*/
	0,                            /*tp_methods*/
	0,                            /*tp_members*/
	0,                            /*tp_getset*/
	0,                            /*tp_base*/
	0,                            /*tp_dict*/
	0,                            /*tp_descr_get*/
	0,                            /*tp_descr_set*/
	0,                            /*tp_dictoffset*/
	(initproc)basicparse_init    /*tp_init*/
};


/*
 * parse generator object structure
 */
typedef struct {
	BasicParseGen basic_parse;
	PyObject *path;
} ParseGen;


/*
 * __init__, destructor, __iter__ and __next__
 */
static int parsegen_init(ParseGen *self, PyObject *args, PyObject *kwargs) {
	if( BasicParseGen_Type.tp_init((PyObject *)self, args, kwargs) < 0 ) {
		return -1;
	}
	M1_N(self->path = PyList_New(0));

	PyObject *empty;
	M1_N(empty = STRING_FROM_UTF8("", 0));
	int res = PyList_Append(self->path, empty);
	Py_DECREF(empty);
	M1_M1( res );

	return 0;
}

static void parsegen_dealloc(ParseGen *self) {
	Py_XDECREF(self->path);
	BasicParseGen_Type.tp_dealloc((PyObject *)self);
}

static PyObject* parsegen_iter(PyObject *self) {
	Py_INCREF(self);
	return self;
}

#define CONCAT(tgt, first, second) \
	do { \
		tgt = PyUnicode_Concat(first, second); \
		Py_DECREF(first); \
		N_N(tgt); \
	} while(0);

static PyObject *dot, *item, *dotitem;
static PyObject* parsegen_iternext(PyObject *self) {

	// unpack
	PyObject *res;
	N_N(res = BasicParseGen_Type.tp_iternext(self));
	PyObject *event = PyTuple_GetItem(res, 0);
	PyObject *value = PyTuple_GetItem(res, 1);
	Py_INCREF(event);
	Py_INCREF(value);
	Py_DECREF(res);

	ParseGen *gen = (ParseGen *)self;
	Py_ssize_t npaths = PyList_Size(gen->path);

	PyObject *prefix;
	if( event == enames.end_array_ename || event == enames.end_map_ename ) {
		// pop
		N_M1(PyList_SetSlice(gen->path, npaths-1, npaths, NULL));
		npaths--;
		N_N(prefix = PySequence_GetItem(gen->path, npaths-1));
	}
	else if( event == enames.map_key_ename ) {

		// last_path = path_stack[-2]
		// to_append = '.' + value if len(path_stack) > 1 else value
		// new_path = path_stack[-2] + to_append
		PyObject *last_path;
		N_N(last_path = PySequence_GetItem(gen->path, npaths-2));
		if( npaths > 2 ) {
			PyObject *last_path_dot;
			CONCAT(last_path_dot, last_path, dot);
			last_path = last_path_dot;
		}
		PyObject *new_path;
		CONCAT(new_path, last_path, value);
		PyList_SetItem(gen->path, npaths-1, new_path);

		N_N(prefix = PySequence_GetItem(gen->path, npaths-2));
	}
	else {
		N_N(prefix = PySequence_GetItem(gen->path, npaths-1));
	}

	// The tuple we'll return
	res = PyTuple_New(3);
	PyTuple_SetItem(res, 0, prefix);
	PyTuple_SetItem(res, 1, event);
	PyTuple_SetItem(res, 2, value);

	if( event == enames.start_array_ename ) {

		// to_append = '.item' if path_stack[-1] else 'item'
		// path_stack.append(path_stack[-1] + to_append)
		PyObject *last_path;
		N_N(last_path = PySequence_GetItem(gen->path, npaths-1));

		PyObject *new_path;
		if( PyUnicode_GET_SIZE(last_path) > 0 ) {
			CONCAT(new_path, last_path, dotitem);
		}
		else {
			CONCAT(new_path, last_path, item);
		}

		int ret = PyList_Append(gen->path, new_path);
		Py_DECREF(new_path);
		N_M1(ret);
	}
	else if( event == enames.start_map_ename ) {
		N_M1(PyList_Append(gen->path, Py_None));
	}

	return res;
}

/*
 * parse generator object type
 */
static PyTypeObject ParseGen_Type = {
#if PY_MAJOR_VERSION >= 3
	PyVarObject_HEAD_INIT(NULL, 0)
#else
	PyObject_HEAD_INIT(NULL)
	0,                            /*ob_size*/
#endif
	"_yajl2.parse",               /*tp_name*/
	sizeof(ParseGen),             /*tp_basicsize*/
	0,                            /*tp_itemsize*/
	(destructor)parsegen_dealloc, /*tp_dealloc*/
	0,                            /*tp_print*/
	0,                            /*tp_getattr*/
	0,                            /*tp_setattr*/
	0,                            /*tp_compare*/
	0,                            /*tp_repr*/
	0,                            /*tp_as_number*/
	0,                            /*tp_as_sequence*/
	0,                            /*tp_as_mapping*/
	0,                            /*tp_hash */
	0,                            /*tp_call*/
	0,                            /*tp_str*/
	0,                            /*tp_getattro*/
	0,                            /*tp_setattro*/
	0,                            /*tp_as_buffer*/
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_ITER, /*tp_flags*/
	"Generates (path,evt,value)", /*tp_doc*/
	0,                            /*tp_traverse*/
	0,                            /*tp_clear*/
	0,                            /*tp_richcompare*/
	0,                            /*tp_weaklistoffset*/
	parsegen_iter,                /*tp_iter: __iter__() method*/
	parsegen_iternext,            /*tp_iternext: next() method*/
	0,                            /*tp_methods*/
	0,                            /*tp_members*/
	0,                            /*tp_getset*/
	&BasicParseGen_Type,          /*tp_base*/
	0,                            /*tp_dict*/
	0,                            /*tp_descr_get*/
	0,                            /*tp_descr_set*/
	0,                            /*tp_dictoffset*/
	(initproc)parsegen_init       /*tp_init*/
};


/*
 * Builder structure and methods
 *
 * This is the parallel of the ObjectBuilder class from the common module,
 * only a bit more complicated since it's all C
 */
typedef struct _builder {
	PyObject *value;
	int active;
	PyObject *key;
	PyObject *value_stack;
	PyObject *map_type;
} builder_t;

static inline
builder_t *builder_create(PyObject *map_type) {

	PyObject *value_stack;
	N_N(value_stack = PyList_New(0));

	builder_t *builder = (builder_t *)calloc(sizeof(builder_t), 1);
	if( !builder ) {
		PyErr_SetString(PyExc_MemoryError, "Not enough memory to create builder object");
		return NULL;
	}

	builder->value_stack = value_stack;
	if (map_type != Py_None) {
		builder->map_type = map_type;
		Py_INCREF(map_type);
	}
	return builder;
}

void builder_destroy(builder_t *builder) {
	Py_DECREF(builder->value_stack);
	Py_XDECREF(builder->map_type);
	free(builder);
}

static inline
int builder_isactive(builder_t *builder) {
	return builder->active;
}

static inline
PyObject *builder_value(builder_t *builder) {
	Py_INCREF(builder->value);
	return builder->value;
}

static inline
int builder_reset(builder_t *builder) {

	builder->active = 0;

	Py_XDECREF(builder->value);
	Py_XDECREF(builder->key);
	builder->key = NULL;
	builder->value = NULL;

	Py_ssize_t nvals = PyList_Size(builder->value_stack);
	M1_M1( PyList_SetSlice(builder->value_stack, 0, nvals, NULL) );

	return 0;
}

static inline
int builder_add(builder_t *builder, PyObject *value) {

	Py_ssize_t nvals = PyList_Size(builder->value_stack);
	if( nvals == 0 ) {
		Py_INCREF(value);
		builder->value = value;
	}
	else {
		PyObject *last;
		M1_N(last = PyList_GetItem(builder->value_stack, nvals-1));
		if( PyList_Check(last) ) {
			M1_M1( PyList_Append(last, value) );
		}
		else if (PyMapping_Check(last)) { // it's a dict-like object
			M1_M1( PyObject_SetItem(last, builder->key, value) );
		}
		else {
			PyErr_SetString(PyExc_TypeError, "Incorrect type found in value_stack");
			return -1;
		}
	}

	return 0;
}

static inline
int builder_event(builder_t *builder, PyObject *ename, PyObject *value) {
	builder->active = 1;

	if( ename == enames.map_key_ename ) {
		Py_XDECREF(builder->key);
		builder->key = value;
		Py_INCREF(builder->key);
	}
	else if( ename == enames.start_map_ename ) {
		PyObject *mappable;
		if (builder->map_type) {
			mappable = PyObject_CallFunctionObjArgs(builder->map_type, NULL);
		}
		else {
			mappable = PyDict_New();
		}
		M1_N(mappable);
		M1_M1( builder_add(builder, mappable) );
		M1_M1( PyList_Append(builder->value_stack, mappable) );
		Py_DECREF(mappable);
	}
	else if( ename == enames.start_array_ename ) {
		PyObject *list;
		M1_N(list = PyList_New(0));
		M1_M1( builder_add(builder, list) );
		M1_M1( PyList_Append(builder->value_stack, list) );
		Py_DECREF(list);
	}
	else if( ename == enames.end_array_ename || ename == enames.end_map_ename) {
		// pop
		Py_ssize_t nvals = PyList_Size(builder->value_stack);
		M1_M1( PyList_SetSlice(builder->value_stack, nvals-1, nvals, NULL) );
	}
	else {
		M1_M1( builder_add(builder, value) );
	}

	return 0;
}

/*
 * parse generator object structure
 */
typedef struct {
	ParseGen parse;
	builder_t *builder;
	PyObject *prefix;
	PyObject *end_event;
} ItemsGen;


/*
 * __init__, destructor, __iter__ and __next__
 */
static int itemsgen_init(ItemsGen *self, PyObject *args, PyObject *kwargs) {

	self->builder = NULL;
	self->prefix = NULL;
	self->end_event = NULL;

	PyObject *read, *decimal, *jsonerror, *jsonincompleteerror, *map_type;
	int ret = PyArg_ParseTuple(args, "OOOOOO", &(self->prefix), &read, &decimal, &jsonerror, &jsonincompleteerror, &map_type);
	M1_Z(ret);

	// call super.__init__ with everything except self->prefix
	Py_INCREF(self->prefix);
	Py_INCREF(decimal);
	Py_INCREF(read);
	Py_INCREF(jsonerror);
	Py_INCREF(jsonincompleteerror);
	PyObject *subargs;
	M1_N(subargs = PyTuple_New(4));
	M1_NZ( PyTuple_SetItem(subargs, 0, read) );
	M1_NZ( PyTuple_SetItem(subargs, 1, decimal) );
	M1_NZ( PyTuple_SetItem(subargs, 2, jsonerror) );
	M1_NZ( PyTuple_SetItem(subargs, 3, jsonincompleteerror) );
	ret = ParseGen_Type.tp_init((PyObject *)self, subargs, kwargs);
	Py_DECREF(subargs);
	M1_M1(ret);

	M1_N(self->builder = builder_create(map_type));
	Py_INCREF(Py_None);
	return 0;
}

static void itemsgen_dealloc(ItemsGen *self) {
	Py_XDECREF(self->prefix);
	if( self->builder ) {
		builder_destroy(self->builder);
	}
	ParseGen_Type.tp_dealloc((PyObject *)self);
}

static PyObject* itemsgen_iter(PyObject *self) {
	Py_INCREF(self);
	return self;
}

static PyObject* itemsgen_iternext(PyObject *self) {

	ItemsGen *gen = (ItemsGen *)self;

	while( 1 ) {

		/* for path,event,value in parse(): */
		PyObject *res;
		N_N(res = ParseGen_Type.tp_iternext(self));
		PyObject *path  = PyTuple_GetItem(res, 0);
		PyObject *event = PyTuple_GetItem(res, 1);
		PyObject *value = PyTuple_GetItem(res, 2);
		Py_INCREF(path);
		Py_INCREF(event);
		Py_INCREF(value);
		Py_DECREF(res);

		PyObject *retval = NULL;
		if( builder_isactive(gen->builder) ) {
			int cmp = PyObject_RichCompareBool(path, gen->prefix, Py_EQ);
			N_M1(cmp);
			if( event != gen->end_event || cmp == 0 ) {
				N_M1( builder_event(gen->builder, event, value) );
			}
			else {
				retval = builder_value(gen->builder);
				N_M1( builder_reset(gen->builder) );
			}
		}
		else {
			int cmp = PyObject_RichCompareBool(path, gen->prefix, Py_EQ);
			N_M1(cmp);
			if( cmp ) {
				if( event == enames.start_map_ename || event == enames.start_array_ename ) {
					gen->end_event = (event == enames.start_array_ename) ? enames.end_array_ename : enames.end_map_ename;
					N_M1( builder_event(gen->builder, event, value) );
				}
				else {
					Py_INCREF(value);
					retval = value;
				}
			}
		}

		Py_DECREF(path);
		Py_DECREF(event);
		Py_DECREF(value);
		if( retval ) {
			return retval;
		}
	}

}

/*
 * items generator object type
 */
static PyTypeObject ItemsGen_Type = {
#if PY_MAJOR_VERSION >= 3
	PyVarObject_HEAD_INIT(NULL, 0)
#else
	PyObject_HEAD_INIT(NULL)
	0,                            /*ob_size*/
#endif
	"_yajl2.items",               /*tp_name*/
	sizeof(ItemsGen),             /*tp_basicsize*/
	0,                            /*tp_itemsize*/
	(destructor)itemsgen_dealloc, /*tp_dealloc*/
	0,                            /*tp_print*/
	0,                            /*tp_getattr*/
	0,                            /*tp_setattr*/
	0,                            /*tp_compare*/
	0,                            /*tp_repr*/
	0,                            /*tp_as_number*/
	0,                            /*tp_as_sequence*/
	0,                            /*tp_as_mapping*/
	0,                            /*tp_hash */
	0,                            /*tp_call*/
	0,                            /*tp_str*/
	0,                            /*tp_getattro*/
	0,                            /*tp_setattro*/
	0,                            /*tp_as_buffer*/
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_ITER, /*tp_flags*/
	"Generates items",            /*tp_doc*/
	0,                            /*tp_traverse*/
	0,                            /*tp_clear*/
	0,                            /*tp_richcompare*/
	0,                            /*tp_weaklistoffset*/
	itemsgen_iter,                /*tp_iter: __iter__() method*/
	itemsgen_iternext,            /*tp_iternext: next() method*/
	0,                            /*tp_methods*/
	0,                            /*tp_members*/
	0,                            /*tp_getset*/
	&ParseGen_Type,               /*tp_base*/
	0,                            /*tp_dict*/
	0,                            /*tp_descr_get*/
	0,                            /*tp_descr_set*/
	0,                            /*tp_dictoffset*/
	(initproc)itemsgen_init       /*tp_init*/
};


static PyMethodDef yajl2_methods[] = {
	{NULL, NULL, 0, NULL}        /* Sentinel */
};

/* Module initialization */

/* Support for Python 2/3 */
#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef moduledef = {PyModuleDef_HEAD_INIT, "_yajl2", "wrapper for yajl2 methods", -1, yajl2_methods};
	#define MOD_INIT(name) PyMODINIT_FUNC PyInit_##name(void)
	#define MOD_DEF(m, name, doc, methods) \
		m = PyModule_Create(&moduledef);
	#define MOD_VAL(v) v
#else
	#define MOD_INIT(name) PyMODINIT_FUNC init##name(void)
	#define MOD_DEF(m, name, doc, methods) \
		m = Py_InitModule3(name, methods, doc);
	#define MOD_VAL(v)
#endif

MOD_INIT(_yajl2)
{
	PyObject *m;
	BasicParseGen_Type.tp_new = PyType_GenericNew;
	ParseGen_Type.tp_new = PyType_GenericNew;
	ItemsGen_Type.tp_new = PyType_GenericNew;
	X_LZ(PyType_Ready(&BasicParseGen_Type), MOD_VAL(NULL));
	X_LZ(PyType_Ready(&ParseGen_Type), MOD_VAL(NULL));
	X_LZ(PyType_Ready(&ItemsGen_Type), MOD_VAL(NULL));

	MOD_DEF(m, "_yajl2", "wrapper for yajl2 methods", yajl2_methods);
	X_N(m, MOD_VAL(NULL));

	Py_INCREF(&BasicParseGen_Type);
	Py_INCREF(&ParseGen_Type);
	Py_INCREF(&ItemsGen_Type);
	PyModule_AddObject(m, "basic_parse", (PyObject *)&BasicParseGen_Type);
	PyModule_AddObject(m, "parse", (PyObject *)&ParseGen_Type);
	PyModule_AddObject(m, "items", (PyObject *)&ItemsGen_Type);

	dot = STRING_FROM_UTF8(".", 1);
	item = STRING_FROM_UTF8("item", 4);
	dotitem = STRING_FROM_UTF8(".item", 5);
#define INIT_ENAME(x) enames.x##_ename = STRING_FROM_UTF8(#x, strlen(#x))
	INIT_ENAME(null);
	INIT_ENAME(boolean);
	INIT_ENAME(integer);
	INIT_ENAME(double);
	INIT_ENAME(number);
	INIT_ENAME(string);
	INIT_ENAME(start_map);
	INIT_ENAME(map_key);
	INIT_ENAME(end_map);
	INIT_ENAME(start_array);
	INIT_ENAME(end_array);

	return MOD_VAL(m);

}

