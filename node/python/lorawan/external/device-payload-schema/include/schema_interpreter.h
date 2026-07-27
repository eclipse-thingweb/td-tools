/*
 * schema_interpreter.h - Runtime Payload Schema Interpreter
 *
 * Decodes LoRaWAN payloads using schema definitions at runtime.
 * Portable C99, no dynamic memory allocation option available.
 *
 * Supports:
 * - Programmatic schema building (field_u8, field_s16, etc.)
 * - Binary schema loading (schema_load_binary)
 *
 * Binary schema format (compact, ~4 bytes/field):
 *   Header: 'P' 'S' version flags field_count
 *   Per field: type_byte mult_exp field_id[2] [options]
 *
 * Usage (programmatic):
 *   schema_t schema;
 *   schema_init(&schema);
 *   schema_add_field(&schema, &field_s16("temperature", ENDIAN_BIG));
 *   
 * Usage (binary):
 *   schema_t schema;
 *   schema_load_binary(&schema, binary_data, binary_len);
 *   
 *   decode_result_t result;
 *   schema_decode(&schema, payload, payload_len, &result);
 */

#ifndef SCHEMA_INTERPRETER_H
#define SCHEMA_INTERPRETER_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Configuration - adjust for your platform */
#ifndef SCHEMA_MAX_FIELDS
#define SCHEMA_MAX_FIELDS 32
#define SCHEMA_MAX_PAYLOAD 256
#endif

#ifndef SCHEMA_MAX_NAME_LEN
#define SCHEMA_MAX_NAME_LEN 32
#endif

#ifndef SCHEMA_MAX_CASES
#define SCHEMA_MAX_CASES 16
#endif

#ifndef SCHEMA_MAX_LOOKUP
#define SCHEMA_MAX_LOOKUP 16
#endif

/* ============================================
 * Type Definitions
 * ============================================ */

typedef enum {
    FIELD_TYPE_U8 = 0,
    FIELD_TYPE_U16,
    FIELD_TYPE_U24,
    FIELD_TYPE_U32,
    FIELD_TYPE_U64,
    FIELD_TYPE_S8,
    FIELD_TYPE_S16,
    FIELD_TYPE_S24,
    FIELD_TYPE_S32,
    FIELD_TYPE_S64,
    FIELD_TYPE_F16,     /* IEEE 754 half-precision */
    FIELD_TYPE_F32,
    FIELD_TYPE_F64,
    FIELD_TYPE_BOOL,
    FIELD_TYPE_BITS,
    FIELD_TYPE_SKIP,
    FIELD_TYPE_ASCII,
    FIELD_TYPE_HEX,
    FIELD_TYPE_BASE64,
    FIELD_TYPE_BYTES,
    FIELD_TYPE_OBJECT,
    FIELD_TYPE_MATCH,
    FIELD_TYPE_ENUM,
    FIELD_TYPE_BYTE_GROUP,
    FIELD_TYPE_UDEC,    /* Nibble-decimal: upper=whole, lower=tenths */
    FIELD_TYPE_SDEC,    /* Signed nibble-decimal */
    FIELD_TYPE_UNKNOWN
} field_type_t;

typedef enum {
    ENDIAN_DEFAULT = 0,    /* Not explicitly set - use schema default */
    ENDIAN_BIG = 1,
    ENDIAN_LITTLE = 2
} endian_t;

typedef union {
    int64_t  i64;
    uint64_t u64;
    double   f64;
    bool     b;
    char     str[SCHEMA_MAX_NAME_LEN];
    uint8_t  bytes[SCHEMA_MAX_NAME_LEN];
} field_value_t;

typedef struct {
    int key;
    char value[SCHEMA_MAX_NAME_LEN];
} lookup_entry_t;

typedef struct field_def field_def_t;

typedef struct {
    int match_value;           /* Single value or -1 for default */
    int match_list[8];         /* List of values, -1 terminated */
    int range_min, range_max;  /* Range match */
    bool is_default;
    int field_start;           /* Index into fields array */
    int field_count;
} case_def_t;

struct field_def {
    char name[SCHEMA_MAX_NAME_LEN];
    field_type_t type;
    uint8_t size;              /* Size in bytes (or bits for bitfield) */
    uint8_t bit_start;         /* Bit position for bitfields */
    uint8_t bit_width;         /* Bit width for bitfields */
    bool consume;              /* Whether to advance position */
    endian_t endian;
    
    /* Modifiers */
    double mult;
    double div;
    double add;
    bool has_mult, has_div, has_add;
    
    /* Variable storage */
    char var_name[SCHEMA_MAX_NAME_LEN];
    
    /* Lookup table */
    lookup_entry_t lookup[SCHEMA_MAX_LOOKUP];
    int lookup_count;
    
    /* For match type */
    char match_var[SCHEMA_MAX_NAME_LEN];
    case_def_t cases[SCHEMA_MAX_CASES];
    int case_count;
    
    /* For nested objects */
    int nested_start;
    int nested_count;
};

typedef struct {
    char name[SCHEMA_MAX_NAME_LEN];
    field_value_t value;
    field_type_t type;
    bool valid;
} decoded_field_t;

typedef struct {
    char name[SCHEMA_MAX_NAME_LEN];
    int version;
    endian_t endian;
    field_def_t fields[SCHEMA_MAX_FIELDS];
    int field_count;
} schema_t;

typedef struct {
    decoded_field_t fields[SCHEMA_MAX_FIELDS];
    int field_count;
    int bytes_consumed;
    int error_code;
    char error_msg[64];
} decode_result_t;

/* Variable storage for match conditions */
typedef struct {
    char name[SCHEMA_MAX_NAME_LEN];
    int64_t value;
} variable_t;

typedef struct {
    variable_t vars[SCHEMA_MAX_FIELDS];
    int count;
} var_context_t;

/* ============================================
 * Error Codes
 * ============================================ */

#define SCHEMA_OK              0
#define SCHEMA_ERR_PARSE      -1
#define SCHEMA_ERR_BUFFER     -2
#define SCHEMA_ERR_OVERFLOW   -3
#define SCHEMA_ERR_TYPE       -4
#define SCHEMA_ERR_MATCH      -5
#define SCHEMA_ERR_UNSUPPORTED -6
#define SCHEMA_ERR_MISSING    -7

/* ============================================
 * Byte Reading Utilities
 * ============================================ */

static inline uint8_t read_u8(const uint8_t* buf) {
    return buf[0];
}

static inline uint16_t read_u16_be(const uint8_t* buf) {
    return ((uint16_t)buf[0] << 8) | buf[1];
}

static inline uint16_t read_u16_le(const uint8_t* buf) {
    return ((uint16_t)buf[1] << 8) | buf[0];
}

static inline uint32_t read_u24_be(const uint8_t* buf) {
    return ((uint32_t)buf[0] << 16) | ((uint32_t)buf[1] << 8) | buf[2];
}

static inline uint32_t read_u24_le(const uint8_t* buf) {
    return ((uint32_t)buf[2] << 16) | ((uint32_t)buf[1] << 8) | buf[0];
}

static inline uint32_t read_u32_be(const uint8_t* buf) {
    return ((uint32_t)buf[0] << 24) | ((uint32_t)buf[1] << 16) |
           ((uint32_t)buf[2] << 8) | buf[3];
}

static inline uint32_t read_u32_le(const uint8_t* buf) {
    return ((uint32_t)buf[3] << 24) | ((uint32_t)buf[2] << 16) |
           ((uint32_t)buf[1] << 8) | buf[0];
}

static inline int8_t read_s8(const uint8_t* buf) {
    return (int8_t)buf[0];
}

static inline int16_t read_s16_be(const uint8_t* buf) {
    return (int16_t)read_u16_be(buf);
}

static inline int16_t read_s16_le(const uint8_t* buf) {
    return (int16_t)read_u16_le(buf);
}

static inline int32_t read_s24_be(const uint8_t* buf) {
    uint32_t val = read_u24_be(buf);
    if (val & 0x800000) val |= 0xFF000000;  /* Sign extend */
    return (int32_t)val;
}

static inline int32_t read_s24_le(const uint8_t* buf) {
    uint32_t val = read_u24_le(buf);
    if (val & 0x800000) val |= 0xFF000000;
    return (int32_t)val;
}

static inline int32_t read_s32_be(const uint8_t* buf) {
    return (int32_t)read_u32_be(buf);
}

static inline int32_t read_s32_le(const uint8_t* buf) {
    return (int32_t)read_u32_le(buf);
}

static inline uint64_t read_u64_be(const uint8_t* buf) {
    return ((uint64_t)read_u32_be(buf) << 32) | read_u32_be(buf + 4);
}

static inline uint64_t read_u64_le(const uint8_t* buf) {
    return ((uint64_t)read_u32_le(buf + 4) << 32) | read_u32_le(buf);
}

static inline int64_t read_s64_be(const uint8_t* buf) {
    return (int64_t)read_u64_be(buf);
}

static inline int64_t read_s64_le(const uint8_t* buf) {
    return (int64_t)read_u64_le(buf);
}

static inline float read_f32_be(const uint8_t* buf) {
    union { uint32_t u; float f; } conv;
    conv.u = read_u32_be(buf);
    return conv.f;
}

static inline float read_f32_le(const uint8_t* buf) {
    union { uint32_t u; float f; } conv;
    conv.u = read_u32_le(buf);
    return conv.f;
}

static inline double read_f64_be(const uint8_t* buf) {
    union { uint64_t u; double d; } conv;
    conv.u = read_u64_be(buf);
    return conv.d;
}

static inline double read_f64_le(const uint8_t* buf) {
    union { uint64_t u; double d; } conv;
    conv.u = read_u64_le(buf);
    return conv.d;
}

/* IEEE 754 half-precision float decode */
static inline float read_f16_be(const uint8_t* buf) {
    uint16_t h = read_u16_be(buf);
    uint32_t sign = (h >> 15) & 1;
    uint32_t exp = (h >> 10) & 0x1F;
    uint32_t frac = h & 0x3FF;
    
    if (exp == 0) {
        if (frac == 0) return sign ? -0.0f : 0.0f;
        /* Subnormal */
        float val = (float)frac / 1024.0f;
        val *= 6.103515625e-05f;  /* 2^-14 */
        return sign ? -val : val;
    }
    if (exp == 31) {
        if (frac == 0) return sign ? -1.0f/0.0f : 1.0f/0.0f;
        return 0.0f/0.0f;  /* NaN */
    }
    
    float val = (1.0f + (float)frac / 1024.0f);
    int actual_exp = (int)exp - 15;
    if (actual_exp > 0) {
        for (int i = 0; i < actual_exp; i++) val *= 2.0f;
    } else {
        for (int i = 0; i < -actual_exp; i++) val /= 2.0f;
    }
    return sign ? -val : val;
}

static inline float read_f16_le(const uint8_t* buf) {
    uint8_t swapped[2] = {buf[1], buf[0]};
    return read_f16_be(swapped);
}

/* ============================================
 * Bitfield Extraction
 * ============================================ */

static inline uint8_t extract_bits(uint8_t byte, uint8_t start, uint8_t width) {
    return (byte >> start) & ((1 << width) - 1);
}

/* ============================================
 * Type Parsing from String
 * ============================================ */

static inline field_type_t parse_type_string(const char* type_str, 
                                              uint8_t* bit_start,
                                              uint8_t* bit_width) {
    *bit_start = 0;
    *bit_width = 0;
    
    /* Bitfield syntax 1: Python slice u8[3:5] - bits 3..5 inclusive */
    {
        int start, end;
        if (sscanf(type_str, "u8[%d:%d]", &start, &end) == 2) {
            *bit_start = (uint8_t)start;
            *bit_width = (uint8_t)(end - start + 1);
            return FIELD_TYPE_BITS;
        }
        if (sscanf(type_str, "u16[%d:%d]", &start, &end) == 2) {
            *bit_start = (uint8_t)start;
            *bit_width = (uint8_t)(end - start + 1);
            return FIELD_TYPE_BITS;
        }
    }
    
    /* Bitfield syntax 2: Verilog part-select u8[3+:2] - 2 bits at offset 3 */
    {
        int offset, width;
        if (sscanf(type_str, "u8[%d+:%d]", &offset, &width) == 2) {
            *bit_start = (uint8_t)offset;
            *bit_width = (uint8_t)width;
            return FIELD_TYPE_BITS;
        }
    }
    
    /* Bitfield syntax 3: C++ template bits<3,2> */
    {
        int offset, width;
        if (sscanf(type_str, "bits<%d,%d>", &offset, &width) == 2) {
            *bit_start = (uint8_t)offset;
            *bit_width = (uint8_t)width;
            return FIELD_TYPE_BITS;
        }
    }
    
    /* Bitfield syntax 4: @ notation bits:2@3 */
    {
        int width, offset;
        if (sscanf(type_str, "bits:%d@%d", &width, &offset) == 2) {
            *bit_start = (uint8_t)offset;
            *bit_width = (uint8_t)width;
            return FIELD_TYPE_BITS;
        }
    }
    
    /* Bitfield syntax 5: Sequential u8:2 - next N bits (bit_start=255 sentinel) */
    {
        int base, width;
        if (sscanf(type_str, "u%d:%d", &base, &width) == 2 && 
            strchr(type_str, '[') == NULL) {
            *bit_start = 255;  /* Sentinel: sequential mode */
            *bit_width = (uint8_t)width;
            return FIELD_TYPE_BITS;
        }
    }
    
    /* Standard types */
    if (strcmp(type_str, "u8") == 0 || strcmp(type_str, "uint8") == 0) 
        return FIELD_TYPE_U8;
    if (strcmp(type_str, "u16") == 0 || strcmp(type_str, "uint16") == 0) 
        return FIELD_TYPE_U16;
    if (strcmp(type_str, "u24") == 0 || strcmp(type_str, "uint24") == 0) 
        return FIELD_TYPE_U24;
    if (strcmp(type_str, "u32") == 0 || strcmp(type_str, "uint32") == 0) 
        return FIELD_TYPE_U32;
    if (strcmp(type_str, "u64") == 0 || strcmp(type_str, "uint64") == 0) 
        return FIELD_TYPE_U64;
    if (strcmp(type_str, "s8") == 0 || strcmp(type_str, "i8") == 0 || 
        strcmp(type_str, "int8") == 0) 
        return FIELD_TYPE_S8;
    if (strcmp(type_str, "s16") == 0 || strcmp(type_str, "i16") == 0 || 
        strcmp(type_str, "int16") == 0) 
        return FIELD_TYPE_S16;
    if (strcmp(type_str, "s24") == 0 || strcmp(type_str, "i24") == 0 || 
        strcmp(type_str, "int24") == 0) 
        return FIELD_TYPE_S24;
    if (strcmp(type_str, "s32") == 0 || strcmp(type_str, "i32") == 0 || 
        strcmp(type_str, "int32") == 0) 
        return FIELD_TYPE_S32;
    if (strcmp(type_str, "s64") == 0 || strcmp(type_str, "i64") == 0 || 
        strcmp(type_str, "int64") == 0) 
        return FIELD_TYPE_S64;
    if (strcmp(type_str, "f16") == 0) return FIELD_TYPE_F16;
    if (strcmp(type_str, "f32") == 0 || strcmp(type_str, "float") == 0) 
        return FIELD_TYPE_F32;
    if (strcmp(type_str, "f64") == 0 || strcmp(type_str, "double") == 0) 
        return FIELD_TYPE_F64;
    if (strcmp(type_str, "bool") == 0) return FIELD_TYPE_BOOL;
    if (strcmp(type_str, "skip") == 0) return FIELD_TYPE_SKIP;
    if (strcmp(type_str, "ascii") == 0 || strcmp(type_str, "string") == 0) 
        return FIELD_TYPE_ASCII;
    if (strcmp(type_str, "hex") == 0) return FIELD_TYPE_HEX;
    if (strcmp(type_str, "base64") == 0) return FIELD_TYPE_BASE64;
    if (strcmp(type_str, "bytes") == 0) return FIELD_TYPE_BYTES;
    if (strcmp(type_str, "object") == 0) return FIELD_TYPE_OBJECT;
    if (strcmp(type_str, "match") == 0) return FIELD_TYPE_MATCH;
    if (strcmp(type_str, "enum") == 0) return FIELD_TYPE_ENUM;
    if (strcmp(type_str, "udec") == 0 || strcmp(type_str, "UDec") == 0) 
        return FIELD_TYPE_UDEC;
    if (strcmp(type_str, "sdec") == 0 || strcmp(type_str, "SDec") == 0) 
        return FIELD_TYPE_SDEC;
    
    return FIELD_TYPE_UNKNOWN;
}

/* ============================================
 * Variable Context Management
 * ============================================ */

static inline void var_set(var_context_t* ctx, const char* name, int64_t value) {
    for (int i = 0; i < ctx->count; i++) {
        if (strcmp(ctx->vars[i].name, name) == 0) {
            ctx->vars[i].value = value;
            return;
        }
    }
    if (ctx->count < SCHEMA_MAX_FIELDS) {
        strncpy(ctx->vars[ctx->count].name, name, SCHEMA_MAX_NAME_LEN - 1);
        ctx->vars[ctx->count].value = value;
        ctx->count++;
    }
}

static inline int64_t var_get(var_context_t* ctx, const char* name) {
    for (int i = 0; i < ctx->count; i++) {
        if (strcmp(ctx->vars[i].name, name) == 0) {
            return ctx->vars[i].value;
        }
    }
    return 0;
}

/* ============================================
 * Schema Initialization
 * ============================================ */

static inline void schema_init(schema_t* schema) {
    memset(schema, 0, sizeof(schema_t));
    schema->endian = ENDIAN_BIG;
}

static inline void schema_add_field(schema_t* schema, const field_def_t* field) {
    if (schema->field_count < SCHEMA_MAX_FIELDS) {
        schema->fields[schema->field_count++] = *field;
    }
}

/* ============================================
 * Decode Single Field
 * ============================================ */

static inline int decode_field(
    const field_def_t* field,
    const uint8_t* buf,
    size_t len,
    size_t* pos,
    decoded_field_t* out,
    var_context_t* vars,
    endian_t default_endian
) {
    endian_t endian = (field->endian != ENDIAN_DEFAULT) ? field->endian : default_endian;
    int64_t raw_value = 0;
    double final_value = 0;
    
    out->valid = false;
    strncpy(out->name, field->name, SCHEMA_MAX_NAME_LEN - 1);
    out->type = field->type;
    
    switch (field->type) {
        case FIELD_TYPE_U8:
            if (*pos + 1 > len) return SCHEMA_ERR_BUFFER;
            raw_value = read_u8(buf + *pos);
            *pos += 1;
            break;
            
        case FIELD_TYPE_U16:
            if (*pos + 2 > len) return SCHEMA_ERR_BUFFER;
            raw_value = endian == ENDIAN_BIG ? 
                read_u16_be(buf + *pos) : read_u16_le(buf + *pos);
            *pos += 2;
            break;
            
        case FIELD_TYPE_U24:
            if (*pos + 3 > len) return SCHEMA_ERR_BUFFER;
            raw_value = endian == ENDIAN_BIG ? 
                read_u24_be(buf + *pos) : read_u24_le(buf + *pos);
            *pos += 3;
            break;
            
        case FIELD_TYPE_U32:
            if (*pos + 4 > len) return SCHEMA_ERR_BUFFER;
            raw_value = endian == ENDIAN_BIG ? 
                read_u32_be(buf + *pos) : read_u32_le(buf + *pos);
            *pos += 4;
            break;
            
        case FIELD_TYPE_S8:
            if (*pos + 1 > len) return SCHEMA_ERR_BUFFER;
            raw_value = read_s8(buf + *pos);
            *pos += 1;
            break;
            
        case FIELD_TYPE_S16:
            if (*pos + 2 > len) return SCHEMA_ERR_BUFFER;
            raw_value = endian == ENDIAN_BIG ? 
                read_s16_be(buf + *pos) : read_s16_le(buf + *pos);
            *pos += 2;
            break;
            
        case FIELD_TYPE_S24:
            if (*pos + 3 > len) return SCHEMA_ERR_BUFFER;
            raw_value = endian == ENDIAN_BIG ? 
                read_s24_be(buf + *pos) : read_s24_le(buf + *pos);
            *pos += 3;
            break;
            
        case FIELD_TYPE_S32:
            if (*pos + 4 > len) return SCHEMA_ERR_BUFFER;
            raw_value = endian == ENDIAN_BIG ? 
                read_s32_be(buf + *pos) : read_s32_le(buf + *pos);
            *pos += 4;
            break;
            
        case FIELD_TYPE_U64:
            if (*pos + 8 > len) return SCHEMA_ERR_BUFFER;
            out->value.u64 = endian == ENDIAN_BIG ?
                read_u64_be(buf + *pos) : read_u64_le(buf + *pos);
            *pos += 8;
            /* Apply modifiers on u64 directly */
            final_value = (double)out->value.u64;
            if (field->has_mult) final_value *= field->mult;
            if (field->has_div && field->div != 0) final_value /= field->div;
            if (field->has_add) final_value += field->add;
            out->value.f64 = final_value;
            out->valid = true;
            if (field->var_name[0]) var_set(vars, field->var_name, (int64_t)out->value.u64);
            return SCHEMA_OK;
            
        case FIELD_TYPE_S64:
            if (*pos + 8 > len) return SCHEMA_ERR_BUFFER;
            raw_value = endian == ENDIAN_BIG ?
                read_s64_be(buf + *pos) : read_s64_le(buf + *pos);
            *pos += 8;
            break;
            
        case FIELD_TYPE_F16:
            if (*pos + 2 > len) return SCHEMA_ERR_BUFFER;
            out->value.f64 = endian == ENDIAN_BIG ?
                read_f16_be(buf + *pos) : read_f16_le(buf + *pos);
            *pos += 2;
            out->valid = true;
            return SCHEMA_OK;
            
        case FIELD_TYPE_F32:
            if (*pos + 4 > len) return SCHEMA_ERR_BUFFER;
            out->value.f64 = endian == ENDIAN_BIG ? 
                read_f32_be(buf + *pos) : read_f32_le(buf + *pos);
            *pos += 4;
            out->valid = true;
            return SCHEMA_OK;
            
        case FIELD_TYPE_F64:
            if (*pos + 8 > len) return SCHEMA_ERR_BUFFER;
            out->value.f64 = endian == ENDIAN_BIG ?
                read_f64_be(buf + *pos) : read_f64_le(buf + *pos);
            *pos += 8;
            out->valid = true;
            return SCHEMA_OK;
            
        case FIELD_TYPE_BOOL:
            if (*pos + 1 > len) return SCHEMA_ERR_BUFFER;
            {
                uint8_t byte = buf[*pos];
                uint8_t bit_pos = field->bit_start;
                out->value.b = ((byte >> bit_pos) & 1) != 0;
            }
            if (field->consume) *pos += 1;
            out->valid = true;
            if (field->var_name[0]) var_set(vars, field->var_name, out->value.b ? 1 : 0);
            return SCHEMA_OK;
            
        case FIELD_TYPE_BITS:
            if (*pos >= len) return SCHEMA_ERR_BUFFER;
            raw_value = extract_bits(buf[*pos], field->bit_start, field->bit_width);
            if (field->consume) *pos += 1;
            break;
            
        case FIELD_TYPE_SKIP:
            *pos += field->size ? field->size : 1;
            return SCHEMA_OK;
            
        case FIELD_TYPE_ASCII:
            if (*pos + field->size > len) return SCHEMA_ERR_BUFFER;
            memcpy(out->value.str, buf + *pos, field->size < SCHEMA_MAX_NAME_LEN ? field->size : SCHEMA_MAX_NAME_LEN - 1);
            out->value.str[field->size < SCHEMA_MAX_NAME_LEN ? field->size : SCHEMA_MAX_NAME_LEN - 1] = '\0';
            /* Strip trailing nulls */
            {
                int slen = (int)strlen(out->value.str);
                while (slen > 0 && out->value.str[slen - 1] == '\0') slen--;
            }
            *pos += field->size;
            out->valid = true;
            return SCHEMA_OK;
            
        case FIELD_TYPE_HEX:
            if (*pos + field->size > len) return SCHEMA_ERR_BUFFER;
            {
                int hex_len = field->size < (SCHEMA_MAX_NAME_LEN / 2) ? field->size : (SCHEMA_MAX_NAME_LEN / 2 - 1);
                for (int h = 0; h < hex_len; h++) {
                    static const char hex_chars[] = "0123456789ABCDEF";
                    out->value.str[h * 2] = hex_chars[(buf[*pos + h] >> 4) & 0x0F];
                    out->value.str[h * 2 + 1] = hex_chars[buf[*pos + h] & 0x0F];
                }
                out->value.str[hex_len * 2] = '\0';
            }
            *pos += field->size;
            out->valid = true;
            out->type = FIELD_TYPE_HEX;
            return SCHEMA_OK;
            
        case FIELD_TYPE_BASE64:
            if (*pos + field->size > len) return SCHEMA_ERR_BUFFER;
            {
                static const char b64[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
                int in_len = field->size;
                int out_idx = 0;
                for (int b = 0; b < in_len && out_idx < SCHEMA_MAX_NAME_LEN - 4; b += 3) {
                    uint32_t triple = ((uint32_t)buf[*pos + b]) << 16;
                    if (b + 1 < in_len) triple |= ((uint32_t)buf[*pos + b + 1]) << 8;
                    if (b + 2 < in_len) triple |= buf[*pos + b + 2];
                    out->value.str[out_idx++] = b64[(triple >> 18) & 0x3F];
                    out->value.str[out_idx++] = b64[(triple >> 12) & 0x3F];
                    out->value.str[out_idx++] = (b + 1 < in_len) ? b64[(triple >> 6) & 0x3F] : '=';
                    out->value.str[out_idx++] = (b + 2 < in_len) ? b64[triple & 0x3F] : '=';
                }
                out->value.str[out_idx] = '\0';
            }
            *pos += field->size;
            out->valid = true;
            out->type = FIELD_TYPE_BASE64;
            return SCHEMA_OK;
            
        case FIELD_TYPE_BYTES:
            if (*pos + field->size > len) return SCHEMA_ERR_BUFFER;
            {
                int copy_len = field->size < SCHEMA_MAX_NAME_LEN ? field->size : SCHEMA_MAX_NAME_LEN;
                memcpy(out->value.bytes, buf + *pos, copy_len);
            }
            *pos += field->size;
            out->valid = true;
            return SCHEMA_OK;
            
        case FIELD_TYPE_ENUM:
            /* Decode as underlying integer then apply enum lookup */
            if (*pos + field->size > len) return SCHEMA_ERR_BUFFER;
            {
                int esize = field->size ? field->size : 1;
                if (esize == 1) {
                    raw_value = read_u8(buf + *pos);
                } else if (esize == 2) {
                    raw_value = endian == ENDIAN_BIG ? read_u16_be(buf + *pos) : read_u16_le(buf + *pos);
                } else {
                    raw_value = read_u8(buf + *pos);
                }
                *pos += esize;
            }
            /* Apply lookup */
            if (field->lookup_count > 0) {
                for (int li = 0; li < field->lookup_count; li++) {
                    if (field->lookup[li].key == (int)raw_value) {
                        strncpy(out->value.str, field->lookup[li].value, SCHEMA_MAX_NAME_LEN - 1);
                        out->valid = true;
                        if (field->var_name[0]) var_set(vars, field->var_name, raw_value);
                        return SCHEMA_OK;
                    }
                }
                /* Unknown enum value - store raw */
                snprintf(out->value.str, SCHEMA_MAX_NAME_LEN, "unknown(%d)", (int)raw_value);
                out->valid = true;
                if (field->var_name[0]) var_set(vars, field->var_name, raw_value);
                return SCHEMA_OK;
            }
            break;
            
        case FIELD_TYPE_UDEC:
            /* Nibble-decimal: upper nibble = whole, lower = tenths */
            if (*pos + 1 > len) return SCHEMA_ERR_BUFFER;
            {
                uint8_t byte = buf[*pos];
                final_value = (byte >> 4) + (byte & 0x0F) * 0.1;
            }
            *pos += 1;
            /* Apply modifiers and store directly (raw_value not used) */
            if (field->has_mult) final_value *= field->mult;
            if (field->has_div) final_value /= field->div;
            if (field->has_add) final_value += field->add;
            out->value.f64 = final_value;
            out->valid = true;
            return SCHEMA_OK;
            
        case FIELD_TYPE_SDEC:
            /* Signed nibble-decimal: sign-extend upper nibble */
            if (*pos + 1 > len) return SCHEMA_ERR_BUFFER;
            {
                uint8_t byte = buf[*pos];
                int8_t whole = (int8_t)(byte >> 4);
                if (whole >= 8) whole -= 16;  /* Sign extend 4-bit */
                final_value = whole + (byte & 0x0F) * 0.1;
            }
            *pos += 1;
            /* Apply modifiers and store directly */
            if (field->has_mult) final_value *= field->mult;
            if (field->has_div) final_value /= field->div;
            if (field->has_add) final_value += field->add;
            out->value.f64 = final_value;
            out->valid = true;
            return SCHEMA_OK;
            
        default:
            return SCHEMA_ERR_TYPE;
    }
    
    /* Store raw value for variable */
    if (field->var_name[0]) {
        var_set(vars, field->var_name, raw_value);
    }
    
    /* Apply modifiers */
    final_value = (double)raw_value;
    if (field->has_mult) final_value *= field->mult;
    if (field->has_div && field->div != 0) final_value /= field->div;
    if (field->has_add) final_value += field->add;
    
    /* Apply lookup if present */
    if (field->lookup_count > 0) {
        for (int i = 0; i < field->lookup_count; i++) {
            if (field->lookup[i].key == (int)raw_value) {
                strncpy(out->value.str, field->lookup[i].value, SCHEMA_MAX_NAME_LEN - 1);
                out->valid = true;
                return SCHEMA_OK;
            }
        }
        /* No match - store raw value */
        out->value.i64 = raw_value;
    } else {
        out->value.f64 = final_value;
    }
    
    out->valid = true;
    return SCHEMA_OK;
}

/* ============================================
 * Main Decode Function
 * ============================================ */

static inline int schema_decode(
    const schema_t* schema,
    const uint8_t* buf,
    size_t len,
    decode_result_t* result
) {
    memset(result, 0, sizeof(decode_result_t));
    
    size_t pos = 0;
    var_context_t vars = {0};
    
    for (int i = 0; i < schema->field_count; i++) {
        const field_def_t* field = &schema->fields[i];
        
        /* Handle match type */
        if (field->type == FIELD_TYPE_MATCH) {
            /* Get match variable value */
            const char* var_name = field->match_var;
            if (var_name[0] == '$') var_name++;
            int64_t match_val = var_get(&vars, var_name);
            
            /* Find matching case */
            for (int c = 0; c < field->case_count; c++) {
                const case_def_t* cs = &field->cases[c];
                bool matched = false;
                
                if (cs->is_default) {
                    matched = true;
                } else if (cs->match_value == (int)match_val) {
                    matched = true;
                } else if (cs->range_min != cs->range_max) {
                    matched = (match_val >= cs->range_min && match_val <= cs->range_max);
                } else {
                    /* Check list */
                    for (int j = 0; cs->match_list[j] != -1 && j < 8; j++) {
                        if (cs->match_list[j] == (int)match_val) {
                            matched = true;
                            break;
                        }
                    }
                }
                
                if (matched) {
                    /* Decode case fields */
                    for (int f = 0; f < cs->field_count; f++) {
                        int field_idx = cs->field_start + f;
                        if (field_idx >= schema->field_count) break;
                        
                        int rc = decode_field(
                            &schema->fields[field_idx],
                            buf, len, &pos,
                            &result->fields[result->field_count],
                            &vars, schema->endian
                        );
                        if (rc != SCHEMA_OK) {
                            result->error_code = rc;
                            return rc;
                        }
                        if (result->fields[result->field_count].valid) {
                            result->field_count++;
                        }
                    }
                    break;
                }
            }
            continue;
        }
        
        /* Regular field */
        int rc = decode_field(
            field, buf, len, &pos,
            &result->fields[result->field_count],
            &vars, schema->endian
        );
        
        if (rc != SCHEMA_OK) {
            result->error_code = rc;
            return rc;
        }
        
        if (result->fields[result->field_count].valid &&
            field->name[0] && field->name[0] != '_') {
            result->field_count++;
        }
    }
    
    result->bytes_consumed = (int)pos;
    return SCHEMA_OK;
}

/* ============================================
 * Encoder: Values → Payload Bytes
 * ============================================ */

typedef struct {
    uint8_t data[SCHEMA_MAX_PAYLOAD];
    int len;
    int error_code;
} encode_result_t;

/* Input values for encoding */
typedef struct {
    char name[SCHEMA_MAX_NAME_LEN];
    field_value_t value;
} encode_input_t;

typedef struct {
    encode_input_t inputs[SCHEMA_MAX_FIELDS];
    int count;
} encode_inputs_t;

static inline void encode_inputs_init(encode_inputs_t* inputs) {
    memset(inputs, 0, sizeof(*inputs));
}

static inline void encode_inputs_add_int(encode_inputs_t* inputs, const char* name, int64_t val) {
    if (inputs->count >= SCHEMA_MAX_FIELDS) return;
    strncpy(inputs->inputs[inputs->count].name, name, SCHEMA_MAX_NAME_LEN - 1);
    inputs->inputs[inputs->count].value.i64 = val;
    inputs->count++;
}

static inline void encode_inputs_add_double(encode_inputs_t* inputs, const char* name, double val) {
    if (inputs->count >= SCHEMA_MAX_FIELDS) return;
    strncpy(inputs->inputs[inputs->count].name, name, SCHEMA_MAX_NAME_LEN - 1);
    inputs->inputs[inputs->count].value.f64 = val;
    inputs->count++;
}

/* Find input value by name */
static inline const encode_input_t* find_input(const encode_inputs_t* inputs, const char* name) {
    for (int i = 0; i < inputs->count; i++) {
        if (strcmp(inputs->inputs[i].name, name) == 0) {
            return &inputs->inputs[i];
        }
    }
    return NULL;
}

/* Write integer to buffer */
static inline void write_int(uint8_t* buf, size_t* pos, int64_t val, int size, endian_t endian) {
    uint64_t uval = (uint64_t)val;
    if (endian == ENDIAN_BIG) {
        for (int i = size - 1; i >= 0; i--) {
            buf[*pos + i] = uval & 0xFF;
            uval >>= 8;
        }
    } else {
        for (int i = 0; i < size; i++) {
            buf[*pos + i] = uval & 0xFF;
            uval >>= 8;
        }
    }
    *pos += size;
}

/* Encode single field */
static inline int encode_field(
    const field_def_t* field,
    const encode_inputs_t* inputs,
    uint8_t* buf,
    size_t* pos,
    endian_t schema_endian
) {
    const encode_input_t* input = find_input(inputs, field->name);
    if (!input && field->type != FIELD_TYPE_SKIP) {
        return SCHEMA_ERR_PARSE;  /* Missing input */
    }
    
    double raw_val = input ? input->value.f64 : 0.0;
    
    /* Reverse modifiers: encode_formula or inverse of mult/add */
    if (field->has_add) {
        raw_val -= field->add;
    }
    if (field->has_mult && field->mult != 0) {
        raw_val /= field->mult;
    }
    if (field->has_div) {
        raw_val *= field->div;
    }
    
    int64_t int_val = (int64_t)(raw_val + (raw_val >= 0 ? 0.5 : -0.5));  /* Round */
    endian_t endian = (field->endian != ENDIAN_DEFAULT) ? field->endian : schema_endian;
    
    switch (field->type) {
        case FIELD_TYPE_U8:
        case FIELD_TYPE_S8:
            buf[*pos] = (uint8_t)(int_val & 0xFF);
            (*pos)++;
            break;
            
        case FIELD_TYPE_U16:
        case FIELD_TYPE_S16:
            write_int(buf, pos, int_val, 2, endian);
            break;
            
        case FIELD_TYPE_U24:
        case FIELD_TYPE_S24:
            write_int(buf, pos, int_val, 3, endian);
            break;
            
        case FIELD_TYPE_U32:
        case FIELD_TYPE_S32:
            write_int(buf, pos, int_val, 4, endian);
            break;
            
        case FIELD_TYPE_U64:
        case FIELD_TYPE_S64:
            write_int(buf, pos, int_val, 8, endian);
            break;
            
        case FIELD_TYPE_F32: {
            float fval = (float)raw_val;
            uint32_t bits;
            memcpy(&bits, &fval, sizeof(bits));
            write_int(buf, pos, bits, 4, endian);
            break;
        }
        
        case FIELD_TYPE_F64: {
            uint64_t dbits;
            memcpy(&dbits, &raw_val, sizeof(dbits));
            write_int(buf, pos, (int64_t)dbits, 8, endian);
            break;
        }
        
        case FIELD_TYPE_BOOL:
            buf[*pos] = int_val ? 1 : 0;
            (*pos)++;
            break;
            
        case FIELD_TYPE_BITS: {
            /* Bitfield - read current byte, modify bits, write back */
            uint8_t byte_val = buf[*pos];
            uint8_t mask = ((1 << field->bit_width) - 1) << field->bit_start;
            byte_val &= ~mask;
            byte_val |= ((int_val & ((1 << field->bit_width) - 1)) << field->bit_start);
            buf[*pos] = byte_val;
            if (field->consume) {
                (*pos)++;
            }
            break;
        }
        
        case FIELD_TYPE_SKIP:
            for (int i = 0; i < field->size; i++) {
                buf[*pos] = 0;
                (*pos)++;
            }
            break;
            
        case FIELD_TYPE_UDEC: {
            /* Encode nibble-decimal: value 3.7 -> 0x37 */
            int whole = (int)raw_val;
            int frac = (int)((raw_val - whole) * 10 + 0.5);
            if (whole > 9) whole = 9;
            if (whole < 0) whole = 0;
            if (frac > 9) frac = 9;
            buf[*pos] = (uint8_t)((whole << 4) | (frac & 0x0F));
            (*pos)++;
            break;
        }
        
        case FIELD_TYPE_SDEC: {
            /* Encode signed nibble-decimal */
            int whole = (int)raw_val;
            double frac_part = raw_val - whole;
            if (raw_val < 0 && frac_part != 0) {
                whole--;  /* Handle negative fractional */
                frac_part = raw_val - whole;
            }
            int frac = (int)(frac_part * 10 + 0.5);
            if (whole < -8) whole = -8;
            if (whole > 7) whole = 7;
            if (frac > 9) frac = 9;
            uint8_t whole_nibble = (uint8_t)(whole & 0x0F);
            buf[*pos] = (whole_nibble << 4) | (frac & 0x0F);
            (*pos)++;
            break;
        }
            
        default:
            return SCHEMA_ERR_UNSUPPORTED;
    }
    
    return SCHEMA_OK;
}

/* Main encode function */
static inline int schema_encode(
    const schema_t* schema,
    const encode_inputs_t* inputs,
    encode_result_t* result
) {
    memset(result, 0, sizeof(*result));
    size_t pos = 0;
    
    for (int i = 0; i < schema->field_count; i++) {
        const field_def_t* field = &schema->fields[i];
        
        /* Skip internal/match fields for now */
        if (field->name[0] == '_' || field->type == FIELD_TYPE_MATCH) {
            continue;
        }
        
        int rc = encode_field(field, inputs, result->data, &pos, schema->endian);
        if (rc != SCHEMA_OK) {
            result->error_code = rc;
            return rc;
        }
    }
    
    result->len = (int)pos;
    return SCHEMA_OK;
}

/* ============================================
 * Convenience: Build Schema Programmatically
 * ============================================ */

static inline field_def_t field_u8(const char* name) {
    field_def_t f = {0};
    strncpy(f.name, name, SCHEMA_MAX_NAME_LEN - 1);
    f.type = FIELD_TYPE_U8;
    f.size = 1;
    return f;
}

static inline field_def_t field_u16(const char* name, endian_t endian) {
    field_def_t f = {0};
    strncpy(f.name, name, SCHEMA_MAX_NAME_LEN - 1);
    f.type = FIELD_TYPE_U16;
    f.size = 2;
    f.endian = endian;
    return f;
}

static inline field_def_t field_s16(const char* name, endian_t endian) {
    field_def_t f = {0};
    strncpy(f.name, name, SCHEMA_MAX_NAME_LEN - 1);
    f.type = FIELD_TYPE_S16;
    f.size = 2;
    f.endian = endian;
    return f;
}

static inline field_def_t field_bits(const char* name, uint8_t start, uint8_t width, bool consume) {
    field_def_t f = {0};
    strncpy(f.name, name, SCHEMA_MAX_NAME_LEN - 1);
    f.type = FIELD_TYPE_BITS;
    f.bit_start = start;
    f.bit_width = width;
    f.consume = consume;
    return f;
}

static inline void field_set_mult(field_def_t* f, double mult) {
    f->mult = mult;
    f->has_mult = true;
}

static inline void field_set_add(field_def_t* f, double add) {
    f->add = add;
    f->has_add = true;
}

static inline void field_set_var(field_def_t* f, const char* var_name) {
    strncpy(f->var_name, var_name, SCHEMA_MAX_NAME_LEN - 1);
}

static inline void field_set_div(field_def_t* f, double div) {
    f->div = div;
    f->has_div = true;
}

static inline void field_add_lookup(field_def_t* f, int key, const char* value) {
    if (f->lookup_count < SCHEMA_MAX_LOOKUP) {
        f->lookup[f->lookup_count].key = key;
        strncpy(f->lookup[f->lookup_count].value, value, SCHEMA_MAX_NAME_LEN - 1);
        f->lookup_count++;
    }
}

static inline field_def_t field_u24(const char* name, endian_t endian) {
    field_def_t f = {0};
    strncpy(f.name, name, SCHEMA_MAX_NAME_LEN - 1);
    f.type = FIELD_TYPE_U24;
    f.size = 3;
    f.endian = endian;
    return f;
}

static inline field_def_t field_u32(const char* name, endian_t endian) {
    field_def_t f = {0};
    strncpy(f.name, name, SCHEMA_MAX_NAME_LEN - 1);
    f.type = FIELD_TYPE_U32;
    f.size = 4;
    f.endian = endian;
    return f;
}

static inline field_def_t field_s8(const char* name) {
    field_def_t f = {0};
    strncpy(f.name, name, SCHEMA_MAX_NAME_LEN - 1);
    f.type = FIELD_TYPE_S8;
    f.size = 1;
    return f;
}

static inline field_def_t field_s24(const char* name, endian_t endian) {
    field_def_t f = {0};
    strncpy(f.name, name, SCHEMA_MAX_NAME_LEN - 1);
    f.type = FIELD_TYPE_S24;
    f.size = 3;
    f.endian = endian;
    return f;
}

static inline field_def_t field_s32(const char* name, endian_t endian) {
    field_def_t f = {0};
    strncpy(f.name, name, SCHEMA_MAX_NAME_LEN - 1);
    f.type = FIELD_TYPE_S32;
    f.size = 4;
    f.endian = endian;
    return f;
}

static inline field_def_t field_u64(const char* name, endian_t endian) {
    field_def_t f = {0};
    strncpy(f.name, name, SCHEMA_MAX_NAME_LEN - 1);
    f.type = FIELD_TYPE_U64;
    f.size = 8;
    f.endian = endian;
    return f;
}

static inline field_def_t field_s64(const char* name, endian_t endian) {
    field_def_t f = {0};
    strncpy(f.name, name, SCHEMA_MAX_NAME_LEN - 1);
    f.type = FIELD_TYPE_S64;
    f.size = 8;
    f.endian = endian;
    return f;
}

static inline field_def_t field_f16(const char* name, endian_t endian) {
    field_def_t f = {0};
    strncpy(f.name, name, SCHEMA_MAX_NAME_LEN - 1);
    f.type = FIELD_TYPE_F16;
    f.size = 2;
    f.endian = endian;
    return f;
}

static inline field_def_t field_f32(const char* name, endian_t endian) {
    field_def_t f = {0};
    strncpy(f.name, name, SCHEMA_MAX_NAME_LEN - 1);
    f.type = FIELD_TYPE_F32;
    f.size = 4;
    f.endian = endian;
    return f;
}

static inline field_def_t field_f64(const char* name, endian_t endian) {
    field_def_t f = {0};
    strncpy(f.name, name, SCHEMA_MAX_NAME_LEN - 1);
    f.type = FIELD_TYPE_F64;
    f.size = 8;
    f.endian = endian;
    return f;
}

static inline field_def_t field_bool(const char* name, uint8_t bit_pos, bool consume) {
    field_def_t f = {0};
    strncpy(f.name, name, SCHEMA_MAX_NAME_LEN - 1);
    f.type = FIELD_TYPE_BOOL;
    f.bit_start = bit_pos;
    f.consume = consume;
    return f;
}

static inline field_def_t field_enum(const char* name, uint8_t base_size) {
    field_def_t f = {0};
    strncpy(f.name, name, SCHEMA_MAX_NAME_LEN - 1);
    f.type = FIELD_TYPE_ENUM;
    f.size = base_size;
    return f;
}

static inline field_def_t field_hex(const char* name, uint8_t length) {
    field_def_t f = {0};
    strncpy(f.name, name, SCHEMA_MAX_NAME_LEN - 1);
    f.type = FIELD_TYPE_HEX;
    f.size = length;
    return f;
}

static inline field_def_t field_ascii(const char* name, uint8_t length) {
    field_def_t f = {0};
    strncpy(f.name, name, SCHEMA_MAX_NAME_LEN - 1);
    f.type = FIELD_TYPE_ASCII;
    f.size = length;
    return f;
}

static inline field_def_t field_skip(uint8_t length) {
    field_def_t f = {0};
    strncpy(f.name, "_skip", SCHEMA_MAX_NAME_LEN - 1);
    f.type = FIELD_TYPE_SKIP;
    f.size = length;
    return f;
}

static inline field_def_t field_bytes_type(const char* name, uint8_t length) {
    field_def_t f = {0};
    strncpy(f.name, name, SCHEMA_MAX_NAME_LEN - 1);
    f.type = FIELD_TYPE_BYTES;
    f.size = length;
    return f;
}

/* ============================================
 * Result Access Helpers
 * ============================================ */

static inline const decoded_field_t* result_get_field(
    const decode_result_t* result, 
    const char* name
) {
    for (int i = 0; i < result->field_count; i++) {
        if (strcmp(result->fields[i].name, name) == 0) {
            return &result->fields[i];
        }
    }
    return NULL;
}

static inline double result_get_double(
    const decode_result_t* result, 
    const char* name, 
    double default_val
) {
    const decoded_field_t* f = result_get_field(result, name);
    return f ? f->value.f64 : default_val;
}

static inline int64_t result_get_int(
    const decode_result_t* result, 
    const char* name, 
    int64_t default_val
) {
    const decoded_field_t* f = result_get_field(result, name);
    return f ? f->value.i64 : default_val;
}

static inline const char* result_get_string(
    const decode_result_t* result, 
    const char* name
) {
    const decoded_field_t* f = result_get_field(result, name);
    return f ? f->value.str : NULL;
}

/* ============================================
 * Binary Schema Loading
 * ============================================
 *
 * Binary format (compact, ~4 bytes/field):
 *   Header (5 bytes): 'P' 'S' version flags field_count
 *   Per field:
 *     type_byte: [TTTT SSSS] type(4) size(4)
 *     mult_exp:  signed exponent, mult = 10^exp
 *     field_id:  2 bytes little-endian (IPSO or hash)
 *     [options]: bitfield info, add value, lookup table
 *
 * Type codes:
 *   0x0 = uint, 0x1 = sint, 0x2 = float, 0x3 = bytes,
 *   0x4 = bool, 0x5 = enum, 0x6 = bitfield, 0x7 = match
 */

#define BINARY_TYPE_UINT     0x0
#define BINARY_TYPE_SINT     0x1
#define BINARY_TYPE_FLOAT    0x2
#define BINARY_TYPE_BYTES    0x3
#define BINARY_TYPE_BOOL     0x4
#define BINARY_TYPE_ENUM     0x5
#define BINARY_TYPE_BITFIELD 0x6
#define BINARY_TYPE_MATCH    0x7
#define BINARY_TYPE_SKIP     0x8

/* Convert type code + size to field_type_t */
static inline field_type_t binary_type_to_field_type(uint8_t type_code, uint8_t size) {
    switch (type_code) {
        case BINARY_TYPE_UINT:
            switch (size) {
                case 1: return FIELD_TYPE_U8;
                case 2: return FIELD_TYPE_U16;
                case 3: return FIELD_TYPE_U24;
                case 4: return FIELD_TYPE_U32;
                case 8: return FIELD_TYPE_U64;
            }
            break;
        case BINARY_TYPE_SINT:
            switch (size) {
                case 1: return FIELD_TYPE_S8;
                case 2: return FIELD_TYPE_S16;
                case 3: return FIELD_TYPE_S24;
                case 4: return FIELD_TYPE_S32;
                case 8: return FIELD_TYPE_S64;
            }
            break;
        case BINARY_TYPE_FLOAT:
            if (size == 2) return FIELD_TYPE_F16;
            if (size == 4) return FIELD_TYPE_F32;
            return FIELD_TYPE_F64;
        case BINARY_TYPE_BOOL:
            return FIELD_TYPE_BOOL;
        case BINARY_TYPE_BITFIELD:
            return FIELD_TYPE_BITS;
        case BINARY_TYPE_SKIP:
            return FIELD_TYPE_SKIP;
        case BINARY_TYPE_BYTES:
            return FIELD_TYPE_BYTES;
        case BINARY_TYPE_MATCH:
            return FIELD_TYPE_MATCH;
    }
    return FIELD_TYPE_U8;
}

/* Convert exponent byte to multiplier */
static inline double binary_exp_to_mult(uint8_t exp) {
    if (exp == 0) return 1.0;
    
    /* Special cases for 0.5-based */
    if (exp == 0x81) return 0.5;
    if (exp == 0x82) return 0.25;
    if (exp == 0x84) return 0.0625;
    
    /* Signed exponent for power of 10 */
    int8_t signed_exp = (exp > 127) ? (int8_t)(exp - 256) : (int8_t)exp;
    
    double mult = 1.0;
    if (signed_exp > 0) {
        for (int i = 0; i < signed_exp; i++) mult *= 10.0;
    } else {
        for (int i = 0; i < -signed_exp; i++) mult /= 10.0;
    }
    return mult;
}

/* IPSO object ID to name (common ones) */
static inline const char* ipso_to_name(uint16_t id, char* buf) {
    switch (id) {
        case 3303: return "temperature";
        case 3304: return "humidity";
        case 3315: return "pressure";
        case 3316: return "voltage";
        case 3317: return "current";
        case 3328: return "power";
        case 3330: return "distance";
        case 3301: return "illuminance";
        default:
            snprintf(buf, SCHEMA_MAX_NAME_LEN, "field_%04x", id);
            return buf;
    }
}

/* Load schema from binary format */
static inline int schema_load_binary(
    schema_t* schema,
    const uint8_t* data,
    size_t len
) {
    if (len < 5) return SCHEMA_ERR_PARSE;
    if (data[0] != 'P' || data[1] != 'S') return SCHEMA_ERR_PARSE;
    
    schema_init(schema);
    schema->version = data[2];
    schema->endian = (data[3] & 0x01) ? ENDIAN_LITTLE : ENDIAN_BIG;
    
    uint8_t field_count = data[4];
    size_t offset = 5;
    char name_buf[SCHEMA_MAX_NAME_LEN];
    
    for (int i = 0; i < field_count && offset < len; i++) {
        field_def_t f = {0};
        
        uint8_t type_byte = data[offset++];
        bool has_lookup = (type_byte & 0x80) != 0;
        uint8_t type_code = (type_byte >> 4) & 0x07;
        uint8_t size = type_byte & 0x0F;
        
        f.type = binary_type_to_field_type(type_code, size);
        f.size = size;
        
        /* Multiplier exponent */
        if (offset >= len) break;
        uint8_t mult_exp = data[offset++];
        double mult = binary_exp_to_mult(mult_exp);
        if (mult != 1.0) {
            f.mult = mult;
            f.has_mult = true;
        }
        
        /* Field ID (2 bytes LE) */
        if (offset + 1 >= len) break;
        uint16_t field_id = data[offset] | (data[offset + 1] << 8);
        offset += 2;
        
        /* Name from IPSO or generate */
        const char* name = ipso_to_name(field_id, name_buf);
        strncpy(f.name, name, SCHEMA_MAX_NAME_LEN - 1);
        
        /* Bitfield extra info */
        if (type_code == BINARY_TYPE_BITFIELD && offset < len) {
            uint8_t bf_byte = data[offset++];
            f.bit_start = (bf_byte >> 4) & 0x0F;
            f.bit_width = bf_byte & 0x0F;
            if (offset < len && data[offset] == 0x01) {
                f.consume = true;
                offset++;
            }
        }
        
        /* Add marker (0xA0) */
        if (offset < len && data[offset] == 0xA0) {
            offset++;
            if (offset + 1 < len) {
                int16_t add_val = (int16_t)(data[offset] | (data[offset + 1] << 8));
                f.add = add_val / 100.0;
                f.has_add = true;
                offset += 2;
            }
        }
        
        /* Lookup table */
        if (has_lookup && offset < len) {
            uint8_t lookup_count = data[offset++];
            for (int j = 0; j < lookup_count && j < SCHEMA_MAX_LOOKUP && offset < len; j++) {
                uint8_t key = data[offset++];
                if (offset >= len) break;
                uint8_t str_len = data[offset++];
                if (offset + str_len > len) break;
                
                f.lookup[f.lookup_count].key = key;
                size_t copy_len = (str_len < SCHEMA_MAX_NAME_LEN - 1) ? str_len : SCHEMA_MAX_NAME_LEN - 1;
                memcpy(f.lookup[f.lookup_count].value, &data[offset], copy_len);
                f.lookup[f.lookup_count].value[copy_len] = '\0';
                f.lookup_count++;
                offset += str_len;
            }
        }
        
        schema_add_field(schema, &f);
    }
    
    return SCHEMA_OK;
}

#ifdef __cplusplus
}
#endif

#endif /* SCHEMA_INTERPRETER_H */
