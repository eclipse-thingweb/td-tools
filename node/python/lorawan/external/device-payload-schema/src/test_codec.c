/*
 * test_codec.c - Test generated codec
 *
 * Build:
 *   gcc -o test_codec src/test_codec.c -I include
 *
 * Run:
 *   ./test_codec
 */

#include <stdio.h>
#include <string.h>
#include "rt.h"
#include "env_sensor_codec.h"

/* Test helper */
static void print_hex(const u1_t* buf, size_t len) {
    for (size_t i = 0; i < len; i++) {
        printf("%02X ", buf[i]);
    }
    printf("\n");
}

int main(int argc, char** argv) {
    (void)argc;
    (void)argv;
    int result;
    
    printf("Payload Schema Generated Codec Test\n");
    printf("====================================\n\n");
    
    /* Test 1: Decode */
    printf("Test 1: Decode\n");
    {
        /* Payload: temp=2500 (25.0°C), humidity=100 (50%), battery=3000mV, status=0 */
        u1_t payload[] = {0xC4, 0x09, 0x64, 0xB8, 0x0B, 0x00};
        env_sensor_t decoded;
        
        printf("  Input:  ");
        print_hex(payload, sizeof(payload));
        
        result = decode_env_sensor(payload, sizeof(payload), &decoded);
        
        if (result < 0) {
            printf("  FAIL: decode returned %d\n", result);
            return 1;
        }
        
        printf("  Bytes consumed: %d\n", result);
        printf("  temperature: %d (raw) = %.2f °C\n", 
               decoded.temperature, decoded.temperature * 0.01);
        printf("  humidity:    %d (raw) = %.1f %%RH\n",
               decoded.humidity, decoded.humidity * 0.5);
        printf("  battery_mv:  %d mV\n", decoded.battery_mv);
        printf("  status:      %d\n", decoded.status);
        
        /* Verify values */
        if (decoded.temperature == 2500 &&
            decoded.humidity == 100 &&
            decoded.battery_mv == 3000 &&
            decoded.status == 0) {
            printf("  PASS\n");
        } else {
            printf("  FAIL: values mismatch\n");
            return 1;
        }
    }
    printf("\n");
    
    /* Test 2: Encode */
    printf("Test 2: Encode\n");
    {
        env_sensor_t sensor = {
            .temperature = 2500,  /* 25.0°C */
            .humidity = 100,      /* 50% */
            .battery_mv = 3000,
            .status = 0
        };
        
        u1_t buffer[16];
        memset(buffer, 0xFF, sizeof(buffer));
        
        result = encode_env_sensor(&sensor, buffer, sizeof(buffer));
        
        if (result < 0) {
            printf("  FAIL: encode returned %d\n", result);
            return 1;
        }
        
        printf("  Bytes written: %d\n", result);
        printf("  Output: ");
        print_hex(buffer, result);
        
        /* Expected: C4 09 64 B8 0B 00 */
        u1_t expected[] = {0xC4, 0x09, 0x64, 0xB8, 0x0B, 0x00};
        
        if (result == sizeof(expected) && 
            memcmp(buffer, expected, result) == 0) {
            printf("  PASS\n");
        } else {
            printf("  Expected: ");
            print_hex(expected, sizeof(expected));
            printf("  FAIL: output mismatch\n");
            return 1;
        }
    }
    printf("\n");
    
    /* Test 3: Round-trip */
    printf("Test 3: Round-trip\n");
    {
        env_sensor_t original = {
            .temperature = -1234,  /* Negative temperature */
            .humidity = 200,
            .battery_mv = 4200,
            .status = 0xAB
        };
        
        u1_t buffer[16];
        env_sensor_t decoded;
        
        result = encode_env_sensor(&original, buffer, sizeof(buffer));
        if (result < 0) {
            printf("  FAIL: encode returned %d\n", result);
            return 1;
        }
        
        printf("  Encoded: ");
        print_hex(buffer, result);
        
        result = decode_env_sensor(buffer, result, &decoded);
        if (result < 0) {
            printf("  FAIL: decode returned %d\n", result);
            return 1;
        }
        
        if (decoded.temperature == original.temperature &&
            decoded.humidity == original.humidity &&
            decoded.battery_mv == original.battery_mv &&
            decoded.status == original.status) {
            printf("  PASS\n");
        } else {
            printf("  FAIL: round-trip mismatch\n");
            printf("    temp: %d vs %d\n", original.temperature, decoded.temperature);
            printf("    hum:  %d vs %d\n", original.humidity, decoded.humidity);
            printf("    bat:  %d vs %d\n", original.battery_mv, decoded.battery_mv);
            printf("    stat: %d vs %d\n", original.status, decoded.status);
            return 1;
        }
    }
    printf("\n");
    
    /* Test 4: Error handling */
    printf("Test 4: Error handling\n");
    {
        env_sensor_t decoded;
        u1_t short_buf[] = {0xC4, 0x09};  /* Only 2 bytes, need 6 */
        
        result = decode_env_sensor(short_buf, sizeof(short_buf), &decoded);
        
        if (result == -2) {
            printf("  Buffer too short: correctly returned -2\n");
            printf("  PASS\n");
        } else {
            printf("  FAIL: expected -2, got %d\n", result);
            return 1;
        }
        
        result = decode_env_sensor(NULL, 6, &decoded);
        if (result == -1) {
            printf("  NULL buffer: correctly returned -1\n");
        } else {
            printf("  FAIL: expected -1, got %d\n", result);
            return 1;
        }
    }
    printf("\n");
    
    printf("All tests passed!\n");
    printf("\n");
    printf("Code characteristics:\n");
    printf("  - Header-only (no .c file needed)\n");
    printf("  - No dynamic memory allocation\n");
    printf("  - No external dependencies (except rt.h)\n");
    printf("  - Struct size: %zu bytes\n", sizeof(env_sensor_t));
    printf("  - Suitable for embedded firmware\n");
    
    return 0;
}
