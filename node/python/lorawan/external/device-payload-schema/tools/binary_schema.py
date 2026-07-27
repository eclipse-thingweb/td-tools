#!/usr/bin/env python3
"""
binary_schema.py - Binary Schema Encoder/Decoder for OTA Schema Transfer

Implements the compact binary schema format defined in Payload Schema Section 17.

Design Rationale
----------------
Two format versions serve distinct roles in the LoRaWAN ecosystem:

Version 1 (flat fields only):
    - Device-side uplink encoding: device walks 4-byte records to pack
      sensor readings into a payload. Trivial C implementation (~20 lines).
    - Fixed 4 bytes per field: type(1) + mult_exp(1) + semantic_id(2).
      Enables constant-time field access: schema[2 + i*4].
    - No string table, no variable-length records, no heap allocation.

Version 2 (structural constructs):
    - Network-side schema parsing: the network uses MATCH records to
      understand the device's multi-message uplink format and downlink
      command set, enabling generic codec without custom JavaScript.
    - Data fields remain 4 bytes (same layout as v1). Only structural
      opcodes (MATCH, VAR) introduce variable-length records.
    - The device stores and transmits v2 schemas but does not need to
      parse structural opcodes — they are opaque bytes from the device's
      perspective. The device only parses the v1 flat portion for its
      own uplink encoding.

Why devices don't need MATCH for downlink:
    - Downlink command handlers are hardcoded in device firmware.
      A generic MATCH parser adds 200-500 bytes of code without
      removing the application switch/dispatch logic.
    - Byte extraction (the part MATCH replaces) is 1-2 lines of C per
      field — trivial. The complex part is the command-specific action
      (set_interval, configure_threshold, etc.) which is custom either way.
    - The MATCH schema documents the command set for the network's
      benefit, not the device's.

Binary Format (Version 1):
    Header (2 bytes): version(0x01) + field_count
    Per Field (4 bytes): type_byte + mult_exp + semantic_id(LE)

Binary Format (Version 2):
    Header (3 bytes): version(0x02) + flags + record_count
    Records: data fields (4 bytes each) + structural opcodes (variable)

Usage:
    from binary_schema import BinarySchemaEncoder, BinarySchemaDecoder

    # Encode schema to binary (auto-selects v1 or v2)
    encoder = BinarySchemaEncoder()
    binary = encoder.encode(yaml_schema)

    # Decode binary back to schema
    decoder = BinarySchemaDecoder()
    schema = decoder.decode(binary)
"""

import struct
import math
import base64
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import IntEnum


class FieldType(IntEnum):
    """Binary field type codes (4 bits)."""
    UNSIGNED = 0x0
    SIGNED = 0x1
    FLOAT = 0x2
    BYTES = 0x3
    BOOL = 0x4
    ENUM = 0x5
    BITFIELD = 0x6
    STRUCTURAL = 0x7  # Structural construct prefix


# Structural construct opcodes (type nibble = 0x7)
OPCODE_MATCH = 0x70
OPCODE_TLV = 0x71
OPCODE_OBJECT = 0x72
OPCODE_VAR = 0x73
OPCODE_END = 0x74


# Map schema type strings to (FieldType, size_bytes)
TYPE_MAP = {
    'u8': (FieldType.UNSIGNED, 1),
    'u16': (FieldType.UNSIGNED, 2),
    'u24': (FieldType.UNSIGNED, 3),
    'u32': (FieldType.UNSIGNED, 4),
    'u64': (FieldType.UNSIGNED, 8),
    'i8': (FieldType.SIGNED, 1),
    's8': (FieldType.SIGNED, 1),
    'i16': (FieldType.SIGNED, 2),
    's16': (FieldType.SIGNED, 2),
    'i24': (FieldType.SIGNED, 3),
    's24': (FieldType.SIGNED, 3),
    'i32': (FieldType.SIGNED, 4),
    's32': (FieldType.SIGNED, 4),
    'i64': (FieldType.SIGNED, 8),
    's64': (FieldType.SIGNED, 8),
    'f32': (FieldType.FLOAT, 4),
    'f64': (FieldType.FLOAT, 8),
    'bool': (FieldType.BOOL, 1),
}

# Reverse map for decoding
SIZE_TO_TYPE = {
    (FieldType.UNSIGNED, 1): 'u8',
    (FieldType.UNSIGNED, 2): 'u16',
    (FieldType.UNSIGNED, 3): 'u24',
    (FieldType.UNSIGNED, 4): 'u32',
    (FieldType.UNSIGNED, 8): 'u64',
    (FieldType.SIGNED, 1): 's8',
    (FieldType.SIGNED, 2): 's16',
    (FieldType.SIGNED, 3): 's24',
    (FieldType.SIGNED, 4): 's32',
    (FieldType.SIGNED, 8): 's64',
    (FieldType.FLOAT, 4): 'f32',
    (FieldType.FLOAT, 8): 'f64',
    (FieldType.BOOL, 1): 'bool',
}


@dataclass
class BinaryField:
    """Represents a field in binary schema format."""
    type_code: FieldType
    size: int
    mult_exponent: int = 0
    semantic_id: int = 0
    name: Optional[str] = None
    
    def to_bytes(self) -> bytes:
        """Encode field to 4 bytes."""
        type_byte = (self.type_code << 4) | (self.size & 0x0F)
        return struct.pack('<BBH', type_byte, 
                          self.mult_exponent & 0xFF, 
                          self.semantic_id)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'BinaryField':
        """Decode field from 4 bytes."""
        if len(data) < 4:
            raise ValueError(f"Need 4 bytes, got {len(data)}")
        
        type_byte, mult_exp, semantic_id = struct.unpack('<BBH', data[:4])
        type_code = FieldType((type_byte >> 4) & 0x0F)
        size = type_byte & 0x0F
        
        # Convert signed exponent
        if mult_exp > 127:
            mult_exp = mult_exp - 256
        
        return cls(type_code=type_code, size=size, 
                  mult_exponent=mult_exp, semantic_id=semantic_id)


@dataclass
class BinarySchema:
    """Binary-encoded schema structure.
    
    Version 1: flat fields only (2-byte header + 4 bytes per field)
    Version 2: structural constructs (3-byte header + variable records)
    
    For v2, the `records` field contains raw pre-encoded record bytes.
    For v1, `fields` contains BinaryField objects (backward compat).
    """
    version: int = 1
    fields: List[BinaryField] = field(default_factory=list)
    records: Optional[bytes] = None  # v2: raw record bytes
    flags: int = 0  # v2: header flags (bit 0 = little-endian)
    record_count: int = 0  # v2: top-level record count
    
    def to_bytes(self) -> bytes:
        """Encode complete schema to bytes."""
        if self.version >= 2 and self.records is not None:
            # Version 2: 3-byte header + raw records
            header = struct.pack('BBB', self.version, self.flags,
                                self.record_count)
            return header + self.records
        
        # Version 1: 2-byte header + 4-byte fields
        header = struct.pack('BB', self.version, len(self.fields))
        field_data = b''.join(f.to_bytes() for f in self.fields)
        return header + field_data
    
    def to_base64(self, url_safe: bool = True) -> str:
        """Encode schema to base64 string."""
        binary = self.to_bytes()
        if url_safe:
            return base64.urlsafe_b64encode(binary).decode('ascii').rstrip('=')
        return base64.b64encode(binary).decode('ascii')
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'BinarySchema':
        """Decode schema from bytes."""
        if len(data) < 2:
            raise ValueError("Schema too short")
        
        version = data[0]
        
        if version >= 2:
            # Version 2: 3-byte header
            if len(data) < 3:
                raise ValueError("Schema too short for v2 header")
            flags = data[1]
            record_count = data[2]
            return cls(version=version, flags=flags,
                      record_count=record_count, records=data[3:])
        
        # Version 1: 2-byte header + flat fields
        count = data[1]
        fields = []
        pos = 2
        for _ in range(count):
            if pos + 4 > len(data):
                raise ValueError("Truncated field data")
            f = BinaryField.from_bytes(data[pos:pos+4])
            fields.append(f)
            pos += 4
        
        return cls(version=version, fields=fields)
    
    @classmethod
    def from_base64(cls, encoded: str) -> 'BinarySchema':
        """Decode schema from base64 string."""
        # Handle URL-safe base64 without padding
        padding = 4 - (len(encoded) % 4)
        if padding != 4:
            encoded += '=' * padding
        
        # Try URL-safe first, then standard
        try:
            binary = base64.urlsafe_b64decode(encoded)
        except Exception:
            binary = base64.b64decode(encoded)
        
        return cls.from_bytes(binary)


class BinarySchemaEncoder:
    """Encodes YAML/dict schemas to binary format."""
    
    def __init__(self):
        self.special_multipliers = {
            0.5: (-1, True),   # Encoded as 10^-1 with flag
            0.25: (-2, True),  # Encoded as 10^-2 with special handling
        }
    
    def _parse_type(self, type_str: str) -> Tuple[FieldType, int]:
        """Parse schema type string to (FieldType, size)."""
        # Handle bitfield shorthand: u8[3:4], u8:2, bits<3,2>, etc.
        if '[' in type_str or ':' in type_str or '<' in type_str:
            return FieldType.BITFIELD, 1
        
        if type_str in TYPE_MAP:
            return TYPE_MAP[type_str]
        
        raise ValueError(f"Unknown type: {type_str}")
    
    def _mult_to_exponent(self, mult: float) -> int:
        """Convert multiplier to exponent (mult = 10^exp)."""
        if mult is None or mult == 1.0:
            return 0
        
        if mult == 0:
            return 0
        
        # Handle special non-power-of-10 multipliers
        if mult == 0.5:
            return 0xFF  # Special encoding for 0.5
        
        # Calculate log10
        try:
            exp = math.log10(mult)
            # Check if it's close to an integer
            rounded = round(exp)
            if abs(exp - rounded) < 0.001:
                # Clamp to signed byte range
                return max(-128, min(127, rounded))
        except (ValueError, OverflowError):
            pass
        
        return 0
    
    def _get_semantic_id(self, field_def: dict) -> int:
        """Extract semantic ID (IPSO) from field definition."""
        semantic = field_def.get('semantic', {})
        if isinstance(semantic, dict):
            return semantic.get('ipso', 0)
        return 0
    
    def encode_field(self, field_def: dict) -> BinaryField:
        """Encode a single field definition to binary format."""
        field_type = field_def.get('type', 'u8')
        type_code, size = self._parse_type(field_type)
        
        mult = field_def.get('mult', 1.0)
        mult_exp = self._mult_to_exponent(mult)
        
        semantic_id = self._get_semantic_id(field_def)
        
        return BinaryField(
            type_code=type_code,
            size=size,
            mult_exponent=mult_exp,
            semantic_id=semantic_id,
            name=field_def.get('name')
        )
    
    def _has_structural(self, schema: dict) -> bool:
        """Check if schema contains structural constructs."""
        for field_def in schema.get('fields', []):
            field_type = field_def.get('type', '')
            if field_type in ('match', 'object'):
                return True
            if 'match' in field_def and not field_def.get('type'):
                return True
            if 'object' in field_def and not field_def.get('type'):
                return True
            if 'tlv' in field_def and not field_def.get('type'):
                return True
        return False
    
    def _encode_data_field(self, field_def: dict) -> bytes:
        """Encode a single data field to exactly 4 bytes (compact format).
        
        Fixed 4-byte record: [type_byte, mult_exp, semantic_id_lo, semantic_id_hi]
        Same layout as v1 BinaryField — always 4 bytes, no variable-length
        extensions. This keeps the format trivially parseable on constrained
        devices (just walk 4-byte records).
        
        The mult_exponent byte encodes the multiplier as 10^exp (signed byte).
        """
        field_type = field_def.get('type', 'u8')
        type_code, size = self._parse_type(field_type)
        
        mult = field_def.get('mult', 1.0)
        div = field_def.get('div')
        if div is not None and div != 0:
            mult = 1.0 / div
        
        mult_exp = self._mult_to_exponent(mult)
        semantic_id = self._get_semantic_id(field_def)
        
        type_byte = (type_code << 4) | (size & 0x0F)
        return struct.pack('<BBH', type_byte, mult_exp & 0xFF, semantic_id)
    
    def _encode_var_record(self) -> bytes:
        """Encode a VAR opcode (1 byte)."""
        return bytes([OPCODE_VAR])
    
    def _encode_match_record(self, match_def: dict) -> bytes:
        """Encode a MATCH record (section 17 compact format).
        
        MATCH: 0x70 + flags(1) + case_count(1) + case entries
        """
        out = bytearray()
        out.append(OPCODE_MATCH)
        
        # Build flags
        flags = 0
        field_ref = match_def.get('field', '')
        length = match_def.get('length')
        cases = match_def.get('cases', {})
        default = match_def.get('default')
        
        # Separate default from numbered cases
        default_fields = None
        numbered_cases = []
        for case_key, case_fields in cases.items():
            if case_key == 'default':
                default_fields = case_fields
            else:
                numbered_cases.append((int(case_key), case_fields))
        
        if default is not None or default_fields is not None:
            flags |= 0x40  # has_default
        
        # Check if any case value > 255
        wide = any(v > 255 for v, _ in numbered_cases)
        if wide:
            flags |= 0x20  # wide_value
        
        if length is not None:
            # Inline mode
            flags |= 0x10  # inline bit
        elif field_ref.startswith('$'):
            # Variable-based mode: field_ref index in bits 0-3
            # Variable index is auto-assigned; we use the index directly
            var_idx = getattr(self, '_var_index_map', {}).get(
                field_ref[1:], 0)
            flags |= (var_idx & 0x0F)
        
        out.append(flags)
        out.append(len(numbered_cases))
        
        # Case entries
        for case_val, case_fields in numbered_cases:
            if wide:
                out.extend(struct.pack('<H', case_val))
            else:
                out.append(case_val & 0xFF)
            
            # Encode case fields
            encoded_fields = []
            for cf in case_fields:
                encoded_fields.append(self._encode_data_field(cf))
            
            out.append(len(encoded_fields))
            for ef in encoded_fields:
                out.extend(ef)
        
        # Default case (no value byte, just field_count + fields)
        if flags & 0x40:
            if isinstance(default_fields, list) and default_fields:
                encoded_defaults = [self._encode_data_field(df)
                                   for df in default_fields]
                out.append(len(encoded_defaults))
                for ed in encoded_defaults:
                    out.extend(ed)
            elif default == 'skip' or default_fields == 'skip':
                out.append(0)  # 0 fields = skip
            elif default == 'error' or default_fields == 'error':
                out.append(0xFF)  # 0xFF = error marker
            else:
                out.append(0)
        
        return bytes(out)
    
    def _encode_v2_records(self, schema: dict) -> Tuple[bytes, int]:
        """Encode all records for v2 format.
        
        Returns (record_bytes, top_level_record_count).
        """
        out = bytearray()
        record_count = 0
        self._var_counter = 0
        self._var_index_map = {}
        
        for field_def in schema.get('fields', []):
            # Skip internal fields
            name = field_def.get('name', '')
            if name.startswith('_'):
                continue
            
            # Option B: match: as top-level key
            if 'match' in field_def and not field_def.get('type'):
                match_def = field_def['match']
                out.extend(self._encode_match_record(match_def))
                record_count += 1
                continue
            
            # Legacy: type: match
            field_type = field_def.get('type', 'u8')
            if field_type == 'match':
                # Convert legacy to match_def format
                match_def = {
                    'cases': {},
                    'default': field_def.get('default'),
                }
                on = field_def.get('on', '')
                if on.startswith('$'):
                    match_def['field'] = on
                else:
                    match_def['length'] = 1
                # Convert legacy case list to dict
                for case in field_def.get('cases', []):
                    if 'default' in case:
                        match_def['default'] = case['default']
                    elif 'case' in case:
                        match_def['cases'][case['case']] = case.get(
                            'fields', [])
                out.extend(self._encode_match_record(match_def))
                record_count += 1
                continue
            
            # Skip unsupported complex types
            if field_type in ('object',):
                continue
            if 'object' in field_def or 'tlv' in field_def:
                continue
            
            # Data field
            out.extend(self._encode_data_field(field_def))
            record_count += 1
            
            # VAR record follows if field has var:
            if field_def.get('var'):
                var_name = field_def['var']
                self._var_index_map[var_name] = self._var_counter
                self._var_counter += 1
                out.extend(self._encode_var_record())
                # VAR doesn't count as a top-level record (it's a modifier)
        
        return bytes(out), record_count
    
    def encode(self, schema: dict) -> BinarySchema:
        """Encode complete schema dict to binary schema.
        
        Automatically selects v1 (flat) or v2 (structural) format:
        - v1: flat sequential fields, 2-byte header, 4 bytes/field
        - v2: includes MATCH/VAR opcodes, 3-byte header
        """
        if self._has_structural(schema):
            # Version 2: structural constructs
            flags = 0
            if schema.get('endian', 'big') == 'little':
                flags |= 0x01
            
            records_data, record_count = self._encode_v2_records(schema)
            
            return BinarySchema(
                version=2,
                flags=flags,
                record_count=record_count,
                records=records_data,
            )
        
        # Version 1: flat fields only
        fields = []
        for field_def in schema.get('fields', []):
            name = field_def.get('name', '')
            if name.startswith('_'):
                continue
            
            field_type = field_def.get('type', 'u8')
            if field_type in ('match', 'object'):
                continue
            
            binary_field = self.encode_field(field_def)
            fields.append(binary_field)
        
        return BinarySchema(version=1, fields=fields)
    
    def encode_to_bytes(self, schema: dict) -> bytes:
        """Convenience method: encode schema directly to bytes."""
        return self.encode(schema).to_bytes()
    
    def encode_to_base64(self, schema: dict, url_safe: bool = True) -> str:
        """Convenience method: encode schema directly to base64."""
        return self.encode(schema).to_base64(url_safe=url_safe)


class BinarySchemaDecoder:
    """Decodes binary schema back to dict format."""
    
    def _exponent_to_mult(self, exp: int) -> float:
        """Convert exponent back to multiplier."""
        if exp == 0:
            return 1.0
        if exp == 0xFF or exp == -1:
            return 0.1  # Could be 0.5 with special encoding
        return 10.0 ** exp
    
    def decode_field(self, binary_field: BinaryField, index: int) -> dict:
        """Decode binary field to schema dict (v1 format)."""
        # Determine type string
        type_key = (binary_field.type_code, binary_field.size)
        type_str = SIZE_TO_TYPE.get(type_key, 'u8')
        
        field_def = {
            'name': binary_field.name or f'field_{index}',
            'type': type_str,
        }
        
        # Add multiplier if not 1.0
        mult = self._exponent_to_mult(binary_field.mult_exponent)
        if mult != 1.0:
            field_def['mult'] = mult
        
        # Add semantic if present
        if binary_field.semantic_id:
            field_def['semantic'] = {'ipso': binary_field.semantic_id}
        
        return field_def
    
    def _decode_v2_data_field(self, data: bytes, pos: int,
                              field_idx: int) -> Tuple[dict, int]:
        """Decode a single v2 data field record (always 4 bytes).
        
        Same layout as v1 BinaryField: [type_byte, mult_exp, semantic_id LE].
        Returns (field_def, new_pos, has_var_flag).
        """
        if pos + 4 > len(data):
            raise ValueError(f"Truncated field at pos {pos}")
        
        type_byte, mult_exp, semantic_id = struct.unpack(
            '<BBH', data[pos:pos + 4])
        pos += 4
        
        type_code = FieldType((type_byte >> 4) & 0x0F)
        size = type_byte & 0x0F
        
        type_key = (type_code, size)
        type_str = SIZE_TO_TYPE.get(type_key, 'u8')
        
        field_def = {
            'name': f'field_{field_idx}',
            'type': type_str,
        }
        
        if semantic_id:
            field_def['semantic'] = {'ipso': semantic_id}
        
        # Multiplier from signed exponent byte
        if mult_exp > 127:
            mult_exp = mult_exp - 256
        mult = self._exponent_to_mult(mult_exp)
        if mult != 1.0:
            field_def['mult'] = mult
        
        return field_def, pos, False
    
    def _decode_v2_match(self, data: bytes, pos: int) -> Tuple[dict, int]:
        """Decode a MATCH record from v2 byte stream.
        
        Returns (match_field_def, new_pos).
        """
        if pos + 2 > len(data):
            raise ValueError("Truncated MATCH record")
        
        flags = data[pos]
        case_count = data[pos + 1]
        pos += 2
        
        field_ref = flags & 0x0F
        is_inline = bool(flags & 0x10)
        wide_value = bool(flags & 0x20)
        has_default = bool(flags & 0x40)
        
        match_def = {}
        if is_inline:
            match_def['length'] = 2 if wide_value else 1
        else:
            match_def['field'] = f'$var_{field_ref}'
        
        cases = {}
        val_size = 2 if wide_value else 1
        
        for _ in range(case_count):
            if pos + val_size > len(data):
                raise ValueError("Truncated case value")
            if wide_value:
                case_val = struct.unpack('<H', data[pos:pos + 2])[0]
            else:
                case_val = data[pos]
            pos += val_size
            
            if pos >= len(data):
                raise ValueError("Truncated case field_count")
            field_count = data[pos]
            pos += 1
            
            case_fields = []
            for fi in range(field_count):
                fd, pos, _ = self._decode_v2_data_field(data, pos, fi)
                case_fields.append(fd)
            
            cases[case_val] = case_fields
        
        # Default case
        if has_default:
            if pos >= len(data):
                raise ValueError("Truncated default case")
            default_count = data[pos]
            pos += 1
            
            if default_count == 0:
                match_def['default'] = 'skip'
            elif default_count == 0xFF:
                match_def['default'] = 'error'
            else:
                default_fields = []
                for fi in range(default_count):
                    fd, pos, _ = self._decode_v2_data_field(data, pos, fi)
                    default_fields.append(fd)
                cases['default'] = default_fields
        
        match_def['cases'] = cases
        return {'match': match_def}, pos
    
    def _decode_v2(self, binary: BinarySchema) -> dict:
        """Decode v2 binary schema with structural records."""
        data = binary.records
        if data is None:
            return {'version': 2, 'fields': []}
        
        big_endian = not bool(binary.flags & 0x01)
        
        fields = []
        pos = 0
        field_idx = 0
        var_counter = 0
        var_names = {}  # index -> name
        
        while pos < len(data):
            byte = data[pos]
            
            if byte == OPCODE_MATCH:
                pos += 1
                match_def, pos = self._decode_v2_match(data, pos)
                # Resolve variable references
                match_inner = match_def['match']
                if 'field' in match_inner:
                    ref = match_inner['field']
                    if ref.startswith('$var_'):
                        idx = int(ref[5:])
                        if idx in var_names:
                            match_inner['field'] = f'${var_names[idx]}'
                fields.append(match_def)
                
            elif byte == OPCODE_VAR:
                pos += 1
                # VAR modifies the preceding field
                if fields and isinstance(fields[-1], dict):
                    last = fields[-1]
                    var_name = last.get('name', f'var_{var_counter}')
                    last['var'] = var_name
                    var_names[var_counter] = var_name
                    var_counter += 1
                
            elif (byte >> 4) & 0x0F < 0x7:
                # Data field (type nibble 0x0-0x6)
                fd, pos, has_var = self._decode_v2_data_field(
                    data, pos, field_idx)
                fields.append(fd)
                field_idx += 1
                
                if has_var:
                    # Expect VAR opcode next
                    pass  # Will be handled when we see 0x73
                
            else:
                # Unknown opcode - skip
                pos += 1
        
        result = {
            'version': 2,
            'endian': 'big' if big_endian else 'little',
            'fields': fields,
        }
        return result
    
    def decode(self, binary: BinarySchema) -> dict:
        """Decode binary schema to dict format."""
        if binary.version >= 2 and binary.records is not None:
            return self._decode_v2(binary)
        
        # Version 1
        fields = []
        for i, bf in enumerate(binary.fields):
            field_def = self.decode_field(bf, i)
            fields.append(field_def)
        
        return {
            'version': binary.version,
            'fields': fields,
        }
    
    def decode_from_bytes(self, data: bytes) -> dict:
        """Convenience method: decode bytes directly to dict."""
        binary = BinarySchema.from_bytes(data)
        return self.decode(binary)
    
    def decode_from_base64(self, encoded: str) -> dict:
        """Convenience method: decode base64 directly to dict."""
        binary = BinarySchema.from_base64(encoded)
        return self.decode(binary)


def compute_crc32(data: bytes) -> int:
    """Compute CRC32 for schema hash."""
    import zlib
    return zlib.crc32(data) & 0xFFFFFFFF


# Convenience functions
def encode_schema(schema: dict) -> bytes:
    """Encode schema dict to binary bytes."""
    return BinarySchemaEncoder().encode_to_bytes(schema)


def decode_schema(data: bytes) -> dict:
    """Decode binary bytes to schema dict."""
    return BinarySchemaDecoder().decode_from_bytes(data)


def schema_to_base64(schema: dict, url_safe: bool = True) -> str:
    """Encode schema dict to base64 string."""
    return BinarySchemaEncoder().encode_to_base64(schema, url_safe=url_safe)


def base64_to_schema(encoded: str) -> dict:
    """Decode base64 string to schema dict."""
    return BinarySchemaDecoder().decode_from_base64(encoded)


def schema_hash(schema: dict) -> int:
    """Compute schema hash (CRC32) for OTA transfer."""
    binary = encode_schema(schema)
    return compute_crc32(binary)


if __name__ == '__main__':
    import yaml
    import sys
    
    # Example usage
    example_schema = {
        'name': 'env_sensor',
        'fields': [
            {'name': 'temperature', 'type': 's16', 'mult': 0.01, 
             'semantic': {'ipso': 3303}},
            {'name': 'humidity', 'type': 'u8', 'mult': 0.5,
             'semantic': {'ipso': 3304}},
            {'name': 'battery_mv', 'type': 'u16',
             'semantic': {'ipso': 3316}},
            {'name': 'status', 'type': 'u8'},
        ]
    }
    
    print("=== Binary Schema Encoder/Decoder Demo ===\n")
    
    # Encode
    binary = encode_schema(example_schema)
    print(f"Schema: {example_schema['name']}")
    print(f"Fields: {len(example_schema['fields'])}")
    print(f"\nBinary ({len(binary)} bytes):")
    print(' '.join(f'{b:02X}' for b in binary))
    
    # Base64
    b64 = schema_to_base64(example_schema)
    print(f"\nBase64: {b64}")
    print(f"Base64 length: {len(b64)} chars")
    
    # Hash
    h = schema_hash(example_schema)
    print(f"\nSchema hash: 0x{h:08X}")
    
    # Decode back
    decoded = decode_schema(binary)
    print(f"\nDecoded fields: {len(decoded['fields'])}")
    for f in decoded['fields']:
        print(f"  - {f}")
