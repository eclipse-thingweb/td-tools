/*
 * rt.h - Runtime portability header
 *
 * Provides fixed-width types and common utilities for portable C code.
 * Target platforms: Linux, Zephyr RTOS, FreeRTOS
 */

#ifndef _rt_h_
#define _rt_h_

#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdarg.h>
#include <string.h>

/* Fixed-width integer types for protocol structures */
typedef uint8_t   u1_t;
typedef int8_t    s1_t;
typedef uint16_t  u2_t;
typedef int16_t   s2_t;
typedef uint32_t  u4_t;
typedef int32_t   s4_t;
typedef uint64_t  u8_t;
typedef int64_t   s8_t;

typedef unsigned int uint;
typedef const char*  str_t;

/* Timestamp type (microseconds since epoch or boot) */
typedef s8_t ustime_t;

#define USTIME_MIN ((ustime_t)0x8000000000000000LL)
#define USTIME_MAX ((ustime_t)0x7FFFFFFFFFFFFFFFLL)

/* Array size utility */
#define SIZE_ARRAY(a) (sizeof(a) / sizeof((a)[0]))

/* Member-to-struct pointer conversion */
#define memberof(type, memberp, member) \
    ((type*)((u1_t*)(memberp) - offsetof(type, member)))

/* Min/max macros (evaluate arguments once) */
#define rt_max(a, b) ({ \
    __typeof__(a) _a = (a); \
    __typeof__(b) _b = (b); \
    _a > _b ? _a : _b; \
})

#define rt_min(a, b) ({ \
    __typeof__(a) _a = (a); \
    __typeof__(b) _b = (b); \
    _a < _b ? _a : _b; \
})

/* Byte order utilities - little-endian (LoRaWAN MAC layer) */
static inline u2_t read_u2_le(const u1_t* buf) {
    return (u2_t)buf[0] | ((u2_t)buf[1] << 8);
}

static inline u4_t read_u4_le(const u1_t* buf) {
    return (u4_t)buf[0] | ((u4_t)buf[1] << 8) |
           ((u4_t)buf[2] << 16) | ((u4_t)buf[3] << 24);
}

static inline u8_t read_u8_le(const u1_t* buf) {
    return (u8_t)read_u4_le(buf) | ((u8_t)read_u4_le(buf + 4) << 32);
}

static inline void write_u2_le(u1_t* buf, u2_t val) {
    buf[0] = (u1_t)(val);
    buf[1] = (u1_t)(val >> 8);
}

static inline void write_u4_le(u1_t* buf, u4_t val) {
    buf[0] = (u1_t)(val);
    buf[1] = (u1_t)(val >> 8);
    buf[2] = (u1_t)(val >> 16);
    buf[3] = (u1_t)(val >> 24);
}

static inline void write_u8_le(u1_t* buf, u8_t val) {
    write_u4_le(buf, (u4_t)val);
    write_u4_le(buf + 4, (u4_t)(val >> 32));
}

/* Byte order utilities - big-endian (common sensor payloads) */
static inline u2_t read_u2_be(const u1_t* buf) {
    return ((u2_t)buf[0] << 8) | (u2_t)buf[1];
}

static inline s2_t read_s2_be(const u1_t* buf) {
    return (s2_t)read_u2_be(buf);
}

static inline u4_t read_u4_be(const u1_t* buf) {
    return ((u4_t)buf[0] << 24) | ((u4_t)buf[1] << 16) |
           ((u4_t)buf[2] << 8) | (u4_t)buf[3];
}

static inline s4_t read_s4_be(const u1_t* buf) {
    return (s4_t)read_u4_be(buf);
}

static inline void write_u2_be(u1_t* buf, u2_t val) {
    buf[0] = (u1_t)(val >> 8);
    buf[1] = (u1_t)(val);
}

static inline void write_s2_be(u1_t* buf, s2_t val) {
    write_u2_be(buf, (u2_t)val);
}

static inline void write_u4_be(u1_t* buf, u4_t val) {
    buf[0] = (u1_t)(val >> 24);
    buf[1] = (u1_t)(val >> 16);
    buf[2] = (u1_t)(val >> 8);
    buf[3] = (u1_t)(val);
}

static inline void write_s4_be(u1_t* buf, s4_t val) {
    write_u4_be(buf, (u4_t)val);
}

/* Log levels */
enum {
    LOG_DEBUG   = 0,
    LOG_VERBOSE = 1,
    LOG_INFO    = 2,
    LOG_NOTICE  = 3,
    LOG_WARNING = 4,
    LOG_ERROR   = 5,
    LOG_CRITICAL = 6
};

/* Forward declaration for logging */
void rt_log(int level, const char* mod, const char* fmt, ...);

#define LOG(level, mod, ...) rt_log(level, mod, __VA_ARGS__)

#endif /* _rt_h_ */
