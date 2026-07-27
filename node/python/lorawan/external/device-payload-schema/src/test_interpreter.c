/*
 * test_interpreter.c - Test and benchmark the schema interpreter
 *
 * Compile: gcc -O2 -I../include -o test_interpreter test_interpreter.c
 */

#include <stdio.h>
#include <time.h>
#include "schema_interpreter.h"

/* Build Radio Bridge schema programmatically */
void build_radio_bridge_schema(schema_t* schema) {
    schema_init(schema);
    strncpy(schema->name, "radio_bridge", SCHEMA_MAX_NAME_LEN - 1);
    schema->endian = ENDIAN_BIG;
    
    /* Protocol version - upper nibble */
    field_def_t f1 = field_bits("protocol_version", 4, 4, false);
    schema_add_field(schema, &f1);
    
    /* Packet counter - lower nibble, consume byte */
    field_def_t f2 = field_bits("packet_counter", 0, 4, true);
    schema_add_field(schema, &f2);
    
    /* Event type */
    field_def_t f3 = field_u8("event_type");
    field_set_var(&f3, "evt");
    field_add_lookup(&f3, 0, "reset");
    field_add_lookup(&f3, 1, "supervisory");
    field_add_lookup(&f3, 2, "tamper");
    field_add_lookup(&f3, 3, "door_window");
    field_add_lookup(&f3, 6, "button");
    field_add_lookup(&f3, 7, "contact");
    field_add_lookup(&f3, 8, "water");
    schema_add_field(schema, &f3);
    
    /* State field (used by multiple event types) */
    field_def_t f4 = field_u8("state");
    field_add_lookup(&f4, 0, "Closed");
    field_add_lookup(&f4, 1, "Open");
    schema_add_field(schema, &f4);
}

/* Build simple env sensor schema */
void build_env_sensor_schema(schema_t* schema) {
    schema_init(schema);
    strncpy(schema->name, "env_sensor", SCHEMA_MAX_NAME_LEN - 1);
    schema->endian = ENDIAN_BIG;
    
    /* Temperature: s16 * 0.01 */
    field_def_t f1 = field_s16("temperature", ENDIAN_BIG);
    field_set_mult(&f1, 0.01);
    schema_add_field(schema, &f1);
    
    /* Humidity: u8 * 0.5 */
    field_def_t f2 = field_u8("humidity");
    field_set_mult(&f2, 0.5);
    schema_add_field(schema, &f2);
    
    /* Battery: u16 */
    field_def_t f3 = field_u16("battery_mv", ENDIAN_BIG);
    schema_add_field(schema, &f3);
    
    /* Status: u8 */
    field_def_t f4 = field_u8("status");
    schema_add_field(schema, &f4);
}

void print_result(const decode_result_t* result) {
    printf("Decoded %d fields (%d bytes):\n", 
           result->field_count, result->bytes_consumed);
    
    for (int i = 0; i < result->field_count; i++) {
        const decoded_field_t* f = &result->fields[i];
        printf("  %s: ", f->name);
        
        switch (f->type) {
            case FIELD_TYPE_BITS:
            case FIELD_TYPE_U8:
            case FIELD_TYPE_U16:
            case FIELD_TYPE_U24:
            case FIELD_TYPE_U32:
            case FIELD_TYPE_S8:
            case FIELD_TYPE_S16:
            case FIELD_TYPE_S24:
            case FIELD_TYPE_S32:
                /* Check if it's a string (from lookup) */
                if (f->value.str[0] >= 'A' && f->value.str[0] <= 'z') {
                    printf("%s\n", f->value.str);
                } else {
                    printf("%.4f\n", f->value.f64);
                }
                break;
            case FIELD_TYPE_F32:
            case FIELD_TYPE_F64:
                printf("%.4f\n", f->value.f64);
                break;
            case FIELD_TYPE_BOOL:
                printf("%s\n", f->value.b ? "true" : "false");
                break;
            case FIELD_TYPE_ASCII:
                printf("\"%s\"\n", f->value.str);
                break;
            default:
                printf("(unknown type)\n");
        }
    }
}

void benchmark(const char* name, schema_t* schema, 
               const uint8_t* payload, size_t len, int iterations) {
    decode_result_t result;
    
    /* Warmup */
    for (int i = 0; i < 1000; i++) {
        schema_decode(schema, payload, len, &result);
    }
    
    clock_t start = clock();
    for (int i = 0; i < iterations; i++) {
        schema_decode(schema, payload, len, &result);
    }
    clock_t end = clock();
    
    double elapsed_ms = (double)(end - start) / CLOCKS_PER_SEC * 1000;
    double avg_us = elapsed_ms * 1000 / iterations;
    
    printf("\n%s Benchmark:\n", name);
    printf("  Iterations: %d\n", iterations);
    printf("  Total time: %.2f ms\n", elapsed_ms);
    printf("  Per decode: %.4f µs\n", avg_us);
    printf("  Throughput: %.0f decodes/sec\n", iterations / (elapsed_ms / 1000));
}

int main() {
    printf("=== C Schema Interpreter Test ===\n\n");
    
    /* Test 1: Environment Sensor */
    printf("--- Environment Sensor ---\n");
    schema_t env_schema;
    build_env_sensor_schema(&env_schema);
    
    /* temp=23.45°C, humidity=65%, battery=3300mV, status=0 */
    uint8_t env_payload[] = {0x09, 0x29, 0x82, 0x0C, 0xE4, 0x00};
    
    decode_result_t result;
    int rc = schema_decode(&env_schema, env_payload, sizeof(env_payload), &result);
    
    if (rc == SCHEMA_OK) {
        print_result(&result);
        
        /* Access specific fields */
        printf("\nDirect access:\n");
        printf("  Temperature: %.2f°C\n", result_get_double(&result, "temperature", 0));
        printf("  Humidity: %.1f%%\n", result_get_double(&result, "humidity", 0));
        printf("  Battery: %.0f mV\n", result_get_double(&result, "battery_mv", 0));
    } else {
        printf("Decode error: %d\n", rc);
    }
    
    /* Test 2: Radio Bridge Door Sensor */
    printf("\n--- Radio Bridge Door Sensor ---\n");
    schema_t rb_schema;
    build_radio_bridge_schema(&rb_schema);
    
    /* Door open event: protocol=1, counter=0, event=3 (door_window), state=1 (open) */
    uint8_t rb_payload[] = {0x10, 0x03, 0x01};
    
    rc = schema_decode(&rb_schema, rb_payload, sizeof(rb_payload), &result);
    if (rc == SCHEMA_OK) {
        print_result(&result);
    } else {
        printf("Decode error: %d\n", rc);
    }
    
    /* Test 3: Radio Bridge Water Sensor */
    printf("\n--- Radio Bridge Water Sensor ---\n");
    uint8_t rb_water[] = {0x30, 0x08, 0x00};  /* water detected */
    
    rc = schema_decode(&rb_schema, rb_water, sizeof(rb_water), &result);
    if (rc == SCHEMA_OK) {
        print_result(&result);
    }
    
    /* Benchmarks */
    printf("\n=== Benchmarks ===\n");
    benchmark("Env Sensor", &env_schema, env_payload, sizeof(env_payload), 10000000);
    benchmark("Radio Bridge", &rb_schema, rb_payload, sizeof(rb_payload), 10000000);
    
    return 0;
}
