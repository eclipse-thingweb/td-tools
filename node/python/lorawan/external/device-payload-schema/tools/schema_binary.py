#!/usr/bin/env python3
"""
schema_binary.py - Compact Binary Schema Encoder/Decoder

Creates the binary schema format defined in Payload Schema Section 17 (OTA Transfer).

Binary format (per field, 4 bytes minimum):
┌─────────┬──────────┬───────────┬───────────┐
│ Type    │ Mult Exp │ Field ID  │ [Options] │
│ 1 byte  │ 1 byte   │ 2 bytes   │ variable  │
└─────────┴──────────┴───────────┴───────────┘

Type byte: [TTTT SSSS]
  TTTT = Type (4 bits): 0=uint, 1=sint, 2=float, 3=bytes, 4=bool, 5=enum, 6=bitfield
  SSSS = Size (4 bits): byte count or bit count for bitfields

Usage:
  # Encode schema to binary
  python schema_binary.py encode schema.yaml -o schema.bin
  
  # Decode binary to YAML
  python schema_binary.py decode schema.bin -o schema.yaml
  
  # Show binary hex dump with annotations
  python schema_binary.py dump schema.bin
  
  # Get info/stats
  python schema_binary.py info schema.yaml
"""

import argparse
import struct
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import re

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Type codes (4 bits)
TYPE_UINT = 0x0
TYPE_SINT = 0x1
TYPE_FLOAT = 0x2
TYPE_BYTES = 0x3
TYPE_BOOL = 0x4
TYPE_ENUM = 0x5
TYPE_BITFIELD = 0x6
TYPE_MATCH = 0x7
TYPE_SKIP = 0x8
TYPE_LOOKUP = 0x9  # Field has lookup table following

# IPSO Smart Object IDs (common ones)
IPSO_IDS = {
    'temperature': 3303,
    'humidity': 3304,
    'pressure': 3315,
    'voltage': 3316,
    'current': 3317,
    'power': 3328,
    'energy': 3331,
    'distance': 3330,
    'illuminance': 3301,
    'presence': 3302,
    'accel_x': 3313,
    'accel_y': 3314,
    'accel_z': 3315,
    'latitude': 3336,
    'longitude': 3337,
    'altitude': 3338,
}

# Reverse lookup
IPSO_NAMES = {v: k for k, v in IPSO_IDS.items()}


def parse_type(type_str: str) -> Tuple[int, int, Optional[Tuple[int, int]]]:
    """Parse type string, return (type_code, size, bitfield_info)."""
    type_str = type_str.lower().strip()
    
    # Bitfield: u8[3:5] or u8[3+:2]
    bitfield_match = re.match(r'u8\[(\d+):(\d+)\]', type_str)
    if bitfield_match:
        start, end = int(bitfield_match.group(1)), int(bitfield_match.group(2))
        width = end - start + 1
        return TYPE_BITFIELD, width, (start, width)
    
    bitfield_match = re.match(r'u8\[(\d+)\+:(\d+)\]', type_str)
    if bitfield_match:
        start, width = int(bitfield_match.group(1)), int(bitfield_match.group(2))
        return TYPE_BITFIELD, width, (start, width)
    
    # Standard types
    type_map = {
        'u8': (TYPE_UINT, 1), 'uint8': (TYPE_UINT, 1),
        'u16': (TYPE_UINT, 2), 'uint16': (TYPE_UINT, 2),
        'u24': (TYPE_UINT, 3),
        'u32': (TYPE_UINT, 4), 'uint32': (TYPE_UINT, 4),
        's8': (TYPE_SINT, 1), 'i8': (TYPE_SINT, 1), 'int8': (TYPE_SINT, 1),
        's16': (TYPE_SINT, 2), 'i16': (TYPE_SINT, 2), 'int16': (TYPE_SINT, 2),
        's24': (TYPE_SINT, 3),
        's32': (TYPE_SINT, 4), 'i32': (TYPE_SINT, 4), 'int32': (TYPE_SINT, 4),
        'f32': (TYPE_FLOAT, 4), 'float': (TYPE_FLOAT, 4),
        'f64': (TYPE_FLOAT, 8), 'double': (TYPE_FLOAT, 8),
        'f16': (TYPE_FLOAT, 2),
        'bool': (TYPE_BOOL, 1),
        'skip': (TYPE_SKIP, 1),
        'bytes': (TYPE_BYTES, 0),  # Variable
        'string': (TYPE_BYTES, 0),
        'ascii': (TYPE_BYTES, 0),
        'hex': (TYPE_BYTES, 0),
        'match': (TYPE_MATCH, 0),
        'object': (TYPE_MATCH, 0),  # Nested
        'enum': (TYPE_ENUM, 1),
    }
    
    if type_str in type_map:
        code, size = type_map[type_str]
        return code, size, None
    
    return TYPE_UINT, 1, None  # Default


def mult_to_exp(mult: float) -> int:
    """Convert multiplier to signed exponent byte. mult = 10^exp."""
    if mult == 1.0:
        return 0
    if mult == 0:
        return 0
    
    # Handle common cases
    exp_map = {
        0.001: -3, 0.01: -2, 0.1: -1,
        10: 1, 100: 2, 1000: 3,
        0.0001: -4, 0.00001: -5,
        0.5: 0x80 | 1,  # Special: 0.5 = flag + scale
        0.0625: 0x80 | 4,  # 1/16
        0.00390625: 0x80 | 8,  # 1/256
    }
    
    if mult in exp_map:
        return exp_map[mult] & 0xFF
    
    # Calculate exponent
    import math
    if mult > 0:
        exp = round(math.log10(mult))
        return exp & 0xFF
    
    return 0


def exp_to_mult(exp: int) -> float:
    """Convert exponent byte back to multiplier."""
    if exp == 0:
        return 1.0
    
    # Handle special flag for non-power-of-10
    if exp & 0x80:
        scale = exp & 0x7F
        return 1.0 / (2 ** scale)
    
    # Signed byte
    if exp > 127:
        exp = exp - 256
    
    return 10.0 ** exp


def get_field_id(field: Dict) -> int:
    """Get numeric field ID from field definition."""
    # Check for explicit IPSO mapping
    if 'semantic' in field:
        sem = field['semantic']
        if isinstance(sem, dict) and 'ipso' in sem:
            return sem['ipso']
    
    # Check name against known IPSO
    name = field.get('name', '').lower()
    if name in IPSO_IDS:
        return IPSO_IDS[name]
    
    # Generate hash-based ID for unknown fields
    name_bytes = field.get('name', '').encode('utf-8')
    return (hash(name_bytes) & 0xFFFF) | 0x8000  # Set high bit for custom


def encode_field(field: Dict) -> bytes:
    """Encode a single field to binary."""
    result = bytearray()
    
    type_str = field.get('type', 'u8')
    type_code, size, bitfield_info = parse_type(type_str)
    
    # Handle variable-length types
    if type_code == TYPE_BYTES:
        size = field.get('length', 0)
    elif type_code == TYPE_SKIP:
        size = field.get('length', 1)
    
    # Type byte: [TTTT SSSS]
    type_byte = ((type_code & 0x0F) << 4) | (size & 0x0F)
    
    # Check for lookup table
    has_lookup = bool(field.get('lookup') or field.get('values'))
    if has_lookup:
        type_byte |= 0x80  # Set high bit to indicate lookup follows
    
    result.append(type_byte)
    
    # Multiplier exponent
    mult = field.get('mult', 1.0)
    div = field.get('div', 1.0)
    if div != 1.0:
        mult = mult / div
    result.append(mult_to_exp(mult))
    
    # Field ID (2 bytes, little-endian)
    field_id = get_field_id(field)
    result.extend(struct.pack('<H', field_id))
    
    # Bitfield info (if applicable)
    if bitfield_info:
        start, width = bitfield_info
        result.append((start << 4) | width)
        # Consume flag
        consume = field.get('consume', 0)
        if consume:
            result.append(0x01)
    
    # Add offset
    add = field.get('add', 0)
    if add != 0:
        result.append(0xA0)  # Add marker
        result.extend(struct.pack('<h', int(add * 100)))  # Fixed point
    
    # Lookup table
    if has_lookup:
        lookup = field.get('lookup') or field.get('values', {})
        if isinstance(lookup, list):
            # Convert list to dict
            lookup = {i: v for i, v in enumerate(lookup)}
        
        result.append(len(lookup))
        for key, value in lookup.items():
            result.append(int(key) & 0xFF)
            value_bytes = str(value).encode('utf-8')[:15]  # Max 15 chars
            result.append(len(value_bytes))
            result.extend(value_bytes)
    
    return bytes(result)


def encode_schema(schema: Dict) -> bytes:
    """Encode full schema to binary."""
    result = bytearray()
    
    # Header
    result.append(0x50)  # Magic: 'P' for Payload Schema
    result.append(0x53)  # Magic: 'S'
    result.append(schema.get('version', 1))
    
    # Flags
    flags = 0
    if schema.get('endian', 'big') == 'little':
        flags |= 0x01
    result.append(flags)
    
    # Field count
    fields = schema.get('fields', [])
    result.append(len(fields))
    
    # Encode each field
    for field in fields:
        field_type = field.get('type', '')
        
        # Handle match/nested
        if field_type == 'match':
            result.append((TYPE_MATCH << 4) | 0)
            # Variable name
            var_name = field.get('on', field.get('true', '')).lstrip('$')
            var_bytes = var_name.encode('utf-8')[:15]
            result.append(len(var_bytes))
            result.extend(var_bytes)
            
            # Cases
            cases = field.get('cases', [])
            result.append(len(cases))
            for case in cases:
                if 'default' in case:
                    result.append(0xFF)  # Default marker
                else:
                    case_val = case.get('case', 0)
                    result.append(case_val & 0xFF)
                
                # Case fields
                case_fields = case.get('fields', [])
                result.append(len(case_fields))
                for cf in case_fields:
                    result.extend(encode_field(cf))
        else:
            result.extend(encode_field(field))
    
    return bytes(result)


def decode_field(data: bytes, offset: int) -> Tuple[Dict, int]:
    """Decode a single field from binary. Returns (field_dict, new_offset)."""
    field = {}
    
    type_byte = data[offset]
    has_lookup = bool(type_byte & 0x80)
    type_code = (type_byte >> 4) & 0x07
    size = type_byte & 0x0F
    offset += 1
    
    # Multiplier
    mult_exp = data[offset]
    mult = exp_to_mult(mult_exp)
    offset += 1
    
    # Field ID
    field_id = struct.unpack_from('<H', data, offset)[0]
    offset += 2
    
    # Determine type string
    type_names = {
        TYPE_UINT: {1: 'u8', 2: 'u16', 3: 'u24', 4: 'u32'},
        TYPE_SINT: {1: 's8', 2: 's16', 3: 's24', 4: 's32'},
        TYPE_FLOAT: {2: 'f16', 4: 'f32', 8: 'f64'},
        TYPE_BOOL: {1: 'bool'},
        TYPE_SKIP: {0: 'skip'},
        TYPE_BYTES: {0: 'bytes'},
        TYPE_ENUM: {1: 'enum'},
    }
    
    if type_code == TYPE_BITFIELD:
        # Read bitfield info
        bf_byte = data[offset]
        start = (bf_byte >> 4) & 0x0F
        width = bf_byte & 0x0F
        offset += 1
        field['type'] = f'u8[{start}:{start + width - 1}]'
        
        # Check consume
        if offset < len(data) and data[offset] == 0x01:
            field['consume'] = 1
            offset += 1
    else:
        type_map = type_names.get(type_code, {})
        field['type'] = type_map.get(size, 'u8')
    
    # Name from IPSO or generate
    if field_id in IPSO_NAMES:
        field['name'] = IPSO_NAMES[field_id]
    elif field_id & 0x8000:
        field['name'] = f'field_{field_id & 0x7FFF:04x}'
    else:
        field['name'] = f'ipso_{field_id}'
    
    # Multiplier
    if mult != 1.0:
        field['mult'] = mult
    
    # Check for add marker
    if offset < len(data) and data[offset] == 0xA0:
        offset += 1
        add_val = struct.unpack_from('<h', data, offset)[0] / 100.0
        field['add'] = add_val
        offset += 2
    
    # Lookup table
    if has_lookup:
        lookup_count = data[offset]
        offset += 1
        lookup = {}
        for _ in range(lookup_count):
            key = data[offset]
            offset += 1
            str_len = data[offset]
            offset += 1
            value = data[offset:offset + str_len].decode('utf-8')
            offset += str_len
            lookup[key] = value
        field['lookup'] = lookup
    
    return field, offset


def decode_schema(data: bytes) -> Dict:
    """Decode binary schema to dict."""
    if len(data) < 5:
        raise ValueError("Binary too short")
    
    if data[0:2] != b'PS':
        raise ValueError("Invalid magic bytes")
    
    schema = {
        'version': data[2],
        'endian': 'little' if data[3] & 0x01 else 'big',
        'fields': []
    }
    
    field_count = data[4]
    offset = 5
    
    for _ in range(field_count):
        if offset >= len(data):
            break
        
        type_peek = data[offset]
        type_code = (type_peek >> 4) & 0x0F
        
        if type_code == TYPE_MATCH:
            # Match field
            offset += 1
            var_len = data[offset]
            offset += 1
            var_name = data[offset:offset + var_len].decode('utf-8')
            offset += var_len
            
            match_field = {
                'type': 'match',
                'on': f'${var_name}',
                'cases': []
            }
            
            case_count = data[offset]
            offset += 1
            
            for _ in range(case_count):
                case_val = data[offset]
                offset += 1
                
                case_obj = {}
                if case_val == 0xFF:
                    case_obj['default'] = 'skip'
                else:
                    case_obj['case'] = case_val
                
                case_field_count = data[offset]
                offset += 1
                case_obj['fields'] = []
                
                for _ in range(case_field_count):
                    cf, offset = decode_field(data, offset)
                    case_obj['fields'].append(cf)
                
                match_field['cases'].append(case_obj)
            
            schema['fields'].append(match_field)
        else:
            field, offset = decode_field(data, offset)
            schema['fields'].append(field)
    
    return schema


def dump_binary(data: bytes) -> str:
    """Create annotated hex dump."""
    lines = []
    lines.append(f"Binary Schema: {len(data)} bytes")
    lines.append("-" * 60)
    
    if len(data) < 5:
        lines.append("ERROR: Too short")
        return '\n'.join(lines)
    
    lines.append(f"00-01: {data[0]:02X} {data[1]:02X}  Magic: 'PS'")
    lines.append(f"02:    {data[2]:02X}        Version: {data[2]}")
    lines.append(f"03:    {data[3]:02X}        Flags: {'little-endian' if data[3] & 1 else 'big-endian'}")
    lines.append(f"04:    {data[4]:02X}        Field count: {data[4]}")
    
    offset = 5
    field_num = 0
    
    while offset < len(data):
        lines.append("")
        type_byte = data[offset]
        type_code = (type_byte >> 4) & 0x07
        size = type_byte & 0x0F
        has_lookup = bool(type_byte & 0x80)
        
        type_names = ['uint', 'sint', 'float', 'bytes', 'bool', 'enum', 'bits', 'match', 'skip', 'lookup']
        type_name = type_names[type_code] if type_code < len(type_names) else 'unknown'
        
        lines.append(f"Field {field_num}:")
        lines.append(f"  {offset:02X}: {type_byte:02X}  Type: {type_name}, size: {size}, lookup: {has_lookup}")
        offset += 1
        
        if offset >= len(data):
            break
        
        if type_code == TYPE_MATCH:
            var_len = data[offset]
            offset += 1
            var_name = data[offset:offset + var_len].decode('utf-8', errors='replace')
            offset += var_len
            lines.append(f"       Match on: ${var_name}")
            # Skip case details for dump
            break
        
        mult_exp = data[offset]
        mult = exp_to_mult(mult_exp)
        lines.append(f"  {offset:02X}: {mult_exp:02X}  Mult exp: {mult_exp} -> {mult}")
        offset += 1
        
        if offset + 1 >= len(data):
            break
        
        field_id = struct.unpack_from('<H', data, offset)[0]
        name = IPSO_NAMES.get(field_id, f'custom_{field_id:04X}')
        lines.append(f"  {offset:02X}: {data[offset]:02X} {data[offset+1]:02X}  Field ID: {field_id} ({name})")
        offset += 2
        
        field_num += 1
        
        # Skip detailed parsing for dump
        if has_lookup and offset < len(data):
            lookup_count = data[offset]
            lines.append(f"  {offset:02X}: {lookup_count:02X}  Lookup entries: {lookup_count}")
            offset += 1
            # Skip lookup data
            for _ in range(lookup_count):
                if offset >= len(data):
                    break
                offset += 1  # key
                if offset >= len(data):
                    break
                str_len = data[offset]
                offset += 1 + str_len
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Binary schema encoder/decoder')
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Encode
    enc = subparsers.add_parser('encode', help='Encode YAML schema to binary')
    enc.add_argument('input', type=Path, help='Input YAML file')
    enc.add_argument('-o', '--output', type=Path, help='Output binary file')
    enc.add_argument('--base64', action='store_true', help='Output as base64')
    
    # Decode
    dec = subparsers.add_parser('decode', help='Decode binary to YAML')
    dec.add_argument('input', type=Path, help='Input binary file')
    dec.add_argument('-o', '--output', type=Path, help='Output YAML file')
    
    # Dump
    dmp = subparsers.add_parser('dump', help='Hex dump with annotations')
    dmp.add_argument('input', type=Path, help='Input binary file')
    
    # Info
    inf = subparsers.add_parser('info', help='Show schema size info')
    inf.add_argument('input', type=Path, help='Input YAML file')
    
    args = parser.parse_args()
    
    if not HAS_YAML:
        print("Error: PyYAML required. Install with: pip install pyyaml", file=sys.stderr)
        sys.exit(1)
    
    if args.command == 'encode':
        schema = yaml.safe_load(args.input.read_text())
        binary = encode_schema(schema)
        
        if args.base64:
            import base64
            output = base64.b64encode(binary).decode('ascii')
            print(output)
        elif args.output:
            args.output.write_bytes(binary)
            print(f"Encoded to {args.output} ({len(binary)} bytes)", file=sys.stderr)
        else:
            # Hex output
            print(binary.hex())
        
        print(f"# YAML: {args.input.stat().st_size} bytes -> Binary: {len(binary)} bytes", file=sys.stderr)
        print(f"# Compression: {args.input.stat().st_size / len(binary):.1f}x", file=sys.stderr)
    
    elif args.command == 'decode':
        binary = args.input.read_bytes()
        schema = decode_schema(binary)
        
        output = yaml.dump(schema, default_flow_style=False, sort_keys=False)
        
        if args.output:
            args.output.write_text(output)
            print(f"Decoded to {args.output}", file=sys.stderr)
        else:
            print(output)
    
    elif args.command == 'dump':
        binary = args.input.read_bytes()
        print(dump_binary(binary))
    
    elif args.command == 'info':
        schema = yaml.safe_load(args.input.read_text())
        binary = encode_schema(schema)
        
        yaml_size = args.input.stat().st_size
        bin_size = len(binary)
        
        print(f"Schema: {schema.get('name', 'unnamed')}")
        print(f"Fields: {len(schema.get('fields', []))}")
        print(f"YAML size: {yaml_size} bytes")
        print(f"Binary size: {bin_size} bytes")
        print(f"Compression: {yaml_size / bin_size:.1f}x")
        print(f"LoRaWAN packets (DR0, 51 bytes): {(bin_size + 50) // 51}")
        print(f"LoRaWAN packets (DR3, 115 bytes): {(bin_size + 114) // 115}")
        print(f"QR code friendly: {'Yes' if bin_size < 100 else 'No (consider compression)'}")


if __name__ == '__main__':
    main()
