// Package schema_native provides Go bindings for the C schema interpreter.
//
// This uses CGO to call the high-performance C implementation directly,
// providing ~32M msg/s decode throughput vs ~2M msg/s for pure Go.
//
// Usage:
//
//	schema, err := schema_native.FromBinary(binaryData)
//	if err != nil {
//	    log.Fatal(err)
//	}
//	defer schema.Free()
//
//	result, err := schema.Decode(payload)
//	if err != nil {
//	    log.Fatal(err)
//	}
//	fmt.Println(result) // map[temperature:25.5 humidity:60]
//
// Build requirements:
//   - CGO enabled (CGO_ENABLED=1)
//   - C compiler (gcc/clang)
//   - libschema.so in library path or linked statically
package schema_native

/*
#cgo CFLAGS: -I${SRCDIR}/../../include -I${SRCDIR}/../c
#cgo LDFLAGS: -L${SRCDIR}/../c -lschema

#include <stdlib.h>
#include <stdint.h>
#include "schema_ffi.h"
*/
import "C"
import (
	"fmt"
	"runtime"
	"unsafe"
)

// FieldType represents the type of a decoded field value.
type FieldType int

const (
	FieldTypeInt    FieldType = C.FIELD_VAL_INT
	FieldTypeFloat  FieldType = C.FIELD_VAL_FLOAT
	FieldTypeString FieldType = C.FIELD_VAL_STRING
	FieldTypeBool   FieldType = C.FIELD_VAL_BOOL
	FieldTypeBytes  FieldType = C.FIELD_VAL_BYTES
)

// Error codes from the C library.
const (
	ErrOK       = C.SCHEMA_OK
	ErrInvalid  = C.SCHEMA_ERR_INVALID
	ErrParse    = C.SCHEMA_ERR_PARSE
	ErrDecode   = C.SCHEMA_ERR_DECODE
	ErrMemory   = C.SCHEMA_ERR_MEMORY
	ErrOverflow = C.SCHEMA_ERR_OVERFLOW
)

// SchemaError represents an error from schema operations.
type SchemaError struct {
	Code    int
	Message string
}

func (e *SchemaError) Error() string {
	return fmt.Sprintf("schema error %d: %s", e.Code, e.Message)
}

// Schema represents a loaded schema that can decode payloads.
type Schema struct {
	handle C.schema_t_ffi
}

// FromBinary creates a Schema from binary schema data.
func FromBinary(data []byte) (*Schema, error) {
	if len(data) == 0 {
		return nil, &SchemaError{Code: ErrInvalid, Message: "empty binary data"}
	}

	ptr := (*C.uint8_t)(unsafe.Pointer(&data[0]))
	handle := C.schema_create_binary(ptr, C.size_t(len(data)))
	if handle == nil {
		return nil, &SchemaError{Code: ErrParse, Message: "failed to parse binary schema"}
	}

	s := &Schema{handle: handle}
	runtime.SetFinalizer(s, (*Schema).Free)
	return s, nil
}

// Free releases the native resources. Called automatically by finalizer,
// but can be called explicitly for deterministic cleanup.
func (s *Schema) Free() {
	if s.handle != nil {
		C.schema_free(s.handle)
		s.handle = nil
	}
}

// Name returns the schema name.
func (s *Schema) Name() string {
	if s.handle == nil {
		return ""
	}
	return C.GoString(C.schema_get_name(s.handle))
}

// FieldCount returns the number of fields in the schema.
func (s *Schema) FieldCount() int {
	if s.handle == nil {
		return 0
	}
	return int(C.schema_get_field_count(s.handle))
}

// Decode decodes a payload using the schema.
func (s *Schema) Decode(payload []byte) (map[string]interface{}, error) {
	if s.handle == nil {
		return nil, &SchemaError{Code: ErrInvalid, Message: "schema handle is nil"}
	}
	if len(payload) == 0 {
		return nil, &SchemaError{Code: ErrInvalid, Message: "empty payload"}
	}

	ptr := (*C.uint8_t)(unsafe.Pointer(&payload[0]))
	result := C.schema_decode(s.handle, ptr, C.size_t(len(payload)))
	if result == nil {
		return nil, &SchemaError{Code: ErrDecode, Message: "decode returned null"}
	}
	defer C.result_free(result)

	errCode := int(C.result_get_error(result))
	if errCode != 0 {
		errMsg := C.GoString(C.result_get_error_msg(result))
		return nil, &SchemaError{Code: errCode, Message: errMsg}
	}

	fieldCount := int(C.result_get_field_count(result))
	output := make(map[string]interface{}, fieldCount)

	for i := 0; i < fieldCount; i++ {
		name := C.GoString(C.result_get_field_name(result, C.int(i)))
		if name == "" {
			continue
		}

		fieldType := FieldType(C.result_get_field_type(result, C.int(i)))
		switch fieldType {
		case FieldTypeInt:
			output[name] = int64(C.result_get_field_int(result, C.int(i)))
		case FieldTypeFloat:
			output[name] = float64(C.result_get_field_float(result, C.int(i)))
		case FieldTypeString:
			output[name] = C.GoString(C.result_get_field_string(result, C.int(i)))
		case FieldTypeBool:
			output[name] = C.result_get_field_bool(result, C.int(i)) != 0
		default:
			output[name] = int64(C.result_get_field_int(result, C.int(i)))
		}
	}

	return output, nil
}

// DecodeJSON decodes a payload and returns JSON string directly.
// More efficient than Decode() + json.Marshal() as JSON is generated in C.
func (s *Schema) DecodeJSON(payload []byte) (string, error) {
	if s.handle == nil {
		return "", &SchemaError{Code: ErrInvalid, Message: "schema handle is nil"}
	}
	if len(payload) == 0 {
		return "", &SchemaError{Code: ErrInvalid, Message: "empty payload"}
	}

	ptr := (*C.uint8_t)(unsafe.Pointer(&payload[0]))
	result := C.schema_decode(s.handle, ptr, C.size_t(len(payload)))
	if result == nil {
		return "", &SchemaError{Code: ErrDecode, Message: "decode returned null"}
	}
	defer C.result_free(result)

	errCode := int(C.result_get_error(result))
	if errCode != 0 {
		errMsg := C.GoString(C.result_get_error_msg(result))
		return "", &SchemaError{Code: errCode, Message: errMsg}
	}

	jsonPtr := C.result_to_json(result)
	if jsonPtr == nil {
		return "", &SchemaError{Code: ErrDecode, Message: "JSON conversion failed"}
	}
	defer C.schema_free_string(jsonPtr)

	return C.GoString(jsonPtr), nil
}

// Version returns the native library version string.
func Version() string {
	return C.GoString(C.schema_version())
}
