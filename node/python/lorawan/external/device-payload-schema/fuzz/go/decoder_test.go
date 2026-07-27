// Package fuzz provides fuzz testing for payload schema decoder
//
// Run with:
//   go test -fuzz=FuzzDecode -fuzztime=60s
//   go test -fuzz=FuzzDecodeEncode -fuzztime=60s
package fuzz

import (
	"encoding/binary"
	"math"
	"testing"
)

// EnvSensor represents decoded environmental sensor data
type EnvSensor struct {
	Temperature float64
	Humidity    float64
	BatteryMV   uint16
	Status      uint8
}

// DecodeEnvSensor decodes env_sensor payload (big-endian)
// Returns decoded struct and error if payload too short
func DecodeEnvSensor(data []byte) (EnvSensor, error) {
	var s EnvSensor

	if len(data) < 6 {
		return s, &DecodeError{"payload too short", len(data), 6}
	}

	// s16 temperature with mult 0.01
	rawTemp := int16(binary.BigEndian.Uint16(data[0:2]))
	s.Temperature = float64(rawTemp) * 0.01

	// u8 humidity with mult 0.5
	s.Humidity = float64(data[2]) * 0.5

	// u16 battery_mv
	s.BatteryMV = binary.BigEndian.Uint16(data[3:5])

	// u8 status
	s.Status = data[5]

	return s, nil
}

// EncodeEnvSensor encodes env_sensor struct to bytes
func EncodeEnvSensor(s EnvSensor) []byte {
	data := make([]byte, 6)

	// s16 temperature (reverse mult 0.01)
	rawTemp := int16(math.Round(s.Temperature / 0.01))
	binary.BigEndian.PutUint16(data[0:2], uint16(rawTemp))

	// u8 humidity (reverse mult 0.5)
	data[2] = uint8(math.Round(s.Humidity / 0.5))

	// u16 battery_mv
	binary.BigEndian.PutUint16(data[3:5], s.BatteryMV)

	// u8 status
	data[5] = s.Status

	return data
}

// DecodeError represents a decoding error
type DecodeError struct {
	Message  string
	Got      int
	Expected int
}

func (e *DecodeError) Error() string {
	return e.Message
}

// FuzzDecode tests that decoder doesn't panic on any input
func FuzzDecode(f *testing.F) {
	// Seed corpus with known-good payloads from test vectors
	f.Add([]byte{0x09, 0x29, 0x82, 0x0C, 0xE4, 0x00}) // normal_room
	f.Add([]byte{0xFE, 0x0C, 0x14, 0x0B, 0xB8, 0x01}) // cold_dry
	f.Add([]byte{0x0D, 0xAC, 0xC8, 0x0D, 0x48, 0x02}) // hot_humid
	f.Add([]byte{0x08, 0x98, 0x78, 0x09, 0xC4, 0x04}) // low_battery

	// Edge cases
	f.Add([]byte{})                                           // empty
	f.Add([]byte{0x00})                                       // too short
	f.Add([]byte{0x00, 0x00, 0x00, 0x00, 0x00, 0x00})         // all zeros
	f.Add([]byte{0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF})         // all ones
	f.Add([]byte{0x80, 0x00, 0x00, 0x00, 0x00, 0x00})         // min int16
	f.Add([]byte{0x7F, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF})         // max int16

	f.Fuzz(func(t *testing.T, data []byte) {
		// Should never panic
		_, _ = DecodeEnvSensor(data)
	})
}

// FuzzDecodeEncode tests decode/encode roundtrip
func FuzzDecodeEncode(f *testing.F) {
	// Seed with valid payloads
	f.Add([]byte{0x09, 0x29, 0x82, 0x0C, 0xE4, 0x00})
	f.Add([]byte{0xFE, 0x0C, 0x14, 0x0B, 0xB8, 0x01})
	f.Add([]byte{0x00, 0x00, 0x00, 0x00, 0x00, 0x00})
	f.Add([]byte{0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF})

	f.Fuzz(func(t *testing.T, data []byte) {
		decoded, err := DecodeEnvSensor(data)
		if err != nil {
			return // Short payloads are expected to fail
		}

		// Re-encode
		encoded := EncodeEnvSensor(decoded)

		// Decode again
		decoded2, err := DecodeEnvSensor(encoded)
		if err != nil {
			t.Errorf("roundtrip decode failed: %v", err)
			return
		}

		// Values should match (within float tolerance)
		const tolerance = 0.01
		if math.Abs(decoded.Temperature-decoded2.Temperature) > tolerance {
			t.Errorf("temperature mismatch: %f vs %f", decoded.Temperature, decoded2.Temperature)
		}
		if math.Abs(decoded.Humidity-decoded2.Humidity) > tolerance {
			t.Errorf("humidity mismatch: %f vs %f", decoded.Humidity, decoded2.Humidity)
		}
		if decoded.BatteryMV != decoded2.BatteryMV {
			t.Errorf("battery_mv mismatch: %d vs %d", decoded.BatteryMV, decoded2.BatteryMV)
		}
		if decoded.Status != decoded2.Status {
			t.Errorf("status mismatch: %d vs %d", decoded.Status, decoded2.Status)
		}
	})
}

// FuzzSchemaInterpreter tests the generic schema interpreter concept
func FuzzSchemaInterpreter(f *testing.F) {
	// This would fuzz against a generic interpreter
	// For now, just test that various byte patterns don't cause issues

	f.Add([]byte{0x01, 0x02, 0x03})
	f.Add([]byte{0xFF, 0xFE, 0xFD})
	f.Add(make([]byte, 256)) // Long payload

	f.Fuzz(func(t *testing.T, data []byte) {
		// Interpret as various field types without panicking

		// u8
		if len(data) >= 1 {
			_ = data[0]
		}

		// u16 big-endian
		if len(data) >= 2 {
			_ = binary.BigEndian.Uint16(data[0:2])
		}

		// s16 big-endian
		if len(data) >= 2 {
			_ = int16(binary.BigEndian.Uint16(data[0:2]))
		}

		// u32 big-endian
		if len(data) >= 4 {
			_ = binary.BigEndian.Uint32(data[0:4])
		}

		// f32 big-endian
		if len(data) >= 4 {
			bits := binary.BigEndian.Uint32(data[0:4])
			_ = math.Float32frombits(bits)
		}
	})
}

// Unit tests for known values
func TestDecodeKnownValues(t *testing.T) {
	tests := []struct {
		name        string
		payload     []byte
		temperature float64
		humidity    float64
		batteryMV   uint16
		status      uint8
	}{
		{
			name:        "normal_room",
			payload:     []byte{0x09, 0x29, 0x82, 0x0C, 0xE4, 0x00},
			temperature: 23.45,
			humidity:    65.0,
			batteryMV:   3300,
			status:      0,
		},
		{
			name:        "cold_dry",
			payload:     []byte{0xFE, 0x0C, 0x14, 0x0B, 0xB8, 0x01},
			temperature: -5.0,
			humidity:    10.0,
			batteryMV:   3000,
			status:      1,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s, err := DecodeEnvSensor(tt.payload)
			if err != nil {
				t.Fatalf("decode failed: %v", err)
			}

			const tolerance = 0.01
			if math.Abs(s.Temperature-tt.temperature) > tolerance {
				t.Errorf("temperature: got %f, want %f", s.Temperature, tt.temperature)
			}
			if math.Abs(s.Humidity-tt.humidity) > tolerance {
				t.Errorf("humidity: got %f, want %f", s.Humidity, tt.humidity)
			}
			if s.BatteryMV != tt.batteryMV {
				t.Errorf("battery_mv: got %d, want %d", s.BatteryMV, tt.batteryMV)
			}
			if s.Status != tt.status {
				t.Errorf("status: got %d, want %d", s.Status, tt.status)
			}
		})
	}
}
