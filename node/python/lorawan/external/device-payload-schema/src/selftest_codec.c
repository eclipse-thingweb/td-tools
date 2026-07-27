/*
 * selftest_codec.c - Self-tests for message codec
 *
 * These tests verify encoding/decoding functions against
 * known-good values from the specification.
 */

#include "selftests.h"
#include "rt.h"

/* Module identifier for logging */
#define MOD "TEST"

/*
 * Test: Byte order utilities
 */
static void test_byte_order(void) {
    u1_t buf[8];
    
    /* Test 16-bit little-endian */
    write_u2_le(buf, 0x1234);
    TCHECK(buf[0] == 0x34);
    TCHECK(buf[1] == 0x12);
    TCHECK(read_u2_le(buf) == 0x1234);
    
    /* Test 32-bit little-endian */
    write_u4_le(buf, 0x12345678);
    TCHECK(buf[0] == 0x78);
    TCHECK(buf[1] == 0x56);
    TCHECK(buf[2] == 0x34);
    TCHECK(buf[3] == 0x12);
    TCHECK(read_u4_le(buf) == 0x12345678);
    
    /* Test 64-bit little-endian */
    write_u8_le(buf, 0x123456789ABCDEF0ULL);
    TCHECK(buf[0] == 0xF0);
    TCHECK(buf[7] == 0x12);
    TCHECK(read_u8_le(buf) == 0x123456789ABCDEF0ULL);
}

/*
 * Test: Example message encoding
 * Replace with actual protocol message tests
 */
static void test_example_encode(void) {
    /* Example: Encode a simple header
     * Replace with actual protocol structure from spec
     */
    u1_t buf[16];
    int pos = 0;
    
    /* Hypothetical message header */
    u1_t mtype = 0x40;  /* Example: Unconfirmed Data Up */
    u4_t devaddr = 0x01020304;
    u2_t fcnt = 0x0001;
    
    buf[pos++] = mtype;
    write_u4_le(&buf[pos], devaddr);
    pos += 4;
    write_u2_le(&buf[pos], fcnt);
    pos += 2;
    
    /* Verify encoding */
    TCHECK(pos == 7);
    TCHECK(buf[0] == 0x40);
    TCHECK(buf[1] == 0x04);  /* DevAddr LSB */
    TCHECK(buf[4] == 0x01);  /* DevAddr MSB */
    TCHECK(buf[5] == 0x01);  /* FCnt LSB */
    TCHECK(buf[6] == 0x00);  /* FCnt MSB */
}

/*
 * Test: Example message decoding
 * Replace with actual protocol message tests
 */
static void test_example_decode(void) {
    /* Known-good packet from spec or test vector */
    u1_t packet[] = {0x40, 0x04, 0x03, 0x02, 0x01, 0x01, 0x00};
    
    int pos = 0;
    u1_t mtype = packet[pos++];
    u4_t devaddr = read_u4_le(&packet[pos]);
    pos += 4;
    u2_t fcnt = read_u2_le(&packet[pos]);
    pos += 2;
    
    TCHECK(mtype == 0x40);
    TCHECK(devaddr == 0x01020304);
    TCHECK(fcnt == 0x0001);
}

/*
 * Main test entry point
 */
void selftest_codec(void) {
    LOG(LOG_INFO, MOD, "Running codec self-tests");
    
    test_byte_order();
    test_example_encode();
    test_example_decode();
    
    LOG(LOG_INFO, MOD, "Codec self-tests complete");
}
