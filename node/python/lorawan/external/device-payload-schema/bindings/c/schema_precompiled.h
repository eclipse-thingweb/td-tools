/*
 * schema_precompiled.h - FFI wrapper for precompiled (generated) codecs
 *
 * Precompiled codecs are 5-10x faster than interpreted schemas because:
 * - No runtime schema parsing
 * - Direct struct access, no field lookup
 * - Compiler optimizations (inlining, SIMD)
 *
 * Usage:
 *   1. Generate C codec: python tools/generate-c.py schema.yaml -o mycodec.h
 *   2. Include this header and generated codec
 *   3. Use codec_register() to register with FFI layer
 *   4. Call via standard FFI API
 *
 * Performance comparison:
 *   Interpreted schema: ~32M msg/s
 *   Precompiled codec:  ~200M msg/s
 */

#ifndef SCHEMA_PRECOMPILED_H
#define SCHEMA_PRECOMPILED_H

#include <stdint.h>
#include <stddef.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Maximum registered codecs */
#ifndef MAX_PRECOMPILED_CODECS
#define MAX_PRECOMPILED_CODECS 32
#endif

/* Maximum fields per codec */
#ifndef MAX_CODEC_FIELDS
#define MAX_CODEC_FIELDS 64
#endif

/* Field value types */
typedef enum {
    CODEC_VAL_INT = 0,
    CODEC_VAL_FLOAT,
    CODEC_VAL_STRING,
    CODEC_VAL_BOOL,
    CODEC_VAL_BYTES
} codec_val_type_t;

/* Decoded field value */
typedef struct {
    const char* name;
    codec_val_type_t type;
    union {
        int64_t  i64;
        double   f64;
        const char* str;
        struct { const uint8_t* data; size_t len; } bytes;
    } value;
} codec_field_t;

/* Decode result */
typedef struct {
    codec_field_t fields[MAX_CODEC_FIELDS];
    int field_count;
    int bytes_consumed;
    int error_code;
    const char* error_msg;
} codec_result_t;

/* Codec function signatures */
typedef int (*codec_decode_fn)(const uint8_t* data, size_t len, void* out);
typedef int (*codec_encode_fn)(const void* in, uint8_t* out, size_t max_len);
typedef int (*codec_to_fields_fn)(const void* decoded, codec_result_t* result);

/* Registered codec entry */
typedef struct {
    const char* name;
    size_t struct_size;
    codec_decode_fn decode;
    codec_encode_fn encode;
    codec_to_fields_fn to_fields;
} codec_entry_t;

/* Registry */
static codec_entry_t codec_registry[MAX_PRECOMPILED_CODECS];
static int codec_count = 0;

/* ============================================
 * Registration API
 * ============================================ */

/* Register a precompiled codec */
static inline int codec_register(
    const char* name,
    size_t struct_size,
    codec_decode_fn decode,
    codec_encode_fn encode,
    codec_to_fields_fn to_fields
) {
    if (codec_count >= MAX_PRECOMPILED_CODECS) return -1;
    
    codec_entry_t* e = &codec_registry[codec_count++];
    e->name = name;
    e->struct_size = struct_size;
    e->decode = decode;
    e->encode = encode;
    e->to_fields = to_fields;
    return codec_count - 1;
}

/* Find codec by name */
static inline codec_entry_t* codec_find(const char* name) {
    for (int i = 0; i < codec_count; i++) {
        if (strcmp(codec_registry[i].name, name) == 0) {
            return &codec_registry[i];
        }
    }
    return NULL;
}

/* Get codec by index */
static inline codec_entry_t* codec_get(int index) {
    if (index < 0 || index >= codec_count) return NULL;
    return &codec_registry[index];
}

/* Get codec count */
static inline int codec_get_count(void) {
    return codec_count;
}

/* ============================================
 * Helper macros for generated codecs
 * ============================================ */

/* Add integer field to result */
#define CODEC_ADD_INT(result, fname, val) do { \
    codec_field_t* f = &(result)->fields[(result)->field_count++]; \
    f->name = fname; \
    f->type = CODEC_VAL_INT; \
    f->value.i64 = (int64_t)(val); \
} while(0)

/* Add float field to result */
#define CODEC_ADD_FLOAT(result, fname, val) do { \
    codec_field_t* f = &(result)->fields[(result)->field_count++]; \
    f->name = fname; \
    f->type = CODEC_VAL_FLOAT; \
    f->value.f64 = (double)(val); \
} while(0)

/* Add string field to result */
#define CODEC_ADD_STRING(result, fname, val) do { \
    codec_field_t* f = &(result)->fields[(result)->field_count++]; \
    f->name = fname; \
    f->type = CODEC_VAL_STRING; \
    f->value.str = (val); \
} while(0)

/* Add bool field to result */
#define CODEC_ADD_BOOL(result, fname, val) do { \
    codec_field_t* f = &(result)->fields[(result)->field_count++]; \
    f->name = fname; \
    f->type = CODEC_VAL_BOOL; \
    f->value.i64 = (val) ? 1 : 0; \
} while(0)

#ifdef __cplusplus
}
#endif

#endif /* SCHEMA_PRECOMPILED_H */
