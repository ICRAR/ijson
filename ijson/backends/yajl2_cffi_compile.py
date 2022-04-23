"""
CFFI-Wrapper for YAJL C library version 2.x.

New ffi.compile() style, with separate wrapper .py
"""

from cffi import FFI

ffi = FFI()
ffi.cdef(
    """
typedef void * (*yajl_malloc_func)(void *ctx, size_t sz);
typedef void (*yajl_free_func)(void *ctx, void * ptr);
typedef void * (*yajl_realloc_func)(void *ctx, void * ptr, size_t sz);
typedef struct
{
    yajl_malloc_func malloc;
    yajl_realloc_func realloc;
    yajl_free_func free;
    void * ctx;
} yajl_alloc_funcs;
typedef struct yajl_handle_t * yajl_handle;
typedef enum {
    yajl_status_ok,
    yajl_status_client_canceled,
    yajl_status_error
} yajl_status;
typedef enum {
    yajl_allow_comments = 0x01,
    yajl_dont_validate_strings     = 0x02,
    yajl_allow_trailing_garbage = 0x04,
    yajl_allow_multiple_values = 0x08,
    yajl_allow_partial_values = 0x10
} yajl_option;
typedef struct {
    int (* yajl_null)(void * ctx);
    int (* yajl_boolean)(void * ctx, int boolVal);
    int (* yajl_integer)(void * ctx, long long integerVal);
    int (* yajl_double)(void * ctx, double doubleVal);
    int (* yajl_number)(void * ctx, const char * numberVal,
                        size_t numberLen);
    int (* yajl_string)(void * ctx, const unsigned char * stringVal,
                        size_t stringLen);
    int (* yajl_start_map)(void * ctx);
    int (* yajl_map_key)(void * ctx, const unsigned char * key,
                         size_t stringLen);
    int (* yajl_end_map)(void * ctx);
    int (* yajl_start_array)(void * ctx);
    int (* yajl_end_array)(void * ctx);
} yajl_callbacks;
int yajl_version(void);
yajl_handle yajl_alloc(const yajl_callbacks *callbacks, yajl_alloc_funcs *afs, void *ctx);
int yajl_config(yajl_handle h, yajl_option opt, ...);
yajl_status yajl_parse(yajl_handle hand, const unsigned char *jsonText, size_t jsonTextLength);
yajl_status yajl_complete_parse(yajl_handle hand);
unsigned char* yajl_get_error(yajl_handle hand, int verbose, const unsigned char *jsonText, size_t jsonTextLength);
void yajl_free_error(yajl_handle hand, unsigned char * str);
void yajl_free(yajl_handle handle);
size_t yajl_get_bytes_consumed (yajl_handle hand);
"""
)

# 'extern Python' callbacks
ffi.cdef(
    """
extern "Python" int (yajl_null)(void *ctx);
extern "Python" int (yajl_boolean)(void * ctx, int boolVal);
extern "Python" int (yajl_integer)(void * ctx, long long integerVal);
extern "Python" int (yajl_double)(void * ctx, double doubleVal);
/** A callback which passes the string representation of the number
  * back to the client.  Will be used for all numbers when present */
extern "Python" int (yajl_number)(void * ctx, const char * numberVal,
                    size_t numberLen);

/** strings are returned as pointers into the JSON text when,
  * possible, as a result, they are _not_ null padded */
extern "Python" int (yajl_string)(void * ctx, const unsigned char * stringVal,
                    size_t stringLen);

extern "Python" int (yajl_start_map)(void * ctx);
extern "Python" int (yajl_map_key)(void * ctx, const unsigned char * key,
                        size_t stringLen);
extern "Python" int (yajl_end_map)(void * ctx);

extern "Python" int (yajl_start_array)(void * ctx);
extern "Python" int (yajl_end_array)(void * ctx);
"""
)


if __name__ == "__main__":
    ffi.set_source(
        "_yajl2_cffi",
        """
#include <yajl/yajl_common.h>
#include <yajl/yajl_version.h>
#include <yajl/yajl_parse.h>
    """,
        libraries=["yajl"],
    )
    ffi.compile(verbose=True)
