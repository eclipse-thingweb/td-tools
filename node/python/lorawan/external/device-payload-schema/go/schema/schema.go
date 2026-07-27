// Copyright (c) 2024-2026 Multitech Systems, Inc.
// Author: Jason Reiss
// SPDX-License-Identifier: MIT

// Package schema provides a schema-based payload formatter for LoRaWAN devices.
// It implements the PayloadEncoderDecoder interface using declarative YAML/JSON schemas.
package schema

import (
	"encoding/base64"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math"
	"regexp"
	"strconv"
	"strings"

	"gopkg.in/yaml.v3"
)

// FieldType represents the type of a schema field.
type FieldType string

const (
	TypeByte    FieldType = "Byte"
	TypeUInt    FieldType = "UInt"
	TypeSInt    FieldType = "SInt"
	TypeBInt    FieldType = "BInt"
	TypeFloat16 FieldType = "Float16"
	TypeFloat32 FieldType = "Float32"
	TypeFloat64 FieldType = "Float64"
	TypeBool    FieldType = "Bool"
	TypeBits    FieldType = "Bits"
	TypeAscii   FieldType = "Ascii"
	TypeHex     FieldType = "Hex"
	TypeBase64  FieldType = "Base64"
	TypeSkip    FieldType = "Skip"
	TypeString  FieldType = "String"
	TypeNumber  FieldType = "Number"
	TypeObject  FieldType = "Object"
	TypeMatch   FieldType = "Match"
	TypeTLV     FieldType = "TLV"

	// Shorthand types (lowercase)
	TypeU8  FieldType = "u8"
	TypeU16 FieldType = "u16"
	TypeU32 FieldType = "u32"
	TypeU64 FieldType = "u64"
	TypeS8  FieldType = "s8"
	TypeS16 FieldType = "s16"
	TypeS32 FieldType = "s32"
	TypeS64 FieldType = "s64"
	TypeI8  FieldType = "i8"
	TypeI16 FieldType = "i16"
	TypeI32 FieldType = "i32"
	TypeI64 FieldType = "i64"
	TypeF16 FieldType = "f16"
	TypeF32 FieldType = "f32"
	TypeF64 FieldType = "f64"

	// 24-bit integer types
	TypeU24 FieldType = "u24"
	TypeS24 FieldType = "s24"

	// Lowercase variants
	TypeBitsLower   FieldType = "bits"
	TypeSkipLower   FieldType = "skip"
	TypeMatchLower  FieldType = "match"
	TypeObjectLower FieldType = "object"
	TypeTLVLower    FieldType = "tlv"

	// Bytes type (raw bytes with format options)
	TypeBytes      FieldType = "Bytes"
	TypeBytesLower FieldType = "bytes"

	// Enum type (maps integer values to strings)
	TypeEnum      FieldType = "Enum"
	TypeEnumLower FieldType = "enum"

	// Bool lowercase
	TypeBoolLower FieldType = "bool"

	// String/Ascii lowercase
	TypeStringLower FieldType = "string"
	TypeAsciiLower  FieldType = "ascii"

	// Repeat type (arrays)
	TypeRepeat      FieldType = "Repeat"
	TypeRepeatLower FieldType = "repeat"

	// Bitfield string (version strings)
	TypeBitfieldString FieldType = "bitfield_string"
)

// Field represents a field definition in the schema.
type Field struct {
	Name        string         `json:"name,omitempty" yaml:"name,omitempty"`
	Type        FieldType      `json:"type" yaml:"type"`
	Length      int            `json:"length,omitempty" yaml:"length,omitempty"`
	ByteOffset  int            `json:"byte_offset,omitempty" yaml:"byte_offset,omitempty"`
	BitOffset   int            `json:"bit_offset,omitempty" yaml:"bit_offset,omitempty"`
	Bits        int            `json:"bits,omitempty" yaml:"bits,omitempty"`
	Endian      string         `json:"endian,omitempty" yaml:"endian,omitempty"`
	Add         *float64       `json:"add,omitempty" yaml:"add,omitempty"`
	Mult        *float64       `json:"mult,omitempty" yaml:"mult,omitempty"`
	Div         *float64       `json:"div,omitempty" yaml:"div,omitempty"`
	ModOrder    []string       `json:"-" yaml:"-"` // YAML key order for add/mult/div
	Transform   []Transform    `json:"transform,omitempty" yaml:"transform,omitempty"`
	Modifiers   []Transform    `json:"modifiers,omitempty" yaml:"modifiers,omitempty"` // Legacy support
	Lookup      map[int]string `json:"lookup,omitempty" yaml:"lookup,omitempty"`
	LookupArray []any          `json:"lookup_array,omitempty" yaml:"lookup_array,omitempty"`
	Var         string         `json:"var,omitempty" yaml:"var,omitempty"`
	Value       any            `json:"value,omitempty" yaml:"value,omitempty"`
	Fields      []Field        `json:"fields,omitempty" yaml:"fields,omitempty"`
	On          string         `json:"on,omitempty" yaml:"on,omitempty"`
	Cases       []Case         `json:"cases,omitempty" yaml:"cases,omitempty"`
	// Repeat/array fields
	Count      any    `json:"count,omitempty" yaml:"count,omitempty"`           // Number of iterations or variable reference
	ByteLength any    `json:"byte_length,omitempty" yaml:"byte_length,omitempty"` // Byte-based repeat length
	Until      string `json:"until,omitempty" yaml:"until,omitempty"`           // "end" for until end of payload
	Max        int    `json:"max,omitempty" yaml:"max,omitempty"`               // Maximum iterations (safety limit)
	Min        int    `json:"min,omitempty" yaml:"min,omitempty"`               // Minimum required iterations
	// Bytes field options
	Format    string `json:"format,omitempty" yaml:"format,omitempty"`       // hex, hex:upper, base64, array
	Separator string `json:"separator,omitempty" yaml:"separator,omitempty"` // Byte separator for hex output
	// Enum field options
	Base       string         `json:"base,omitempty" yaml:"base,omitempty"`     // Base type (u8, u16, etc.)
	Values     map[int]string `json:"values,omitempty" yaml:"values,omitempty"` // Enum value mapping
	// Bool field options
	Bit     int  `json:"bit,omitempty" yaml:"bit,omitempty"`         // Bit position for bool extraction
	Consume int  `json:"consume,omitempty" yaml:"consume,omitempty"` // Bytes to consume after reading
	// Byte group (inline grouped bitfields)
	ByteGroup []Field `json:"byte_group,omitempty" yaml:"byte_group,omitempty"`
	Size      int     `json:"size,omitempty" yaml:"size,omitempty"` // Size of byte group in bytes
	// $ref for definitions
	Ref2 string `json:"$ref,omitempty" yaml:"$ref,omitempty"` // Reference to definition
	// TLV-specific fields
	TagSize    int                `json:"tag_size,omitempty" yaml:"tag_size,omitempty"`
	LengthSize int                `json:"length_size,omitempty" yaml:"length_size,omitempty"`
	TagFields  []Field            `json:"tag_fields,omitempty" yaml:"tag_fields,omitempty"`
	TagKey     any                `json:"tag_key,omitempty" yaml:"tag_key,omitempty"`
	Merge      *bool              `json:"merge,omitempty" yaml:"merge,omitempty"`
	Unknown    string             `json:"unknown,omitempty" yaml:"unknown,omitempty"`
	TLVCases   map[string][]Field `json:"-" yaml:"-"` // Populated during parsing for TLV
	// Bitfield string fields
	Parts     [][]any `json:"parts,omitempty" yaml:"parts,omitempty"`
	Delimiter string  `json:"delimiter,omitempty" yaml:"delimiter,omitempty"`
	Prefix    string  `json:"prefix,omitempty" yaml:"prefix,omitempty"`
	// Formula (can reference $field_name for computed values) - DEPRECATED
	Formula string `json:"formula,omitempty" yaml:"formula,omitempty"`
	// Semantic fields
	ValidRange []float64 `json:"valid_range,omitempty" yaml:"valid_range,omitempty"` // [min, max] bounds for quality checks
	Resolution *float64  `json:"resolution,omitempty" yaml:"resolution,omitempty"`   // Minimum detectable change
	UNECE      string    `json:"unece,omitempty" yaml:"unece,omitempty"`             // UNECE Rec 20 unit code
	// Phase 2: Declarative computed values
	Ref        string     `json:"ref,omitempty" yaml:"ref,omitempty"`               // Reference to another field ($field_name)
	Polynomial []float64  `json:"polynomial,omitempty" yaml:"polynomial,omitempty"` // Coefficients [a_n, ..., a_0] for Horner's method
	Compute    *ComputeDef `json:"-" yaml:"-"`                                       // Binary operation (div, mul, add, sub)
	Guard      *GuardDef   `json:"-" yaml:"-"`                                       // Conditional evaluation
	// Flagged construct (inline struct)
	Flagged *FlaggedDef `json:"-" yaml:"-"`
	// TLV inline (for port-based schemas where tlv: is a nested key)
	TLVInline *Field `json:"-" yaml:"-"`
	// Match inline (for Option B syntax: `- match: { field: $var, cases: {...} }`)
	MatchInline *Field `json:"-" yaml:"-"`
}

// Transform represents a single transformation stage.
type Transform struct {
	Add  *float64 `json:"add,omitempty" yaml:"add,omitempty"`
	Sub  *float64 `json:"sub,omitempty" yaml:"sub,omitempty"`
	Mult *float64 `json:"mult,omitempty" yaml:"mult,omitempty"`
	Div  *float64 `json:"div,omitempty" yaml:"div,omitempty"`
}

// Case represents a match case in conditional parsing.
type Case struct {
	Case    any     `json:"case,omitempty" yaml:"case,omitempty"`
	Match   any     `json:"match,omitempty" yaml:"match,omitempty"` // Legacy support
	Default bool    `json:"default,omitempty" yaml:"default,omitempty"`
	Fields  []Field `json:"fields,omitempty" yaml:"fields,omitempty"`
}

// ComputeDef represents a binary arithmetic operation.
type ComputeDef struct {
	Op string `json:"op" yaml:"op"` // div, mul, add, sub
	A  string `json:"a" yaml:"a"`   // First operand ($field or literal)
	B  string `json:"b" yaml:"b"`   // Second operand ($field or literal)
}

// GuardCondition represents a single guard condition.
type GuardCondition struct {
	Field string   `json:"field" yaml:"field"` // Field reference ($field_name)
	Gt    *float64 `json:"gt,omitempty" yaml:"gt,omitempty"`
	Gte   *float64 `json:"gte,omitempty" yaml:"gte,omitempty"`
	Lt    *float64 `json:"lt,omitempty" yaml:"lt,omitempty"`
	Lte   *float64 `json:"lte,omitempty" yaml:"lte,omitempty"`
	Eq    *float64 `json:"eq,omitempty" yaml:"eq,omitempty"`
}

// GuardDef represents conditional evaluation with fallback.
type GuardDef struct {
	When []GuardCondition `json:"when" yaml:"when"`
	Else float64          `json:"else" yaml:"else"`
}

// FlaggedGroup represents a single bitmask-gated field group.
type FlaggedGroup struct {
	Bit    int     `json:"bit" yaml:"bit"`
	Fields []Field `json:"fields" yaml:"fields"`
}

// FlaggedDef represents a flagged/bitmask field presence construct.
type FlaggedDef struct {
	Field  string         `json:"field" yaml:"field"`
	Groups []FlaggedGroup `json:"groups" yaml:"groups"`
}

// PortDef represents a port-specific schema definition.
type PortDef struct {
	Direction   string  `json:"direction,omitempty" yaml:"direction,omitempty"`
	Description string  `json:"description,omitempty" yaml:"description,omitempty"`
	Fields      []Field `json:"fields,omitempty" yaml:"fields,omitempty"`
}

// DefinitionDef represents a reusable field definition.
type DefinitionDef struct {
	Fields []Field `json:"fields,omitempty" yaml:"fields,omitempty"`
}

// Schema represents a payload schema definition.
type Schema struct {
	Name        string                    `json:"name,omitempty" yaml:"name,omitempty"`
	Version     int                       `json:"version,omitempty" yaml:"version,omitempty"`
	Description string                    `json:"description,omitempty" yaml:"description,omitempty"`
	Endian      string                    `json:"endian,omitempty" yaml:"endian,omitempty"`
	Header      []Field                   `json:"header,omitempty" yaml:"header,omitempty"`
	Fields      []Field                   `json:"fields,omitempty" yaml:"fields,omitempty"`
	Ports       map[string]*PortDef       `json:"-" yaml:"-"` // Port-based schema selection
	Definitions map[string]*DefinitionDef `json:"-" yaml:"-"` // Reusable definitions
}

// DecodeContext maintains state during decoding.
type DecodeContext struct {
	Data      []byte
	Offset    int
	Endian    string
	Variables map[string]any
	Quality   map[string]string   // Quality status for fields with valid_range
	Warnings  []string            // Quality warnings
}

// EncodeContext maintains state during encoding.
type EncodeContext struct {
	Buffer    []byte
	Endian    string
	Variables map[string]any
}

// NewEncodeContext creates a new encode context.
func NewEncodeContext(endian string) *EncodeContext {
	if endian == "" {
		endian = "big"
	}
	return &EncodeContext{
		Buffer:    make([]byte, 0),
		Endian:    endian,
		Variables: make(map[string]any),
	}
}

// Write appends bytes to the buffer.
func (ctx *EncodeContext) Write(data []byte) {
	ctx.Buffer = append(ctx.Buffer, data...)
}

// inferLengthFromType returns the byte length for shorthand types like u8, s16, etc.
func inferLengthFromType(t FieldType) int {
	switch t {
	case TypeU8, TypeS8, TypeI8:
		return 1
	case TypeU16, TypeS16, TypeI16:
		return 2
	case TypeU24, TypeS24:
		return 3
	case TypeU32, TypeS32, TypeI32, TypeF32:
		return 4
	case TypeU64, TypeS64, TypeI64, TypeF64:
		return 8
	case TypeF16:
		return 2
	default:
		return 1
	}
}

// NewDecodeContext creates a new decode context.
func NewDecodeContext(data []byte, endian string) *DecodeContext {
	if endian == "" {
		endian = "big"
	}
	return &DecodeContext{
		Data:      data,
		Offset:    0,
		Endian:    endian,
		Variables: make(map[string]any),
		Quality:   make(map[string]string),
		Warnings:  []string{},
	}
}

// checkValidRange checks if value is within valid_range and updates quality.
// Returns "good" if in range (or no range defined), "out_of_range" otherwise.
func (ctx *DecodeContext) checkValidRange(value any, field Field) string {
	if len(field.ValidRange) < 2 {
		return "good"
	}
	
	numVal, ok := toFloat64(value)
	if !ok {
		return "good"
	}
	
	minVal, maxVal := field.ValidRange[0], field.ValidRange[1]
	
	if numVal < minVal || numVal > maxVal {
		warning := fmt.Sprintf("%s: value %v outside valid range [%v, %v]",
			field.Name, numVal, minVal, maxVal)
		ctx.Warnings = append(ctx.Warnings, warning)
		ctx.Quality[field.Name] = "out_of_range"
		return "out_of_range"
	}
	
	ctx.Quality[field.Name] = "good"
	return "good"
}

// Remaining returns the number of bytes remaining.
func (ctx *DecodeContext) Remaining() int {
	return len(ctx.Data) - ctx.Offset
}

// Read reads n bytes and advances the offset.
func (ctx *DecodeContext) Read(n int) ([]byte, error) {
	if ctx.Offset+n > len(ctx.Data) {
		return nil, fmt.Errorf("buffer underflow: need %d bytes at offset %d, but only %d remaining",
			n, ctx.Offset, ctx.Remaining())
	}
	result := ctx.Data[ctx.Offset : ctx.Offset+n]
	ctx.Offset += n
	return result, nil
}

// Peek reads n bytes without advancing the offset.
func (ctx *DecodeContext) Peek(n int, offset int) ([]byte, error) {
	pos := ctx.Offset + offset
	if pos+n > len(ctx.Data) {
		return nil, fmt.Errorf("buffer underflow at peek offset %d", pos)
	}
	return ctx.Data[pos : pos+n], nil
}

// extractModOrder extracts the YAML key order of modifier keys (add, mult, div)
// from a yaml.Node mapping node.
func extractModOrder(node *yaml.Node) []string {
	if node == nil || node.Kind != yaml.MappingNode {
		return nil
	}
	var order []string
	for i := 0; i < len(node.Content)-1; i += 2 {
		key := node.Content[i].Value
		if key == "add" || key == "mult" || key == "div" {
			order = append(order, key)
		}
	}
	return order
}

// findFieldNodes returns a mapping from field index to its yaml.Node for a fields sequence.
func findFieldNodes(root *yaml.Node, path ...string) []*yaml.Node {
	node := root
	for _, key := range path {
		if node == nil {
			return nil
		}
		if node.Kind == yaml.DocumentNode && len(node.Content) > 0 {
			node = node.Content[0]
		}
		if node.Kind != yaml.MappingNode {
			return nil
		}
		found := false
		for i := 0; i < len(node.Content)-1; i += 2 {
			if node.Content[i].Value == key {
				node = node.Content[i+1]
				found = true
				break
			}
		}
		if !found {
			return nil
		}
	}
	if node.Kind != yaml.SequenceNode {
		return nil
	}
	return node.Content
}

// ParseSchema parses a schema from YAML or JSON string.
func ParseSchema(data string) (*Schema, error) {
	// First parse raw to handle TLV cases (which use map instead of array)
	var raw map[string]any
	if err := yaml.Unmarshal([]byte(data), &raw); err != nil {
		if err := json.Unmarshal([]byte(data), &raw); err != nil {
			return nil, fmt.Errorf("failed to parse schema: %w", err)
		}
	}

	// Also parse into yaml.Node tree to extract YAML key ordering for modifiers
	var rootNode yaml.Node
	_ = yaml.Unmarshal([]byte(data), &rootNode)
	fieldNodes := findFieldNodes(&rootNode, "fields")

	schema := &Schema{}
	
	if name, ok := raw["name"].(string); ok {
		schema.Name = name
	}
	if version, ok := raw["version"].(int); ok {
		schema.Version = version
	}
	if endian, ok := raw["endian"].(string); ok {
		schema.Endian = endian
	}
	if schema.Endian == "" {
		schema.Endian = "big"
	}

	// Parse definitions
	if defsRaw, ok := raw["definitions"].(map[string]any); ok {
		schema.Definitions = make(map[string]*DefinitionDef)
		for defName, defVal := range defsRaw {
			if defMap, ok := defVal.(map[string]any); ok {
				dd := &DefinitionDef{}
				if defFields, ok := defMap["fields"].([]any); ok {
					dd.Fields = parseFieldsRaw(defFields)
				}
				schema.Definitions[defName] = dd
			}
		}
	}
	// Handle map[any]any from YAML
	if defsRaw, ok := raw["definitions"].(map[any]any); ok {
		schema.Definitions = make(map[string]*DefinitionDef)
		for defName, defVal := range defsRaw {
			name := fmt.Sprintf("%v", defName)
			if defMap, ok := defVal.(map[string]any); ok {
				dd := &DefinitionDef{}
				if defFields, ok := defMap["fields"].([]any); ok {
					dd.Fields = parseFieldsRaw(defFields)
				}
				schema.Definitions[name] = dd
			}
			if defMap, ok := defVal.(map[any]any); ok {
				dd := &DefinitionDef{}
				if defFields, ok := defMap["fields"].([]any); ok {
					dd.Fields = parseFieldsRaw(defFields)
				}
				schema.Definitions[name] = dd
			}
		}
	}

	// Parse fields
	if fieldsRaw, ok := raw["fields"].([]any); ok {
		schema.Fields = parseFieldsRawWithNodes(fieldsRaw, fieldNodes)
	}

	// Parse ports (port-based schema selection)
	if portsRaw, ok := raw["ports"].(map[string]any); ok {
		schema.Ports = make(map[string]*PortDef)
		for portKey, portVal := range portsRaw {
			if portMap, ok := portVal.(map[string]any); ok {
				pd := &PortDef{}
				if dir, ok := portMap["direction"].(string); ok {
					pd.Direction = dir
				}
				if desc, ok := portMap["description"].(string); ok {
					pd.Description = desc
				}
				if pFields, ok := portMap["fields"].([]any); ok {
					pd.Fields = parseFieldsRaw(pFields)
				}
				schema.Ports[portKey] = pd
			}
		}
	}
	// YAML may parse numeric port keys as int
	if portsRaw, ok := raw["ports"].(map[any]any); ok {
		schema.Ports = make(map[string]*PortDef)
		for portKey, portVal := range portsRaw {
			key := fmt.Sprintf("%v", portKey)
			if portMap, ok := portVal.(map[string]any); ok {
				pd := &PortDef{}
				if dir, ok := portMap["direction"].(string); ok {
					pd.Direction = dir
				}
				if desc, ok := portMap["description"].(string); ok {
					pd.Description = desc
				}
				if pFields, ok := portMap["fields"].([]any); ok {
					pd.Fields = parseFieldsRaw(pFields)
				}
				schema.Ports[key] = pd
			}
			if portMap, ok := portVal.(map[any]any); ok {
				pd := &PortDef{}
				if dir, ok := portMap["direction"].(string); ok {
					pd.Direction = dir
				}
				if desc, ok := portMap["description"].(string); ok {
					pd.Description = desc
				}
				if pFields, ok := portMap["fields"].([]any); ok {
					pd.Fields = parseFieldsRaw(pFields)
				}
				schema.Ports[key] = pd
			}
		}
	}

	return schema, nil
}

func parseFieldsRaw(fieldsRaw []any) []Field {
	return parseFieldsRawWithNodes(fieldsRaw, nil)
}

func parseFieldsRawWithNodes(fieldsRaw []any, nodes []*yaml.Node) []Field {
	var fields []Field
	for i, fr := range fieldsRaw {
		if fm, ok := fr.(map[string]any); ok {
			var node *yaml.Node
			if i < len(nodes) {
				node = nodes[i]
			}
			fields = append(fields, parseFieldMap(fm, node))
		}
	}
	return fields
}

func parseFieldMap(fm map[string]any, node *yaml.Node) Field {
	f := Field{}
	
	if name, ok := fm["name"].(string); ok {
		f.Name = name
	}
	if typ, ok := fm["type"].(string); ok {
		f.Type = FieldType(typ)
	}
	if length, ok := fm["length"].(int); ok {
		f.Length = length
	}
	if length, ok := fm["length"].(float64); ok {
		f.Length = int(length)
	}
	if endian, ok := fm["endian"].(string); ok {
		f.Endian = endian
	}
	// Handle modifiers - could be float64 or int
	if mult, ok := fm["mult"].(float64); ok {
		f.Mult = &mult
	} else if mult, ok := fm["mult"].(int); ok {
		m := float64(mult)
		f.Mult = &m
	}
	if div, ok := fm["div"].(float64); ok {
		f.Div = &div
	} else if div, ok := fm["div"].(int); ok {
		d := float64(div)
		f.Div = &d
	}
	if add, ok := fm["add"].(float64); ok {
		f.Add = &add
	} else if add, ok := fm["add"].(int); ok {
		a := float64(add)
		f.Add = &a
	}
	// Extract modifier key order from YAML node
	f.ModOrder = extractModOrder(node)

	// Parse transform array
	if transformRaw, ok := fm["transform"].([]any); ok {
		for _, tRaw := range transformRaw {
			if tm, ok := tRaw.(map[string]any); ok {
				t := Transform{}
				if add, ok := tm["add"].(float64); ok {
					t.Add = &add
				} else if add, ok := tm["add"].(int); ok {
					a := float64(add)
					t.Add = &a
				}
				if sub, ok := tm["sub"].(float64); ok {
					t.Sub = &sub
				} else if sub, ok := tm["sub"].(int); ok {
					s := float64(sub)
					t.Sub = &s
				}
				if mult, ok := tm["mult"].(float64); ok {
					t.Mult = &mult
				} else if mult, ok := tm["mult"].(int); ok {
					m := float64(mult)
					t.Mult = &m
				}
				if div, ok := tm["div"].(float64); ok {
					t.Div = &div
				} else if div, ok := tm["div"].(int); ok {
					d := float64(div)
					t.Div = &d
				}
				f.Transform = append(f.Transform, t)
			}
		}
	}

	// Parse modifiers array (legacy)
	if modifiersRaw, ok := fm["modifiers"].([]any); ok {
		for _, mRaw := range modifiersRaw {
			if mm, ok := mRaw.(map[string]any); ok {
				t := Transform{}
				if add, ok := mm["add"].(float64); ok {
					t.Add = &add
				} else if add, ok := mm["add"].(int); ok {
					a := float64(add)
					t.Add = &a
				}
				if mult, ok := mm["mult"].(float64); ok {
					t.Mult = &mult
				} else if mult, ok := mm["mult"].(int); ok {
					m := float64(mult)
					t.Mult = &m
				}
				if div, ok := mm["div"].(float64); ok {
					t.Div = &div
				} else if div, ok := mm["div"].(int); ok {
					d := float64(div)
					t.Div = &d
				}
				f.Modifiers = append(f.Modifiers, t)
			}
		}
	}

	if varName, ok := fm["var"].(string); ok {
		f.Var = varName
	}
	if on, ok := fm["on"].(string); ok {
		f.On = on
	}
	
	// Lookup table - handle both string and int keys
	if lookup, ok := fm["lookup"].(map[string]any); ok {
		f.Lookup = make(map[int]string)
		for k, v := range lookup {
			if key, err := strconv.Atoi(k); err == nil {
				if str, ok := v.(string); ok {
					f.Lookup[key] = str
				}
			}
		}
	}
	// YAML may parse numeric keys as int
	if lookup, ok := fm["lookup"].(map[int]any); ok {
		f.Lookup = make(map[int]string)
		for k, v := range lookup {
			if str, ok := v.(string); ok {
				f.Lookup[k] = str
			}
		}
	}
	// Handle map[any]any from YAML
	if lookup, ok := fm["lookup"].(map[any]any); ok {
		f.Lookup = make(map[int]string)
		for k, v := range lookup {
			var key int
			switch kv := k.(type) {
			case int:
				key = kv
			case float64:
				key = int(kv)
			case string:
				key, _ = strconv.Atoi(kv)
			}
			if str, ok := v.(string); ok {
				f.Lookup[key] = str
			}
		}
	}
	
	// Nested fields (for Object type)
	if fieldsRaw, ok := fm["fields"].([]any); ok {
		f.Fields = parseFieldsRaw(fieldsRaw)
	}
	
	// Match cases (array format)
	if casesRaw, ok := fm["cases"].([]any); ok {
		for _, cr := range casesRaw {
			if cm, ok := cr.(map[string]any); ok {
				c := Case{}
				c.Case = cm["case"]
				if c.Case == nil {
					c.Case = cm["match"]
				}
				if def, ok := cm["default"].(bool); ok {
					c.Default = def
				}
				if caseFieldsRaw, ok := cm["fields"].([]any); ok {
					c.Fields = parseFieldsRaw(caseFieldsRaw)
				}
				f.Cases = append(f.Cases, c)
			}
		}
	}
	
	// TLV-specific fields
	if tagSize, ok := fm["tag_size"].(int); ok {
		f.TagSize = tagSize
	}
	if tagSize, ok := fm["tag_size"].(float64); ok {
		f.TagSize = int(tagSize)
	}
	if lengthSize, ok := fm["length_size"].(int); ok {
		f.LengthSize = lengthSize
	}
	if lengthSize, ok := fm["length_size"].(float64); ok {
		f.LengthSize = int(lengthSize)
	}
	if tagFieldsRaw, ok := fm["tag_fields"].([]any); ok {
		f.TagFields = parseFieldsRaw(tagFieldsRaw)
	}
	if tagKey, ok := fm["tag_key"]; ok {
		f.TagKey = tagKey
	}
	if merge, ok := fm["merge"].(bool); ok {
		f.Merge = &merge
	}
	if unknown, ok := fm["unknown"].(string); ok {
		f.Unknown = unknown
	}

	// Repeat/array fields
	if count, ok := fm["count"]; ok {
		f.Count = count
	}
	if byteLen, ok := fm["byte_length"]; ok {
		f.ByteLength = byteLen
	}
	if until, ok := fm["until"].(string); ok {
		f.Until = until
	}
	if max, ok := fm["max"].(int); ok {
		f.Max = max
	} else if max, ok := fm["max"].(float64); ok {
		f.Max = int(max)
	}
	if min, ok := fm["min"].(int); ok {
		f.Min = min
	} else if min, ok := fm["min"].(float64); ok {
		f.Min = int(min)
	}

	// Bytes format options
	if format, ok := fm["format"].(string); ok {
		f.Format = format
	}
	if separator, ok := fm["separator"].(string); ok {
		f.Separator = separator
	}

	// Bool field options
	if bit, ok := fm["bit"].(int); ok {
		f.Bit = bit
	} else if bit, ok := fm["bit"].(float64); ok {
		f.Bit = int(bit)
	}
	if consume, ok := fm["consume"].(int); ok {
		f.Consume = consume
	} else if consume, ok := fm["consume"].(float64); ok {
		f.Consume = int(consume)
	}

	// Enum field options
	if base, ok := fm["base"].(string); ok {
		f.Base = base
	}
	if valuesRaw, ok := fm["values"].(map[string]any); ok {
		f.Values = make(map[int]string)
		for k, v := range valuesRaw {
			if key, err := strconv.Atoi(k); err == nil {
				if str, ok := v.(string); ok {
					f.Values[key] = str
				}
			}
		}
	}
	if valuesRaw, ok := fm["values"].(map[any]any); ok {
		f.Values = make(map[int]string)
		for k, v := range valuesRaw {
			var key int
			switch kv := k.(type) {
			case int:
				key = kv
			case float64:
				key = int(kv)
			case string:
				key, _ = strconv.Atoi(kv)
			}
			if str, ok := v.(string); ok {
				f.Values[key] = str
			}
		}
	}

	// Byte group (inline grouped bitfields) - array format
	if bgRaw, ok := fm["byte_group"].([]any); ok {
		f.ByteGroup = parseFieldsRaw(bgRaw)
	}
	// Byte group - Option B format: `- byte_group: { size: N, fields: [...] }`
	if bgMap, ok := fm["byte_group"].(map[string]any); ok {
		if bgSize, ok := bgMap["size"].(int); ok {
			f.Size = bgSize
		} else if bgSize, ok := bgMap["size"].(float64); ok {
			f.Size = int(bgSize)
		}
		if bgFields, ok := bgMap["fields"].([]any); ok {
			f.ByteGroup = parseFieldsRaw(bgFields)
		}
	}
	// Also handle map[any]any for YAML parsing quirks
	if bgMap, ok := fm["byte_group"].(map[any]any); ok {
		if bgSize, ok := bgMap["size"].(int); ok {
			f.Size = bgSize
		} else if bgSize, ok := bgMap["size"].(float64); ok {
			f.Size = int(bgSize)
		}
		if bgFields, ok := bgMap["fields"].([]any); ok {
			f.ByteGroup = parseFieldsRaw(bgFields)
		}
	}
	if size, ok := fm["size"].(int); ok {
		f.Size = size
	} else if size, ok := fm["size"].(float64); ok {
		f.Size = int(size)
	}

	// $ref for definitions
	if ref2, ok := fm["$ref"].(string); ok {
		f.Ref2 = ref2
	}

	// TLV cases (map format)
	if f.Type == TypeTLV || f.Type == "tlv" {
		if casesMap, ok := fm["cases"].(map[string]any); ok {
			f.TLVCases = make(map[string][]Field)
			for key, value := range casesMap {
				if caseFieldsRaw, ok := value.([]any); ok {
					f.TLVCases[key] = parseFieldsRaw(caseFieldsRaw)
				}
			}
		}
	}

	// Bitfield string fields
	if delimiter, ok := fm["delimiter"].(string); ok {
		f.Delimiter = delimiter
	}
	if prefix, ok := fm["prefix"].(string); ok {
		f.Prefix = prefix
	}
	if partsRaw, ok := fm["parts"].([]any); ok {
		for _, pRaw := range partsRaw {
			if pArr, ok := pRaw.([]any); ok {
				f.Parts = append(f.Parts, pArr)
			}
		}
	}

	// Formula (deprecated)
	if formula, ok := fm["formula"].(string); ok {
		f.Formula = formula
	}

	// Semantic fields
	if vrRaw, ok := fm["valid_range"].([]any); ok {
		for _, v := range vrRaw {
			if vf, ok := toFloat64(v); ok {
				f.ValidRange = append(f.ValidRange, vf)
			}
		}
	}
	if res, ok := fm["resolution"].(float64); ok {
		f.Resolution = &res
	} else if res, ok := fm["resolution"].(int); ok {
		r := float64(res)
		f.Resolution = &r
	}
	if unece, ok := fm["unece"].(string); ok {
		f.UNECE = unece
	}

	// Phase 2: ref (field reference)
	if ref, ok := fm["ref"].(string); ok {
		f.Ref = ref
	}

	// Phase 2: polynomial coefficients
	if polyRaw, ok := fm["polynomial"].([]any); ok {
		for _, c := range polyRaw {
			if cf, ok := toFloat64(c); ok {
				f.Polynomial = append(f.Polynomial, cf)
			}
		}
	}

	// Phase 2: compute (binary operation)
	if compRaw, ok := fm["compute"].(map[string]any); ok {
		cd := &ComputeDef{}
		if op, ok := compRaw["op"].(string); ok {
			cd.Op = op
		}
		if a, ok := compRaw["a"].(string); ok {
			cd.A = a
		} else if a, ok := compRaw["a"].(float64); ok {
			cd.A = strconv.FormatFloat(a, 'f', -1, 64)
		} else if a, ok := compRaw["a"].(int); ok {
			cd.A = strconv.Itoa(a)
		}
		if b, ok := compRaw["b"].(string); ok {
			cd.B = b
		} else if b, ok := compRaw["b"].(float64); ok {
			cd.B = strconv.FormatFloat(b, 'f', -1, 64)
		} else if b, ok := compRaw["b"].(int); ok {
			cd.B = strconv.Itoa(b)
		}
		f.Compute = cd
	}

	// Phase 2: guard (conditional evaluation)
	if guardRaw, ok := fm["guard"].(map[string]any); ok {
		gd := &GuardDef{}
		if elseVal, ok := guardRaw["else"].(float64); ok {
			gd.Else = elseVal
		} else if elseVal, ok := guardRaw["else"].(int); ok {
			gd.Else = float64(elseVal)
		}
		if whenRaw, ok := guardRaw["when"].([]any); ok {
			for _, w := range whenRaw {
				if wm, ok := w.(map[string]any); ok {
					gc := GuardCondition{}
					if field, ok := wm["field"].(string); ok {
						gc.Field = field
					}
					if gt, ok := wm["gt"].(float64); ok {
						gc.Gt = &gt
					} else if gt, ok := wm["gt"].(int); ok {
						gtf := float64(gt)
						gc.Gt = &gtf
					}
					if gte, ok := wm["gte"].(float64); ok {
						gc.Gte = &gte
					} else if gte, ok := wm["gte"].(int); ok {
						gtef := float64(gte)
						gc.Gte = &gtef
					}
					if lt, ok := wm["lt"].(float64); ok {
						gc.Lt = &lt
					} else if lt, ok := wm["lt"].(int); ok {
						ltf := float64(lt)
						gc.Lt = &ltf
					}
					if lte, ok := wm["lte"].(float64); ok {
						gc.Lte = &lte
					} else if lte, ok := wm["lte"].(int); ok {
						ltef := float64(lte)
						gc.Lte = &ltef
					}
					if eq, ok := wm["eq"].(float64); ok {
						gc.Eq = &eq
					} else if eq, ok := wm["eq"].(int); ok {
						eqf := float64(eq)
						gc.Eq = &eqf
					}
					gd.When = append(gd.When, gc)
				}
			}
		}
		f.Guard = gd
	}

	// Flagged construct (inline)
	if flaggedRaw, ok := fm["flagged"].(map[string]any); ok {
		fd := &FlaggedDef{}
		if field, ok := flaggedRaw["field"].(string); ok {
			fd.Field = field
		}
		if groupsRaw, ok := flaggedRaw["groups"].([]any); ok {
			for _, gRaw := range groupsRaw {
				if gMap, ok := gRaw.(map[string]any); ok {
					g := FlaggedGroup{}
					if bit, ok := gMap["bit"].(int); ok {
						g.Bit = bit
					} else if bit, ok := gMap["bit"].(float64); ok {
						g.Bit = int(bit)
					}
					if gFields, ok := gMap["fields"].([]any); ok {
						g.Fields = parseFieldsRaw(gFields)
					}
					fd.Groups = append(fd.Groups, g)
				}
			}
		}
		f.Flagged = fd
	}

	// TLV inline (for port-based schemas: `- tlv: { ... }`)
	if tlvRaw, ok := fm["tlv"].(map[string]any); ok {
		tlvField := parseFieldMap(tlvRaw, nil)
		tlvField.Type = "tlv"
		f.TLVInline = &tlvField
	}

	// Match inline (for Option B syntax: `- match: { field: $var, cases: {...} }`)
	if matchRaw, ok := fm["match"].(map[string]any); ok {
		matchField := Field{Type: TypeMatch}
		if fieldRef, ok := matchRaw["field"].(string); ok {
			matchField.On = fieldRef
		}
		if casesRaw, ok := matchRaw["cases"].(map[string]any); ok {
			for caseKey, caseVal := range casesRaw {
				c := Case{}
				// Parse case key (could be int or string)
				if keyInt, err := strconv.Atoi(caseKey); err == nil {
					c.Case = keyInt
				} else {
					c.Case = caseKey
				}
				// Parse case fields
				if caseFields, ok := caseVal.([]any); ok {
					c.Fields = parseFieldsRaw(caseFields)
				}
				matchField.Cases = append(matchField.Cases, c)
			}
		}
		// Also check for cases as map[any]any (YAML parsing quirk)
		if casesRaw, ok := matchRaw["cases"].(map[any]any); ok {
			for caseKey, caseVal := range casesRaw {
				c := Case{}
				switch k := caseKey.(type) {
				case int:
					c.Case = k
				case float64:
					c.Case = int(k)
				case string:
					if keyInt, err := strconv.Atoi(k); err == nil {
						c.Case = keyInt
					} else {
						c.Case = k
					}
				default:
					c.Case = fmt.Sprintf("%v", k)
				}
				if caseFields, ok := caseVal.([]any); ok {
					c.Fields = parseFieldsRaw(caseFields)
				}
				matchField.Cases = append(matchField.Cases, c)
			}
		}
		f.MatchInline = &matchField
	}
	
	return f
}

// FieldMetadata contains semantic annotations for a field.
type FieldMetadata struct {
	Unit        string    `json:"unit,omitempty"`
	ValidRange  []float64 `json:"valid_range,omitempty"`
	Resolution  *float64  `json:"resolution,omitempty"`
	UNECE       string    `json:"unece,omitempty"`
	Description string    `json:"description,omitempty"`
	IPSO        int       `json:"ipso,omitempty"`
	SenMLUnit   string    `json:"senml_unit,omitempty"`
}

// GetFieldMetadata returns semantic metadata for schema fields.
// If fieldName is empty, returns metadata for all fields.
func (s *Schema) GetFieldMetadata(fieldName string) map[string]FieldMetadata {
	result := make(map[string]FieldMetadata)
	collectFieldMetadata(s.Fields, result)
	
	if fieldName != "" {
		if meta, ok := result[fieldName]; ok {
			return map[string]FieldMetadata{fieldName: meta}
		}
		return map[string]FieldMetadata{}
	}
	return result
}

func collectFieldMetadata(fields []Field, result map[string]FieldMetadata) {
	for _, f := range fields {
		if f.Name == "" {
			continue
		}
		
		meta := FieldMetadata{
			ValidRange:  f.ValidRange,
			Resolution:  f.Resolution,
			UNECE:       f.UNECE,
		}
		
		// These would need to be added to Field struct if needed
		// For now, just include the semantic fields
		
		if len(meta.ValidRange) > 0 || meta.Resolution != nil || meta.UNECE != "" {
			result[f.Name] = meta
		}
		
		// Recurse into nested structures
		if len(f.Fields) > 0 {
			collectFieldMetadata(f.Fields, result)
		}
		if len(f.ByteGroup) > 0 {
			collectFieldMetadata(f.ByteGroup, result)
		}
	}
}

// ResolveFields returns the field set for a given fPort.
// If the schema uses ports, selects the matching port entry.
// Otherwise returns the top-level fields.
func (s *Schema) ResolveFields(fPort int) ([]Field, error) {
	if s.Ports == nil {
		return s.Fields, nil
	}

	portKey := strconv.Itoa(fPort)
	if pd, ok := s.Ports[portKey]; ok {
		return pd.Fields, nil
	}
	if pd, ok := s.Ports["default"]; ok {
		return pd.Fields, nil
	}
	return nil, fmt.Errorf("no port definition for fPort %d and no default in schema '%s'", fPort, s.Name)
}

// DecodeWithPort decodes binary data using the schema, selecting fields by fPort.
func (s *Schema) DecodeWithPort(data []byte, fPort int) (map[string]any, error) {
	fields, err := s.ResolveFields(fPort)
	if err != nil {
		return nil, err
	}

	ctx := NewDecodeContext(data, s.Endian)
	result := make(map[string]any)

	if len(s.Header) > 0 {
		headerResult, err := decodeFields(s.Header, ctx)
		if err != nil {
			return nil, err
		}
		for k, v := range headerResult {
			result[k] = v
		}
	}

	fieldsResult, err := decodeFields(fields, ctx)
	if err != nil {
		return nil, err
	}
	for k, v := range fieldsResult {
		result[k] = v
	}

	// Add quality dict to output if any quality flags were set
	if len(ctx.Quality) > 0 {
		result["_quality"] = ctx.Quality
	}

	return result, nil
}

// Decode decodes binary data using the schema.
func (s *Schema) Decode(data []byte) (map[string]any, error) {
	ctx := NewDecodeContext(data, s.Endian)
	result := make(map[string]any)

	// Decode header fields
	if len(s.Header) > 0 {
		headerResult, err := decodeFieldsWithSchema(s.Header, ctx, s)
		if err != nil {
			return nil, err
		}
		for k, v := range headerResult {
			result[k] = v
		}
	}

	// Decode main fields
	fieldsResult, err := decodeFieldsWithSchema(s.Fields, ctx, s)
	if err != nil {
		return nil, err
	}
	for k, v := range fieldsResult {
		result[k] = v
	}

	// Add quality dict to output if any quality flags were set
	if len(ctx.Quality) > 0 {
		result["_quality"] = ctx.Quality
	}

	return result, nil
}

func decodeFields(fields []Field, ctx *DecodeContext) (map[string]any, error) {
	return decodeFieldsWithSchema(fields, ctx, nil)
}

func decodeFieldsWithSchema(fields []Field, ctx *DecodeContext, schema *Schema) (map[string]any, error) {
	result := make(map[string]any)

	for _, field := range fields {
		// $ref to definition
		if field.Ref2 != "" && schema != nil {
			refResult, err := resolveRef(field.Ref2, ctx, schema)
			if err != nil {
				return nil, err
			}
			for k, v := range refResult {
				result[k] = v
				ctx.Variables[k] = v
			}
			continue
		}

		// Byte group (inline grouped bitfields)
		if len(field.ByteGroup) > 0 {
			bgResult, err := decodeByteGroup(field, ctx)
			if err != nil {
				return nil, err
			}
			for k, v := range bgResult {
				result[k] = v
				ctx.Variables[k] = v
			}
			continue
		}

		// TLV fields merge directly into result
		if field.Type == TypeTLV || field.Type == "tlv" {
			tlvResult, err := decodeTLV(field, ctx)
			if err != nil {
				return nil, err
			}
			for k, v := range tlvResult {
				result[k] = v
			}
			continue
		}

		// TLV inline (from port-based schemas)
		if field.TLVInline != nil {
			tlvResult, err := decodeTLV(*field.TLVInline, ctx)
			if err != nil {
				return nil, err
			}
			for k, v := range tlvResult {
				result[k] = v
			}
			continue
		}

		// Flagged construct
		if field.Flagged != nil {
			flaggedResult, err := decodeFlagged(field.Flagged, ctx)
			if err != nil {
				return nil, err
			}
			for k, v := range flaggedResult {
				result[k] = v
				ctx.Variables[k] = v
			}
			continue
		}

		// Match inline (Option B syntax: `- match: { field: $var, cases: {...} }`)
		if field.MatchInline != nil {
			matchResult, err := decodeMatch(*field.MatchInline, ctx)
			if err != nil {
				return nil, err
			}
			if matchMap, ok := matchResult.(map[string]any); ok {
				for k, v := range matchMap {
					result[k] = v
					ctx.Variables[k] = v
				}
			}
			continue
		}

		value, err := decodeField(field, ctx)
		if err != nil {
			return nil, err
		}

		if value != nil && field.Name != "" {
			result[field.Name] = value
			ctx.Variables[field.Name] = value
			// Check valid_range and update quality
			if len(field.ValidRange) >= 2 {
				ctx.checkValidRange(value, field)
			}
		}
	}

	return result, nil
}

// resolveRef resolves a $ref reference to a definition.
func resolveRef(ref string, ctx *DecodeContext, schema *Schema) (map[string]any, error) {
	// Parse ref like "#/definitions/header"
	if !strings.HasPrefix(ref, "#/definitions/") {
		return nil, fmt.Errorf("unsupported $ref format: %s", ref)
	}
	defName := strings.TrimPrefix(ref, "#/definitions/")
	
	if schema.Definitions == nil {
		return nil, fmt.Errorf("no definitions in schema")
	}
	
	def, ok := schema.Definitions[defName]
	if !ok {
		return nil, fmt.Errorf("definition not found: %s", defName)
	}
	
	return decodeFieldsWithSchema(def.Fields, ctx, schema)
}

// decodeByteGroup decodes a byte group (multiple bitfields from shared bytes).
func decodeByteGroup(field Field, ctx *DecodeContext) (map[string]any, error) {
	size := field.Size
	if size == 0 {
		size = 1
	}
	
	data, err := ctx.Read(size)
	if err != nil {
		return nil, err
	}
	
	result := make(map[string]any)
	
	// Parse each subfield from the shared bytes
	for _, subfield := range field.ByteGroup {
		// Parse bit range from type like "u8[4:7]"
		typeStr := string(subfield.Type)
		bitStart, bitEnd := 0, 7
		
		if idx := strings.Index(typeStr, "["); idx >= 0 {
			rangeStr := typeStr[idx+1 : len(typeStr)-1]
			parts := strings.Split(rangeStr, ":")
			if len(parts) == 2 {
				bitStart, _ = strconv.Atoi(parts[0])
				bitEnd, _ = strconv.Atoi(parts[1])
			}
		}
		
		// Extract bits from the data
		var rawVal uint64
		for i, b := range data {
			rawVal |= uint64(b) << (8 * i)
		}
		
		bitLen := bitEnd - bitStart + 1
		mask := uint64((1 << bitLen) - 1)
		value := float64((rawVal >> bitStart) & mask)
		
		if subfield.Name != "" {
			result[subfield.Name] = value
		}
	}
	
	return result, nil
}

func decodeFlagged(fd *FlaggedDef, ctx *DecodeContext) (map[string]any, error) {
	flagsVal, ok := ctx.Variables[fd.Field]
	if !ok {
		return nil, fmt.Errorf("flagged field reference not found: %s", fd.Field)
	}
	flags, _ := toInt(flagsVal)

	result := make(map[string]any)

	for _, group := range fd.Groups {
		isPresent := (flags >> group.Bit) & 1
		if isPresent != 0 {
			groupResult, err := decodeFields(group.Fields, ctx)
			if err != nil {
				return nil, err
			}
			for k, v := range groupResult {
				result[k] = v
			}
		}
	}

	return result, nil
}

func decodeField(field Field, ctx *DecodeContext) (any, error) {
	length := field.Length
	if length == 0 {
		// Infer length from shorthand type names
		length = inferLengthFromType(field.Type)
	}
	endian := field.Endian
	if endian == "" {
		endian = ctx.Endian
	}

	var value any
	var err error

	switch field.Type {
	case TypeByte, TypeUInt, TypeU8, TypeU16, TypeU32, TypeU64, TypeU24:
		data, err := ctx.Read(length)
		if err != nil {
			return nil, err
		}
		value = decodeUint(data, endian)

	case TypeSInt, TypeS8, TypeS16, TypeS32, TypeS64, TypeI8, TypeI16, TypeI32, TypeI64, TypeS24:
		data, err := ctx.Read(length)
		if err != nil {
			return nil, err
		}
		value = decodeSint(data, endian)

	case TypeBInt:
		data, err := ctx.Read(length)
		if err != nil {
			return nil, err
		}
		value = decodeUint(data, "big")

	case TypeFloat16, TypeFloat32, TypeFloat64, TypeF16, TypeF32, TypeF64:
		size := map[FieldType]int{
			TypeFloat16: 2, TypeFloat32: 4, TypeFloat64: 8,
			TypeF16: 2, TypeF32: 4, TypeF64: 8,
		}[field.Type]
		data, err := ctx.Read(size)
		if err != nil {
			return nil, err
		}
		value, err = decodeFloat(data, size, endian)
		if err != nil {
			return nil, err
		}

	case TypeBool, TypeBoolLower:
		// Bool extracts a single bit from the current byte
		data, err := ctx.Peek(1, 0)
		if err != nil {
			return nil, err
		}
		value = decodeBits(data[0], field.Bit, 1) != 0
		// Consume bytes if specified
		if field.Consume > 0 {
			ctx.Read(field.Consume)
		}

	case TypeBits, TypeBitsLower:
		data, err := ctx.Peek(1, field.ByteOffset)
		if err != nil {
			return nil, err
		}
		bits := field.Bits
		if bits == 0 {
			bits = 1
		}
		value = decodeBits(data[0], field.BitOffset, bits)

	case TypeString, TypeStringLower:
		// If length is specified, read bytes; otherwise use static value
		if length > 0 {
			data, err := ctx.Read(length)
			if err != nil {
				return nil, err
			}
			value = strings.TrimRight(string(data), "\x00")
		} else {
			value = field.Value
		}

	case TypeAscii, TypeAsciiLower:
		data, err := ctx.Read(length)
		if err != nil {
			return nil, err
		}
		value = strings.TrimRight(string(data), "\x00")

	case TypeEnum, TypeEnumLower:
		// Enum: read base type and map to string
		baseLen := 1
		switch field.Base {
		case "u8", "s8":
			baseLen = 1
		case "u16", "s16":
			baseLen = 2
		case "u32", "s32":
			baseLen = 4
		}
		data, err := ctx.Read(baseLen)
		if err != nil {
			return nil, err
		}
		intVal := int(decodeUint(data, endian))
		if field.Values != nil {
			if str, ok := field.Values[intVal]; ok {
				value = str
			} else {
				value = intVal // Return raw value if not in enum
			}
		} else {
			value = intVal
		}

	case TypeHex:
		data, err := ctx.Read(length)
		if err != nil {
			return nil, err
		}
		value = hex.EncodeToString(data)

	case TypeSkip, TypeSkipLower:
		_, err := ctx.Read(length)
		if err != nil {
			return nil, err
		}
		return nil, nil

	case TypeBytes, TypeBytesLower:
		data, err := ctx.Read(length)
		if err != nil {
			return nil, err
		}
		value = formatBytes(data, field.Format, field.Separator)

	case TypeRepeat, TypeRepeatLower:
		value, err = decodeRepeat(field, ctx)
		if err != nil {
			return nil, err
		}

	case TypeBitfieldString:
		data, err := ctx.Read(length)
		if err != nil {
			return nil, err
		}
		intVal := decodeUint(data, endian)
		delimiter := field.Delimiter
		if delimiter == "" {
			delimiter = "."
		}
		prefix := field.Prefix
		var partStrs []string
		for _, part := range field.Parts {
			if len(part) < 2 {
				continue
			}
			bitOff, _ := toInt(part[0])
			bitLen, _ := toInt(part[1])
			format := "decimal"
			if len(part) >= 3 {
				if f, ok := part[2].(string); ok {
					format = f
				}
			}
			mask := (uint64(1) << bitLen) - 1
			raw := (intVal >> bitOff) & mask
			if format == "hex" {
				partStrs = append(partStrs, strings.ToUpper(strconv.FormatUint(raw, 16)))
			} else {
				partStrs = append(partStrs, strconv.FormatUint(raw, 10))
			}
		}
		value = prefix + strings.Join(partStrs, delimiter)

	case TypeNumber, "number":
		// Computed field — reads no bytes
		// Phase 2: ref with polynomial/transform, compute with guard
		if field.Ref != "" {
			refName := strings.TrimPrefix(field.Ref, "$")
			refVal, ok := ctx.Variables[refName]
			if !ok {
				return nil, fmt.Errorf("ref field not found: %s", refName)
			}
			numVal, _ := toFloat64(refVal)

			// Apply polynomial (Horner's method)
			if len(field.Polynomial) > 0 {
				numVal = evaluatePolynomial(field.Polynomial, numVal)
			}

			// Apply transform array (for ref fields, transform comes before guard)
			if len(field.Transform) > 0 {
				for _, stage := range field.Transform {
					if stage.Sub != nil {
						numVal = numVal - *stage.Sub
					}
					if stage.Add != nil {
						numVal = numVal + *stage.Add
					}
					if stage.Mult != nil {
						numVal = numVal * *stage.Mult
					}
					if stage.Div != nil && *stage.Div != 0 {
						numVal = numVal / *stage.Div
					}
				}
			}

			// Apply top-level modifiers (mult, add, div) for number fields with ref
			if field.Mult != nil {
				numVal = numVal * *field.Mult
			}
			if field.Div != nil && *field.Div != 0 {
				numVal = numVal / *field.Div
			}
			if field.Add != nil {
				numVal = numVal + *field.Add
			}

			value = numVal
		} else if field.Compute != nil {
			// Binary operation
			result, err := evaluateCompute(field.Compute, ctx)
			if err != nil {
				return nil, err
			}
			value = result
		} else if field.Formula != "" {
			// Legacy formula support
			val, err := evaluateFormula(field.Formula, 0, ctx)
			if err != nil {
				return nil, err
			}
			value = val
		} else {
			value = field.Value
		}

		// Apply guard if present (checks conditions on other fields, returns else if fail)
		if field.Guard != nil {
			if numVal, ok := toFloat64(value); ok {
				value = evaluateGuard(field.Guard, numVal, ctx)
			}
		}

	case TypeObject:
		value, err = decodeFields(field.Fields, ctx)
		if err != nil {
			return nil, err
		}

	case TypeMatch, "CTRL-SWITCH", "Switch":
		value, err = decodeMatch(field, ctx)
		if err != nil {
			return nil, err
		}

	case TypeTLV, "tlv":
		return decodeTLV(field, ctx)

	default:
		return nil, fmt.Errorf("unknown field type: %s", field.Type)
	}

	// Formula takes precedence over top-level modifiers (per spec section 03)
	// For TypeNumber with ref, transform is already applied in the ref block
	if field.Formula != "" && field.Type != TypeNumber {
		if numVal, ok := toFloat64(value); ok {
			result, err := evaluateFormula(field.Formula, numVal, ctx)
			if err != nil {
				return nil, err
			}
			value = result
		}
	} else if (field.Type == TypeNumber || field.Type == "number") && field.Ref != "" {
		// Transform already applied in the ref block, skip
	} else if numVal, ok := toFloat64(value); ok {
		// Apply transformations in order
		// Support both top-level shortcuts and transform array
		if len(field.Transform) > 0 {
			// Transform array: each stage applied sequentially, ops within
			// each stage in YAML key order
			for _, stage := range field.Transform {
				if stage.Add != nil {
					numVal = numVal + *stage.Add
				}
				if stage.Mult != nil {
					numVal = numVal * *stage.Mult
				}
				if stage.Div != nil && *stage.Div != 0 {
					numVal = numVal / *stage.Div
				}
			}
		// Check for legacy 'modifiers' array
		} else if len(field.Modifiers) > 0 {
			for _, stage := range field.Modifiers {
				if stage.Add != nil {
					numVal = numVal + *stage.Add
				}
				if stage.Mult != nil {
					numVal = numVal * *stage.Mult
				}
				if stage.Div != nil && *stage.Div != 0 {
					numVal = numVal / *stage.Div
				}
			}
		// Top-level shortcuts — apply in YAML key order (ModOrder)
		} else if len(field.ModOrder) > 0 {
			for _, key := range field.ModOrder {
				switch key {
				case "add":
					if field.Add != nil {
						numVal = numVal + *field.Add
					}
				case "mult":
					if field.Mult != nil {
						numVal = numVal * *field.Mult
					}
				case "div":
					if field.Div != nil && *field.Div != 0 {
						numVal = numVal / *field.Div
					}
				}
			}
		// Fallback for fields without ModOrder (e.g. from JSON)
		} else {
			if field.Add != nil {
				numVal = numVal + *field.Add
			}
			if field.Mult != nil {
				numVal = numVal * *field.Mult
			}
			if field.Div != nil && *field.Div != 0 {
				numVal = numVal / *field.Div
			}
		}
		value = numVal
	}

	// Apply lookup
	if field.Lookup != nil {
		if intVal, ok := toInt(value); ok {
			if lookup, found := field.Lookup[intVal]; found {
				value = lookup
			}
		}
	}
	if field.LookupArray != nil {
		if intVal, ok := toInt(value); ok {
			if intVal >= 0 && intVal < len(field.LookupArray) {
				value = field.LookupArray[intVal]
			}
		}
	}

	// Store variable
	if field.Var != "" {
		ctx.Variables[field.Var] = value
	}

	return value, nil
}

func decodeMatch(field Field, ctx *DecodeContext) (any, error) {
	var matchValue int

	if field.On != "" {
		// Variable-based match
		varName := strings.TrimPrefix(field.On, "$")
		val, ok := ctx.Variables[varName]
		if !ok {
			return nil, fmt.Errorf("variable not found: $%s", varName)
		}
		matchValue, _ = toInt(val)
	} else {
		// Inline match - read bytes
		length := field.Length
		if length == 0 {
			length = 1
		}
		data, err := ctx.Read(length)
		if err != nil {
			return nil, err
		}
		matchValue = int(decodeUint(data, ctx.Endian))
	}

	// Find matching case
	for _, c := range field.Cases {
		if c.Default {
			return decodeFields(c.Fields, ctx)
		}

		caseVal := c.Case
		if caseVal == nil {
			caseVal = c.Match // Legacy support
		}

		if caseVal == nil {
			continue
		}

		matched := false

		switch v := caseVal.(type) {
		case int:
			matched = matchValue == v
		case float64:
			matched = matchValue == int(v)
		case []any:
			for _, item := range v {
				if itemInt, ok := toInt(item); ok && matchValue == itemInt {
					matched = true
					break
				}
			}
		case map[string]any:
			minVal := math.MinInt
			maxVal := math.MaxInt
			if min, ok := v["min"]; ok {
				minVal, _ = toInt(min)
			}
			if max, ok := v["max"]; ok {
				maxVal, _ = toInt(max)
			}
			matched = matchValue >= minVal && matchValue <= maxVal
		}

		if matched {
			return decodeFields(c.Fields, ctx)
		}
	}

	return nil, nil
}

func decodeTLV(field Field, ctx *DecodeContext) (map[string]any, error) {
	tagSize := field.TagSize
	if tagSize == 0 {
		tagSize = 1
	}
	lengthSize := field.LengthSize
	merge := field.Merge == nil || *field.Merge // Default true
	unknownMode := field.Unknown
	if unknownMode == "" {
		unknownMode = "skip"
	}

	result := make(map[string]any)
	var channels []map[string]any

	// Parse until end of data
	for ctx.Remaining() > 0 {
		var tag []int
		var tagValues map[string]int

		if len(field.TagFields) > 0 {
			// Structured tag
			tagValues = make(map[string]int)
			for _, tf := range field.TagFields {
				length := tf.Length
				if length == 0 {
					length = 1
				}
				data, err := ctx.Read(length)
				if err != nil {
					break
				}
				val := int(decodeUint(data, ctx.Endian))
				if tf.Name != "" {
					tagValues[tf.Name] = val
				}
			}

			// Build tag key
			switch tk := field.TagKey.(type) {
			case []any:
				for _, k := range tk {
					if key, ok := k.(string); ok {
						tag = append(tag, tagValues[key])
					}
				}
			case []string:
				for _, key := range tk {
					tag = append(tag, tagValues[key])
				}
			case string:
				tag = []int{tagValues[tk]}
			default:
				// Use first tag field
				if len(field.TagFields) > 0 && field.TagFields[0].Name != "" {
					tag = []int{tagValues[field.TagFields[0].Name]}
				}
			}
		} else {
			// Simple numeric tag
			data, err := ctx.Read(tagSize)
			if err != nil {
				break
			}
			tag = []int{int(decodeUint(data, ctx.Endian))}
		}

		// Read length if specified
		var dataLength int = -1
		if lengthSize > 0 {
			data, err := ctx.Read(lengthSize)
			if err != nil {
				break
			}
			dataLength = int(decodeUint(data, ctx.Endian))
		}

		// Find matching case
		caseKey := findTLVCaseKey(field.TLVCases, tag)
		
		if caseKey != "" {
			caseFields := field.TLVCases[caseKey]
			caseResult, err := decodeFields(caseFields, ctx)
			if err != nil {
				return nil, err
			}

			if merge {
				// Merge fields, converting to array if repeated
				for k, v := range caseResult {
					if existing, ok := result[k]; ok {
						if arr, isArr := existing.([]any); isArr {
							result[k] = append(arr, v)
						} else {
							result[k] = []any{existing, v}
						}
					} else {
						result[k] = v
					}
				}
			} else {
				entry := map[string]any{"tag": tag}
				for k, v := range caseResult {
					entry[k] = v
				}
				channels = append(channels, entry)
			}
		} else {
			// Unknown tag
			if unknownMode == "error" {
				return nil, fmt.Errorf("unknown TLV tag: %v", tag)
			} else if dataLength >= 0 {
				ctx.Read(dataLength) // Skip
			} else {
				break // Can't skip without length
			}
		}
	}

	if !merge {
		result["channels"] = channels
	}

	return result, nil
}

func findTLVCaseKey(cases map[string][]Field, tag []int) string {
	if cases == nil {
		return ""
	}

	// Try direct match for single tag
	if len(tag) == 1 {
		key := strconv.Itoa(tag[0])
		if _, ok := cases[key]; ok {
			return key
		}
	}

	// Try JSON array format
	tagJSON, _ := json.Marshal(tag)
	tagStr := string(tagJSON)
	if _, ok := cases[tagStr]; ok {
		return tagStr
	}

	return ""
}

// formatBytes formats a byte slice according to the specified format option.
func formatBytes(data []byte, format, separator string) any {
	if format == "" {
		format = "hex"
	}

	switch format {
	case "hex", "hex:lower":
		if separator != "" {
			parts := make([]string, len(data))
			for i, b := range data {
				parts[i] = fmt.Sprintf("%02x", b)
			}
			return strings.Join(parts, separator)
		}
		return hex.EncodeToString(data)

	case "hex:upper":
		if separator != "" {
			parts := make([]string, len(data))
			for i, b := range data {
				parts[i] = fmt.Sprintf("%02X", b)
			}
			return strings.Join(parts, separator)
		}
		return strings.ToUpper(hex.EncodeToString(data))

	case "base64":
		return base64.StdEncoding.EncodeToString(data)

	case "array":
		arr := make([]any, len(data))
		for i, b := range data {
			arr[i] = float64(b)
		}
		return arr

	default:
		return hex.EncodeToString(data)
	}
}

// decodeRepeat decodes a repeat/array field.
func decodeRepeat(field Field, ctx *DecodeContext) ([]any, error) {
	maxIterations := field.Max
	if maxIterations == 0 {
		maxIterations = 1000 // Safety limit
	}
	minIterations := field.Min

	var result []any

	// Determine iteration mode
	if field.Count != nil {
		// Count-based: fixed number of iterations
		var count int
		switch c := field.Count.(type) {
		case int:
			count = c
		case float64:
			count = int(c)
		case string:
			// Variable reference
			varName := strings.TrimPrefix(c, "$")
			if val, ok := ctx.Variables[varName]; ok {
				count, _ = toInt(val)
			} else {
				return nil, fmt.Errorf("repeat count variable not found: %s", varName)
			}
		default:
			return nil, fmt.Errorf("invalid count type: %T", field.Count)
		}

		if count > maxIterations {
			count = maxIterations
		}

		for i := 0; i < count; i++ {
			element, err := decodeFields(field.Fields, ctx)
			if err != nil {
				return nil, err
			}
			result = append(result, element)
		}

	} else if field.ByteLength != nil {
		// Byte-length based: consume specified number of bytes
		var byteLength int
		switch bl := field.ByteLength.(type) {
		case int:
			byteLength = bl
		case float64:
			byteLength = int(bl)
		case string:
			varName := strings.TrimPrefix(bl, "$")
			if val, ok := ctx.Variables[varName]; ok {
				byteLength, _ = toInt(val)
			} else {
				return nil, fmt.Errorf("repeat byte_length variable not found: %s", varName)
			}
		default:
			return nil, fmt.Errorf("invalid byte_length type: %T", field.ByteLength)
		}

		endOffset := ctx.Offset + byteLength
		iterations := 0

		for ctx.Offset < endOffset && iterations < maxIterations {
			element, err := decodeFields(field.Fields, ctx)
			if err != nil {
				return nil, err
			}
			result = append(result, element)
			iterations++
		}

		if ctx.Offset != endOffset {
			return nil, fmt.Errorf("repeat byte_length mismatch: expected end at %d, got %d",
				endOffset, ctx.Offset)
		}

	} else if field.Until == "end" {
		// Until-end: repeat until payload exhausted
		iterations := 0

		for ctx.Remaining() > 0 && iterations < maxIterations {
			element, err := decodeFields(field.Fields, ctx)
			if err != nil {
				return nil, err
			}
			result = append(result, element)
			iterations++
		}

	} else {
		return nil, fmt.Errorf("repeat field must specify one of: count, byte_length, or until")
	}

	// Validate minimum iterations
	if len(result) < minIterations {
		return nil, fmt.Errorf("repeat produced %d elements, but minimum is %d",
			len(result), minIterations)
	}

	return result, nil
}

// =============================================================================
// ENCODING
// =============================================================================

// Encode encodes data to binary using the schema.
func (s *Schema) Encode(data map[string]any) ([]byte, error) {
	return s.EncodeWithPort(data, 0)
}

// EncodeWithPort encodes data to binary using port-based schema selection.
func (s *Schema) EncodeWithPort(data map[string]any, fPort int) ([]byte, error) {
	ctx := NewEncodeContext(s.Endian)

	// Encode header fields first
	if len(s.Header) > 0 {
		if err := encodeFields(s.Header, data, ctx); err != nil {
			return nil, err
		}
	}

	// Resolve fields (port-based or top-level)
	fields, _ := s.ResolveFields(fPort)

	// Encode main fields
	if err := encodeFields(fields, data, ctx); err != nil {
		return nil, err
	}

	return ctx.Buffer, nil
}

func encodeFields(fields []Field, data map[string]any, ctx *EncodeContext) error {
	// Pre-scan flagged constructs to compute flag values
	flagsPatches := map[string]int{}
	for _, field := range fields {
		if field.Flagged != nil {
			flags := 0
			for _, group := range field.Flagged.Groups {
				for _, gf := range group.Fields {
					if gf.Name != "" {
						if _, ok := data[gf.Name]; ok {
							flags |= (1 << group.Bit)
							break
						}
					}
				}
			}
			flagsPatches[field.Flagged.Field] = flags
		}
	}

	for _, field := range fields {
		// Flagged construct
		if field.Flagged != nil {
			if err := encodeFlagged(field.Flagged, data, ctx); err != nil {
				return err
			}
			continue
		}

		if field.Name == "" || strings.HasPrefix(field.Name, "_") {
			continue
		}

		// Skip computed fields
		if field.Formula != "" && (field.Type == TypeNumber || field.Type == "number") {
			continue
		}

		// Bitfield string encoding
		if field.Type == TypeBitfieldString {
			if strVal, ok := data[field.Name].(string); ok {
				if err := encodeBitfieldString(field, strVal, ctx); err != nil {
					return err
				}
			}
			continue
		}

		// Patch flags value
		var value any
		if patchedFlags, ok := flagsPatches[field.Name]; ok {
			value = float64(patchedFlags)
		} else {
			var exists bool
			value, exists = data[field.Name]
			if !exists {
				continue
			}
		}

		if err := encodeField(field, value, ctx); err != nil {
			return err
		}
	}
	return nil
}

func encodeFlagged(fd *FlaggedDef, data map[string]any, ctx *EncodeContext) error {
	flags := 0
	for _, group := range fd.Groups {
		for _, gf := range group.Fields {
			if gf.Name != "" {
				if _, ok := data[gf.Name]; ok {
					flags |= (1 << group.Bit)
					break
				}
			}
		}
	}

	for _, group := range fd.Groups {
		if (flags>>group.Bit)&1 == 0 {
			continue
		}
		for _, gf := range group.Fields {
			if gf.Name == "" || strings.HasPrefix(gf.Name, "_") {
				continue
			}
			if gf.Formula != "" && (gf.Type == TypeNumber || gf.Type == "number") {
				continue
			}
			value, ok := data[gf.Name]
			if !ok {
				continue
			}
			if err := encodeField(gf, value, ctx); err != nil {
				return err
			}
		}
	}
	return nil
}

func encodeBitfieldString(field Field, strVal string, ctx *EncodeContext) error {
	parts := field.Parts
	delimiter := field.Delimiter
	if delimiter == "" {
		delimiter = "."
	}
	prefix := field.Prefix

	if prefix != "" && strings.HasPrefix(strVal, prefix) {
		strVal = strVal[len(prefix):]
	}

	segments := strings.Split(strVal, delimiter)
	length := field.Length
	if length == 0 {
		length = 2
	}
	endian := field.Endian
	if endian == "" {
		endian = ctx.Endian
	}

	var intVal uint64
	for i, part := range parts {
		if len(part) < 2 {
			continue
		}
		bitOff := 0
		bitLen := 8
		format := "decimal"
		if f, ok := part[0].(float64); ok {
			bitOff = int(f)
		} else if f, ok := part[0].(int); ok {
			bitOff = f
		}
		if f, ok := part[1].(float64); ok {
			bitLen = int(f)
		} else if f, ok := part[1].(int); ok {
			bitLen = f
		}
		if len(part) > 2 {
			if s, ok := part[2].(string); ok {
				format = s
			}
		}
		seg := "0"
		if i < len(segments) {
			seg = segments[i]
		}
		var val uint64
		if format == "hex" {
			v, _ := strconv.ParseUint(seg, 16, 64)
			val = v
		} else {
			v, _ := strconv.ParseUint(seg, 10, 64)
			val = v
		}
		mask := uint64((1 << bitLen) - 1)
		intVal |= (val & mask) << bitOff
	}

	ctx.Write(encodeUint(intVal, length, endian))
	return nil
}

func encodeField(field Field, value any, ctx *EncodeContext) error {
	length := field.Length
	if length == 0 {
		length = inferLengthFromType(field.Type)
	}
	endian := field.Endian
	if endian == "" {
		endian = ctx.Endian
	}

	// Reverse lookup if value is a string and lookup exists
	if strVal, ok := value.(string); ok && field.Lookup != nil {
		for k, v := range field.Lookup {
			if v == strVal {
				value = float64(k)
				break
			}
		}
	}

	// Reverse modifiers for numeric values
	if numVal, ok := toFloat64(value); ok {
		// Reverse stages in reverse order; within each stage, reverse ops
		if len(field.Transform) > 0 {
			for i := len(field.Transform) - 1; i >= 0; i-- {
				stage := field.Transform[i]
				if stage.Div != nil {
					numVal = numVal * *stage.Div
				}
				if stage.Mult != nil {
					numVal = numVal / *stage.Mult
				}
				if stage.Add != nil {
					numVal = numVal - *stage.Add
				}
			}
		} else if len(field.Modifiers) > 0 {
			for i := len(field.Modifiers) - 1; i >= 0; i-- {
				stage := field.Modifiers[i]
				if stage.Div != nil {
					numVal = numVal * *stage.Div
				}
				if stage.Mult != nil {
					numVal = numVal / *stage.Mult
				}
				if stage.Add != nil {
					numVal = numVal - *stage.Add
				}
			}
		// Top-level shortcuts — reverse YAML key order (ModOrder)
		} else if len(field.ModOrder) > 0 {
			for i := len(field.ModOrder) - 1; i >= 0; i-- {
				switch field.ModOrder[i] {
				case "add":
					if field.Add != nil {
						numVal = numVal - *field.Add
					}
				case "mult":
					if field.Mult != nil {
						numVal = numVal / *field.Mult
					}
				case "div":
					if field.Div != nil {
						numVal = numVal * *field.Div
					}
				}
			}
		// Fallback for fields without ModOrder
		} else {
			if field.Div != nil {
				numVal = numVal * *field.Div
			}
			if field.Mult != nil {
				numVal = numVal / *field.Mult
			}
			if field.Add != nil {
				numVal = numVal - *field.Add
			}
		}
		value = numVal
	}

	switch field.Type {
	case TypeByte, TypeUInt, TypeU8, TypeU16, TypeU32, TypeU64:
		if numVal, ok := toFloat64(value); ok {
			ctx.Write(encodeUint(uint64(numVal), length, endian))
		}

	case TypeSInt, TypeS8, TypeS16, TypeS32, TypeS64, TypeI8, TypeI16, TypeI32, TypeI64:
		if numVal, ok := toFloat64(value); ok {
			ctx.Write(encodeSint(int64(numVal), length, endian))
		}

	case TypeFloat32, TypeF32:
		if numVal, ok := toFloat64(value); ok {
			ctx.Write(encodeFloat32(float32(numVal), endian))
		}

	case TypeFloat64, TypeF64:
		if numVal, ok := toFloat64(value); ok {
			ctx.Write(encodeFloat64(numVal, endian))
		}

	case TypeAscii:
		if strVal, ok := value.(string); ok {
			data := make([]byte, length)
			copy(data, []byte(strVal))
			ctx.Write(data)
		}

	case TypeHex:
		if strVal, ok := value.(string); ok {
			strVal = strings.ReplaceAll(strVal, ":", "")
			strVal = strings.ReplaceAll(strVal, "-", "")
			data, _ := hex.DecodeString(strVal)
			padded := make([]byte, length)
			copy(padded, data)
			ctx.Write(padded)
		}

	case TypeBytes, TypeBytesLower:
		if err := encodeBytes(field, value, length, ctx); err != nil {
			return err
		}

	case TypeObject:
		if mapVal, ok := value.(map[string]any); ok {
			if err := encodeFields(field.Fields, mapVal, ctx); err != nil {
				return err
			}
		}

	case TypeRepeat, TypeRepeatLower:
		if arrVal, ok := value.([]any); ok {
			for _, elem := range arrVal {
				if elemMap, ok := elem.(map[string]any); ok {
					if err := encodeFields(field.Fields, elemMap, ctx); err != nil {
						return err
					}
				}
			}
		}

	case TypeSkip, TypeSkipLower:
		ctx.Write(make([]byte, length))
	}

	return nil
}

func encodeBytes(field Field, value any, length int, ctx *EncodeContext) error {
	var data []byte

	switch v := value.(type) {
	case string:
		// Try to detect format
		if strings.Contains(v, ":") || strings.Contains(v, "-") {
			// Has separator - strip it
			hexStr := strings.ReplaceAll(v, ":", "")
			hexStr = strings.ReplaceAll(hexStr, "-", "")
			data, _ = hex.DecodeString(hexStr)
		} else if len(v)%4 == 0 && len(v) > 0 {
			// Try base64
			if decoded, err := base64.StdEncoding.DecodeString(v); err == nil && len(decoded) == length {
				data = decoded
			} else {
				data, _ = hex.DecodeString(v)
			}
		} else {
			data, _ = hex.DecodeString(v)
		}

	case []any:
		data = make([]byte, len(v))
		for i, b := range v {
			if num, ok := toFloat64(b); ok {
				data[i] = byte(num)
			}
		}

	case []byte:
		data = v
	}

	// Pad or truncate to exact length
	padded := make([]byte, length)
	copy(padded, data)
	ctx.Write(padded)

	return nil
}

func encodeUint(val uint64, length int, endian string) []byte {
	buf := make([]byte, length)
	if endian == "little" {
		for i := 0; i < length; i++ {
			buf[i] = byte(val >> (8 * i))
		}
	} else {
		for i := length - 1; i >= 0; i-- {
			buf[i] = byte(val)
			val >>= 8
		}
	}
	return buf
}

func encodeSint(val int64, length int, endian string) []byte {
	// Convert to unsigned for encoding
	if val < 0 {
		val = (1 << (length * 8)) + val
	}
	return encodeUint(uint64(val), length, endian)
}

func encodeFloat32(val float32, endian string) []byte {
	buf := make([]byte, 4)
	bits := math.Float32bits(val)
	if endian == "little" {
		binary.LittleEndian.PutUint32(buf, bits)
	} else {
		binary.BigEndian.PutUint32(buf, bits)
	}
	return buf
}

func encodeFloat64(val float64, endian string) []byte {
	buf := make([]byte, 8)
	bits := math.Float64bits(val)
	if endian == "little" {
		binary.LittleEndian.PutUint64(buf, bits)
	} else {
		binary.BigEndian.PutUint64(buf, bits)
	}
	return buf
}

// =============================================================================
// Helper functions
// =============================================================================

func decodeUint(data []byte, endian string) uint64 {
	var val uint64
	if endian == "little" {
		for i := len(data) - 1; i >= 0; i-- {
			val = (val << 8) | uint64(data[i])
		}
	} else {
		for _, b := range data {
			val = (val << 8) | uint64(b)
		}
	}
	return val
}

func decodeSint(data []byte, endian string) int64 {
	uval := decodeUint(data, endian)
	bits := len(data) * 8
	signBit := uint64(1) << (bits - 1)
	if uval >= signBit {
		return int64(uval) - (1 << bits)
	}
	return int64(uval)
}

func decodeFloat(data []byte, size int, endian string) (float64, error) {
	switch size {
	case 2:
		// Float16
		var u16 uint16
		if endian == "little" {
			u16 = binary.LittleEndian.Uint16(data)
		} else {
			u16 = binary.BigEndian.Uint16(data)
		}
		return float16ToFloat64(u16), nil
	case 4:
		var u32 uint32
		if endian == "little" {
			u32 = binary.LittleEndian.Uint32(data)
		} else {
			u32 = binary.BigEndian.Uint32(data)
		}
		return float64(math.Float32frombits(u32)), nil
	case 8:
		var u64 uint64
		if endian == "little" {
			u64 = binary.LittleEndian.Uint64(data)
		} else {
			u64 = binary.BigEndian.Uint64(data)
		}
		return math.Float64frombits(u64), nil
	default:
		return 0, fmt.Errorf("unsupported float size: %d", size)
	}
}

func float16ToFloat64(u16 uint16) float64 {
	sign := (u16 >> 15) & 0x1
	exp := (u16 >> 10) & 0x1f
	mant := u16 & 0x3ff

	var val float64
	if exp == 0 {
		// Subnormal or zero
		val = math.Pow(2, -14) * float64(mant) / 1024
	} else if exp == 31 {
		// Inf or NaN
		if mant != 0 {
			return math.NaN()
		}
		val = math.Inf(1)
	} else {
		val = math.Pow(2, float64(exp)-15) * (1 + float64(mant)/1024)
	}

	if sign == 1 {
		val = -val
	}
	return val
}

func decodeBits(byteVal byte, bitOffset, bits int) int {
	mask := (1 << bits) - 1
	return (int(byteVal) >> bitOffset) & mask
}

func toFloat64(v any) (float64, bool) {
	switch val := v.(type) {
	case float64:
		return val, true
	case float32:
		return float64(val), true
	case int:
		return float64(val), true
	case int64:
		return float64(val), true
	case uint64:
		return float64(val), true
	case uint:
		return float64(val), true
	}
	return 0, false
}

func toInt(v any) (int, bool) {
	switch val := v.(type) {
	case int:
		return val, true
	case int64:
		return int(val), true
	case uint64:
		return int(val), true
	case float64:
		return int(val), true
	case float32:
		return int(val), true
	}
	return 0, false
}

// Compact format parsing

var compactFormatPattern = regexp.MustCompile(`(\d*)([a-zA-Z?]):?(\w*)`)

var structFormats = map[byte]struct {
	Type   FieldType
	Length int
}{
	'b': {TypeSInt, 1},
	'B': {TypeUInt, 1},
	'h': {TypeSInt, 2},
	'H': {TypeUInt, 2},
	'i': {TypeSInt, 4},
	'I': {TypeUInt, 4},
	'l': {TypeSInt, 4},
	'L': {TypeUInt, 4},
	'q': {TypeSInt, 8},
	'Q': {TypeUInt, 8},
	'e': {TypeFloat16, 2},
	'f': {TypeFloat32, 4},
	'd': {TypeFloat64, 8},
	'?': {TypeBool, 1},
	'c': {TypeByte, 1},
	'x': {TypeSkip, 1},
	's': {TypeAscii, 0},
	'p': {TypeAscii, 0},
}

var byteOrderPrefixes = map[byte]string{
	'>': "big",
	'<': "little",
	'!': "big",
	'=': "native",
	'@': "native",
}

// ParseCompactFormat parses a Python struct-like format string into fields.
func ParseCompactFormat(format string) ([]Field, string, error) {
	endian := "big"

	if len(format) > 0 {
		if e, ok := byteOrderPrefixes[format[0]]; ok {
			endian = e
			format = format[1:]
		}
	}

	var fields []Field
	matches := compactFormatPattern.FindAllStringSubmatch(format, -1)

	for _, match := range matches {
		countStr, fmtChar, name := match[1], match[2][0], match[3]

		count := 1
		if countStr != "" {
			count, _ = strconv.Atoi(countStr)
		}

		spec, ok := structFormats[fmtChar]
		if !ok {
			return nil, "", fmt.Errorf("unknown format character: %c", fmtChar)
		}

		length := spec.Length
		if fmtChar == 's' || fmtChar == 'p' {
			length = count
			count = 1
		}

		for i := 0; i < count; i++ {
			field := Field{
				Type:   spec.Type,
				Length: length,
				Endian: endian,
			}
			if name != "" {
				if count > 1 {
					field.Name = fmt.Sprintf("%s_%d", name, i)
				} else {
					field.Name = name
				}
			}
			fields = append(fields, field)
		}
	}

	return fields, endian, nil
}

// DecodeCompact decodes binary data using a compact format string.
func DecodeCompact(format string, data []byte) (map[string]any, error) {
	fields, endian, err := ParseCompactFormat(format)
	if err != nil {
		return nil, err
	}

	ctx := NewDecodeContext(data, endian)
	return decodeFields(fields, ctx)
}

// =============================================================================
// Formula evaluator
// =============================================================================

// evaluateFormula evaluates a formula expression with variable substitution.
// evaluatePolynomial evaluates a polynomial using Horner's method.
// coefficients are in order [a_n, a_{n-1}, ..., a_1, a_0].
func evaluatePolynomial(coeffs []float64, x float64) float64 {
	if len(coeffs) == 0 {
		return 0
	}
	result := coeffs[0]
	for i := 1; i < len(coeffs); i++ {
		result = result*x + coeffs[i]
	}
	return result
}

// evaluateCompute evaluates a binary operation.
func evaluateCompute(cd *ComputeDef, ctx *DecodeContext) (float64, error) {
	a, err := resolveOperand(cd.A, ctx)
	if err != nil {
		return 0, err
	}
	b, err := resolveOperand(cd.B, ctx)
	if err != nil {
		return 0, err
	}

	switch cd.Op {
	case "div":
		if b == 0 {
			return 0, fmt.Errorf("division by zero")
		}
		return a / b, nil
	case "mul":
		return a * b, nil
	case "add":
		return a + b, nil
	case "sub":
		return a - b, nil
	case "mod":
		if b == 0 {
			return 0, fmt.Errorf("modulo by zero")
		}
		return float64(int64(a) % int64(b)), nil
	case "idiv":
		if b == 0 {
			return 0, fmt.Errorf("integer division by zero")
		}
		return float64(int64(a) / int64(b)), nil
	default:
		return 0, fmt.Errorf("unknown compute op: %s", cd.Op)
	}
}

// resolveOperand resolves a compute operand (field reference or literal).
func resolveOperand(op string, ctx *DecodeContext) (float64, error) {
	if strings.HasPrefix(op, "$") {
		name := op[1:]
		if val, ok := ctx.Variables[name]; ok {
			if f, ok := toFloat64(val); ok {
				return f, nil
			}
		}
		return 0, fmt.Errorf("operand field not found: %s", name)
	}
	return strconv.ParseFloat(op, 64)
}

// evaluateGuard applies guard conditions, returning value if all pass or else.
func evaluateGuard(gd *GuardDef, value float64, ctx *DecodeContext) float64 {
	for _, cond := range gd.When {
		fieldName := strings.TrimPrefix(cond.Field, "$")
		fieldVal, ok := ctx.Variables[fieldName]
		if !ok {
			return gd.Else
		}
		fv, ok := toFloat64(fieldVal)
		if !ok {
			return gd.Else
		}

		// Check all conditions on this field
		if cond.Gt != nil && !(fv > *cond.Gt) {
			return gd.Else
		}
		if cond.Gte != nil && !(fv >= *cond.Gte) {
			return gd.Else
		}
		if cond.Lt != nil && !(fv < *cond.Lt) {
			return gd.Else
		}
		if cond.Lte != nil && !(fv <= *cond.Lte) {
			return gd.Else
		}
		if cond.Eq != nil && fv != *cond.Eq {
			return gd.Else
		}
	}
	return value
}

// evaluateFormula (DEPRECATED - use polynomial/compute/guard instead)
// Supports: $field_name references, x (raw value), pow/abs/sqrt/min/max,
// arithmetic operators, ternary (cond ? a : b), and/or.
func evaluateFormula(formula string, x float64, ctx *DecodeContext) (float64, error) {
	expr := formula

	// Substitute $field_name references
	varPattern := regexp.MustCompile(`\$([a-zA-Z_][a-zA-Z0-9_]*)`)
	expr = varPattern.ReplaceAllStringFunc(expr, func(match string) string {
		name := match[1:]
		if val, ok := ctx.Variables[name]; ok {
			if f, ok := toFloat64(val); ok {
				return strconv.FormatFloat(f, 'f', -1, 64)
			}
		}
		return "0"
	})

	// Replace standalone 'x' with raw value
	xPattern := regexp.MustCompile(`\bx\b`)
	expr = xPattern.ReplaceAllString(expr, strconv.FormatFloat(x, 'f', -1, 64))

	// Replace 'and'/'or' with Go-compatible tokens for our evaluator
	expr = regexp.MustCompile(`\band\b`).ReplaceAllString(expr, "&&")
	expr = regexp.MustCompile(`\bor\b`).ReplaceAllString(expr, "||")

	return evalExpr(expr)
}

// evalExpr is a simple recursive descent expression parser.
// Supports: +, -, *, /, >, <, >=, <=, ==, !=, &&, ||, ternary (? :),
// pow(), abs(), sqrt(), min(), max(), parentheses, and numeric literals.
func evalExpr(expr string) (float64, error) {
	p := &exprParser{input: strings.TrimSpace(expr), pos: 0}
	val, err := p.parseTernary()
	if err != nil {
		return 0, fmt.Errorf("formula eval failed for %q: %w", expr, err)
	}
	return val, nil
}

type exprParser struct {
	input string
	pos   int
}

func (p *exprParser) skipSpaces() {
	for p.pos < len(p.input) && p.input[p.pos] == ' ' {
		p.pos++
	}
}

func (p *exprParser) peek() byte {
	p.skipSpaces()
	if p.pos >= len(p.input) {
		return 0
	}
	return p.input[p.pos]
}

func (p *exprParser) peekStr(n int) string {
	p.skipSpaces()
	end := p.pos + n
	if end > len(p.input) {
		end = len(p.input)
	}
	return p.input[p.pos:end]
}

func (p *exprParser) parseTernary() (float64, error) {
	val, err := p.parseOr()
	if err != nil {
		return 0, err
	}
	p.skipSpaces()
	if p.pos < len(p.input) && p.input[p.pos] == '?' {
		p.pos++
		trueVal, err := p.parseTernary()
		if err != nil {
			return 0, err
		}
		p.skipSpaces()
		if p.pos < len(p.input) && p.input[p.pos] == ':' {
			p.pos++
			falseVal, err := p.parseTernary()
			if err != nil {
				return 0, err
			}
			if val != 0 {
				return trueVal, nil
			}
			return falseVal, nil
		}
		return 0, fmt.Errorf("expected ':' in ternary")
	}
	return val, nil
}

func (p *exprParser) parseOr() (float64, error) {
	val, err := p.parseAnd()
	if err != nil {
		return 0, err
	}
	for {
		if p.peekStr(2) == "||" {
			p.pos += 2
			right, err := p.parseAnd()
			if err != nil {
				return 0, err
			}
			if val != 0 || right != 0 {
				val = 1
			} else {
				val = 0
			}
		} else {
			break
		}
	}
	return val, nil
}

func (p *exprParser) parseAnd() (float64, error) {
	val, err := p.parseComparison()
	if err != nil {
		return 0, err
	}
	for {
		if p.peekStr(2) == "&&" {
			p.pos += 2
			right, err := p.parseComparison()
			if err != nil {
				return 0, err
			}
			if val != 0 && right != 0 {
				val = 1
			} else {
				val = 0
			}
		} else {
			break
		}
	}
	return val, nil
}

func (p *exprParser) parseComparison() (float64, error) {
	val, err := p.parseAddSub()
	if err != nil {
		return 0, err
	}
	for {
		p.skipSpaces()
		if p.peekStr(2) == ">=" {
			p.pos += 2
			right, err := p.parseAddSub()
			if err != nil {
				return 0, err
			}
			if val >= right { val = 1 } else { val = 0 }
		} else if p.peekStr(2) == "<=" {
			p.pos += 2
			right, err := p.parseAddSub()
			if err != nil {
				return 0, err
			}
			if val <= right { val = 1 } else { val = 0 }
		} else if p.peekStr(2) == "==" {
			p.pos += 2
			right, err := p.parseAddSub()
			if err != nil {
				return 0, err
			}
			if val == right { val = 1 } else { val = 0 }
		} else if p.peekStr(2) == "!=" {
			p.pos += 2
			right, err := p.parseAddSub()
			if err != nil {
				return 0, err
			}
			if val != right { val = 1 } else { val = 0 }
		} else if p.peek() == '>' {
			p.pos++
			right, err := p.parseAddSub()
			if err != nil {
				return 0, err
			}
			if val > right { val = 1 } else { val = 0 }
		} else if p.peek() == '<' {
			p.pos++
			right, err := p.parseAddSub()
			if err != nil {
				return 0, err
			}
			if val < right { val = 1 } else { val = 0 }
		} else {
			break
		}
	}
	return val, nil
}

func (p *exprParser) parseAddSub() (float64, error) {
	val, err := p.parseMulDiv()
	if err != nil {
		return 0, err
	}
	for {
		p.skipSpaces()
		if p.peek() == '+' {
			p.pos++
			right, err := p.parseMulDiv()
			if err != nil {
				return 0, err
			}
			val += right
		} else if p.peek() == '-' {
			p.pos++
			right, err := p.parseMulDiv()
			if err != nil {
				return 0, err
			}
			val -= right
		} else {
			break
		}
	}
	return val, nil
}

func (p *exprParser) parseMulDiv() (float64, error) {
	val, err := p.parseUnary()
	if err != nil {
		return 0, err
	}
	for {
		p.skipSpaces()
		if p.peek() == '*' {
			p.pos++
			right, err := p.parseUnary()
			if err != nil {
				return 0, err
			}
			val *= right
		} else if p.peek() == '/' {
			p.pos++
			right, err := p.parseUnary()
			if err != nil {
				return 0, err
			}
			if right == 0 {
				val = 0
			} else {
				val /= right
			}
		} else {
			break
		}
	}
	return val, nil
}

func (p *exprParser) parseUnary() (float64, error) {
	p.skipSpaces()
	if p.peek() == '-' {
		p.pos++
		val, err := p.parsePrimary()
		if err != nil {
			return 0, err
		}
		return -val, nil
	}
	return p.parsePrimary()
}

func (p *exprParser) parsePrimary() (float64, error) {
	p.skipSpaces()

	// Parenthesized expression
	if p.peek() == '(' {
		p.pos++
		val, err := p.parseTernary()
		if err != nil {
			return 0, err
		}
		p.skipSpaces()
		if p.peek() == ')' {
			p.pos++
		}
		return val, nil
	}

	// Function calls: pow, abs, sqrt, min, max
	for _, fname := range []string{"pow", "abs", "sqrt", "min", "max"} {
		if strings.HasPrefix(p.input[p.pos:], fname+"(") {
			p.pos += len(fname) + 1
			arg1, err := p.parseTernary()
			if err != nil {
				return 0, err
			}
			p.skipSpaces()

			switch fname {
			case "abs":
				if p.peek() == ')' { p.pos++ }
				return math.Abs(arg1), nil
			case "sqrt":
				if p.peek() == ')' { p.pos++ }
				return math.Sqrt(arg1), nil
			}

			// Two-argument functions
			if p.peek() == ',' {
				p.pos++
			}
			arg2, err := p.parseTernary()
			if err != nil {
				return 0, err
			}
			p.skipSpaces()
			if p.peek() == ')' { p.pos++ }

			switch fname {
			case "pow":
				return math.Pow(arg1, arg2), nil
			case "min":
				return math.Min(arg1, arg2), nil
			case "max":
				return math.Max(arg1, arg2), nil
			}
		}
	}

	// Number literal
	start := p.pos
	if p.pos < len(p.input) && (p.input[p.pos] == '-' || p.input[p.pos] == '+') {
		p.pos++
	}
	for p.pos < len(p.input) && (p.input[p.pos] >= '0' && p.input[p.pos] <= '9' || p.input[p.pos] == '.' || p.input[p.pos] == 'e' || p.input[p.pos] == 'E') {
		p.pos++
	}
	if p.pos > start {
		numStr := p.input[start:p.pos]
		val, err := strconv.ParseFloat(numStr, 64)
		if err != nil {
			return 0, fmt.Errorf("invalid number: %s", numStr)
		}
		return val, nil
	}

	return 0, fmt.Errorf("unexpected token at position %d: %q", p.pos, p.input[p.pos:])
}
