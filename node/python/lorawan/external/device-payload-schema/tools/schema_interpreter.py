#!/usr/bin/env python3
"""
schema_interpreter.py - Runtime Schema Interpreter for Payload Decoding

Decodes LoRaWAN payloads using Payload Schema definitions at runtime.
This is the reference implementation of the Payload Schema decoder.

Usage:
    from schema_interpreter import SchemaInterpreter
    
    interpreter = SchemaInterpreter(schema)
    result = interpreter.decode(payload_bytes)
    
    # Or encode
    payload = interpreter.encode(data_dict)
"""

import struct
import re
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Union
from enum import Enum


class Endian(Enum):
    BIG = 'big'
    LITTLE = 'little'


@dataclass
class DecodeResult:
    """Result of decoding a payload."""
    data: Dict[str, Any]
    bytes_consumed: int
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    quality: Dict[str, str] = field(default_factory=dict)
    
    @property
    def success(self) -> bool:
        return len(self.errors) == 0


@dataclass
class EncodeResult:
    """Result of encoding data to payload."""
    payload: bytes
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class SchemaInterpreter:
    """
    Runtime interpreter for Payload Schema definitions.
    
    Supports:
    - All integer types (u8, u16, u24, u32, i8, i16, etc.)
    - Floating point (f32, f64)
    - Bitfields (u8[3:4], u8:2, bits<3,2>, etc.)
    - Boolean
    - Bytes/strings
    - Arithmetic modifiers (mult, add, div)
    - Lookup tables
    - Nested objects
    - Conditional/match fields
    - Semantic mappings (IPSO, SenML)
    """
    
    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema
        self.endian = Endian(schema.get('endian', 'big'))
        self.name = schema.get('name', 'unknown')
        self.version = schema.get('version', 1)
        self.definitions = schema.get('definitions', {})
        self.direction = schema.get('direction', 'uplink')  # uplink|downlink|bidirectional
        self.downlink_commands = schema.get('downlink_commands', {})
        
        # Bitfield state for sequential extraction
        self._bit_pos = 0
    
    def _parse_compact_format(self, format_str: str) -> tuple:
        """
        Parse compact format string to field definitions.
        
        Format: ">B:version H:length I:timestamp"
        - >/<: big/little endian prefix
        - b/B: s8/u8, h/H: s16/u16, i/I: s32/u32, q/Q: s64/u64
        - f: f32, d: f64, x: skip 1 byte, Nx: skip N bytes
        - :name suffix assigns field name
        
        Returns:
            Tuple of (field list, endian override or None)
        """
        FORMAT_CHARS = {
            'b': ('s8', 1), 'B': ('u8', 1),
            'h': ('s16', 2), 'H': ('u16', 2),
            'i': ('s32', 4), 'I': ('u32', 4),
            'q': ('s64', 8), 'Q': ('u64', 8),
            'f': ('f32', 4), 'd': ('f64', 8),
            'e': ('f16', 2),
            'x': ('skip', 1),
            '?': ('bool', 1),
        }
        
        fields = []
        parts = format_str.split()
        endian_override = None
        
        for part in parts:
            # Handle endian prefix
            if part in ('>', '<'):
                endian_override = Endian.BIG if part == '>' else Endian.LITTLE
                continue
            
            # Check for endian prefix at start of token
            if part.startswith('>') or part.startswith('<'):
                endian_override = Endian.BIG if part[0] == '>' else Endian.LITTLE
                part = part[1:]
            
            # Parse count prefix (e.g., "2x" for 2 skip bytes)
            count = 1
            if part and part[0].isdigit():
                count_str = ''
                while part and part[0].isdigit():
                    count_str += part[0]
                    part = part[1:]
                count = int(count_str) if count_str else 1
            
            if not part:
                continue
            
            # Extract format char and optional name
            if ':' in part:
                fmt_char = part[0]
                name = part[2:]  # Skip format char and colon
            else:
                fmt_char = part[0]
                name = f'_field{len(fields)}'
            
            if fmt_char not in FORMAT_CHARS:
                raise ValueError(f"Unknown format character: {fmt_char}")
            
            type_name, size = FORMAT_CHARS[fmt_char]
            
            # Handle skip with count
            if type_name == 'skip':
                fields.append({
                    'name': f'_skip{len(fields)}',
                    'type': 'skip',
                    'length': count
                })
            else:
                field_def = {'name': name, 'type': type_name}
                fields.append(field_def)
        
        return fields, endian_override
    
    def _resolve_fields(self, fPort: int = None) -> list:
        """Resolve fields for a given fPort (port-based schema selection)."""
        ports = self.schema.get('ports')
        if not ports:
            fields = self.schema.get('fields', [])
            # Handle compact format string
            if isinstance(fields, str):
                parsed_fields, endian_override = self._parse_compact_format(fields)
                if endian_override:
                    self.endian = endian_override
                return parsed_fields
            return fields
        
        if fPort is not None:
            port_key = str(fPort)
            if port_key in ports:
                fields = ports[port_key].get('fields', [])
                if isinstance(fields, str):
                    parsed_fields, endian_override = self._parse_compact_format(fields)
                    if endian_override:
                        self.endian = endian_override
                    return parsed_fields
                return fields
            # Try int key (YAML may parse as int)
            if fPort in ports:
                fields = ports[fPort].get('fields', [])
                if isinstance(fields, str):
                    parsed_fields, endian_override = self._parse_compact_format(fields)
                    if endian_override:
                        self.endian = endian_override
                    return parsed_fields
                return fields
        
        if 'default' in ports:
            fields = ports['default'].get('fields', [])
            if isinstance(fields, str):
                parsed_fields, endian_override = self._parse_compact_format(fields)
                if endian_override:
                    self.endian = endian_override
                return parsed_fields
            return fields
        
        raise ValueError(f"No port definition for fPort {fPort} and no default in schema '{self.name}'")
    
    def _resolve_ref(self, ref: str) -> Dict[str, Any]:
        """
        Resolve a $ref reference to its definition.
        
        Supports: #/definitions/name format (local references)
        """
        if not ref.startswith('#/definitions/'):
            raise ValueError(f"Unsupported $ref format: {ref}")
        
        def_name = ref.split('/')[-1]
        if def_name not in self.definitions:
            raise ValueError(f"Definition not found: {def_name}")
        
        return self.definitions[def_name]
    
    def _read_int(self, buf: bytes, pos: int, size: int, signed: bool) -> Tuple[int, int]:
        """Read integer from buffer."""
        if pos + size > len(buf):
            raise ValueError(f"Buffer too short: need {size} bytes at pos {pos}")
        
        data = buf[pos:pos + size]
        
        if self.endian == Endian.LITTLE:
            value = int.from_bytes(data, 'little', signed=signed)
        else:
            value = int.from_bytes(data, 'big', signed=signed)
        
        return value, pos + size
    
    def _write_int(self, value: int, size: int, signed: bool) -> bytes:
        """Write integer to bytes."""
        byteorder = 'little' if self.endian == Endian.LITTLE else 'big'
        return value.to_bytes(size, byteorder, signed=signed)
    
    def _read_float(self, buf: bytes, pos: int, size: int) -> Tuple[float, int]:
        """Read float from buffer."""
        if pos + size > len(buf):
            raise ValueError(f"Buffer too short: need {size} bytes at pos {pos}")
        
        data = buf[pos:pos + size]
        fmt = '<f' if self.endian == Endian.LITTLE else '>f'
        if size == 8:
            fmt = '<d' if self.endian == Endian.LITTLE else '>d'
        
        value = struct.unpack(fmt, data)[0]
        return value, pos + size
    
    def _read_float16(self, buf: bytes, pos: int) -> Tuple[float, int]:
        """Read IEEE 754 half-precision float (2 bytes)."""
        if pos + 2 > len(buf):
            raise ValueError(f"Buffer too short: need 2 bytes at pos {pos}")
        
        data = buf[pos:pos + 2]
        # Use struct 'e' format for half-precision (Python 3.6+)
        fmt = '<e' if self.endian == Endian.LITTLE else '>e'
        try:
            value = struct.unpack(fmt, data)[0]
        except struct.error:
            # Fallback: manual conversion for older Python
            value = self._float16_to_float(data)
        return value, pos + 2
    
    def _float16_to_float(self, data: bytes) -> float:
        """Manual IEEE 754 half-precision to float conversion."""
        if self.endian == Endian.LITTLE:
            h = data[0] | (data[1] << 8)
        else:
            h = (data[0] << 8) | data[1]
        
        sign = (h >> 15) & 1
        exp = (h >> 10) & 0x1F
        frac = h & 0x3FF
        
        if exp == 0:
            if frac == 0:
                return -0.0 if sign else 0.0
            # Subnormal
            return ((-1) ** sign) * (frac / 1024) * (2 ** -14)
        elif exp == 31:
            if frac == 0:
                return float('-inf') if sign else float('inf')
            return float('nan')
        
        return ((-1) ** sign) * (1 + frac / 1024) * (2 ** (exp - 15))
    
    def _decode_encoding(self, value: int, encoding: str, size: int) -> int:
        """
        Decode value from special encoding format.
        
        Supports:
        - sign_magnitude: MSB is sign bit, remaining bits are magnitude
        - bcd: Binary-coded decimal (each nibble is 0-9)
        - gray: Gray code (adjacent values differ by one bit)
        """
        if encoding == 'sign_magnitude':
            # MSB is sign, rest is magnitude
            sign_bit = 1 << (size * 8 - 1)
            if value & sign_bit:
                return -(value & (sign_bit - 1))
            return value
        
        elif encoding == 'bcd':
            # Binary-coded decimal: each nibble is a decimal digit
            result = 0
            multiplier = 1
            temp = value
            for _ in range(size * 2):  # 2 nibbles per byte
                digit = temp & 0x0F
                if digit > 9:
                    raise ValueError(f"Invalid BCD digit: {digit}")
                result += digit * multiplier
                multiplier *= 10
                temp >>= 4
            return result
        
        elif encoding == 'gray':
            # Gray code to binary: XOR with right-shifted versions
            result = value
            shift = 1
            while shift < size * 8:
                result ^= (result >> shift)
                shift <<= 1
            return result
        
        return value
    
    def _encode_encoding(self, value: int, encoding: str, size: int) -> int:
        """
        Encode value to special encoding format.
        
        Reverse of _decode_encoding for encoding payloads.
        """
        if encoding == 'sign_magnitude':
            sign_bit = 1 << (size * 8 - 1)
            if value < 0:
                return sign_bit | abs(value)
            return value
        
        elif encoding == 'bcd':
            # Binary to BCD
            result = 0
            shift = 0
            temp = abs(int(value))
            while temp > 0:
                digit = temp % 10
                result |= (digit << shift)
                shift += 4
                temp //= 10
            return result
        
        elif encoding == 'gray':
            # Binary to Gray code: XOR with right-shifted self
            return value ^ (value >> 1)
        
        return value
    
    def _parse_bitfield_type(self, type_str: str) -> Tuple[int, int, int]:
        """
        Parse bitfield type string.
        
        Returns: (base_size_bytes, bit_offset, bit_width)
        """
        # Python slice: u8[3:4] - bits 3 to 4 inclusive
        match = re.match(r'u(\d+)\[(\d+):(\d+)\]', type_str)
        if match:
            base_size = int(match.group(1)) // 8
            start = int(match.group(2))
            end = int(match.group(3))
            width = end - start + 1
            return base_size, start, width
        
        # Verilog part-select: u8[3+:2] - 2 bits starting at bit 3
        match = re.match(r'u(\d+)\[(\d+)\+:(\d+)\]', type_str)
        if match:
            base_size = int(match.group(1)) // 8
            offset = int(match.group(2))
            width = int(match.group(3))
            return base_size, offset, width
        
        # C++ template: bits<3,2> - 2 bits at offset 3
        match = re.match(r'bits<(\d+),(\d+)>', type_str)
        if match:
            offset = int(match.group(1))
            width = int(match.group(2))
            return 1, offset, width
        
        # @ notation: bits:2@3 - 2 bits at offset 3
        match = re.match(r'bits:(\d+)@(\d+)', type_str)
        if match:
            width = int(match.group(1))
            offset = int(match.group(2))
            return 1, offset, width
        
        # Sequential: u8:2 - next 2 bits
        match = re.match(r'u(\d+):(\d+)', type_str)
        if match:
            base_size = int(match.group(1)) // 8
            width = int(match.group(2))
            return base_size, -1, width  # -1 = sequential
        
        raise ValueError(f"Unknown bitfield format: {type_str}")
    
    def _extract_bits(self, buf: bytes, pos: int, bit_offset: int, 
                      bit_width: int, base_size: int) -> Tuple[int, int, bool]:
        """
        Extract bits from buffer.
        
        Returns: (value, new_pos, consumed_byte)
        """
        if pos >= len(buf):
            raise ValueError(f"Buffer too short at pos {pos}")
        
        byte_val = buf[pos]
        
        if bit_offset < 0:
            # Sequential mode - use internal bit position
            if self._current_byte_pos != pos:
                self._current_byte_pos = pos
                self._current_byte = byte_val
                self._bit_pos = 8  # Start from MSB
            
            self._bit_pos -= bit_width
            if self._bit_pos < 0:
                raise ValueError("Bit overflow in sequential extraction")
            
            mask = (1 << bit_width) - 1
            value = (self._current_byte >> self._bit_pos) & mask
            
            consumed = self._bit_pos == 0
            return value, pos, consumed
        else:
            # Explicit offset mode
            mask = (1 << bit_width) - 1
            value = (byte_val >> bit_offset) & mask
            return value, pos, False
    
    def _decode_field(self, field_def: Dict[str, Any], buf: bytes, 
                      pos: int) -> Tuple[Any, int]:
        """Decode a single field from buffer."""
        field_type = field_def.get('type', 'u8')
        consume = field_def.get('consume', None)
        
        # Handle bitfields
        if any(c in str(field_type) for c in ['[', ':', '<']):
            base_size, bit_offset, bit_width = self._parse_bitfield_type(field_type)
            value, new_pos, auto_consumed = self._extract_bits(
                buf, pos, bit_offset, bit_width, base_size
            )
            
            # Determine position advancement
            if consume is not None:
                new_pos = pos + consume
            elif auto_consumed:
                new_pos = pos + 1
            else:
                new_pos = pos
            
            return value, new_pos
        
        # Handle standard types with aliases
        # Canonical: u8/s8, Aliases: uint8/int8/i8
        type_info = {
            # Unsigned (canonical: u prefix)
            'u8': (1, False), 'uint8': (1, False),
            'u16': (2, False), 'uint16': (2, False),
            'u24': (3, False), 'uint24': (3, False),
            'u32': (4, False), 'uint32': (4, False),
            'u64': (8, False), 'uint64': (8, False),
            # Signed (canonical: s prefix, aliases: i prefix, int prefix)
            's8': (1, True), 'i8': (1, True), 'int8': (1, True),
            's16': (2, True), 'i16': (2, True), 'int16': (2, True),
            's24': (3, True), 'i24': (3, True), 'int24': (3, True),
            's32': (4, True), 'i32': (4, True), 'int32': (4, True),
            's64': (8, True), 'i64': (8, True), 'int64': (8, True),
        }
        
        if field_type in type_info:
            size, signed = type_info[field_type]
            value, new_pos = self._read_int(buf, pos, size, signed)
            # Apply encoding if specified (sign_magnitude, bcd, gray)
            encoding = field_def.get('encoding')
            if encoding:
                # For encoded values, read as unsigned first
                if signed:
                    value, _ = self._read_int(buf, pos, size, False)
                value = self._decode_encoding(value, encoding, size)
            return value, new_pos
        
        # Nibble-decimal types: upper nibble = whole, lower nibble = tenths
        if field_type in ('udec', 'UDec'):
            if pos >= len(buf):
                raise ValueError("Buffer too short for udec")
            byte = buf[pos]
            value = (byte >> 4) + (byte & 0x0F) * 0.1
            return value, pos + 1
        
        if field_type in ('sdec', 'SDec'):
            if pos >= len(buf):
                raise ValueError("Buffer too short for sdec")
            byte = buf[pos]
            whole = byte >> 4
            # Sign extend the 4-bit whole part
            if whole >= 8:
                whole -= 16
            value = whole + (byte & 0x0F) * 0.1
            return value, pos + 1
        
        if field_type == 'f16':
            # IEEE 754 half-precision (2 bytes)
            return self._read_float16(buf, pos)
        
        if field_type in ('f32', 'float'):
            return self._read_float(buf, pos, 4)
        
        if field_type in ('f64', 'double'):
            return self._read_float(buf, pos, 8)
        
        if field_type == 'bool':
            bit = field_def.get('bit', 0)
            if pos >= len(buf):
                raise ValueError("Buffer too short for bool")
            value = bool((buf[pos] >> bit) & 1)
            # Bool doesn't advance position by default
            if consume:
                return value, pos + consume
            return value, pos
        
        if field_type == 'bytes':
            length = field_def.get('length', 1)
            if pos + length > len(buf):
                raise ValueError("Buffer too short for bytes")
            value = buf[pos:pos + length]
            return value, pos + length
        
        if field_type == 'string':
            length = field_def.get('length', 1)
            if pos + length > len(buf):
                raise ValueError("Buffer too short for string")
            value = buf[pos:pos + length].decode('utf-8', errors='replace').rstrip('\x00')
            return value, pos + length
        
        if field_type == 'ascii':
            length = field_def.get('length', 1)
            if pos + length > len(buf):
                raise ValueError("Buffer too short for ascii")
            value = buf[pos:pos + length].decode('ascii', errors='replace').rstrip('\x00')
            return value, pos + length
        
        if field_type == 'hex':
            length = field_def.get('length', 1)
            if pos + length > len(buf):
                raise ValueError("Buffer too short for hex")
            value = buf[pos:pos + length].hex().upper()
            return value, pos + length
        
        if field_type == 'base64':
            import base64 as b64
            length = field_def.get('length', 1)
            if pos + length > len(buf):
                raise ValueError("Buffer too short for base64")
            value = b64.b64encode(buf[pos:pos + length]).decode('ascii')
            return value, pos + length
        
        if field_type == 'skip':
            # Padding/reserved bytes - advance position but don't output
            length = field_def.get('length', 1)
            return None, pos + length
        
        if field_type == 'version_string':
            # Phase 3: Assemble a version string from packed bytes
            return self._decode_version_string(field_def, buf, pos)
        
        if field_type == 'object':
            # Nested object
            nested_fields = field_def.get('fields', [])
            nested_result = {}
            for nested_field in nested_fields:
                name = nested_field.get('name', 'unknown')
                value, pos = self._decode_field(nested_field, buf, pos)
                value = self._apply_modifiers(value, nested_field)
                nested_result[name] = value
            return nested_result, pos
        
        if field_type == 'repeat':
            # Repeated/array field
            return self._decode_repeat(field_def, buf, pos)
        
        if field_type == 'enum':
            # Enum type: decode base type then map to string
            return self._decode_enum(field_def, buf, pos)
        
        if field_type == 'match':
            # Conditional decoding
            return self._decode_match(field_def, buf, pos)
        
        raise ValueError(f"Unknown type: {field_type}")
    
    def _decode_enum(self, field_def: Dict[str, Any], buf: bytes,
                     pos: int) -> Tuple[Any, int]:
        """Decode enum field: base integer type mapped to string value."""
        base_type = field_def.get('base', 'u8')
        values = field_def.get('values', {})
        
        # Decode the base integer type
        base_field = {'type': base_type}
        raw_value, new_pos = self._decode_field(base_field, buf, pos)
        
        # Map to string value
        # Values can be dict {0: 'idle', 1: 'running'} or list ['idle', 'running']
        if isinstance(values, dict):
            # Convert string keys to int if needed
            values_map = {int(k) if isinstance(k, str) else k: v for k, v in values.items()}
            if raw_value in values_map:
                return values_map[raw_value], new_pos
            else:
                # Unknown value - return raw with warning marker
                return f"unknown({raw_value})", new_pos
        elif isinstance(values, list):
            if 0 <= raw_value < len(values):
                return values[raw_value], new_pos
            else:
                return f"unknown({raw_value})", new_pos
        
        # No mapping - return raw value
        return raw_value, new_pos
    
    def _decode_repeat(self, field_def: Dict[str, Any], buf: bytes,
                       pos: int) -> Tuple[List[Any], int]:
        """
        Decode repeated/array field.
        
        Supports three modes:
        - count: fixed number of iterations (int or $variable)
        - byte_length: repeat until N bytes consumed (int or $variable)
        - until: "end" to repeat until payload exhausted
        
        Options:
        - max: maximum iterations (safety limit, default 1000)
        - min: minimum required iterations
        - fields: nested fields to decode per iteration
        """
        nested_fields = field_def.get('fields', [])
        max_iterations = field_def.get('max', 1000)
        min_iterations = field_def.get('min', 0)
        
        result = []
        iterations = 0
        
        # Determine iteration mode
        count = field_def.get('count')
        byte_length = field_def.get('byte_length')
        until = field_def.get('until')
        
        if count is not None:
            # Count-based: fixed number of iterations
            if isinstance(count, str) and count.startswith('$'):
                var_name = count[1:]
                if hasattr(self, '_variables') and var_name in self._variables:
                    count = int(self._variables[var_name])
                else:
                    raise ValueError(f"repeat count variable not found: {var_name}")
            else:
                count = int(count)
            
            count = min(count, max_iterations)
            
            for _ in range(count):
                element = {}
                for nested_field in nested_fields:
                    name = nested_field.get('name', 'unknown')
                    value, pos = self._decode_field(nested_field, buf, pos)
                    value = self._apply_modifiers(value, nested_field)
                    if value is not None:
                        element[name] = value
                result.append(element)
                
        elif byte_length is not None:
            # Byte-length based: consume specified number of bytes
            if isinstance(byte_length, str) and byte_length.startswith('$'):
                var_name = byte_length[1:]
                if hasattr(self, '_variables') and var_name in self._variables:
                    byte_length = int(self._variables[var_name])
                else:
                    raise ValueError(f"repeat byte_length variable not found: {var_name}")
            else:
                byte_length = int(byte_length)
            
            end_pos = pos + byte_length
            
            while pos < end_pos and iterations < max_iterations:
                element = {}
                for nested_field in nested_fields:
                    name = nested_field.get('name', 'unknown')
                    value, pos = self._decode_field(nested_field, buf, pos)
                    value = self._apply_modifiers(value, nested_field)
                    if value is not None:
                        element[name] = value
                result.append(element)
                iterations += 1
            
            if pos != end_pos:
                raise ValueError(f"repeat byte_length mismatch: expected end at {end_pos}, got {pos}")
                
        elif until == 'end':
            # Until-end: repeat until payload exhausted
            while pos < len(buf) and iterations < max_iterations:
                element = {}
                start_pos = pos
                for nested_field in nested_fields:
                    name = nested_field.get('name', 'unknown')
                    value, pos = self._decode_field(nested_field, buf, pos)
                    value = self._apply_modifiers(value, nested_field)
                    if value is not None:
                        element[name] = value
                # Safety: check we made progress
                if pos == start_pos:
                    break
                result.append(element)
                iterations += 1
        else:
            raise ValueError("repeat field must specify one of: count, byte_length, or until")
        
        # Validate minimum iterations
        if len(result) < min_iterations:
            raise ValueError(f"repeat produced {len(result)} elements, but minimum is {min_iterations}")
        
        return result, pos
    
    def _decode_match(self, field_def: Dict[str, Any], buf: bytes, 
                      pos: int) -> Tuple[Dict[str, Any], int]:
        """
        Decode conditional/match field.
        
        Supports both legacy syntax and Option B syntax:
        
        Legacy:
          type: match, on: field_name, cases: [{case: 1, fields: [...]}, ...]
        
        Option B:
          match:
            field: $var_name    # variable-based
            length: 1           # OR inline read
            name: output_name   # optional: include match value in output
            var: var_name       # optional: store as variable
            cases:
              1: [fields...]
              2: [fields...]
        
        Case patterns:
        - Single value: 1
        - List of values: [1, 2, 3]
        - Range: "2..5" or 2..5
        - Default handling: default: error | skip | {fields}
        """
        # Option B syntax: match_def is the nested dict under 'match:'
        match_def = field_def.get('match', {})
        if isinstance(match_def, dict) and match_def:
            return self._decode_match_option_b(match_def, buf, pos)
        
        # Legacy syntax
        on_field = field_def.get('on')
        cases = field_def.get('cases', [])
        default = field_def.get('default', 'error')
        
        # Get the discriminator value from previously decoded fields
        discriminator = None
        if on_field and hasattr(self, '_current_data') and self._current_data:
            # Handle $ prefix for variable reference
            field_name = on_field.lstrip('$')
            discriminator = self._current_data.get(field_name)
            # Also check variables store
            if discriminator is None and hasattr(self, '_variables'):
                discriminator = self._variables.get(field_name)
        
        if discriminator is None:
            # Fallback: peek at next byte as discriminator
            if pos < len(buf):
                discriminator = buf[pos]
        
        # Find matching case
        matched_case = None
        for case in cases:
            case_pattern = case.get('case')
            if self._match_case_pattern(discriminator, case_pattern):
                matched_case = case
                break
        
        # Handle no match
        if matched_case is None:
            if default == 'error':
                raise ValueError(f"No matching case for value {discriminator}")
            elif default == 'skip':
                return {}, pos
            elif isinstance(default, dict) and 'fields' in default:
                # Default case with fields
                matched_case = default
            else:
                return {}, pos
        
        # Decode matched case fields
        result = {}
        case_fields = matched_case.get('fields', [])
        for cf in case_fields:
            name = cf.get('name', 'unknown')
            if name.startswith('_'):
                # Internal field - decode but don't output
                _, pos = self._decode_field(cf, buf, pos)
            else:
                value, pos = self._decode_field(cf, buf, pos)
                value = self._apply_modifiers(value, cf)
                result[name] = value
        
        return result, pos
    
    def _decode_match_option_b(self, match_def: Dict[str, Any], buf: bytes,
                                pos: int) -> Tuple[Dict[str, Any], int]:
        """
        Decode match using Option B syntax.
        
        match_def has:
          field: $var_name  (variable-based)
          OR length: N      (inline read)
          name: key         (optional: include value in output)
          var: var_name     (optional: store as variable)
          default: error|skip|[fields]
          cases: {value: [fields], ...}
        """
        result = {}
        field_ref = match_def.get('field')
        length = match_def.get('length')
        match_name = match_def.get('name')
        match_var = match_def.get('var')
        cases = match_def.get('cases', {})
        default = match_def.get('default', 'error')
        
        discriminator = None
        
        if field_ref:
            # Variable-based: look up stored variable
            var_name = field_ref.lstrip('$')
            if hasattr(self, '_variables') and var_name in self._variables:
                discriminator = self._variables[var_name]
            elif hasattr(self, '_current_data') and self._current_data:
                discriminator = self._current_data.get(var_name)
        elif length is not None:
            # Inline: read bytes from payload
            if pos + length > len(buf):
                raise ValueError(f"Buffer too short for match: need {length} bytes at pos {pos}")
            if length == 1:
                discriminator = buf[pos]
            elif length == 2:
                if self.endian == Endian.LITTLE:
                    discriminator = buf[pos] | (buf[pos + 1] << 8)
                else:
                    discriminator = (buf[pos] << 8) | buf[pos + 1]
            else:
                discriminator = int.from_bytes(buf[pos:pos + length],
                    'little' if self.endian == Endian.LITTLE else 'big')
            pos += length
            
            # Optionally include in JSON output
            if match_name:
                result[match_name] = discriminator
                if hasattr(self, '_current_data'):
                    self._current_data[match_name] = discriminator
            
            # Optionally store as variable
            if match_var:
                if not hasattr(self, '_variables'):
                    self._variables = {}
                self._variables[match_var] = discriminator
        
        if discriminator is None:
            raise ValueError("Match has neither 'field' nor 'length'")
        
        # Cases in Option B are a dict: {value: [field_list], ...}
        matched_fields = None
        default_fields = None
        
        for case_key, case_fields in cases.items():
            if case_key == 'default':
                default_fields = case_fields
                continue
            if self._match_case_pattern(discriminator, case_key):
                matched_fields = case_fields
                break
        
        if matched_fields is None:
            if default_fields is not None:
                matched_fields = default_fields
            elif default == 'error':
                raise ValueError(f"No matching case for value {discriminator}")
            elif default == 'skip':
                return result, pos
            elif isinstance(default, list):
                matched_fields = default
            else:
                return result, pos
        
        # Decode matched case fields (handling nested Option B constructs)
        for cf in matched_fields:
            # Option B: nested match: inside case
            if 'match' in cf and not cf.get('type'):
                nested_result, pos = self._decode_match(cf, buf, pos)
                result.update(nested_result)
                if hasattr(self, '_current_data'):
                    self._current_data.update(nested_result)
                continue
            
            # Option B: nested object: inside case
            if 'object' in cf and not cf.get('type'):
                obj_name = cf['object']
                sub_result, pos = self._decode_nested_object_b(cf, buf, pos)
                result[obj_name] = sub_result
                if hasattr(self, '_current_data'):
                    self._current_data[obj_name] = sub_result
                continue
            
            name = cf.get('name', 'unknown')
            if name.startswith('_'):
                _, pos = self._decode_field(cf, buf, pos)
            else:
                value, pos = self._decode_field(cf, buf, pos)
                value = self._apply_modifiers(value, cf)
                result[name] = value
                if hasattr(self, '_current_data'):
                    self._current_data[name] = value
                # Check for var on nested fields
                if cf.get('var'):
                    if not hasattr(self, '_variables'):
                        self._variables = {}
                    self._variables[cf['var']] = value
        
        return result, pos
    
    def _match_case_pattern(self, value: Any, pattern: Any) -> bool:
        """
        Check if value matches case pattern.
        
        Supports:
        - Single value: 1
        - List: [1, 2, 3]
        - Range string: "2..5"
        - Range (parsed from YAML): handled as string
        """
        if value is None:
            return False
        
        # List of values
        if isinstance(pattern, list):
            return value in pattern
        
        # Range pattern (string like "2..5")
        if isinstance(pattern, str) and '..' in pattern:
            try:
                parts = pattern.split('..')
                start = int(parts[0])
                end = int(parts[1])
                return start <= value <= end
            except (ValueError, IndexError):
                return False
        
        # Single value comparison
        return value == pattern
    
    def _decode_flagged(self, flagged_def: Dict[str, Any], buf: bytes, pos: int) -> Tuple[Dict[str, Any], int]:
        """Decode flagged/bitmask field groups."""
        field_name = flagged_def.get('field', '')
        groups = flagged_def.get('groups', [])
        
        if field_name not in self._variables:
            raise ValueError(f"Flagged field reference not found: {field_name}")
        flags = int(self._variables[field_name])
        
        result = {}
        for group in groups:
            bit = group.get('bit', 0)
            is_present = (flags >> bit) & 1
            if is_present:
                for gf in group.get('fields', []):
                    gf_name = gf.get('name', 'unknown')
                    gf_type = gf.get('type', 'u8')
                    
                    # Handle computed fields (type: number)
                    if gf_type == 'number':
                        value = self._decode_computed_field(gf)
                        if value is not None:
                            result[gf_name] = value
                            self._variables[gf_name] = value
                        continue
                    
                    value, pos = self._decode_field(gf, buf, pos)
                    if value is not None:
                        if gf.get('formula'):
                            import warnings
                            warnings.warn(f"Field '{gf_name}': 'formula' is deprecated.", DeprecationWarning)
                            value = self._evaluate_formula(gf['formula'], value)
                        else:
                            value = self._apply_modifiers(value, gf)
                        result[gf_name] = value
                        self._variables[gf_name] = value
        
        return result, pos
    
    def _decode_computed_field(self, field_def: Dict[str, Any]) -> Optional[float]:
        """Decode a computed field (type: number) - ref, polynomial, compute, guard."""
        value = None
        
        # Deprecated: formula field
        if field_def.get('formula'):
            import warnings
            warnings.warn(f"Field '{field_def.get('name', 'unknown')}': 'formula' is deprecated.", DeprecationWarning)
            value = self._evaluate_formula(field_def['formula'], None)
        
        # ref + polynomial/transform
        elif field_def.get('ref'):
            if 'guard' in field_def:
                passed, fallback = self._evaluate_guard(field_def['guard'])
                if not passed:
                    value = fallback if fallback is not None else float('nan')
                else:
                    value = self._resolve_ref_value(field_def)
            else:
                value = self._resolve_ref_value(field_def)
        
        # compute (cross-field binary operation)
        elif field_def.get('compute'):
            if 'guard' in field_def:
                passed, fallback = self._evaluate_guard(field_def['guard'])
                if not passed:
                    value = fallback if fallback is not None else float('nan')
                else:
                    value = self._evaluate_compute(field_def['compute'])
            else:
                value = self._evaluate_compute(field_def['compute'])
            
            # Apply transform after compute
            if value is not None and 'transform' in field_def:
                value = self._apply_transform(float(value), field_def['transform'])
        
        # Literal value
        elif 'value' in field_def:
            value = field_def['value']
        
        return value
    
    def _decode_bitfield_string(self, field_def: Dict[str, Any], buf: bytes, pos: int) -> Tuple[str, int]:
        """Decode a bitfield_string field (e.g., firmware version)."""
        length = field_def.get('length', 2)
        parts = field_def.get('parts', [])
        delimiter = field_def.get('delimiter', '.')
        prefix = field_def.get('prefix', '')
        
        if pos + length > len(buf):
            raise ValueError(f"Buffer too short for bitfield_string at pos {pos}")
        
        data = buf[pos:pos + length]
        if self.endian == Endian.LITTLE:
            int_val = int.from_bytes(data, 'little')
        else:
            int_val = int.from_bytes(data, 'big')
        pos += length
        
        part_strs = []
        for part in parts:
            bit_off = part[0]
            bit_len = part[1]
            fmt = part[2] if len(part) >= 3 else 'decimal'
            mask = (1 << bit_len) - 1
            raw = (int_val >> bit_off) & mask
            if fmt == 'hex':
                part_strs.append(format(raw, 'X'))
            else:
                part_strs.append(str(raw))
        
        return prefix + delimiter.join(part_strs), pos
    
    def _decode_version_string(self, field_def: Dict[str, Any], buf: bytes,
                                pos: int) -> Tuple[str, int]:
        """
        Phase 3: Decode version_string - assemble version from sequential bytes.
        
        version_string:
          fields: [major, minor, patch]  # byte names (for docs)
          length: 3                      # bytes to consume
          delimiter: '.'
          prefix: 'v'
        
        Reads N bytes and joins them as "prefix" + "byte1.byte2.byte3"
        """
        length = field_def.get('length', 3)
        delimiter = field_def.get('delimiter', '.')
        prefix = field_def.get('prefix', '')
        
        if pos + length > len(buf):
            raise ValueError(f"Buffer too short for version_string at pos {pos}")
        
        parts = []
        for i in range(length):
            parts.append(str(buf[pos + i]))
        pos += length
        
        return prefix + delimiter.join(parts), pos
    
    def _evaluate_encode_formula(self, formula: str, value: float) -> float:
        """
        Phase 3: Evaluate an encode_formula for custom encoding.
        
        encode_formula is the inverse of formula, used during encoding.
        Variable 'x' or 'value' refers to the application-level value.
        """
        import math as _math
        
        expr = formula
        # Replace x/value with actual value
        expr = re.sub(r'\bx\b', str(value), expr)
        expr = re.sub(r'\bvalue\b', str(value), expr)
        
        try:
            result = eval(expr, {"__builtins__": {}, "_math": _math,
                                 "abs": abs, "min": min, "max": max, "int": int, "round": round})
            return float(result)
        except Exception as e:
            raise ValueError(f"encode_formula evaluation failed: '{formula}' -> '{expr}': {e}")
    
    def _evaluate_formula(self, formula: str, x=None) -> float:
        """Evaluate a formula with variable substitution and math functions."""
        import math as _math
        
        expr = formula
        
        # Substitute $field_name references
        expr = re.sub(r'\$([a-zA-Z_][a-zA-Z0-9_]*)', 
                      lambda m: str(self._variables.get(m.group(1), 0)), expr)
        
        # Replace standalone 'x' with raw value
        if x is not None:
            expr = re.sub(r'\bx\b', str(x), expr)
        
        # Replace function names
        expr = re.sub(r'\bpow\s*\(', '_math.pow(', expr)
        expr = re.sub(r'\babs\s*\(', 'abs(', expr)
        expr = re.sub(r'\bsqrt\s*\(', '_math.sqrt(', expr)
        expr = re.sub(r'\bmin\s*\(', 'min(', expr)
        expr = re.sub(r'\bmax\s*\(', 'max(', expr)
        
        # Replace 'and'/'or'
        expr = re.sub(r'\band\b', 'and', expr)
        expr = re.sub(r'\bor\b', 'or', expr)
        
        # Convert C-style ternary (cond ? true_val : false_val) to Python (true_val if cond else false_val)
        ternary_match = re.match(r'^(.+?)\s*\?\s*(.+?)\s*:\s*(.+)$', expr)
        if ternary_match:
            cond, true_val, false_val = ternary_match.groups()
            expr = f"({true_val}) if ({cond}) else ({false_val})"
        
        try:
            result = eval(expr, {"__builtins__": {}, "_math": _math, 
                                 "abs": abs, "min": min, "max": max,
                                 "True": True, "False": False})
            return float(result) if isinstance(result, (int, float)) else 0.0
        except Exception as e:
            raise ValueError(f"Formula evaluation failed: '{formula}' -> '{expr}': {e}")
    
    def _evaluate_polynomial(self, coefficients: List[float], x: float) -> float:
        """
        Evaluate polynomial using Horner's method for numerical stability.
        
        Coefficients are in descending power order: [a_n, a_{n-1}, ..., a_1, a_0]
        Result: a_n * x^n + a_{n-1} * x^(n-1) + ... + a_1 * x + a_0
        
        Horner's form: (((a_n * x + a_{n-1}) * x + a_{n-2}) * x + ...) * x + a_0
        """
        if not coefficients:
            return 0.0
        
        result = float(coefficients[0])
        for coef in coefficients[1:]:
            result = result * x + float(coef)
        return result
    
    def _evaluate_compute(self, compute_def: Dict[str, Any]) -> float:
        """
        Evaluate a cross-field binary computation.
        
        compute_def: {op: 'add'|'sub'|'mul'|'div'|'mod'|'idiv', a: '$field'|literal, b: '$field'|literal}
        """
        op = compute_def.get('op', 'add')
        a_spec = compute_def.get('a', 0)
        b_spec = compute_def.get('b', 0)
        
        # Resolve operands
        def resolve_operand(spec):
            if isinstance(spec, str) and spec.startswith('$'):
                field_name = spec[1:]
                return float(self._variables.get(field_name, 0))
            return float(spec)
        
        a = resolve_operand(a_spec)
        b = resolve_operand(b_spec)
        
        # Apply operation
        if op == 'add':
            return a + b
        elif op == 'sub':
            return a - b
        elif op == 'mul':
            return a * b
        elif op == 'div':
            if b == 0:
                return float('nan')
            return a / b
        elif op == 'mod':
            if b == 0:
                return float('nan')
            return float(int(a) % int(b))
        elif op == 'idiv':
            if b == 0:
                return float('nan')
            return float(int(a) // int(b))
        else:
            raise ValueError(f"Unknown compute op: {op}")
    
    def _evaluate_guard(self, guard_def: Dict[str, Any]) -> Tuple[bool, Any]:
        """
        Evaluate guard conditions.
        
        guard_def: {when: [{field: '$x', gt: 0}, ...], else: fallback}
        
        Returns: (conditions_passed, fallback_value)
        """
        when_conditions = guard_def.get('when', [])
        else_value = guard_def.get('else', None)
        
        for condition in when_conditions:
            field_ref = condition.get('field', '')
            if isinstance(field_ref, str) and field_ref.startswith('$'):
                field_name = field_ref[1:]
                field_value = float(self._variables.get(field_name, 0))
            else:
                continue  # Invalid condition
            
            # Check comparison operators
            passed = True
            if 'gt' in condition:
                passed = field_value > float(condition['gt'])
            elif 'gte' in condition:
                passed = field_value >= float(condition['gte'])
            elif 'lt' in condition:
                passed = field_value < float(condition['lt'])
            elif 'lte' in condition:
                passed = field_value <= float(condition['lte'])
            elif 'eq' in condition:
                passed = field_value == float(condition['eq'])
            elif 'ne' in condition:
                passed = field_value != float(condition['ne'])
            
            if not passed:
                return (False, else_value)
        
        return (True, else_value)
    
    def _resolve_ref_value(self, field_def: Dict[str, Any]) -> float:
        """
        Resolve a ref field and apply modifiers/polynomial/transform.
        
        field_def must have 'ref' key.
        """
        ref_field = field_def['ref']
        if isinstance(ref_field, str) and ref_field.startswith('$'):
            ref_name = ref_field[1:]
            value = float(self._variables.get(ref_name, 0))
        else:
            value = float(ref_field)
        
        # Apply polynomial if present
        if 'polynomial' in field_def:
            coeffs = field_def['polynomial']
            if isinstance(coeffs, list) and len(coeffs) >= 2:
                value = self._evaluate_polynomial(coeffs, value)
        
        # Apply basic modifiers (mult, div, add) in YAML key order
        for key in field_def:
            if key == 'mult' and field_def['mult'] is not None:
                value = value * field_def['mult']
            elif key == 'div' and field_def['div'] is not None and field_def['div'] != 0:
                value = value / field_def['div']
            elif key == 'add' and field_def['add'] is not None:
                value = value + field_def['add']
        
        # Apply transform array if present
        if 'transform' in field_def:
            value = self._apply_transform(value, field_def['transform'])
        
        return value
    
    def _apply_transform(self, value: float, transform_ops: List[Dict[str, Any]]) -> float:
        """
        Apply transform operations sequentially.
        
        Supported ops: sqrt, abs, pow, floor, ceiling, clamp, log10, log,
                       add, mult, div
        """
        import math
        
        for op in transform_ops:
            if 'sqrt' in op and op['sqrt']:
                value = math.sqrt(max(0, value))  # Clamp to avoid domain error
            elif 'abs' in op and op['abs']:
                value = abs(value)
            elif 'pow' in op:
                value = math.pow(value, float(op['pow']))
            elif 'floor' in op:  # Clamp lower bound (renamed from max)
                value = max(value, float(op['floor']))
            elif 'ceiling' in op:  # Clamp upper bound (renamed from min)
                value = min(value, float(op['ceiling']))
            elif 'clamp' in op:
                bounds = op['clamp']
                if isinstance(bounds, list) and len(bounds) >= 2:
                    value = max(float(bounds[0]), min(float(bounds[1]), value))
            elif 'log10' in op and op['log10']:
                value = math.log10(max(1e-10, value))  # Avoid domain error
            elif 'log' in op and op['log']:
                value = math.log(max(1e-10, value))  # Natural log
            elif 'add' in op:
                value = value + float(op['add'])
            elif 'mult' in op:
                value = value * float(op['mult'])
            elif 'div' in op and float(op['div']) != 0:
                value = value / float(op['div'])
            elif 'round' in op:
                decimals = op['round']
                if decimals is True or decimals == 0:
                    value = round(value)
                else:
                    value = round(value, int(decimals))
            elif 'op' in op:
                # Handle {op: 'round', decimals: N} syntax
                if op['op'] == 'round':
                    decimals = op.get('decimals', 0)
                    if decimals == 0:
                        value = round(value)
                    else:
                        value = round(value, int(decimals))
                elif op['op'] == 'floor':
                    value = math.floor(value)
                elif op['op'] == 'ceiling' or op['op'] == 'ceil':
                    value = math.ceil(value)
        
        return value
    
    def _decode_byte_group(self, field_def: Dict[str, Any], buf: bytes,
                           pos: int, result: DecodeResult) -> int:
        """
        Decode a byte_group - multiple bitfields sharing the same byte(s).
        
        byte_group automatically handles:
        - All fields read from same starting position
        - Advances position by group size after all fields decoded
        
        Supports two formats:
            # Format 1: List directly under byte_group
            - byte_group:
                - name: flags_low
                  type: u8[0:3]
              size: 1
            
            # Format 2: Nested fields key
            - byte_group:
                size: 1
                fields:
                  - name: flags_low
                    type: u8[0:3]
        """
        byte_group = field_def.get('byte_group', [])
        
        # Handle both formats
        if isinstance(byte_group, dict):
            # Format 2: {size: N, fields: [...]}
            group_fields = byte_group.get('fields', [])
            group_size = byte_group.get('size', 1)
        else:
            # Format 1: list of fields directly
            group_fields = byte_group
            group_size = field_def.get('size', 1)
        
        if not group_fields:
            return pos
        
        # Decode all fields from the same starting position
        for gf in group_fields:
            name = gf.get('name', 'unknown')
            
            # Force consume: 0 for all but track internally
            gf_copy = dict(gf)
            gf_copy['consume'] = 0
            
            try:
                value, _ = self._decode_field(gf_copy, buf, pos)
                value = self._apply_modifiers(value, gf)
                if not name.startswith('_'):
                    result.data[name] = value
                # Add to variables so field can be referenced by compute/formula
                self._variables[name] = value
            except Exception as e:
                result.errors.append(f"Error in byte_group field {name}: {e}")
        
        # Advance past the group
        return pos + group_size
    
    def _decode_nested_object_b(self, field_def: Dict[str, Any], buf: bytes,
                                 pos: int) -> Tuple[Dict[str, Any], int]:
        """Decode nested object using Option B syntax (object: key)."""
        nested_fields = field_def.get('fields', [])
        nested_result = {}
        
        for nf in nested_fields:
            if 'match' in nf and not nf.get('type'):
                match_result, pos = self._decode_match(nf, buf, pos)
                nested_result.update(match_result)
            elif 'object' in nf and not nf.get('type'):
                sub_name = nf['object']
                sub_result, pos = self._decode_nested_object_b(nf, buf, pos)
                nested_result[sub_name] = sub_result
            else:
                nf_name = nf.get('name', 'unknown')
                value, pos = self._decode_field(nf, buf, pos)
                if value is not None:
                    value = self._apply_modifiers(value, nf)
                    if not nf_name.startswith('_'):
                        nested_result[nf_name] = value
                if nf.get('var'):
                    self._variables[nf['var']] = value
        
        return nested_result, pos
    
    def _decode_tlv(self, field_def: Dict[str, Any], buf: bytes,
                    pos: int) -> Tuple[Dict[str, Any], int]:
        """
        Decode TLV (Type-Length-Value) loop using Option B syntax.
        
        tlv:
          tag_size: 1
          length_size: 0        # 0 = implicit (no length field)
          merge: true           # merge into parent (default)
          unknown: skip|error|raw
          cases:
            0x01:
              - name: temperature
                type: s16
        """
        tlv_def = field_def.get('tlv', {})
        tag_size = tlv_def.get('tag_size', 1)
        length_size = tlv_def.get('length_size', 0)
        merge = tlv_def.get('merge', True)
        unknown_mode = tlv_def.get('unknown', 'skip')
        cases = tlv_def.get('cases', {})
        tag_fields = tlv_def.get('tag_fields')
        tag_key = tlv_def.get('tag_key')
        
        result = {}
        channels = []
        
        while pos < len(buf):
            # Read tag
            if pos + tag_size > len(buf):
                break
            
            if tag_fields and tag_key:
                # Composite tag: read sub-fields
                tag_parts = {}
                tag_start = pos
                for tf in tag_fields:
                    tf_name = tf.get('name', 'unknown')
                    tf_value, pos = self._decode_field(tf, buf, pos)
                    tag_parts[tf_name] = tf_value
                
                # Build composite key for matching
                if isinstance(tag_key, list):
                    tag_tuple = tuple(tag_parts[k] for k in tag_key)
                else:
                    tag_tuple = (tag_parts[tag_key],)
            else:
                # Simple tag
                if tag_size == 1:
                    tag_value = buf[pos]
                elif tag_size == 2:
                    if self.endian == Endian.LITTLE:
                        tag_value = buf[pos] | (buf[pos + 1] << 8)
                    else:
                        tag_value = (buf[pos] << 8) | buf[pos + 1]
                else:
                    tag_value = int.from_bytes(buf[pos:pos + tag_size],
                        'little' if self.endian == Endian.LITTLE else 'big')
                pos += tag_size
                tag_tuple = (tag_value,)
            
            # Read length if present
            data_length = None
            if length_size > 0:
                if pos + length_size > len(buf):
                    break
                if length_size == 1:
                    data_length = buf[pos]
                elif length_size == 2:
                    if self.endian == Endian.LITTLE:
                        data_length = buf[pos] | (buf[pos + 1] << 8)
                    else:
                        data_length = (buf[pos] << 8) | buf[pos + 1]
                pos += length_size
            
            # Find matching case
            matched_fields = None
            for case_key, case_fields in cases.items():
                if case_key == 'default':
                    continue
                # Normalize case key for comparison
                if isinstance(case_key, (list, tuple)):
                    if tuple(case_key) == tag_tuple:
                        matched_fields = case_fields
                        break
                elif isinstance(case_key, str) and case_key.startswith('['):
                    # Parse string representation of composite tag e.g. "[1, 117]"
                    try:
                        parsed = tuple(json.loads(case_key))
                        if parsed == tag_tuple:
                            matched_fields = case_fields
                            break
                    except (json.JSONDecodeError, TypeError):
                        pass
                elif len(tag_tuple) == 1 and self._match_case_pattern(tag_tuple[0], case_key):
                    matched_fields = case_fields
                    break
            
            if matched_fields is None:
                if unknown_mode == 'error':
                    raise ValueError(f"Unknown TLV tag: {tag_tuple}")
                elif unknown_mode == 'skip':
                    if data_length is not None:
                        pos += data_length
                    else:
                        break  # Can't skip without length
                elif unknown_mode == 'raw':
                    if data_length is not None:
                        raw = buf[pos:pos + data_length].hex().upper()
                        channels.append({'tag': list(tag_tuple), 'raw': raw})
                        pos += data_length
                    else:
                        break
                continue
            
            # Decode fields for this tag
            tag_result = {}
            for cf in matched_fields:
                cf_name = cf.get('name', 'unknown')
                cf_type = cf.get('type', 'u8')
                
                # Handle bitfield_string inside TLV cases
                if cf_type == 'bitfield_string':
                    value, pos = self._decode_bitfield_string(cf, buf, pos)
                    if not cf_name.startswith('_'):
                        tag_result[cf_name] = value
                    continue
                
                value, pos = self._decode_field(cf, buf, pos)
                if value is not None:
                    value = self._apply_modifiers(value, cf)
                    if not cf_name.startswith('_'):
                        tag_result[cf_name] = value
            
            if merge:
                for k, v in tag_result.items():
                    if k in result:
                        # Repeated tag -> collect into array
                        if isinstance(result[k], list):
                            result[k].append(v)
                        else:
                            result[k] = [result[k], v]
                    else:
                        result[k] = v
            else:
                entry = {'tag': list(tag_tuple)}
                entry.update(tag_result)
                channels.append(entry)
        
        if not merge and channels:
            result['channels'] = channels
        
        return result, pos
    
    def _check_valid_range(self, value: Any, field_def: Dict[str, Any], 
                           result: 'DecodeResult') -> str:
        """
        Check if value is within valid_range and update quality.
        
        Returns: "good" if in range (or no range defined), "out_of_range" otherwise
        """
        valid_range = field_def.get('valid_range')
        name = field_def.get('name', 'unknown')
        
        if valid_range is None or not isinstance(value, (int, float)):
            return "good"
        
        if not isinstance(valid_range, list) or len(valid_range) < 2:
            return "good"
        
        min_val, max_val = valid_range[0], valid_range[1]
        
        if value < min_val or value > max_val:
            result.warnings.append(
                f"{name}: value {value} outside valid range [{min_val}, {max_val}]"
            )
            return "out_of_range"
        
        return "good"
    
    def _apply_modifiers(self, value: Any, field_def: Dict[str, Any]) -> Any:
        """Apply arithmetic modifiers to decoded value."""
        if not isinstance(value, (int, float)):
            return value
        
        # Formula takes precedence - use sandboxed evaluator (DEPRECATED)
        formula = field_def.get('formula')
        if formula:
            import warnings
            warnings.warn(
                f"Field '{field_def.get('name', 'unknown')}': 'formula' is deprecated. "
                "Use 'polynomial', 'compute', or 'transform' instead.",
                DeprecationWarning
            )
            try:
                value = self._evaluate_formula(formula, x=value)
            except ValueError:
                pass  # Keep original value on formula error
            return value
        
        # Apply modifiers in YAML key order (dict preserves insertion order in Python 3.7+)
        for key in field_def:
            if key == 'mult' and field_def['mult'] is not None:
                value = value * field_def['mult']
            elif key == 'div' and field_def['div'] is not None and field_def['div'] != 0:
                value = value / field_def['div']
            elif key == 'add' and field_def['add'] is not None:
                value = value + field_def['add']
        
        # Apply transform array (new declarative constructs)
        transform = field_def.get('transform')
        if transform and isinstance(transform, list):
            value = self._apply_transform(float(value), transform)
        
        # Apply lookup table
        lookup = field_def.get('lookup')
        if lookup and isinstance(value, int) and 0 <= value < len(lookup):
            value = lookup[value]
        
        return value
    
    def decode(self, payload: bytes, fPort: int = None, input_metadata: Dict[str, Any] = None) -> DecodeResult:
        """
        Decode payload bytes using schema.
        
        Args:
            payload: Raw payload bytes
            fPort: LoRaWAN fPort (for port-based schema selection)
            input_metadata: Optional TS013 input metadata (recvTime, rxMetadata, etc.)
            
        Returns:
            DecodeResult with decoded data
        """
        result = DecodeResult(data={}, bytes_consumed=0)
        
        # Reset bitfield state
        self._bit_pos = 0
        self._current_byte = 0
        self._current_byte_pos = -1
        
        # Track current data for match references
        self._current_data = result.data
        # Variable storage for Option B match references
        self._variables = {}
        
        pos = 0
        fields = self._resolve_fields(fPort)
        
        for field_def in fields:
            # Handle $ref - inline the referenced definition
            if '$ref' in field_def:
                try:
                    ref_def = self._resolve_ref(field_def['$ref'])
                    ref_fields = ref_def.get('fields', [])
                    for rf in ref_fields:
                        rf_name = rf.get('name', 'unknown')
                        if not rf_name.startswith('_'):
                            value, pos = self._decode_field(rf, payload, pos)
                            value = self._apply_modifiers(value, rf)
                            if value is not None:
                                result.data[rf_name] = value
                        else:
                            _, pos = self._decode_field(rf, payload, pos)
                except Exception as e:
                    result.errors.append(f"Error resolving $ref: {e}")
                continue
            
            # Handle byte_group construct
            if 'byte_group' in field_def:
                pos = self._decode_byte_group(field_def, payload, pos, result)
                continue
            
            # Option B: match: as top-level key
            if 'match' in field_def and not field_def.get('type'):
                try:
                    match_result, pos = self._decode_match(field_def, payload, pos)
                    result.data.update(match_result)
                except Exception as e:
                    result.errors.append(f"Error in match: {e}")
                continue
            
            # Option B: object: as top-level key
            if 'object' in field_def and not field_def.get('type'):
                try:
                    obj_name = field_def['object']
                    nested_fields = field_def.get('fields', [])
                    nested_result = {}
                    saved_data = self._current_data
                    # nested object still adds vars to top-level scope
                    for nf in nested_fields:
                        # Recursively handle Option B constructs in nested fields
                        if 'match' in nf and not nf.get('type'):
                            match_result, pos = self._decode_match(nf, payload, pos)
                            nested_result.update(match_result)
                        elif 'object' in nf and not nf.get('type'):
                            sub_name = nf['object']
                            sub_result, pos = self._decode_nested_object_b(nf, payload, pos)
                            nested_result[sub_name] = sub_result
                        else:
                            nf_name = nf.get('name', 'unknown')
                            value, pos = self._decode_field(nf, payload, pos)
                            if value is not None:
                                value = self._apply_modifiers(value, nf)
                                if not nf_name.startswith('_'):
                                    nested_result[nf_name] = value
                            # Store variable if var: specified
                            if nf.get('var'):
                                self._variables[nf['var']] = value
                    self._current_data = saved_data
                    result.data[obj_name] = nested_result
                except Exception as e:
                    result.errors.append(f"Error in object '{field_def.get('object')}': {e}")
                continue
            
            # Option B: tlv: as top-level key
            if 'tlv' in field_def and not field_def.get('type'):
                try:
                    tlv_result, pos = self._decode_tlv(field_def, payload, pos)
                    result.data.update(tlv_result)
                except Exception as e:
                    result.errors.append(f"Error in tlv: {e}")
                continue
            
            # Phase 2: flagged: construct (bitmask field presence)
            if 'flagged' in field_def and not field_def.get('type'):
                try:
                    flagged_def = field_def['flagged']
                    flagged_result, pos = self._decode_flagged(flagged_def, payload, pos)
                    result.data.update(flagged_result)
                    # Store flagged fields as variables and check valid_range
                    for k, v in flagged_result.items():
                        self._variables[k] = v
                    # Check valid_range for fields in flagged groups
                    for group in flagged_def.get('groups', []):
                        for gf in group.get('fields', []):
                            gf_name = gf.get('name')
                            if gf_name and gf_name in flagged_result and gf.get('valid_range'):
                                quality = self._check_valid_range(flagged_result[gf_name], gf, result)
                                result.quality[gf_name] = quality
                except Exception as e:
                    result.errors.append(f"Error in flagged: {e}")
                continue
            
            name = field_def.get('name', 'unknown')
            field_type = field_def.get('type', 'u8')
            
            # Phase 2: bitfield_string type
            if field_type == 'bitfield_string':
                try:
                    value, pos = self._decode_bitfield_string(field_def, payload, pos)
                    result.data[name] = value
                    self._variables[name] = value
                except Exception as e:
                    result.errors.append(f"Error decoding {name}: {e}")
                continue
            
            # Computed field (type: number) - supports formula, ref, polynomial, compute, guard
            if field_type == 'number':
                try:
                    value = self._decode_computed_field(field_def)
                    if value is not None:
                        result.data[name] = value
                        self._variables[name] = value
                        # Check valid_range for computed fields
                        if field_def.get('valid_range'):
                            quality = self._check_valid_range(value, field_def, result)
                            result.quality[name] = quality
                except Exception as e:
                    result.errors.append(f"Error computing {name}: {e}")
                continue
            
            # Handle match at field level (legacy: no name, type: match)
            if field_type == 'match' and name == 'unknown':
                try:
                    match_result, pos = self._decode_match(field_def, payload, pos)
                    result.data.update(match_result)
                except Exception as e:
                    result.errors.append(f"Error in match: {e}")
                continue
            
            # Skip internal fields
            if name.startswith('_'):
                try:
                    _, pos = self._decode_field(field_def, payload, pos)
                except Exception as e:
                    result.errors.append(f"Error in internal field: {e}")
                continue
            
            try:
                value, pos = self._decode_field(field_def, payload, pos)
                # Skip type returns None - don't add to output
                if value is not None:
                    # Formula takes precedence over mult/add/div modifiers
                    if field_def.get('formula'):
                        value = self._evaluate_formula(field_def['formula'], value)
                    else:
                        value = self._apply_modifiers(value, field_def)
                    result.data[name] = value
                    # Check valid_range and update quality
                    if field_def.get('valid_range'):
                        quality = self._check_valid_range(value, field_def, result)
                        result.quality[name] = quality
                    # Store variable if var: specified (Option B)
                    if field_def.get('var'):
                        self._variables[field_def['var']] = value
                    # Always store by field name (for flagged/formula lookups)
                    self._variables[name] = value
            except Exception as e:
                result.errors.append(f"Error decoding {name}: {e}")
                break
        
        result.bytes_consumed = pos
        
        # Metadata enrichment
        metadata_def = self.schema.get('metadata')
        if metadata_def and input_metadata is not None:
            self._enrich_metadata(result.data, metadata_def, input_metadata)
        
        # Add quality dict to output if any quality flags were set
        if result.quality:
            result.data['_quality'] = dict(result.quality)
        
        return result
    
    def _resolve_metadata_ref(self, ref: str, input_meta: Dict[str, Any]) -> Any:
        """Resolve a $ metadata reference against TS013 input."""
        if not isinstance(ref, str) or not ref.startswith('$'):
            return None
        path = ref[1:]  # Remove $
        import re as _re
        path = _re.sub(r'\[(\d+)\]', r'.\1', path)
        parts = path.split('.')
        current = input_meta
        for part in parts:
            if current is None:
                return None
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, (list, tuple)):
                try:
                    current = current[int(part)]
                except (IndexError, ValueError):
                    return None
            else:
                return None
        return current
    
    def _enrich_metadata(self, data: Dict[str, Any], metadata_def: Dict[str, Any],
                         input_meta: Dict[str, Any]) -> None:
        """Enrich decoded data with network metadata from TS013 input."""
        from datetime import datetime, timedelta, timezone
        
        # Include mappings
        for mapping in metadata_def.get('include', []):
            name = mapping.get('name')
            source = mapping.get('source')
            if name and source:
                value = self._resolve_metadata_ref(source, input_meta)
                if value is not None:
                    data[name] = value
        
        # Timestamp enrichment
        for ts in metadata_def.get('timestamps', []):
            name = ts.get('name', 'timestamp')
            mode = ts.get('mode')
            
            if mode == 'rx_time' or ts.get('source') == '$recvTime':
                data[name] = input_meta.get('recvTime')
            
            elif mode == 'subtract':
                offset_field = ts.get('offset_field')
                recv_time = input_meta.get('recvTime')
                if recv_time and offset_field and offset_field in data:
                    try:
                        rx_dt = datetime.fromisoformat(recv_time.replace('Z', '+00:00'))
                        offset_sec = data[offset_field]
                        meas_dt = rx_dt - timedelta(seconds=offset_sec)
                        data[name] = meas_dt.strftime('%Y-%m-%dT%H:%M:%S.') + \
                            f'{meas_dt.microsecond // 1000:03d}Z'
                    except Exception:
                        pass
            
            elif mode == 'unix_epoch':
                field = ts.get('field')
                if field and field in data:
                    try:
                        dt = datetime.fromtimestamp(data[field], tz=timezone.utc)
                        data[name] = dt.strftime('%Y-%m-%dT%H:%M:%S.') + \
                            f'{dt.microsecond // 1000:03d}Z'
                    except Exception:
                        pass
            
            elif mode == 'iso8601':
                # Format a raw epoch/offset field as ISO 8601 string
                field = ts.get('field')
                fmt = ts.get('format', '%Y-%m-%dT%H:%M:%SZ')
                if field and field in data:
                    try:
                        dt = datetime.fromtimestamp(data[field], tz=timezone.utc)
                        data[name] = dt.strftime(fmt)
                    except Exception:
                        pass
            
            elif mode == 'elapsed_to_absolute':
                # Convert elapsed seconds to absolute time: rx_time - elapsed
                elapsed_field = ts.get('elapsed_field') or ts.get('offset_field')
                time_base = ts.get('time_base', 'rx_time')
                recv_time = input_meta.get('recvTime') if time_base == 'rx_time' else None
                if recv_time and elapsed_field and elapsed_field in data:
                    try:
                        rx_dt = datetime.fromisoformat(recv_time.replace('Z', '+00:00'))
                        offset_sec = data[elapsed_field]
                        abs_dt = rx_dt - timedelta(seconds=offset_sec)
                        data[name] = abs_dt.strftime('%Y-%m-%dT%H:%M:%S.') + \
                            f'{abs_dt.microsecond // 1000:03d}Z'
                    except Exception:
                        pass
    
    def encode(self, data: Dict[str, Any], fPort: int = None) -> EncodeResult:
        """
        Encode data dict to payload bytes using schema.
        
        Args:
            data: Dictionary of field values
            fPort: Optional LoRaWAN fPort for port-based schema selection
            
        Returns:
            EncodeResult with encoded payload
        """
        result = EncodeResult(payload=b'')
        output = bytearray()
        
        fields = self._resolve_fields(fPort)
        
        # Pre-scan for flagged constructs to compute flags values
        flags_patches = {}
        for field_def in fields:
            if 'flagged' in field_def:
                flagged_def = field_def['flagged']
                field_name = flagged_def.get('field', '')
                groups = flagged_def.get('groups', [])
                flags = 0
                for group in groups:
                    bit = group.get('bit', 0)
                    group_fields = group.get('fields', [])
                    if any(gf.get('name') and gf['name'] in data for gf in group_fields):
                        flags |= (1 << bit)
                flags_patches[field_name] = flags
        
        for field_def in fields:
            # Flagged construct
            if 'flagged' in field_def:
                encoded = self._encode_flagged(field_def['flagged'], data)
                output.extend(encoded)
                continue
            
            name = field_def.get('name', 'unknown')
            field_type = field_def.get('type', 'u8')
            
            # Skip computed fields
            if field_type == 'number' and field_def.get('formula'):
                continue
            
            # Bitfield string encoding
            if field_type == 'bitfield_string':
                value = data.get(name, '')
                encoded = self._encode_bitfield_string(field_def, str(value))
                output.extend(encoded)
                continue
            
            # Version string encoding
            if field_type == 'version_string':
                value = data.get(name, '')
                encoded = self._encode_version_string(field_def, str(value))
                output.extend(encoded)
                continue
            
            # Skip type: emit zero bytes, no input needed
            if field_type == 'skip':
                length = field_def.get('length', 1)
                output.extend(bytes(length))
                continue
            
            # Skip internal fields - use default or 0
            if name.startswith('_'):
                default = field_def.get('default', 0)
                value = default
            elif name in flags_patches:
                value = flags_patches[name]
            else:
                value = data.get(name)
                if value is None:
                    result.warnings.append(f"Missing field: {name}")
                    value = 0
            
            try:
                # Reverse modifiers
                value = self._reverse_modifiers(value, field_def)
                
                encoded = self._encode_field(field_def, value)
                output.extend(encoded)
            except Exception as e:
                result.errors.append(f"Error encoding {name}: {e}")
        
        result.payload = bytes(output)
        return result
    
    def _encode_flagged(self, flagged_def: Dict[str, Any], data: Dict[str, Any]) -> bytes:
        """Encode flagged groups: only encode groups where data is present."""
        groups = flagged_def.get('groups', [])
        output = bytearray()
        
        for group in groups:
            bit = group.get('bit', 0)
            group_fields = group.get('fields', [])
            has_data = any(gf.get('name') and gf['name'] in data for gf in group_fields)
            if not has_data:
                continue
            for gf in group_fields:
                gf_name = gf.get('name', '')
                gf_type = gf.get('type', 'u8')
                if not gf_name or gf_name.startswith('_'):
                    continue
                if gf_type == 'number' and gf.get('formula'):
                    continue
                value = data.get(gf_name, 0)
                value = self._reverse_modifiers(value, gf)
                output.extend(self._encode_field(gf, value))
        
        return bytes(output)
    
    def _encode_bitfield_string(self, field_def: Dict[str, Any], value: str) -> bytes:
        """Encode bitfield_string: parse string back into packed integer bytes."""
        parts = field_def.get('parts', [])
        delimiter = field_def.get('delimiter', '.')
        prefix = field_def.get('prefix', '')
        length = field_def.get('length', 2)
        
        if prefix and value.startswith(prefix):
            value = value[len(prefix):]
        
        segments = value.split(delimiter)
        int_val = 0
        
        for i, part in enumerate(parts):
            if len(part) < 2:
                continue
            bit_off = int(part[0])
            bit_len = int(part[1])
            fmt = part[2] if len(part) > 2 else 'decimal'
            seg = segments[i] if i < len(segments) else '0'
            val = int(seg, 16) if fmt == 'hex' else int(seg)
            mask = (1 << bit_len) - 1
            int_val |= (val & mask) << bit_off
        
        return self._write_int(int_val, length, signed=False)
    
    def _encode_version_string(self, field_def: Dict[str, Any], value: str) -> bytes:
        """Phase 3: Encode version_string back to bytes."""
        length = field_def.get('length', 3)
        delimiter = field_def.get('delimiter', '.')
        prefix = field_def.get('prefix', '')
        
        if prefix and value.startswith(prefix):
            value = value[len(prefix):]
        
        segments = value.split(delimiter)
        output = bytearray(length)
        for i in range(min(length, len(segments))):
            try:
                output[i] = int(segments[i]) & 0xFF
            except ValueError:
                output[i] = 0
        
        return bytes(output)
    
    def _reverse_modifiers(self, value: Any, field_def: Dict[str, Any]) -> Any:
        """Reverse arithmetic modifiers for encoding."""
        if not isinstance(value, (int, float)):
            return value
        
        # Phase 3: encode_formula takes precedence
        encode_formula = field_def.get('encode_formula')
        if encode_formula:
            return int(round(self._evaluate_encode_formula(encode_formula, value)))
        
        # Reverse lookup
        lookup = field_def.get('lookup')
        if lookup:
            try:
                value = lookup.index(value)
            except ValueError:
                pass
        
        # Reverse modifiers in reverse YAML key order with inverse operations
        mod_keys = [k for k in field_def if k in ('add', 'mult', 'div')]
        for key in reversed(mod_keys):
            if key == 'add' and field_def['add'] is not None:
                value = value - field_def['add']
            elif key == 'div' and field_def['div'] is not None and field_def['div'] != 0:
                value = value * field_def['div']
            elif key == 'mult' and field_def['mult'] is not None and field_def['mult'] != 0:
                value = value / field_def['mult']
        
        # Float types should preserve fractional values
        field_type = field_def.get('type', 'u8')
        if field_type in ('f16', 'f32', 'float', 'f64', 'double'):
            return float(value)
        
        return int(round(value))
    
    def _encode_field(self, field_def: Dict[str, Any], value: Any) -> bytes:
        """Encode a single field value."""
        field_type = field_def.get('type', 'u8')
        
        # Handle bitfields - simplified (just return byte with value)
        if any(c in str(field_type) for c in ['[', ':', '<']):
            return bytes([int(value) & 0xFF])
        
        # Type info with all aliases (must match decoder)
        type_info = {
            # Unsigned (canonical: u prefix)
            'u8': (1, False), 'uint8': (1, False),
            'u16': (2, False), 'uint16': (2, False),
            'u24': (3, False), 'uint24': (3, False),
            'u32': (4, False), 'uint32': (4, False),
            'u64': (8, False), 'uint64': (8, False),
            # Signed (canonical: s prefix, aliases: i prefix, int prefix)
            's8': (1, True), 'i8': (1, True), 'int8': (1, True),
            's16': (2, True), 'i16': (2, True), 'int16': (2, True),
            's24': (3, True), 'i24': (3, True), 'int24': (3, True),
            's32': (4, True), 'i32': (4, True), 'int32': (4, True),
            's64': (8, True), 'i64': (8, True), 'int64': (8, True),
        }
        
        if field_type in type_info:
            size, signed = type_info[field_type]
            int_val = int(value)
            # Apply encoding if specified (sign_magnitude, bcd, gray)
            encoding = field_def.get('encoding')
            if encoding:
                int_val = self._encode_encoding(int_val, encoding, size)
                # Encoded values are written as unsigned
                signed = False
            return self._write_int(int_val, size, signed)
        
        if field_type == 'f16':
            fmt = '<e' if self.endian == Endian.LITTLE else '>e'
            return struct.pack(fmt, float(value))
        
        if field_type in ('f32', 'float'):
            fmt = '<f' if self.endian == Endian.LITTLE else '>f'
            return struct.pack(fmt, float(value))
        
        if field_type in ('f64', 'double'):
            fmt = '<d' if self.endian == Endian.LITTLE else '>d'
            return struct.pack(fmt, float(value))
        
        if field_type == 'bool':
            return bytes([1 if value else 0])
        
        if field_type == 'skip':
            length = field_def.get('length', 1)
            return bytes(length)
        
        if field_type == 'bytes':
            length = field_def.get('length', len(value))
            if isinstance(value, bytes):
                return value[:length].ljust(length, b'\x00')
            return bytes(length)
        
        if field_type in ('string', 'ascii'):
            length = field_def.get('length', len(str(value)))
            encoded = str(value).encode('utf-8')[:length]
            return encoded.ljust(length, b'\x00')
        
        if field_type == 'hex':
            length = field_def.get('length', len(str(value)) // 2)
            return bytes.fromhex(str(value).replace(' ', ''))[:length].ljust(length, b'\x00')
        
        if field_type == 'base64':
            import base64 as b64
            length = field_def.get('length', 0)
            decoded = b64.b64decode(str(value))
            if length:
                return decoded[:length].ljust(length, b'\x00')
            return decoded
        
        if field_type == 'version_string':
            return self._encode_version_string(field_def, str(value))
        
        if field_type == 'enum':
            return self._encode_enum(field_def, value)
        
        raise ValueError(f"Cannot encode type: {field_type}")
    
    def _encode_enum(self, field_def: Dict[str, Any], value: Any) -> bytes:
        """Encode enum field: map string value back to integer."""
        base_type = field_def.get('base', 'u8')
        values = field_def.get('values', {})
        
        # Find the integer value for the string
        int_value = None
        
        if isinstance(values, dict):
            # Reverse lookup: string -> int
            for k, v in values.items():
                if v == value:
                    int_value = int(k) if isinstance(k, str) else k
                    break
        elif isinstance(values, list):
            # Find index of value
            if value in values:
                int_value = values.index(value)
        
        if int_value is None:
            # Try parsing as integer (e.g., "unknown(5)")
            if isinstance(value, str) and value.startswith('unknown('):
                try:
                    int_value = int(value[8:-1])
                except ValueError:
                    raise ValueError(f"Cannot encode unknown enum value: {value}")
            elif isinstance(value, int):
                int_value = value
            else:
                raise ValueError(f"Enum value not found: {value}")
        
        # Encode as base type
        base_field = {'type': base_type}
        return self._encode_field(base_field, int_value)
    
    def encode_command(self, command_name: str, data: Dict[str, Any] = None) -> EncodeResult:
        """
        Encode a downlink command by name.
        
        Args:
            command_name: Name of the command (from downlink_commands)
            data: Command parameters (field values)
            
        Returns:
            EncodeResult with encoded payload starting with command_id
        """
        result = EncodeResult(payload=b'')
        data = data or {}
        
        if command_name not in self.downlink_commands:
            result.errors.append(f"Unknown command: {command_name}")
            return result
        
        cmd_def = self.downlink_commands[command_name]
        command_id = cmd_def.get('command_id', 0)
        fields = cmd_def.get('fields', [])
        
        output = bytearray()
        
        # Write command_id as first byte
        if isinstance(command_id, int):
            output.append(command_id & 0xFF)
        elif isinstance(command_id, str) and command_id.startswith('0x'):
            output.append(int(command_id, 16) & 0xFF)
        
        # Encode command fields
        for field_def in fields:
            name = field_def.get('name', '_')
            if name.startswith('_'):
                continue
            
            value = data.get(name, 0)
            if value is None:
                result.warnings.append(f"Missing command field: {name}")
                value = 0
            
            try:
                value = self._reverse_modifiers(value, field_def)
                encoded = self._encode_field(field_def, value)
                output.extend(encoded)
            except Exception as e:
                result.errors.append(f"Error encoding command field {name}: {e}")
        
        result.payload = bytes(output)
        return result
    
    def decode_command(self, payload: bytes) -> DecodeResult:
        """
        Decode a downlink command from payload.
        
        First byte is command_id, followed by command-specific fields.
        
        Returns:
            DecodeResult with decoded data including '_command' name
        """
        result = DecodeResult(data={}, bytes_consumed=0)
        
        if len(payload) < 1:
            result.errors.append("Payload too short for command_id")
            return result
        
        command_id = payload[0]
        pos = 1
        
        # Find matching command by command_id
        matched_cmd = None
        matched_name = None
        for cmd_name, cmd_def in self.downlink_commands.items():
            cmd_id = cmd_def.get('command_id', -1)
            if isinstance(cmd_id, str) and cmd_id.startswith('0x'):
                cmd_id = int(cmd_id, 16)
            if cmd_id == command_id:
                matched_cmd = cmd_def
                matched_name = cmd_name
                break
        
        if matched_cmd is None:
            result.errors.append(f"Unknown command_id: 0x{command_id:02X}")
            result.data['_command_id'] = command_id
            result.bytes_consumed = 1
            return result
        
        result.data['_command'] = matched_name
        result.data['_command_id'] = command_id
        
        # Decode command fields
        fields = matched_cmd.get('fields', [])
        for field_def in fields:
            name = field_def.get('name', 'unknown')
            try:
                value, pos = self._decode_field(field_def, payload, pos)
                if value is not None:
                    value = self._apply_modifiers(value, field_def)
                    if not name.startswith('_'):
                        result.data[name] = value
            except Exception as e:
                result.errors.append(f"Error decoding command field {name}: {e}")
                break
        
        result.bytes_consumed = pos
        return result
    
    def list_commands(self) -> Dict[str, Dict[str, Any]]:
        """
        List available downlink commands with their metadata.
        
        Returns:
            Dict mapping command names to their definitions
        """
        commands = {}
        for cmd_name, cmd_def in self.downlink_commands.items():
            cmd_id = cmd_def.get('command_id', 0)
            if isinstance(cmd_id, str) and cmd_id.startswith('0x'):
                cmd_id = int(cmd_id, 16)
            
            fields = []
            for f in cmd_def.get('fields', []):
                field_info = {'name': f.get('name'), 'type': f.get('type', 'u8')}
                if 'unit' in f:
                    field_info['unit'] = f['unit']
                fields.append(field_info)
            
            commands[cmd_name] = {
                'command_id': cmd_id,
                'fields': fields,
            }
        return commands
    
    def get_field_metadata(self, field_name: str = None) -> Dict[str, Any]:
        """
        Get semantic metadata for schema fields.
        
        Args:
            field_name: Specific field name, or None for all fields
            
        Returns:
            Metadata dict with unit, valid_range, resolution, unece, ipso, etc.
        """
        def extract_metadata(field_def: Dict[str, Any]) -> Dict[str, Any]:
            meta = {}
            for key in ('unit', 'valid_range', 'resolution', 'unece', 
                       'description', 'semantic', 'ipso', 'senml_unit'):
                if key in field_def:
                    meta[key] = field_def[key]
            # Flatten semantic sub-dict
            if 'semantic' in meta:
                for k, v in meta.pop('semantic').items():
                    meta[k] = v
            return meta
        
        def collect_fields(fields: List[Dict[str, Any]], result: Dict[str, Dict]):
            for field_def in fields:
                name = field_def.get('name')
                if name:
                    meta = extract_metadata(field_def)
                    if meta:
                        result[name] = meta
                # Recurse into nested structures
                if 'fields' in field_def:
                    collect_fields(field_def['fields'], result)
                if 'byte_group' in field_def:
                    collect_fields(field_def['byte_group'], result)
        
        all_metadata = {}
        collect_fields(self.schema.get('fields', []), all_metadata)
        
        if field_name:
            return all_metadata.get(field_name, {})
        return all_metadata
    
    def get_semantic_output(self, decoded: Dict[str, Any], 
                           format: str = 'ipso') -> Dict[str, Any]:
        """
        Convert decoded data to semantic format.
        
        Args:
            decoded: Decoded field values
            format: 'ipso', 'senml', or 'ttn'
            
        Returns:
            Semantically formatted output
        """
        fields = self.schema.get('fields', [])
        
        if format == 'ipso':
            return self._to_ipso(decoded, fields)
        elif format == 'senml':
            return self._to_senml(decoded, fields)
        elif format == 'ttn':
            return self._to_ttn(decoded, fields)
        else:
            return decoded
    
    def _to_ipso(self, decoded: Dict[str, Any], 
                 fields: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert to IPSO Smart Object format."""
        result = {}
        
        for field_def in fields:
            name = field_def.get('name')
            if name not in decoded:
                continue
            
            semantic = field_def.get('semantic', {})
            ipso = semantic.get('ipso')
            
            if ipso:
                obj_id = str(ipso)
                if obj_id not in result:
                    result[obj_id] = {}
                result[obj_id]['value'] = decoded[name]
                
                unit = field_def.get('unit')
                if unit:
                    result[obj_id]['unit'] = unit
            else:
                result[name] = decoded[name]
        
        return result
    
    def _to_senml(self, decoded: Dict[str, Any], 
                  fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert to SenML format."""
        records = []
        
        for field_def in fields:
            name = field_def.get('name')
            if name not in decoded:
                continue
            
            record = {'n': name}
            value = decoded[name]
            
            if isinstance(value, bool):
                record['vb'] = value
            elif isinstance(value, (int, float)):
                record['v'] = value
            elif isinstance(value, str):
                record['vs'] = value
            elif isinstance(value, bytes):
                record['vd'] = value.hex()
            else:
                record['v'] = value
            
            unit = field_def.get('unit')
            if unit:
                record['u'] = unit
            
            records.append(record)
        
        return records
    
    def _to_ttn(self, decoded: Dict[str, Any], 
                fields: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert to TTN normalized format."""
        return {
            'decoded_payload': decoded,
            'normalized_payload': [
                {
                    'measurement': {
                        field_def.get('name'): {
                            'value': decoded.get(field_def.get('name')),
                            'unit': field_def.get('unit', ''),
                        }
                    }
                }
                for field_def in fields
                if field_def.get('name') in decoded
            ]
        }


def decode_payload(schema: Dict[str, Any], payload: bytes) -> Dict[str, Any]:
    """Convenience function to decode payload."""
    interpreter = SchemaInterpreter(schema)
    result = interpreter.decode(payload)
    if not result.success:
        raise ValueError(f"Decode errors: {result.errors}")
    return result.data


def encode_payload(schema: Dict[str, Any], data: Dict[str, Any]) -> bytes:
    """Convenience function to encode data."""
    interpreter = SchemaInterpreter(schema)
    result = interpreter.encode(data)
    if not result.success:
        raise ValueError(f"Encode errors: {result.errors}")
    return result.payload


if __name__ == '__main__':
    # Demo
    print("=== Schema Interpreter Demo ===\n")
    
    schema = {
        'name': 'env_sensor',
        'endian': 'big',
        'fields': [
            {'name': 'temperature', 'type': 's16', 'mult': 0.01, 'unit': '°C',
             'semantic': {'ipso': 3303}},
            {'name': 'humidity', 'type': 'u8', 'mult': 0.5, 'unit': '%RH',
             'semantic': {'ipso': 3304}},
            {'name': 'battery_mv', 'type': 'u16', 'unit': 'mV',
             'semantic': {'ipso': 3316}},
            {'name': 'status', 'type': 'u8'},
        ]
    }
    
    # Sample payload: temp=23.45°C, humidity=65%, battery=3300mV, status=0
    # temp: 2345 (0x0929), hum: 130 (0x82), batt: 3300 (0x0CE4), status: 0
    payload = bytes([0x09, 0x29, 0x82, 0x0C, 0xE4, 0x00])
    
    interpreter = SchemaInterpreter(schema)
    
    print(f"Schema: {schema['name']}")
    print(f"Payload: {payload.hex().upper()}")
    print(f"Payload length: {len(payload)} bytes\n")
    
    result = interpreter.decode(payload)
    print("Decoded:")
    for k, v in result.data.items():
        print(f"  {k}: {v}")
    
    print(f"\nBytes consumed: {result.bytes_consumed}")
    
    # Semantic outputs
    print("\n--- IPSO Format ---")
    ipso = interpreter.get_semantic_output(result.data, 'ipso')
    for obj_id, obj in ipso.items():
        if isinstance(obj, dict):
            print(f"  /{obj_id}: {obj}")
        else:
            print(f"  {obj_id}: {obj}")
    
    print("\n--- SenML Format ---")
    senml = interpreter.get_semantic_output(result.data, 'senml')
    for record in senml:
        print(f"  {record}")
    
    # Round-trip test
    print("\n--- Encode Round-Trip ---")
    encoded = interpreter.encode(result.data)
    print(f"Original:  {payload.hex().upper()}")
    print(f"Encoded:   {encoded.payload.hex().upper()}")
    print(f"Match: {payload == encoded.payload}")
