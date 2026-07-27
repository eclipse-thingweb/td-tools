#!/usr/bin/env python3
"""
generate-c.py - Generate C codec from Payload Schema YAML

Usage:
    python tools/generate-c.py schema.yaml -o output.h

Generates:
    - Struct definitions for decoded data
    - decode_<name>() function
    - encode_<name>() function
    - Header-only, no dynamic allocation
"""

import argparse
import yaml
import sys
from pathlib import Path
from datetime import datetime

# Type mappings: schema type -> (C type, size in bytes, signed)
TYPE_MAP = {
    # Unsigned types
    'u8': ('u1_t', 1, False),
    'u16': ('u2_t', 2, False),
    'u24': ('u4_t', 3, False),  # Stored in u32
    'u32': ('u4_t', 4, False),
    'u64': ('u8_t', 8, False),
    # Signed types (i prefix)
    'i8': ('s1_t', 1, True),
    'i16': ('s2_t', 2, True),
    'i24': ('s4_t', 3, True),   # Stored in s32
    'i32': ('s4_t', 4, True),
    'i64': ('s8_t', 8, True),
    # Signed types (s prefix - alias)
    's8': ('s1_t', 1, True),
    's16': ('s2_t', 2, True),
    's24': ('s4_t', 3, True),
    's32': ('s4_t', 4, True),
    's64': ('s8_t', 8, True),
    # Long form aliases
    'uint8': ('u1_t', 1, False),
    'uint16': ('u2_t', 2, False),
    'uint32': ('u4_t', 4, False),
    'int8': ('s1_t', 1, True),
    'int16': ('s2_t', 2, True),
    'int32': ('s4_t', 4, True),
}


def to_c_name(name: str) -> str:
    """Convert schema name to valid C identifier."""
    return name.replace('-', '_').replace('.', '_').lower()


def generate_struct(schema: dict) -> str:
    """Generate C struct from schema fields."""
    name = to_c_name(schema['name'])
    lines = [f"typedef struct {{"]
    
    for field in schema.get('fields', []):
        field_name = to_c_name(field['name'])
        field_type = field.get('type', 'u8')
        
        # Skip internal fields
        if field_name.startswith('_'):
            continue
        
        # Handle match/conditional - create union
        if field_type == 'match':
            lines.append(f"    /* Conditional field - see cases */")
            continue
        
        # Handle bitfields
        if ':' in str(field_type):
            base_type, bits = field_type.split(':')
            c_type = TYPE_MAP.get(base_type, ('u1_t', 1, False))[0]
            lines.append(f"    {c_type} {field_name};")
        elif field_type == 'bytes':
            length = field.get('length', 16)
            if isinstance(length, int):
                lines.append(f"    u1_t {field_name}[{length}];")
                lines.append(f"    u1_t {field_name}_len;")
            else:
                lines.append(f"    u1_t* {field_name};")
                lines.append(f"    u2_t {field_name}_len;")
        elif field_type in TYPE_MAP:
            c_type = TYPE_MAP[field_type][0]
            lines.append(f"    {c_type} {field_name};")
        else:
            lines.append(f"    u1_t {field_name};  /* unknown type: {field_type} */")
    
    lines.append(f"}} {name}_t;")
    return '\n'.join(lines)


def generate_decoder(schema: dict) -> str:
    """Generate decode function from schema."""
    name = to_c_name(schema['name'])
    endian = schema.get('endian', 'big')
    read_suffix = '_le' if endian == 'little' else '_be'
    
    lines = [
        f"static inline int decode_{name}(",
        f"    const u1_t* buf,",
        f"    size_t len,",
        f"    {name}_t* out",
        f") {{",
        f"    if (!buf || !out) return -1;",
        f"    memset(out, 0, sizeof(*out));",
        f"    size_t pos = 0;",
        f"",
    ]
    
    for field in schema.get('fields', []):
        field_name = to_c_name(field['name'])
        field_type = field.get('type', 'u8')
        
        # Skip internal/hidden fields
        if field_name.startswith('_'):
            continue
            
        # Skip conditional types for now
        if field_type == 'match':
            lines.append(f"    /* TODO: conditional field {field_name} */")
            continue
        
        # Handle bitfields
        if ':' in str(field_type):
            base_type, bits = field_type.split(':')
            bits = int(bits)
            type_info = TYPE_MAP.get(base_type, ('u1_t', 1, False))
            size = type_info[1]
            
            lines.append(f"    /* {field_name}: {bits} bits */")
            lines.append(f"    if (pos + {size} > len) return -2;")
            
            if size == 1:
                lines.append(f"    out->{field_name} = buf[pos] & ((1 << {bits}) - 1);")
            else:
                lines.append(f"    out->{field_name} = read_u{size}{read_suffix}(buf + pos) & ((1 << {bits}) - 1);")
            
            # Check for consume field
            consume = field.get('consume', 0)
            if consume:
                lines.append(f"    pos += {consume};")
            continue
        
        if field_type not in TYPE_MAP:
            lines.append(f"    /* TODO: {field_name} type {field_type} */")
            continue
        
        type_info = TYPE_MAP[field_type]
        c_type, size, signed = type_info
        
        lines.append(f"    /* {field_name}: {field_type} */")
        lines.append(f"    if (pos + {size} > len) return -2;")
        
        if size == 1:
            lines.append(f"    out->{field_name} = buf[pos];")
        elif size == 3:  # u24/i24
            lines.append(f"    out->{field_name} = buf[pos] | ((u4_t)buf[pos+1] << 8) | ((u4_t)buf[pos+2] << 16);")
            if signed:
                lines.append(f"    if (out->{field_name} & 0x800000) out->{field_name} |= 0xFF000000;  /* sign extend */")
        else:
            lines.append(f"    out->{field_name} = read_u{size}{read_suffix}(buf + pos);")
        
        lines.append(f"    pos += {size};")
        
        # Apply multiplier if present
        mult = field.get('mult')
        if mult and mult != 1:
            lines.append(f"    /* Note: apply mult {mult} in application */")
        
        lines.append("")
    
    lines.extend([
        f"    return (int)pos;  /* bytes consumed */",
        f"}}",
    ])
    
    return '\n'.join(lines)


def generate_encoder(schema: dict) -> str:
    """Generate encode function from schema."""
    name = to_c_name(schema['name'])
    endian = schema.get('endian', 'big')
    write_suffix = '_le' if endian == 'little' else '_be'
    
    lines = [
        f"static inline int encode_{name}(",
        f"    const {name}_t* in,",
        f"    u1_t* buf,",
        f"    size_t max_len",
        f") {{",
        f"    if (!in || !buf) return -1;",
        f"    size_t pos = 0;",
        f"",
    ]
    
    for field in schema.get('fields', []):
        field_name = to_c_name(field['name'])
        field_type = field.get('type', 'u8')
        
        if field_name.startswith('_'):
            continue
            
        if field_type == 'match':
            lines.append(f"    /* TODO: conditional field {field_name} */")
            continue
        
        # Handle bitfields
        if ':' in str(field_type):
            base_type, bits = field_type.split(':')
            bits = int(bits)
            type_info = TYPE_MAP.get(base_type, ('u1_t', 1, False))
            size = type_info[1]
            
            lines.append(f"    /* {field_name}: {bits} bits */")
            if size == 1:
                lines.append(f"    if (pos + 1 > max_len) return -2;")
                lines.append(f"    buf[pos] = in->{field_name} & ((1 << {bits}) - 1);")
            
            consume = field.get('consume', 0)
            if consume:
                lines.append(f"    pos += {consume};")
            continue
        
        if field_type not in TYPE_MAP:
            lines.append(f"    /* TODO: {field_name} type {field_type} */")
            continue
        
        type_info = TYPE_MAP[field_type]
        c_type, size, signed = type_info
        
        lines.append(f"    /* {field_name}: {field_type} */")
        lines.append(f"    if (pos + {size} > max_len) return -2;")
        
        if size == 1:
            lines.append(f"    buf[pos] = in->{field_name};")
        elif size == 3:
            lines.append(f"    buf[pos] = in->{field_name} & 0xFF;")
            lines.append(f"    buf[pos+1] = (in->{field_name} >> 8) & 0xFF;")
            lines.append(f"    buf[pos+2] = (in->{field_name} >> 16) & 0xFF;")
        else:
            lines.append(f"    write_u{size}{write_suffix}(buf + pos, in->{field_name});")
        
        lines.append(f"    pos += {size};")
        lines.append("")
    
    lines.extend([
        f"    return (int)pos;  /* bytes written */",
        f"}}",
    ])
    
    return '\n'.join(lines)


def generate_header(schema: dict) -> str:
    """Generate complete header file."""
    name = to_c_name(schema['name'])
    guard = f"_{name.upper()}_CODEC_H_"
    
    header = f"""/*
 * {name}_codec.h - Auto-generated codec for {schema.get('name', 'unknown')}
 *
 * Generated by: generate-c.py
 * Generated at: {datetime.now().isoformat()}
 * Schema version: {schema.get('version', '1')}
 *
 * DO NOT EDIT - Regenerate from schema
 */

#ifndef {guard}
#define {guard}

#include "rt.h"

#ifdef __cplusplus
extern "C" {{
#endif

/* ============================================
 * Constants
 * ============================================ */

#define {name.upper()}_VERSION "{schema.get('version', '1')}"

/* ============================================
 * Data Structure
 * ============================================ */

{generate_struct(schema)}

/* ============================================
 * Decoder
 * ============================================ */

/**
 * Decode {name} payload from bytes
 *
 * @param buf    Input buffer
 * @param len    Input length
 * @param out    Output structure
 * @return       Bytes consumed on success, negative on error
 *               -1: Invalid parameters
 *               -2: Buffer too short
 */
{generate_decoder(schema)}

/* ============================================
 * Encoder
 * ============================================ */

/**
 * Encode {name} payload to bytes
 *
 * @param in      Input structure
 * @param buf     Output buffer
 * @param max_len Maximum buffer size
 * @return        Bytes written on success, negative on error
 */
{generate_encoder(schema)}

#ifdef __cplusplus
}}
#endif

#endif /* {guard} */
"""
    return header


def main():
    parser = argparse.ArgumentParser(
        description='Generate C codec from Payload Schema YAML'
    )
    parser.add_argument('schema', help='Path to schema YAML file')
    parser.add_argument('-o', '--output', help='Output header file')
    args = parser.parse_args()
    
    # Load schema
    with open(args.schema) as f:
        schema = yaml.safe_load(f)
    
    # Generate header
    header = generate_header(schema)
    
    # Write output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(header)
        print(f"Generated: {args.output}")
    else:
        print(header)


if __name__ == '__main__':
    main()
