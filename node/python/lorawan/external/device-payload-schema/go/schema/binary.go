// Copyright (c) 2024-2026 Multitech Systems, Inc.
// Author: Jason Reiss
// SPDX-License-Identifier: MIT

package schema

import (
	"encoding/binary"
	"fmt"
)

// Binary schema format constants
const (
	BinaryVersion1    = 0x01
	BinaryVersion2    = 0x02
	BinaryMagic       = "PS" // Magic header for validation
)

// Field type codes for binary format
const (
	BinTypeUnsigned  = 0x0
	BinTypeSigned    = 0x1
	BinTypeFloat     = 0x2
	BinTypeBytes     = 0x3
	BinTypeBool      = 0x4
	BinTypeEnum      = 0x5
	BinTypeBitfield  = 0x6
	BinTypeStructural = 0x7
)

// BinaryField represents a field in binary schema format (4 bytes)
type BinaryField struct {
	TypeByte   byte   // Type (4 bits) + Size (4 bits)
	MultExp    int8   // Multiplier exponent (-128 to 127)
	SemanticID uint16 // IPSO semantic ID or 0
}

// BinarySchema represents a binary-encoded schema
type BinarySchema struct {
	Version    byte
	Flags      byte
	FieldCount int
	Fields     []BinaryField
	Raw        []byte // Original binary data
}

// ParseBinarySchema parses a binary schema format into a Schema struct.
// Format v1: header(2) + fields(4*n)
// Header: version(1) + field_count(1)
// Field:  type_byte(1) + mult_exp(1) + semantic_id(2)
func ParseBinarySchema(data []byte) (*Schema, error) {
	if len(data) < 2 {
		return nil, fmt.Errorf("binary schema too short")
	}

	version := data[0]
	if version != BinaryVersion1 && version != BinaryVersion2 {
		return nil, fmt.Errorf("unsupported binary schema version: %d", version)
	}

	fieldCount := int(data[1])
	expectedLen := 2 + fieldCount*4
	if len(data) < expectedLen {
		return nil, fmt.Errorf("binary schema truncated: expected %d bytes, got %d", expectedLen, len(data))
	}

	schema := &Schema{
		Endian: "big", // Default for binary schemas
		Fields: make([]Field, 0, fieldCount),
	}

	pos := 2
	for i := 0; i < fieldCount; i++ {
		typeByte := data[pos]
		multExp := int8(data[pos+1])
		semanticID := binary.LittleEndian.Uint16(data[pos+2 : pos+4])
		pos += 4

		typeCode := typeByte >> 4
		sizeCode := typeByte & 0x0F

		field := Field{
			Name:   fmt.Sprintf("field_%d", i),
			Length: decodeSizeCode(sizeCode),
		}

		// Set type based on type code
		switch typeCode {
		case BinTypeUnsigned:
			field.Type = sizeToUintType(field.Length)
		case BinTypeSigned:
			field.Type = sizeToSintType(field.Length)
		case BinTypeFloat:
			field.Type = sizeToFloatType(field.Length)
		case BinTypeBool:
			field.Type = TypeBool
		case BinTypeBytes:
			field.Type = TypeBytes
		default:
			field.Type = TypeU8
		}

		// Apply multiplier from exponent
		if multExp != 0 {
			mult := expToMult(multExp)
			field.Mult = &mult
		}

		// Store semantic ID in field (for future use)
		_ = semanticID

		schema.Fields = append(schema.Fields, field)
	}

	return schema, nil
}

// EncodeBinarySchema encodes a Schema to binary format
func EncodeBinarySchema(schema *Schema) ([]byte, error) {
	fieldCount := len(schema.Fields)
	if fieldCount > 255 {
		return nil, fmt.Errorf("too many fields for binary schema: %d (max 255)", fieldCount)
	}

	data := make([]byte, 2+fieldCount*4)
	data[0] = BinaryVersion1
	data[1] = byte(fieldCount)

	pos := 2
	for _, field := range schema.Fields {
		typeCode, sizeCode := fieldToBinaryCodes(field)
		data[pos] = (typeCode << 4) | sizeCode
		data[pos+1] = byte(multToExp(field.Mult))
		binary.LittleEndian.PutUint16(data[pos+2:pos+4], 0) // semantic ID placeholder
		pos += 4
	}

	return data, nil
}

// Helper functions

func decodeSizeCode(code byte) int {
	sizes := []int{1, 2, 3, 4, 8, 16, 32, 64}
	if int(code) < len(sizes) {
		return sizes[code]
	}
	return 1
}

func sizeToUintType(size int) FieldType {
	switch size {
	case 1:
		return TypeU8
	case 2:
		return TypeU16
	case 4:
		return TypeU32
	case 8:
		return TypeU64
	default:
		return TypeU8
	}
}

func sizeToSintType(size int) FieldType {
	switch size {
	case 1:
		return TypeS8
	case 2:
		return TypeS16
	case 4:
		return TypeS32
	case 8:
		return TypeS64
	default:
		return TypeS8
	}
}

func sizeToFloatType(size int) FieldType {
	switch size {
	case 2:
		return TypeF16
	case 4:
		return TypeF32
	case 8:
		return TypeF64
	default:
		return TypeF32
	}
}

func expToMult(exp int8) float64 {
	if exp == 0 {
		return 1.0
	}
	result := 1.0
	if exp > 0 {
		for i := int8(0); i < exp; i++ {
			result *= 10
		}
	} else {
		for i := int8(0); i > exp; i-- {
			result /= 10
		}
	}
	return result
}

func multToExp(mult *float64) int8 {
	if mult == nil || *mult == 1.0 {
		return 0
	}
	m := *mult
	exp := int8(0)
	if m >= 1 {
		for m >= 10 && exp < 127 {
			m /= 10
			exp++
		}
	} else {
		for m < 1 && exp > -128 {
			m *= 10
			exp--
		}
	}
	return exp
}

func fieldToBinaryCodes(field Field) (typeCode byte, sizeCode byte) {
	length := field.Length
	if length == 0 {
		length = inferLengthFromType(field.Type)
	}

	// Size code
	switch length {
	case 1:
		sizeCode = 0
	case 2:
		sizeCode = 1
	case 3:
		sizeCode = 2
	case 4:
		sizeCode = 3
	case 8:
		sizeCode = 4
	default:
		sizeCode = 0
	}

	// Type code
	switch field.Type {
	case TypeU8, TypeU16, TypeU32, TypeU64, TypeUInt, TypeByte:
		typeCode = BinTypeUnsigned
	case TypeS8, TypeS16, TypeS32, TypeS64, TypeSInt, TypeI8, TypeI16, TypeI32, TypeI64:
		typeCode = BinTypeSigned
	case TypeF16, TypeF32, TypeF64, TypeFloat16, TypeFloat32, TypeFloat64:
		typeCode = BinTypeFloat
	case TypeBool:
		typeCode = BinTypeBool
	case TypeBytes, TypeBytesLower, TypeHex:
		typeCode = BinTypeBytes
	default:
		typeCode = BinTypeUnsigned
	}

	return
}
