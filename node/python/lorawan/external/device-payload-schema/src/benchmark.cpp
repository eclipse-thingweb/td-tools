/*
 * benchmark.cpp - Codec performance benchmark
 *
 * Compares:
 * 1. Generated C codec (compiled from schema)
 * 2. Interpreter (runtime schema parsing)
 *
 * Build:
 *   g++ -O3 -o benchmark src/benchmark.cpp -I include
 *
 * Run:
 *   ./benchmark
 */

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstddef>
#include <chrono>
#include <vector>

extern "C" {
#include "rt.h"
#include "env_sensor_codec.h"
}

// ============================================
// Simple Interpreter (for comparison)
// ============================================

enum FieldType {
    FIELD_U8,
    FIELD_I8,
    FIELD_U16,
    FIELD_I16,
    FIELD_U32,
    FIELD_I32,
};

struct FieldDef {
    const char* name;
    FieldType type;
    int offset;     // Offset in output struct
    float mult;     // Multiplier (applied in float domain)
};

// Interpreted schema for env_sensor
// Offsets match env_sensor_t struct layout
static const FieldDef env_sensor_schema[] = {
    {"temperature", FIELD_I16, offsetof(env_sensor_t, temperature), 0.01f},
    {"humidity",    FIELD_U8,  offsetof(env_sensor_t, humidity), 0.5f},
    {"battery_mv",  FIELD_U16, offsetof(env_sensor_t, battery_mv), 1.0f},
    {"status",      FIELD_U8,  offsetof(env_sensor_t, status), 1.0f},
};

static int field_size(FieldType t) {
    switch (t) {
        case FIELD_U8:
        case FIELD_I8:
            return 1;
        case FIELD_U16:
        case FIELD_I16:
            return 2;
        case FIELD_U32:
        case FIELD_I32:
            return 4;
    }
    return 0;
}

// Interpreter decode function
static int decode_interpreted(
    const FieldDef* schema,
    size_t num_fields,
    const uint8_t* buf,
    size_t len,
    void* out
) {
    size_t pos = 0;
    uint8_t* out_bytes = (uint8_t*)out;
    
    for (size_t i = 0; i < num_fields; i++) {
        const FieldDef& f = schema[i];
        int size = field_size(f.type);
        
        if (pos + size > len) return -2;
        
        switch (f.type) {
            case FIELD_U8:
                out_bytes[f.offset] = buf[pos];
                break;
            case FIELD_I8:
                out_bytes[f.offset] = buf[pos];
                break;
            case FIELD_U16:
            case FIELD_I16:
                *(uint16_t*)(out_bytes + f.offset) = 
                    buf[pos] | (buf[pos + 1] << 8);
                break;
            case FIELD_U32:
            case FIELD_I32:
                *(uint32_t*)(out_bytes + f.offset) = 
                    buf[pos] | (buf[pos + 1] << 8) |
                    (buf[pos + 2] << 16) | (buf[pos + 3] << 24);
                break;
        }
        pos += size;
    }
    
    return (int)pos;
}

// ============================================
// Benchmark Runner
// ============================================

static const int ITERATIONS = 1000000;

// Prevent compiler from optimizing away the result
volatile int checksum = 0;

int main(int argc, char** argv) {
    (void)argc;
    (void)argv;
    
    // Test payload: temperature=2500 (25.0°C), humidity=100 (50%), battery=3000mV, status=0
    uint8_t payload[] = {0xC4, 0x09, 0x64, 0xB8, 0x0B, 0x00};
    size_t payload_len = sizeof(payload);
    
    env_sensor_t decoded;
    
    printf("Payload Schema Codec Benchmark\n");
    printf("==============================\n\n");
    printf("Payload: %zu bytes\n", payload_len);
    printf("Iterations: %d\n\n", ITERATIONS);
    
    // Warmup
    for (int i = 0; i < 1000; i++) {
        decode_env_sensor(payload, payload_len, &decoded);
    }
    
    // Benchmark: Generated codec
    auto start1 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < ITERATIONS; i++) {
        decode_env_sensor(payload, payload_len, &decoded);
        checksum += decoded.temperature;  // Prevent optimization
    }
    auto end1 = std::chrono::high_resolution_clock::now();
    auto duration1 = std::chrono::duration_cast<std::chrono::microseconds>(end1 - start1);
    
    printf("Generated C Codec:\n");
    printf("  Total time:   %ld µs\n", duration1.count());
    printf("  Per decode:   %.3f µs\n", (double)duration1.count() / ITERATIONS);
    printf("  Throughput:   %.2f M decodes/sec\n", 
           (double)ITERATIONS / duration1.count());
    printf("  Result: temp=%d (%.2f°C), humidity=%d (%.1f%%), battery=%d mV\n",
           decoded.temperature, decoded.temperature * 0.01,
           decoded.humidity, decoded.humidity * 0.5,
           decoded.battery_mv);
    printf("\n");
    
    // Benchmark: Interpreter
    auto start2 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < ITERATIONS; i++) {
        decode_interpreted(
            env_sensor_schema,
            sizeof(env_sensor_schema) / sizeof(env_sensor_schema[0]),
            payload,
            payload_len,
            &decoded
        );
        checksum += decoded.temperature;  // Prevent optimization
    }
    auto end2 = std::chrono::high_resolution_clock::now();
    auto duration2 = std::chrono::duration_cast<std::chrono::microseconds>(end2 - start2);
    
    printf("Interpreted Schema:\n");
    printf("  Total time:   %ld µs\n", duration2.count());
    printf("  Per decode:   %.3f µs\n", (double)duration2.count() / ITERATIONS);
    printf("  Throughput:   %.2f M decodes/sec\n", 
           (double)ITERATIONS / duration2.count());
    printf("  Result: temp=%d, humidity=%d, battery=%d mV\n",
           decoded.temperature, decoded.humidity, decoded.battery_mv);
    printf("\n");
    
    // Comparison
    printf("Comparison:\n");
    printf("  Generated is %.2fx faster than interpreted\n",
           (double)duration2.count() / duration1.count());
    printf("\n");
    
    // Encode benchmark
    decoded.temperature = 2500;
    decoded.humidity = 100;
    decoded.battery_mv = 3000;
    decoded.status = 0;
    
    uint8_t encoded[16];
    
    auto start3 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < ITERATIONS; i++) {
        encode_env_sensor(&decoded, encoded, sizeof(encoded));
        checksum += encoded[0];  // Prevent optimization
    }
    auto end3 = std::chrono::high_resolution_clock::now();
    auto duration3 = std::chrono::duration_cast<std::chrono::microseconds>(end3 - start3);
    
    printf("Generated C Encoder:\n");
    printf("  Total time:   %ld µs\n", duration3.count());
    printf("  Per encode:   %.3f µs\n", (double)duration3.count() / ITERATIONS);
    printf("  Throughput:   %.2f M encodes/sec\n", 
           (double)ITERATIONS / duration3.count());
    
    // Verify round-trip
    env_sensor_t roundtrip;
    decode_env_sensor(encoded, sizeof(encoded), &roundtrip);
    
    if (roundtrip.temperature == decoded.temperature &&
        roundtrip.humidity == decoded.humidity &&
        roundtrip.battery_mv == decoded.battery_mv) {
        printf("  Round-trip:   PASS\n");
    } else {
        printf("  Round-trip:   FAIL\n");
    }
    
    printf("\n");
    printf("Memory footprint:\n");
    printf("  Struct size:  %zu bytes\n", sizeof(env_sensor_t));
    printf("  Code size:    ~200 bytes (inline functions)\n");
    printf("  No heap allocation\n");
    
    return 0;
}
