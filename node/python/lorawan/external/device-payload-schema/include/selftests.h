/*
 * selftests.h - Self-test framework
 *
 * Provides macros and utilities for writing embedded self-tests.
 * These run on the target platform to verify correct behavior.
 */

#ifndef _selftests_h_
#define _selftests_h_

#include "rt.h"

/*
 * Test assertion macro
 * Fails the test if condition is false
 */
#define TCHECK(cond) do {                                     \
    if (!(cond)) {                                            \
        selftest_fail(#cond, __FILE__, __LINE__);             \
    }                                                         \
} while (0)

/*
 * Explicit test failure
 */
#define TFAIL(msg) selftest_fail(msg, __FILE__, __LINE__)

/*
 * Test functions returning error count
 */
#define TSTART() int _terrs = 0
#define TERROR() _terrs++
#define TDONE()  return _terrs

/*
 * Self-test function declarations
 * Add new test modules here
 */
extern void selftest_codec(void);
extern void selftest_protocol(void);
/* Add more as needed:
extern void selftest_yourmodule(void);
*/

/*
 * Framework functions
 */

/* Called when a test fails */
void selftest_fail(const char* expr, const char* file, int line);

/* Run all self-tests, returns 0 on success */
int selftests_run(void);

/* Get number of failures from last run */
int selftests_failures(void);

#endif /* _selftests_h_ */
