/*
 * schema_ffi.h - FFI-friendly wrapper for schema interpreter
 *
 * Provides a simplified C API suitable for FFI bindings from:
 * - Python (ctypes/cffi)
 * - Go (CGO)
 * - Node.js (N-API/node-ffi)
 * - Rust (bindgen)
 *
 * Build as shared library:
 *   gcc -shared -fPIC -O2 -o libschema.so schema_ffi.c
 *   clang -shared -fPIC -O2 -o libschema.dylib schema_ffi.c  # macOS
 */

#ifndef SCHEMA_FFI_H
#define SCHEMA_FFI_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#ifdef _WIN32
  #ifdef SCHEMA_FFI_EXPORTS
    #define SCHEMA_API __declspec(dllexport)
  #else
    #define SCHEMA_API __declspec(dllimport)
  #endif
#else
  #define SCHEMA_API __attribute__((visibility("default")))
#endif

/* Opaque handle types for FFI safety */
typedef struct schema_handle* schema_t_ffi;
typedef struct result_handle* result_t_ffi;

/* Error codes */
#define SCHEMA_OK              0
#define SCHEMA_ERR_INVALID    -1
#define SCHEMA_ERR_PARSE      -2
#define SCHEMA_ERR_DECODE     -3
#define SCHEMA_ERR_MEMORY     -4
#define SCHEMA_ERR_OVERFLOW   -5

/* Field value types (matches internal enum) */
#define FIELD_VAL_INT    0
#define FIELD_VAL_FLOAT  1
#define FIELD_VAL_STRING 2
#define FIELD_VAL_BOOL   3
#define FIELD_VAL_BYTES  4

/* ============================================
 * Schema Management
 * ============================================ */

/* Create a new schema from binary data */
SCHEMA_API schema_t_ffi schema_create_binary(const uint8_t* data, size_t len);

/* Create a new schema from YAML string (if YAML parser linked) */
SCHEMA_API schema_t_ffi schema_create_yaml(const char* yaml_str);

/* Free a schema */
SCHEMA_API void schema_free(schema_t_ffi schema);

/* Get schema name */
SCHEMA_API const char* schema_get_name(schema_t_ffi schema);

/* Get field count */
SCHEMA_API int schema_get_field_count(schema_t_ffi schema);

/* ============================================
 * Decoding
 * ============================================ */

/* Decode a payload, returns result handle */
SCHEMA_API result_t_ffi schema_decode(schema_t_ffi schema, 
                                       const uint8_t* payload, 
                                       size_t payload_len);

/* Free a decode result */
SCHEMA_API void result_free(result_t_ffi result);

/* Get error code from result (0 = success) */
SCHEMA_API int result_get_error(result_t_ffi result);

/* Get error message */
SCHEMA_API const char* result_get_error_msg(result_t_ffi result);

/* Get number of decoded fields */
SCHEMA_API int result_get_field_count(result_t_ffi result);

/* Get bytes consumed */
SCHEMA_API int result_get_bytes_consumed(result_t_ffi result);

/* ============================================
 * Field Access
 * ============================================ */

/* Get field name by index */
SCHEMA_API const char* result_get_field_name(result_t_ffi result, int index);

/* Get field value type */
SCHEMA_API int result_get_field_type(result_t_ffi result, int index);

/* Get field value as int64 (for integer types) */
SCHEMA_API int64_t result_get_field_int(result_t_ffi result, int index);

/* Get field value as double (for float types) */
SCHEMA_API double result_get_field_float(result_t_ffi result, int index);

/* Get field value as string (for string types) */
SCHEMA_API const char* result_get_field_string(result_t_ffi result, int index);

/* Get field value as bool */
SCHEMA_API int result_get_field_bool(result_t_ffi result, int index);

/* ============================================
 * JSON Output (convenience)
 * ============================================ */

/* Convert result to JSON string (caller must free with schema_free_string) */
SCHEMA_API char* result_to_json(result_t_ffi result);

/* Free a string allocated by this library */
SCHEMA_API void schema_free_string(char* str);

/* ============================================
 * Version Info
 * ============================================ */

/* Get library version string */
SCHEMA_API const char* schema_version(void);

#ifdef __cplusplus
}
#endif

#endif /* SCHEMA_FFI_H */
