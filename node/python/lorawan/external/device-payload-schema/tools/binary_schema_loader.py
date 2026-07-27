#!/usr/bin/env python3
"""
binary_schema_loader.py - Load binary schemas for fast interpretation

Loads the compact binary schema format and converts to interpreter format,
or provides direct binary-to-decode capability for maximum performance.

Performance benefits:
- No YAML/JSON parsing (biggest win)
- Pre-parsed type codes (no string matching)
- Direct struct unpacking
- Memory-mappable for C interpreters
"""

import struct
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, BinaryIO
from enum import IntEnum


class TypeCode(IntEnum):
    """Binary type codes (4 bits)."""
    UINT = 0x0
    SINT = 0x1
    FLOAT = 0x2
    BYTES = 0x3
    BOOL = 0x4
    ENUM = 0x5
    BITFIELD = 0x6
    MATCH = 0x7
    SKIP = 0x8


# IPSO Smart Object IDs
IPSO_NAMES = {
    3303: 'temperature',
    3304: 'humidity',
    3315: 'pressure',
    3316: 'voltage',
    3317: 'current',
    3328: 'power',
    3331: 'energy',
    3330: 'distance',
    3301: 'illuminance',
    3302: 'presence',
}


@dataclass
class BinaryField:
    """Pre-parsed field for fast decoding."""
    name: str
    type_code: TypeCode
    size: int  # bytes or bits for bitfield
    mult: float = 1.0
    add: float = 0.0
    field_id: int = 0
    bitfield_start: int = 0
    bitfield_width: int = 0
    consume: bool = True
    lookup: Optional[Dict[int, str]] = None
    
    # For match fields
    match_var: str = ''
    cases: List[Tuple[int, List['BinaryField']]] = field(default_factory=list)


@dataclass 
class BinarySchema:
    """Pre-parsed schema for fast decoding."""
    version: int
    endian: str  # 'big' or 'little'
    fields: List[BinaryField]
    
    # Original dict for compatibility
    _dict_cache: Optional[Dict] = None


def exp_to_mult(exp: int) -> float:
    """Convert exponent byte to multiplier."""
    if exp == 0:
        return 1.0
    
    # Check for special 0.5-based multipliers (0x80 | scale)
    # 0x81 = 0.5, 0x82 = 0.25, etc.
    if exp == 0x81:
        return 0.5
    if exp == 0x82:
        return 0.25
    if exp == 0x84:
        return 0.0625
    
    # Treat as signed byte for power-of-10
    if exp > 127:
        exp = exp - 256
    
    return 10.0 ** exp


def load_binary_field(data: bytes, offset: int) -> Tuple[BinaryField, int]:
    """Load a single field from binary. Returns (field, new_offset)."""
    type_byte = data[offset]
    has_lookup = bool(type_byte & 0x80)
    type_code_raw = (type_byte >> 4) & 0x0F
    # Handle lookup flag in high bit of type nibble
    if type_code_raw > 8:
        type_code_raw &= 0x07
        has_lookup = True
    try:
        type_code = TypeCode(type_code_raw)
    except ValueError:
        type_code = TypeCode.UINT  # Default
    size = type_byte & 0x0F
    offset += 1
    
    # Multiplier
    mult_exp = data[offset]
    mult = exp_to_mult(mult_exp)
    offset += 1
    
    # Field ID
    field_id = struct.unpack_from('<H', data, offset)[0]
    offset += 2
    
    # Name from IPSO or generate
    if field_id in IPSO_NAMES:
        name = IPSO_NAMES[field_id]
    elif field_id & 0x8000:
        name = f'field_{field_id & 0x7FFF:04x}'
    else:
        name = f'ipso_{field_id}'
    
    bf_start, bf_width = 0, 0
    consume = True
    add = 0.0
    
    # Bitfield info
    if type_code == TypeCode.BITFIELD:
        bf_byte = data[offset]
        bf_start = (bf_byte >> 4) & 0x0F
        bf_width = bf_byte & 0x0F
        offset += 1
        if offset < len(data) and data[offset] == 0x01:
            consume = True
            offset += 1
        else:
            consume = False
    
    # Add marker
    if offset < len(data) and data[offset] == 0xA0:
        offset += 1
        add = struct.unpack_from('<h', data, offset)[0] / 100.0
        offset += 2
    
    # Lookup table
    lookup = None
    if has_lookup and offset < len(data):
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
    
    return BinaryField(
        name=name,
        type_code=type_code,
        size=size,
        mult=mult,
        add=add,
        field_id=field_id,
        bitfield_start=bf_start,
        bitfield_width=bf_width,
        consume=consume,
        lookup=lookup,
    ), offset


def load_binary_schema(data: bytes) -> BinarySchema:
    """Load schema from binary format."""
    if len(data) < 5 or data[0:2] != b'PS':
        raise ValueError("Invalid binary schema format")
    
    version = data[2]
    endian = 'little' if data[3] & 0x01 else 'big'
    field_count = data[4]
    
    fields = []
    offset = 5
    
    for _ in range(field_count):
        if offset >= len(data):
            break
        
        type_peek = data[offset]
        type_code = (type_peek >> 4) & 0x0F
        
        if type_code == TypeCode.MATCH:
            # Match field - complex parsing
            offset += 1
            var_len = data[offset]
            offset += 1
            var_name = data[offset:offset + var_len].decode('utf-8')
            offset += var_len
            
            case_count = data[offset]
            offset += 1
            
            cases = []
            for _ in range(case_count):
                case_val = data[offset]
                offset += 1
                
                case_field_count = data[offset]
                offset += 1
                
                case_fields = []
                for _ in range(case_field_count):
                    cf, offset = load_binary_field(data, offset)
                    case_fields.append(cf)
                
                cases.append((case_val if case_val != 0xFF else -1, case_fields))
            
            fields.append(BinaryField(
                name='_match',
                type_code=TypeCode.MATCH,
                size=0,
                match_var=var_name,
                cases=cases,
            ))
        else:
            bf, offset = load_binary_field(data, offset)
            fields.append(bf)
    
    return BinarySchema(version=version, endian=endian, fields=fields)


def binary_schema_to_dict(schema: BinarySchema) -> Dict[str, Any]:
    """Convert BinarySchema to dict for compatibility with SchemaInterpreter."""
    def field_to_dict(f: BinaryField) -> Dict[str, Any]:
        type_names = {
            TypeCode.UINT: {1: 'u8', 2: 'u16', 3: 'u24', 4: 'u32'},
            TypeCode.SINT: {1: 's8', 2: 's16', 3: 's24', 4: 's32'},
            TypeCode.FLOAT: {2: 'f16', 4: 'f32', 8: 'f64'},
            TypeCode.BOOL: {1: 'bool'},
            TypeCode.SKIP: {0: 'skip', 1: 'skip'},
            TypeCode.BYTES: {0: 'bytes'},
            TypeCode.ENUM: {1: 'enum'},
        }
        
        d = {'name': f.name}
        
        if f.type_code == TypeCode.BITFIELD:
            d['type'] = f'u8[{f.bitfield_start}:{f.bitfield_start + f.bitfield_width - 1}]'
            if f.consume:
                d['consume'] = 1
        elif f.type_code == TypeCode.MATCH:
            d['type'] = 'match'
            d['on'] = f'${f.match_var}'
            d['cases'] = []
            for case_val, case_fields in f.cases:
                case_dict = {'fields': [field_to_dict(cf) for cf in case_fields]}
                if case_val == -1:
                    case_dict['default'] = 'skip'
                else:
                    case_dict['case'] = case_val
                d['cases'].append(case_dict)
        else:
            type_map = type_names.get(f.type_code, {})
            d['type'] = type_map.get(f.size, 'u8')
        
        if f.mult != 1.0:
            d['mult'] = f.mult
        if f.add != 0.0:
            d['add'] = f.add
        if f.lookup:
            d['lookup'] = f.lookup
        
        return d
    
    return {
        'version': schema.version,
        'endian': schema.endian,
        'fields': [field_to_dict(f) for f in schema.fields],
    }


class BinarySchemaDecoder:
    """
    Fast decoder using pre-parsed binary schema.
    
    This bypasses the generic SchemaInterpreter for maximum performance.
    """
    
    def __init__(self, schema: BinarySchema):
        self.schema = schema
        self.endian = '<' if schema.endian == 'little' else '>'
    
    def decode(self, payload: bytes) -> Dict[str, Any]:
        """Decode payload using binary schema."""
        result = {}
        variables = {}
        pos = 0
        
        for field in self.schema.fields:
            if pos >= len(payload) and field.type_code != TypeCode.SKIP:
                break
            
            value, pos = self._decode_field(field, payload, pos, variables)
            
            if field.name and not field.name.startswith('_'):
                # Store variable for match
                if field.name:
                    variables[field.name] = value
                
                # Apply modifiers
                if isinstance(value, (int, float)):
                    if field.mult != 1.0:
                        value = value * field.mult
                    if field.add != 0.0:
                        value = value + field.add
                
                # Apply lookup
                if field.lookup and isinstance(value, int):
                    value = field.lookup.get(value, f'unknown({value})')
                
                result[field.name] = value
        
        return result
    
    def _decode_field(self, field: BinaryField, buf: bytes, pos: int, 
                      variables: Dict) -> Tuple[Any, int]:
        """Decode single field."""
        tc = field.type_code
        size = field.size
        
        if tc == TypeCode.UINT:
            if size == 1:
                return buf[pos], pos + 1
            elif size == 2:
                fmt = f'{self.endian}H'
                return struct.unpack_from(fmt, buf, pos)[0], pos + 2
            elif size == 3:
                if self.endian == '>':
                    return (buf[pos] << 16) | (buf[pos+1] << 8) | buf[pos+2], pos + 3
                else:
                    return buf[pos] | (buf[pos+1] << 8) | (buf[pos+2] << 16), pos + 3
            elif size == 4:
                fmt = f'{self.endian}I'
                return struct.unpack_from(fmt, buf, pos)[0], pos + 4
        
        elif tc == TypeCode.SINT:
            if size == 1:
                v = buf[pos]
                return v - 256 if v > 127 else v, pos + 1
            elif size == 2:
                fmt = f'{self.endian}h'
                return struct.unpack_from(fmt, buf, pos)[0], pos + 2
            elif size == 4:
                fmt = f'{self.endian}i'
                return struct.unpack_from(fmt, buf, pos)[0], pos + 4
        
        elif tc == TypeCode.FLOAT:
            if size == 4:
                fmt = f'{self.endian}f'
                return struct.unpack_from(fmt, buf, pos)[0], pos + 4
            elif size == 8:
                fmt = f'{self.endian}d'
                return struct.unpack_from(fmt, buf, pos)[0], pos + 8
        
        elif tc == TypeCode.BOOL:
            return buf[pos] != 0, pos + 1
        
        elif tc == TypeCode.BITFIELD:
            byte_val = buf[pos]
            value = (byte_val >> field.bitfield_start) & ((1 << field.bitfield_width) - 1)
            new_pos = pos + 1 if field.consume else pos
            return value, new_pos
        
        elif tc == TypeCode.SKIP:
            return None, pos + (size if size else 1)
        
        elif tc == TypeCode.MATCH:
            var_value = variables.get(field.match_var, 0)
            for case_val, case_fields in field.cases:
                if case_val == -1 or case_val == var_value:
                    for cf in case_fields:
                        val, pos = self._decode_field(cf, buf, pos, variables)
                        if cf.name and not cf.name.startswith('_'):
                            variables[cf.name] = val
                    break
            return None, pos
        
        return 0, pos


def load_schema(path_or_data) -> Tuple[BinarySchema, Dict]:
    """
    Load schema from file or bytes.
    
    Returns (BinarySchema, dict) for both fast and compatible access.
    """
    if isinstance(path_or_data, bytes):
        data = path_or_data
    else:
        from pathlib import Path
        p = Path(path_or_data)
        if p.suffix in ['.bin', '.pbs']:
            data = p.read_bytes()
        else:
            # YAML/JSON - use schema_binary to convert
            from schema_binary import encode_schema
            import yaml
            schema_dict = yaml.safe_load(p.read_text())
            data = encode_schema(schema_dict)
    
    schema = load_binary_schema(data)
    schema_dict = binary_schema_to_dict(schema)
    
    return schema, schema_dict


# Benchmark helper
def benchmark_binary_vs_yaml(schema_path: str, payload: bytes, iterations: int = 10000):
    """Compare binary vs YAML schema loading and decoding performance."""
    import time
    import yaml
    from pathlib import Path
    from schema_interpreter import SchemaInterpreter
    from schema_binary import encode_schema
    
    # Load YAML
    yaml_content = Path(schema_path).read_text()
    
    # Time YAML parsing
    start = time.perf_counter()
    for _ in range(100):
        schema_dict = yaml.safe_load(yaml_content)
    yaml_parse_time = (time.perf_counter() - start) / 100 * 1000
    
    # Convert to binary
    binary_data = encode_schema(schema_dict)
    
    # Time binary parsing
    start = time.perf_counter()
    for _ in range(100):
        bin_schema = load_binary_schema(binary_data)
    binary_parse_time = (time.perf_counter() - start) / 100 * 1000
    
    # Time YAML-based decoding
    interpreter = SchemaInterpreter(schema_dict)
    start = time.perf_counter()
    for _ in range(iterations):
        interpreter.decode(payload)
    yaml_decode_time = (time.perf_counter() - start) / iterations * 1e6
    
    # Time binary-based decoding
    decoder = BinarySchemaDecoder(bin_schema)
    start = time.perf_counter()
    for _ in range(iterations):
        decoder.decode(payload)
    binary_decode_time = (time.perf_counter() - start) / iterations * 1e6
    
    print(f"Schema parsing:")
    print(f"  YAML:   {yaml_parse_time:.3f} ms")
    print(f"  Binary: {binary_parse_time:.3f} ms")
    print(f"  Speedup: {yaml_parse_time / binary_parse_time:.1f}x")
    print()
    print(f"Payload decoding ({iterations} iterations):")
    print(f"  YAML interpreter:   {yaml_decode_time:.2f} µs/decode")
    print(f"  Binary decoder:     {binary_decode_time:.2f} µs/decode")
    print(f"  Speedup: {yaml_decode_time / binary_decode_time:.1f}x")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'benchmark':
        # Run benchmark
        schema_path = sys.argv[2] if len(sys.argv) > 2 else 'test_schema.yaml'
        payload = bytes.fromhex(sys.argv[3]) if len(sys.argv) > 3 else b'\x09\x29\x82\x0C\xE4\x00'
        benchmark_binary_vs_yaml(schema_path, payload)
    else:
        print("Usage: python binary_schema_loader.py benchmark <schema.yaml> [payload_hex]")
