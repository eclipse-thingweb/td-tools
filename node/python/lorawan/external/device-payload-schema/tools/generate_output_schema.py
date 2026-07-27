#!/usr/bin/env python3
"""
Generate JSON Schema for device codec output.

This tool generates a JSON Schema that describes the structure of the decoded
payload data returned by the codec. This schema can be used to validate
decoder output with standard JSON Schema tools.

Usage:
    python generate_output_schema.py schema.yaml > output-schema.json
    python generate_output_schema.py schema.yaml -o output-schema.json
"""

import argparse
import json
import sys
import yaml
from typing import Any, Dict, List, Optional


def yaml_type_to_json_schema(field_type: str, field_def: Dict[str, Any]) -> Dict[str, Any]:
    """Convert YAML field type to JSON Schema type definition."""
    
    # Handle bitfield syntax like u8[4:7]
    base_type = field_type.split('[')[0].split(':')[0]
    
    # Remove endian prefix
    if base_type.startswith('be_') or base_type.startswith('le_'):
        base_type = base_type[3:]
    
    # Integer types
    if base_type in ('u8', 'u16', 'u24', 'u32', 'u64', 'uint8', 'uint16', 'uint24', 'uint32', 'uint64'):
        schema = {"type": "integer", "minimum": 0}
        # Add maximum based on bit width
        bits = {'u8': 8, 'u16': 16, 'u24': 24, 'u32': 32, 'u64': 64,
                'uint8': 8, 'uint16': 16, 'uint24': 24, 'uint32': 32, 'uint64': 64}
        if base_type in bits:
            # Check for bitfield extraction
            if '[' in field_type:
                import re
                match = re.search(r'\[(\d+):(\d+)\]', field_type)
                if match:
                    low, high = int(match.group(1)), int(match.group(2))
                    bit_width = high - low + 1
                    schema["maximum"] = (1 << bit_width) - 1
            else:
                schema["maximum"] = (1 << bits[base_type]) - 1
        return schema
    
    # Signed integer types
    if base_type in ('s8', 's16', 's24', 's32', 's64', 'i8', 'i16', 'i24', 'i32', 'i64',
                     'int8', 'int16', 'int24', 'int32', 'int64'):
        return {"type": "integer"}
    
    # Float types - after modifiers, output is always number
    if base_type in ('f16', 'f32', 'f64', 'float16', 'float32', 'float64'):
        return {"type": "number"}
    
    # Bool type
    if base_type == 'bool':
        return {"type": "boolean"}
    
    # String types
    if base_type in ('ascii', 'string', 'hex', 'base64'):
        return {"type": "string"}
    
    # Bytes type
    if base_type == 'bytes':
        fmt = field_def.get('format', 'hex')
        if fmt == 'array':
            return {"type": "array", "items": {"type": "integer", "minimum": 0, "maximum": 255}}
        return {"type": "string"}
    
    # Number type (computed fields)
    if base_type == 'number':
        return {"type": "number"}
    
    # Enum type
    if base_type == 'enum':
        values = field_def.get('values', {})
        if values:
            return {"type": "string", "enum": list(values.values())}
        return {"type": ["string", "integer"]}
    
    # Default to number (most fields with modifiers become numbers)
    return {"type": "number"}


def has_modifiers(field_def: Dict[str, Any]) -> bool:
    """Check if field has arithmetic modifiers that convert to float."""
    return any(k in field_def for k in ('mult', 'div', 'add', 'polynomial', 'transform'))


def field_to_json_schema(field_def: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert a field definition to JSON Schema property."""
    
    field_type = field_def.get('type', '')
    name = field_def.get('name', '')
    
    # Skip internal fields
    if name.startswith('_'):
        return None
    
    # Get base schema from type
    schema = yaml_type_to_json_schema(field_type, field_def)
    
    # If field has modifiers, output becomes number
    if has_modifiers(field_def) and schema.get('type') == 'integer':
        schema = {"type": "number"}
    
    # Handle lookup - converts to string or keeps original
    if 'lookup' in field_def:
        lookup = field_def['lookup']
        if isinstance(lookup, dict):
            # Lookup values become the output
            schema = {"type": ["string", "integer"]}
        elif isinstance(lookup, list):
            schema = {"type": "string", "enum": lookup}
    
    # Add description from field
    if field_def.get('description'):
        schema['description'] = field_def['description']
    
    # Add unit as description suffix
    if field_def.get('unit'):
        unit_desc = f"Unit: {field_def['unit']}"
        if 'description' in schema:
            schema['description'] += f" ({unit_desc})"
        else:
            schema['description'] = unit_desc
    
    # Add valid_range as bounds hint in description
    if field_def.get('valid_range'):
        vr = field_def['valid_range']
        range_desc = f"Valid range: [{vr[0]}, {vr[1]}]"
        if 'description' in schema:
            schema['description'] += f". {range_desc}"
        else:
            schema['description'] = range_desc
    
    return schema


def process_byte_group(bg_def: Dict[str, Any], properties: Dict, required: List[str]):
    """Process byte_group fields and add to properties."""
    if isinstance(bg_def, dict):
        fields = bg_def.get('fields', [])
    else:
        fields = bg_def if isinstance(bg_def, list) else []
    
    for field in fields:
        if not isinstance(field, dict):
            continue
        name = field.get('name', '')
        if name and not name.startswith('_'):
            schema = field_to_json_schema(field)
            if schema:
                properties[name] = schema
                required.append(name)


def process_fields(fields: List[Dict], properties: Dict, required: List[str]):
    """Process field list and populate properties dict."""
    
    for field in fields:
        if not isinstance(field, dict):
            continue
        
        # Handle byte_group
        if 'byte_group' in field:
            process_byte_group(field['byte_group'], properties, required)
            continue
        
        # Handle flagged groups
        if 'flagged' in field:
            flagged = field['flagged']
            for group in flagged.get('groups', []):
                if 'fields' in group:
                    process_fields(group['fields'], properties, required)
            continue
        
        # Handle switch
        if 'switch' in field:
            switch = field['switch']
            for case_fields in switch.get('cases', {}).values():
                if isinstance(case_fields, list):
                    process_fields(case_fields, properties, required)
            continue
        
        # Handle tlv
        if 'tlv' in field:
            tlv = field['tlv']
            for case_fields in tlv.get('cases', {}).values():
                if isinstance(case_fields, list):
                    process_fields(case_fields, properties, required)
            continue
        
        # Handle nested object
        if 'object' in field and not field.get('type'):
            obj_name = field['object']
            nested_props = {}
            nested_req = []
            if 'fields' in field:
                process_fields(field['fields'], nested_props, nested_req)
            properties[obj_name] = {
                "type": "object",
                "properties": nested_props
            }
            if nested_req:
                properties[obj_name]["required"] = nested_req
            required.append(obj_name)
            continue
        
        # Regular field
        name = field.get('name', '')
        if name and not name.startswith('_'):
            schema = field_to_json_schema(field)
            if schema:
                properties[name] = schema
                # Fields are generally required unless conditional
                required.append(name)


def generate_output_schema(yaml_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Generate JSON Schema for codec output from YAML payload schema."""
    
    schema_name = yaml_schema.get('name', 'payload')
    schema_version = yaml_schema.get('version', 1)
    description = yaml_schema.get('description', f'{schema_name} decoded payload')
    
    properties = {}
    required = []
    
    # Process top-level fields
    fields = yaml_schema.get('fields', [])
    process_fields(fields, properties, required)
    
    # Process port-based fields
    ports = yaml_schema.get('ports', {})
    for port_num, port_def in ports.items():
        if isinstance(port_def, dict) and 'fields' in port_def:
            process_fields(port_def['fields'], properties, required)
    
    # Build output schema
    output_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": f"https://lorawan-schema.org/devices/{schema_name}/v{schema_version}/output",
        "title": f"{schema_name} Decoded Payload",
        "description": description,
        "type": "object",
        "properties": properties,
        "additionalProperties": True  # Allow _quality and other metadata
    }
    
    # Don't require all fields since some may be conditional
    # Only mark truly required fields
    # For now, don't add required array since most fields are conditional
    
    return output_schema


def main():
    parser = argparse.ArgumentParser(
        description='Generate JSON Schema for device codec output'
    )
    parser.add_argument('schema', help='Input YAML schema file')
    parser.add_argument('-o', '--output', help='Output file (default: stdout)')
    parser.add_argument('--compact', action='store_true', help='Compact JSON output')
    
    args = parser.parse_args()
    
    # Load YAML schema
    with open(args.schema, 'r') as f:
        yaml_schema = yaml.safe_load(f)
    
    # Generate output schema
    output_schema = generate_output_schema(yaml_schema)
    
    # Format output
    indent = None if args.compact else 2
    json_output = json.dumps(output_schema, indent=indent)
    
    # Write output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(json_output)
            f.write('\n')
        print(f"Generated: {args.output}", file=sys.stderr)
    else:
        print(json_output)


if __name__ == '__main__':
    main()
