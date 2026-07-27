#!/usr/bin/env python3
"""
generate_jsonschema.py - Generate JSON Schema for Payload Schema validation

Generates a JSON Schema (draft-07) that validates Payload Schema YAML files.
This enables IDE autocompletion, inline validation, and CI pipeline checks.

Usage:
    python tools/generate_jsonschema.py > payload-schema.json
    python tools/generate_jsonschema.py --output schemas/payload-schema.json
"""

import argparse
import json
import sys


def generate_payload_schema() -> dict:
    """Generate the JSON Schema for validating Payload Schema files."""
    
    # Reusable type enum
    field_types = [
        "u8", "u16", "u24", "u32", "u64",
        "uint8", "uint16", "uint24", "uint32", "uint64",
        "s8", "s16", "s24", "s32", "s64",
        "i8", "i16", "i24", "i32", "i64",
        "int8", "int16", "int24", "int32", "int64",
        "f16", "f32", "f64", "float", "double",
        "bool", "bytes", "string", "ascii", "hex", "base64",
        "object", "match", "enum", "skip",
        "bitfield_string", "number", "version_string",
        "udec", "sdec", "UDec", "SDec",
    ]
    
    # Field definition (recursive for nested objects)
    field_def = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Field name in decoded output. Prefix with _ for internal/hidden fields."
            },
            "type": {
                "type": "string",
                "description": "Data type. Standard types or bitfield syntax (u8[3:4], bits<3,2>, etc.)"
            },
            "length": {
                "type": "integer",
                "minimum": 1,
                "description": "Byte length for bytes/string/hex/base64/bitfield_string/version_string types"
            },
            "consume": {
                "type": "integer",
                "minimum": 0,
                "description": "Bytes to advance after reading. 0 = don't advance (shared byte)."
            },
            "bit": {
                "type": "integer",
                "minimum": 0,
                "maximum": 7,
                "description": "Bit position for bool type"
            },
            "mult": {
                "type": "number",
                "description": "Multiply raw value by this factor"
            },
            "div": {
                "type": "number",
                "exclusiveMinimum": 0,
                "description": "Divide raw value by this factor"
            },
            "add": {
                "type": "number",
                "description": "Add this offset to raw value"
            },
            "formula": {
                "type": "string",
                "description": "DEPRECATED: Custom formula. Use polynomial, compute, or ref+transform instead."
            },
            "encode_formula": {
                "type": "string",
                "description": "Custom inverse formula for encoding (Phase 3)"
            },
            "ref": {
                "type": "string",
                "description": "Reference to another field value ($field_name) for computed fields"
            },
            "polynomial": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 2,
                "description": "Polynomial coefficients in descending power order [a_n, ..., a_0]"
            },
            "compute": {
                "type": "object",
                "properties": {
                    "op": {
                        "type": "string",
                        "enum": ["add", "sub", "mul", "div", "mod", "idiv"],
                        "description": "Binary operation to perform"
                    },
                    "a": {
                        "description": "First operand: $field_name or literal number"
                    },
                    "b": {
                        "description": "Second operand: $field_name or literal number"
                    }
                },
                "required": ["op", "a", "b"],
                "description": "Cross-field binary computation"
            },
            "guard": {
                "type": "object",
                "properties": {
                    "when": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field": {"type": "string", "description": "$field_name to check"},
                                "gt": {"type": "number", "description": "Greater than"},
                                "gte": {"type": "number", "description": "Greater than or equal"},
                                "lt": {"type": "number", "description": "Less than"},
                                "lte": {"type": "number", "description": "Less than or equal"},
                                "eq": {"type": "number", "description": "Equal to"},
                                "ne": {"type": "number", "description": "Not equal to"}
                            },
                            "required": ["field"]
                        },
                        "description": "Conditions that must all pass (AND)"
                    },
                    "else": {
                        "description": "Fallback value if conditions fail"
                    }
                },
                "required": ["when"],
                "description": "Conditional evaluation with fallback"
            },
            "transform": {
                "type": "array",
                "items": {
                    "type": "object",
                    "description": "Transform operation: sqrt, abs, pow, floor, ceiling, clamp, log10, log, add, mult, div"
                },
                "description": "Sequential math operations to apply"
            },
            "unit": {
                "type": "string",
                "description": "Engineering unit (e.g., degC, %RH, mV)"
            },
            "var": {
                "type": "string",
                "description": "Store decoded value as variable for later match/formula references"
            },
            "lookup": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Lookup table: index -> string value"
            },
            "values": {
                "description": "Enum values: dict {int: string} or list [string]"
            },
            "base": {
                "type": "string",
                "description": "Base integer type for enum (default: u8)"
            },
            "fields": {
                "type": "array",
                "items": {"$ref": "#/definitions/field"},
                "description": "Nested fields for object type"
            },
            "on": {
                "type": "string",
                "description": "Match discriminator field name (legacy syntax)"
            },
            "cases": {
                "description": "Match cases: legacy [{case:, fields:}] or Option B {value: [fields]}"
            },
            "default": {
                "description": "Default case behavior: 'error', 'skip', or {fields: [...]}"
            },
            "semantic": {
                "type": "object",
                "properties": {
                    "ipso": {"type": "integer", "description": "IPSO Smart Object ID"},
                    "senml": {"type": "string", "description": "SenML name"}
                },
                "description": "Semantic mapping for output formats"
            },
            "description": {
                "type": "string",
                "description": "Human-readable field description"
            },
            "parts": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": [
                        {"type": "integer", "description": "Bit offset"},
                        {"type": "integer", "description": "Bit length"},
                    ]
                },
                "description": "Bitfield string parts: [[bitOffset, bitLength, format?], ...]"
            },
            "delimiter": {
                "type": "string",
                "description": "Delimiter for bitfield_string/version_string assembly"
            },
            "prefix": {
                "type": "string",
                "description": "Prefix for bitfield_string/version_string output"
            },
        },
        "additionalProperties": True
    }
    
    # Match construct (Option B)
    match_def = {
        "type": "object",
        "properties": {
            "field": {"type": "string", "description": "Variable reference ($var) for dispatch"},
            "length": {"type": "integer", "description": "Inline read N bytes for dispatch value"},
            "name": {"type": "string", "description": "Include dispatch value in output with this name"},
            "var": {"type": "string", "description": "Store dispatch value as variable"},
            "cases": {"type": "object", "description": "Map of value -> [field_list]"},
            "default": {"description": "'error', 'skip', or [field_list]"},
        }
    }
    
    # TLV construct
    tlv_def = {
        "type": "object",
        "properties": {
            "tag_size": {"type": "integer", "minimum": 1, "description": "Tag size in bytes"},
            "length_size": {"type": "integer", "minimum": 0, "description": "Length field size (0=implicit)"},
            "merge": {"type": "boolean", "description": "Merge into parent (default: true)"},
            "unknown": {"type": "string", "enum": ["skip", "error", "raw"]},
            "cases": {"type": "object", "description": "Map of tag_value -> [field_list]"},
            "tag_fields": {"type": "array", "description": "Composite tag field definitions"},
            "tag_key": {"description": "Key field(s) for composite tag matching"},
        },
        "required": ["cases"]
    }
    
    # Flagged construct
    flagged_def = {
        "type": "object",
        "properties": {
            "field": {"type": "string", "description": "Name of the flags/bitmask field"},
            "groups": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "bit": {"type": "integer", "minimum": 0},
                        "fields": {
                            "type": "array",
                            "items": {"$ref": "#/definitions/field"}
                        }
                    },
                    "required": ["bit", "fields"]
                }
            }
        },
        "required": ["field", "groups"]
    }
    
    # Byte group construct
    byte_group_def = {
        "type": "object",
        "properties": {
            "byte_group": {
                "type": "array",
                "items": {"$ref": "#/definitions/field"},
                "description": "Fields sharing the same byte(s)"
            },
            "size": {"type": "integer", "minimum": 1, "description": "Group byte size"}
        },
        "required": ["byte_group"]
    }
    
    # Top-level field entry (union of field, match, object, tlv, flagged, byte_group)
    top_field = {
        "oneOf": [
            {"$ref": "#/definitions/field"},
            {
                "type": "object",
                "properties": {
                    "match": match_def,
                },
                "required": ["match"]
            },
            {
                "type": "object",
                "properties": {
                    "object": {"type": "string"},
                    "fields": {"type": "array", "items": {"$ref": "#/definitions/field"}},
                },
                "required": ["object", "fields"]
            },
            {
                "type": "object",
                "properties": {
                    "tlv": tlv_def,
                },
                "required": ["tlv"]
            },
            {
                "type": "object",
                "properties": {
                    "flagged": flagged_def,
                },
                "required": ["flagged"]
            },
            byte_group_def,
            {
                "type": "object",
                "properties": {
                    "$ref": {"type": "string", "pattern": "^#/definitions/"},
                },
                "required": ["$ref"]
            }
        ]
    }
    
    # Port definition
    port_def = {
        "type": "object",
        "properties": {
            "direction": {
                "type": "string",
                "enum": ["uplink", "downlink", "both"],
                "description": "Data direction"
            },
            "description": {"type": "string"},
            "fields": {
                "type": "array",
                "minItems": 1,
                "description": "Field definitions for this port"
            }
        },
        "required": ["fields"]
    }
    
    # Test vector
    test_vector = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
            "payload": {"description": "Hex string, byte array, or 0x-prefixed string"},
            "fport": {"type": "integer", "minimum": 1, "maximum": 255},
            "fPort": {"type": "integer", "minimum": 1, "maximum": 255},
            "expected": {"type": "object", "description": "Expected decoded field values"},
            "input_metadata": {"type": "object", "description": "TS013 input metadata for testing"},
        },
        "required": ["name", "payload", "expected"]
    }
    
    # Metadata enrichment
    metadata_def = {
        "type": "object",
        "properties": {
            "include": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "source": {"type": "string", "description": "$ reference to TS013 input"},
                    },
                    "required": ["name", "source"]
                }
            },
            "timestamps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "mode": {
                            "type": "string",
                            "enum": ["rx_time", "subtract", "unix_epoch", "iso8601", "elapsed_to_absolute"]
                        },
                        "field": {"type": "string"},
                        "offset_field": {"type": "string"},
                        "elapsed_field": {"type": "string"},
                        "time_base": {"type": "string"},
                        "source": {"type": "string"},
                        "format": {"type": "string", "description": "strftime format for iso8601 mode"},
                    },
                    "required": ["name"]
                }
            }
        }
    }
    
    # Main schema
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://lorawan-schema.org/payload-schema/v1",
        "title": "LoRaWAN Payload Schema",
        "description": "Schema for defining LoRaWAN device payload codec descriptions",
        "type": "object",
        "definitions": {
            "field": field_def,
        },
        "properties": {
            "name": {
                "type": "string",
                "description": "Schema name (typically device model)"
            },
            "version": {
                "type": "integer",
                "minimum": 1,
                "description": "Schema version"
            },
            "endian": {
                "type": "string",
                "enum": ["big", "little"],
                "default": "big",
                "description": "Default byte order"
            },
            "description": {
                "type": "string",
                "description": "Human-readable schema description"
            },
            "manufacturer": {
                "type": "string",
                "description": "Device manufacturer name"
            },
            "device": {
                "type": "string",
                "description": "Device model name"
            },
            "fields": {
                "type": "array",
                "minItems": 1,
                "description": "Field definitions (for single-port schemas)"
            },
            "ports": {
                "type": "object",
                "description": "Port-based field definitions: {port_number: {fields: [...]}}"
            },
            "definitions": {
                "type": "object",
                "description": "Reusable field group definitions for $ref"
            },
            "test_vectors": {
                "type": "array",
                "items": test_vector,
                "description": "Test cases for validation"
            },
            "metadata": metadata_def,
        },
        "required": ["name"],
        "anyOf": [
            {"required": ["fields"]},
            {"required": ["ports"]}
        ]
    }
    
    return schema


def main():
    parser = argparse.ArgumentParser(
        description='Generate JSON Schema for Payload Schema validation'
    )
    parser.add_argument('-o', '--output', help='Output file path (default: stdout)')
    parser.add_argument('--compact', action='store_true', help='Compact JSON output')
    args = parser.parse_args()
    
    schema = generate_payload_schema()
    
    indent = None if args.compact else 2
    output = json.dumps(schema, indent=indent)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
            f.write('\n')
        print(f"JSON Schema written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == '__main__':
    main()
