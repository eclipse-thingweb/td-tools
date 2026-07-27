/*
 * sys_linux.c - Linux/POSIX system abstraction
 */

#define _GNU_SOURCE
#include "sys.h"
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdarg.h>

static int log_level = LOG_INFO;

ustime_t sys_time(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (ustime_t)ts.tv_sec * 1000000LL + ts.tv_nsec / 1000;
}

ustime_t sys_utc(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_REALTIME, &ts) != 0) {
        return 0;
    }
    return (ustime_t)ts.tv_sec * 1000000LL + ts.tv_nsec / 1000;
}

void sys_usleep(ustime_t us) {
    if (us > 0) {
        usleep((useconds_t)us);
    }
}

int sys_random(u1_t* buf, int len) {
    int fd = open("/dev/urandom", O_RDONLY);
    if (fd < 0) {
        return -1;
    }
    
    int total = 0;
    while (total < len) {
        int n = read(fd, buf + total, len - total);
        if (n <= 0) {
            close(fd);
            return -1;
        }
        total += n;
    }
    
    close(fd);
    return 0;
}

void sys_log_output(str_t line, int len) {
    fwrite(line, 1, len, stderr);
    fflush(stderr);
}

void rt_log(int level, const char* mod, const char* fmt, ...) {
    if (level < log_level) {
        return;
    }
    
    static const char* level_names[] = {
        "DEBUG", "VERB", "INFO", "NOTE", "WARN", "ERROR", "CRIT"
    };
    
    char buf[512];
    int pos = 0;
    
    /* Timestamp */
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    struct tm tm;
    localtime_r(&ts.tv_sec, &tm);
    pos += snprintf(buf + pos, sizeof(buf) - pos,
        "%02d:%02d:%02d.%03d [%-5s] %-6s: ",
        tm.tm_hour, tm.tm_min, tm.tm_sec, (int)(ts.tv_nsec / 1000000),
        level_names[level], mod);
    
    /* Message */
    va_list ap;
    va_start(ap, fmt);
    pos += vsnprintf(buf + pos, sizeof(buf) - pos, fmt, ap);
    va_end(ap);
    
    /* Newline */
    if (pos < (int)sizeof(buf) - 1) {
        buf[pos++] = '\n';
    }
    
    sys_log_output(buf, pos);
}

u8_t sys_eui(void) {
    /* For testing, generate a pseudo-random EUI */
    static u8_t eui = 0;
    if (eui == 0) {
        u1_t buf[8];
        sys_random(buf, 8);
        eui = read_u8_le(buf);
    }
    return eui;
}

str_t sys_version(void) {
    return "prototype-0.1.0-linux";
}

void sys_init(void) {
    /* Nothing to initialize for basic Linux */
}

void sys_shutdown(void) {
    /* Nothing to clean up */
}

void sys_fatal(int code) {
    char buf[64];
    int len = snprintf(buf, sizeof(buf), "FATAL ERROR: code=%d\n", code);
    sys_log_output(buf, len);
    exit(code);
}
