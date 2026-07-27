/*
 * selftests.c - Self-test framework implementation
 */

#include "selftests.h"
#include "sys.h"
#include <stdio.h>

static int test_failures = 0;
static int test_count = 0;

void selftest_fail(const char* expr, const char* file, int line) {
    char buf[256];
    int len = snprintf(buf, sizeof(buf), "FAIL: %s at %s:%d\n", expr, file, line);
    sys_log_output(buf, len);
    test_failures++;
}

/* Array of all test functions */
typedef void (*selftest_fn)(void);

static const selftest_fn all_tests[] = {
    selftest_codec,
    selftest_protocol,
    /* Add new test functions here */
};

int selftests_run(void) {
    test_failures = 0;
    test_count = SIZE_ARRAY(all_tests);
    
    char buf[128];
    int len;
    
    len = snprintf(buf, sizeof(buf), "Running %d self-test modules...\n", test_count);
    sys_log_output(buf, len);
    
    for (int i = 0; i < test_count; i++) {
        all_tests[i]();
    }
    
    if (test_failures == 0) {
        len = snprintf(buf, sizeof(buf), "ALL %d SELFTESTS PASSED\n", test_count);
        sys_log_output(buf, len);
        return 0;
    } else {
        len = snprintf(buf, sizeof(buf), "%d SELFTEST(S) FAILED\n", test_failures);
        sys_log_output(buf, len);
        return 1;
    }
}

int selftests_failures(void) {
    return test_failures;
}

#ifdef SELFTEST_MAIN
int main(void) {
    return selftests_run();
}
#endif
