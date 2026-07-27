/*
 * test_comprehensive.c - Comprehensive test suite for C schema interpreter
 *
 * Tests all types, bitfield syntaxes, endianness, and encoder.
 * Returns 0 on success, 1 on failure.
 *
 * Compile: gcc -O2 -I../include -o test_comprehensive test_comprehensive.c -lm
 */

#include <stdio.h>
#include <math.h>
#include <string.h>
#include "schema_interpreter.h"

static int tests_run = 0;
static int tests_passed = 0;
static int tests_failed = 0;

#define TCHECK(cond, msg) do { \
    tests_run++; \
    if (!(cond)) { \
        printf("  FAIL: %s (line %d)\n", msg, __LINE__); \
        tests_failed++; \
    } else { \
        tests_passed++; \
    } \
} while(0)

#define TCHECK_FLOAT(actual, expected, tol, msg) do { \
    tests_run++; \
    if (fabs((actual) - (expected)) > (tol)) { \
        printf("  FAIL: %s: expected %.6f, got %.6f (line %d)\n", msg, (double)(expected), (double)(actual), __LINE__); \
        tests_failed++; \
    } else { \
        tests_passed++; \
    } \
} while(0)

#define TCHECK_INT(actual, expected, msg) do { \
    tests_run++; \
    if ((actual) != (expected)) { \
        printf("  FAIL: %s: expected %lld, got %lld (line %d)\n", msg, (long long)(expected), (long long)(actual), __LINE__); \
        tests_failed++; \
    } else { \
        tests_passed++; \
    } \
} while(0)

#define TCHECK_STR(actual, expected, msg) do { \
    tests_run++; \
    if (strcmp((actual), (expected)) != 0) { \
        printf("  FAIL: %s: expected \"%s\", got \"%s\" (line %d)\n", msg, (expected), (actual), __LINE__); \
        tests_failed++; \
    } else { \
        tests_passed++; \
    } \
} while(0)

/* ============================================
 * Integer Type Tests
 * ============================================ */

void test_integer_types(void) {
    printf("--- Integer Types ---\n");
    
    /* u8 */
    {
        schema_t s; schema_init(&s);
        schema_add_field(&s, &(field_def_t){.name="val", .type=FIELD_TYPE_U8, .size=1});
        uint8_t buf[] = {0xFF};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 255.0, 0.01, "u8=255");
    }
    
    /* u16 big-endian */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_u16("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x01, 0x02};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 0x0102, 0.01, "u16 BE=0x0102");
    }
    
    /* u16 little-endian */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_LITTLE;
        field_def_t f = field_u16("val", ENDIAN_LITTLE);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x34, 0x12};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 0x1234, 0.01, "u16 LE=0x1234");
    }
    
    /* u24 big-endian */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_u24("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x01, 0x02, 0x03};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 0x010203, 0.01, "u24 BE=0x010203");
    }
    
    /* u24 little-endian */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_LITTLE;
        field_def_t f = field_u24("val", ENDIAN_LITTLE);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x03, 0x02, 0x01};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 0x010203, 0.01, "u24 LE=0x010203");
    }
    
    /* u32 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_u32("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x00, 0x01, 0x00, 0x00};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 65536.0, 0.01, "u32=65536");
    }
    
    /* s8 */
    {
        schema_t s; schema_init(&s);
        field_def_t f = field_s8("val");
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x80};  /* -128 */
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, -128.0, 0.01, "s8=-128");
    }
    
    /* s16 negative */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_s16("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0xFF, 0x9C};  /* -100 */
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, -100.0, 0.01, "s16=-100");
    }
    
    /* s24 negative */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_s24("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0xFF, 0xFF, 0x9C};  /* -100 */
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, -100.0, 0.01, "s24=-100");
    }
    
    /* s32 negative */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_LITTLE;
        field_def_t f = field_s32("val", ENDIAN_LITTLE);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0xFE, 0xFF, 0xFF, 0xFF};  /* -2 */
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, -2.0, 0.01, "s32 LE=-2");
    }
    
    /* u64 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_u64("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 256.0, 0.01, "u64=256");
    }
    
    /* s64 negative */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_s64("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, -1.0, 0.01, "s64=-1");
    }
}

/* ============================================
 * Float Type Tests
 * ============================================ */

void test_float_types(void) {
    printf("--- Float Types ---\n");
    
    /* f32 big-endian */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_f32("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        float fval = 1.5f;
        uint32_t bits;
        memcpy(&bits, &fval, sizeof(bits));
        uint8_t buf[4] = {(bits >> 24) & 0xFF, (bits >> 16) & 0xFF, (bits >> 8) & 0xFF, bits & 0xFF};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 1.5, 0.001, "f32 BE=1.5");
    }
    
    /* f32 little-endian */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_LITTLE;
        field_def_t f = field_f32("val", ENDIAN_LITTLE);
        schema_add_field(&s, &f);
        float fval = -1.5f;
        uint32_t bits;
        memcpy(&bits, &fval, sizeof(bits));
        uint8_t buf[4] = {bits & 0xFF, (bits >> 8) & 0xFF, (bits >> 16) & 0xFF, (bits >> 24) & 0xFF};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, -1.5, 0.001, "f32 LE=-1.5");
    }
    
    /* f64 big-endian */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_f64("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        double dval = 3.14159;
        uint64_t bits;
        memcpy(&bits, &dval, sizeof(bits));
        uint8_t buf[8];
        for (int i = 0; i < 8; i++) buf[i] = (bits >> (56 - i * 8)) & 0xFF;
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 3.14159, 0.0001, "f64 BE=3.14159");
    }
    
    /* f16 half-precision */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_f16("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        /* 0x4248 = 3.140625 in half-precision */
        uint8_t buf[] = {0x42, 0x48};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 3.140625, 0.01, "f16=3.14");
    }
    
    /* f16 = 1.0 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_f16("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        /* 0x3C00 = 1.0 in half-precision */
        uint8_t buf[] = {0x3C, 0x00};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 1.0, 0.001, "f16=1.0");
    }
    
    /* f16 = 0.0 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_f16("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x00, 0x00};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 0.0, 0.001, "f16=0.0");
    }
}

/* ============================================
 * Bitfield Syntax Tests
 * ============================================ */

void test_bitfield_syntaxes(void) {
    printf("--- Bitfield Syntaxes ---\n");
    
    /* Test parse_type_string for all 5 syntaxes */
    uint8_t bs, bw;
    
    /* Syntax 1: u8[3:4] - bits 3..4 inclusive = 2 bits */
    {
        field_type_t t = parse_type_string("u8[3:4]", &bs, &bw);
        TCHECK(t == FIELD_TYPE_BITS, "u8[3:4] type");
        TCHECK_INT(bs, 3, "u8[3:4] start");
        TCHECK_INT(bw, 2, "u8[3:4] width");
    }
    
    /* Syntax 2: u8[3+:2] */
    {
        field_type_t t = parse_type_string("u8[3+:2]", &bs, &bw);
        TCHECK(t == FIELD_TYPE_BITS, "u8[3+:2] type");
        TCHECK_INT(bs, 3, "u8[3+:2] start");
        TCHECK_INT(bw, 2, "u8[3+:2] width");
    }
    
    /* Syntax 3: bits<3,2> */
    {
        field_type_t t = parse_type_string("bits<3,2>", &bs, &bw);
        TCHECK(t == FIELD_TYPE_BITS, "bits<3,2> type");
        TCHECK_INT(bs, 3, "bits<3,2> start");
        TCHECK_INT(bw, 2, "bits<3,2> width");
    }
    
    /* Syntax 4: bits:2@3 */
    {
        field_type_t t = parse_type_string("bits:2@3", &bs, &bw);
        TCHECK(t == FIELD_TYPE_BITS, "bits:2@3 type");
        TCHECK_INT(bs, 3, "bits:2@3 start");
        TCHECK_INT(bw, 2, "bits:2@3 width");
    }
    
    /* Syntax 5: u8:2 (sequential) */
    {
        field_type_t t = parse_type_string("u8:2", &bs, &bw);
        TCHECK(t == FIELD_TYPE_BITS, "u8:2 type");
        TCHECK_INT(bs, 255, "u8:2 start=255 (sequential)");
        TCHECK_INT(bw, 2, "u8:2 width");
    }
    
    /* Decode: all 5 syntaxes on byte 0x18 (bits 3-4 set = 0b11) */
    uint8_t buf[] = {0x18};  /* 0b00011000 */
    
    {
        schema_t s; schema_init(&s);
        field_def_t f = field_bits("val", 3, 2, true);
        schema_add_field(&s, &f);
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 3.0, 0.01, "bits[3:4]=3");
    }
    
    /* Multiple bitfields from same byte */
    {
        schema_t s; schema_init(&s);
        uint8_t buf2[] = {0xF5};  /* 0b11110101 */
        field_def_t f1 = field_bits("a", 0, 1, false);
        field_def_t f2 = field_bits("b", 1, 1, false);
        field_def_t f3 = field_bits("c", 2, 1, false);
        field_def_t f4 = field_bits("d", 3, 5, true);
        schema_add_field(&s, &f1);
        schema_add_field(&s, &f2);
        schema_add_field(&s, &f3);
        schema_add_field(&s, &f4);
        decode_result_t r;
        schema_decode(&s, buf2, sizeof(buf2), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 1.0, 0.01, "bit0=1");
        TCHECK_FLOAT(r.fields[1].value.f64, 0.0, 0.01, "bit1=0");
        TCHECK_FLOAT(r.fields[2].value.f64, 1.0, 0.01, "bit2=1");
        TCHECK_FLOAT(r.fields[3].value.f64, 30.0, 0.01, "bits[3:7]=30");
    }
}

/* ============================================
 * Bool Type Tests
 * ============================================ */

void test_bool_type(void) {
    printf("--- Bool Type ---\n");
    
    /* bool bit 0 */
    {
        schema_t s; schema_init(&s);
        field_def_t f = field_bool("flag", 0, true);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x01};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK(r.fields[0].value.b == true, "bool bit0=true");
    }
    
    /* bool bit 7 */
    {
        schema_t s; schema_init(&s);
        field_def_t f = field_bool("flag", 7, true);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x80};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK(r.fields[0].value.b == true, "bool bit7=true");
    }
    
    /* bool false */
    {
        schema_t s; schema_init(&s);
        field_def_t f = field_bool("flag", 0, true);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x00};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK(r.fields[0].value.b == false, "bool=false");
    }
}

/* ============================================
 * Enum Type Tests
 * ============================================ */

void test_enum_type(void) {
    printf("--- Enum Type ---\n");
    
    {
        schema_t s; schema_init(&s);
        field_def_t f = field_enum("status", 1);
        field_add_lookup(&f, 0, "idle");
        field_add_lookup(&f, 1, "running");
        field_add_lookup(&f, 2, "error");
        schema_add_field(&s, &f);
        
        uint8_t buf[] = {0x01};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_STR(r.fields[0].value.str, "running", "enum=running");
    }
    
    /* Unknown enum value */
    {
        schema_t s; schema_init(&s);
        field_def_t f = field_enum("status", 1);
        field_add_lookup(&f, 0, "idle");
        field_add_lookup(&f, 1, "running");
        schema_add_field(&s, &f);
        
        uint8_t buf[] = {0xFF};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_STR(r.fields[0].value.str, "unknown(255)", "enum unknown");
    }
}

/* ============================================
 * Hex and Base64 Output Tests
 * ============================================ */

void test_hex_base64(void) {
    printf("--- Hex and Base64 ---\n");
    
    /* Hex */
    {
        schema_t s; schema_init(&s);
        field_def_t f = field_hex("mac", 4);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0xDE, 0xAD, 0xBE, 0xEF};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_STR(r.fields[0].value.str, "DEADBEEF", "hex=DEADBEEF");
    }
    
    /* Base64: {0x01, 0x02, 0x03} = "AQID" */
    {
        schema_t s; schema_init(&s);
        field_def_t f = {0};
        strncpy(f.name, "data", SCHEMA_MAX_NAME_LEN - 1);
        f.type = FIELD_TYPE_BASE64;
        f.size = 3;
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x01, 0x02, 0x03};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_STR(r.fields[0].value.str, "AQID", "base64=AQID");
    }
}

/* ============================================
 * Modifier Tests
 * ============================================ */

void test_modifiers(void) {
    printf("--- Modifiers ---\n");
    
    /* mult */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_s16("temp", ENDIAN_BIG);
        field_set_mult(&f, 0.01);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x09, 0x29};  /* 2345 * 0.01 = 23.45 */
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 23.45, 0.001, "mult=0.01");
    }
    
    /* add */
    {
        schema_t s; schema_init(&s);
        field_def_t f = field_u8("val");
        field_set_add(&f, 100.0);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x0A};  /* 10 + 100 = 110 */
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 110.0, 0.01, "add=100");
    }
    
    /* div */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_u16("val", ENDIAN_BIG);
        field_set_div(&f, 10.0);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x00, 0x64};  /* 100 / 10 = 10 */
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 10.0, 0.01, "div=10");
    }
    
    /* Lookup */
    {
        schema_t s; schema_init(&s);
        field_def_t f = field_u8("mode");
        field_add_lookup(&f, 0, "off");
        field_add_lookup(&f, 1, "low");
        field_add_lookup(&f, 2, "medium");
        field_add_lookup(&f, 3, "high");
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x02};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_STR(r.fields[0].value.str, "medium", "lookup=medium");
    }
}

/* ============================================
 * Skip and ASCII Tests
 * ============================================ */

void test_skip_ascii(void) {
    printf("--- Skip and ASCII ---\n");
    
    /* Skip */
    {
        schema_t s; schema_init(&s);
        field_def_t f1 = field_u8("header");
        field_def_t f2 = field_skip(2);
        field_def_t f3 = field_u8("data");
        schema_add_field(&s, &f1);
        schema_add_field(&s, &f2);
        schema_add_field(&s, &f3);
        uint8_t buf[] = {0x01, 0xAA, 0xBB, 0x02};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 1.0, 0.01, "header=1");
        TCHECK_FLOAT(r.fields[1].value.f64, 2.0, 0.01, "data=2 (after skip)");
        TCHECK_INT(r.bytes_consumed, 4, "skip consumed 4 bytes");
    }
    
    /* ASCII */
    {
        schema_t s; schema_init(&s);
        field_def_t f = field_ascii("name", 4);
        schema_add_field(&s, &f);
        uint8_t buf[] = {'T', 'E', 'S', 'T'};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_STR(r.fields[0].value.str, "TEST", "ascii=TEST");
    }
}

/* ============================================
 * Nibble Decimal Tests
 * ============================================ */

void test_nibble_decimal(void) {
    printf("--- Nibble Decimal ---\n");
    
    /* UDec */
    {
        schema_t s; schema_init(&s);
        field_def_t f = {0};
        strncpy(f.name, "val", SCHEMA_MAX_NAME_LEN - 1);
        f.type = FIELD_TYPE_UDEC;
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x37};  /* 3.7 */
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 3.7, 0.01, "udec=3.7");
    }
    
    /* SDec */
    {
        schema_t s; schema_init(&s);
        field_def_t f = {0};
        strncpy(f.name, "val", SCHEMA_MAX_NAME_LEN - 1);
        f.type = FIELD_TYPE_SDEC;
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x25};  /* 2.5 */
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 2.5, 0.01, "sdec=2.5");
    }
}

/* ============================================
 * Encode/Decode Roundtrip Tests
 * ============================================ */

void test_encode_roundtrip(void) {
    printf("--- Encode/Decode Roundtrip ---\n");
    
    /* u16 with mult */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_s16("temperature", ENDIAN_BIG);
        field_set_mult(&f, 0.01);
        schema_add_field(&s, &f);
        
        encode_inputs_t inputs; encode_inputs_init(&inputs);
        encode_inputs_add_double(&inputs, "temperature", 23.45);
        
        encode_result_t enc;
        schema_encode(&s, &inputs, &enc);
        TCHECK_INT(enc.len, 2, "encoded 2 bytes");
        TCHECK_INT(enc.data[0], 0x09, "byte[0]=0x09");
        TCHECK_INT(enc.data[1], 0x29, "byte[1]=0x29");
        
        /* Decode back */
        decode_result_t dec;
        schema_decode(&s, enc.data, enc.len, &dec);
        TCHECK_FLOAT(dec.fields[0].value.f64, 23.45, 0.01, "roundtrip temp=23.45");
    }
    
    /* Multi-field roundtrip */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f1 = field_u8("header");
        field_def_t f2 = field_s16("temp", ENDIAN_BIG);
        field_set_mult(&f2, 0.01);
        field_def_t f3 = field_u16("batt", ENDIAN_BIG);
        schema_add_field(&s, &f1);
        schema_add_field(&s, &f2);
        schema_add_field(&s, &f3);
        
        encode_inputs_t inputs; encode_inputs_init(&inputs);
        encode_inputs_add_double(&inputs, "header", 1.0);
        encode_inputs_add_double(&inputs, "temp", 25.0);
        encode_inputs_add_double(&inputs, "batt", 3300.0);
        
        encode_result_t enc;
        schema_encode(&s, &inputs, &enc);
        TCHECK_INT(enc.len, 5, "multi-field encoded 5 bytes");
        
        decode_result_t dec;
        schema_decode(&s, enc.data, enc.len, &dec);
        TCHECK_FLOAT(dec.fields[0].value.f64, 1.0, 0.01, "header=1");
        TCHECK_FLOAT(dec.fields[1].value.f64, 25.0, 0.01, "temp=25.0");
        TCHECK_FLOAT(dec.fields[2].value.f64, 3300.0, 0.01, "batt=3300");
    }
}

/* ============================================
 * Buffer Safety Tests
 * ============================================ */

void test_buffer_safety(void) {
    printf("--- Buffer Safety ---\n");
    
    /* Short buffer for u16 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_u16("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x01};
        decode_result_t r;
        int rc = schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK(rc == SCHEMA_ERR_BUFFER, "short buffer u16");
    }
    
    /* Short buffer for u32 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_u32("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x01, 0x02};
        decode_result_t r;
        int rc = schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK(rc == SCHEMA_ERR_BUFFER, "short buffer u32");
    }
    
    /* Empty buffer */
    {
        schema_t s; schema_init(&s);
        field_def_t f = field_u8("val");
        schema_add_field(&s, &f);
        decode_result_t r;
        (void)schema_decode(&s, NULL, 0, &r);
        TCHECK(r.field_count == 0, "empty buffer no fields");
    }
}

/* ============================================
 * Binary Schema Loading Tests
 * ============================================ */

void test_binary_schema(void) {
    printf("--- Binary Schema ---\n");
    
    static const uint8_t binary_schema[] = {
        0x50, 0x53, 0x01, 0x00, 0x03,      /* Header: PS v1, big-endian, 3 fields */
        0x12, 0xFE, 0xE7, 0x0C,             /* s16, mult=0.01, IPSO 3303 (temperature) */
        0x01, 0x81, 0xE8, 0x0C,             /* u8, mult=0.5, IPSO 3304 (humidity) */
        0x02, 0x00, 0xF4, 0x0C,             /* u16, mult=1.0, IPSO 3316 (voltage) */
    };
    
    schema_t s;
    int rc = schema_load_binary(&s, binary_schema, sizeof(binary_schema));
    TCHECK(rc == SCHEMA_OK, "binary load OK");
    TCHECK_INT(s.field_count, 3, "binary 3 fields");
    
    /* Decode */
    uint8_t payload[] = {0x09, 0x29, 0x82, 0x0C, 0xE4};
    decode_result_t r;
    schema_decode(&s, payload, sizeof(payload), &r);
    TCHECK_FLOAT(r.fields[0].value.f64, 23.45, 0.01, "binary temp=23.45");
    TCHECK_FLOAT(r.fields[1].value.f64, 65.0, 0.01, "binary hum=65");
    TCHECK_FLOAT(r.fields[2].value.f64, 3300.0, 1.0, "binary batt=3300");
}

/* ============================================
 * Match/Conditional Tests
 * ============================================ */

void test_match(void) {
    printf("--- Match/Conditional ---\n");
    
    schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
    
    /* msg_type field */
    field_def_t f1 = field_u8("msg_type");
    field_set_var(&f1, "msg_type");
    schema_add_field(&s, &f1);
    
    /* Match on msg_type (single value) */
    field_def_t match_f = {0};
    strncpy(match_f.name, "_match", SCHEMA_MAX_NAME_LEN - 1);
    match_f.type = FIELD_TYPE_MATCH;
    strncpy(match_f.match_var, "$msg_type", SCHEMA_MAX_NAME_LEN - 1);
    
    /* Initialize match_list to -1 (terminator) to avoid false matches */
    for (int ci = 0; ci < SCHEMA_MAX_CASES; ci++) {
        for (int ji = 0; ji < 8; ji++) {
            match_f.cases[ci].match_list[ji] = -1;
        }
    }
    
    /* Case 1: temp (s16) at fields[2] */
    match_f.cases[0].match_value = 1;
    match_f.cases[0].field_start = 2;
    match_f.cases[0].field_count = 1;
    
    /* Case 2: humidity (u8) at fields[3] */
    match_f.cases[1].match_value = 2;
    match_f.cases[1].field_start = 3;
    match_f.cases[1].field_count = 1;
    
    match_f.case_count = 2;
    schema_add_field(&s, &match_f);
    
    /* Case 1 fields */
    field_def_t temp_f = field_s16("temperature", ENDIAN_BIG);
    field_set_mult(&temp_f, 0.01);
    schema_add_field(&s, &temp_f);
    
    /* Case 2 fields */
    field_def_t hum_f = field_u8("humidity");
    schema_add_field(&s, &hum_f);
    
    /* Test case 1 */
    {
        uint8_t buf[] = {0x01, 0x09, 0x29};  /* msg_type=1, temp=2345 */
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK(r.field_count >= 2, "match case 1 fields");
        TCHECK_FLOAT(result_get_double(&r, "temperature", 0), 23.45, 0.01, "match temp=23.45");
    }
    
    /* Test case 2 */
    {
        uint8_t buf[] = {0x02, 0x64};  /* msg_type=2, humidity=100 */
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK(r.field_count >= 2, "match case 2 fields");
        TCHECK_FLOAT(result_get_double(&r, "humidity", 0), 100.0, 0.01, "match hum=100");
    }
}

/* ============================================
 * Variable Storage Tests
 * ============================================ */

void test_variables(void) {
    printf("--- Variable Storage ---\n");
    
    var_context_t ctx = {0};
    
    var_set(&ctx, "temperature", 2345);
    var_set(&ctx, "humidity", 65);
    
    TCHECK_INT(var_get(&ctx, "temperature"), 2345, "var_get temperature");
    TCHECK_INT(var_get(&ctx, "humidity"), 65, "var_get humidity");
    TCHECK_INT(var_get(&ctx, "missing"), 0, "var_get missing=0");
    
    /* Update existing */
    var_set(&ctx, "temperature", 9999);
    TCHECK_INT(var_get(&ctx, "temperature"), 9999, "var_set update");
}

/* ============================================
 * Type Parsing Tests
 * ============================================ */

void test_type_parsing(void) {
    printf("--- Type Parsing ---\n");
    
    uint8_t bs, bw;
    
    TCHECK(parse_type_string("u8", &bs, &bw) == FIELD_TYPE_U8, "parse u8");
    TCHECK(parse_type_string("uint8", &bs, &bw) == FIELD_TYPE_U8, "parse uint8");
    TCHECK(parse_type_string("u16", &bs, &bw) == FIELD_TYPE_U16, "parse u16");
    TCHECK(parse_type_string("uint16", &bs, &bw) == FIELD_TYPE_U16, "parse uint16");
    TCHECK(parse_type_string("u24", &bs, &bw) == FIELD_TYPE_U24, "parse u24");
    TCHECK(parse_type_string("uint24", &bs, &bw) == FIELD_TYPE_U24, "parse uint24");
    TCHECK(parse_type_string("u32", &bs, &bw) == FIELD_TYPE_U32, "parse u32");
    TCHECK(parse_type_string("uint32", &bs, &bw) == FIELD_TYPE_U32, "parse uint32");
    TCHECK(parse_type_string("u64", &bs, &bw) == FIELD_TYPE_U64, "parse u64");
    TCHECK(parse_type_string("uint64", &bs, &bw) == FIELD_TYPE_U64, "parse uint64");
    
    TCHECK(parse_type_string("s8", &bs, &bw) == FIELD_TYPE_S8, "parse s8");
    TCHECK(parse_type_string("i8", &bs, &bw) == FIELD_TYPE_S8, "parse i8");
    TCHECK(parse_type_string("int8", &bs, &bw) == FIELD_TYPE_S8, "parse int8");
    TCHECK(parse_type_string("s16", &bs, &bw) == FIELD_TYPE_S16, "parse s16");
    TCHECK(parse_type_string("i16", &bs, &bw) == FIELD_TYPE_S16, "parse i16");
    TCHECK(parse_type_string("s24", &bs, &bw) == FIELD_TYPE_S24, "parse s24");
    TCHECK(parse_type_string("i24", &bs, &bw) == FIELD_TYPE_S24, "parse i24");
    TCHECK(parse_type_string("s32", &bs, &bw) == FIELD_TYPE_S32, "parse s32");
    TCHECK(parse_type_string("s64", &bs, &bw) == FIELD_TYPE_S64, "parse s64");
    TCHECK(parse_type_string("i64", &bs, &bw) == FIELD_TYPE_S64, "parse i64");
    TCHECK(parse_type_string("int64", &bs, &bw) == FIELD_TYPE_S64, "parse int64");
    
    TCHECK(parse_type_string("f16", &bs, &bw) == FIELD_TYPE_F16, "parse f16");
    TCHECK(parse_type_string("f32", &bs, &bw) == FIELD_TYPE_F32, "parse f32");
    TCHECK(parse_type_string("float", &bs, &bw) == FIELD_TYPE_F32, "parse float");
    TCHECK(parse_type_string("f64", &bs, &bw) == FIELD_TYPE_F64, "parse f64");
    TCHECK(parse_type_string("double", &bs, &bw) == FIELD_TYPE_F64, "parse double");
    
    TCHECK(parse_type_string("bool", &bs, &bw) == FIELD_TYPE_BOOL, "parse bool");
    TCHECK(parse_type_string("skip", &bs, &bw) == FIELD_TYPE_SKIP, "parse skip");
    TCHECK(parse_type_string("ascii", &bs, &bw) == FIELD_TYPE_ASCII, "parse ascii");
    TCHECK(parse_type_string("string", &bs, &bw) == FIELD_TYPE_ASCII, "parse string");
    TCHECK(parse_type_string("hex", &bs, &bw) == FIELD_TYPE_HEX, "parse hex");
    TCHECK(parse_type_string("base64", &bs, &bw) == FIELD_TYPE_BASE64, "parse base64");
    TCHECK(parse_type_string("bytes", &bs, &bw) == FIELD_TYPE_BYTES, "parse bytes");
    TCHECK(parse_type_string("enum", &bs, &bw) == FIELD_TYPE_ENUM, "parse enum");
    TCHECK(parse_type_string("match", &bs, &bw) == FIELD_TYPE_MATCH, "parse match");
    TCHECK(parse_type_string("udec", &bs, &bw) == FIELD_TYPE_UDEC, "parse udec");
    TCHECK(parse_type_string("sdec", &bs, &bw) == FIELD_TYPE_SDEC, "parse sdec");
    TCHECK(parse_type_string("garbage", &bs, &bw) == FIELD_TYPE_UNKNOWN, "parse unknown");
}

/* ============================================
 * Short Buffer Tests (per type)
 * ============================================ */

void test_short_buffers(void) {
    printf("--- Short Buffer Tests ---\n");

    /* u24: needs 3, give 2 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_u24("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x01, 0x02};
        decode_result_t r;
        int rc = schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK(rc == SCHEMA_ERR_BUFFER, "short buffer u24");
    }

    /* u64: needs 8, give 4 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_u64("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x01, 0x02, 0x03, 0x04};
        decode_result_t r;
        int rc = schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK(rc == SCHEMA_ERR_BUFFER, "short buffer u64");
    }

    /* s64: needs 8, give 7 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_s64("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
        decode_result_t r;
        int rc = schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK(rc == SCHEMA_ERR_BUFFER, "short buffer s64");
    }

    /* f16: needs 2, give 1 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_f16("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x3C};
        decode_result_t r;
        int rc = schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK(rc == SCHEMA_ERR_BUFFER, "short buffer f16");
    }

    /* f64: needs 8, give 4 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_f64("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x40, 0x09, 0x21, 0xFB};
        decode_result_t r;
        int rc = schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK(rc == SCHEMA_ERR_BUFFER, "short buffer f64");
    }

    /* ascii: needs 4, give 2 */
    {
        schema_t s; schema_init(&s);
        field_def_t f = field_ascii("val", 4);
        schema_add_field(&s, &f);
        uint8_t buf[] = {'A', 'B'};
        decode_result_t r;
        int rc = schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK(rc == SCHEMA_ERR_BUFFER, "short buffer ascii");
    }

    /* hex: needs 4, give 2 */
    {
        schema_t s; schema_init(&s);
        field_def_t f = field_hex("val", 4);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0xDE, 0xAD};
        decode_result_t r;
        int rc = schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK(rc == SCHEMA_ERR_BUFFER, "short buffer hex");
    }

    /* base64: needs 3, give 1 */
    {
        schema_t s; schema_init(&s);
        field_def_t f = {0};
        strncpy(f.name, "val", SCHEMA_MAX_NAME_LEN - 1);
        f.type = FIELD_TYPE_BASE64;
        f.size = 3;
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x01};
        decode_result_t r;
        int rc = schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK(rc == SCHEMA_ERR_BUFFER, "short buffer base64");
    }

    /* s16: needs 2, give 1 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_s16("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0xFF};
        decode_result_t r;
        int rc = schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK(rc == SCHEMA_ERR_BUFFER, "short buffer s16");
    }

    /* s24: needs 3, give 1 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_s24("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0xFF};
        decode_result_t r;
        int rc = schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK(rc == SCHEMA_ERR_BUFFER, "short buffer s24");
    }

    /* f32: needs 4, give 2 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_f32("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x3F, 0xC0};
        decode_result_t r;
        int rc = schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK(rc == SCHEMA_ERR_BUFFER, "short buffer f32");
    }
}

/* ============================================
 * Integer Boundary Value Tests
 * ============================================ */

void test_integer_boundaries(void) {
    printf("--- Integer Boundary Values ---\n");

    /* u8 = 0 */
    {
        schema_t s; schema_init(&s);
        schema_add_field(&s, &(field_def_t){.name="val", .type=FIELD_TYPE_U8, .size=1});
        uint8_t buf[] = {0x00};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 0.0, 0.01, "u8=0");
    }

    /* u16 = 0xFFFF = 65535 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_u16("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0xFF, 0xFF};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 65535.0, 0.01, "u16=65535");
    }

    /* u16 = 0 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_u16("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x00, 0x00};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 0.0, 0.01, "u16=0");
    }

    /* s8 = +127 */
    {
        schema_t s; schema_init(&s);
        field_def_t f = field_s8("val");
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x7F};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 127.0, 0.01, "s8=+127");
    }

    /* s8 = 0 */
    {
        schema_t s; schema_init(&s);
        field_def_t f = field_s8("val");
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x00};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 0.0, 0.01, "s8=0");
    }

    /* s16 = -32768 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_s16("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x80, 0x00};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, -32768.0, 0.01, "s16=-32768");
    }

    /* s16 = +32767 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_s16("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x7F, 0xFF};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 32767.0, 0.01, "s16=+32767");
    }

    /* u32 = 0xFFFFFFFF */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_u32("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0xFF, 0xFF, 0xFF, 0xFF};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 4294967295.0, 1.0, "u32=0xFFFFFFFF");
    }

    /* s32 = -2147483648 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_s32("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x80, 0x00, 0x00, 0x00};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, -2147483648.0, 1.0, "s32=-2147483648");
    }
}

/* ============================================
 * Float Edge Case Tests
 * ============================================ */

void test_float_edge_cases(void) {
    printf("--- Float Edge Cases ---\n");

    /* f16 = -1.0 (0xBC00 BE) */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_f16("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0xBC, 0x00};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, -1.0, 0.001, "f16=-1.0");
    }

    /* f32 = 0.0 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_f32("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x00, 0x00, 0x00, 0x00};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 0.0, 0.001, "f32=0.0");
    }

    /* f32 = -42.5 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_f32("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        float fval = -42.5f;
        uint32_t bits;
        memcpy(&bits, &fval, sizeof(bits));
        uint8_t buf[4] = {(bits >> 24) & 0xFF, (bits >> 16) & 0xFF,
                          (bits >> 8) & 0xFF, bits & 0xFF};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, -42.5, 0.01, "f32=-42.5");
    }

    /* f64 = -99.99 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
        field_def_t f = field_f64("val", ENDIAN_BIG);
        schema_add_field(&s, &f);
        double dval = -99.99;
        uint64_t bits;
        memcpy(&bits, &dval, sizeof(bits));
        uint8_t buf[8];
        for (int i = 0; i < 8; i++) buf[i] = (bits >> (56 - i * 8)) & 0xFF;
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, -99.99, 0.01, "f64=-99.99");
    }

    /* f16 little-endian = 1.5 (0x3E00 => LE: 0x00 0x3E) */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_LITTLE;
        field_def_t f = field_f16("val", ENDIAN_LITTLE);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x00, 0x3E};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 1.5, 0.001, "f16 LE=1.5");
    }
}

/* ============================================
 * Binary Schema Error Tests
 * ============================================ */

void test_binary_schema_errors(void) {
    printf("--- Binary Schema Errors ---\n");

    /* Wrong magic bytes */
    {
        schema_t s;
        uint8_t bad_magic[] = {'X', 'X', 0x01, 0x00, 0x01, 0x01, 0x00, 0xE7, 0x0C};
        int rc = schema_load_binary(&s, bad_magic, sizeof(bad_magic));
        TCHECK(rc == SCHEMA_ERR_PARSE, "binary wrong magic");
    }

    /* Truncated header (< 5 bytes) */
    {
        schema_t s;
        uint8_t truncated[] = {'P', 'S', 0x01};
        int rc = schema_load_binary(&s, truncated, sizeof(truncated));
        TCHECK(rc == SCHEMA_ERR_PARSE, "binary truncated header");
    }

    /* Empty data */
    {
        schema_t s;
        int rc = schema_load_binary(&s, NULL, 0);
        TCHECK(rc == SCHEMA_ERR_PARSE, "binary empty data");
    }

    /* Valid header, 0 fields */
    {
        schema_t s;
        uint8_t zero_fields[] = {'P', 'S', 0x01, 0x00, 0x00};
        int rc = schema_load_binary(&s, zero_fields, sizeof(zero_fields));
        TCHECK(rc == SCHEMA_OK, "binary 0 fields OK");
        TCHECK_INT(s.field_count, 0, "binary 0 fields count");
    }
}

/* ============================================
 * Schema Field Overflow Test
 * ============================================ */

void test_schema_field_overflow(void) {
    printf("--- Schema Field Overflow ---\n");

    schema_t s;
    schema_init(&s);

    /* Add SCHEMA_MAX_FIELDS + 1 fields */
    for (int i = 0; i < SCHEMA_MAX_FIELDS + 1; i++) {
        char name[SCHEMA_MAX_NAME_LEN];
        snprintf(name, sizeof(name), "f%d", i);
        field_def_t f = field_u8(name);
        schema_add_field(&s, &f);
    }

    TCHECK_INT(s.field_count, SCHEMA_MAX_FIELDS, "field_count capped at SCHEMA_MAX_FIELDS");
}

/* ============================================
 * result_get_field NULL on Missing Name
 * ============================================ */

void test_result_get_field_null(void) {
    printf("--- result_get_field NULL ---\n");

    schema_t s; schema_init(&s);
    schema_add_field(&s, &(field_def_t){.name="temperature", .type=FIELD_TYPE_U8, .size=1});
    uint8_t buf[] = {0x42};
    decode_result_t r;
    schema_decode(&s, buf, sizeof(buf), &r);

    TCHECK(result_get_field(&r, "temperature") != NULL, "existing field found");
    TCHECK(result_get_field(&r, "nonexistent") == NULL, "missing field returns NULL");
    TCHECK_FLOAT(result_get_double(&r, "nonexistent", -999.0), -999.0, 0.01,
                 "result_get_double default for missing");
    TCHECK(result_get_string(&r, "nonexistent") == NULL, "result_get_string NULL for missing");
}

/* ============================================
 * Encode with Missing Input Field
 * ============================================ */

void test_encode_missing_field(void) {
    printf("--- Encode Missing Field ---\n");

    schema_t s; schema_init(&s); s.endian = ENDIAN_BIG;
    field_def_t f1 = field_u8("temperature");
    field_def_t f2 = field_u8("humidity");
    schema_add_field(&s, &f1);
    schema_add_field(&s, &f2);

    /* Only provide temperature, missing humidity */
    encode_inputs_t inputs; encode_inputs_init(&inputs);
    encode_inputs_add_double(&inputs, "temperature", 25.0);

    encode_result_t enc;
    int rc = schema_encode(&s, &inputs, &enc);
    TCHECK(rc != SCHEMA_OK, "encode missing field returns error");
}

/* ============================================
 * Negative Add Modifier
 * ============================================ */

void test_negative_add_modifier(void) {
    printf("--- Negative Add Modifier ---\n");

    schema_t s; schema_init(&s);
    field_def_t f = field_u8("val");
    field_set_add(&f, -40.0);
    schema_add_field(&s, &f);
    uint8_t buf[] = {200};  /* 200 + (-40) = 160 */
    decode_result_t r;
    schema_decode(&s, buf, sizeof(buf), &r);
    TCHECK_FLOAT(r.fields[0].value.f64, 160.0, 0.01, "add=-40: 200+(-40)=160");
}

/* ============================================
 * Bitfield on Empty Buffer
 * ============================================ */

void test_bitfield_empty_buffer(void) {
    printf("--- Bitfield Empty Buffer ---\n");

    schema_t s; schema_init(&s);
    field_def_t f = field_bits("val", 3, 2, true);
    schema_add_field(&s, &f);
    decode_result_t r;
    (void)schema_decode(&s, NULL, 0, &r);
    TCHECK(r.field_count == 0, "bitfield empty buffer no fields");
}

/* ============================================
 * Bool on Empty Buffer
 * ============================================ */

void test_bool_empty_buffer(void) {
    printf("--- Bool Empty Buffer ---\n");

    schema_t s; schema_init(&s);
    field_def_t f = field_bool("flag", 0, true);
    schema_add_field(&s, &f);
    decode_result_t r;
    int rc = schema_decode(&s, NULL, 0, &r);
    (void)rc;
    TCHECK(r.field_count == 0, "bool empty buffer no fields");
}

/* ============================================
 * Little-Endian Signed Types (s24, s32 LE)
 * ============================================ */

void test_little_endian_signed(void) {
    printf("--- Little-Endian Signed ---\n");

    /* s24 LE = -100 (0x9C 0xFF 0xFF in LE) */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_LITTLE;
        field_def_t f = field_s24("val", ENDIAN_LITTLE);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x9C, 0xFF, 0xFF};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, -100.0, 0.01, "s24 LE=-100");
    }

    /* s24 LE = +100 (0x64 0x00 0x00 in LE) */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_LITTLE;
        field_def_t f = field_s24("val", ENDIAN_LITTLE);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x64, 0x00, 0x00};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 100.0, 0.01, "s24 LE=+100");
    }

    /* s32 LE = -100000 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_LITTLE;
        field_def_t f = field_s32("val", ENDIAN_LITTLE);
        schema_add_field(&s, &f);
        /* -100000 = 0xFFFE7960, LE: 0x60 0x79 0xFE 0xFF */
        uint8_t buf[] = {0x60, 0x79, 0xFE, 0xFF};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, -100000.0, 0.01, "s32 LE=-100000");
    }

    /* s64 LE = -1 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_LITTLE;
        field_def_t f = field_s64("val", ENDIAN_LITTLE);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, -1.0, 0.01, "s64 LE=-1");
    }

    /* u64 LE = 256 */
    {
        schema_t s; schema_init(&s); s.endian = ENDIAN_LITTLE;
        field_def_t f = field_u64("val", ENDIAN_LITTLE);
        schema_add_field(&s, &f);
        uint8_t buf[] = {0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_FLOAT(r.fields[0].value.f64, 256.0, 0.01, "u64 LE=256");
    }
}

/* ============================================
 * Enum Encode Test (C encoder: FIELD_TYPE_ENUM)
 * ============================================ */

void test_enum_encode(void) {
    printf("--- Enum Encode ---\n");

    /* C encoder doesn't support FIELD_TYPE_ENUM - should return error */
    {
        schema_t s; schema_init(&s);
        field_def_t f = field_enum("status", 1);
        field_add_lookup(&f, 0, "idle");
        field_add_lookup(&f, 1, "running");
        schema_add_field(&s, &f);

        encode_inputs_t inputs; encode_inputs_init(&inputs);
        encode_inputs_add_double(&inputs, "status", 1.0);

        encode_result_t enc;
        int rc = schema_encode(&s, &inputs, &enc);
        TCHECK(rc == SCHEMA_ERR_UNSUPPORTED, "enum encode unsupported");
    }
}

/* ============================================
 * Lookup Out-of-Range
 * ============================================ */

void test_lookup_out_of_range(void) {
    printf("--- Lookup Out-of-Range ---\n");

    /* u8 lookup with value=10 but only 4 entries (keys 0-3) */
    {
        schema_t s; schema_init(&s);
        field_def_t f = field_u8("mode");
        field_add_lookup(&f, 0, "off");
        field_add_lookup(&f, 1, "low");
        field_add_lookup(&f, 2, "medium");
        field_add_lookup(&f, 3, "high");
        schema_add_field(&s, &f);

        uint8_t buf[] = {0x0A};  /* 10 - not in lookup */
        decode_result_t r;
        int rc = schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK(rc == SCHEMA_OK, "lookup out-of-range OK");
        /* Should store raw integer value when no match */
        TCHECK_INT(r.fields[0].value.i64, 10, "lookup no match raw=10");
    }

    /* Enum with value not in lookup -> "unknown(N)" string */
    {
        schema_t s; schema_init(&s);
        field_def_t f = field_enum("status", 1);
        field_add_lookup(&f, 0, "idle");
        field_add_lookup(&f, 1, "running");
        schema_add_field(&s, &f);

        uint8_t buf[] = {0x05};  /* 5 - not in lookup */
        decode_result_t r;
        schema_decode(&s, buf, sizeof(buf), &r);
        TCHECK_STR(r.fields[0].value.str, "unknown(5)", "enum out-of-range=unknown(5)");
    }
}

/* ============================================
 * Main
 * ============================================ */

int main(void) {
    printf("=== Comprehensive C Schema Interpreter Tests ===\n\n");
    
    test_integer_types();
    test_float_types();
    test_bitfield_syntaxes();
    test_bool_type();
    test_enum_type();
    test_hex_base64();
    test_modifiers();
    test_skip_ascii();
    test_nibble_decimal();
    test_encode_roundtrip();
    test_buffer_safety();
    test_binary_schema();
    test_match();
    test_variables();
    test_type_parsing();
    test_short_buffers();
    test_integer_boundaries();
    test_float_edge_cases();
    test_binary_schema_errors();
    test_schema_field_overflow();
    test_result_get_field_null();
    test_encode_missing_field();
    test_negative_add_modifier();
    test_bitfield_empty_buffer();
    test_bool_empty_buffer();
    test_little_endian_signed();
    test_enum_encode();
    test_lookup_out_of_range();
    
    printf("\n=== Results ===\n");
    printf("Tests run:    %d\n", tests_run);
    printf("Tests passed: %d\n", tests_passed);
    printf("Tests failed: %d\n", tests_failed);
    
    if (tests_failed == 0) {
        printf("\nALL TESTS PASSED\n");
        return 0;
    } else {
        printf("\n%d TESTS FAILED\n", tests_failed);
        return 1;
    }
}
