#!/usr/bin/env python3
"""
generate_codec.py - Generate C codec AND unit tests from Payload Schema

Usage:
    python tools/generate_codec.py schema.yaml -o output_dir/
    
Generates:
    - <name>_codec.h     - Codec header (struct + decode/encode)
    - <name>_codec.c     - Codec implementation (optional)
    - <name>_test.c      - Unit tests with test vectors
    - <name>_test.py     - Python unit tests
    - test_vectors.h     - Test vector data

The schema can include test_vectors for automatic test generation.
"""

import argparse
import yaml
import json
import struct
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Import the interpreter for generating test vectors
import sys
sys.path.insert(0, str(Path(__file__).parent))
from schema_interpreter import SchemaInterpreter


# Type mappings: schema type -> (C type, size in bytes, signed, format_char)
TYPE_MAP = {
    'u8': ('uint8_t', 1, False, 'B'),
    # Unsigned types (canonical u + alias uint)
    'u16': ('uint16_t', 2, False, 'H'),
    'u24': ('uint32_t', 3, False, None),
    'u32': ('uint32_t', 4, False, 'I'),
    'u64': ('uint64_t', 8, False, 'Q'),
    'uint8': ('uint8_t', 1, False, 'B'),
    'uint16': ('uint16_t', 2, False, 'H'),
    'uint24': ('uint32_t', 3, False, None),
    'uint32': ('uint32_t', 4, False, 'I'),
    'uint64': ('uint64_t', 8, False, 'Q'),
    # Signed types (canonical s + aliases i, int)
    's8': ('int8_t', 1, True, 'b'),
    's16': ('int16_t', 2, True, 'h'),
    's24': ('int32_t', 3, True, None),
    's32': ('int32_t', 4, True, 'i'),
    's64': ('int64_t', 8, True, 'q'),
    'i8': ('int8_t', 1, True, 'b'),
    'i16': ('int16_t', 2, True, 'h'),
    'i24': ('int32_t', 3, True, None),
    'i32': ('int32_t', 4, True, 'i'),
    'i64': ('int64_t', 8, True, 'q'),
    'int8': ('int8_t', 1, True, 'b'),
    'int16': ('int16_t', 2, True, 'h'),
    'int24': ('int32_t', 3, True, None),
    'int32': ('int32_t', 4, True, 'i'),
    'int64': ('int64_t', 8, True, 'q'),
    # Float
    'f32': ('float', 4, True, 'f'),
    'f64': ('double', 8, True, 'd'),
    'float': ('float', 4, True, 'f'),
    'double': ('double', 8, True, 'd'),
    # Bool
    'bool': ('bool', 1, False, '?'),
}


def to_c_name(name: str) -> str:
    """Convert schema name to valid C identifier."""
    return name.replace('-', '_').replace('.', '_').lower()


def to_upper_name(name: str) -> str:
    """Convert to UPPER_CASE for macros."""
    return to_c_name(name).upper()


class TestVector:
    """Represents a test vector for codec testing."""
    
    def __init__(self, name: str, payload_hex: str, expected: Dict[str, Any],
                 description: str = ""):
        self.name = name
        self.payload_hex = payload_hex.replace(' ', '')
        self.payload_bytes = bytes.fromhex(self.payload_hex)
        self.expected = expected
        self.description = description
    
    def to_c_array(self) -> str:
        """Generate C byte array literal."""
        bytes_str = ', '.join(f'0x{b:02X}' for b in self.payload_bytes)
        return f"{{ {bytes_str} }}"
    
    @classmethod
    def from_dict(cls, d: dict) -> 'TestVector':
        return cls(
            name=d.get('name', 'test'),
            payload_hex=d.get('payload', ''),
            expected=d.get('expected', {}),
            description=d.get('description', '')
        )


class CodeGenerator:
    """Generates C code and tests from schema."""
    
    def __init__(self, schema: dict):
        self.schema = schema
        self.name = to_c_name(schema.get('name', 'codec'))
        self.name_upper = to_upper_name(schema.get('name', 'codec'))
        self.endian = schema.get('endian', 'big')
        self.fields = schema.get('fields', [])
        self.test_vectors = self._load_test_vectors()
        self.interpreter = SchemaInterpreter(schema)
    
    def _load_test_vectors(self) -> List[TestVector]:
        """Load test vectors from schema or generate defaults."""
        vectors = []
        
        # Load explicit test vectors
        for tv in self.schema.get('test_vectors', []):
            vectors.append(TestVector.from_dict(tv))
        
        # Generate automatic test vectors if none provided
        if not vectors:
            vectors = self._generate_test_vectors()
        
        return vectors
    
    def _generate_test_vectors(self) -> List[TestVector]:
        """Auto-generate test vectors based on field types."""
        vectors = []
        
        # Generate zero test
        zero_payload = self._generate_payload({f['name']: 0 for f in self.fields 
                                               if not f.get('name', '').startswith('_')})
        if zero_payload:
            vectors.append(TestVector(
                name='all_zeros',
                payload_hex=zero_payload.hex(),
                expected={f['name']: self._apply_modifiers(0, f) 
                         for f in self.fields if not f.get('name', '').startswith('_')},
                description='All fields zero'
            ))
        
        # Generate typical values test
        typical = self._generate_typical_values()
        typical_payload = self._generate_payload(typical)
        if typical_payload:
            expected = {}
            for f in self.fields:
                if f.get('name', '').startswith('_'):
                    continue
                name = f['name']
                if name in typical:
                    expected[name] = self._apply_modifiers(typical[name], f)
            vectors.append(TestVector(
                name='typical_values',
                payload_hex=typical_payload.hex(),
                expected=expected,
                description='Typical sensor values'
            ))
        
        # Generate max values test
        max_vals = self._generate_max_values()
        max_payload = self._generate_payload(max_vals)
        if max_payload:
            expected = {}
            for f in self.fields:
                if f.get('name', '').startswith('_'):
                    continue
                name = f['name']
                if name in max_vals:
                    expected[name] = self._apply_modifiers(max_vals[name], f)
            vectors.append(TestVector(
                name='max_values',
                payload_hex=max_payload.hex(),
                expected=expected,
                description='Maximum field values'
            ))
        
        return vectors
    
    def _generate_typical_values(self) -> Dict[str, int]:
        """Generate typical raw values for each field."""
        values = {}
        for f in self.fields:
            if f.get('name', '').startswith('_'):
                continue
            name = f['name']
            ftype = f.get('type', 'u8')
            
            # Typical values based on common sensor data
            if 'temp' in name.lower():
                values[name] = 2345  # 23.45 with mult 0.01
            elif 'hum' in name.lower():
                values[name] = 130   # 65% with mult 0.5
            elif 'batt' in name.lower():
                values[name] = 3300  # 3300mV
            elif 'press' in name.lower():
                values[name] = 10132  # 1013.2 hPa with mult 0.1
            else:
                # Generic middle value
                type_info = TYPE_MAP.get(ftype.split('[')[0].split(':')[0])
                if type_info:
                    size = type_info[1]
                    signed = type_info[2]
                    if signed:
                        values[name] = 100
                    else:
                        values[name] = (1 << (size * 4)) - 1  # Half max
                else:
                    values[name] = 100
        return values
    
    def _generate_max_values(self) -> Dict[str, int]:
        """Generate maximum values for each field."""
        values = {}
        for f in self.fields:
            if f.get('name', '').startswith('_'):
                continue
            name = f['name']
            ftype = f.get('type', 'u8')
            
            base_type = ftype.split('[')[0].split(':')[0]
            type_info = TYPE_MAP.get(base_type)
            if type_info:
                size = type_info[1]
                signed = type_info[2]
                if signed:
                    values[name] = (1 << (size * 8 - 1)) - 1  # Max positive
                else:
                    values[name] = (1 << (size * 8)) - 1  # Max unsigned
            else:
                values[name] = 255
        return values
    
    def _apply_modifiers(self, raw_value: int, field: dict) -> Any:
        """Apply field modifiers to get expected decoded value."""
        value = raw_value
        
        mult = field.get('mult')
        if mult:
            value = value * mult
        
        div = field.get('div')
        if div:
            value = value / div
        
        add = field.get('add')
        if add:
            value = value + add
        
        lookup = field.get('lookup')
        if lookup and isinstance(raw_value, int) and 0 <= raw_value < len(lookup):
            value = lookup[raw_value]
        
        return value
    
    def _generate_payload(self, values: Dict[str, int]) -> Optional[bytes]:
        """Generate payload bytes from raw values."""
        result = self.interpreter.encode(values)
        if result.success:
            return result.payload
        return None
    
    def generate_header(self) -> str:
        """Generate C header file content."""
        guard = f"_{self.name_upper}_CODEC_H_"
        
        struct_def = self._generate_struct()
        decoder = self._generate_decoder()
        encoder = self._generate_encoder()
        
        return f'''/*
 * {self.name}_codec.h - Auto-generated codec
 *
 * Generated by: generate_codec.py
 * Generated at: {datetime.now().isoformat()}
 * Schema: {self.schema.get('name', 'unknown')} v{self.schema.get('version', 1)}
 *
 * DO NOT EDIT - Regenerate from schema
 */

#ifndef {guard}
#define {guard}

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {{
#endif

/* ============================================
 * Constants
 * ============================================ */

#define {self.name_upper}_VERSION {self.schema.get('version', 1)}
#define {self.name_upper}_PAYLOAD_SIZE {self._calc_payload_size()}

/* ============================================
 * Data Structure
 * ============================================ */

{struct_def}

/* ============================================
 * Decoder
 * ============================================ */

{decoder}

/* ============================================
 * Encoder
 * ============================================ */

{encoder}

#ifdef __cplusplus
}}
#endif

#endif /* {guard} */
'''
    
    def _generate_struct(self) -> str:
        """Generate C struct definition."""
        lines = [f"typedef struct {{"]
        
        for field in self.fields:
            name = to_c_name(field['name'])
            if name.startswith('_'):
                continue
            
            ftype = field.get('type', 'u8')
            base_type = ftype.split('[')[0].split(':')[0]
            
            type_info = TYPE_MAP.get(base_type)
            if type_info:
                c_type = type_info[0]
                # Use float for fields with multipliers
                if field.get('mult') or field.get('div'):
                    c_type = 'float'
                lines.append(f"    {c_type} {name};")
            else:
                lines.append(f"    uint8_t {name};  /* unknown type: {ftype} */")
        
        lines.append(f"}} {self.name}_t;")
        return '\n'.join(lines)
    
    def _calc_payload_size(self) -> int:
        """Calculate expected payload size in bytes."""
        size = 0
        for field in self.fields:
            ftype = field.get('type', 'u8')
            base_type = ftype.split('[')[0].split(':')[0]
            type_info = TYPE_MAP.get(base_type)
            if type_info:
                # Only count if consume is set or it's a full type
                if '[' not in ftype and ':' not in ftype:
                    size += type_info[1]
                elif field.get('consume'):
                    size += field['consume']
        return size
    
    def _generate_decoder(self) -> str:
        """Generate decoder function."""
        endian_suffix = 'le' if self.endian == 'little' else 'be'
        
        lines = [
            f"/**",
            f" * Decode {self.name} payload",
            f" * @param buf    Input buffer",
            f" * @param len    Input length",
            f" * @param out    Output structure",
            f" * @return       Bytes consumed, or negative on error",
            f" */",
            f"static inline int {self.name}_decode(",
            f"    const uint8_t* buf,",
            f"    size_t len,",
            f"    {self.name}_t* out",
            f") {{",
            f"    if (!buf || !out) return -1;",
            f"    if (len < {self._calc_payload_size()}) return -2;",
            f"    memset(out, 0, sizeof(*out));",
            f"    size_t pos = 0;",
            f"",
        ]
        
        for field in self.fields:
            name = to_c_name(field['name'])
            if name.startswith('_'):
                lines.append(f"    pos += {self._field_size(field)};  /* skip {name} */")
                continue
            
            ftype = field.get('type', 'u8')
            base_type = ftype.split('[')[0].split(':')[0]
            type_info = TYPE_MAP.get(base_type)
            
            if not type_info:
                lines.append(f"    /* TODO: {name} type {ftype} */")
                continue
            
            c_type, size, signed, _ = type_info
            mult = field.get('mult')
            add = field.get('add')
            
            lines.append(f"    /* {name} */")
            
            # Read raw value
            if size == 1:
                if signed:
                    lines.append(f"    int8_t raw_{name} = (int8_t)buf[pos];")
                else:
                    lines.append(f"    uint8_t raw_{name} = buf[pos];")
            elif self.endian == 'little':
                if size == 2:
                    lines.append(f"    {'int16_t' if signed else 'uint16_t'} raw_{name} = "
                               f"buf[pos] | ((uint16_t)buf[pos+1] << 8);")
                elif size == 4:
                    lines.append(f"    {'int32_t' if signed else 'uint32_t'} raw_{name} = "
                               f"buf[pos] | ((uint32_t)buf[pos+1] << 8) | "
                               f"((uint32_t)buf[pos+2] << 16) | ((uint32_t)buf[pos+3] << 24);")
            else:  # big endian
                if size == 2:
                    lines.append(f"    {'int16_t' if signed else 'uint16_t'} raw_{name} = "
                               f"((uint16_t)buf[pos] << 8) | buf[pos+1];")
                elif size == 4:
                    lines.append(f"    {'int32_t' if signed else 'uint32_t'} raw_{name} = "
                               f"((uint32_t)buf[pos] << 24) | ((uint32_t)buf[pos+1] << 16) | "
                               f"((uint32_t)buf[pos+2] << 8) | buf[pos+3];")
            
            # Apply modifiers
            if mult or add:
                expr = f"raw_{name}"
                if mult:
                    expr = f"({expr} * {mult}f)"
                if add:
                    expr = f"({expr} + {add}f)"
                lines.append(f"    out->{name} = {expr};")
            else:
                lines.append(f"    out->{name} = raw_{name};")
            
            lines.append(f"    pos += {size};")
            lines.append("")
        
        lines.extend([
            f"    return (int)pos;",
            f"}}",
        ])
        
        return '\n'.join(lines)
    
    def _generate_encoder(self) -> str:
        """Generate encoder function."""
        lines = [
            f"/**",
            f" * Encode {self.name} payload",
            f" * @param in      Input structure",
            f" * @param buf     Output buffer",
            f" * @param max_len Maximum buffer size",
            f" * @return        Bytes written, or negative on error",
            f" */",
            f"static inline int {self.name}_encode(",
            f"    const {self.name}_t* in,",
            f"    uint8_t* buf,",
            f"    size_t max_len",
            f") {{",
            f"    if (!in || !buf) return -1;",
            f"    if (max_len < {self._calc_payload_size()}) return -2;",
            f"    size_t pos = 0;",
            f"",
        ]
        
        for field in self.fields:
            name = to_c_name(field['name'])
            if name.startswith('_'):
                lines.append(f"    buf[pos++] = 0;  /* {name} */")
                continue
            
            ftype = field.get('type', 'u8')
            base_type = ftype.split('[')[0].split(':')[0]
            type_info = TYPE_MAP.get(base_type)
            
            if not type_info:
                continue
            
            c_type, size, signed, _ = type_info
            mult = field.get('mult')
            add = field.get('add')
            
            lines.append(f"    /* {name} */")
            
            # Reverse modifiers
            if mult or add:
                expr = f"in->{name}"
                if add:
                    expr = f"({expr} - {add}f)"
                if mult:
                    expr = f"({expr} / {mult}f)"
                lines.append(f"    {'int32_t' if signed else 'uint32_t'} raw_{name} = (int)({expr});")
                var = f"raw_{name}"
            else:
                var = f"in->{name}"
            
            # Write bytes
            if size == 1:
                lines.append(f"    buf[pos] = (uint8_t){var};")
            elif self.endian == 'little':
                if size == 2:
                    lines.append(f"    buf[pos] = (uint8_t){var};")
                    lines.append(f"    buf[pos+1] = (uint8_t)({var} >> 8);")
                elif size == 4:
                    lines.append(f"    buf[pos] = (uint8_t){var};")
                    lines.append(f"    buf[pos+1] = (uint8_t)({var} >> 8);")
                    lines.append(f"    buf[pos+2] = (uint8_t)({var} >> 16);")
                    lines.append(f"    buf[pos+3] = (uint8_t)({var} >> 24);")
            else:  # big endian
                if size == 2:
                    lines.append(f"    buf[pos] = (uint8_t)({var} >> 8);")
                    lines.append(f"    buf[pos+1] = (uint8_t){var};")
                elif size == 4:
                    lines.append(f"    buf[pos] = (uint8_t)({var} >> 24);")
                    lines.append(f"    buf[pos+1] = (uint8_t)({var} >> 16);")
                    lines.append(f"    buf[pos+2] = (uint8_t)({var} >> 8);")
                    lines.append(f"    buf[pos+3] = (uint8_t){var};")
            
            lines.append(f"    pos += {size};")
            lines.append("")
        
        lines.extend([
            f"    return (int)pos;",
            f"}}",
        ])
        
        return '\n'.join(lines)
    
    def _field_size(self, field: dict) -> int:
        """Get size of a field in bytes."""
        ftype = field.get('type', 'u8')
        base_type = ftype.split('[')[0].split(':')[0]
        type_info = TYPE_MAP.get(base_type)
        return type_info[1] if type_info else 1
    
    def generate_c_tests(self) -> str:
        """Generate C unit tests."""
        lines = [
            f"/*",
            f" * {self.name}_test.c - Auto-generated unit tests",
            f" *",
            f" * Generated by: generate_codec.py",
            f" * Generated at: {datetime.now().isoformat()}",
            f" */",
            f"",
            f"#include <stdio.h>",
            f"#include <string.h>",
            f"#include <math.h>",
            f'#include "{self.name}_codec.h"',
            f"",
            f"#define ASSERT_EQ(a, b, name) do {{ \\",
            f"    if ((a) != (b)) {{ \\",
            f'        printf("FAIL: %s: expected %d, got %d\\n", name, (int)(b), (int)(a)); \\',
            f"        failures++; \\",
            f"    }} else {{ \\",
            f'        printf("PASS: %s\\n", name); \\',
            f"        passes++; \\",
            f"    }} \\",
            f"}} while(0)",
            f"",
            f"#define ASSERT_FLOAT_EQ(a, b, tol, name) do {{ \\",
            f"    if (fabs((a) - (b)) > (tol)) {{ \\",
            f'        printf("FAIL: %s: expected %.4f, got %.4f\\n", name, (double)(b), (double)(a)); \\',
            f"        failures++; \\",
            f"    }} else {{ \\",
            f'        printf("PASS: %s\\n", name); \\',
            f"        passes++; \\",
            f"    }} \\",
            f"}} while(0)",
            f"",
            f"static int passes = 0;",
            f"static int failures = 0;",
            f"",
        ]
        
        # Generate test vectors
        for i, tv in enumerate(self.test_vectors):
            lines.append(f"/* Test vector: {tv.name} - {tv.description} */")
            lines.append(f"static const uint8_t test_payload_{i}[] = {tv.to_c_array()};")
            lines.append("")
        
        # Generate test functions
        for i, tv in enumerate(self.test_vectors):
            lines.extend(self._generate_test_function(i, tv))
            lines.append("")
        
        # Generate roundtrip test
        lines.extend(self._generate_roundtrip_test())
        
        # Main function
        lines.extend([
            f"int main(void) {{",
            f'    printf("=== {self.name} Codec Tests ===\\n\\n");',
            f"",
        ])
        
        for i, tv in enumerate(self.test_vectors):
            lines.append(f"    test_{tv.name}();")
        
        lines.extend([
            f"    test_roundtrip();",
            f"",
            f'    printf("\\n=== Results: %d passed, %d failed ===\\n", passes, failures);',
            f"    return failures > 0 ? 1 : 0;",
            f"}}",
        ])
        
        return '\n'.join(lines)
    
    def _generate_test_function(self, idx: int, tv: TestVector) -> List[str]:
        """Generate a single test function."""
        lines = [
            f"static void test_{tv.name}(void) {{",
            f'    printf("--- Test: {tv.name} ---\\n");',
            f"    {self.name}_t decoded;",
            f"    int ret = {self.name}_decode(test_payload_{idx}, sizeof(test_payload_{idx}), &decoded);",
            f'    ASSERT_EQ(ret > 0, 1, "decode_success");',
            f"",
        ]
        
        for field_name, expected in tv.expected.items():
            c_name = to_c_name(field_name)
            if isinstance(expected, float):
                lines.append(f'    ASSERT_FLOAT_EQ(decoded.{c_name}, {expected}f, 0.01f, "{c_name}");')
            elif isinstance(expected, bool):
                lines.append(f'    ASSERT_EQ(decoded.{c_name}, {1 if expected else 0}, "{c_name}");')
            elif isinstance(expected, int):
                lines.append(f'    ASSERT_EQ(decoded.{c_name}, {expected}, "{c_name}");')
        
        lines.append(f"}}")
        return lines
    
    def _generate_roundtrip_test(self) -> List[str]:
        """Generate encode/decode roundtrip test."""
        return [
            f"static void test_roundtrip(void) {{",
            f'    printf("--- Test: roundtrip ---\\n");',
            f"    {self.name}_t original, decoded;",
            f"    uint8_t buffer[{self._calc_payload_size() + 10}];",
            f"",
            f"    /* Set test values */",
            f"    memset(&original, 0, sizeof(original));",
        ] + [
            f"    original.{to_c_name(f['name'])} = {self._get_test_value(f)};"
            for f in self.fields if not f.get('name', '').startswith('_')
        ] + [
            f"",
            f"    /* Encode */",
            f"    int enc_len = {self.name}_encode(&original, buffer, sizeof(buffer));",
            f'    ASSERT_EQ(enc_len > 0, 1, "encode_success");',
            f"",
            f"    /* Decode */",
            f"    int dec_len = {self.name}_decode(buffer, enc_len, &decoded);",
            f'    ASSERT_EQ(dec_len, enc_len, "roundtrip_length");',
            f"",
            f"    /* Compare */",
        ] + [
            f'    ASSERT_FLOAT_EQ(decoded.{to_c_name(f["name"])}, original.{to_c_name(f["name"])}, 0.1f, "rt_{to_c_name(f["name"])}");'
            if f.get('mult') or f.get('div') else
            f'    ASSERT_EQ(decoded.{to_c_name(f["name"])}, original.{to_c_name(f["name"])}, "rt_{to_c_name(f["name"])}");'
            for f in self.fields if not f.get('name', '').startswith('_')
        ] + [
            f"}}",
        ]
    
    def _get_test_value(self, field: dict) -> str:
        """Get a test value for a field."""
        name = field.get('name', '').lower()
        if 'temp' in name:
            return "23.45f" if field.get('mult') else "2345"
        elif 'hum' in name:
            return "65.0f" if field.get('mult') else "130"
        elif 'batt' in name:
            return "3300"
        else:
            return "100"
    
    def generate_python_tests(self) -> str:
        """Generate Python unit tests."""
        lines = [
            f'"""',
            f'Auto-generated Python tests for {self.name} codec.',
            f'',
            f'Generated by: generate_codec.py',
            f'Generated at: {datetime.now().isoformat()}',
            f'"""',
            f'',
            f'import pytest',
            f'import sys',
            f'from pathlib import Path',
            f'',
            f'sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))',
            f'from schema_interpreter import SchemaInterpreter, decode_payload',
            f'',
            f'',
            f'# Schema definition',
            f'SCHEMA = {json.dumps(self.schema, indent=4)}',
            f'',
            f'',
            f'@pytest.fixture',
            f'def interpreter():',
            f'    return SchemaInterpreter(SCHEMA)',
            f'',
            f'',
        ]
        
        # Generate test classes
        lines.append(f'class Test{self.name.title().replace("_", "")}Decode:')
        lines.append(f'    """Decoder tests with test vectors."""')
        lines.append(f'')
        
        for tv in self.test_vectors:
            lines.extend([
                f'    def test_{tv.name}(self, interpreter):',
                f'        """{tv.description}"""',
                f'        payload = bytes.fromhex("{tv.payload_hex}")',
                f'        result = interpreter.decode(payload)',
                f'        assert result.success',
                f'',
            ])
            
            for field_name, expected in tv.expected.items():
                if isinstance(expected, float):
                    lines.append(f'        assert abs(result.data["{field_name}"] - {expected}) < 0.01')
                elif isinstance(expected, str):
                    lines.append(f'        assert result.data["{field_name}"] == "{expected}"')
                else:
                    lines.append(f'        assert result.data["{field_name}"] == {expected}')
            
            lines.append(f'')
        
        # Roundtrip test
        lines.extend([
            f'',
            f'class Test{self.name.title().replace("_", "")}Roundtrip:',
            f'    """Encode/decode roundtrip tests."""',
            f'',
            f'    def test_encode_decode_roundtrip(self, interpreter):',
            f'        """Test that encode followed by decode returns original values."""',
            f'        original = {{',
        ])
        
        for f in self.fields:
            if f.get('name', '').startswith('_'):
                continue
            name = f['name']
            val = self._get_python_test_value(f)
            lines.append(f'            "{name}": {val},')
        
        lines.extend([
            f'        }}',
            f'',
            f'        encoded = interpreter.encode(original)',
            f'        assert encoded.success',
            f'',
            f'        decoded = interpreter.decode(encoded.payload)',
            f'        assert decoded.success',
            f'',
        ])
        
        for f in self.fields:
            if f.get('name', '').startswith('_'):
                continue
            name = f['name']
            if f.get('mult') or f.get('div'):
                lines.append(f'        assert abs(decoded.data["{name}"] - original["{name}"]) < 0.1')
            else:
                lines.append(f'        assert decoded.data["{name}"] == original["{name}"]')
        
        lines.append(f'')
        return '\n'.join(lines)
    
    def _get_python_test_value(self, field: dict) -> str:
        """Get a Python test value for a field."""
        name = field.get('name', '').lower()
        if 'temp' in name:
            return "23.45" if field.get('mult') else "2345"
        elif 'hum' in name:
            return "65.0" if field.get('mult') else "130"
        elif 'batt' in name:
            return "3300"
        else:
            return "100"


def main():
    parser = argparse.ArgumentParser(
        description='Generate C codec and unit tests from Payload Schema'
    )
    parser.add_argument('schema', help='Path to schema YAML file')
    parser.add_argument('-o', '--output', help='Output directory', default='.')
    parser.add_argument('--header-only', action='store_true',
                       help='Generate header file only')
    parser.add_argument('--tests-only', action='store_true',
                       help='Generate test files only')
    args = parser.parse_args()
    
    # Load schema
    with open(args.schema) as f:
        schema = yaml.safe_load(f)
    
    # Create generator
    gen = CodeGenerator(schema)
    
    # Create output directory
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate files
    if not args.tests_only:
        header_path = out_dir / f"{gen.name}_codec.h"
        with open(header_path, 'w') as f:
            f.write(gen.generate_header())
        print(f"Generated: {header_path}")
    
    if not args.header_only:
        c_test_path = out_dir / f"{gen.name}_test.c"
        with open(c_test_path, 'w') as f:
            f.write(gen.generate_c_tests())
        print(f"Generated: {c_test_path}")
        
        py_test_path = out_dir / f"test_{gen.name}.py"
        with open(py_test_path, 'w') as f:
            f.write(gen.generate_python_tests())
        print(f"Generated: {py_test_path}")
    
    print(f"\nGenerated {len(gen.test_vectors)} test vectors")


if __name__ == '__main__':
    main()
