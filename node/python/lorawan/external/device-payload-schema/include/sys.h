/*
 * sys.h - System abstraction interface
 *
 * Platform-specific implementations in:
 *   src/sys_linux.c   - Linux/POSIX
 *   src/sys_zephyr.c  - Zephyr RTOS
 *   src/sys_freertos.c - FreeRTOS
 *   src/sys_stub.c    - Stub for unit tests
 */

#ifndef _sys_h_
#define _sys_h_

#include "rt.h"

/*
 * Time functions
 */

/* Get monotonic time in microseconds */
ustime_t sys_time(void);

/* Get UTC time in microseconds, returns 0 if not available */
ustime_t sys_utc(void);

/* Sleep for specified microseconds */
void sys_usleep(ustime_t us);

/*
 * Random number generation
 */

/* Fill buffer with random bytes, returns 0 on success */
int sys_random(u1_t* buf, int len);

/*
 * Logging
 */

/* Output a log line (always newline-terminated) */
void sys_log_output(str_t line, int len);

/*
 * System identification
 */

/* Get system EUI (8 bytes) */
u8_t sys_eui(void);

/* Get version string */
str_t sys_version(void);

/*
 * Initialization
 */

/* Initialize system layer */
void sys_init(void);

/* Shutdown system layer */
void sys_shutdown(void);

/*
 * Error handling
 */

/* Fatal error - log and halt/restart */
void sys_fatal(int code);

/* Error codes */
enum {
    SYS_ERR_NONE       = 0,
    SYS_ERR_INIT       = 1,
    SYS_ERR_MEMORY     = 2,
    SYS_ERR_IO         = 3,
    SYS_ERR_TIMEOUT    = 4,
    SYS_ERR_PROTOCOL   = 5,
};

#endif /* _sys_h_ */
