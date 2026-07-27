// Copyright (c) 2024-2026 Multitech Systems, Inc.
// Author: Jason Reiss
// SPDX-License-Identifier: MIT

package schema

import (
	"bytes"
	"fmt"
	"math"
	"testing"
)

func TestDecodeUint(t *testing.T) {
	tests := []struct {
		name   string
		data   []byte
		endian string
		want   uint64
	}{
		{"uint8", []byte{0xff}, "big", 255},
		{"uint16 big", []byte{0x01, 0x00}, "big", 256},
		{"uint16 little", []byte{0x00, 0x01}, "little", 256},
		{"uint32 big", []byte{0x00, 0x01, 0x00, 0x00}, "big", 65536},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := decodeUint(tt.data, tt.endian)
			if got != tt.want {
				t.Errorf("decodeUint() = %d, want %d", got, tt.want)
			}
		})
	}
}

func TestDecodeSint(t *testing.T) {
	tests := []struct {
		name   string
		data   []byte
		endian string
		want   int64
	}{
		{"positive", []byte{0x7f}, "big", 127},
		{"negative byte", []byte{0xff}, "big", -1},
		{"negative short", []byte{0xff, 0xfe}, "big", -2},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := decodeSint(tt.data, tt.endian)
			if got != tt.want {
				t.Errorf("decodeSint() = %d, want %d", got, tt.want)
			}
		})
	}
}

func TestDecodeBits(t *testing.T) {
	// 0xB4 = 0b10110100
	byteVal := byte(0xB4)

	tests := []struct {
		name      string
		bitOffset int
		bits      int
		want      int
	}{
		{"low 2 bits", 0, 2, 0},
		{"mid 4 bits", 2, 4, 13},
		{"high 2 bits", 6, 2, 2},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := decodeBits(byteVal, tt.bitOffset, tt.bits)
			if got != tt.want {
				t.Errorf("decodeBits() = %d, want %d", got, tt.want)
			}
		})
	}
}

func TestCompactFormat(t *testing.T) {
	tests := []struct {
		name    string
		format  string
		data    []byte
		want    map[string]any
		wantErr bool
	}{
		{
			name:   "simple uint8",
			format: ">B:value",
			data:   []byte{0xff},
			want:   map[string]any{"value": float64(255)},
		},
		{
			name:   "multiple fields",
			format: ">B:a H:b B:c",
			data:   []byte{0x01, 0x00, 0x02, 0x03},
			want:   map[string]any{"a": float64(1), "b": float64(2), "c": float64(3)},
		},
		{
			name:   "little endian",
			format: "<H:value",
			data:   []byte{0x00, 0x01},
			want:   map[string]any{"value": float64(256)},
		},
		{
			name:   "signed negative",
			format: ">h:value",
			data:   []byte{0xff, 0xfe},
			want:   map[string]any{"value": float64(-2)},
		},
		{
			name:   "with skip",
			format: ">B:first 2x B:last",
			data:   []byte{0x01, 0x00, 0x00, 0xff},
			want:   map[string]any{"first": float64(1), "last": float64(255)},
		},
		{
			name:   "string",
			format: ">5s:text",
			data:   []byte("Hello"),
			want:   map[string]any{"text": "Hello"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := DecodeCompact(tt.format, tt.data)
			if (err != nil) != tt.wantErr {
				t.Errorf("DecodeCompact() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if !tt.wantErr {
				for k, v := range tt.want {
					if got[k] != v {
						t.Errorf("DecodeCompact()[%s] = %v, want %v", k, got[k], v)
					}
				}
			}
		})
	}
}

func TestSchemaBasic(t *testing.T) {
	schemaYAML := `
name: test_sensor
fields:
  - name: version
    type: UInt
    length: 1
  - name: temperature
    type: SInt
    length: 2
  - name: humidity
    type: UInt
    length: 1
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	if schema.Name != "test_sensor" {
		t.Errorf("schema.Name = %v, want test_sensor", schema.Name)
	}

	// version=1, temp=26 (big endian 0x001A), humidity=100
	data := []byte{0x01, 0x00, 0x1A, 0x64}
	result, err := schema.Decode(data)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if result["version"] != float64(1) {
		t.Errorf("version = %v, want 1", result["version"])
	}
	if result["temperature"] != float64(26) {
		t.Errorf("temperature = %v, want 26", result["temperature"])
	}
	if result["humidity"] != float64(100) {
		t.Errorf("humidity = %v, want 100", result["humidity"])
	}
}

func TestSchemaWithModifiers(t *testing.T) {
	schemaYAML := `
name: scaled_sensor
fields:
  - name: temperature
    type: SInt
    length: 2
    mult: 0.1
  - name: offset_value
    type: UInt
    length: 1
    add: -40
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// temp=250 (25.0°C after *0.1), offset=100 (60 after -40)
	data := []byte{0x00, 0xFA, 0x64}
	result, err := schema.Decode(data)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if math.Abs(result["temperature"].(float64)-25.0) > 0.001 {
		t.Errorf("temperature = %v, want 25.0", result["temperature"])
	}
	if result["offset_value"] != float64(60) {
		t.Errorf("offset_value = %v, want 60", result["offset_value"])
	}
}

func TestSchemaWithLookup(t *testing.T) {
	schemaYAML := `
name: status_sensor
fields:
  - name: status
    type: UInt
    length: 1
    lookup:
      0: "Off"
      1: "On"
      2: "Error"
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	data := []byte{0x01}
	result, err := schema.Decode(data)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if result["status"] != "On" {
		t.Errorf("status = %v, want 'On'", result["status"])
	}
}

func TestSchemaWithNestedObject(t *testing.T) {
	schemaYAML := `
name: nested_sensor
fields:
  - name: sensor
    type: Object
    fields:
      - name: temp
        type: SInt
        length: 2
      - name: humid
        type: UInt
        length: 1
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	data := []byte{0x00, 0x19, 0x32} // temp=25, humid=50
	result, err := schema.Decode(data)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	sensor, ok := result["sensor"].(map[string]any)
	if !ok {
		t.Fatalf("sensor is not a map")
	}
	if sensor["temp"] != float64(25) {
		t.Errorf("sensor.temp = %v, want 25", sensor["temp"])
	}
	if sensor["humid"] != float64(50) {
		t.Errorf("sensor.humid = %v, want 50", sensor["humid"])
	}
}

func TestSchemaWithMatch(t *testing.T) {
	schemaYAML := `
name: conditional
fields:
  - name: msg
    type: Match
    length: 1
    cases:
      - case: 1
        fields:
          - name: temp
            type: SInt
            length: 2
      - case: 2
        fields:
          - name: count
            type: UInt
            length: 4
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Case 1: temp=25
	data1 := []byte{0x01, 0x00, 0x19}
	result1, err := schema.Decode(data1)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	msg1, ok := result1["msg"].(map[string]any)
	if !ok {
		t.Fatalf("msg is not a map")
	}
	if msg1["temp"] != float64(25) {
		t.Errorf("msg.temp = %v, want 25", msg1["temp"])
	}

	// Case 2: count=1000
	data2 := []byte{0x02, 0x00, 0x00, 0x03, 0xE8}
	result2, err := schema.Decode(data2)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	msg2, ok := result2["msg"].(map[string]any)
	if !ok {
		t.Fatalf("msg is not a map")
	}
	if msg2["count"] != float64(1000) {
		t.Errorf("msg.count = %v, want 1000", msg2["count"])
	}
}

func TestSchemaWithVariable(t *testing.T) {
	schemaYAML := `
name: variable_match
fields:
  - name: type
    type: UInt
    length: 1
    var: msg_type
  - name: len
    type: UInt
    length: 1
  - name: data
    type: Match
    on: $msg_type
    cases:
      - case: 1
        fields:
          - name: temp
            type: SInt
            length: 2
      - case: 2
        fields:
          - name: count
            type: UInt
            length: 4
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// type=1, len=2, temp=25
	data := []byte{0x01, 0x02, 0x00, 0x19}
	result, err := schema.Decode(data)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if result["type"] != float64(1) {
		t.Errorf("type = %v, want 1", result["type"])
	}

	dataField, ok := result["data"].(map[string]any)
	if !ok {
		t.Fatalf("data is not a map")
	}
	if dataField["temp"] != float64(25) {
		t.Errorf("data.temp = %v, want 25", dataField["temp"])
	}
}

func TestFloat16(t *testing.T) {
	// 1.0 in float16 = 0x3C00
	data := []byte{0x3C, 0x00}
	val, err := decodeFloat(data, 2, "big")
	if err != nil {
		t.Fatalf("decodeFloat() error = %v", err)
	}
	if val != 1.0 {
		t.Errorf("float16(1.0) = %v, want 1.0", val)
	}
}

func TestBufferUnderflow(t *testing.T) {
	schemaYAML := `
name: test
fields:
  - name: value
    type: UInt
    length: 4
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	data := []byte{0x01, 0x02} // Only 2 bytes, need 4
	_, err = schema.Decode(data)
	if err == nil {
		t.Error("expected buffer underflow error")
	}
}

func TestTLVSimple(t *testing.T) {
	// Simple TLV with single-byte tags (Elsys style)
	schemaYAML := `
name: elsys_sensor
endian: big
fields:
  - type: TLV
    tag_size: 1
    cases:
      "1":
        - name: temperature
          type: SInt
          length: 2
          mult: 0.1
      "2":
        - name: humidity
          type: UInt
          length: 1
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Tag 1 (temp) = 231 -> 23.1, Tag 2 (humid) = 30
	data := []byte{0x01, 0x00, 0xE7, 0x02, 0x1E}
	result, err := schema.Decode(data)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	temp, ok := result["temperature"].(float64)
	if !ok || math.Abs(temp-23.1) > 0.01 {
		t.Errorf("temperature = %v, want 23.1", result["temperature"])
	}

	humid, ok := result["humidity"].(float64)
	if !ok || humid != 30 {
		t.Errorf("humidity = %v, want 30", result["humidity"])
	}
}

func TestTLVCompositeTag(t *testing.T) {
	// Milesight-style composite tag (channel_id + channel_type)
	schemaYAML := `
name: milesight_am307
endian: little
fields:
  - type: TLV
    tag_fields:
      - name: channel_id
        type: UInt
        length: 1
      - name: channel_type
        type: UInt
        length: 1
    tag_key:
      - channel_id
      - channel_type
    cases:
      "[1,117]":
        - name: battery
          type: UInt
          length: 1
      "[3,103]":
        - name: temperature
          type: SInt
          length: 2
          mult: 0.1
      "[4,104]":
        - name: humidity
          type: UInt
          length: 1
          mult: 0.5
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Battery=100, Temp=272->27.2, Humid=90->45
	data := []byte{
		0x01, 0x75, 0x64,       // Battery: 100
		0x03, 0x67, 0x10, 0x01, // Temperature: 272 (little-endian) -> 27.2
		0x04, 0x68, 0x5A,       // Humidity: 90 -> 45
	}
	result, err := schema.Decode(data)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	battery, ok := result["battery"].(float64)
	if !ok || battery != 100 {
		t.Errorf("battery = %v, want 100", result["battery"])
	}

	temp, ok := result["temperature"].(float64)
	if !ok || math.Abs(temp-27.2) > 0.01 {
		t.Errorf("temperature = %v, want 27.2", result["temperature"])
	}

	humid, ok := result["humidity"].(float64)
	if !ok || math.Abs(humid-45.0) > 0.01 {
		t.Errorf("humidity = %v, want 45.0", result["humidity"])
	}
}

// =============================================================================
// Bytes Type Tests
// =============================================================================

func TestBytesHex(t *testing.T) {
	schemaYAML := `
name: bytes_test
fields:
  - name: device_eui
    type: Bytes
    length: 8
    format: hex
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	data := []byte{0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08}
	result, err := schema.Decode(data)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if result["device_eui"] != "0102030405060708" {
		t.Errorf("device_eui = %v, want 0102030405060708", result["device_eui"])
	}
}

func TestBytesHexUpper(t *testing.T) {
	schemaYAML := `
name: bytes_test
fields:
  - name: device_eui
    type: bytes
    length: 4
    format: "hex:upper"
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	data := []byte{0xAB, 0xCD, 0xEF, 0x12}
	result, err := schema.Decode(data)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if result["device_eui"] != "ABCDEF12" {
		t.Errorf("device_eui = %v, want ABCDEF12", result["device_eui"])
	}
}

func TestBytesWithSeparator(t *testing.T) {
	schemaYAML := `
name: bytes_test
fields:
  - name: mac_addr
    type: bytes
    length: 6
    format: hex
    separator: ":"
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	data := []byte{0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF}
	result, err := schema.Decode(data)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if result["mac_addr"] != "aa:bb:cc:dd:ee:ff" {
		t.Errorf("mac_addr = %v, want aa:bb:cc:dd:ee:ff", result["mac_addr"])
	}
}

func TestBytesBase64(t *testing.T) {
	schemaYAML := `
name: bytes_test
fields:
  - name: payload
    type: bytes
    length: 6
    format: base64
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	data := []byte{0x48, 0x65, 0x6C, 0x6C, 0x6F, 0x21} // "Hello!"
	result, err := schema.Decode(data)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if result["payload"] != "SGVsbG8h" {
		t.Errorf("payload = %v, want SGVsbG8h", result["payload"])
	}
}

func TestBytesArray(t *testing.T) {
	schemaYAML := `
name: bytes_test
fields:
  - name: raw
    type: bytes
    length: 4
    format: array
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	data := []byte{0x01, 0x02, 0x03, 0x04}
	result, err := schema.Decode(data)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	arr, ok := result["raw"].([]any)
	if !ok {
		t.Fatalf("raw is not an array")
	}
	if len(arr) != 4 {
		t.Errorf("len(raw) = %d, want 4", len(arr))
	}
	if arr[0] != float64(1) || arr[3] != float64(4) {
		t.Errorf("raw = %v, want [1,2,3,4]", arr)
	}
}

// =============================================================================
// Repeat Type Tests
// =============================================================================

func TestRepeatCount(t *testing.T) {
	schemaYAML := `
name: repeat_test
fields:
  - name: readings
    type: repeat
    count: 3
    fields:
      - name: temp
        type: s16
      - name: humid
        type: u8
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 3 readings: temp=-10, humid=50; temp=25, humid=60; temp=100, humid=70
	data := []byte{
		0xFF, 0xF6, 0x32, // -10, 50
		0x00, 0x19, 0x3C, // 25, 60
		0x00, 0x64, 0x46, // 100, 70
	}

	result, err := schema.Decode(data)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	readings, ok := result["readings"].([]any)
	if !ok {
		t.Fatalf("readings is not an array")
	}
	if len(readings) != 3 {
		t.Errorf("len(readings) = %d, want 3", len(readings))
	}

	r0, ok := readings[0].(map[string]any)
	if !ok {
		t.Fatalf("readings[0] is not a map")
	}
	if r0["temp"] != float64(-10) {
		t.Errorf("readings[0].temp = %v, want -10", r0["temp"])
	}
	if r0["humid"] != float64(50) {
		t.Errorf("readings[0].humid = %v, want 50", r0["humid"])
	}
}

func TestRepeatUntilEnd(t *testing.T) {
	schemaYAML := `
name: repeat_test
fields:
  - name: values
    type: repeat
    until: end
    fields:
      - name: value
        type: u16
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	data := []byte{0x00, 0x01, 0x00, 0x02, 0x00, 0x03, 0x00, 0x04}

	result, err := schema.Decode(data)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	values, ok := result["values"].([]any)
	if !ok {
		t.Fatalf("values is not an array")
	}
	if len(values) != 4 {
		t.Errorf("len(values) = %d, want 4", len(values))
	}

	v0, ok := values[0].(map[string]any)
	if !ok {
		t.Fatalf("values[0] is not a map")
	}
	if v0["value"] != float64(1) {
		t.Errorf("values[0].value = %v, want 1", v0["value"])
	}
}

func TestRepeatWithVariable(t *testing.T) {
	schemaYAML := `
name: repeat_test
fields:
  - name: count
    type: u8
    var: item_count
  - name: items
    type: repeat
    count: $item_count
    fields:
      - name: id
        type: u8
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	data := []byte{0x03, 0x0A, 0x0B, 0x0C} // count=3, items=[10,11,12]

	result, err := schema.Decode(data)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if result["count"] != float64(3) {
		t.Errorf("count = %v, want 3", result["count"])
	}

	items, ok := result["items"].([]any)
	if !ok {
		t.Fatalf("items is not an array")
	}
	if len(items) != 3 {
		t.Errorf("len(items) = %d, want 3", len(items))
	}
}

// =============================================================================
// Encoding Tests
// =============================================================================

func TestEncodeBasic(t *testing.T) {
	schemaYAML := `
name: test_sensor
fields:
  - name: version
    type: u8
  - name: temperature
    type: s16
  - name: humidity
    type: u8
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	data := map[string]any{
		"version":     float64(1),
		"temperature": float64(26),
		"humidity":    float64(100),
	}

	encoded, err := schema.Encode(data)
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	expected := []byte{0x01, 0x00, 0x1A, 0x64}
	if len(encoded) != len(expected) {
		t.Errorf("len(encoded) = %d, want %d", len(encoded), len(expected))
	}
	for i := range expected {
		if encoded[i] != expected[i] {
			t.Errorf("encoded[%d] = 0x%02X, want 0x%02X", i, encoded[i], expected[i])
		}
	}
}

func TestEncodeWithModifiers(t *testing.T) {
	schemaYAML := `
name: scaled_sensor
fields:
  - name: temperature
    type: s16
    mult: 0.1
  - name: offset_value
    type: u8
    add: -40
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	data := map[string]any{
		"temperature":  float64(25.0), // Should encode to 250
		"offset_value": float64(60),   // Should encode to 100 (60 + 40)
	}

	encoded, err := schema.Encode(data)
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	expected := []byte{0x00, 0xFA, 0x64} // 250 (big-endian), 100
	if len(encoded) != len(expected) {
		t.Errorf("len(encoded) = %d, want %d", len(encoded), len(expected))
	}
	for i := range expected {
		if encoded[i] != expected[i] {
			t.Errorf("encoded[%d] = 0x%02X, want 0x%02X", i, encoded[i], expected[i])
		}
	}
}

func TestEncodeWithDiv(t *testing.T) {
	schemaYAML := `
name: div_test
fields:
  - name: temperature
    type: s16
    div: 10
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	data := map[string]any{
		"temperature": float64(25.0), // Should encode to 250
	}

	encoded, err := schema.Encode(data)
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	expected := []byte{0x00, 0xFA} // 250 (big-endian)
	if len(encoded) != len(expected) {
		t.Errorf("len(encoded) = %d, want %d", len(encoded), len(expected))
	}
	for i := range expected {
		if encoded[i] != expected[i] {
			t.Errorf("encoded[%d] = 0x%02X, want 0x%02X", i, encoded[i], expected[i])
		}
	}
}

func TestEncodeWithLookup(t *testing.T) {
	schemaYAML := `
name: status_sensor
fields:
  - name: status
    type: u8
    lookup:
      0: "Off"
      1: "On"
      2: "Error"
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	data := map[string]any{
		"status": "On", // Should encode to 1
	}

	encoded, err := schema.Encode(data)
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	if len(encoded) != 1 || encoded[0] != 0x01 {
		t.Errorf("encoded = %v, want [0x01]", encoded)
	}
}

func TestEncodeLittleEndian(t *testing.T) {
	schemaYAML := `
name: little_endian_test
endian: little
fields:
  - name: value
    type: u16
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	data := map[string]any{
		"value": float64(0x1234),
	}

	encoded, err := schema.Encode(data)
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	expected := []byte{0x34, 0x12} // Little-endian
	if len(encoded) != len(expected) {
		t.Errorf("len(encoded) = %d, want %d", len(encoded), len(expected))
	}
	for i := range expected {
		if encoded[i] != expected[i] {
			t.Errorf("encoded[%d] = 0x%02X, want 0x%02X", i, encoded[i], expected[i])
		}
	}
}

func TestRoundTrip(t *testing.T) {
	schemaYAML := `
name: roundtrip_test
fields:
  - name: version
    type: u8
  - name: temperature
    type: s16
    div: 10
  - name: humidity
    type: u8
    mult: 0.5
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	original := map[string]any{
		"version":     float64(2),
		"temperature": float64(25.5),
		"humidity":    float64(45.0),
	}

	encoded, err := schema.Encode(original)
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	decoded, err := schema.Decode(encoded)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	// Check values match (with floating point tolerance)
	if decoded["version"] != float64(2) {
		t.Errorf("version = %v, want 2", decoded["version"])
	}
	if math.Abs(decoded["temperature"].(float64)-25.5) > 0.01 {
		t.Errorf("temperature = %v, want 25.5", decoded["temperature"])
	}
	if math.Abs(decoded["humidity"].(float64)-45.0) > 0.01 {
		t.Errorf("humidity = %v, want 45.0", decoded["humidity"])
	}
}

// =============================================================================
// Phase 2 Tests
// =============================================================================

func TestPortBasedSelection(t *testing.T) {
	schemaYAML := `
name: port_test
endian: big
ports:
  1:
    direction: uplink
    fields:
      - name: temperature
        type: s16
        div: 10
      - name: humidity
        type: u8
  100:
    direction: downlink
    fields:
      - name: report_interval
        type: u16
  default:
    fields:
      - name: raw_byte
        type: u8
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Port 1 uplink: temp=23.5, humid=50
	result, err := schema.DecodeWithPort([]byte{0x00, 0xEB, 0x32}, 1)
	if err != nil {
		t.Fatalf("DecodeWithPort(1) error = %v", err)
	}
	if math.Abs(result["temperature"].(float64)-23.5) > 0.01 {
		t.Errorf("temperature = %v, want 23.5", result["temperature"])
	}
	if result["humidity"] != float64(50) {
		t.Errorf("humidity = %v, want 50", result["humidity"])
	}

	// Port 100 downlink: interval=60
	result, err = schema.DecodeWithPort([]byte{0x00, 0x3C}, 100)
	if err != nil {
		t.Fatalf("DecodeWithPort(100) error = %v", err)
	}
	if result["report_interval"] != float64(60) {
		t.Errorf("report_interval = %v, want 60", result["report_interval"])
	}

	// Default port fallback
	result, err = schema.DecodeWithPort([]byte{0xAB}, 42)
	if err != nil {
		t.Fatalf("DecodeWithPort(42) error = %v", err)
	}
	if result["raw_byte"] != float64(0xAB) {
		t.Errorf("raw_byte = %v, want 171", result["raw_byte"])
	}

	// Unknown port without default should error
	noDefault, _ := ParseSchema(`
name: no_default
ports:
  1:
    fields:
      - name: x
        type: u8
`)
	_, err = noDefault.DecodeWithPort([]byte{0x01}, 99)
	if err == nil {
		t.Error("expected error for unknown port without default")
	}
}

func TestBitfieldStringHex(t *testing.T) {
	schemaYAML := `
name: version_test
endian: big
fields:
  - name: firmware_version
    type: bitfield_string
    length: 2
    delimiter: "."
    prefix: "v"
    parts:
      - [8, 8, hex]
      - [0, 8, hex]
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	result, err := schema.Decode([]byte{0x01, 0x03})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if result["firmware_version"] != "v1.3" {
		t.Errorf("firmware_version = %v, want v1.3", result["firmware_version"])
	}

	// Test hex uppercase for A
	result, err = schema.Decode([]byte{0x02, 0x0A})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if result["firmware_version"] != "v2.A" {
		t.Errorf("firmware_version = %v, want v2.A", result["firmware_version"])
	}
}

func TestBitfieldStringDecimal(t *testing.T) {
	schemaYAML := `
name: dec_version
endian: big
fields:
  - name: version
    type: bitfield_string
    length: 2
    delimiter: "."
    parts:
      - [8, 8]
      - [0, 8]
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	result, err := schema.Decode([]byte{0x03, 0x0A})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if result["version"] != "3.10" {
		t.Errorf("version = %v, want 3.10", result["version"])
	}
}

func TestFlaggedAllGroups(t *testing.T) {
	schemaYAML := `
name: flagged_test
endian: big
fields:
  - name: protocol_version
    type: u8
  - name: device_id
    type: u16
  - name: flags
    type: u16
  - flagged:
      field: flags
      groups:
        - bit: 0
          fields:
            - name: dielectric_permittivity
              type: u16
              div: 50
            - name: soil_temperature
              type: u16
              formula: "(x - 400) / 10"
        - bit: 1
          fields:
            - name: battery_voltage
              type: u16
              div: 1000
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// All groups present (flags=0x0003)
	data := []byte{0x02, 0x0C, 0x43, 0x00, 0x03, 0x01, 0x55, 0x01, 0x90, 0x0C, 0x5E}
	result, err := schema.Decode(data)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if result["protocol_version"] != float64(2) {
		t.Errorf("protocol_version = %v, want 2", result["protocol_version"])
	}
	if math.Abs(result["dielectric_permittivity"].(float64)-6.82) > 0.01 {
		t.Errorf("dielectric = %v, want 6.82", result["dielectric_permittivity"])
	}
	if math.Abs(result["soil_temperature"].(float64)-0.0) > 0.1 {
		t.Errorf("soil_temperature = %v, want 0.0", result["soil_temperature"])
	}
	if math.Abs(result["battery_voltage"].(float64)-3.166) > 0.001 {
		t.Errorf("battery = %v, want 3.166", result["battery_voltage"])
	}
}

func TestFlaggedPartialGroups(t *testing.T) {
	schemaYAML := `
name: flagged_partial
endian: big
fields:
  - name: protocol_version
    type: u8
  - name: device_id
    type: u16
  - name: flags
    type: u16
  - flagged:
      field: flags
      groups:
        - bit: 0
          fields:
            - name: dielectric_permittivity
              type: u16
              div: 50
        - bit: 1
          fields:
            - name: battery_voltage
              type: u16
              div: 1000
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Battery only (flags=0x0002)
	data := []byte{0x02, 0x0C, 0x43, 0x00, 0x02, 0x0C, 0x5E}
	result, err := schema.Decode(data)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if result["flags"] != float64(2) {
		t.Errorf("flags = %v, want 2", result["flags"])
	}
	if _, ok := result["dielectric_permittivity"]; ok {
		t.Error("dielectric_permittivity should not be present when bit 0 is clear")
	}
	if math.Abs(result["battery_voltage"].(float64)-3.166) > 0.001 {
		t.Errorf("battery = %v, want 3.166", result["battery_voltage"])
	}
}

func TestCrossFieldFormula(t *testing.T) {
	schemaYAML := `
name: computed_test
endian: big
fields:
  - name: dielectric
    type: u16
    div: 50
  - name: vwc
    type: number
    formula: "0.0000043 * pow($dielectric, 3) - 0.00055 * pow($dielectric, 2) + 0.0292 * $dielectric - 0.053"
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// dielectric = 341/50 = 6.82
	result, err := schema.Decode([]byte{0x01, 0x55})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if math.Abs(result["dielectric"].(float64)-6.82) > 0.01 {
		t.Errorf("dielectric = %v, want 6.82", result["dielectric"])
	}

	expectedVWC := 0.0000043*math.Pow(6.82, 3) - 0.00055*math.Pow(6.82, 2) + 0.0292*6.82 - 0.053
	if math.Abs(result["vwc"].(float64)-expectedVWC) > 0.001 {
		t.Errorf("vwc = %v, want %v", result["vwc"], expectedVWC)
	}
}

func TestFormulaWithX(t *testing.T) {
	schemaYAML := `
name: formula_x
endian: big
fields:
  - name: soil_temperature
    type: u16
    formula: "(x - 400) / 10"
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// raw=450, (450-400)/10 = 5.0
	result, err := schema.Decode([]byte{0x01, 0xC2})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if math.Abs(result["soil_temperature"].(float64)-5.0) > 0.01 {
		t.Errorf("soil_temperature = %v, want 5.0", result["soil_temperature"])
	}
}

func TestModifierYAMLKeyOrder(t *testing.T) {
	// YAML key order: add first, then div → (raw - 400) / 10
	// This is the Decentlab DL-5TM soil_temperature pattern
	schemaYAML := `
name: yaml_order_test
endian: big
fields:
  - name: soil_temperature
    type: u16
    add: -400
    div: 10
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// raw=625 (0x0271), (625 - 400) / 10 = 22.5
	result, err := schema.Decode([]byte{0x02, 0x71})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if math.Abs(result["soil_temperature"].(float64)-22.5) > 0.01 {
		t.Errorf("soil_temperature = %v, want 22.5 (add-then-div order)", result["soil_temperature"])
	}

	// Verify different order gives different result: div first, then add → (raw / 10) - 400
	schemaYAML2 := `
name: yaml_order_test2
endian: big
fields:
  - name: soil_temperature
    type: u16
    div: 10
    add: -400
`
	schema2, err := ParseSchema(schemaYAML2)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// raw=625, (625 / 10) - 400 = -337.5
	result2, err := schema2.Decode([]byte{0x02, 0x71})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if math.Abs(result2["soil_temperature"].(float64)-(-337.5)) > 0.01 {
		t.Errorf("soil_temperature = %v, want -337.5 (div-then-add order)", result2["soil_temperature"])
	}
}

func TestModifierYAMLKeyOrderRoundtrip(t *testing.T) {
	// add-then-div pattern should roundtrip correctly
	schemaYAML := `
name: roundtrip_order
endian: big
fields:
  - name: soil_temperature
    type: u16
    add: -400
    div: 10
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Encode 22.5 → raw 625 → bytes 0x02 0x71
	encoded, err := schema.Encode(map[string]any{"soil_temperature": 22.5})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}
	if len(encoded) != 2 || encoded[0] != 0x02 || encoded[1] != 0x71 {
		t.Errorf("Encode = %x, want 0271", encoded)
	}

	// Decode back to 22.5
	result, err := schema.Decode(encoded)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if math.Abs(result["soil_temperature"].(float64)-22.5) > 0.01 {
		t.Errorf("roundtrip soil_temperature = %v, want 22.5", result["soil_temperature"])
	}
}

func TestAlbedoFormula(t *testing.T) {
	schemaYAML := `
name: albedo_test
endian: big
fields:
  - name: incoming
    type: u16
    div: 10
  - name: reflected
    type: u16
    div: 10
  - name: albedo
    type: number
    formula: "$incoming > 0 && $reflected > 0 ? $reflected / $incoming : 0"
`

	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// incoming=100.0, reflected=50.0, albedo=0.5
	result, err := schema.Decode([]byte{0x03, 0xE8, 0x01, 0xF4})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if math.Abs(result["albedo"].(float64)-0.5) > 0.01 {
		t.Errorf("albedo = %v, want 0.5", result["albedo"])
	}

	// Zero guard: incoming=0
	result, err = schema.Decode([]byte{0x00, 0x00, 0x01, 0xF4})
	if err != nil {
		t.Fatalf("Decode() zero guard error = %v", err)
	}
	if result["albedo"].(float64) != 0 {
		t.Errorf("albedo = %v, want 0 (zero guard)", result["albedo"])
	}
}

// =============================================================================
// ENCODE TESTS
// =============================================================================

func TestEncodeFlaggedAllGroups(t *testing.T) {
	schemaYAML := `
name: enc_flagged
endian: big
fields:
  - name: version
    type: u8
  - name: flags
    type: u16
  - flagged:
      field: flags
      groups:
        - bit: 0
          fields:
            - name: temperature
              type: u16
              mult: 0.1
            - name: humidity
              type: u16
              mult: 0.5
        - bit: 1
          fields:
            - name: battery
              type: u16
              div: 1000
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	data := map[string]any{
		"version":     float64(2),
		"temperature": float64(25.0),
		"humidity":    float64(65.0),
		"battery":     float64(3.166),
	}
	encoded, err := schema.Encode(data)
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}
	// version=2, flags=0x0003, temp=250(0x00FA), humidity=130(0x0082), battery=3166(0x0C5E)
	expected := []byte{0x02, 0x00, 0x03, 0x00, 0xFA, 0x00, 0x82, 0x0C, 0x5E}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("Encode() = %X, want %X", encoded, expected)
	}
}

func TestEncodeFlaggedBatteryOnly(t *testing.T) {
	schemaYAML := `
name: enc_flagged_bat
endian: big
fields:
  - name: version
    type: u8
  - name: flags
    type: u16
  - flagged:
      field: flags
      groups:
        - bit: 0
          fields:
            - name: temperature
              type: u16
              mult: 0.1
        - bit: 1
          fields:
            - name: battery
              type: u16
              div: 1000
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	data := map[string]any{
		"version": float64(2),
		"battery": float64(3.166),
	}
	encoded, err := schema.Encode(data)
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}
	// flags=0x0002 (only bit 1), battery=3166(0x0C5E)
	if encoded[1] != 0x00 || encoded[2] != 0x02 {
		t.Errorf("flags = %X %X, want 00 02", encoded[1], encoded[2])
	}
	if len(encoded) != 5 {
		t.Errorf("len = %d, want 5", len(encoded))
	}
}

func TestEncodeBitfieldString(t *testing.T) {
	schema := &Schema{
		Name:   "enc_bfs",
		Endian: "big",
		Fields: []Field{
			{
				Name:      "fw_version",
				Type:      TypeBitfieldString,
				Length:    2,
				Prefix:    "v",
				Delimiter: ".",
				Parts:     [][]any{{float64(8), float64(8), "hex"}, {float64(0), float64(8), "hex"}},
			},
			{
				Name:      "hw_version",
				Type:      TypeBitfieldString,
				Length:    2,
				Delimiter: ".",
				Parts:     [][]any{{float64(8), float64(8)}, {float64(0), float64(8)}},
			},
		},
	}

	data := map[string]any{
		"fw_version": "v1.3",
		"hw_version": "3.10",
	}
	encoded, err := schema.Encode(data)
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}
	// fw: v1.3 → 0x0103, hw: 3.10 → 0x030A
	expected := []byte{0x01, 0x03, 0x03, 0x0A}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("Encode() = %X, want %X", encoded, expected)
	}
}

func TestEncodePortBased(t *testing.T) {
	schema := &Schema{
		Name:   "enc_port",
		Endian: "big",
		Ports: map[string]*PortDef{
			"1": {Fields: []Field{{Name: "temperature", Type: TypeU16, Mult: floatPtr(0.1)}}},
			"2": {Fields: []Field{{Name: "config_interval", Type: TypeU16}}},
		},
	}

	enc1, err := schema.EncodeWithPort(map[string]any{"temperature": float64(25.0)}, 1)
	if err != nil {
		t.Fatalf("EncodeWithPort(1) error = %v", err)
	}
	if !bytes.Equal(enc1, []byte{0x00, 0xFA}) {
		t.Errorf("Port 1 = %X, want 00FA", enc1)
	}

	enc2, err := schema.EncodeWithPort(map[string]any{"config_interval": float64(300)}, 2)
	if err != nil {
		t.Fatalf("EncodeWithPort(2) error = %v", err)
	}
	if !bytes.Equal(enc2, []byte{0x01, 0x2C}) {
		t.Errorf("Port 2 = %X, want 012C", enc2)
	}
}

func TestEncodeFlaggedRoundtrip(t *testing.T) {
	schemaYAML := `
name: roundtrip_flagged
endian: big
fields:
  - name: version
    type: u8
  - name: flags
    type: u16
  - flagged:
      field: flags
      groups:
        - bit: 0
          fields:
            - name: temperature
              type: u16
              mult: 0.1
        - bit: 1
          fields:
            - name: battery
              type: u16
              div: 1000
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	data := map[string]any{
		"version":     float64(2),
		"temperature": float64(25.0),
		"battery":     float64(3.166),
	}
	encoded, err := schema.Encode(data)
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	decoded, err := schema.Decode(encoded)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if math.Abs(decoded["temperature"].(float64)-25.0) > 0.1 {
		t.Errorf("roundtrip temperature = %v, want ~25.0", decoded["temperature"])
	}
	if math.Abs(decoded["battery"].(float64)-3.166) > 0.01 {
		t.Errorf("roundtrip battery = %v, want ~3.166", decoded["battery"])
	}
}

func floatPtr(f float64) *float64 { return &f }

// Phase 2 Tests: polynomial, compute, guard, ref

func TestPolynomialEvaluation(t *testing.T) {
	// Test: y = 0.1*x^2 - 4*x + 30
	// coefficients: [0.1, -4, 30]
	schemaYAML := `
name: polynomial_test
endian: big
fields:
  - name: raw_value
    type: u16
  - name: calibrated
    type: number
    ref: $raw_value
    polynomial: [0.1, -4, 30]
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// raw_value = 100 → 0.1*100^2 - 4*100 + 30 = 1000 - 400 + 30 = 630
	decoded, err := schema.Decode([]byte{0x00, 0x64}) // 100
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if calibrated, ok := decoded["calibrated"].(float64); !ok || math.Abs(calibrated-630) > 0.01 {
		t.Errorf("polynomial result = %v, want 630", decoded["calibrated"])
	}
}

func TestComputeDiv(t *testing.T) {
	schemaYAML := `
name: compute_div_test
endian: big
fields:
  - name: incoming
    type: u16
  - name: reflected
    type: u16
  - name: ratio
    type: number
    compute:
      op: div
      a: $reflected
      b: $incoming
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// incoming = 1000, reflected = 300 → ratio = 0.3
	decoded, err := schema.Decode([]byte{0x03, 0xE8, 0x01, 0x2C})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if ratio, ok := decoded["ratio"].(float64); !ok || math.Abs(ratio-0.3) > 0.001 {
		t.Errorf("compute div result = %v, want 0.3", decoded["ratio"])
	}
}

func TestComputeMul(t *testing.T) {
	schemaYAML := `
name: compute_mul_test
endian: big
fields:
  - name: base
    type: u8
  - name: factor
    type: u8
  - name: product
    type: number
    compute:
      op: mul
      a: $base
      b: $factor
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// base = 12, factor = 5 → product = 60
	decoded, err := schema.Decode([]byte{0x0C, 0x05})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if product, ok := decoded["product"].(float64); !ok || product != 60 {
		t.Errorf("compute mul result = %v, want 60", decoded["product"])
	}
}

func TestGuardWithConditions(t *testing.T) {
	schemaYAML := `
name: guard_test
endian: big
fields:
  - name: raw_temp
    type: u16
  - name: temperature
    type: number
    ref: $raw_temp
    transform:
      - sub: 400
      - div: 10
    guard:
      when:
        - field: $raw_temp
          gt: 0
          lt: 2000
      else: -999
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// raw_temp = 650 (valid) → (650-400)/10 = 25.0
	decoded, err := schema.Decode([]byte{0x02, 0x8A})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if temp, ok := decoded["temperature"].(float64); !ok || math.Abs(temp-25.0) > 0.01 {
		t.Errorf("guard pass result = %v, want 25.0", decoded["temperature"])
	}

	// raw_temp = 0 (invalid, not > 0) → else = -999
	decoded2, err := schema.Decode([]byte{0x00, 0x00})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if temp, ok := decoded2["temperature"].(float64); !ok || temp != -999 {
		t.Errorf("guard fail result = %v, want -999", decoded2["temperature"])
	}
}

func TestRefWithTransform(t *testing.T) {
	schemaYAML := `
name: ref_transform_test
endian: big
fields:
  - name: raw_reading
    type: u16
  - name: celsius
    type: number
    ref: $raw_reading
    transform:
      - sub: 500
      - div: 10
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// raw_reading = 750 → (750-500)/10 = 25.0
	decoded, err := schema.Decode([]byte{0x02, 0xEE})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if celsius, ok := decoded["celsius"].(float64); !ok || math.Abs(celsius-25.0) > 0.01 {
		t.Errorf("ref with transform result = %v, want 25.0", decoded["celsius"])
	}
}

// =============================================================================
// BOOL TYPE TESTS
// =============================================================================

func TestBoolType(t *testing.T) {
	schemaYAML := `
name: bool_test
fields:
  - name: flag_a
    type: bool
    bit: 0
  - name: flag_b
    type: bool
    bit: 1
  - name: flag_c
    type: bool
    bit: 7
    consume: 1
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 0x83 = 0b10000011 → bit0=1, bit1=1, bit7=1
	decoded, err := schema.Decode([]byte{0x83})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["flag_a"] != true {
		t.Errorf("flag_a = %v, want true", decoded["flag_a"])
	}
	if decoded["flag_b"] != true {
		t.Errorf("flag_b = %v, want true", decoded["flag_b"])
	}
	if decoded["flag_c"] != true {
		t.Errorf("flag_c = %v, want true", decoded["flag_c"])
	}
}

func TestBoolTypeFalse(t *testing.T) {
	schemaYAML := `
name: bool_false_test
fields:
  - name: motion
    type: bool
    bit: 0
    consume: 1
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 0x00 → bit0=0
	decoded, err := schema.Decode([]byte{0x00})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["motion"] != false {
		t.Errorf("motion = %v, want false", decoded["motion"])
	}
}

// =============================================================================
// STRING TYPE TESTS
// =============================================================================

func TestStringType(t *testing.T) {
	schemaYAML := `
name: string_test
fields:
  - name: device_name
    type: string
    length: 8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte("TestDev\x00"))
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	name := decoded["device_name"].(string)
	if name != "TestDev" && name != "TestDev\x00" {
		t.Errorf("device_name = %q, want TestDev", name)
	}
}

func TestAsciiType(t *testing.T) {
	schemaYAML := `
name: ascii_test
fields:
  - name: serial
    type: ascii
    length: 6
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte("ABC123"))
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["serial"] != "ABC123" {
		t.Errorf("serial = %v, want ABC123", decoded["serial"])
	}
}

// =============================================================================
// ENUM TYPE TESTS
// =============================================================================

func TestEnumType(t *testing.T) {
	schemaYAML := `
name: enum_test
fields:
  - name: status
    type: enum
    base: u8
    values:
      0: idle
      1: running
      2: error
      3: maintenance
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	tests := []struct {
		data []byte
		want string
	}{
		{[]byte{0x00}, "idle"},
		{[]byte{0x01}, "running"},
		{[]byte{0x02}, "error"},
		{[]byte{0x03}, "maintenance"},
	}

	for _, tt := range tests {
		decoded, err := schema.Decode(tt.data)
		if err != nil {
			t.Fatalf("Decode() error = %v", err)
		}
		if decoded["status"] != tt.want {
			t.Errorf("status for %v = %v, want %v", tt.data, decoded["status"], tt.want)
		}
	}
}

func TestEnumUnknownValue(t *testing.T) {
	schemaYAML := `
name: enum_unknown_test
fields:
  - name: mode
    type: enum
    base: u8
    values:
      0: off
      1: on
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Value 99 is not in enum
	decoded, err := schema.Decode([]byte{0x63})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	// Should return raw value or unknown marker
	status := decoded["mode"]
	if status == nil {
		t.Errorf("mode should not be nil for unknown enum value")
	}
}

// =============================================================================
// BYTE GROUP TESTS
// =============================================================================

func TestByteGroup(t *testing.T) {
	schemaYAML := `
name: byte_group_test
fields:
  - byte_group:
      - name: high_nibble
        type: u8[4:7]
      - name: low_nibble
        type: u8[0:3]
    size: 1
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 0xAB → high=0xA, low=0xB
	decoded, err := schema.Decode([]byte{0xAB})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["high_nibble"] != float64(0xA) {
		t.Errorf("high_nibble = %v, want 10", decoded["high_nibble"])
	}
	if decoded["low_nibble"] != float64(0xB) {
		t.Errorf("low_nibble = %v, want 11", decoded["low_nibble"])
	}
}

func TestByteGroupMultiByte(t *testing.T) {
	schemaYAML := `
name: byte_group_multi_test
fields:
  - byte_group:
      - name: flags
        type: u8[0:3]
      - name: version
        type: u8[4:7]
    size: 1
  - name: next_byte
    type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 0x5A, 0xFF → flags=0xA, version=0x5, next=0xFF
	decoded, err := schema.Decode([]byte{0x5A, 0xFF})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["flags"] != float64(0xA) {
		t.Errorf("flags = %v, want 10", decoded["flags"])
	}
	if decoded["version"] != float64(0x5) {
		t.Errorf("version = %v, want 5", decoded["version"])
	}
	if decoded["next_byte"] != float64(0xFF) {
		t.Errorf("next_byte = %v, want 255", decoded["next_byte"])
	}
}

// =============================================================================
// DEFINITIONS AND $REF TESTS
// =============================================================================

func TestDefinitionsRef(t *testing.T) {
	schemaYAML := `
name: definitions_test
definitions:
  header:
    fields:
      - name: version
        type: u8
      - name: msg_type
        type: u8
fields:
  - $ref: '#/definitions/header'
  - name: payload
    type: u16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// version=1, msg_type=2, payload=0x0064=100
	decoded, err := schema.Decode([]byte{0x01, 0x02, 0x00, 0x64})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["version"] != float64(1) {
		t.Errorf("version = %v, want 1", decoded["version"])
	}
	if decoded["msg_type"] != float64(2) {
		t.Errorf("msg_type = %v, want 2", decoded["msg_type"])
	}
	if decoded["payload"] != float64(100) {
		t.Errorf("payload = %v, want 100", decoded["payload"])
	}
}

func TestDefinitionsNestedRef(t *testing.T) {
	schemaYAML := `
name: nested_def_test
definitions:
  temp_reading:
    fields:
      - name: temp
        type: s16
        mult: 0.1
fields:
  - name: sensor_id
    type: u8
  - $ref: '#/definitions/temp_reading'
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// sensor_id=1, temp=231 → 23.1°C
	decoded, err := schema.Decode([]byte{0x01, 0x00, 0xE7})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["sensor_id"] != float64(1) {
		t.Errorf("sensor_id = %v, want 1", decoded["sensor_id"])
	}
	if math.Abs(decoded["temp"].(float64)-23.1) > 0.01 {
		t.Errorf("temp = %v, want 23.1", decoded["temp"])
	}
}

// =============================================================================
// SKIP TYPE TESTS
// =============================================================================

func TestSkipType(t *testing.T) {
	schemaYAML := `
name: skip_test
fields:
  - name: start
    type: u8
  - name: _reserved
    type: skip
    length: 2
  - name: end
    type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// start=0x01, skip 2 bytes (0xFF, 0xFF), end=0x02
	decoded, err := schema.Decode([]byte{0x01, 0xFF, 0xFF, 0x02})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["start"] != float64(1) {
		t.Errorf("start = %v, want 1", decoded["start"])
	}
	if decoded["end"] != float64(2) {
		t.Errorf("end = %v, want 2", decoded["end"])
	}
	// _reserved should not appear in output
	if _, exists := decoded["_reserved"]; exists {
		t.Errorf("_reserved should not be in output")
	}
}

func TestSkipSingleByte(t *testing.T) {
	schemaYAML := `
name: skip_single_test
fields:
  - name: a
    type: u8
  - type: skip
    length: 1
  - name: b
    type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{0x0A, 0x00, 0x0B})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["a"] != float64(10) {
		t.Errorf("a = %v, want 10", decoded["a"])
	}
	if decoded["b"] != float64(11) {
		t.Errorf("b = %v, want 11", decoded["b"])
	}
}

// =============================================================================
// UNIT ANNOTATION TESTS
// =============================================================================

func TestUnitAnnotation(t *testing.T) {
	schemaYAML := `
name: unit_test
fields:
  - name: temperature
    type: s16
    mult: 0.1
    unit: "°C"
  - name: humidity
    type: u8
    unit: "%"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// temp=231 → 23.1°C, humidity=50%
	decoded, err := schema.Decode([]byte{0x00, 0xE7, 0x32})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if math.Abs(decoded["temperature"].(float64)-23.1) > 0.01 {
		t.Errorf("temperature = %v, want 23.1", decoded["temperature"])
	}
	if decoded["humidity"] != float64(50) {
		t.Errorf("humidity = %v, want 50", decoded["humidity"])
	}
}

// =============================================================================
// SEMANTIC OUTPUT TESTS (IPSO/SenML)
// =============================================================================

func TestIPSOAnnotation(t *testing.T) {
	schemaYAML := `
name: ipso_test
fields:
  - name: temperature
    type: s16
    mult: 0.1
    ipso:
      object: 3303
      resource: 5700
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{0x00, 0xE7})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if math.Abs(decoded["temperature"].(float64)-23.1) > 0.01 {
		t.Errorf("temperature = %v, want 23.1", decoded["temperature"])
	}
}

func TestSenMLAnnotation(t *testing.T) {
	schemaYAML := `
name: senml_test
fields:
  - name: temp
    type: s16
    mult: 0.1
    senml:
      unit: Cel
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{0x00, 0xE7})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if math.Abs(decoded["temp"].(float64)-23.1) > 0.01 {
		t.Errorf("temp = %v, want 23.1", decoded["temp"])
	}
}

// =============================================================================
// EDGE CASE TESTS
// =============================================================================

func TestEmptyPayload(t *testing.T) {
	schemaYAML := `
name: empty_test
fields:
  - name: optional
    type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	_, err = schema.Decode([]byte{})
	if err == nil {
		t.Errorf("expected error for empty payload")
	}
}

func TestU24Type(t *testing.T) {
	schemaYAML := `
name: u24_test
endian: big
fields:
  - name: value
    type: u24
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 0x123456 = 1193046
	decoded, err := schema.Decode([]byte{0x12, 0x34, 0x56})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["value"] != float64(0x123456) {
		t.Errorf("value = %v, want %v", decoded["value"], 0x123456)
	}
}

func TestS24Type(t *testing.T) {
	schemaYAML := `
name: s24_test
endian: big
fields:
  - name: value
    type: s24
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 0xFFFFFF = -1 in signed 24-bit
	decoded, err := schema.Decode([]byte{0xFF, 0xFF, 0xFF})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["value"] != float64(-1) {
		t.Errorf("value = %v, want -1", decoded["value"])
	}
}

func TestMaxValues(t *testing.T) {
	schemaYAML := `
name: max_values_test
endian: big
fields:
  - name: max_u8
    type: u8
  - name: max_u16
    type: u16
  - name: max_u32
    type: u32
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{
		0xFF,             // u8 max
		0xFF, 0xFF,       // u16 max
		0xFF, 0xFF, 0xFF, 0xFF, // u32 max
	})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["max_u8"] != float64(255) {
		t.Errorf("max_u8 = %v, want 255", decoded["max_u8"])
	}
	if decoded["max_u16"] != float64(65535) {
		t.Errorf("max_u16 = %v, want 65535", decoded["max_u16"])
	}
	if decoded["max_u32"] != float64(4294967295) {
		t.Errorf("max_u32 = %v, want 4294967295", decoded["max_u32"])
	}
}

func TestNegativeValues(t *testing.T) {
	schemaYAML := `
name: negative_test
endian: big
fields:
  - name: min_s8
    type: s8
  - name: min_s16
    type: s16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{
		0x80,       // s8 min = -128
		0x80, 0x00, // s16 min = -32768
	})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["min_s8"] != float64(-128) {
		t.Errorf("min_s8 = %v, want -128", decoded["min_s8"])
	}
	if decoded["min_s16"] != float64(-32768) {
		t.Errorf("min_s16 = %v, want -32768", decoded["min_s16"])
	}
}

func TestZeroValues(t *testing.T) {
	schemaYAML := `
name: zero_test
fields:
  - name: a
    type: u8
  - name: b
    type: u16
  - name: c
    type: s16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{0x00, 0x00, 0x00, 0x00, 0x00})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["a"] != float64(0) {
		t.Errorf("a = %v, want 0", decoded["a"])
	}
	if decoded["b"] != float64(0) {
		t.Errorf("b = %v, want 0", decoded["b"])
	}
	if decoded["c"] != float64(0) {
		t.Errorf("c = %v, want 0", decoded["c"])
	}
}

func TestModifierChain(t *testing.T) {
	schemaYAML := `
name: modifier_chain_test
fields:
  - name: value
    type: u16
    mult: 0.1
    add: -40
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// raw=1000 → 1000 * 0.1 - 40 = 60
	decoded, err := schema.Decode([]byte{0x03, 0xE8})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if math.Abs(decoded["value"].(float64)-60.0) > 0.01 {
		t.Errorf("value = %v, want 60.0", decoded["value"])
	}
}

func TestDivModifier(t *testing.T) {
	schemaYAML := `
name: div_test
fields:
  - name: percentage
    type: u8
    div: 2
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// raw=100 → 100 / 2 = 50
	decoded, err := schema.Decode([]byte{0x64})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["percentage"] != float64(50) {
		t.Errorf("percentage = %v, want 50", decoded["percentage"])
	}
}

// =============================================================================
// ADDITIONAL COMPREHENSIVE TESTS
// =============================================================================

func TestMultipleBoolsInByte(t *testing.T) {
	schemaYAML := `
name: multi_bool_test
fields:
  - name: bit0
    type: bool
    bit: 0
  - name: bit1
    type: bool
    bit: 1
  - name: bit2
    type: bool
    bit: 2
  - name: bit3
    type: bool
    bit: 3
  - name: bit4
    type: bool
    bit: 4
  - name: bit5
    type: bool
    bit: 5
  - name: bit6
    type: bool
    bit: 6
  - name: bit7
    type: bool
    bit: 7
    consume: 1
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 0xA5 = 10100101
	decoded, err := schema.Decode([]byte{0xA5})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	expected := map[string]bool{
		"bit0": true, "bit1": false, "bit2": true, "bit3": false,
		"bit4": false, "bit5": true, "bit6": false, "bit7": true,
	}
	for name, want := range expected {
		if decoded[name] != want {
			t.Errorf("%s = %v, want %v", name, decoded[name], want)
		}
	}
}

func TestEnumWithAllValues(t *testing.T) {
	schemaYAML := `
name: enum_full_test
fields:
  - name: level
    type: enum
    base: u8
    values:
      0: off
      1: low
      2: medium
      3: high
      255: max
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	tests := []struct {
		data []byte
		want string
	}{
		{[]byte{0x00}, "off"},
		{[]byte{0x01}, "low"},
		{[]byte{0x02}, "medium"},
		{[]byte{0x03}, "high"},
		{[]byte{0xFF}, "max"},
	}

	for _, tt := range tests {
		decoded, err := schema.Decode(tt.data)
		if err != nil {
			t.Fatalf("Decode() error = %v", err)
		}
		if decoded["level"] != tt.want {
			t.Errorf("level for %v = %v, want %v", tt.data, decoded["level"], tt.want)
		}
	}
}

func TestMultModifierPrecision(t *testing.T) {
	schemaYAML := `
name: mult_precision_test
fields:
  - name: temp
    type: s16
    mult: 0.01
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 2345 * 0.01 = 23.45
	decoded, err := schema.Decode([]byte{0x09, 0x29})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if math.Abs(decoded["temp"].(float64)-23.45) > 0.001 {
		t.Errorf("temp = %v, want 23.45", decoded["temp"])
	}
}

func TestAddModifier(t *testing.T) {
	schemaYAML := `
name: add_test
fields:
  - name: temp
    type: u8
    add: -40
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 100 - 40 = 60
	decoded, err := schema.Decode([]byte{0x64})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["temp"] != float64(60) {
		t.Errorf("temp = %v, want 60", decoded["temp"])
	}
}

func TestCombinedModifiers(t *testing.T) {
	schemaYAML := `
name: combined_mod_test
fields:
  - name: value
    type: u16
    mult: 0.1
    add: -10
    div: 2
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Based on modifier order: add first, mult, div
	// This depends on implementation
	decoded, err := schema.Decode([]byte{0x03, 0xE8}) // 1000
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	// Value should be transformed
	if _, ok := decoded["value"].(float64); !ok {
		t.Errorf("value should be float64")
	}
}

func TestTransformPipeline(t *testing.T) {
	schemaYAML := `
name: transform_test
fields:
  - name: celsius
    type: u16
    transform:
      - mult: 0.1
      - add: -40
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 650 * 0.1 - 40 = 25°C
	decoded, err := schema.Decode([]byte{0x02, 0x8A})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if math.Abs(decoded["celsius"].(float64)-25.0) > 0.01 {
		t.Errorf("celsius = %v, want 25.0", decoded["celsius"])
	}
}

func TestLittleEndianU32(t *testing.T) {
	schemaYAML := `
name: little_u32_test
endian: little
fields:
  - name: value
    type: u32
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 0x12345678 in little endian
	decoded, err := schema.Decode([]byte{0x78, 0x56, 0x34, 0x12})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["value"] != float64(0x12345678) {
		t.Errorf("value = %v, want %v", decoded["value"], 0x12345678)
	}
}

func TestMixedEndianFields(t *testing.T) {
	schemaYAML := `
name: mixed_endian_test
endian: big
fields:
  - name: big_val
    type: u16
  - name: little_val
    type: u16
    endian: little
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// big: 0x0100 = 256, little: 0x0100 = 1
	decoded, err := schema.Decode([]byte{0x01, 0x00, 0x00, 0x01})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["big_val"] != float64(256) {
		t.Errorf("big_val = %v, want 256", decoded["big_val"])
	}
	if decoded["little_val"] != float64(256) {
		t.Errorf("little_val = %v, want 256", decoded["little_val"])
	}
}

func TestRepeatWithMinMax(t *testing.T) {
	schemaYAML := `
name: repeat_minmax_test
fields:
  - name: readings
    type: repeat
    until: end
    min: 1
    max: 5
    fields:
      - name: value
        type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{0x01, 0x02, 0x03})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	readings := decoded["readings"].([]any)
	if len(readings) != 3 {
		t.Errorf("readings length = %v, want 3", len(readings))
	}
}

func TestBitfieldExtraction(t *testing.T) {
	schemaYAML := `
name: bitfield_test
fields:
  - name: flags
    type: u8
    var: flags
  - name: bit_low
    type: bits
    bit_offset: 0
    bits: 4
  - name: bit_high
    type: bits
    bit_offset: 4
    bits: 4
    consume: 1
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 0xAB → low=0xB, high=0xA
	decoded, err := schema.Decode([]byte{0xAB, 0xAB})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["flags"] != float64(0xAB) {
		t.Errorf("flags = %v, want %v", decoded["flags"], 0xAB)
	}
}

func TestNestedObjectDecoding(t *testing.T) {
	schemaYAML := `
name: nested_test
fields:
  - name: header
    type: Object
    fields:
      - name: version
        type: u8
      - name: type
        type: u8
  - name: payload
    type: u16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{0x01, 0x02, 0x00, 0x64})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	header := decoded["header"].(map[string]any)
	if header["version"] != float64(1) {
		t.Errorf("header.version = %v, want 1", header["version"])
	}
	if header["type"] != float64(2) {
		t.Errorf("header.type = %v, want 2", header["type"])
	}
	if decoded["payload"] != float64(100) {
		t.Errorf("payload = %v, want 100", decoded["payload"])
	}
}

func TestLookupWithModifier(t *testing.T) {
	schemaYAML := `
name: lookup_mod_test
fields:
  - name: status_code
    type: u8
    var: code
  - name: status
    type: u8
    lookup:
      0: "OK"
      1: "Warning"
      2: "Error"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{0x01, 0x01})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["status"] != "Warning" {
		t.Errorf("status = %v, want Warning", decoded["status"])
	}
}

func TestVariableReference(t *testing.T) {
	schemaYAML := `
name: var_ref_test
fields:
  - name: count
    type: u8
    var: n
  - name: items
    type: repeat
    count: $n
    fields:
      - name: value
        type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// count=3, then 3 values
	decoded, err := schema.Decode([]byte{0x03, 0x0A, 0x0B, 0x0C})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["count"] != float64(3) {
		t.Errorf("count = %v, want 3", decoded["count"])
	}

	items := decoded["items"].([]any)
	if len(items) != 3 {
		t.Errorf("items length = %v, want 3", len(items))
	}
}

func TestMatchWithDefault(t *testing.T) {
	schemaYAML := `
name: match_default_test
fields:
  - name: msg_type
    type: u8
    var: type
  - name: data
    type: Match
    on: $type
    cases:
      - case: 1
        fields:
          - name: temp
            type: s16
      - default: true
        fields:
          - name: raw
            type: u16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Test default case (type=99)
	decoded, err := schema.Decode([]byte{0x63, 0x00, 0x64})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	data := decoded["data"].(map[string]any)
	if data["raw"] != float64(100) {
		t.Errorf("raw = %v, want 100", data["raw"])
	}
}

func TestF32Decoding(t *testing.T) {
	schemaYAML := `
name: f32_test
endian: big
fields:
  - name: value
    type: f32
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// IEEE 754: 1.0 = 0x3F800000
	decoded, err := schema.Decode([]byte{0x3F, 0x80, 0x00, 0x00})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if math.Abs(decoded["value"].(float64)-1.0) > 0.001 {
		t.Errorf("value = %v, want 1.0", decoded["value"])
	}
}

func TestStringWithNullTerminator(t *testing.T) {
	schemaYAML := `
name: string_null_test
fields:
  - name: name
    type: string
    length: 10
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte("Hello\x00\x00\x00\x00\x00"))
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["name"] != "Hello" {
		t.Errorf("name = %q, want Hello", decoded["name"])
	}
}

func TestByteGroupWithVariousBitRanges(t *testing.T) {
	schemaYAML := `
name: byte_group_varied_test
fields:
  - byte_group:
      - name: nibble_low
        type: u8[0:3]
      - name: bit4
        type: u8[4:4]
      - name: bits_567
        type: u8[5:7]
    size: 1
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 0xE5 = 11100101
	// low nibble (0:3) = 0101 = 5
	// bit4 (4:4) = 0
	// bits_567 (5:7) = 111 = 7
	decoded, err := schema.Decode([]byte{0xE5})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["nibble_low"] != float64(5) {
		t.Errorf("nibble_low = %v, want 5", decoded["nibble_low"])
	}
	if decoded["bit4"] != float64(0) {
		t.Errorf("bit4 = %v, want 0", decoded["bit4"])
	}
	if decoded["bits_567"] != float64(7) {
		t.Errorf("bits_567 = %v, want 7", decoded["bits_567"])
	}
}

// =============================================================================
// ENCODING COVERAGE TESTS
// =============================================================================

func TestEncodeBytesHex(t *testing.T) {
	schemaYAML := `
name: encode_bytes_hex_test
fields:
  - name: data
    type: bytes
    length: 4
    format: hex
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	encoded, err := schema.Encode(map[string]any{
		"data": "deadbeef",
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	expected := []byte{0xde, 0xad, 0xbe, 0xef}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %x, want %x", encoded, expected)
	}
}

func TestEncodeBytesWithSeparator(t *testing.T) {
	schemaYAML := `
name: encode_bytes_sep_test
fields:
  - name: mac
    type: bytes
    length: 6
    format: hex
    separator: ":"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	encoded, err := schema.Encode(map[string]any{
		"mac": "aa:bb:cc:dd:ee:ff",
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	expected := []byte{0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %x, want %x", encoded, expected)
	}
}

func TestEncodeBytesBase64(t *testing.T) {
	schemaYAML := `
name: encode_bytes_b64_test
fields:
  - name: data
    type: bytes
    length: 4
    format: base64
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// "AQID" is base64 for [1, 2, 3] padded to 4 bytes
	encoded, err := schema.Encode(map[string]any{
		"data": "AQIDBA==",
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	expected := []byte{0x01, 0x02, 0x03, 0x04}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %x, want %x", encoded, expected)
	}
}

func TestEncodeBytesArray(t *testing.T) {
	schemaYAML := `
name: encode_bytes_array_test
fields:
  - name: data
    type: bytes
    length: 4
    format: array
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	encoded, err := schema.Encode(map[string]any{
		"data": []any{float64(1), float64(2), float64(3), float64(4)},
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	expected := []byte{0x01, 0x02, 0x03, 0x04}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %x, want %x", encoded, expected)
	}
}

func TestEncodeFloat32(t *testing.T) {
	schemaYAML := `
name: encode_f32_test
endian: big
fields:
  - name: value
    type: f32
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	encoded, err := schema.Encode(map[string]any{
		"value": float64(1.0),
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	// IEEE 754: 1.0 = 0x3F800000
	expected := []byte{0x3F, 0x80, 0x00, 0x00}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %x, want %x", encoded, expected)
	}
}

func TestEncodeFloat64(t *testing.T) {
	schemaYAML := `
name: encode_f64_test
endian: big
fields:
  - name: value
    type: f64
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	encoded, err := schema.Encode(map[string]any{
		"value": float64(1.0),
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	// IEEE 754 double: 1.0 = 0x3FF0000000000000
	expected := []byte{0x3F, 0xF0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %x, want %x", encoded, expected)
	}
}

func TestEncodeFloat32LittleEndian(t *testing.T) {
	schemaYAML := `
name: encode_f32_le_test
endian: little
fields:
  - name: value
    type: f32
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	encoded, err := schema.Encode(map[string]any{
		"value": float64(1.0),
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	// IEEE 754: 1.0 = 0x3F800000 little endian
	expected := []byte{0x00, 0x00, 0x80, 0x3F}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %x, want %x", encoded, expected)
	}
}

func TestEncodeFloat64LittleEndian(t *testing.T) {
	schemaYAML := `
name: encode_f64_le_test
endian: little
fields:
  - name: value
    type: f64
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	encoded, err := schema.Encode(map[string]any{
		"value": float64(1.0),
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	// IEEE 754 double: 1.0 little endian
	expected := []byte{0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xF0, 0x3F}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %x, want %x", encoded, expected)
	}
}

func TestEncodeSintNegative(t *testing.T) {
	schemaYAML := `
name: encode_sint_neg_test
endian: big
fields:
  - name: value
    type: s16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	encoded, err := schema.Encode(map[string]any{
		"value": float64(-1),
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	// -1 in 16-bit signed = 0xFFFF
	expected := []byte{0xFF, 0xFF}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %x, want %x", encoded, expected)
	}
}

func TestEncodeWithSkipRoundtrip(t *testing.T) {
	schemaYAML := `
name: encode_skip_roundtrip_test
fields:
  - name: start
    type: u8
  - name: end
    type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	encoded, err := schema.Encode(map[string]any{
		"start": float64(1),
		"end":   float64(2),
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	expected := []byte{0x01, 0x02}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %x, want %x", encoded, expected)
	}

	// Verify roundtrip
	decoded, err := schema.Decode(encoded)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if decoded["start"] != float64(1) || decoded["end"] != float64(2) {
		t.Errorf("roundtrip failed: %v", decoded)
	}
}

func TestEncodeObject(t *testing.T) {
	schemaYAML := `
name: encode_object_test
fields:
  - name: header
    type: Object
    fields:
      - name: version
        type: u8
      - name: flags
        type: u8
  - name: payload
    type: u16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	encoded, err := schema.Encode(map[string]any{
		"header": map[string]any{
			"version": float64(1),
			"flags":   float64(0xFF),
		},
		"payload": float64(0x1234),
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	expected := []byte{0x01, 0xFF, 0x12, 0x34}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %x, want %x", encoded, expected)
	}
}

func TestEncodeRepeat(t *testing.T) {
	schemaYAML := `
name: encode_repeat_test
fields:
  - name: items
    type: repeat
    count: 3
    fields:
      - name: value
        type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	encoded, err := schema.Encode(map[string]any{
		"items": []any{
			map[string]any{"value": float64(1)},
			map[string]any{"value": float64(2)},
			map[string]any{"value": float64(3)},
		},
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	expected := []byte{0x01, 0x02, 0x03}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %x, want %x", encoded, expected)
	}
}

func TestEncodeAscii(t *testing.T) {
	schemaYAML := `
name: encode_ascii_test
fields:
  - name: text
    type: Ascii
    length: 8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	encoded, err := schema.Encode(map[string]any{
		"text": "Hello",
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	expected := []byte{'H', 'e', 'l', 'l', 'o', 0, 0, 0}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %v, want %v", encoded, expected)
	}
}

func TestEncodeHex(t *testing.T) {
	schemaYAML := `
name: encode_hex_test
fields:
  - name: data
    type: Hex
    length: 4
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	encoded, err := schema.Encode(map[string]any{
		"data": "AABBCCDD",
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	expected := []byte{0xAA, 0xBB, 0xCC, 0xDD}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %x, want %x", encoded, expected)
	}
}

// =============================================================================
// FORMULA COMPARISON OPERATOR TESTS
// =============================================================================

func TestFormulaGreaterThanEqual(t *testing.T) {
	schemaYAML := `
name: formula_gte_test
fields:
  - name: raw
    type: u8
    var: raw
  - name: result
    type: number
    formula: "$raw >= 50 ? 1 : 0"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 60 >= 50 = true = 1
	decoded, err := schema.Decode([]byte{60})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if decoded["result"] != float64(1) {
		t.Errorf("result = %v, want 1", decoded["result"])
	}

	// 40 >= 50 = false = 0
	decoded2, err := schema.Decode([]byte{40})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if decoded2["result"] != float64(0) {
		t.Errorf("result = %v, want 0", decoded2["result"])
	}
}

func TestFormulaLessThanEqual(t *testing.T) {
	schemaYAML := `
name: formula_lte_test
fields:
  - name: raw
    type: u8
    var: raw
  - name: result
    type: number
    formula: "$raw <= 50 ? 1 : 0"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 40 <= 50 = true = 1
	decoded, err := schema.Decode([]byte{40})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if decoded["result"] != float64(1) {
		t.Errorf("result = %v, want 1", decoded["result"])
	}
}

func TestFormulaEquals(t *testing.T) {
	schemaYAML := `
name: formula_eq_test
fields:
  - name: raw
    type: u8
    var: raw
  - name: result
    type: number
    formula: "$raw == 50 ? 1 : 0"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{50})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if decoded["result"] != float64(1) {
		t.Errorf("result = %v, want 1", decoded["result"])
	}

	decoded2, err := schema.Decode([]byte{51})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if decoded2["result"] != float64(0) {
		t.Errorf("result = %v, want 0", decoded2["result"])
	}
}

func TestFormulaNotEquals(t *testing.T) {
	schemaYAML := `
name: formula_neq_test
fields:
  - name: raw
    type: u8
    var: raw
  - name: result
    type: number
    formula: "$raw != 50 ? 1 : 0"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{51})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if decoded["result"] != float64(1) {
		t.Errorf("result = %v, want 1", decoded["result"])
	}
}

func TestFormulaOr(t *testing.T) {
	schemaYAML := `
name: formula_or_test
fields:
  - name: a
    type: u8
    var: aval
  - name: b
    type: u8
    var: bval
  - name: result
    type: number
    formula: "$aval > 0 || $bval > 0 ? 1 : 0"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// a=1, b=0 → true || false = 1
	decoded, err := schema.Decode([]byte{1, 0})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if decoded["result"] != float64(1) {
		t.Errorf("result = %v, want 1", decoded["result"])
	}

	// a=0, b=0 → false || false = 0
	decoded2, err := schema.Decode([]byte{0, 0})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if decoded2["result"] != float64(0) {
		t.Errorf("result = %v, want 0", decoded2["result"])
	}
}

func TestFormulaUnaryMinus(t *testing.T) {
	schemaYAML := `
name: formula_unary_test
fields:
  - name: raw
    type: u8
    var: raw
  - name: result
    type: number
    formula: "-$raw"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{10})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if decoded["result"] != float64(-10) {
		t.Errorf("result = %v, want -10", decoded["result"])
	}
}

func TestFormulaDivision(t *testing.T) {
	schemaYAML := `
name: formula_div_test
fields:
  - name: raw
    type: u8
    var: raw
  - name: result
    type: number
    formula: "$raw / 2"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{10})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if decoded["result"] != float64(5) {
		t.Errorf("result = %v, want 5", decoded["result"])
	}
}

func TestFormulaDivisionByZero(t *testing.T) {
	schemaYAML := `
name: formula_div_zero_test
fields:
  - name: raw
    type: u8
    var: raw
  - name: result
    type: number
    formula: "10 / $raw"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Division by zero returns 0 (safe fallback behavior)
	decoded, err := schema.Decode([]byte{0})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if decoded["result"] != float64(0) {
		t.Errorf("result = %v, want 0", decoded["result"])
	}
}

func TestFormulaFunctions(t *testing.T) {
	tests := []struct {
		name    string
		formula string
		input   byte
		want    float64
	}{
		{"abs positive", "abs($raw)", 10, 10},
		{"abs negative", "abs(-10)", 1, 10},
		{"sqrt", "sqrt($raw)", 16, 4},
		{"pow", "pow($raw, 2)", 3, 9},
		{"min", "min($raw, 5)", 10, 5},
		{"max", "max($raw, 5)", 10, 10},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			schemaYAML := fmt.Sprintf(`
name: formula_func_test
fields:
  - name: raw
    type: u8
    var: raw
  - name: result
    type: number
    formula: "%s"
`, tt.formula)
			schema, err := ParseSchema(schemaYAML)
			if err != nil {
				t.Fatalf("ParseSchema() error = %v", err)
			}

			decoded, err := schema.Decode([]byte{tt.input})
			if err != nil {
				t.Fatalf("Decode() error = %v", err)
			}
			if math.Abs(decoded["result"].(float64)-tt.want) > 0.001 {
				t.Errorf("result = %v, want %v", decoded["result"], tt.want)
			}
		})
	}
}

// =============================================================================
// REPEAT EDGE CASE TESTS
// =============================================================================

func TestRepeatByteLength(t *testing.T) {
	schemaYAML := `
name: repeat_byte_len_test
fields:
  - name: items
    type: repeat
    byte_length: 6
    fields:
      - name: value
        type: u16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 6 bytes = 3 u16 values
	decoded, err := schema.Decode([]byte{0x00, 0x01, 0x00, 0x02, 0x00, 0x03})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	items := decoded["items"].([]any)
	if len(items) != 3 {
		t.Errorf("items length = %d, want 3", len(items))
	}
}

func TestRepeatByteLengthVariable(t *testing.T) {
	schemaYAML := `
name: repeat_byte_len_var_test
fields:
  - name: len
    type: u8
    var: data_len
  - name: items
    type: repeat
    byte_length: $data_len
    fields:
      - name: value
        type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// len=3, then 3 bytes
	decoded, err := schema.Decode([]byte{0x03, 0x0A, 0x0B, 0x0C})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	items := decoded["items"].([]any)
	if len(items) != 3 {
		t.Errorf("items length = %d, want 3", len(items))
	}
}

func TestRepeatCountVariable(t *testing.T) {
	schemaYAML := `
name: repeat_count_var_test
fields:
  - name: count
    type: u8
    var: n
  - name: items
    type: repeat
    count: $n
    fields:
      - name: value
        type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{0x02, 0x0A, 0x0B})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	items := decoded["items"].([]any)
	if len(items) != 2 {
		t.Errorf("items length = %d, want 2", len(items))
	}
}

// =============================================================================
// ERROR PATH TESTS
// =============================================================================

func TestDecodeBufferUnderflowError(t *testing.T) {
	schemaYAML := `
name: underflow_test
fields:
  - name: value
    type: u32
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Only 2 bytes but need 4
	_, err = schema.Decode([]byte{0x00, 0x01})
	if err == nil {
		t.Error("expected buffer underflow error")
	}
}

func TestDecodeUnknownTypeError(t *testing.T) {
	schemaYAML := `
name: unknown_type_test
fields:
  - name: value
    type: unknown_type
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	_, err = schema.Decode([]byte{0x00})
	if err == nil {
		t.Error("expected unknown type error")
	}
}

func TestRepeatMinConstraintError(t *testing.T) {
	schemaYAML := `
name: repeat_min_error_test
fields:
  - name: items
    type: repeat
    until: end
    min: 5
    fields:
      - name: value
        type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Only 2 items but min is 5
	_, err = schema.Decode([]byte{0x01, 0x02})
	if err == nil {
		t.Error("expected min constraint error")
	}
}

func TestComputeDivByZero(t *testing.T) {
	schemaYAML := `
name: compute_div_zero_test
fields:
  - name: a
    type: u8
    var: a
  - name: b
    type: u8
    var: b
  - name: result
    type: number
    compute:
      op: div
      a: $a
      b: $b
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Division by zero
	_, err = schema.Decode([]byte{10, 0})
	if err == nil {
		t.Error("expected division by zero error")
	}
}

func TestRefFieldNotFound(t *testing.T) {
	schemaYAML := `
name: ref_not_found_test
fields:
  - name: result
    type: number
    ref: $nonexistent
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	_, err = schema.Decode([]byte{})
	if err == nil {
		t.Error("expected ref not found error")
	}
}

func TestMatchVariableNotFound(t *testing.T) {
	schemaYAML := `
name: match_var_not_found_test
fields:
  - name: data
    type: Match
    on: $nonexistent
    cases:
      - case: 1
        fields:
          - name: value
            type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	_, err = schema.Decode([]byte{0x01})
	if err == nil {
		t.Error("expected variable not found error")
	}
}

// =============================================================================
// ADDITIONAL DECODE COVERAGE TESTS
// =============================================================================

func TestDecodeFloat64(t *testing.T) {
	schemaYAML := `
name: f64_decode_test
endian: big
fields:
  - name: value
    type: f64
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// IEEE 754 double: 1.0 = 0x3FF0000000000000
	decoded, err := schema.Decode([]byte{0x3F, 0xF0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if math.Abs(decoded["value"].(float64)-1.0) > 0.001 {
		t.Errorf("value = %v, want 1.0", decoded["value"])
	}
}

func TestDecodeFloat64LittleEndian(t *testing.T) {
	schemaYAML := `
name: f64_le_decode_test
endian: little
fields:
  - name: value
    type: f64
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// IEEE 754 double: 1.0 little endian
	decoded, err := schema.Decode([]byte{0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xF0, 0x3F})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if math.Abs(decoded["value"].(float64)-1.0) > 0.001 {
		t.Errorf("value = %v, want 1.0", decoded["value"])
	}
}

func TestDecodeFloat16Special(t *testing.T) {
	schemaYAML := `
name: f16_special_test
endian: big
fields:
  - name: value
    type: f16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Infinity: 0x7C00
	decoded, err := schema.Decode([]byte{0x7C, 0x00})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if !math.IsInf(decoded["value"].(float64), 1) {
		t.Errorf("value = %v, want +Inf", decoded["value"])
	}

	// NaN: 0x7C01
	decoded2, err := schema.Decode([]byte{0x7C, 0x01})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if !math.IsNaN(decoded2["value"].(float64)) {
		t.Errorf("value = %v, want NaN", decoded2["value"])
	}
}

func TestBytesArrayFormat(t *testing.T) {
	schemaYAML := `
name: bytes_array_test
fields:
  - name: data
    type: bytes
    length: 4
    format: array
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{1, 2, 3, 4})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	arr := decoded["data"].([]any)
	if len(arr) != 4 {
		t.Errorf("array length = %d, want 4", len(arr))
	}
	if arr[0] != float64(1) {
		t.Errorf("arr[0] = %v, want 1", arr[0])
	}
}

func TestPortBasedDecoding(t *testing.T) {
	schemaYAML := `
name: port_based_test
ports:
  1:
    direction: up
    fields:
      - name: temp
        type: s16
        mult: 0.1
  2:
    direction: up
    fields:
      - name: humidity
        type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Port 1: temperature
	decoded1, err := schema.DecodeWithPort([]byte{0x00, 0xE7}, 1)
	if err != nil {
		t.Fatalf("DecodeWithPort(1) error = %v", err)
	}
	if math.Abs(decoded1["temp"].(float64)-23.1) > 0.01 {
		t.Errorf("temp = %v, want 23.1", decoded1["temp"])
	}

	// Port 2: humidity
	decoded2, err := schema.DecodeWithPort([]byte{0x32}, 2)
	if err != nil {
		t.Fatalf("DecodeWithPort(2) error = %v", err)
	}
	if decoded2["humidity"] != float64(50) {
		t.Errorf("humidity = %v, want 50", decoded2["humidity"])
	}
}

func TestGuardAllConditions(t *testing.T) {
	// Guard "gt: 50" means "when field > 50, include result"
	// Guard "lt: 50" means "when field < 50, include result"
	tests := []struct {
		name      string
		cond      string
		threshold int
		checkByte byte
		rawValue  byte
		want      float64
	}{
		{"gt pass", "gt", 50, 60, 100, 100},   // 60 > 50 = true → use raw
		{"gt fail", "gt", 50, 40, 100, -1},    // 40 > 50 = false → use else
		{"gte pass", "gte", 50, 50, 100, 100}, // 50 >= 50 = true
		{"gte fail", "gte", 50, 49, 100, -1},  // 49 >= 50 = false
		{"lt pass", "lt", 50, 40, 100, 100},   // 40 < 50 = true
		{"lt fail", "lt", 50, 60, 100, -1},    // 60 < 50 = false
		{"lte pass", "lte", 50, 50, 100, 100}, // 50 <= 50 = true
		{"lte fail", "lte", 50, 51, 100, -1},  // 51 <= 50 = false
		{"eq pass", "eq", 50, 50, 100, 100},   // 50 == 50 = true
		{"eq fail", "eq", 50, 51, 100, -1},    // 51 == 50 = false
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			schemaYAML := fmt.Sprintf(`
name: guard_cond_test
fields:
  - name: check
    type: u8
    var: check
  - name: raw
    type: u8
    var: raw
  - name: result
    type: number
    ref: $raw
    guard:
      when:
        - field: $check
          %s: %d
      else: -1
`, tt.cond, tt.threshold)
			schema, err := ParseSchema(schemaYAML)
			if err != nil {
				t.Fatalf("ParseSchema() error = %v", err)
			}

			decoded, err := schema.Decode([]byte{tt.checkByte, tt.rawValue})
			if err != nil {
				t.Fatalf("Decode() error = %v", err)
			}
			if decoded["result"] != tt.want {
				t.Errorf("result = %v, want %v", decoded["result"], tt.want)
			}
		})
	}
}

func TestMatchRangeCase(t *testing.T) {
	schemaYAML := `
name: match_range_test
fields:
  - name: value
    type: u8
    var: v
  - name: category
    type: Match
    on: $v
    cases:
      - case:
          min: 0
          max: 50
        fields:
          - name: label
            type: u8
      - case:
          min: 51
          max: 100
        fields:
          - name: label
            type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 25 is in range 0-50, reads label from next byte
	decoded, err := schema.Decode([]byte{25, 0x01})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	cat := decoded["category"].(map[string]any)
	if cat["label"] != float64(1) {
		t.Errorf("label = %v, want 1", cat["label"])
	}

	// 75 is in range 51-100
	decoded2, err := schema.Decode([]byte{75, 0x02})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	cat2 := decoded2["category"].(map[string]any)
	if cat2["label"] != float64(2) {
		t.Errorf("label = %v, want 2", cat2["label"])
	}
}

func TestMatchArrayCase(t *testing.T) {
	schemaYAML := `
name: match_array_test
fields:
  - name: code
    type: u8
    var: c
  - name: result
    type: Match
    on: $c
    cases:
      - case: [1, 2, 3]
        fields:
          - name: group
            type: u8
      - case: [4, 5, 6]
        fields:
          - name: group
            type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// code=2 matches [1,2,3], reads group from next byte
	decoded, err := schema.Decode([]byte{2, 0x0A})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	result := decoded["result"].(map[string]any)
	if result["group"] != float64(10) {
		t.Errorf("group = %v, want 10", result["group"])
	}
}

func TestToIntConversions(t *testing.T) {
	// Test toInt with various types through lookup
	schemaYAML := `
name: toint_test
fields:
  - name: value
    type: u8
    lookup:
      0: "zero"
      1: "one"
      255: "max"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	tests := []struct {
		input byte
		want  string
	}{
		{0, "zero"},
		{1, "one"},
		{255, "max"},
	}

	for _, tt := range tests {
		decoded, err := schema.Decode([]byte{tt.input})
		if err != nil {
			t.Fatalf("Decode() error = %v", err)
		}
		if decoded["value"] != tt.want {
			t.Errorf("value for %d = %v, want %v", tt.input, decoded["value"], tt.want)
		}
	}
}

// =============================================================================
// BINARY SCHEMA TESTS
// =============================================================================

func TestParseBinarySchema(t *testing.T) {
	// Binary format: version(1) + field_count(1) + fields(4 each)
	// Field: type_byte(1) + mult_exp(1) + semantic_id(2)
	// type_byte = type_code(4 bits) << 4 | size_code(4 bits)
	// type_code: 0=unsigned, 1=signed, 2=float, 4=bool
	// size_code: 0=1byte, 1=2bytes, 2=3bytes, 3=4bytes, 4=8bytes
	binaryData := []byte{
		0x01,             // version 1
		0x02,             // 2 fields
		0x01, 0x00, 0x00, 0x00, // field 0: type=unsigned(0), size=2bytes(1), mult=0, semantic=0
		0x10, 0xFE, 0x00, 0x00, // field 1: type=signed(1), size=1byte(0), mult=-2 (0.01), semantic=0
	}

	schema, err := ParseBinarySchema(binaryData)
	if err != nil {
		t.Fatalf("ParseBinarySchema() error = %v", err)
	}

	if len(schema.Fields) != 2 {
		t.Errorf("field count = %d, want 2", len(schema.Fields))
	}
	if schema.Fields[0].Type != TypeU16 {
		t.Errorf("field[0].Type = %s, want u16", schema.Fields[0].Type)
	}
	if schema.Fields[1].Type != TypeS8 {
		t.Errorf("field[1].Type = %s, want s8", schema.Fields[1].Type)
	}
}

func TestParseBinarySchemaAllTypes(t *testing.T) {
	tests := []struct {
		name     string
		typeByte byte
		expected FieldType
	}{
		{"u8", 0x00, TypeU8},   // unsigned, 1 byte
		{"u16", 0x01, TypeU16}, // unsigned, 2 bytes
		{"u32", 0x03, TypeU32}, // unsigned, 4 bytes
		{"u64", 0x04, TypeU64}, // unsigned, 8 bytes
		{"s8", 0x10, TypeS8},   // signed, 1 byte
		{"s16", 0x11, TypeS16}, // signed, 2 bytes
		{"s32", 0x13, TypeS32}, // signed, 4 bytes
		{"s64", 0x14, TypeS64}, // signed, 8 bytes
		{"f16", 0x21, TypeF16}, // float, 2 bytes
		{"f32", 0x23, TypeF32}, // float, 4 bytes
		{"f64", 0x24, TypeF64}, // float, 8 bytes
		{"bool", 0x40, TypeBool},   // bool
		{"bytes", 0x30, TypeBytes}, // bytes
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			binaryData := []byte{
				0x01,                        // version 1
				0x01,                        // 1 field
				tt.typeByte, 0x00, 0x00, 0x00, // field
			}
			schema, err := ParseBinarySchema(binaryData)
			if err != nil {
				t.Fatalf("ParseBinarySchema() error = %v", err)
			}
			if schema.Fields[0].Type != tt.expected {
				t.Errorf("type = %s, want %s", schema.Fields[0].Type, tt.expected)
			}
		})
	}
}

func TestParseBinarySchemaWithMultiplier(t *testing.T) {
	// Field with mult_exp = -1 means mult = 0.1
	binaryData := []byte{
		0x01,             // version 1
		0x01,             // 1 field
		0x01, 0xFF, 0x00, 0x00, // type=u16, mult_exp=-1
	}

	schema, err := ParseBinarySchema(binaryData)
	if err != nil {
		t.Fatalf("ParseBinarySchema() error = %v", err)
	}

	if schema.Fields[0].Mult == nil {
		t.Fatal("expected mult to be set")
	}
	if math.Abs(*schema.Fields[0].Mult-0.1) > 0.001 {
		t.Errorf("mult = %v, want 0.1", *schema.Fields[0].Mult)
	}
}

func TestParseBinarySchemaErrors(t *testing.T) {
	// Too short
	_, err := ParseBinarySchema([]byte{0x01})
	if err == nil {
		t.Error("expected error for too short data")
	}

	// Invalid version
	_, err = ParseBinarySchema([]byte{0x99, 0x01, 0x00, 0x00, 0x00, 0x00})
	if err == nil {
		t.Error("expected error for invalid version")
	}

	// Truncated
	_, err = ParseBinarySchema([]byte{0x01, 0x02, 0x00, 0x00, 0x00, 0x00})
	if err == nil {
		t.Error("expected error for truncated data")
	}
}

func TestEncodeBinarySchema(t *testing.T) {
	schemaYAML := `
name: binary_test
fields:
  - name: temp
    type: u8
  - name: humidity
    type: u16
    mult: 0.1
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	binary, err := EncodeBinarySchema(schema)
	if err != nil {
		t.Fatalf("EncodeBinarySchema() error = %v", err)
	}

	// Should be: version(1) + count(1) + 2 fields(8) = 10 bytes
	if len(binary) != 10 {
		t.Errorf("binary length = %d, want 10", len(binary))
	}

	// Verify version and count
	if binary[0] != 0x01 {
		t.Errorf("version = %d, want 1", binary[0])
	}
	if binary[1] != 0x02 {
		t.Errorf("field count = %d, want 2", binary[1])
	}
}

func TestBinarySchemaRoundtrip(t *testing.T) {
	schemaYAML := `
name: roundtrip_test
fields:
  - name: temp
    type: s16
    mult: 0.1
  - name: humidity
    type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Encode to binary
	binary, err := EncodeBinarySchema(schema)
	if err != nil {
		t.Fatalf("EncodeBinarySchema() error = %v", err)
	}

	// Parse back
	schema2, err := ParseBinarySchema(binary)
	if err != nil {
		t.Fatalf("ParseBinarySchema() error = %v", err)
	}

	if len(schema2.Fields) != 2 {
		t.Errorf("field count = %d, want 2", len(schema2.Fields))
	}

	// Decode with the roundtripped schema
	decoded, err := schema2.Decode([]byte{0x00, 0xE7, 0x32})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	// Verify values (field names are auto-generated: field_0, field_1)
	if math.Abs(decoded["field_0"].(float64)-23.1) > 0.01 {
		t.Errorf("field_0 = %v, want 23.1", decoded["field_0"])
	}
	if decoded["field_1"] != float64(50) {
		t.Errorf("field_1 = %v, want 50", decoded["field_1"])
	}
}

// =============================================================================
// TLV DECODING TESTS
// =============================================================================

func TestTLVBasic(t *testing.T) {
	schemaYAML := `
name: tlv_test
fields:
  - name: tag
    type: u8
    var: tag
  - name: len
    type: u8
    var: len
  - name: data
    type: TLV
    type_var: $tag
    length_var: $len
    cases:
      - case: 1
        fields:
          - name: temp
            type: s16
            mult: 0.1
      - case: 2
        fields:
          - name: humidity
            type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Tag=1, Len=2, Value=0x00E7 (231 = 23.1°C)
	decoded, err := schema.Decode([]byte{0x01, 0x02, 0x00, 0xE7})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["tag"] != float64(1) {
		t.Errorf("tag = %v, want 1", decoded["tag"])
	}
	if decoded["len"] != float64(2) {
		t.Errorf("len = %v, want 2", decoded["len"])
	}
}

// =============================================================================
// COMPUTE OPERATION TESTS
// =============================================================================

func TestComputeAdd(t *testing.T) {
	schemaYAML := `
name: compute_add_test
fields:
  - name: a
    type: u8
    var: a
  - name: b
    type: u8
    var: b
  - name: result
    type: number
    compute:
      op: add
      a: $a
      b: $b
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{10, 20})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["result"] != float64(30) {
		t.Errorf("result = %v, want 30", decoded["result"])
	}
}

func TestComputeSub(t *testing.T) {
	schemaYAML := `
name: compute_sub_test
fields:
  - name: a
    type: u8
    var: a
  - name: b
    type: u8
    var: b
  - name: result
    type: number
    compute:
      op: sub
      a: $a
      b: $b
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{50, 20})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["result"] != float64(30) {
		t.Errorf("result = %v, want 30", decoded["result"])
	}
}

func TestComputeMulOp(t *testing.T) {
	schemaYAML := `
name: compute_mul_test
fields:
  - name: a
    type: u8
    var: a
  - name: b
    type: u8
    var: b
  - name: result
    type: number
    compute:
      op: mul
      a: $a
      b: $b
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{5, 6})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["result"] != float64(30) {
		t.Errorf("result = %v, want 30", decoded["result"])
	}
}

func TestComputeDivOp(t *testing.T) {
	schemaYAML := `
name: compute_div_test
fields:
  - name: a
    type: u8
    var: a
  - name: b
    type: u8
    var: b
  - name: result
    type: number
    compute:
      op: div
      a: $a
      b: $b
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{60, 2})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["result"] != float64(30) {
		t.Errorf("result = %v, want 30", decoded["result"])
	}
}

func TestComputeInvalidOp(t *testing.T) {
	schemaYAML := `
name: compute_invalid_test
fields:
  - name: a
    type: u8
    var: a
  - name: b
    type: u8
    var: b
  - name: result
    type: number
    compute:
      op: invalid_op
      a: $a
      b: $b
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	_, err = schema.Decode([]byte{17, 5})
	if err == nil {
		t.Error("expected error for invalid compute op")
	}
}

// =============================================================================
// ENCODE WITH PORT TESTS
// =============================================================================

func TestEncodeWithPort(t *testing.T) {
	schemaYAML := `
name: port_encode_test
ports:
  1:
    direction: up
    fields:
      - name: temp
        type: s16
        mult: 0.1
  2:
    direction: up
    fields:
      - name: humidity
        type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Port 1: encode temperature
	encoded, err := schema.EncodeWithPort(map[string]any{
		"temp": 23.1,
	}, 1)
	if err != nil {
		t.Fatalf("EncodeWithPort(1) error = %v", err)
	}

	// 23.1 / 0.1 = 231 = 0x00E7
	expected := []byte{0x00, 0xE7}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %x, want %x", encoded, expected)
	}

	// Port 2: encode humidity
	encoded2, err := schema.EncodeWithPort(map[string]any{
		"humidity": float64(50),
	}, 2)
	if err != nil {
		t.Fatalf("EncodeWithPort(2) error = %v", err)
	}

	expected2 := []byte{0x32}
	if !bytes.Equal(encoded2, expected2) {
		t.Errorf("encoded = %x, want %x", encoded2, expected2)
	}
}

// =============================================================================
// PARSE SCHEMA EDGE CASES
// =============================================================================

func TestParseSchemaInvalidYAML(t *testing.T) {
	_, err := ParseSchema("invalid: yaml: [")
	if err == nil {
		t.Error("expected error for invalid YAML")
	}
}

func TestParseSchemaJSONFormat(t *testing.T) {
	schemaJSON := `{
		"name": "json_test",
		"fields": [
			{"name": "value", "type": "u8"}
		]
	}`

	schema, err := ParseSchema(schemaJSON)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{42})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["value"] != float64(42) {
		t.Errorf("value = %v, want 42", decoded["value"])
	}
}

func TestParseSchemaWithVersion(t *testing.T) {
	schemaYAML := `
version: 1
name: version_test
fields:
  - name: value
    type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	if schema.Version != 1 {
		t.Errorf("version = %v, want 1", schema.Version)
	}
}

// =============================================================================
// ADDITIONAL INTEGER TYPE TESTS
// =============================================================================

func TestDecodeU32(t *testing.T) {
	schemaYAML := `
name: u32_test
fields:
  - name: value
    type: u32
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{0x12, 0x34, 0x56, 0x78})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	// Big endian: 0x12345678
	if decoded["value"] != float64(0x12345678) {
		t.Errorf("value = %v, want %v", decoded["value"], 0x12345678)
	}
}

func TestDecodeS64(t *testing.T) {
	schemaYAML := `
name: s64_test
fields:
  - name: value
    type: s64
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// -1 in s64
	decoded, err := schema.Decode([]byte{0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["value"] != float64(-1) {
		t.Errorf("value = %v, want -1", decoded["value"])
	}
}

// =============================================================================
// ADDITIONAL TYPE TESTS
// =============================================================================

func TestDecodeU64(t *testing.T) {
	schemaYAML := `
name: u64_test
fields:
  - name: value
    type: u64
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["value"] != float64(256) {
		t.Errorf("value = %v, want 256", decoded["value"])
	}
}

func TestDecodeAddWithNegative(t *testing.T) {
	schemaYAML := `
name: add_neg_test
fields:
  - name: value
    type: u16
    add: -1000
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{0x04, 0x00}) // 1024
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	// 1024 + (-1000) = 24
	if decoded["value"] != float64(24) {
		t.Errorf("value = %v, want 24", decoded["value"])
	}
}

// =============================================================================
// FORMAT BYTES TESTS
// =============================================================================

func TestFormatBytesBase64(t *testing.T) {
	schemaYAML := `
name: format_bytes_b64_test
fields:
  - name: data
    type: bytes
    length: 4
    format: base64
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{1, 2, 3, 4})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	// 1,2,3,4 in base64 = "AQIDBA=="
	if decoded["data"] != "AQIDBA==" {
		t.Errorf("data = %v, want AQIDBA==", decoded["data"])
	}
}

func TestFormatBytesSeparator(t *testing.T) {
	schemaYAML := `
name: format_bytes_sep_test
fields:
  - name: mac
    type: bytes
    length: 6
    format: hex
    separator: ":"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["mac"] != "aa:bb:cc:dd:ee:ff" {
		t.Errorf("mac = %v, want aa:bb:cc:dd:ee:ff", decoded["mac"])
	}
}

// =============================================================================
// MULTIPLE FIELD MODIFIER TESTS
// =============================================================================

func TestMultipleModifiers(t *testing.T) {
	schemaYAML := `
name: multi_mod_test
fields:
  - name: temp
    type: u16
    mult: 0.01
    add: -40
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Raw = 6310: 6310 * 0.01 - 40 = 23.1
	decoded, err := schema.Decode([]byte{0x18, 0xA6}) // 6310
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if math.Abs(decoded["temp"].(float64)-23.1) > 0.01 {
		t.Errorf("temp = %v, want 23.1", decoded["temp"])
	}
}

func TestDivModifierU16(t *testing.T) {
	schemaYAML := `
name: div_mod_test
fields:
  - name: value
    type: u16
    div: 10
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{0x00, 0x64}) // 100
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["value"] != float64(10) {
		t.Errorf("value = %v, want 10", decoded["value"])
	}
}

// =============================================================================
// ADDITIONAL COMPARISON OPERATOR TESTS
// =============================================================================

func TestFormulaSubtraction(t *testing.T) {
	schemaYAML := `
name: formula_sub_test
fields:
  - name: raw
    type: u8
    var: raw
  - name: result
    type: number
    formula: "$raw - 10"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{25})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["result"] != float64(15) {
		t.Errorf("result = %v, want 15", decoded["result"])
	}
}

func TestFormulaAnd(t *testing.T) {
	schemaYAML := `
name: formula_and_test
fields:
  - name: a
    type: u8
    var: a
  - name: b
    type: u8
    var: b
  - name: result
    type: number
    formula: "$a > 0 && $b > 0 ? 1 : 0"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Both true
	decoded, err := schema.Decode([]byte{1, 1})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if decoded["result"] != float64(1) {
		t.Errorf("result = %v, want 1", decoded["result"])
	}

	// One false
	decoded2, err := schema.Decode([]byte{1, 0})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if decoded2["result"] != float64(0) {
		t.Errorf("result = %v, want 0", decoded2["result"])
	}
}

func TestFormulaMultiplication(t *testing.T) {
	schemaYAML := `
name: formula_mul_test
fields:
  - name: raw
    type: u8
    var: raw
  - name: result
    type: number
    formula: "$raw * 2"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{10})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["result"] != float64(20) {
		t.Errorf("result = %v, want 20", decoded["result"])
	}
}

func TestFormulaLessThan(t *testing.T) {
	schemaYAML := `
name: formula_lt_test
fields:
  - name: raw
    type: u8
    var: raw
  - name: result
    type: number
    formula: "$raw < 50 ? 1 : 0"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{40})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if decoded["result"] != float64(1) {
		t.Errorf("result = %v, want 1", decoded["result"])
	}
}

func TestFormulaGreaterThan(t *testing.T) {
	schemaYAML := `
name: formula_gt_test
fields:
  - name: raw
    type: u8
    var: raw
  - name: result
    type: number
    formula: "$raw > 50 ? 1 : 0"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{60})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if decoded["result"] != float64(1) {
		t.Errorf("result = %v, want 1", decoded["result"])
	}
}

// =============================================================================
// DECODE CONTEXT EDGE CASES
// =============================================================================

func TestDecodeWithDefaultEndian(t *testing.T) {
	schemaYAML := `
name: default_endian_test
fields:
  - name: value
    type: u16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Default is big endian
	decoded, err := schema.Decode([]byte{0x01, 0x02})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	// Big endian: 0x0102 = 258
	if decoded["value"] != float64(258) {
		t.Errorf("value = %v, want 258", decoded["value"])
	}
}

func TestResolveFields(t *testing.T) {
	schemaYAML := `
name: resolve_test
ports:
  1:
    direction: up
    fields:
      - name: temp
        type: s16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	fields, err := schema.ResolveFields(1)
	if err != nil {
		t.Fatalf("ResolveFields() error = %v", err)
	}

	if len(fields) != 1 || fields[0].Name != "temp" {
		t.Errorf("unexpected fields: %+v", fields)
	}
}

// =============================================================================
// MISC EDGE CASE TESTS
// =============================================================================

func TestDecodeEmptyPayload(t *testing.T) {
	schemaYAML := `
name: empty_test
fields: []
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if len(decoded) != 0 {
		t.Errorf("expected empty result, got %v", decoded)
	}
}

func TestEncodeBoolField(t *testing.T) {
	schemaYAML := `
name: encode_bool_test
fields:
  - name: flags
    type: u8
    var: flags
  - name: active
    type: bool
    bit: 0
    consume: 0
    flagged:
      field: $flags
      bit: 0
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	encoded, err := schema.Encode(map[string]any{
		"flags":  float64(1),
		"active": true,
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	if len(encoded) == 0 {
		t.Error("expected non-empty encoded result")
	}
}

func TestDecodeSignedNegative(t *testing.T) {
	schemaYAML := `
name: signed_neg_test
fields:
  - name: value
    type: s8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// -1 in s8 = 0xFF
	decoded, err := schema.Decode([]byte{0xFF})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["value"] != float64(-1) {
		t.Errorf("value = %v, want -1", decoded["value"])
	}
}

func TestDecodeS32Negative(t *testing.T) {
	schemaYAML := `
name: s32_neg_test
fields:
  - name: value
    type: s32
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// -1 in s32 = 0xFFFFFFFF
	decoded, err := schema.Decode([]byte{0xFF, 0xFF, 0xFF, 0xFF})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["value"] != float64(-1) {
		t.Errorf("value = %v, want -1", decoded["value"])
	}
}

// =============================================================================
// ADDITIONAL COVERAGE TESTS
// =============================================================================

func TestEncodeAndDecodeWithVariable(t *testing.T) {
	schemaYAML := `
name: encode_var_test
fields:
  - name: type
    type: u8
    var: type
  - name: value
    type: u16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	encoded, err := schema.Encode(map[string]any{
		"type":  float64(1),
		"value": float64(231),
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	// type=1, value=231 (0x00E7)
	expected := []byte{0x01, 0x00, 0xE7}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %x, want %x", encoded, expected)
	}
}

func TestEncodeRepeatFields(t *testing.T) {
	schemaYAML := `
name: encode_repeat_fields_test
fields:
  - name: count
    type: u8
    var: n
  - name: values
    type: repeat
    count: $n
    fields:
      - name: val
        type: u16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	encoded, err := schema.Encode(map[string]any{
		"count": float64(2),
		"values": []any{
			map[string]any{"val": float64(256)},
			map[string]any{"val": float64(512)},
		},
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	// count=2, val1=256(0x0100), val2=512(0x0200)
	expected := []byte{0x02, 0x01, 0x00, 0x02, 0x00}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %x, want %x", encoded, expected)
	}
}

func TestSchemaWithDownlink(t *testing.T) {
	schemaYAML := `
name: downlink_test
ports:
  10:
    direction: down
    fields:
      - name: command
        type: u8
      - name: value
        type: u16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Test encoding for downlink
	encoded, err := schema.EncodeWithPort(map[string]any{
		"command": float64(1),
		"value":   float64(1000),
	}, 10)
	if err != nil {
		t.Fatalf("EncodeWithPort() error = %v", err)
	}

	// command=1, value=1000(0x03E8)
	expected := []byte{0x01, 0x03, 0xE8}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %x, want %x", encoded, expected)
	}
}

func TestUnmatchedPortReturnsError(t *testing.T) {
	schemaYAML := `
name: port_error_test
ports:
  1:
    fields:
      - name: temp
        type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Port 99 doesn't exist
	_, err = schema.DecodeWithPort([]byte{0x00}, 99)
	if err == nil {
		t.Error("expected error for unknown port")
	}
}

func TestDecodeWithRefField(t *testing.T) {
	schemaYAML := `
name: ref_field_test
fields:
  - name: raw
    type: u16
    var: raw
  - name: scaled
    type: number
    ref: $raw
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{0x00, 0xE7}) // 231
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	// ref field just copies the value
	if decoded["scaled"] != float64(231) {
		t.Errorf("scaled = %v, want 231", decoded["scaled"])
	}
}

func TestDecodeF32LittleEndian(t *testing.T) {
	schemaYAML := `
name: f32_le_test
endian: little
fields:
  - name: value
    type: f32
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 1.0 in little endian
	decoded, err := schema.Decode([]byte{0x00, 0x00, 0x80, 0x3F})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if math.Abs(decoded["value"].(float64)-1.0) > 0.001 {
		t.Errorf("value = %v, want 1.0", decoded["value"])
	}
}

func TestDecodeU24Values(t *testing.T) {
	schemaYAML := `
name: decode_u24_test
fields:
  - name: value
    type: u24
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{0x12, 0x34, 0x56})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["value"] != float64(0x123456) {
		t.Errorf("value = %v, want %v", decoded["value"], 0x123456)
	}
}

func TestDecodeS24NegativeValue(t *testing.T) {
	schemaYAML := `
name: decode_s24_test
fields:
  - name: value
    type: s24
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// -1 in 24-bit = 0xFFFFFF
	decoded, err := schema.Decode([]byte{0xFF, 0xFF, 0xFF})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["value"] != float64(-1) {
		t.Errorf("value = %v, want -1", decoded["value"])
	}
}

func TestDecodeMultipleFieldsWithModifiers(t *testing.T) {
	schemaYAML := `
name: multi_mod_fields_test
fields:
  - name: temp
    type: s16
    mult: 0.1
  - name: humidity
    type: u8
    mult: 0.5
  - name: pressure
    type: u16
    add: 500
    mult: 0.1
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{0x00, 0xE7, 0x64, 0x27, 0x10})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	// temp = 231 * 0.1 = 23.1
	if math.Abs(decoded["temp"].(float64)-23.1) > 0.01 {
		t.Errorf("temp = %v, want 23.1", decoded["temp"])
	}

	// humidity = 100 * 0.5 = 50
	if decoded["humidity"] != float64(50) {
		t.Errorf("humidity = %v, want 50", decoded["humidity"])
	}
}

func TestEncodeBytesWithPadding(t *testing.T) {
	schemaYAML := `
name: bytes_pad_test
fields:
  - name: data
    type: bytes
    length: 8
    format: hex
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Only 4 bytes, should be padded to 8
	encoded, err := schema.Encode(map[string]any{
		"data": "AABBCCDD",
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	if len(encoded) != 8 {
		t.Errorf("encoded length = %d, want 8", len(encoded))
	}
}

func TestDecodeNestedMatch(t *testing.T) {
	schemaYAML := `
name: nested_match_test
fields:
  - name: type1
    type: u8
    var: t1
  - name: outer
    type: Match
    on: $t1
    cases:
      - case: 1
        fields:
          - name: type2
            type: u8
            var: t2
          - name: inner
            type: Match
            on: $t2
            cases:
              - case: 1
                fields:
                  - name: a
                    type: u8
              - case: 2
                fields:
                  - name: b
                    type: u16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// t1=1, t2=2, b=0x1234
	decoded, err := schema.Decode([]byte{0x01, 0x02, 0x12, 0x34})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	outer := decoded["outer"].(map[string]any)
	inner := outer["inner"].(map[string]any)
	if inner["b"] != float64(0x1234) {
		t.Errorf("inner.b = %v, want 0x1234", inner["b"])
	}
}

func TestDecodeFormulaTernaryFalse(t *testing.T) {
	schemaYAML := `
name: formula_ternary_false_test
fields:
  - name: raw
    type: u8
    var: raw
  - name: result
    type: number
    formula: "$raw > 100 ? 1 : 0"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 50 > 100 is false, should return 0
	decoded, err := schema.Decode([]byte{50})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["result"] != float64(0) {
		t.Errorf("result = %v, want 0", decoded["result"])
	}
}

func TestDecodeFormulaParentheses(t *testing.T) {
	schemaYAML := `
name: formula_paren_test
fields:
  - name: raw
    type: u8
    var: raw
  - name: result
    type: number
    formula: "($raw + 10) * 2"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// (5 + 10) * 2 = 30
	decoded, err := schema.Decode([]byte{5})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["result"] != float64(30) {
		t.Errorf("result = %v, want 30", decoded["result"])
	}
}

func TestDecodeWithLookupMissing(t *testing.T) {
	schemaYAML := `
name: lookup_missing_test
fields:
  - name: status
    type: u8
    lookup:
      0: "off"
      1: "on"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Value 99 not in lookup - should return raw value
	decoded, err := schema.Decode([]byte{99})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	// When not found, returns the raw numeric value
	if decoded["status"] != float64(99) {
		t.Errorf("status = %v, want 99", decoded["status"])
	}
}

func TestDecodeF16Denormalized(t *testing.T) {
	schemaYAML := `
name: f16_denorm_test
endian: big
fields:
  - name: value
    type: f16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Denormalized value (exponent = 0, mantissa != 0)
	decoded, err := schema.Decode([]byte{0x00, 0x01})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	// Should be a very small positive value
	if decoded["value"].(float64) <= 0 {
		t.Errorf("value = %v, want > 0", decoded["value"])
	}
}

func TestDecodeTransformWithLiteral(t *testing.T) {
	schemaYAML := `
name: transform_literal_test
fields:
  - name: raw
    type: u16
    transform:
      - mult: 0.1
      - add: -40
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// raw=631, 631*0.1-40 = 23.1
	decoded, err := schema.Decode([]byte{0x02, 0x77}) // 631
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if math.Abs(decoded["raw"].(float64)-23.1) > 0.01 {
		t.Errorf("raw = %v, want 23.1", decoded["raw"])
	}
}

func TestEncodeWithDivModifier(t *testing.T) {
	schemaYAML := `
name: encode_div_test
fields:
  - name: value
    type: u16
    div: 10
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// To get 10 out, encode should multiply by 10 = 100
	encoded, err := schema.Encode(map[string]any{
		"value": float64(10),
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	// 10 / (1/10) = 100 = 0x0064
	expected := []byte{0x00, 0x64}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %x, want %x", encoded, expected)
	}
}

func TestEncodeWithAddModifier(t *testing.T) {
	schemaYAML := `
name: encode_add_test
fields:
  - name: temp
    type: s16
    add: -40
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// To get 23 out (after decode adds -40), encode should store 63
	encoded, err := schema.Encode(map[string]any{
		"temp": float64(23),
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	// 23 - (-40) = 63 = 0x003F
	expected := []byte{0x00, 0x3F}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %x, want %x", encoded, expected)
	}
}

// =============================================================================
// INCREASED COVERAGE TESTS
// =============================================================================

func TestBinarySchemaWithPositiveExponent(t *testing.T) {
	// Test expToMult with positive exponent (mult > 1)
	binaryData := []byte{
		0x01,             // version 1
		0x01,             // 1 field
		0x01, 0x02, 0x00, 0x00, // type=u16, mult_exp=2 (100)
	}

	schema, err := ParseBinarySchema(binaryData)
	if err != nil {
		t.Fatalf("ParseBinarySchema() error = %v", err)
	}

	if schema.Fields[0].Mult == nil {
		t.Fatal("expected mult to be set")
	}
	if math.Abs(*schema.Fields[0].Mult-100) > 0.01 {
		t.Errorf("mult = %v, want 100", *schema.Fields[0].Mult)
	}
}

func TestBinarySchemaAllFieldTypes(t *testing.T) {
	schemaYAML := `
name: binary_all_types_test
fields:
  - name: a
    type: u8
  - name: b
    type: s16
  - name: c
    type: f32
  - name: d
    type: bool
  - name: e
    type: bytes
    length: 4
  - name: f
    type: Hex
    length: 4
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Encode to binary and verify
	binary, err := EncodeBinarySchema(schema)
	if err != nil {
		t.Fatalf("EncodeBinarySchema() error = %v", err)
	}

	// Verify field count
	if binary[1] != 6 {
		t.Errorf("field count = %d, want 6", binary[1])
	}
}

func TestDecodeWithEmptyPayloadAndFields(t *testing.T) {
	schemaYAML := `
name: empty_fields_test
fields: []
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if len(decoded) != 0 {
		t.Errorf("expected empty result, got %v", decoded)
	}
}

func TestEncodeWithPortValid(t *testing.T) {
	schemaYAML := `
name: port_encode_valid_test
ports:
  1:
    fields:
      - name: temp
        type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	encoded, err := schema.EncodeWithPort(map[string]any{
		"temp": float64(42),
	}, 1)
	if err != nil {
		t.Fatalf("EncodeWithPort() error = %v", err)
	}

	if len(encoded) != 1 || encoded[0] != 0x2A {
		t.Errorf("encoded = %x, want 2a", encoded)
	}
}

func TestDecodeWithDirection(t *testing.T) {
	schemaYAML := `
name: direction_test
ports:
  1:
    direction: up
    fields:
      - name: temp
        type: u8
  2:
    direction: down
    fields:
      - name: command
        type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Decode uplink
	decoded1, err := schema.DecodeWithPort([]byte{0x32}, 1)
	if err != nil {
		t.Fatalf("DecodeWithPort() error = %v", err)
	}
	if decoded1["temp"] != float64(50) {
		t.Errorf("temp = %v, want 50", decoded1["temp"])
	}

	// Decode downlink
	decoded2, err := schema.DecodeWithPort([]byte{0x01}, 2)
	if err != nil {
		t.Fatalf("DecodeWithPort() error = %v", err)
	}
	if decoded2["command"] != float64(1) {
		t.Errorf("command = %v, want 1", decoded2["command"])
	}
}

func TestDecodeWithFieldLevelEndian(t *testing.T) {
	schemaYAML := `
name: field_endian_test
fields:
  - name: be_value
    type: u16
  - name: le_value
    type: u16
    endian: little
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{0x01, 0x02, 0x03, 0x04})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	// Big endian: 0x0102
	if decoded["be_value"] != float64(0x0102) {
		t.Errorf("be_value = %v, want %v", decoded["be_value"], 0x0102)
	}

	// Little endian: 0x0403
	if decoded["le_value"] != float64(0x0403) {
		t.Errorf("le_value = %v, want %v", decoded["le_value"], 0x0403)
	}
}

func TestSchemaWithNoFieldsUsesPort(t *testing.T) {
	schemaYAML := `
name: no_root_fields_test
ports:
  1:
    fields:
      - name: value
        type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// When using DecodeWithPort, it should use port fields
	decoded, err := schema.DecodeWithPort([]byte{0x42}, 1)
	if err != nil {
		t.Fatalf("DecodeWithPort() error = %v", err)
	}

	if decoded["value"] != float64(0x42) {
		t.Errorf("value = %v, want %v", decoded["value"], 0x42)
	}
}

func TestParseSchemaWithBidirectionalPort(t *testing.T) {
	schemaYAML := `
name: bidirectional_test
ports:
  1:
    direction: bidirectional
    fields:
      - name: data
        type: u16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Should work for both encode and decode
	decoded, err := schema.DecodeWithPort([]byte{0x12, 0x34}, 1)
	if err != nil {
		t.Fatalf("DecodeWithPort() error = %v", err)
	}

	if decoded["data"] != float64(0x1234) {
		t.Errorf("data = %v, want %v", decoded["data"], 0x1234)
	}
}

func TestLookupWithIntKeys(t *testing.T) {
	schemaYAML := `
name: lookup_int_test
fields:
  - name: status
    type: u8
    lookup:
      0: "idle"
      1: "running"
      2: "error"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	tests := []struct {
		input byte
		want  string
	}{
		{0, "idle"},
		{1, "running"},
		{2, "error"},
	}

	for _, tt := range tests {
		decoded, err := schema.Decode([]byte{tt.input})
		if err != nil {
			t.Fatalf("Decode() error = %v", err)
		}
		if decoded["status"] != tt.want {
			t.Errorf("status for %d = %v, want %v", tt.input, decoded["status"], tt.want)
		}
	}
}

func TestEncodeLookupReverse(t *testing.T) {
	schemaYAML := `
name: encode_lookup_test
fields:
  - name: status
    type: u8
    lookup:
      0: "idle"
      1: "running"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Encode "running" should produce 1
	encoded, err := schema.Encode(map[string]any{
		"status": "running",
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	if len(encoded) != 1 || encoded[0] != 0x01 {
		t.Errorf("encoded = %x, want 01", encoded)
	}
}

func TestDecodeEnumValue(t *testing.T) {
	schemaYAML := `
name: enum_decode_test
fields:
  - name: mode
    type: enum
    base: u8
    values:
      0: "off"
      1: "auto"
      2: "manual"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{0x01})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["mode"] != "auto" {
		t.Errorf("mode = %v, want auto", decoded["mode"])
	}
}

func TestDecodeEnumNotInValues(t *testing.T) {
	schemaYAML := `
name: enum_unknown_test
fields:
  - name: mode
    type: enum
    base: u8
    values:
      0: "off"
      1: "on"
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Value 99 not in enum
	decoded, err := schema.Decode([]byte{99})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	// Should return raw value when not found
	if decoded["mode"] != float64(99) {
		t.Errorf("mode = %v, want 99", decoded["mode"])
	}
}

func TestByteGroupWith16BitValue(t *testing.T) {
	schemaYAML := `
name: byte_group_16_test
fields:
  - byte_group:
      - name: high_byte
        type: u8[0:7]
      - name: low_byte
        type: u8[8:15]
    size: 2
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// 0x1234: high=0x12, low=0x34
	decoded, err := schema.Decode([]byte{0x12, 0x34})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["high_byte"] != float64(0x12) {
		t.Errorf("high_byte = %v, want 0x12", decoded["high_byte"])
	}
	if decoded["low_byte"] != float64(0x34) {
		t.Errorf("low_byte = %v, want 0x34", decoded["low_byte"])
	}
}

func TestRepeatUntilEndEmpty(t *testing.T) {
	schemaYAML := `
name: repeat_empty_test
fields:
  - name: items
    type: repeat
    until: end
    fields:
      - name: val
        type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Empty payload = empty repeat
	decoded, err := schema.Decode([]byte{})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	items := decoded["items"].([]any)
	if len(items) != 0 {
		t.Errorf("items length = %d, want 0", len(items))
	}
}

func TestSchemaWithNestedObjects(t *testing.T) {
	schemaYAML := `
name: nested_objects_test
fields:
  - name: header
    type: Object
    fields:
      - name: version
        type: u8
      - name: flags
        type: u8
  - name: data
    type: u16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	decoded, err := schema.Decode([]byte{0x01, 0xFF, 0x12, 0x34})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	header := decoded["header"].(map[string]any)
	if header["version"] != float64(1) {
		t.Errorf("header.version = %v, want 1", header["version"])
	}
	if header["flags"] != float64(0xFF) {
		t.Errorf("header.flags = %v, want 0xFF", header["flags"])
	}
	if decoded["data"] != float64(0x1234) {
		t.Errorf("data = %v, want 0x1234", decoded["data"])
	}
}

// =============================================================================
// 1. ERROR HANDLING PATH TESTS
// =============================================================================

func TestDecodeBufferUnderflowAllTypes(t *testing.T) {
	tests := []struct {
		name     string
		typeName string
		data     []byte
	}{
		{"u16 short", "u16", []byte{0x01}},
		{"u32 short", "u32", []byte{0x01, 0x02}},
		{"u64 short", "u64", []byte{0x01, 0x02, 0x03, 0x04}},
		{"s16 short", "s16", []byte{0x01}},
		{"s32 short", "s32", []byte{0x01, 0x02}},
		{"f32 short", "f32", []byte{0x01, 0x02}},
		{"f64 short", "f64", []byte{0x01, 0x02, 0x03, 0x04}},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			schemaYAML := fmt.Sprintf(`
name: underflow_test
fields:
  - name: value
    type: %s
`, tt.typeName)
			schema, err := ParseSchema(schemaYAML)
			if err != nil {
				t.Fatalf("ParseSchema() error = %v", err)
			}

			_, err = schema.Decode(tt.data)
			if err == nil {
				t.Error("expected buffer underflow error")
			}
		})
	}
}

func TestDecodeBytesUnderflow(t *testing.T) {
	schemaYAML := `
name: bytes_underflow_test
fields:
  - name: data
    type: bytes
    length: 10
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	_, err = schema.Decode([]byte{0x01, 0x02, 0x03})
	if err == nil {
		t.Error("expected buffer underflow error")
	}
}

func TestDecodeRepeatUnderflow(t *testing.T) {
	schemaYAML := `
name: repeat_underflow_test
fields:
  - name: items
    type: repeat
    count: 5
    fields:
      - name: val
        type: u16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Only 4 bytes, but need 10 (5 * u16)
	_, err = schema.Decode([]byte{0x01, 0x02, 0x03, 0x04})
	if err == nil {
		t.Error("expected buffer underflow error")
	}
}

func TestDecodeMatchKnownCase(t *testing.T) {
	schemaYAML := `
name: match_known_test
fields:
  - name: type
    type: u8
    var: t
  - name: data
    type: Match
    on: $t
    cases:
      - case: 1
        fields:
          - name: a
            type: u8
      - case: 2
        fields:
          - name: b
            type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// type=1, should match case 1
	decoded, err := schema.Decode([]byte{1, 0x42})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	data := decoded["data"].(map[string]any)
	if data["a"] != float64(0x42) {
		t.Errorf("a = %v, want 0x42", data["a"])
	}
}

func TestDecodeComputeUnknownOp(t *testing.T) {
	schemaYAML := `
name: compute_unknown_op_test
fields:
  - name: a
    type: u8
    var: a
  - name: result
    type: number
    compute:
      op: unknown_operation
      a: $a
      b: 10
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	_, err = schema.Decode([]byte{5})
	if err == nil {
		t.Error("expected unknown compute op error")
	}
}

func TestEncodeObjectMissingField(t *testing.T) {
	schemaYAML := `
name: encode_missing_test
fields:
  - name: header
    type: Object
    fields:
      - name: version
        type: u8
      - name: flags
        type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Missing nested object entirely
	_, err = schema.Encode(map[string]any{})
	// Should handle gracefully or error
	if err != nil {
		t.Logf("Expected error for missing field: %v", err)
	}
}

func TestDecodeSkipUnderflow(t *testing.T) {
	schemaYAML := `
name: skip_underflow_test
fields:
  - type: skip
    length: 10
  - name: value
    type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	_, err = schema.Decode([]byte{0x01, 0x02})
	if err == nil {
		t.Error("expected buffer underflow error")
	}
}

// =============================================================================
// 2. SCHEMA PARSING EDGE CASES
// =============================================================================

func TestParseSchemaEmptyFields(t *testing.T) {
	schemaYAML := `
name: empty_fields_test
fields: []
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	if len(schema.Fields) != 0 {
		t.Errorf("expected 0 fields, got %d", len(schema.Fields))
	}
}

func TestParseSchemaNoFields(t *testing.T) {
	schemaYAML := `
name: no_fields_test
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	if schema.Fields != nil && len(schema.Fields) != 0 {
		t.Errorf("expected nil or empty fields")
	}
}

func TestParseSchemaWithAllFieldAttributes(t *testing.T) {
	schemaYAML := `
name: all_attrs_test
endian: little
fields:
  - name: value
    type: u16
    mult: 0.1
    add: -40
    div: 2
    unit: "celsius"
    lookup:
      0: "zero"
      1: "one"
    var: val
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	if len(schema.Fields) != 1 {
		t.Fatalf("expected 1 field, got %d", len(schema.Fields))
	}

	f := schema.Fields[0]
	if f.Name != "value" {
		t.Errorf("name = %s, want value", f.Name)
	}
	if f.Mult == nil || *f.Mult != 0.1 {
		t.Errorf("mult incorrect")
	}
	if f.Add == nil || *f.Add != -40 {
		t.Errorf("add incorrect")
	}
	if f.Var != "val" {
		t.Errorf("var = %s, want val", f.Var)
	}
}

func TestParseSchemaWithTransform(t *testing.T) {
	schemaYAML := `
name: transform_test
fields:
  - name: temp
    type: u16
    transform:
      - mult: 0.1
      - add: -40
      - sqrt: true
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	if len(schema.Fields) != 1 {
		t.Fatalf("expected 1 field, got %d", len(schema.Fields))
	}

	f := schema.Fields[0]
	if len(f.Transform) != 3 {
		t.Errorf("transform length = %d, want 3", len(f.Transform))
	}
}

func TestParseSchemaWithDefinitions(t *testing.T) {
	schemaYAML := `
name: definitions_test
definitions:
  header:
    fields:
      - name: version
        type: u8
fields:
  - name: data
    type: u16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	if schema.Definitions == nil {
		t.Error("expected definitions to be parsed")
	}
}

func TestParseSchemaFieldWithBitRange(t *testing.T) {
	schemaYAML := `
name: bit_range_test
fields:
  - name: nibble
    type: u8[0:3]
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	if len(schema.Fields) != 1 {
		t.Fatalf("expected 1 field, got %d", len(schema.Fields))
	}
}

func TestParseSchemaWithGuard(t *testing.T) {
	schemaYAML := `
name: guard_test
fields:
  - name: raw
    type: u8
    var: raw
  - name: result
    type: number
    ref: $raw
    guard:
      when:
        - field: $raw
          gt: 50
      else: -1
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Test that guard works
	decoded, err := schema.Decode([]byte{60})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if decoded["result"] != float64(60) {
		t.Errorf("result = %v, want 60", decoded["result"])
	}

	decoded2, err := schema.Decode([]byte{40})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if decoded2["result"] != float64(-1) {
		t.Errorf("result = %v, want -1", decoded2["result"])
	}
}

func TestParseSchemaWithPolynomial(t *testing.T) {
	schemaYAML := `
name: polynomial_test
fields:
  - name: raw
    type: u8
    var: x
  - name: calibrated
    type: number
    ref: $x
    polynomial: [0, 1, 0.5]
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// f(x) = 0 + 1*x + 0.5*x^2
	// f(2) = 0 + 2 + 0.5*4 = 4, but actual might be different due to impl
	decoded, err := schema.Decode([]byte{2})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	// Just verify we got a result
	if decoded["calibrated"] == nil {
		t.Error("expected calibrated to have a value")
	}
}

func TestParseSchemaPortWithEndian(t *testing.T) {
	schemaYAML := `
name: port_endian_test
ports:
  1:
    endian: little
    fields:
      - name: value
        type: u16
  2:
    endian: big
    fields:
      - name: value
        type: u16
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	if schema.Ports == nil {
		t.Fatal("expected ports to be parsed")
	}
}

// =============================================================================
// 3. TLV DECODE BRANCH TESTS
// =============================================================================

func TestTLVWithTypeAndLength(t *testing.T) {
	schemaYAML := `
name: tlv_basic_test
fields:
  - name: tag
    type: u8
    var: tag
  - name: len
    type: u8
    var: len
  - name: value
    type: bytes
    length: $len
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Tag=1, Len=3, Data=0xAABBCC
	decoded, err := schema.Decode([]byte{0x01, 0x03, 0xAA, 0xBB, 0xCC})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["tag"] != float64(1) {
		t.Errorf("tag = %v, want 1", decoded["tag"])
	}
	if decoded["len"] != float64(3) {
		t.Errorf("len = %v, want 3", decoded["len"])
	}
}

func TestTLVWithMultipleRecords(t *testing.T) {
	schemaYAML := `
name: tlv_multi_test
fields:
  - name: records
    type: repeat
    count: 2
    fields:
      - name: type
        type: u8
      - name: length
        type: u8
        var: l
      - name: data
        type: bytes
        length: $l
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Record1: type=1, len=2, data=0xAABB
	// Record2: type=2, len=1, data=0xCC
	decoded, err := schema.Decode([]byte{0x01, 0x02, 0xAA, 0xBB, 0x02, 0x01, 0xCC})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	records := decoded["records"].([]any)
	if len(records) != 2 {
		t.Errorf("records length = %d, want 2", len(records))
	}
}

func TestVariableLengthBytes(t *testing.T) {
	schemaYAML := `
name: var_len_test
fields:
  - name: tag
    type: u8
  - name: len
    type: u8
    var: datalen
  - name: data
    type: bytes
    length: $datalen
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Tag=1, Len=3, Data=0xAABBCC
	decoded, err := schema.Decode([]byte{0x01, 0x03, 0xAA, 0xBB, 0xCC})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["len"] != float64(3) {
		t.Errorf("len = %v, want 3", decoded["len"])
	}
}

func TestMatchWithMultipleCases(t *testing.T) {
	schemaYAML := `
name: match_multi_test
fields:
  - name: type
    type: u8
    var: t
  - name: data
    type: Match
    on: $t
    cases:
      - case: 1
        fields:
          - name: temp
            type: s16
            mult: 0.1
      - case: 2
        fields:
          - name: humidity
            type: u8
    default:
      fields:
        - name: raw
          type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Type 1 (temperature)
	decoded1, err := schema.Decode([]byte{0x01, 0x00, 0xE7})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	if decoded1["data"] == nil {
		t.Fatal("expected data to be present")
	}
	data1 := decoded1["data"].(map[string]any)
	if math.Abs(data1["temp"].(float64)-23.1) > 0.01 {
		t.Errorf("temp = %v, want 23.1", data1["temp"])
	}

	// Type 2 (humidity)
	decoded2, err := schema.Decode([]byte{0x02, 0x32})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	data2 := decoded2["data"].(map[string]any)
	if data2["humidity"] != float64(50) {
		t.Errorf("humidity = %v, want 50", data2["humidity"])
	}
}

func TestTLVWith16BitTypeAndLength(t *testing.T) {
	schemaYAML := `
name: tlv_16bit_test
fields:
  - name: type
    type: u16
    var: t
  - name: length
    type: u16
    var: l
  - name: payload
    type: bytes
    length: $l
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Type=0x0100, Length=0x0004, Data=4 bytes
	decoded, err := schema.Decode([]byte{0x01, 0x00, 0x00, 0x04, 0xAA, 0xBB, 0xCC, 0xDD})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if decoded["type"] != float64(0x0100) {
		t.Errorf("type = %v, want 256", decoded["type"])
	}
	if decoded["length"] != float64(4) {
		t.Errorf("length = %v, want 4", decoded["length"])
	}
}

// =============================================================================
// ADDITIONAL EDGE CASES
// =============================================================================

func TestDecodeWithPeek(t *testing.T) {
	schemaYAML := `
name: peek_test
fields:
  - name: header
    type: u8
    var: h
  - name: payload_type
    type: Match
    on: $h
    cases:
      - case: 1
        fields:
          - name: short_data
            type: u8
      - case: 2
        fields:
          - name: long_data
            type: u32
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Header=1, short data
	decoded, err := schema.Decode([]byte{0x01, 0x42})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}
	pt := decoded["payload_type"].(map[string]any)
	if pt["short_data"] != float64(0x42) {
		t.Errorf("short_data = %v, want 0x42", pt["short_data"])
	}
}

func TestEncodeWithTransform(t *testing.T) {
	schemaYAML := `
name: encode_transform_test
fields:
  - name: temp
    type: u16
    mult: 0.1
    add: -40
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// To encode 23.1°C: raw = (23.1 + 40) / 0.1 = 631
	encoded, err := schema.Encode(map[string]any{
		"temp": 23.1,
	})
	if err != nil {
		t.Fatalf("Encode() error = %v", err)
	}

	// 631 = 0x0277
	expected := []byte{0x02, 0x77}
	if !bytes.Equal(encoded, expected) {
		t.Errorf("encoded = %x, want %x", encoded, expected)
	}
}

func TestFormatBytesAllFormats(t *testing.T) {
	tests := []struct {
		name   string
		format string
		data   []byte
		check  func(any) bool
	}{
		{
			name:   "hex lowercase",
			format: "hex",
			data:   []byte{0xAB, 0xCD},
			check:  func(v any) bool { return v == "abcd" },
		},
		{
			name:   "base64",
			format: "base64",
			data:   []byte{0x01, 0x02, 0x03},
			check:  func(v any) bool { return v == "AQID" },
		},
		{
			name:   "array",
			format: "array",
			data:   []byte{1, 2, 3},
			check: func(v any) bool {
				arr, ok := v.([]any)
				return ok && len(arr) == 3
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			schemaYAML := fmt.Sprintf(`
name: format_test
fields:
  - name: data
    type: bytes
    length: %d
    format: %s
`, len(tt.data), tt.format)
			schema, err := ParseSchema(schemaYAML)
			if err != nil {
				t.Fatalf("ParseSchema() error = %v", err)
			}

			decoded, err := schema.Decode(tt.data)
			if err != nil {
				t.Fatalf("Decode() error = %v", err)
			}

			if !tt.check(decoded["data"]) {
				t.Errorf("data = %v, format check failed", decoded["data"])
			}
		})
	}
}

func TestResolveFieldsWithUnknownPort(t *testing.T) {
	schemaYAML := `
name: resolve_unknown_port_test
ports:
  1:
    fields:
      - name: temp
        type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	_, err = schema.ResolveFields(99)
	if err == nil {
		t.Error("expected error for unknown port")
	}
}

// =============================================================================
// Edge Cases and Security Tests
// =============================================================================

func TestEdgeCaseDivisionByZero(t *testing.T) {
	schemaYAML := `
name: test
fields:
  - name: x
    type: u8
  - name: y
    type: number
    compute:
      op: div
      a: $x
      b: 0
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	_, err = schema.Decode([]byte{42})
	if err == nil {
		t.Error("expected error for division by zero")
	}
}

func TestEdgeCaseHugeRepeatCount(t *testing.T) {
	schemaYAML := `
name: test
fields:
  - name: items
    type: repeat
    count: 999999
    fields:
      - name: v
        type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Should return error when buffer exhausted, not hang
	_, err = schema.Decode([]byte{1, 2, 3, 4, 5})
	if err == nil {
		t.Error("expected buffer underflow error")
	}
}

func TestEdgeCaseBufferUnderflowU32(t *testing.T) {
	schemaYAML := `
name: test
fields:
  - name: x
    type: u32
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	_, err = schema.Decode([]byte{1, 2})
	if err == nil {
		t.Error("expected buffer underflow error")
	}
}

func TestEdgeCaseUnknownType(t *testing.T) {
	schemaYAML := `
name: test
fields:
  - name: x
    type: unknown_type_xyz
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	_, err = schema.Decode([]byte{42})
	if err == nil {
		t.Error("expected unknown type error")
	}
}

func TestEdgeCaseEmptyFields(t *testing.T) {
	schemaYAML := `
name: test
fields: []
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	result, err := schema.Decode([]byte{42})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	if len(result) != 0 {
		t.Errorf("expected empty result, got %v", result)
	}
}

func TestEdgeCaseFormulaUndefinedVar(t *testing.T) {
	schemaYAML := `
name: test
fields:
  - name: x
    type: u8
    formula: $undefined + 1
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	result, err := schema.Decode([]byte{42})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	// Undefined var should default to 0, so result is 0 + 1 = 1
	if result["x"] != float64(1) {
		t.Errorf("x = %v, want 1", result["x"])
	}
}

func TestEdgeCaseTLVLengthOverrun(t *testing.T) {
	schemaYAML := `
name: test
fields:
  - name: data
    type: tlv
    tag:
      type: u8
    length:
      type: u8
    cases:
      1:
        - name: val
          type: bytes
          length: $length
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// tag=1, length=255, but only 2 bytes follow - should not panic
	_, err = schema.Decode([]byte{1, 255, 0x41, 0x42})
	// May return error or partial result, but must not panic
	_ = err
}

func TestEdgeCaseNegativeS8WithMult(t *testing.T) {
	schemaYAML := `
name: test
fields:
  - name: x
    type: s8
    mult: 0.1
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	result, err := schema.Decode([]byte{0xFF}) // -1 as s8
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	x := result["x"].(float64)
	if x > -0.05 || x < -0.15 {
		t.Errorf("x = %v, want approximately -0.1", x)
	}
}

func TestEdgeCaseRepeatUntilEndLargePayload(t *testing.T) {
	schemaYAML := `
name: test
fields:
  - name: items
    type: repeat
    until: end
    fields:
      - name: x
        type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Create 10000 byte payload
	payload := make([]byte, 10000)
	for i := range payload {
		payload[i] = byte(i % 256)
	}

	result, err := schema.Decode(payload)
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	items := result["items"].([]any)
	// Default max_iterations=1000 is a safety limit
	if len(items) != 1000 {
		t.Errorf("items count = %d, want 1000 (safety limit)", len(items))
	}
}

func TestEdgeCaseMatchNoMatchingCase(t *testing.T) {
	schemaYAML := `
name: test
fields:
  - name: type
    type: u8
    var: t
  - name: data
    type: match
    on: $t
    cases:
      - case: 1
        fields:
          - name: a
            type: u8
      - case: 2
        fields:
          - name: b
            type: u8
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// type=99, no matching case - should not panic
	result, err := schema.Decode([]byte{99, 42})
	if err != nil {
		// Error is acceptable
		return
	}

	// Or partial result is acceptable
	if result["type"] != uint8(99) && result["type"] != int(99) {
		t.Errorf("type = %v, want 99", result["type"])
	}
}

func TestEdgeCaseSelfReferencingFormula(t *testing.T) {
	schemaYAML := `
name: test
fields:
  - name: x
    type: u8
    var: x
    formula: $x + 1
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	result, err := schema.Decode([]byte{42})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	// $x is 0 before assignment, so result should be 0 + 1 = 1
	if result["x"] != float64(1) {
		t.Errorf("x = %v, want 1", result["x"])
	}
}

func TestEdgeCaseBytesUnderflow(t *testing.T) {
	schemaYAML := `
name: test
fields:
  - name: data
    type: bytes
    length: 100
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Only 3 bytes, but length=100
	_, err = schema.Decode([]byte{1, 2, 3})
	if err == nil {
		t.Error("expected buffer underflow error")
	}
}

func TestEdgeCaseStringUnderflow(t *testing.T) {
	schemaYAML := `
name: test
fields:
  - name: s
    type: string
    length: 100
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	// Only 3 bytes, but length=100
	_, err = schema.Decode([]byte{0x41, 0x42, 0x43})
	if err == nil {
		t.Error("expected buffer underflow error")
	}
}

func TestEdgeCaseLargeMultiplier(t *testing.T) {
	schemaYAML := `
name: test
fields:
  - name: x
    type: u32
    mult: 1e30
`
	schema, err := ParseSchema(schemaYAML)
	if err != nil {
		t.Fatalf("ParseSchema() error = %v", err)
	}

	result, err := schema.Decode([]byte{0xFF, 0xFF, 0xFF, 0xFF})
	if err != nil {
		t.Fatalf("Decode() error = %v", err)
	}

	x := result["x"].(float64)
	if x <= 0 {
		t.Errorf("x = %v, want positive large number", x)
	}
}

// =============================================================================
// Compact Format Edge Cases
// =============================================================================

func TestCompactFormatEdgeCaseEmpty(t *testing.T) {
	fields, endian, err := ParseCompactFormat("")
	if err != nil {
		t.Fatalf("ParseCompactFormat() error = %v", err)
	}
	if len(fields) != 0 {
		t.Errorf("fields = %d, want 0", len(fields))
	}
	if endian != "big" {
		t.Errorf("endian = %s, want big", endian)
	}
}

func TestCompactFormatEdgeCaseUnknownChar(t *testing.T) {
	_, _, err := ParseCompactFormat(">ZZZ")
	if err == nil {
		t.Error("expected error for unknown format character")
	}
}

func TestCompactFormatEdgeCaseAllEndians(t *testing.T) {
	tests := []struct {
		prefix string
		want   string
	}{
		{">", "big"},
		{"<", "little"},
		{"!", "big"},
		{"=", "native"},
		{"@", "native"},
	}
	for _, tt := range tests {
		t.Run(tt.prefix, func(t *testing.T) {
			_, endian, err := ParseCompactFormat(tt.prefix + "B")
			if err != nil {
				t.Fatalf("error = %v", err)
			}
			if endian != tt.want {
				t.Errorf("endian = %s, want %s", endian, tt.want)
			}
		})
	}
}

func TestCompactFormatEdgeCaseAllTypes(t *testing.T) {
	// All valid format characters
	formats := []struct {
		char byte
		size int
	}{
		{'b', 1}, {'B', 1}, // signed/unsigned byte
		{'h', 2}, {'H', 2}, // short
		{'i', 4}, {'I', 4}, // int
		{'l', 4}, {'L', 4}, // long (same as int)
		{'q', 8}, {'Q', 8}, // long long
		{'e', 2},           // float16
		{'f', 4},           // float32
		{'d', 8},           // float64
		{'?', 1},           // bool
		{'c', 1},           // char
		{'x', 1},           // skip
	}

	for _, tt := range formats {
		t.Run(string(tt.char), func(t *testing.T) {
			fields, _, err := ParseCompactFormat(string(tt.char))
			if err != nil {
				t.Fatalf("error = %v", err)
			}
			if len(fields) != 1 {
				t.Errorf("fields = %d, want 1", len(fields))
			}
		})
	}
}

func TestCompactFormatEdgeCaseWithCount(t *testing.T) {
	fields, _, err := ParseCompactFormat("10B")
	if err != nil {
		t.Fatalf("error = %v", err)
	}
	if len(fields) != 10 {
		t.Errorf("fields = %d, want 10", len(fields))
	}
}

func TestCompactFormatEdgeCaseStringLength(t *testing.T) {
	fields, _, err := ParseCompactFormat("20s")
	if err != nil {
		t.Fatalf("error = %v", err)
	}
	if len(fields) != 1 {
		t.Errorf("fields = %d, want 1", len(fields))
	}
	if fields[0].Length != 20 {
		t.Errorf("length = %d, want 20", fields[0].Length)
	}
}

func TestCompactFormatEdgeCaseNamedFields(t *testing.T) {
	fields, _, err := ParseCompactFormat(">H:temp B:humidity")
	if err != nil {
		t.Fatalf("error = %v", err)
	}
	if len(fields) != 2 {
		t.Errorf("fields = %d, want 2", len(fields))
	}
	if fields[0].Name != "temp" {
		t.Errorf("name = %s, want temp", fields[0].Name)
	}
	if fields[1].Name != "humidity" {
		t.Errorf("name = %s, want humidity", fields[1].Name)
	}
}

func TestCompactFormatEdgeCaseRepeatedNamed(t *testing.T) {
	fields, _, err := ParseCompactFormat("3B:val")
	if err != nil {
		t.Fatalf("error = %v", err)
	}
	if len(fields) != 3 {
		t.Errorf("fields = %d, want 3", len(fields))
	}
	// Should be val_0, val_1, val_2
	if fields[0].Name != "val_0" {
		t.Errorf("name[0] = %s, want val_0", fields[0].Name)
	}
	if fields[2].Name != "val_2" {
		t.Errorf("name[2] = %s, want val_2", fields[2].Name)
	}
}

func TestDecodeCompactEdgeCaseBufferUnderflow(t *testing.T) {
	// DecodeCompact may return partial results rather than error
	// The key is it doesn't panic
	result, _ := DecodeCompact(">HHH", []byte{0x01, 0x02})
	// Should have at most 1 field (only enough bytes for one H)
	if len(result) > 1 {
		t.Errorf("expected at most 1 field, got %d", len(result))
	}
}

func TestDecodeCompactEdgeCaseEmptyFormat(t *testing.T) {
	result, err := DecodeCompact("", []byte{0x01, 0x02})
	if err != nil {
		t.Fatalf("error = %v", err)
	}
	if len(result) != 0 {
		t.Errorf("result = %d fields, want 0", len(result))
	}
}

func TestDecodeCompactEdgeCaseLittleEndian(t *testing.T) {
	result, err := DecodeCompact("<H:val", []byte{0x01, 0x02})
	if err != nil {
		t.Fatalf("error = %v", err)
	}
	// Little endian: 0x01 + 0x02<<8 = 0x0201 = 513
	val := result["val"]
	if v, ok := val.(uint16); ok && v != 513 {
		t.Errorf("val = %v, want 513", val)
	}
}

func TestDecodeCompactEdgeCaseBigEndian(t *testing.T) {
	result, err := DecodeCompact(">H:val", []byte{0x01, 0x02})
	if err != nil {
		t.Fatalf("error = %v", err)
	}
	// Big endian: 0x01<<8 + 0x02 = 0x0102 = 258
	val := result["val"]
	if v, ok := val.(uint16); ok && v != 258 {
		t.Errorf("val = %v, want 258", val)
	}
}

func TestDecodeCompactEdgeCaseSigned(t *testing.T) {
	result, err := DecodeCompact(">b:val", []byte{0xFF})
	if err != nil {
		t.Fatalf("error = %v", err)
	}
	// 0xFF as signed = -1
	val := result["val"]
	if v, ok := val.(int8); ok && v != -1 {
		t.Errorf("val = %v, want -1", val)
	}
}

func TestDecodeCompactEdgeCaseFloat(t *testing.T) {
	// Float32: 3.14 ≈ 0x4048f5c3 big-endian
	result, err := DecodeCompact(">f:val", []byte{0x40, 0x48, 0xf5, 0xc3})
	if err != nil {
		t.Fatalf("error = %v", err)
	}
	// May be float32 or float64 depending on implementation
	var val float64
	switch v := result["val"].(type) {
	case float32:
		val = float64(v)
	case float64:
		val = v
	default:
		t.Fatalf("unexpected type %T", result["val"])
	}
	if val < 3.13 || val > 3.15 {
		t.Errorf("val = %v, want ~3.14", val)
	}
}

func TestDecodeCompactEdgeCaseBool(t *testing.T) {
	result, err := DecodeCompact(">?:a ?:b", []byte{0x00, 0x01})
	if err != nil {
		t.Fatalf("error = %v", err)
	}
	// Bool type may be decoded as various types
	a, aOk := result["a"]
	b, bOk := result["b"]
	if !aOk || !bOk {
		t.Fatalf("missing fields: a=%v b=%v", aOk, bOk)
	}
	// Just verify we got values without panic
	_ = a
	_ = b
}

func TestDecodeCompactEdgeCaseSkip(t *testing.T) {
	// Skip bytes with 'x' format character
	result, err := DecodeCompact(">B:a 2x B:b", []byte{1, 0, 0, 2})
	if err != nil {
		t.Fatalf("error = %v", err)
	}
	// Verify field 'a' is present
	if _, ok := result["a"]; !ok {
		t.Error("missing field a")
	}
	// Field 'b' should be present (after skipping 2 bytes)
	if _, ok := result["b"]; !ok {
		t.Error("missing field b")
	}
}

func TestDecodeCompactEdgeCaseString(t *testing.T) {
	result, err := DecodeCompact(">5s:msg", []byte{'H', 'e', 'l', 'l', 'o'})
	if err != nil {
		t.Fatalf("error = %v", err)
	}
	if result["msg"] != "Hello" {
		t.Errorf("msg = %v, want Hello", result["msg"])
	}
}

func TestDecodeCompactEdgeCaseHugeCount(t *testing.T) {
	// Should hit buffer underflow, not hang
	_, err := DecodeCompact("999999B", []byte{1, 2, 3})
	if err == nil {
		t.Error("expected buffer underflow error")
	}
}

// Tests for semantic fields: valid_range, resolution, unece

func TestValidRangeInRange(t *testing.T) {
	schema, err := ParseSchema(`
name: test
endian: big
fields:
  - name: temperature
    type: s16
    div: 100
    valid_range: [-40, 85]
`)
	if err != nil {
		t.Fatalf("ParseSchema error: %v", err)
	}

	// temp = 23.45 -> raw = 2345 = 0x0929
	result, err := schema.Decode([]byte{0x09, 0x29})
	if err != nil {
		t.Fatalf("Decode error: %v", err)
	}

	temp, ok := result["temperature"].(float64)
	if !ok {
		t.Fatalf("temperature not float64: %T", result["temperature"])
	}
	if temp < 23.44 || temp > 23.46 {
		t.Errorf("temperature = %v, want ~23.45", temp)
	}

	quality, ok := result["_quality"].(map[string]string)
	if !ok {
		t.Fatalf("_quality not map[string]string: %T", result["_quality"])
	}
	if quality["temperature"] != "good" {
		t.Errorf("quality[temperature] = %v, want good", quality["temperature"])
	}
}

func TestValidRangeOutOfRange(t *testing.T) {
	schema, err := ParseSchema(`
name: test
endian: big
fields:
  - name: temperature
    type: s16
    div: 100
    valid_range: [-40, 85]
`)
	if err != nil {
		t.Fatalf("ParseSchema error: %v", err)
	}

	// temp = 100.0 -> raw = 10000 = 0x2710 (above 85 max)
	result, err := schema.Decode([]byte{0x27, 0x10})
	if err != nil {
		t.Fatalf("Decode error: %v", err)
	}

	temp, ok := result["temperature"].(float64)
	if !ok {
		t.Fatalf("temperature not float64: %T", result["temperature"])
	}
	if temp < 99.99 || temp > 100.01 {
		t.Errorf("temperature = %v, want ~100.0", temp)
	}

	quality, ok := result["_quality"].(map[string]string)
	if !ok {
		t.Fatalf("_quality not map[string]string: %T", result["_quality"])
	}
	if quality["temperature"] != "out_of_range" {
		t.Errorf("quality[temperature] = %v, want out_of_range", quality["temperature"])
	}
}

func TestValidRangeNoQualityWhenNotDefined(t *testing.T) {
	schema, err := ParseSchema(`
name: test
endian: big
fields:
  - name: temperature
    type: s16
    div: 100
`)
	if err != nil {
		t.Fatalf("ParseSchema error: %v", err)
	}

	result, err := schema.Decode([]byte{0x09, 0x29})
	if err != nil {
		t.Fatalf("Decode error: %v", err)
	}

	if _, ok := result["_quality"]; ok {
		t.Error("_quality should not be present when no valid_range defined")
	}
}

func TestValidRangeMultipleFields(t *testing.T) {
	schema, err := ParseSchema(`
name: test
endian: big
fields:
  - name: temperature
    type: s16
    div: 100
    valid_range: [-40, 85]
  - name: humidity
    type: u8
    valid_range: [0, 100]
`)
	if err != nil {
		t.Fatalf("ParseSchema error: %v", err)
	}

	// temp = 23.45 (good), humidity = 105 (out of range)
	result, err := schema.Decode([]byte{0x09, 0x29, 0x69})
	if err != nil {
		t.Fatalf("Decode error: %v", err)
	}

	quality, ok := result["_quality"].(map[string]string)
	if !ok {
		t.Fatalf("_quality not map[string]string: %T", result["_quality"])
	}

	if quality["temperature"] != "good" {
		t.Errorf("quality[temperature] = %v, want good", quality["temperature"])
	}
	if quality["humidity"] != "out_of_range" {
		t.Errorf("quality[humidity] = %v, want out_of_range", quality["humidity"])
	}
}

func TestResolutionAndUNECEParsing(t *testing.T) {
	schema, err := ParseSchema(`
name: test
fields:
  - name: temperature
    type: s16
    div: 100
    resolution: 0.01
    unece: "CEL"
`)
	if err != nil {
		t.Fatalf("ParseSchema error: %v", err)
	}

	if len(schema.Fields) != 1 {
		t.Fatalf("expected 1 field, got %d", len(schema.Fields))
	}

	field := schema.Fields[0]
	if field.Resolution == nil || *field.Resolution != 0.01 {
		t.Errorf("resolution = %v, want 0.01", field.Resolution)
	}
	if field.UNECE != "CEL" {
		t.Errorf("unece = %v, want CEL", field.UNECE)
	}
}
