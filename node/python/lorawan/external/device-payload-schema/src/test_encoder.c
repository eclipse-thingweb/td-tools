/*
 * test_encoder.c - Test encode functionality
 *
 * Compile: gcc -O2 -I../include -o test_encoder test_encoder.c
 */

#include <stdio.h>
#include <string.h>
#include "schema_interpreter.h"

void print_hex(const uint8_t* data, int len) {
    for (int i = 0; i < len; i++) {
        printf("%02X", data[i]);
    }
    printf("\n");
}

void test_roundtrip(void) {
    printf("=== Encode/Decode Roundtrip Test ===\n\n");
    
    /* Create schema */
    schema_t schema;
    schema_init(&schema);
    strncpy(schema.name, "sensor", SCHEMA_MAX_NAME_LEN - 1);
    schema.endian = ENDIAN_BIG;
    
    field_def_t f1 = field_s16("temperature", ENDIAN_BIG);
    field_set_mult(&f1, 0.01);
    schema_add_field(&schema, &f1);
    
    field_def_t f2 = field_u8("humidity");
    field_set_mult(&f2, 0.5);
    schema_add_field(&schema, &f2);
    
    field_def_t f3 = field_u16("battery", ENDIAN_BIG);
    schema_add_field(&schema, &f3);
    
    /* Encode */
    encode_inputs_t inputs;
    encode_inputs_init(&inputs);
    encode_inputs_add_double(&inputs, "temperature", 23.45);
    encode_inputs_add_double(&inputs, "humidity", 65.0);
    encode_inputs_add_double(&inputs, "battery", 3300.0);
    
    encode_result_t enc_result;
    int rc = schema_encode(&schema, &inputs, &enc_result);
    
    printf("Encode result: %d\n", rc);
    printf("Encoded payload (%d bytes): ", enc_result.len);
    print_hex(enc_result.data, enc_result.len);
    printf("Expected:                    0929820CE4\n");
    
    /* Decode back */
    decode_result_t dec_result;
    rc = schema_decode(&schema, enc_result.data, enc_result.len, &dec_result);
    
    printf("\nDecode result: %d\n", rc);
    printf("Decoded values:\n");
    for (int i = 0; i < dec_result.field_count; i++) {
        printf("  %s: %.2f\n", dec_result.fields[i].name, dec_result.fields[i].value.f64);
    }
    
    /* Verify roundtrip */
    double temp = result_get_double(&dec_result, "temperature", 0.0);
    double hum = result_get_double(&dec_result, "humidity", 0.0);
    double bat = result_get_double(&dec_result, "battery", 0.0);
    
    printf("\nRoundtrip verification:\n");
    printf("  temperature: 23.45 → %.2f %s\n", temp, (temp >= 23.44 && temp <= 23.46) ? "✓" : "✗");
    printf("  humidity:    65.0 → %.1f %s\n", hum, (hum == 65.0) ? "✓" : "✗");
    printf("  battery:     3300 → %.0f %s\n", bat, (bat == 3300.0) ? "✓" : "✗");
}

void test_device_uplink(void) {
    printf("\n=== Device Uplink Simulation ===\n\n");
    
    /* Device has schema loaded from binary */
    static const uint8_t binary_schema[] = {
        0x50, 0x53, 0x01, 0x00, 0x03,
        0x12, 0xFE, 0xE7, 0x0C,  /* temperature */
        0x01, 0x81, 0xE8, 0x0C,  /* humidity */
        0x02, 0x00, 0xF4, 0x0C,  /* voltage */
    };
    
    schema_t schema;
    schema_load_binary(&schema, binary_schema, sizeof(binary_schema));
    
    /* Simulate sensor readings */
    double temp_celsius = 22.5;
    double humidity_percent = 55.0;
    uint16_t battery_mv = 3250;
    
    /* Encode for uplink - use IPSO names from binary schema */
    encode_inputs_t inputs;
    encode_inputs_init(&inputs);
    encode_inputs_add_double(&inputs, "temperature", temp_celsius);
    encode_inputs_add_double(&inputs, "humidity", humidity_percent);
    encode_inputs_add_double(&inputs, "voltage", battery_mv);  /* IPSO 3316 = voltage */
    
    encode_result_t result;
    schema_encode(&schema, &inputs, &result);
    
    printf("Sensor readings:\n");
    printf("  Temperature: %.1f°C\n", temp_celsius);
    printf("  Humidity: %.0f%%\n", humidity_percent);
    printf("  Battery: %dmV\n", battery_mv);
    printf("\nUplink payload (%d bytes): ", result.len);
    print_hex(result.data, result.len);
}

void test_network_downlink(void) {
    printf("\n=== Network Downlink Simulation ===\n\n");
    
    /* Network has schema for device configuration */
    schema_t schema;
    schema_init(&schema);
    strncpy(schema.name, "config", SCHEMA_MAX_NAME_LEN - 1);
    schema.endian = ENDIAN_BIG;
    
    field_def_t f1 = field_u8("command");
    schema_add_field(&schema, &f1);
    
    field_def_t f2 = field_u16("interval", ENDIAN_BIG);
    schema_add_field(&schema, &f2);
    
    field_def_t f3 = field_u8("flags");
    schema_add_field(&schema, &f3);
    
    /* Network encodes configuration command */
    encode_inputs_t inputs;
    encode_inputs_init(&inputs);
    encode_inputs_add_double(&inputs, "command", 0x01);   /* Set interval */
    encode_inputs_add_double(&inputs, "interval", 3600);  /* 1 hour */
    encode_inputs_add_double(&inputs, "flags", 0x03);     /* Enable sensors */
    
    encode_result_t result;
    schema_encode(&schema, &inputs, &result);
    
    printf("Downlink command:\n");
    printf("  Command: SET_INTERVAL (0x01)\n");
    printf("  Interval: 3600 seconds\n");
    printf("  Flags: 0x03\n");
    printf("\nDownlink payload (%d bytes): ", result.len);
    print_hex(result.data, result.len);
    
    /* Device would decode this */
    printf("\nDevice decodes:\n");
    decode_result_t dec;
    schema_decode(&schema, result.data, result.len, &dec);
    for (int i = 0; i < dec.field_count; i++) {
        printf("  %s: %lld\n", dec.fields[i].name, (long long)dec.fields[i].value.i64);
    }
}

int main(void) {
    test_roundtrip();
    test_device_uplink();
    test_network_downlink();
    
    printf("\n=== Summary ===\n");
    printf("Device:  Encoder (uplink) + Decoder (downlink)\n");
    printf("Network: Decoder (uplink) + Encoder (downlink)\n");
    printf("Same schema, same code, bidirectional.\n");
    
    return 0;
}
