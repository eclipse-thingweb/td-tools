// Copyright (c) 2024-2026 Multitech Systems, Inc.
// Author: Jason Reiss
// SPDX-License-Identifier: MIT

package schema

import (
	"encoding/hex"
	"testing"
)

// DL-5TM schema for benchmarking
const dl5tmSchema = `
name: decentlab_dl_5tm
version: 3
endian: big

fields:
  - name: protocol_version
    type: u8

  - name: device_id
    type: u16

  - name: flags
    type: u16
    var: flags

  - flagged:
      field: flags
      groups:
        - bit: 0
          fields:
            - name: _raw_dielectric
              type: u16
              var: raw_dielectric
            - name: dielectric_permittivity
              type: number
              ref: $raw_dielectric
              div: 50
            - name: volumetric_water_content
              type: number
              ref: $dielectric_permittivity
              polynomial: [0.0000043, -0.00055, 0.0292, -0.053]
              unit: "m³/m³"
            - name: soil_temperature_raw
              type: u16
              var: soil_temp_raw
            - name: soil_temperature
              type: number
              ref: $soil_temp_raw
              transform:
                - add: -400
                - div: 10
              unit: "°C"
        - bit: 1
          fields:
            - name: _battery_raw
              type: u16
              var: battery_raw
            - name: battery_voltage
              type: number
              ref: $battery_raw
              div: 1000
              unit: "V"
`

// Test payload: 02 012f 0003 0258 0098 0bb8
// protocol=2, device=303, flags=3, dielectric=600, temp=152, battery=3000
var testPayloadHex = "02012f0003025800980bb8"

func BenchmarkSchemaInterpreter(b *testing.B) {
	payload, _ := hex.DecodeString(testPayloadHex)

	schema, err := ParseSchema(dl5tmSchema)
	if err != nil {
		b.Fatalf("Failed to parse schema: %v", err)
	}

	// Warmup and verify
	result, err := schema.Decode(payload)
	if err != nil {
		b.Fatalf("Failed to decode: %v", err)
	}
	if result["protocol_version"] != float64(2) {
		b.Fatalf("Unexpected protocol_version: %v", result["protocol_version"])
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = schema.Decode(payload)
	}
}

func BenchmarkSchemaInterpreterWithParse(b *testing.B) {
	payload, _ := hex.DecodeString(testPayloadHex)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		schema, _ := ParseSchema(dl5tmSchema)
		_, _ = schema.Decode(payload)
	}
}

func BenchmarkNativeDecoder(b *testing.B) {
	payload, _ := hex.DecodeString(testPayloadHex)

	// Native Go decoder (equivalent to hand-written)
	decode := func(data []byte) map[string]interface{} {
		if len(data) < 5 {
			return nil
		}

		result := make(map[string]interface{})
		result["protocol_version"] = int(data[0])
		result["device_id"] = int(data[1])<<8 | int(data[2])
		flags := int(data[3])<<8 | int(data[4])
		result["flags"] = flags

		pos := 5

		// Sensor group 0 (bit 0)
		if flags&1 != 0 && pos+4 <= len(data) {
			rawDielectric := float64(int(data[pos])<<8 | int(data[pos+1]))
			pos += 2
			dielectric := rawDielectric / 50
			result["dielectric_permittivity"] = dielectric

			// Polynomial: 0.0000043*x³ - 0.00055*x² + 0.0292*x - 0.053
			vwc := 0.0000043*dielectric*dielectric*dielectric -
				0.00055*dielectric*dielectric +
				0.0292*dielectric - 0.053
			result["volumetric_water_content"] = vwc

			rawTemp := float64(int(data[pos])<<8 | int(data[pos+1]))
			pos += 2
			result["soil_temperature_raw"] = rawTemp
			result["soil_temperature"] = (rawTemp - 400) / 10
		}

		// Sensor group 1 (bit 1)
		if flags&2 != 0 && pos+2 <= len(data) {
			rawBattery := float64(int(data[pos])<<8 | int(data[pos+1]))
			result["battery_voltage"] = rawBattery / 1000
		}

		return result
	}

	// Warmup and verify
	result := decode(payload)
	if result["protocol_version"] != 2 {
		b.Fatalf("Unexpected protocol_version: %v", result["protocol_version"])
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = decode(payload)
	}
}

// Binary schema for simple flat fields (no flagged construct)
// This tests the binary schema parsing path
var simpleBinarySchema = []byte{
	0x01,       // Version 1
	0x05,       // 5 fields
	0x00, 0x00, 0x00, 0x00, // u8, mult=1, semantic=0
	0x01, 0x00, 0x00, 0x00, // u16, mult=1, semantic=0
	0x01, 0x00, 0x00, 0x00, // u16 (flags), mult=1, semantic=0
	0x01, 0x00, 0x00, 0x00, // u16 (raw), mult=1, semantic=0
	0x01, 0x00, 0x00, 0x00, // u16 (temp), mult=1, semantic=0
}

// Simple payload for binary schema benchmark (no flagged)
var simplePayloadHex = "02012f00030258009800"

func BenchmarkBinarySchemaInterpreter(b *testing.B) {
	payload, _ := hex.DecodeString(simplePayloadHex)

	schema, err := ParseBinarySchema(simpleBinarySchema)
	if err != nil {
		b.Fatalf("Failed to parse binary schema: %v", err)
	}

	// Warmup
	_, err = schema.Decode(payload)
	if err != nil {
		b.Fatalf("Failed to decode: %v", err)
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = schema.Decode(payload)
	}
}

func BenchmarkBinarySchemaWithParse(b *testing.B) {
	payload, _ := hex.DecodeString(simplePayloadHex)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		schema, _ := ParseBinarySchema(simpleBinarySchema)
		_, _ = schema.Decode(payload)
	}
}

func BenchmarkYAMLParse(b *testing.B) {
	for i := 0; i < b.N; i++ {
		_, _ = ParseSchema(dl5tmSchema)
	}
}

func BenchmarkBinaryParse(b *testing.B) {
	for i := 0; i < b.N; i++ {
		_, _ = ParseBinarySchema(simpleBinarySchema)
	}
}

// Print results for comparison
func TestBenchmarkResults(t *testing.T) {
	payload, _ := hex.DecodeString(testPayloadHex)

	schema, err := ParseSchema(dl5tmSchema)
	if err != nil {
		t.Fatalf("Failed to parse schema: %v", err)
	}

	result, err := schema.Decode(payload)
	if err != nil {
		t.Fatalf("Failed to decode: %v", err)
	}

	t.Logf("Decoded result: %+v", result)
	t.Log("")
	t.Log("Run benchmarks with: go test -bench=. -benchmem")
	t.Log("")
	t.Log("Benchmark groups:")
	t.Log("")
	t.Log("  YAML Schema (complex with flagged):")
	t.Log("    BenchmarkNativeDecoder              - Hand-written Go baseline")
	t.Log("    BenchmarkSchemaInterpreter          - YAML schema pre-parsed")
	t.Log("    BenchmarkSchemaInterpreterWithParse - YAML parse each decode")
	t.Log("")
	t.Log("  Binary Schema (simple flat fields):")
	t.Log("    BenchmarkBinarySchemaInterpreter    - Binary schema pre-parsed")
	t.Log("    BenchmarkBinarySchemaWithParse      - Binary parse each decode")
	t.Log("")
	t.Log("  Parse-only:")
	t.Log("    BenchmarkYAMLParse                  - YAML parsing overhead")
	t.Log("    BenchmarkBinaryParse                - Binary parsing overhead")
}
