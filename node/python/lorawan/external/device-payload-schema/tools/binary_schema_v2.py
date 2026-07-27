#!/usr/bin/env python3
"""
binary_schema_v2.py - Extended Binary Schema Encoder/Decoder

Extends the OTA binary format (Payload Schema Section 17) to support ALL schema features:
- Bitfields (u8[3:4], u8:2, etc.)
- Match/conditional parsing with cases
- Nested objects
- Lookup tables
- Variables
- All modifiers (mult, div, add)
- Skip type

Binary Format Overview:
    Header:
        - Magic: 2 bytes (0x50 0x53 = "PS")
        - Version: 1 byte
        - Flags: 1 byte
        - String table offset: 2 bytes (from start)
        - Lookup table offset: 2 bytes (from start)
        
    Fields section:
        - Field count: varint
        - Field definitions...
        
    String table (for field names, lookup string values):
        - String count: varint
        - For each: length (varint) + UTF-8 bytes
        
    Lookup tables:
        - Table count: varint
        - For each table: entry count + key/value pairs

Usage:
    from binary_schema_v2 import encode_schema, decode_schema
    
    binary = encode_schema(yaml_schema)
    schema = decode_schema(binary)
"""

import struct
import io
import re
import base64
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple, Union
from enum import IntEnum


# =============================================================================
# Constants
# =============================================================================

MAGIC = b'PS'  # Payload Schema
VERSION = 2

class FieldType(IntEnum):
    """Extended field type codes (4 bits)."""
    UNSIGNED = 0x0
    SIGNED = 0x1
    FLOAT = 0x2
    BYTES = 0x3      # ascii, hex, base64
    BOOL = 0x4
    ENUM = 0x5
    BITFIELD = 0x6
    SKIP = 0x7
    OBJECT = 0x8
    MATCH = 0x9
    LITERAL = 0xA    # constant string/number
    RESERVED = 0xF

class FieldFlags(IntEnum):
    """Field modifier flags."""
    HAS_MULT = 0x01
    HAS_DIV = 0x02
    HAS_ADD = 0x04
    HAS_LOOKUP = 0x08
    HAS_VAR = 0x10
    CONSUME = 0x20
    MERGE = 0x40      # for match: merge results into parent

class HeaderFlags(IntEnum):
    """Header flags."""
    BIG_ENDIAN = 0x01
    HAS_STRINGS = 0x02
    HAS_LOOKUPS = 0x04


# =============================================================================
# Varint encoding (like protobuf)
# =============================================================================

def encode_varint(value: int) -> bytes:
    """Encode integer as varint."""
    result = []
    while value > 127:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value)
    return bytes(result)

def decode_varint(stream: io.BytesIO) -> int:
    """Decode varint from stream."""
    result = 0
    shift = 0
    while True:
        b = stream.read(1)
        if not b:
            raise ValueError("Unexpected end of stream")
        byte = b[0]
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return result

def encode_signed_varint(value: int) -> bytes:
    """Encode signed integer using zigzag encoding."""
    zigzag = (value << 1) ^ (value >> 63)
    return encode_varint(zigzag)

def decode_signed_varint(stream: io.BytesIO) -> int:
    """Decode signed varint using zigzag encoding."""
    zigzag = decode_varint(stream)
    return (zigzag >> 1) ^ -(zigzag & 1)


# =============================================================================
# String Table
# =============================================================================

class StringTable:
    """Manages string interning for compact encoding."""
    
    def __init__(self):
        self.strings: List[str] = []
        self.index: Dict[str, int] = {}
    
    def add(self, s: str) -> int:
        """Add string to table, return index."""
        if s in self.index:
            return self.index[s]
        idx = len(self.strings)
        self.strings.append(s)
        self.index[s] = idx
        return idx
    
    def get(self, idx: int) -> str:
        """Get string by index."""
        return self.strings[idx]
    
    def encode(self) -> bytes:
        """Encode string table to bytes."""
        result = io.BytesIO()
        result.write(encode_varint(len(self.strings)))
        for s in self.strings:
            encoded = s.encode('utf-8')
            result.write(encode_varint(len(encoded)))
            result.write(encoded)
        return result.getvalue()
    
    @classmethod
    def decode(cls, stream: io.BytesIO) -> 'StringTable':
        """Decode string table from stream."""
        table = cls()
        count = decode_varint(stream)
        for _ in range(count):
            length = decode_varint(stream)
            s = stream.read(length).decode('utf-8')
            table.strings.append(s)
            table.index[s] = len(table.strings) - 1
        return table


# =============================================================================
# Lookup Table
# =============================================================================

class LookupTable:
    """Manages lookup table encoding."""
    
    def __init__(self):
        self.tables: List[Dict[int, Any]] = []
        self.index: Dict[int, int] = {}  # hash -> table index
    
    def add(self, lookup: Dict) -> int:
        """Add lookup table, return index."""
        # Convert to normalized form
        normalized = {}
        for k, v in lookup.items():
            key = int(k) if isinstance(k, (int, str)) else k
            normalized[key] = v
        
        # Check if already exists
        h = hash(frozenset(normalized.items()))
        if h in self.index:
            return self.index[h]
        
        idx = len(self.tables)
        self.tables.append(normalized)
        self.index[h] = idx
        return idx
    
    def get(self, idx: int) -> Dict:
        """Get lookup table by index."""
        return self.tables[idx]
    
    def encode(self, strings: StringTable) -> bytes:
        """Encode lookup tables to bytes."""
        result = io.BytesIO()
        result.write(encode_varint(len(self.tables)))
        
        for table in self.tables:
            result.write(encode_varint(len(table)))
            for key, value in sorted(table.items()):
                result.write(encode_signed_varint(key))
                if isinstance(value, str):
                    result.write(bytes([0x01]))  # string type
                    result.write(encode_varint(strings.add(value)))
                else:
                    result.write(bytes([0x00]))  # number type
                    result.write(encode_signed_varint(int(value)))
        
        return result.getvalue()
    
    @classmethod
    def decode(cls, stream: io.BytesIO, strings: StringTable) -> 'LookupTable':
        """Decode lookup tables from stream."""
        tables = cls()
        count = decode_varint(stream)
        
        for _ in range(count):
            entry_count = decode_varint(stream)
            table = {}
            for _ in range(entry_count):
                key = decode_signed_varint(stream)
                value_type = stream.read(1)[0]
                if value_type == 0x01:
                    value = strings.get(decode_varint(stream))
                else:
                    value = decode_signed_varint(stream)
                table[key] = value
            tables.tables.append(table)
        
        return tables


# =============================================================================
# Field Encoder
# =============================================================================

class BinarySchemaEncoder:
    """Encodes full schema to binary format."""
    
    def __init__(self):
        self.strings = StringTable()
        self.lookups = LookupTable()
    
    def _parse_bitfield(self, type_str: str) -> Optional[Tuple[int, int, int]]:
        """Parse bitfield syntax, return (byte_width, start_bit, bit_width)."""
        # u8[3:4] - Python slice
        m = re.match(r'u(\d+)\[(\d+):(\d+)\]', type_str)
        if m:
            byte_width = int(m.group(1)) // 8
            start = int(m.group(2))
            end = int(m.group(3))
            return (byte_width, start, end - start + 1)
        
        # u8[3+:2] - Verilog part-select
        m = re.match(r'u(\d+)\[(\d+)\+:(\d+)\]', type_str)
        if m:
            byte_width = int(m.group(1)) // 8
            start = int(m.group(2))
            width = int(m.group(3))
            return (byte_width, start, width)
        
        # bits<3,2> - C++ template
        m = re.match(r'bits<(\d+),(\d+)>', type_str)
        if m:
            return (1, int(m.group(1)), int(m.group(2)))
        
        # bits:2@3 - @ notation
        m = re.match(r'bits:(\d+)@(\d+)', type_str)
        if m:
            return (1, int(m.group(2)), int(m.group(1)))
        
        # u8:2 - Sequential (simplified)
        m = re.match(r'u(\d+):(\d+)$', type_str)
        if m:
            byte_width = int(m.group(1)) // 8
            width = int(m.group(2))
            return (byte_width, 0, width)
        
        return None
    
    def _get_base_type(self, type_str: str) -> Tuple[FieldType, int]:
        """Get base type and size from type string."""
        type_map = {
            'u8': (FieldType.UNSIGNED, 1),
            'u16': (FieldType.UNSIGNED, 2),
            'u24': (FieldType.UNSIGNED, 3),
            'u32': (FieldType.UNSIGNED, 4),
            'u64': (FieldType.UNSIGNED, 8),
            's8': (FieldType.SIGNED, 1),
            'i8': (FieldType.SIGNED, 1),
            's16': (FieldType.SIGNED, 2),
            'i16': (FieldType.SIGNED, 2),
            's24': (FieldType.SIGNED, 3),
            'i24': (FieldType.SIGNED, 3),
            's32': (FieldType.SIGNED, 4),
            'i32': (FieldType.SIGNED, 4),
            'f16': (FieldType.FLOAT, 2),
            'f32': (FieldType.FLOAT, 4),
            'f64': (FieldType.FLOAT, 8),
            'bool': (FieldType.BOOL, 1),
            'ascii': (FieldType.BYTES, 0),
            'hex': (FieldType.BYTES, 0),
            'base64': (FieldType.BYTES, 0),
            'skip': (FieldType.SKIP, 0),
            'object': (FieldType.OBJECT, 0),
            'match': (FieldType.MATCH, 0),
            'enum': (FieldType.ENUM, 1),
            'string': (FieldType.LITERAL, 0),
            'number': (FieldType.LITERAL, 0),
        }
        return type_map.get(type_str, (FieldType.UNSIGNED, 1))
    
    def _encode_float(self, value: float) -> bytes:
        """Encode float as 4 bytes."""
        return struct.pack('<f', value)
    
    def _encode_field(self, field_def: dict, output: io.BytesIO):
        """Encode a single field definition."""
        field_type = field_def.get('type', 'u8')
        name = field_def.get('name', '')
        
        # Option B: match: as top-level key
        if 'match' in field_def and not field_def.get('type'):
            self._encode_match_option_b(field_def, output)
            return
        
        # Option B: object: as top-level key
        if 'object' in field_def and not field_def.get('type'):
            self._encode_object_option_b(field_def, output)
            return
        
        # Option B: tlv: as top-level key
        if 'tlv' in field_def and not field_def.get('type'):
            self._encode_tlv(field_def, output)
            return
        
        # Check for bitfield
        bitfield = self._parse_bitfield(field_type)
        
        # Handle special types (legacy syntax)
        if field_type == 'match':
            self._encode_match(field_def, output)
            return
        
        if field_type == 'object':
            self._encode_object(field_def, output)
            return
        
        if 'byte_group' in field_def:
            self._encode_byte_group(field_def, output)
            return
        
        # Build flags
        flags = 0
        if field_def.get('mult') is not None:
            flags |= FieldFlags.HAS_MULT
        if field_def.get('div') is not None:
            flags |= FieldFlags.HAS_DIV
        if field_def.get('add') is not None:
            flags |= FieldFlags.HAS_ADD
        if field_def.get('lookup'):
            flags |= FieldFlags.HAS_LOOKUP
        if field_def.get('var'):
            flags |= FieldFlags.HAS_VAR
        if field_def.get('consume') == 1:
            flags |= FieldFlags.CONSUME
        
        if bitfield:
            # Bitfield encoding
            byte_width, start_bit, bit_width = bitfield
            type_byte = (FieldType.BITFIELD << 4) | byte_width
            output.write(bytes([type_byte]))
            output.write(bytes([(start_bit << 4) | bit_width]))
            
            # Flags and name for bitfield
            output.write(bytes([flags]))
            name_idx = self.strings.add(name) if name else 0xFFFF
            output.write(struct.pack('<H', name_idx))
            
            # Optional lookup for bitfield
            if flags & FieldFlags.HAS_LOOKUP:
                lookup_idx = self.lookups.add(field_def['lookup'])
                output.write(encode_varint(lookup_idx))
            
            # Optional variable for bitfield
            if flags & FieldFlags.HAS_VAR:
                var_idx = self.strings.add(field_def['var'])
                output.write(encode_varint(var_idx))
            
            return  # Early return for bitfield
        
        # Standard type
        base_type, size = self._get_base_type(field_type)
        type_byte = (base_type << 4) | (size & 0x0F)
        output.write(bytes([type_byte]))
        
        # Flags
        output.write(bytes([flags]))
        
        # Name index
        name_idx = self.strings.add(name) if name else 0xFFFF
        output.write(struct.pack('<H', name_idx))
        
        # Optional length (for bytes/skip types)
        if field_type in ('ascii', 'hex', 'base64', 'skip'):
            output.write(encode_varint(field_def.get('length', 1)))
        
        # Optional modifiers
        if flags & FieldFlags.HAS_MULT:
            output.write(self._encode_float(field_def['mult']))
        if flags & FieldFlags.HAS_DIV:
            output.write(self._encode_float(field_def['div']))
        if flags & FieldFlags.HAS_ADD:
            output.write(self._encode_float(field_def['add']))
        
        # Optional lookup
        if flags & FieldFlags.HAS_LOOKUP:
            lookup_idx = self.lookups.add(field_def['lookup'])
            output.write(encode_varint(lookup_idx))
        
        # Optional variable name
        if flags & FieldFlags.HAS_VAR:
            var_idx = self.strings.add(field_def['var'])
            output.write(encode_varint(var_idx))
    
    def _encode_object(self, field_def: dict, output: io.BytesIO):
        """Encode nested object."""
        type_byte = (FieldType.OBJECT << 4)
        output.write(bytes([type_byte]))
        
        name = field_def.get('name', '')
        name_idx = self.strings.add(name) if name else 0xFFFF
        output.write(struct.pack('<H', name_idx))
        
        # Encode nested fields
        nested_fields = field_def.get('fields', [])
        output.write(encode_varint(len(nested_fields)))
        for nf in nested_fields:
            self._encode_field(nf, output)
    
    def _encode_byte_group(self, field_def: dict, output: io.BytesIO):
        """Encode byte_group as implicit object."""
        # Encode as special object type
        type_byte = (FieldType.OBJECT << 4) | 0x01  # 0x01 = byte_group marker
        output.write(bytes([type_byte]))
        
        group_size = field_def.get('size', 1)
        output.write(encode_varint(group_size))
        
        nested_fields = field_def.get('byte_group', [])
        output.write(encode_varint(len(nested_fields)))
        for nf in nested_fields:
            self._encode_field(nf, output)
    
    def _encode_match(self, field_def: dict, output: io.BytesIO):
        """Encode match/conditional block."""
        type_byte = (FieldType.MATCH << 4)
        
        # Check for merge flag
        flags = 0
        if field_def.get('merge'):
            flags |= FieldFlags.MERGE
        
        output.write(bytes([type_byte, flags]))
        
        name = field_def.get('name', '')
        name_idx = self.strings.add(name) if name else 0xFFFF
        output.write(struct.pack('<H', name_idx))
        
        # Discriminator
        on = field_def.get('on', '')
        if on.startswith('$'):
            # Variable reference
            var_name = on[1:]
            var_idx = self.strings.add(var_name)
            output.write(bytes([0x01]))  # variable mode
            output.write(encode_varint(var_idx))
        else:
            # Inline byte read
            length = field_def.get('length', 1)
            output.write(bytes([0x00]))  # inline mode
            output.write(encode_varint(length))
        
        # Cases
        cases = field_def.get('cases', [])
        output.write(encode_varint(len(cases)))
        
        for case in cases:
            if 'default' in case:
                # Default case marker
                output.write(bytes([0xFF]))
                default_val = case.get('default')
                if default_val == 'skip':
                    output.write(bytes([0x00]))
                elif default_val == 'error':
                    output.write(bytes([0x01]))
                else:
                    output.write(bytes([0x02]))
            else:
                case_val = case.get('case')
                if isinstance(case_val, list):
                    # Multiple values
                    output.write(bytes([0xFE]))
                    output.write(encode_varint(len(case_val)))
                    for v in case_val:
                        output.write(encode_signed_varint(int(v)))
                else:
                    # Single value
                    output.write(bytes([0x00]))
                    output.write(encode_signed_varint(int(case_val)))
            
            # Case fields
            case_fields = case.get('fields', [])
            output.write(encode_varint(len(case_fields)))
            for cf in case_fields:
                self._encode_field(cf, output)
    
    def _encode_match_option_b(self, field_def: dict, output: io.BytesIO):
        """Encode match using Option B syntax (match: as top-level key)."""
        match_def = field_def.get('match', {})
        type_byte = (FieldType.MATCH << 4)
        
        # Check for merge flag
        flags = 0
        if match_def.get('merge'):
            flags |= FieldFlags.MERGE
        
        output.write(bytes([type_byte, flags]))
        
        name = match_def.get('name', '')
        name_idx = self.strings.add(name) if name else 0xFFFF
        output.write(struct.pack('<H', name_idx))
        
        # Discriminator: field (variable) or length (inline)
        field_ref = match_def.get('field', '')
        if field_ref and field_ref.startswith('$'):
            var_name = field_ref[1:]
            var_idx = self.strings.add(var_name)
            output.write(bytes([0x01]))  # variable mode
            output.write(encode_varint(var_idx))
        else:
            length = match_def.get('length', 1)
            output.write(bytes([0x00]))  # inline mode
            output.write(encode_varint(length))
        
        # Optional var storage for inline match
        if match_def.get('var'):
            var_idx = self.strings.add(match_def['var'])
            output.write(bytes([0x01]))  # has_var marker
            output.write(encode_varint(var_idx))
        else:
            output.write(bytes([0x00]))  # no var
        
        # Cases: dict format {value: [fields], ...}
        cases = match_def.get('cases', {})
        # Separate default from numbered cases
        default_fields = None
        numbered_cases = []
        for case_key, case_fields in cases.items():
            if case_key == 'default':
                default_fields = case_fields
            else:
                numbered_cases.append((case_key, case_fields))
        
        output.write(encode_varint(len(numbered_cases)))
        
        for case_val, case_fields in numbered_cases:
            if isinstance(case_val, list):
                output.write(bytes([0xFE]))
                output.write(encode_varint(len(case_val)))
                for v in case_val:
                    output.write(encode_signed_varint(int(v)))
            else:
                output.write(bytes([0x00]))
                output.write(encode_signed_varint(int(case_val)))
            
            output.write(encode_varint(len(case_fields)))
            for cf in case_fields:
                self._encode_field(cf, output)
        
        # Default case
        if default_fields is not None:
            output.write(bytes([0xFF]))
            if isinstance(default_fields, str):
                if default_fields == 'skip':
                    output.write(bytes([0x00]))
                elif default_fields == 'error':
                    output.write(bytes([0x01]))
                else:
                    output.write(bytes([0x02]))
            elif isinstance(default_fields, list):
                output.write(bytes([0x03]))  # field list default
                output.write(encode_varint(len(default_fields)))
                for df in default_fields:
                    self._encode_field(df, output)
    
    def _encode_object_option_b(self, field_def: dict, output: io.BytesIO):
        """Encode object using Option B syntax (object: as top-level key)."""
        type_byte = (FieldType.OBJECT << 4)
        output.write(bytes([type_byte]))
        
        name = field_def.get('object', '')
        name_idx = self.strings.add(name) if name else 0xFFFF
        output.write(struct.pack('<H', name_idx))
        
        nested_fields = field_def.get('fields', [])
        output.write(encode_varint(len(nested_fields)))
        for nf in nested_fields:
            self._encode_field(nf, output)
    
    def _encode_tlv(self, field_def: dict, output: io.BytesIO):
        """Encode TLV using Option B syntax (tlv: as top-level key)."""
        tlv_def = field_def.get('tlv', {})
        
        # TLV opcode
        output.write(bytes([0x71]))
        
        # TLV Flags
        tag_size = tlv_def.get('tag_size', 1)
        length_size = tlv_def.get('length_size', 0)
        tag_fields = tlv_def.get('tag_fields')
        unknown_mode = tlv_def.get('unknown', 'skip')
        
        tlv_flags = (length_size & 0x07)
        if tag_fields:
            tlv_flags |= 0x08  # composite_tag
        
        # Check if case values need 16-bit
        cases = tlv_def.get('cases', {})
        wide = False
        for case_key in cases:
            if case_key == 'default':
                continue
            if isinstance(case_key, (list, tuple)):
                wide = True
                break
            if isinstance(case_key, int) and case_key > 255:
                wide = True
                break
        if wide:
            tlv_flags |= 0x10  # wide_value
        
        if unknown_mode != 'skip':
            tlv_flags |= 0x20  # has_unknown
            mode_map = {'skip': 0, 'error': 1, 'raw': 2}
            tlv_flags |= (mode_map.get(unknown_mode, 0) << 6)
        
        output.write(bytes([tlv_flags]))
        output.write(bytes([tag_size]))
        
        # Numbered cases (excluding default)
        numbered_cases = [(k, v) for k, v in cases.items() if k != 'default']
        output.write(bytes([len(numbered_cases)]))
        
        # Composite tag descriptor
        if tag_fields:
            output.write(bytes([len(tag_fields)]))
            for tf in tag_fields:
                tf_type = tf.get('type', 'u8')
                tf_size = {'u8': 1, 'u16': 2, 'u32': 4}.get(tf_type, 1)
                output.write(bytes([tf_size]))
        
        # Cases
        for case_key, case_fields in numbered_cases:
            if isinstance(case_key, (list, tuple)):
                # Composite key: concatenate as big-endian
                for v in case_key:
                    if wide:
                        output.write(struct.pack('>H', int(v)))
                    else:
                        output.write(bytes([int(v)]))
            else:
                if wide:
                    output.write(struct.pack('>H', int(case_key)))
                else:
                    output.write(bytes([int(case_key)]))
            
            output.write(bytes([len(case_fields)]))
            for cf in case_fields:
                self._encode_field(cf, output)
    
    def _collect_strings_from_lookup(self, lookup: Dict):
        """Pre-add lookup string values to string table."""
        for v in lookup.values():
            if isinstance(v, str):
                self.strings.add(v)
    
    def _collect_all_strings(self, fields: List[dict]):
        """Recursively collect all strings from fields before encoding."""
        for f in fields:
            # Field name
            if f.get('name'):
                self.strings.add(f['name'])
            # Variable
            if f.get('var'):
                self.strings.add(f['var'])
            # Lookup values
            if f.get('lookup'):
                self._collect_strings_from_lookup(f['lookup'])
            # Nested object fields (legacy)
            if f.get('type') == 'object' and f.get('fields'):
                self._collect_all_strings(f['fields'])
            # Byte group fields
            if f.get('byte_group'):
                self._collect_all_strings(f['byte_group'])
            # Match cases (legacy)
            if f.get('type') == 'match':
                for case in f.get('cases', []):
                    if case.get('fields'):
                        self._collect_all_strings(case['fields'])
            # Option B: match: as top-level key
            if 'match' in f and not f.get('type'):
                match_def = f['match']
                if isinstance(match_def, dict):
                    if match_def.get('name'):
                        self.strings.add(match_def['name'])
                    if match_def.get('var'):
                        self.strings.add(match_def['var'])
                    if match_def.get('field', '').startswith('$'):
                        self.strings.add(match_def['field'][1:])
                    for case_key, case_fields in match_def.get('cases', {}).items():
                        if isinstance(case_fields, list):
                            self._collect_all_strings(case_fields)
            # Option B: object: as top-level key
            if 'object' in f and not f.get('type'):
                if f.get('object'):
                    self.strings.add(f['object'])
                if f.get('fields'):
                    self._collect_all_strings(f['fields'])
            # Option B: tlv: as top-level key
            if 'tlv' in f and not f.get('type'):
                tlv_def = f['tlv']
                if isinstance(tlv_def, dict):
                    for case_key, case_fields in tlv_def.get('cases', {}).items():
                        if isinstance(case_fields, list):
                            self._collect_all_strings(case_fields)
    
    def encode(self, schema: dict) -> bytes:
        """Encode complete schema to binary."""
        self.strings = StringTable()
        self.lookups = LookupTable()
        
        # Add schema name to string table
        schema_name = schema.get('name', 'unknown')
        self.strings.add(schema_name)
        
        # Pre-collect ALL strings first (including lookup values)
        fields = schema.get('fields', [])
        self._collect_all_strings(fields)
        
        # Now encode fields to buffer
        fields_buf = io.BytesIO()
        fields_buf.write(encode_varint(len(fields)))
        for f in fields:
            self._encode_field(f, fields_buf)
        fields_data = fields_buf.getvalue()
        
        # Encode string table (now contains all strings)
        strings_data = self.strings.encode()
        
        # Encode lookup tables (string indices are already in table)
        lookups_data = self.lookups.encode(self.strings)
        
        # Build header
        header_flags = HeaderFlags.HAS_STRINGS | HeaderFlags.HAS_LOOKUPS
        if schema.get('endian', 'big') == 'big':
            header_flags |= HeaderFlags.BIG_ENDIAN
        
        # Calculate offsets
        header_size = 2 + 1 + 1 + 2 + 2  # magic + version + flags + 2 offsets
        fields_offset = header_size
        strings_offset = fields_offset + len(fields_data)
        lookups_offset = strings_offset + len(strings_data)
        
        # Build final binary
        result = io.BytesIO()
        result.write(MAGIC)
        result.write(bytes([VERSION, header_flags]))
        result.write(struct.pack('<HH', strings_offset, lookups_offset))
        result.write(fields_data)
        result.write(strings_data)
        result.write(lookups_data)
        
        return result.getvalue()
    
    def encode_to_base64(self, schema: dict, url_safe: bool = True) -> str:
        """Encode schema to base64 string."""
        binary = self.encode(schema)
        if url_safe:
            return base64.urlsafe_b64encode(binary).decode('ascii').rstrip('=')
        return base64.b64encode(binary).decode('ascii')


# =============================================================================
# Field Decoder
# =============================================================================

class BinarySchemaDecoder:
    """Decodes binary schema back to dict format."""
    
    def __init__(self):
        self.strings: Optional[StringTable] = None
        self.lookups: Optional[LookupTable] = None
        self.big_endian = True
    
    def _decode_field(self, stream: io.BytesIO) -> dict:
        """Decode a single field from stream."""
        type_byte = stream.read(1)[0]
        field_type = FieldType((type_byte >> 4) & 0x0F)
        size = type_byte & 0x0F
        
        if field_type == FieldType.MATCH:
            return self._decode_match(stream)
        
        if field_type == FieldType.OBJECT:
            if size == 0x01:
                return self._decode_byte_group(stream)
            return self._decode_object(stream)
        
        if field_type == FieldType.BITFIELD:
            return self._decode_bitfield(stream, size)
        
        # Standard field
        flags = stream.read(1)[0]
        name_idx = struct.unpack('<H', stream.read(2))[0]
        name = self.strings.get(name_idx) if name_idx != 0xFFFF else None
        
        # Type string
        type_str = self._get_type_string(field_type, size)
        
        field = {'type': type_str}
        if name:
            field['name'] = name
        
        # Optional length
        if field_type in (FieldType.BYTES, FieldType.SKIP):
            field['length'] = decode_varint(stream)
        
        # Modifiers
        if flags & FieldFlags.HAS_MULT:
            field['mult'] = struct.unpack('<f', stream.read(4))[0]
        if flags & FieldFlags.HAS_DIV:
            field['div'] = struct.unpack('<f', stream.read(4))[0]
        if flags & FieldFlags.HAS_ADD:
            field['add'] = struct.unpack('<f', stream.read(4))[0]
        if flags & FieldFlags.HAS_LOOKUP:
            lookup_idx = decode_varint(stream)
            field['lookup'] = self.lookups.get(lookup_idx)
        if flags & FieldFlags.HAS_VAR:
            var_idx = decode_varint(stream)
            field['var'] = self.strings.get(var_idx)
        if flags & FieldFlags.CONSUME:
            field['consume'] = 1
        
        return field
    
    def _decode_bitfield(self, stream: io.BytesIO, byte_width: int) -> dict:
        """Decode bitfield."""
        bit_info = stream.read(1)[0]
        start_bit = (bit_info >> 4) & 0x0F
        bit_width = bit_info & 0x0F
        
        # Note: For bitfields, we read flags and name after bit_info
        # But the encoder writes: type_byte, bit_info, flags, name
        # Actually looking at encoder, it writes flags after type for standard fields
        # For bitfield it's: type_byte, bit_info - need to add flags/name
        
        # Read flags and name (added in encoder for bitfields too)
        flags = stream.read(1)[0]
        name_idx = struct.unpack('<H', stream.read(2))[0]
        name = self.strings.get(name_idx) if name_idx != 0xFFFF else None
        
        field = {
            'type': f'u8[{start_bit}:{start_bit + bit_width - 1}]'
        }
        if name:
            field['name'] = name
        
        if flags & FieldFlags.CONSUME:
            field['consume'] = 1
        
        # Check for additional modifiers
        if flags & FieldFlags.HAS_LOOKUP:
            lookup_idx = decode_varint(stream)
            field['lookup'] = self.lookups.get(lookup_idx)
        if flags & FieldFlags.HAS_VAR:
            var_idx = decode_varint(stream)
            field['var'] = self.strings.get(var_idx)
        
        return field
    
    def _decode_object(self, stream: io.BytesIO) -> dict:
        """Decode nested object."""
        name_idx = struct.unpack('<H', stream.read(2))[0]
        name = self.strings.get(name_idx) if name_idx != 0xFFFF else None
        
        field_count = decode_varint(stream)
        fields = [self._decode_field(stream) for _ in range(field_count)]
        
        obj = {'type': 'object', 'fields': fields}
        if name:
            obj['name'] = name
        return obj
    
    def _decode_byte_group(self, stream: io.BytesIO) -> dict:
        """Decode byte_group."""
        group_size = decode_varint(stream)
        field_count = decode_varint(stream)
        fields = [self._decode_field(stream) for _ in range(field_count)]
        
        return {'byte_group': fields, 'size': group_size}
    
    def _decode_match(self, stream: io.BytesIO) -> dict:
        """Decode match block."""
        flags = stream.read(1)[0]
        
        name_idx = struct.unpack('<H', stream.read(2))[0]
        name = self.strings.get(name_idx) if name_idx != 0xFFFF else None
        
        # Discriminator
        mode = stream.read(1)[0]
        if mode == 0x01:
            var_idx = decode_varint(stream)
            on = '$' + self.strings.get(var_idx)
        else:
            length = decode_varint(stream)
            on = None  # inline
        
        # Cases
        case_count = decode_varint(stream)
        cases = []
        
        for _ in range(case_count):
            case_type = stream.read(1)[0]
            
            case_def = {}
            if case_type == 0xFF:
                # Default
                default_mode = stream.read(1)[0]
                if default_mode == 0x00:
                    case_def['default'] = 'skip'
                elif default_mode == 0x01:
                    case_def['default'] = 'error'
                else:
                    case_def['default'] = True
            elif case_type == 0xFE:
                # Multiple values
                val_count = decode_varint(stream)
                case_def['case'] = [decode_signed_varint(stream) for _ in range(val_count)]
            else:
                # Single value
                case_def['case'] = decode_signed_varint(stream)
            
            # Case fields
            field_count = decode_varint(stream)
            case_def['fields'] = [self._decode_field(stream) for _ in range(field_count)]
            cases.append(case_def)
        
        match = {'type': 'match', 'cases': cases}
        if name:
            match['name'] = name
        if on:
            match['on'] = on
        if flags & FieldFlags.MERGE:
            match['merge'] = True
        
        return match
    
    def _get_type_string(self, field_type: FieldType, size: int) -> str:
        """Convert field type and size to type string."""
        if field_type == FieldType.UNSIGNED:
            return {1: 'u8', 2: 'u16', 3: 'u24', 4: 'u32', 8: 'u64'}.get(size, 'u8')
        if field_type == FieldType.SIGNED:
            return {1: 's8', 2: 's16', 3: 's24', 4: 's32', 8: 's64'}.get(size, 's8')
        if field_type == FieldType.FLOAT:
            return {2: 'f16', 4: 'f32', 8: 'f64'}.get(size, 'f32')
        if field_type == FieldType.BOOL:
            return 'bool'
        if field_type == FieldType.BYTES:
            return 'ascii'
        if field_type == FieldType.SKIP:
            return 'skip'
        if field_type == FieldType.ENUM:
            return 'enum'
        return 'u8'
    
    def decode(self, data: bytes) -> dict:
        """Decode binary schema to dict."""
        stream = io.BytesIO(data)
        
        # Read header
        magic = stream.read(2)
        if magic != MAGIC:
            raise ValueError(f"Invalid magic: {magic}")
        
        version = stream.read(1)[0]
        flags = stream.read(1)[0]
        strings_offset, lookups_offset = struct.unpack('<HH', stream.read(4))
        
        self.big_endian = bool(flags & HeaderFlags.BIG_ENDIAN)
        
        # Save fields start position
        fields_start = stream.tell()
        
        # Jump to string table first
        stream.seek(strings_offset)
        self.strings = StringTable.decode(stream)
        
        # Jump to lookup tables
        stream.seek(lookups_offset)
        self.lookups = LookupTable.decode(stream, self.strings)
        
        # Go back and decode fields
        stream.seek(fields_start)
        field_count = decode_varint(stream)
        
        fields = [self._decode_field(stream) for _ in range(field_count)]
        
        schema = {
            'name': self.strings.get(0) if self.strings.strings else 'unknown',
            'version': version,
            'endian': 'big' if self.big_endian else 'little',
            'fields': fields,
        }
        
        return schema
    
    def decode_from_base64(self, encoded: str) -> dict:
        """Decode base64 string to schema dict."""
        # Handle URL-safe base64 without padding
        padding = 4 - (len(encoded) % 4)
        if padding != 4:
            encoded += '=' * padding
        
        try:
            binary = base64.urlsafe_b64decode(encoded)
        except Exception:
            binary = base64.b64decode(encoded)
        
        return self.decode(binary)


# =============================================================================
# Convenience Functions
# =============================================================================

def encode_schema(schema: dict) -> bytes:
    """Encode schema dict to binary bytes."""
    return BinarySchemaEncoder().encode(schema)

def decode_schema(data: bytes) -> dict:
    """Decode binary bytes to schema dict."""
    return BinarySchemaDecoder().decode(data)

def schema_to_base64(schema: dict, url_safe: bool = True) -> str:
    """Encode schema dict to base64 string."""
    return BinarySchemaEncoder().encode_to_base64(schema, url_safe=url_safe)

def base64_to_schema(encoded: str) -> dict:
    """Decode base64 string to schema dict."""
    return BinarySchemaDecoder().decode_from_base64(encoded)


# =============================================================================
# CLI
# =============================================================================

if __name__ == '__main__':
    import yaml
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Binary Schema Encoder/Decoder v2')
    parser.add_argument('input', nargs='?', help='Input schema file (YAML/JSON)')
    parser.add_argument('-o', '--output', help='Output file')
    parser.add_argument('-d', '--decode', action='store_true', help='Decode binary to YAML')
    parser.add_argument('-b', '--base64', action='store_true', help='Output as base64')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if not args.input:
        # Demo mode
        print("=== Binary Schema Encoder v2 Demo ===\n")
        
        example_schema = {
            'name': 'demo_sensor',
            'endian': 'big',
            'fields': [
                {'name': 'version', 'type': 'u8[4:7]'},
                {'name': 'counter', 'type': 'u8[0:3]', 'consume': 1},
                {'name': 'event', 'type': 'u8', 'var': 'evt', 
                 'lookup': {0: 'reset', 1: 'data', 2: 'alarm'}},
                {'name': 'payload', 'type': 'match', 'on': '$evt', 'merge': True,
                 'cases': [
                     {'case': 0, 'fields': [
                         {'name': 'device_id', 'type': 'u16'}
                     ]},
                     {'case': 1, 'fields': [
                         {'name': 'temperature', 'type': 's16', 'div': 100},
                         {'name': 'humidity', 'type': 'u8', 'mult': 0.5}
                     ]},
                     {'default': 'skip'}
                 ]}
            ]
        }
        
        print(f"Schema: {example_schema['name']}")
        print(f"Fields: {len(example_schema['fields'])}")
        
        binary = encode_schema(example_schema)
        print(f"\nBinary ({len(binary)} bytes):")
        print(' '.join(f'{b:02X}' for b in binary))
        
        b64 = schema_to_base64(example_schema)
        print(f"\nBase64 ({len(b64)} chars):")
        print(b64)
        
        # Decode back
        decoded = decode_schema(binary)
        print(f"\nDecoded schema:")
        print(yaml.dump(decoded, default_flow_style=False))
        
        sys.exit(0)
    
    # Process input file
    from pathlib import Path
    input_path = Path(args.input)
    
    if args.decode:
        # Decode binary to YAML
        if input_path.suffix == '.b64':
            schema = base64_to_schema(input_path.read_text().strip())
        else:
            schema = decode_schema(input_path.read_bytes())
        
        output = yaml.dump(schema, default_flow_style=False)
        if args.output:
            Path(args.output).write_text(output)
        else:
            print(output)
    else:
        # Encode YAML to binary
        content = input_path.read_text()
        if input_path.suffix in ['.yaml', '.yml']:
            schema = yaml.safe_load(content)
        else:
            import json
            schema = json.loads(content)
        
        binary = encode_schema(schema)
        
        if args.verbose:
            print(f"Schema: {schema.get('name', 'unknown')}", file=sys.stderr)
            print(f"Fields: {len(schema.get('fields', []))}", file=sys.stderr)
            print(f"Binary size: {len(binary)} bytes", file=sys.stderr)
        
        if args.base64:
            output = schema_to_base64(schema)
            if args.output:
                Path(args.output).write_text(output)
            else:
                print(output)
        else:
            if args.output:
                Path(args.output).write_bytes(binary)
            else:
                sys.stdout.buffer.write(binary)
