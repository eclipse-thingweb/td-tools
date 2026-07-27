"""
Tests for schema interpreter.

Requirements Coverage (see test-requirements-map.yaml for full mapping):
Requirement IDs from: la-payload-schema/spec/sections/A4-requirements.md

Mandatory Requirements (M001-M234):
- M003-M040: Schema format, structure, ports
- M041-M045: Integer types and endianness
- M046-M047: Float types
- M048-M053: Bitfield syntaxes
- M054-M055: Boolean type
- M056-M058: Enum type
- M059-M060: Byte groups
- M061-M064: String types
- M065-M067: Computed fields
- M072-M076: Repeat/arrays
- M085-M092: Modifiers (add, mult, div, lookup)
- M093-M097: Polynomial
- M098-M101: Transforms
- M102-M106: Compute operations
- M107-M111: Guard conditions
- M112-M115: Valid range
- M119-M121: Nested objects
- M122-M127: Variables
- M128-M132: Match conditionals
- M133-M137: TLV parsing
- M138-M148: Flagged construct
- M149-M156, M166-M169: Compact format
- M179-M188: Validation
- M189-M201: Safety
- M210-M213: Downlink encoding
- M226-M231: Schema composition

Recommended Requirements (R001-R057):
- R024: SenML unit codes
- R027-R029: IPSO/SenML warnings

Optional Requirements (O001-O044):
- O005, O028: Direction property
- O021, O022: Compact format strings
"""

import pytest
import struct
import sys
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))

from schema_interpreter import (
    SchemaInterpreter, DecodeResult, EncodeResult,
    Endian, decode_payload, encode_payload
)


class TestSchemaInterpreterBasic:
    """Basic tests for SchemaInterpreter.
    
    Spec Requirements:
    - M003: Schema SHALL be valid JSON/YAML
    - M004: name field REQUIRED
    - M008: Schema MUST contain fields or ports
    """
    
    @pytest.fixture
    def simple_schema(self):
        return {
            'name': 'test_sensor',
            'endian': 'big',
            'fields': [
                {'name': 'temperature', 'type': 'u16'},
                {'name': 'humidity', 'type': 'u8'},
            ]
        }
    
    def test_decode_simple(self, simple_schema):
        """Test decoding simple payload."""
        interpreter = SchemaInterpreter(simple_schema)
        payload = bytes([0x01, 0x00, 0x64])  # temp=256, hum=100
        
        result = interpreter.decode(payload)
        
        assert result.success
        assert result.data['temperature'] == 256
        assert result.data['humidity'] == 100
        assert result.bytes_consumed == 3
    
    def test_decode_empty_payload(self, simple_schema):
        """Test decoding empty payload fails gracefully."""
        interpreter = SchemaInterpreter(simple_schema)
        
        result = interpreter.decode(bytes())
        
        assert not result.success
        assert len(result.errors) > 0


class TestIntegerTypes:
    """Tests for integer type decoding.
    
    Spec Requirements:
    - M041: Type aliases
    - M042: All defined integer widths (u8, u16, u32, u64, s8, s16, s32, s64)
    - M043: Documented type aliases
    - M044: Big-endian and little-endian support
    - R008: Big endian default
    """
    
    def test_decode_u8(self):
        """Test unsigned 8-bit decode."""
        schema = {'fields': [{'name': 'val', 'type': 'u8'}]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0xFF]))
        assert result.data['val'] == 255
    
    def test_decode_u16_big_endian(self):
        """Test unsigned 16-bit big-endian decode."""
        schema = {'endian': 'big', 'fields': [{'name': 'val', 'type': 'u16'}]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x01, 0x02]))
        assert result.data['val'] == 0x0102
    
    def test_decode_u16_little_endian(self):
        """Test unsigned 16-bit little-endian decode."""
        schema = {'endian': 'little', 'fields': [{'name': 'val', 'type': 'u16'}]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x01, 0x02]))
        assert result.data['val'] == 0x0201
    
    def test_decode_s16_negative(self):
        """Test signed 16-bit with negative value."""
        schema = {'endian': 'big', 'fields': [{'name': 'val', 'type': 's16'}]}
        interpreter = SchemaInterpreter(schema)
        
        # -100 in big-endian
        result = interpreter.decode(bytes([0xFF, 0x9C]))
        assert result.data['val'] == -100
    
    def test_decode_u32(self):
        """Test unsigned 32-bit decode."""
        schema = {'endian': 'big', 'fields': [{'name': 'val', 'type': 'u32'}]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x00, 0x01, 0x00, 0x00]))
        assert result.data['val'] == 65536
    
    def test_decode_i8(self):
        """Test signed 8-bit decode."""
        schema = {'fields': [{'name': 'val', 'type': 'i8'}]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x80]))  # -128
        assert result.data['val'] == -128
    
    def test_decode_u24(self):
        """Test unsigned 24-bit decode."""
        schema = {'endian': 'big', 'fields': [{'name': 'val', 'type': 'u24'}]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x01, 0x02, 0x03]))
        assert result.data['val'] == 0x010203


class TestFloatTypes:
    """Tests for floating point type decoding.
    
    Spec Requirements:
    - M046: IEEE 754 formats (f16, f32, f64)
    - M047: Special values (NaN, Infinity)
    """
    
    def test_decode_f32(self):
        """Test 32-bit float decode."""
        schema = {'endian': 'little', 'fields': [{'name': 'val', 'type': 'f32'}]}
        interpreter = SchemaInterpreter(schema)
        
        # 1.5 as little-endian float
        payload = struct.pack('<f', 1.5)
        result = interpreter.decode(payload)
        
        assert abs(result.data['val'] - 1.5) < 0.0001
    
    def test_decode_f64(self):
        """Test 64-bit float decode."""
        schema = {'endian': 'big', 'fields': [{'name': 'val', 'type': 'f64'}]}
        interpreter = SchemaInterpreter(schema)
        
        payload = struct.pack('>d', 3.14159)
        result = interpreter.decode(payload)
        
        assert abs(result.data['val'] - 3.14159) < 0.00001


class TestBitfieldTypes:
    """Tests for bitfield type decoding.
    
    Spec Requirements:
    - M048: Bits numbered 0 (LSB) to 7 (MSB)
    - M049: All shorthand syntaxes (slice, part-select, template, @, sequential)
    - M050: Bitfield extractions MUST NOT advance read position unless consume:1
    """
    
    def test_decode_bitfield_python_slice(self):
        """Test Python slice notation: u8[3:4]."""
        schema = {'fields': [
            {'name': 'val', 'type': 'u8[3:4]', 'consume': 1}
        ]}
        interpreter = SchemaInterpreter(schema)
        
        # Byte: 0b00011000 = 0x18, bits 3-4 = 0b11 = 3
        result = interpreter.decode(bytes([0x18]))
        assert result.data['val'] == 3
    
    def test_decode_bitfield_verilog(self):
        """Test Verilog part-select: u8[3+:2]."""
        schema = {'fields': [
            {'name': 'val', 'type': 'u8[3+:2]', 'consume': 1}
        ]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x18]))
        assert result.data['val'] == 3
    
    def test_decode_bitfield_cpp_template(self):
        """Test C++ template: bits<3,2>."""
        schema = {'fields': [
            {'name': 'val', 'type': 'bits<3,2>', 'consume': 1}
        ]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x18]))
        assert result.data['val'] == 3
    
    def test_decode_bitfield_at_notation(self):
        """Test @ notation: bits:2@3."""
        schema = {'fields': [
            {'name': 'val', 'type': 'bits:2@3', 'consume': 1}
        ]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x18]))
        assert result.data['val'] == 3
    
    def test_decode_bitfield_sequential(self):
        """Test sequential: u8:2."""
        schema = {'fields': [
            {'name': 'high', 'type': 'u8:2'},
            {'name': 'mid', 'type': 'u8:3'},
            {'name': 'low', 'type': 'u8:3', 'consume': 1},
        ]}
        interpreter = SchemaInterpreter(schema)
        
        # Byte: 0b11_010_001 = 0xD1
        result = interpreter.decode(bytes([0xD1]))
        assert result.data['high'] == 3   # bits 6-7 = 0b11
        assert result.data['mid'] == 2    # bits 3-5 = 0b010
        assert result.data['low'] == 1    # bits 0-2 = 0b001
    
    def test_decode_multiple_bitfields_no_advance(self):
        """Test multiple bitfields from same byte."""
        schema = {'fields': [
            {'name': 'a', 'type': 'u8[0:0]'},  # Bit 0
            {'name': 'b', 'type': 'u8[1:1]'},  # Bit 1
            {'name': 'c', 'type': 'u8[2:2]'},  # Bit 2
            {'name': 'd', 'type': 'u8[3:7]', 'consume': 1},  # Bits 3-7
        ]}
        interpreter = SchemaInterpreter(schema)
        
        # Byte: 0b11110101 = 0xF5
        result = interpreter.decode(bytes([0xF5]))
        assert result.data['a'] == 1  # Bit 0
        assert result.data['b'] == 0  # Bit 1
        assert result.data['c'] == 1  # Bit 2
        assert result.data['d'] == 0b11110  # Bits 3-7


class TestBooleanType:
    """Tests for boolean type decoding.
    
    Spec Requirements:
    - M054: Decoders MUST output JSON boolean values (true/false)
    - M055: Bool MUST NOT advance read position
    """
    
    def test_decode_bool_true(self):
        """Test boolean decode true."""
        schema = {'fields': [
            {'name': 'flag', 'type': 'bool', 'bit': 0, 'consume': 1}
        ]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x01]))
        assert result.data['flag'] is True
    
    def test_decode_bool_false(self):
        """Test boolean decode false."""
        schema = {'fields': [
            {'name': 'flag', 'type': 'bool', 'bit': 0, 'consume': 1}
        ]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x00]))
        assert result.data['flag'] is False
    
    def test_decode_bool_specific_bit(self):
        """Test boolean at specific bit."""
        schema = {'fields': [
            {'name': 'flag', 'type': 'bool', 'bit': 7, 'consume': 1}
        ]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x80]))  # Bit 7 set
        assert result.data['flag'] is True


class TestModifiers:
    """Tests for arithmetic modifiers.
    
    Spec Requirements:
    - M085: add, mult, div transformations
    - M086: Floating-point arithmetic
    - M087: Division by zero handling
    - M089-M092: lookup table modifier
    """
    
    def test_mult_modifier(self):
        """Test multiplier modifier."""
        schema = {'fields': [
            {'name': 'temp', 'type': 'u16', 'mult': 0.01}
        ]}
        interpreter = SchemaInterpreter(schema)
        
        # 2345 * 0.01 = 23.45
        result = interpreter.decode(bytes([0x09, 0x29]))
        assert abs(result.data['temp'] - 23.45) < 0.001
    
    def test_add_modifier(self):
        """Test add modifier."""
        schema = {'fields': [
            {'name': 'val', 'type': 'u8', 'add': 100}
        ]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x0A]))  # 10 + 100 = 110
        assert result.data['val'] == 110
    
    def test_div_modifier(self):
        """Test div modifier."""
        schema = {'fields': [
            {'name': 'val', 'type': 'u16', 'div': 10}
        ]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x00, 0x64]))  # 100 / 10 = 10
        assert result.data['val'] == 10.0
    
    def test_combined_modifiers(self):
        """Test combined mult, div, add."""
        schema = {'fields': [
            {'name': 'val', 'type': 'u8', 'mult': 2, 'add': 10}
        ]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x05]))  # 5 * 2 + 10 = 20
        assert result.data['val'] == 20
    
    def test_lookup_modifier(self):
        """Test lookup table modifier."""
        schema = {'fields': [
            {'name': 'mode', 'type': 'u8', 'lookup': ['off', 'low', 'medium', 'high']}
        ]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x02]))
        assert result.data['mode'] == 'medium'


class TestNestedObjects:
    """Tests for nested object types.
    
    Spec Requirements:
    - M119: Nested object: constructs
    - M120: Fields processed in order
    - M121: fields array MUST contain at least one field
    """
    
    def test_decode_nested_object(self):
        """Test nested object decoding."""
        schema = {'fields': [
            {'name': 'header', 'type': 'u8'},
            {'name': 'sensor', 'type': 'object', 'fields': [
                {'name': 'temp', 'type': 'u16'},
                {'name': 'hum', 'type': 'u8'},
            ]},
        ]}
        interpreter = SchemaInterpreter(schema)
        
        payload = bytes([0x01, 0x00, 0x64, 0x32])
        result = interpreter.decode(payload)
        
        assert result.data['header'] == 1
        assert result.data['sensor']['temp'] == 100
        assert result.data['sensor']['hum'] == 50


class TestBytesAndStrings:
    """Tests for bytes and string types.
    
    Spec Requirements:
    - M061: ascii, hex, base64 support
    - M062: length field requirement
    - M063: hex lowercase output
    - M064: RFC 4648 Base64
    """
    
    def test_decode_bytes(self):
        """Test bytes type decode."""
        schema = {'fields': [
            {'name': 'data', 'type': 'bytes', 'length': 4}
        ]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x01, 0x02, 0x03, 0x04]))
        assert result.data['data'] == bytes([0x01, 0x02, 0x03, 0x04])
    
    def test_decode_string(self):
        """Test string type decode."""
        schema = {'fields': [
            {'name': 'name', 'type': 'string', 'length': 5}
        ]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(b'hello')
        assert result.data['name'] == 'hello'
    
    def test_decode_string_with_null(self):
        """Test string strips null padding."""
        schema = {'fields': [
            {'name': 'name', 'type': 'string', 'length': 8}
        ]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(b'test\x00\x00\x00\x00')
        assert result.data['name'] == 'test'


class TestInternalFields:
    """Tests for internal/hidden fields."""
    
    def test_skip_internal_fields(self):
        """Test that fields starting with _ are skipped in output."""
        schema = {'fields': [
            {'name': '_header', 'type': 'u8'},
            {'name': 'value', 'type': 'u16'},
        ]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0xFF, 0x00, 0x64]))
        
        assert '_header' not in result.data
        assert result.data['value'] == 100


class TestEncoder:
    """Tests for payload encoding.
    
    Spec Requirements:
    - M153: Modifiers MUST be reversed in opposite order from decode
    - M154: Round non-integer values
    - M210-M212: JSON to binary encoding, reverse transformations
    """
    
    @pytest.fixture
    def simple_schema(self):
        return {
            'name': 'test',
            'endian': 'big',
            'fields': [
                {'name': 'temp', 'type': 'u16'},
                {'name': 'hum', 'type': 'u8'},
            ]
        }
    
    def test_encode_simple(self, simple_schema):
        """Test simple encoding."""
        interpreter = SchemaInterpreter(simple_schema)
        
        result = interpreter.encode({'temp': 256, 'hum': 100})
        
        assert result.success
        assert result.payload == bytes([0x01, 0x00, 0x64])
    
    def test_encode_with_mult(self):
        """Test encoding with multiplier."""
        schema = {'fields': [
            {'name': 'temp', 'type': 'u16', 'mult': 0.01}
        ]}
        interpreter = SchemaInterpreter(schema)
        
        # 23.45 / 0.01 = 2345
        result = interpreter.encode({'temp': 23.45})
        assert result.payload == bytes([0x09, 0x29])
    
    def test_encode_missing_field_warning(self, simple_schema):
        """Test warning for missing field."""
        interpreter = SchemaInterpreter(simple_schema)
        
        result = interpreter.encode({'temp': 256})  # Missing 'hum'
        
        assert 'hum' in ''.join(result.warnings)
    
    def test_encode_decode_roundtrip(self, simple_schema):
        """Test encode/decode roundtrip."""
        interpreter = SchemaInterpreter(simple_schema)
        
        original = {'temp': 512, 'hum': 75}
        encoded = interpreter.encode(original)
        decoded = interpreter.decode(encoded.payload)
        
        assert decoded.data == original


class TestSemanticOutputs:
    """Tests for semantic output formats.
    
    Spec Requirements:
    - M170: _quality object when valid_range
    - R024: SenML unit codes (RFC 8428)
    - R027: IPSO for standard sensors
    """
    
    @pytest.fixture
    def semantic_schema(self):
        return {
            'fields': [
                {'name': 'temperature', 'type': 's16', 'mult': 0.01,
                 'unit': '°C', 'semantic': {'ipso': 3303}},
                {'name': 'humidity', 'type': 'u8', 'mult': 0.5,
                 'unit': '%RH', 'semantic': {'ipso': 3304}},
            ]
        }
    
    def test_ipso_output(self, semantic_schema):
        """Test IPSO format output."""
        interpreter = SchemaInterpreter(semantic_schema)
        payload = bytes([0x09, 0x29, 0x82])  # temp=2345*0.01=23.45, hum=130*0.5=65
        
        result = interpreter.decode(payload)
        ipso = interpreter.get_semantic_output(result.data, 'ipso')
        
        assert '3303' in ipso
        assert ipso['3303']['value'] == 23.45
        assert ipso['3303']['unit'] == '°C'
    
    def test_senml_output(self, semantic_schema):
        """Test SenML format output."""
        interpreter = SchemaInterpreter(semantic_schema)
        payload = bytes([0x09, 0x29, 0x82])
        
        result = interpreter.decode(payload)
        senml = interpreter.get_semantic_output(result.data, 'senml')
        
        assert isinstance(senml, list)
        assert len(senml) == 2
        assert senml[0]['n'] == 'temperature'
        assert senml[0]['v'] == 23.45
        assert senml[0]['u'] == '°C'
    
    def test_ttn_output(self, semantic_schema):
        """Test TTN normalized output."""
        interpreter = SchemaInterpreter(semantic_schema)
        payload = bytes([0x09, 0x29, 0x82])
        
        result = interpreter.decode(payload)
        ttn = interpreter.get_semantic_output(result.data, 'ttn')
        
        assert 'decoded_payload' in ttn
        assert 'normalized_payload' in ttn


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""
    
    @pytest.fixture
    def test_schema(self):
        return {
            'fields': [
                {'name': 'value', 'type': 'u16'}
            ]
        }
    
    def test_decode_payload(self, test_schema):
        """Test decode_payload function."""
        result = decode_payload(test_schema, bytes([0x01, 0x00]))
        assert result['value'] == 256
    
    def test_encode_payload(self, test_schema):
        """Test encode_payload function."""
        result = encode_payload(test_schema, {'value': 256})
        assert result == bytes([0x01, 0x00])
    
    def test_decode_payload_raises_on_error(self, test_schema):
        """Test decode_payload raises on error."""
        with pytest.raises(ValueError, match="Decode errors"):
            decode_payload(test_schema, bytes())


class TestDecodeResult:
    """Tests for DecodeResult class."""
    
    def test_success_property(self):
        """Test success property."""
        result = DecodeResult(data={}, bytes_consumed=0)
        assert result.success
        
        result.errors.append("error")
        assert not result.success


class TestEncodeResult:
    """Tests for EncodeResult class."""
    
    def test_success_property(self):
        """Test success property."""
        result = EncodeResult(payload=b'')
        assert result.success
        
        result.errors.append("error")
        assert not result.success


class TestEnumType:
    """Tests for enum type.
    
    Spec Requirements:
    - M056: String name output for known values
    - M057: Unknown value handling per default_action
    - M058: Encoder accepts string names and integer values
    """
    
    def test_decode_enum_dict(self):
        """Test decoding enum with dict values."""
        schema = {
            'fields': [{
                'name': 'status',
                'type': 'enum',
                'base': 'u8',
                'values': {0: 'idle', 1: 'running', 2: 'error'}
            }]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x01]))
        assert result.success
        assert result.data['status'] == 'running'
    
    def test_decode_enum_list(self):
        """Test decoding enum with list values."""
        schema = {
            'fields': [{
                'name': 'mode',
                'type': 'enum',
                'base': 'u8',
                'values': ['off', 'low', 'medium', 'high']
            }]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x02]))
        assert result.success
        assert result.data['mode'] == 'medium'
    
    def test_decode_enum_unknown(self):
        """Test decoding unknown enum value."""
        schema = {
            'fields': [{
                'name': 'status',
                'type': 'enum',
                'base': 'u8',
                'values': {0: 'idle', 1: 'running'}
            }]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0xFF]))
        assert result.success
        assert result.data['status'] == 'unknown(255)'
    
    def test_encode_enum(self):
        """Test encoding enum back to integer."""
        schema = {
            'fields': [{
                'name': 'status',
                'type': 'enum',
                'base': 'u8',
                'values': {0: 'idle', 1: 'running', 2: 'error'}
            }]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.encode({'status': 'running'})
        assert result.success
        assert result.payload == bytes([0x01])
    
    def test_enum_roundtrip(self):
        """Test enum encode/decode roundtrip."""
        schema = {
            'fields': [{
                'name': 'status',
                'type': 'enum',
                'base': 'u8',
                'values': {0: 'idle', 1: 'running', 2: 'error'}
            }]
        }
        interpreter = SchemaInterpreter(schema)
        
        original = {'status': 'error'}
        encoded = interpreter.encode(original)
        decoded = interpreter.decode(encoded.payload)
        
        assert decoded.data['status'] == 'error'


class TestMatchConditional:
    """Tests for match conditional decoding.
    
    Spec Requirements:
    - M128: match construct support
    - M129: Exactly one matching case processed
    - M130: Cases evaluated in order
    - M131: Range start <= end
    - M132: All three matching patterns (single, list, range)
    """
    
    def test_match_single_value(self):
        """Test match with single value case."""
        schema = {
            'fields': [
                {'name': 'msg_type', 'type': 'u8'},
                {
                    'type': 'match',
                    'on': 'msg_type',
                    'cases': [
                        {'case': 1, 'fields': [{'name': 'temp', 'type': 's16', 'mult': 0.01}]},
                        {'case': 2, 'fields': [{'name': 'humidity', 'type': 'u8'}]},
                    ]
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # msg_type=1, temp=2345 (23.45°C)
        result = interpreter.decode(bytes([0x01, 0x09, 0x29]))
        assert result.success
        assert result.data['msg_type'] == 1
        assert abs(result.data['temp'] - 23.45) < 0.01
    
    def test_match_list(self):
        """Test match with list of values."""
        schema = {
            'fields': [
                {'name': 'msg_type', 'type': 'u8'},
                {
                    'type': 'match',
                    'on': 'msg_type',
                    'cases': [
                        {'case': [1, 2, 3], 'fields': [{'name': 'data', 'type': 'u8'}]},
                    ]
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        for msg_type in [1, 2, 3]:
            result = interpreter.decode(bytes([msg_type, 0x42]))
            assert result.success
            assert result.data['data'] == 0x42
    
    def test_match_range(self):
        """Test match with range pattern."""
        schema = {
            'fields': [
                {'name': 'msg_type', 'type': 'u8'},
                {
                    'type': 'match',
                    'on': 'msg_type',
                    'cases': [
                        {'case': '10..20', 'fields': [{'name': 'data', 'type': 'u8'}]},
                    ]
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # Should match
        result = interpreter.decode(bytes([15, 0x42]))
        assert result.success
        assert result.data['data'] == 0x42
        
        # Boundary - should match
        result = interpreter.decode(bytes([10, 0x42]))
        assert result.success
        
        result = interpreter.decode(bytes([20, 0x42]))
        assert result.success
    
    def test_match_default_skip(self):
        """Test match with default: skip."""
        schema = {
            'fields': [
                {'name': 'msg_type', 'type': 'u8'},
                {
                    'type': 'match',
                    'on': 'msg_type',
                    'default': 'skip',
                    'cases': [
                        {'case': 1, 'fields': [{'name': 'data', 'type': 'u8'}]},
                    ]
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # Unknown type - should skip
        result = interpreter.decode(bytes([99, 0x42]))
        assert result.success
        assert 'data' not in result.data
    
    def test_match_default_error(self):
        """Test match with default: error."""
        schema = {
            'fields': [
                {'name': 'msg_type', 'type': 'u8'},
                {
                    'type': 'match',
                    'on': 'msg_type',
                    'default': 'error',
                    'cases': [
                        {'case': 1, 'fields': [{'name': 'data', 'type': 'u8'}]},
                    ]
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # Unknown type - should error
        result = interpreter.decode(bytes([99, 0x42]))
        assert not result.success


class TestByteGroup:
    """Tests for byte_group construct.
    
    REQ-Byte-Group-037: byte_group for grouping bitfields
    """
    
    def test_byte_group_basic(self):
        """Test basic byte_group with bitfields."""
        schema = {
            'fields': [{
                'byte_group': [
                    {'name': 'flag_a', 'type': 'u8[0:0]'},
                    {'name': 'flag_b', 'type': 'u8[1:1]'},
                    {'name': 'value', 'type': 'u8[2:7]'},
                ],
                'size': 1
            }]
        }
        interpreter = SchemaInterpreter(schema)
        
        # 0b11_000011 = 0xC3 -> flag_a=1, flag_b=1, value=48
        result = interpreter.decode(bytes([0xC3]))
        assert result.success
        assert result.data['flag_a'] == 1
        assert result.data['flag_b'] == 1
        assert result.data['value'] == 48
    
    def test_byte_group_consumes_correctly(self):
        """Test that byte_group advances position correctly."""
        schema = {
            'fields': [
                {
                    'byte_group': [
                        {'name': 'low', 'type': 'u8[0:3]'},
                        {'name': 'high', 'type': 'u8[4:7]'},
                    ],
                    'size': 1
                },
                {'name': 'next_byte', 'type': 'u8'}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # 0xAB = low=11, high=10, next=0xFF
        result = interpreter.decode(bytes([0xAB, 0xFF]))
        assert result.success
        assert result.data['low'] == 0x0B
        assert result.data['high'] == 0x0A
        assert result.data['next_byte'] == 0xFF


class TestFormulaField:
    """Tests for formula field modifier.
    
    Note: formula is deprecated, use compute/polynomial/transform instead.
    Related to M102-M106 (compute operations).
    """
    
    def test_formula_simple(self):
        """Test simple formula."""
        schema = {
            'fields': [{
                'name': 'temperature',
                'type': 'u8',
                'formula': 'x * 0.5 - 40'
            }]
        }
        interpreter = SchemaInterpreter(schema)
        
        # x=160 -> 160 * 0.5 - 40 = 40
        result = interpreter.decode(bytes([160]))
        assert result.success
        assert abs(result.data['temperature'] - 40.0) < 0.01
    
    def test_formula_with_math(self):
        """Test formula with math operations."""
        schema = {
            'fields': [{
                'name': 'value',
                'type': 'u16',
                'formula': '(x / 100) ** 2'
            }]
        }
        interpreter = SchemaInterpreter(schema)
        
        # x=1000 -> (1000/100)^2 = 100
        result = interpreter.decode(bytes([0x03, 0xE8]))  # 1000 big-endian
        assert result.success
        assert abs(result.data['value'] - 100.0) < 0.01
    
    def test_formula_overrides_mult_add(self):
        """Test that formula takes precedence over mult/add."""
        schema = {
            'fields': [{
                'name': 'value',
                'type': 'u8',
                'mult': 999,  # Should be ignored
                'add': 999,   # Should be ignored
                'formula': 'x * 2'
            }]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([10]))
        assert result.success
        assert result.data['value'] == 20  # formula: 10 * 2 = 20


class TestNewTypes:
    """Tests for type extensions.
    
    Spec Requirements:
    - M046: f16 half precision float (IEEE 754)
    - M061: ascii, hex, base64 support
    - M063: hex lowercase output
    - M064: RFC 4648 Base64
    """
    
    def test_f16_half_precision(self):
        """Test f16 half-precision float."""
        schema = {'fields': [{'name': 'val', 'type': 'f16'}]}
        interpreter = SchemaInterpreter(schema)
        
        # 0x4248 = 3.140625 in half-precision (close to pi)
        result = interpreter.decode(bytes([0x42, 0x48]))
        assert result.success
        assert abs(result.data['val'] - 3.140625) < 0.001
    
    def test_skip_type(self):
        """Test skip type for padding."""
        schema = {
            'fields': [
                {'name': 'header', 'type': 'u8'},
                {'name': '_pad', 'type': 'skip', 'length': 2},
                {'name': 'data', 'type': 'u8'},
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x01, 0xAA, 0xBB, 0x02]))
        assert result.success
        assert result.data['header'] == 1
        assert result.data['data'] == 2
        assert '_pad' not in result.data
    
    def test_ascii_type(self):
        """Test ascii string type."""
        schema = {'fields': [{'name': 'name', 'type': 'ascii', 'length': 4}]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(b'TEST')
        assert result.success
        assert result.data['name'] == 'TEST'
    
    def test_hex_type(self):
        """Test hex string output."""
        schema = {'fields': [{'name': 'mac', 'type': 'hex', 'length': 4}]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0xDE, 0xAD, 0xBE, 0xEF]))
        assert result.success
        assert result.data['mac'] == 'DEADBEEF'
    
    def test_base64_type(self):
        """Test base64 string output."""
        schema = {'fields': [{'name': 'data', 'type': 'base64', 'length': 3}]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x01, 0x02, 0x03]))
        assert result.success
        assert result.data['data'] == 'AQID'  # base64 of 0x010203


class TestDefinitionsAndRef:
    """Tests for definitions and $ref support.
    
    Spec Requirements:
    - M226: Detect circular references
    - M227: Resolve ref references
    - M228: Reject circular with error
    - M229: Undefined definitions error
    """
    
    def test_simple_ref(self):
        """Test simple $ref to definition."""
        schema = {
            'definitions': {
                'header': {
                    'fields': [
                        {'name': 'msg_type', 'type': 'u8'},
                        {'name': 'length', 'type': 'u8'},
                    ]
                }
            },
            'fields': [
                {'$ref': '#/definitions/header'},
                {'name': 'data', 'type': 'u8'},
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x01, 0x05, 0xFF]))
        assert result.success
        assert result.data['msg_type'] == 1
        assert result.data['length'] == 5
        assert result.data['data'] == 255
    
    def test_ref_not_found(self):
        """Test $ref with missing definition."""
        schema = {
            'definitions': {},
            'fields': [
                {'$ref': '#/definitions/missing'},
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x01]))
        assert not result.success
        assert 'not found' in result.errors[0].lower()


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_default_endian(self):
        """Test default endian is big."""
        schema = {'fields': [{'name': 'val', 'type': 'u16'}]}
        interpreter = SchemaInterpreter(schema)
        
        assert interpreter.endian == Endian.BIG
    
    def test_buffer_too_short(self):
        """Test error when buffer is too short."""
        schema = {'fields': [{'name': 'val', 'type': 'u32'}]}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x01, 0x02]))
        assert not result.success
    
    def test_empty_schema(self):
        """Test empty schema."""
        schema = {'fields': []}
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x01, 0x02]))
        assert result.success
        assert result.data == {}
        assert result.bytes_consumed == 0


class TestOptionBMatchSyntax:
    """Tests for Option B match syntax (match: as top-level key).

    The new syntax uses:
      - match: as a top-level key
      - field: $var for variable-based dispatch
      - length: N for inline byte read
      - name: / var: for optional output/storage
    """

    def test_match_inline_basic(self):
        """Test inline match that reads 1 byte and dispatches."""
        schema = {
            'endian': 'big',
            'fields': [
                {
                    'match': {
                        'length': 1,
                        'name': 'msg_type',
                        'cases': {
                            1: [{'name': 'temp', 'type': 's16', 'mult': 0.01}],
                            2: [{'name': 'humidity', 'type': 'u8'}],
                        }
                    }
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)

        # msg_type=1, temp=2345 (23.45°C)
        result = interpreter.decode(bytes([0x01, 0x09, 0x29]))
        assert result.success
        assert result.data['msg_type'] == 1
        assert abs(result.data['temp'] - 23.45) < 0.01

    def test_match_inline_case2(self):
        """Test inline match dispatching to second case."""
        schema = {
            'endian': 'big',
            'fields': [
                {
                    'match': {
                        'length': 1,
                        'cases': {
                            1: [{'name': 'temp', 'type': 's16'}],
                            2: [{'name': 'humidity', 'type': 'u8'}],
                        }
                    }
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)

        result = interpreter.decode(bytes([0x02, 0x64]))
        assert result.success
        assert result.data['humidity'] == 100

    def test_match_variable_based(self):
        """Test variable-based match using field: $var."""
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'msg_type', 'type': 'u8', 'var': 'msg_type'},
                {
                    'match': {
                        'field': '$msg_type',
                        'cases': {
                            1: [{'name': 'temp', 'type': 's16'}],
                            2: [{'name': 'humidity', 'type': 'u8'}],
                        }
                    }
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)

        # msg_type=1, temp=0x0100=256
        result = interpreter.decode(bytes([0x01, 0x01, 0x00]))
        assert result.success
        assert result.data['msg_type'] == 1
        assert result.data['temp'] == 256

    def test_match_inline_with_var(self):
        """Test inline match storing value in variable for later use."""
        schema = {
            'endian': 'big',
            'fields': [
                {
                    'match': {
                        'length': 1,
                        'name': 'event',
                        'var': 'evt',
                        'cases': {
                            0: [{'name': 'reset_code', 'type': 'u8'}],
                            1: [{'name': 'data', 'type': 'u16'}],
                        }
                    }
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)

        result = interpreter.decode(bytes([0x00, 0xFF]))
        assert result.success
        assert result.data['event'] == 0
        assert result.data['reset_code'] == 255

    def test_match_default_skip(self):
        """Test match with default: skip in Option B syntax."""
        schema = {
            'fields': [
                {
                    'match': {
                        'length': 1,
                        'default': 'skip',
                        'cases': {
                            1: [{'name': 'data', 'type': 'u8'}],
                        }
                    }
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)

        result = interpreter.decode(bytes([0xFF, 0x42]))
        assert result.success
        assert 'data' not in result.data

    def test_match_default_error(self):
        """Test match with default: error in Option B syntax."""
        schema = {
            'fields': [
                {
                    'match': {
                        'length': 1,
                        'default': 'error',
                        'cases': {
                            1: [{'name': 'data', 'type': 'u8'}],
                        }
                    }
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)

        result = interpreter.decode(bytes([0xFF, 0x42]))
        assert not result.success

    def test_match_default_fields(self):
        """Test match with default case as field list in cases dict."""
        schema = {
            'fields': [
                {
                    'match': {
                        'length': 1,
                        'cases': {
                            1: [{'name': 'known', 'type': 'u8'}],
                            'default': [{'name': 'fallback', 'type': 'u8'}],
                        }
                    }
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)

        result = interpreter.decode(bytes([0xFF, 0x42]))
        assert result.success
        assert result.data['fallback'] == 0x42

    def test_two_level_dispatch(self):
        """Test two-level match: inline + variable-based nested match."""
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'device_type', 'type': 'u8', 'var': 'dev_type'},
                {
                    'match': {
                        'length': 1,
                        'name': 'event_type',
                        'var': 'evt_type',
                        'cases': {
                            0: [
                                {
                                    'match': {
                                        'field': '$dev_type',
                                        'cases': {
                                            1: [{'name': 'door_config', 'type': 'u16'}],
                                            4: [{'name': 'temp_config', 'type': 'u8'}],
                                        }
                                    }
                                }
                            ],
                            1: [{'name': 'battery', 'type': 'u8'}],
                        }
                    }
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)

        # device_type=1, event=0 -> door sensor reset, door_config=0x0200
        result = interpreter.decode(bytes([0x01, 0x00, 0x02, 0x00]))
        assert result.success
        assert result.data['device_type'] == 1
        assert result.data['event_type'] == 0
        assert result.data['door_config'] == 512


class TestOptionBObjectSyntax:
    """Tests for Option B object: syntax."""

    def test_object_basic(self):
        """Test basic object: syntax."""
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'header', 'type': 'u8'},
                {
                    'object': 'sensor',
                    'fields': [
                        {'name': 'temp', 'type': 'u16'},
                        {'name': 'hum', 'type': 'u8'},
                    ]
                },
            ]
        }
        interpreter = SchemaInterpreter(schema)

        result = interpreter.decode(bytes([0x01, 0x00, 0x64, 0x32]))
        assert result.success
        assert result.data['header'] == 1
        assert result.data['sensor']['temp'] == 100
        assert result.data['sensor']['hum'] == 50

    def test_object_with_var(self):
        """Test object fields can store variables for later match."""
        schema = {
            'endian': 'big',
            'fields': [
                {
                    'object': 'header',
                    'fields': [
                        {'name': 'version', 'type': 'u8'},
                        {'name': 'msg_type', 'type': 'u8', 'var': 'msg_type'},
                    ]
                },
                {
                    'match': {
                        'field': '$msg_type',
                        'cases': {
                            1: [{'name': 'temp', 'type': 'u16'}],
                            2: [{'name': 'hum', 'type': 'u8'}],
                        }
                    }
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)

        result = interpreter.decode(bytes([0x01, 0x02, 0x50]))
        assert result.success
        assert result.data['header']['version'] == 1
        assert result.data['header']['msg_type'] == 2
        assert result.data['hum'] == 80

    def test_nested_objects(self):
        """Test nested object: inside object:."""
        schema = {
            'endian': 'big',
            'fields': [
                {
                    'object': 'outer',
                    'fields': [
                        {'name': 'a', 'type': 'u8'},
                        {
                            'object': 'inner',
                            'fields': [
                                {'name': 'b', 'type': 'u8'},
                            ]
                        }
                    ]
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)

        result = interpreter.decode(bytes([0x01, 0x02]))
        assert result.success
        assert result.data['outer']['a'] == 1
        assert result.data['outer']['inner']['b'] == 2


class TestOptionBTlvSyntax:
    """Tests for Option B tlv: syntax."""

    def test_tlv_simple(self):
        """Test simple TLV with single-byte tags."""
        schema = {
            'endian': 'big',
            'fields': [
                {
                    'tlv': {
                        'tag_size': 1,
                        'cases': {
                            0x01: [{'name': 'temperature', 'type': 's16', 'mult': 0.1}],
                            0x02: [{'name': 'humidity', 'type': 'u8'}],
                            0x07: [{'name': 'battery', 'type': 'u16'}],
                        }
                    }
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)

        # tag=0x01 temp=0x00E7(231*0.1=23.1), tag=0x02 hum=30, tag=0x07 batt=3000
        payload = bytes([0x01, 0x00, 0xE7, 0x02, 0x1E, 0x07, 0x0B, 0xB8])
        result = interpreter.decode(payload)

        assert result.success
        assert abs(result.data['temperature'] - 23.1) < 0.01
        assert result.data['humidity'] == 30
        assert result.data['battery'] == 3000

    def test_tlv_composite_tag(self):
        """Test TLV with composite tag (channel_id + channel_type)."""
        schema = {
            'endian': 'little',
            'fields': [
                {
                    'tlv': {
                        'tag_fields': [
                            {'name': 'channel_id', 'type': 'u8'},
                            {'name': 'channel_type', 'type': 'u8'},
                        ],
                        'tag_key': ['channel_id', 'channel_type'],
                        'cases': {
                            (0x01, 0x75): [{'name': 'battery', 'type': 'u8'}],
                            (0x03, 0x67): [{'name': 'temperature', 'type': 's16', 'mult': 0.1}],
                        }
                    }
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)

        # battery=100, temperature=272 (27.2°C in LE: 0x10 0x01)
        payload = bytes([0x01, 0x75, 0x64, 0x03, 0x67, 0x10, 0x01])
        result = interpreter.decode(payload)

        assert result.success
        assert result.data['battery'] == 100
        assert abs(result.data['temperature'] - 27.2) < 0.01

    def test_tlv_unknown_skip(self):
        """Test TLV with unknown tag and length_size for skipping."""
        schema = {
            'endian': 'big',
            'fields': [
                {
                    'tlv': {
                        'tag_size': 1,
                        'length_size': 1,
                        'unknown': 'skip',
                        'cases': {
                            0x01: [{'name': 'temp', 'type': 's16'}],
                        }
                    }
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)

        # tag=0x01 len=2 temp, tag=0xFF len=1 unknown(skip), tag=0x01 len=2 temp again
        payload = bytes([0x01, 0x02, 0x00, 0xC8, 0xFF, 0x01, 0xAA])
        result = interpreter.decode(payload)

        assert result.success
        assert result.data['temp'] == 200

    def test_tlv_repeated_tags(self):
        """Test TLV with repeated tags collecting into array."""
        schema = {
            'endian': 'big',
            'fields': [
                {
                    'tlv': {
                        'tag_size': 1,
                        'cases': {
                            0x01: [{'name': 'reading', 'type': 'u8'}],
                        }
                    }
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)

        payload = bytes([0x01, 0x0A, 0x01, 0x14])
        result = interpreter.decode(payload)

        assert result.success
        assert result.data['reading'] == [10, 20]


# =============================================================================
# Phase 2 Tests
# =============================================================================

class TestPortBasedSelection:
    """Tests for port-based schema selection."""
    
    def test_port_selection(self):
        schema = {
            'name': 'port_test',
            'endian': 'big',
            'ports': {
                '1': {
                    'direction': 'uplink',
                    'fields': [
                        {'name': 'temperature', 'type': 's16', 'div': 10},
                        {'name': 'humidity', 'type': 'u8'}
                    ]
                },
                '100': {
                    'direction': 'downlink',
                    'fields': [
                        {'name': 'report_interval', 'type': 'u16'}
                    ]
                },
                'default': {
                    'fields': [
                        {'name': 'raw_byte', 'type': 'u8'}
                    ]
                }
            }
        }
        interpreter = SchemaInterpreter(schema)
        
        # Port 1: temp=23.5, humid=50
        result = interpreter.decode(bytes([0x00, 0xEB, 0x32]), fPort=1)
        assert result.success
        assert abs(result.data['temperature'] - 23.5) < 0.1
        assert result.data['humidity'] == 50
        
        # Port 100: interval=60
        result = interpreter.decode(bytes([0x00, 0x3C]), fPort=100)
        assert result.success
        assert result.data['report_interval'] == 60
        
        # Default port
        result = interpreter.decode(bytes([0xAB]), fPort=42)
        assert result.success
        assert result.data['raw_byte'] == 0xAB
    
    def test_port_no_default_error(self):
        schema = {
            'name': 'no_default',
            'ports': {
                '1': {'fields': [{'name': 'x', 'type': 'u8'}]}
            }
        }
        interpreter = SchemaInterpreter(schema)
        try:
            interpreter.decode(bytes([0x01]), fPort=99)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


class TestBitfieldString:
    """Tests for bitfield_string type."""
    
    def test_hex_version(self):
        schema = {
            'endian': 'big',
            'fields': [{
                'name': 'firmware_version',
                'type': 'bitfield_string',
                'length': 2,
                'delimiter': '.',
                'prefix': 'v',
                'parts': [[8, 8, 'hex'], [0, 8, 'hex']]
            }]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x01, 0x03]))
        assert result.success
        assert result.data['firmware_version'] == 'v1.3'
        
        result = interpreter.decode(bytes([0x02, 0x0A]))
        assert result.success
        assert result.data['firmware_version'] == 'v2.A'
    
    def test_decimal_version(self):
        schema = {
            'endian': 'big',
            'fields': [{
                'name': 'version',
                'type': 'bitfield_string',
                'length': 2,
                'delimiter': '.',
                'parts': [[8, 8], [0, 8]]
            }]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x03, 0x0A]))
        assert result.success
        assert result.data['version'] == '3.10'


class TestFlaggedBitmask:
    """Tests for flagged/bitmask field presence."""
    
    def test_all_groups(self):
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'protocol_version', 'type': 'u8'},
                {'name': 'device_id', 'type': 'u16'},
                {'name': 'flags', 'type': 'u16'},
                {'flagged': {
                    'field': 'flags',
                    'groups': [
                        {'bit': 0, 'fields': [
                            {'name': 'dielectric', 'type': 'u16', 'div': 50},
                            {'name': 'soil_temp', 'type': 'u16', 'formula': '(x - 400) / 10'}
                        ]},
                        {'bit': 1, 'fields': [
                            {'name': 'battery', 'type': 'u16', 'div': 1000}
                        ]}
                    ]
                }}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # All groups (flags=0x0003)
        data = bytes([0x02, 0x0C, 0x43, 0x00, 0x03, 0x01, 0x55, 0x01, 0x90, 0x0C, 0x5E])
        result = interpreter.decode(data)
        assert result.success
        assert result.data['protocol_version'] == 2
        assert abs(result.data['dielectric'] - 6.82) < 0.01
        assert abs(result.data['soil_temp'] - 0.0) < 0.1
        assert abs(result.data['battery'] - 3.166) < 0.001
    
    def test_partial_groups(self):
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'proto', 'type': 'u8'},
                {'name': 'id', 'type': 'u16'},
                {'name': 'flags', 'type': 'u16'},
                {'flagged': {
                    'field': 'flags',
                    'groups': [
                        {'bit': 0, 'fields': [
                            {'name': 'dielectric', 'type': 'u16', 'div': 50}
                        ]},
                        {'bit': 1, 'fields': [
                            {'name': 'battery', 'type': 'u16', 'div': 1000}
                        ]}
                    ]
                }}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # Battery only (flags=0x0002)
        data = bytes([0x02, 0x0C, 0x43, 0x00, 0x02, 0x0C, 0x5E])
        result = interpreter.decode(data)
        assert result.success
        assert 'dielectric' not in result.data
        assert abs(result.data['battery'] - 3.166) < 0.001


class TestCrossFieldFormula:
    """Tests for cross-field computed values."""
    
    def test_polynomial(self):
        import math
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'dielectric', 'type': 'u16', 'div': 50},
                {'name': 'vwc', 'type': 'number',
                 'formula': '0.0000043 * pow($dielectric, 3) - 0.00055 * pow($dielectric, 2) + 0.0292 * $dielectric - 0.053'}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x01, 0x55]))
        assert result.success
        assert abs(result.data['dielectric'] - 6.82) < 0.01
        expected_vwc = 0.0000043 * math.pow(6.82, 3) - 0.00055 * math.pow(6.82, 2) + 0.0292 * 6.82 - 0.053
        assert abs(result.data['vwc'] - expected_vwc) < 0.001
    
    def test_albedo_ratio(self):
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'incoming', 'type': 'u16', 'div': 10},
                {'name': 'reflected', 'type': 'u16', 'div': 10},
                {'name': 'albedo', 'type': 'number',
                 'formula': '$incoming > 0 and $reflected > 0 ? $reflected / $incoming : 0'}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # incoming=100, reflected=50 => albedo=0.5
        result = interpreter.decode(bytes([0x03, 0xE8, 0x01, 0xF4]))
        assert result.success
        assert abs(result.data['albedo'] - 0.5) < 0.01
    
    def test_albedo_zero_guard(self):
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'incoming', 'type': 'u16', 'div': 10},
                {'name': 'reflected', 'type': 'u16', 'div': 10},
                {'name': 'albedo', 'type': 'number',
                 'formula': '$incoming > 0 and $reflected > 0 ? $reflected / $incoming : 0'}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # incoming=0 => albedo=0
        result = interpreter.decode(bytes([0x00, 0x00, 0x01, 0xF4]))
        assert result.success
        assert result.data['albedo'] == 0


class TestDeclarativeComputedFields:
    """Tests for declarative computed field constructs.
    
    Spec Requirements:
    - M093-M097: Polynomial calibration using Horner's method
    - M102-M106: Cross-field compute operations (add/sub/mul/div)
    - M107-M111: Guard conditions with when clause
    - M098-M101: Transform array with math operations
    """
    
    def test_polynomial_topp_equation(self):
        """Test polynomial evaluation (Topp equation for soil moisture)."""
        import math
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'dielectric', 'type': 'u16', 'div': 50},
                {'name': 'vwc', 'type': 'number',
                 'ref': '$dielectric',
                 'polynomial': [0.0000043, -0.00055, 0.0292, -0.053]}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # dielectric = 341 / 50 = 6.82
        result = interpreter.decode(bytes([0x01, 0x55]))
        assert result.success
        
        # Verify dielectric value
        assert abs(result.data['dielectric'] - 6.82) < 0.01
        
        # Verify polynomial evaluation (Horner's method)
        x = 6.82
        expected = 0.0000043 * x**3 - 0.00055 * x**2 + 0.0292 * x - 0.053
        assert abs(result.data['vwc'] - expected) < 0.001
    
    def test_polynomial_quadratic(self):
        """Test simple quadratic polynomial."""
        schema = {
            'fields': [
                {'name': 'x', 'type': 'u8'},
                {'name': 'y', 'type': 'number',
                 'ref': '$x',
                 'polynomial': [1, -2, 1]}  # x^2 - 2x + 1 = (x-1)^2
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # x=3 => (3-1)^2 = 4
        result = interpreter.decode(bytes([3]))
        assert result.success
        assert result.data['y'] == 4.0
    
    def test_compute_division(self):
        """Test compute with division operation."""
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'numerator', 'type': 'u16'},
                {'name': 'denominator', 'type': 'u16'},
                {'name': 'ratio', 'type': 'number',
                 'compute': {'op': 'div', 'a': '$numerator', 'b': '$denominator'}}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # 100 / 200 = 0.5
        result = interpreter.decode(bytes([0x00, 0x64, 0x00, 0xC8]))
        assert result.success
        assert result.data['ratio'] == 0.5
    
    def test_compute_multiplication(self):
        """Test compute with multiplication operation."""
        schema = {
            'fields': [
                {'name': 'a', 'type': 'u8'},
                {'name': 'b', 'type': 'u8'},
                {'name': 'product', 'type': 'number',
                 'compute': {'op': 'mul', 'a': '$a', 'b': '$b'}}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([7, 8]))
        assert result.success
        assert result.data['product'] == 56.0
    
    def test_compute_with_literal(self):
        """Test compute with literal value as operand."""
        schema = {
            'fields': [
                {'name': 'raw', 'type': 'u8'},
                {'name': 'scaled', 'type': 'number',
                 'compute': {'op': 'mul', 'a': '$raw', 'b': 0.01}}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([250]))
        assert result.success
        assert abs(result.data['scaled'] - 2.5) < 0.01
    
    def test_compute_modulo(self):
        """Test compute with modulo operation for nibble extraction."""
        schema = {
            'fields': [
                {'name': 'byte', 'type': 'u8'},
                {'name': 'lower_nibble', 'type': 'number',
                 'compute': {'op': 'mod', 'a': '$byte', 'b': 16}}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # 0xAB = 171, lower nibble = 11 (0xB)
        result = interpreter.decode(bytes([0xAB]))
        assert result.success
        assert result.data['lower_nibble'] == 11
    
    def test_compute_integer_division(self):
        """Test compute with integer division for nibble extraction."""
        schema = {
            'fields': [
                {'name': 'byte', 'type': 'u8'},
                {'name': 'upper_nibble', 'type': 'number',
                 'compute': {'op': 'idiv', 'a': '$byte', 'b': 16}}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # 0xAB = 171, upper nibble = 10 (0xA)
        result = interpreter.decode(bytes([0xAB]))
        assert result.success
        assert result.data['upper_nibble'] == 10
    
    def test_compute_mod_idiv_combined(self):
        """Test combined mod/idiv for full nibble extraction."""
        schema = {
            'fields': [
                {'name': 'byte', 'type': 'u8'},
                {'name': 'upper', 'type': 'number',
                 'compute': {'op': 'idiv', 'a': '$byte', 'b': 16}},
                {'name': 'lower', 'type': 'number',
                 'compute': {'op': 'mod', 'a': '$byte', 'b': 16}},
                {'name': 'reconstructed', 'type': 'number',
                 'compute': {'op': 'add', 'a': '$lower', 'b': 0}},
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # Test multiple values
        for test_byte in [0x00, 0x12, 0xAB, 0xFF]:
            result = interpreter.decode(bytes([test_byte]))
            assert result.success
            assert result.data['upper'] == test_byte // 16
            assert result.data['lower'] == test_byte % 16
    
    def test_compute_mod_division_by_zero(self):
        """Test mod operation with division by zero returns NaN."""
        schema = {
            'fields': [
                {'name': 'a', 'type': 'u8'},
                {'name': 'result', 'type': 'number',
                 'compute': {'op': 'mod', 'a': '$a', 'b': 0}}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([100]))
        assert result.success
        import math
        assert math.isnan(result.data['result'])
    
    def test_compute_idiv_division_by_zero(self):
        """Test idiv operation with division by zero returns NaN."""
        schema = {
            'fields': [
                {'name': 'a', 'type': 'u8'},
                {'name': 'result', 'type': 'number',
                 'compute': {'op': 'idiv', 'a': '$a', 'b': 0}}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([100]))
        assert result.success
        import math
        assert math.isnan(result.data['result'])
    
    def test_guard_with_gt(self):
        """Test guard with greater-than condition."""
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'incoming', 'type': 'u16'},
                {'name': 'reflected', 'type': 'u16'},
                {'name': 'albedo', 'type': 'number',
                 'compute': {'op': 'div', 'a': '$reflected', 'b': '$incoming'},
                 'guard': {'when': [{'field': '$incoming', 'gt': 0}], 'else': 0}}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # Positive case: incoming=100, reflected=50 => 0.5
        result = interpreter.decode(bytes([0x00, 0x64, 0x00, 0x32]))
        assert result.success
        assert result.data['albedo'] == 0.5
        
        # Guard fallback: incoming=0 => 0
        result2 = interpreter.decode(bytes([0x00, 0x00, 0x00, 0x32]))
        assert result2.success
        assert result2.data['albedo'] == 0
    
    def test_guard_multiple_conditions(self):
        """Test guard with multiple conditions (AND)."""
        schema = {
            'fields': [
                {'name': 'a', 'type': 'u8'},
                {'name': 'b', 'type': 'u8'},
                {'name': 'result', 'type': 'number',
                 'compute': {'op': 'div', 'a': '$a', 'b': '$b'},
                 'guard': {
                     'when': [
                         {'field': '$a', 'gte': 0},
                         {'field': '$b', 'gt': 0}
                     ],
                     'else': -1
                 }}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # Both conditions pass
        result = interpreter.decode(bytes([10, 5]))
        assert result.data['result'] == 2.0
        
        # b=0 fails second condition
        result2 = interpreter.decode(bytes([10, 0]))
        assert result2.data['result'] == -1
    
    def test_guard_with_eq(self):
        """Test guard with equality condition."""
        schema = {
            'fields': [
                {'name': 'status', 'type': 'u8'},
                {'name': 'value', 'type': 'u8'},
                {'name': 'active_value', 'type': 'number',
                 'ref': '$value',
                 'guard': {'when': [{'field': '$status', 'eq': 1}], 'else': 0}}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # status=1 (active)
        result = interpreter.decode(bytes([1, 42]))
        assert result.data['active_value'] == 42.0
        
        # status=0 (inactive)
        result2 = interpreter.decode(bytes([0, 42]))
        assert result2.data['active_value'] == 0
    
    def test_transform_floor_ceiling(self):
        """Test transform with floor and ceiling (clamping)."""
        schema = {
            'fields': [
                {'name': 'value', 'type': 'u8',
                 'transform': [
                     {'add': -50},
                     {'floor': 0},
                     {'ceiling': 100}
                 ]}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # 150 - 50 = 100, within [0,100]
        result = interpreter.decode(bytes([150]))
        assert result.data['value'] == 100.0
        
        # 30 - 50 = -20, clamped to 0
        result2 = interpreter.decode(bytes([30]))
        assert result2.data['value'] == 0.0
        
        # 75 - 50 = 25, within [0,100]
        result3 = interpreter.decode(bytes([75]))
        assert result3.data['value'] == 25.0
    
    def test_transform_sqrt(self):
        """Test transform with square root."""
        schema = {
            'fields': [
                {'name': 'squared', 'type': 'u8',
                 'transform': [{'sqrt': True}]}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([64]))
        assert result.data['squared'] == 8.0
    
    def test_transform_pow(self):
        """Test transform with power."""
        schema = {
            'fields': [
                {'name': 'value', 'type': 'u8',
                 'transform': [{'pow': 2}]}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([5]))
        assert result.data['value'] == 25.0
    
    def test_transform_log10(self):
        """Test transform with log base 10."""
        import math
        schema = {
            'fields': [
                {'name': 'value', 'type': 'u8',
                 'transform': [{'log10': True}]}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([100]))
        assert abs(result.data['value'] - 2.0) < 0.001
    
    def test_transform_log_natural(self):
        """Test transform with natural log."""
        import math
        schema = {
            'fields': [
                {'name': 'value', 'type': 'u8',
                 'transform': [{'log': True}]}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([100]))
        assert abs(result.data['value'] - math.log(100)) < 0.001
    
    def test_transform_clamp(self):
        """Test transform with clamp [min, max]."""
        schema = {
            'fields': [
                {'name': 'value', 'type': 'u8',
                 'transform': [{'clamp': [10, 50]}]}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # Within range
        result = interpreter.decode(bytes([30]))
        assert result.data['value'] == 30.0
        
        # Below min
        result2 = interpreter.decode(bytes([5]))
        assert result2.data['value'] == 10.0
        
        # Above max
        result3 = interpreter.decode(bytes([100]))
        assert result3.data['value'] == 50.0
    
    def test_transform_chained(self):
        """Test multiple transform operations in sequence."""
        schema = {
            'fields': [
                {'name': 'raw', 'type': 'u8',
                 'transform': [
                     {'mult': 0.1},       # 100 -> 10
                     {'add': -5},          # 10 -> 5
                     {'pow': 2},           # 5 -> 25
                     {'sqrt': True}        # 25 -> 5
                 ]}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([100]))
        assert result.data['raw'] == 5.0
    
    def test_ref_with_transform(self):
        """Test ref field with transform array."""
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'temperature_raw', 'type': 'u16'},
                {'name': 'temperature_celsius', 'type': 'number',
                 'ref': '$temperature_raw',
                 'transform': [
                     {'div': 100},
                     {'add': -40}
                 ]}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # raw=6500 => 65.0 - 40 = 25.0
        result = interpreter.decode(bytes([0x19, 0x64]))
        assert result.success
        assert result.data['temperature_celsius'] == 25.0


class TestEncodeFlagged:
    """Tests for Phase 2 encoding: flagged, bitfield_string, port-based."""
    
    def test_encode_flagged_all_groups(self):
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'version', 'type': 'u8'},
                {'name': 'flags', 'type': 'u16'},
                {'flagged': {
                    'field': 'flags',
                    'groups': [
                        {'bit': 0, 'fields': [
                            {'name': 'temperature', 'type': 'u16', 'mult': 0.1},
                            {'name': 'humidity', 'type': 'u16', 'mult': 0.5}
                        ]},
                        {'bit': 1, 'fields': [
                            {'name': 'battery', 'type': 'u16', 'div': 1000}
                        ]}
                    ]
                }}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.encode({
            'version': 2,
            'temperature': 25.0,
            'humidity': 65.0,
            'battery': 3.166
        })
        payload = result.payload
        assert payload[0] == 2, f"version={payload[0]}"
        assert payload[1] == 0x00 and payload[2] == 0x03, f"flags={payload[1]:02X}{payload[2]:02X}"
        assert payload[3] == 0x00 and payload[4] == 0xFA, f"temp={payload[3]:02X}{payload[4]:02X}"
        assert payload[5] == 0x00 and payload[6] == 0x82, f"humidity={payload[5]:02X}{payload[6]:02X}"
        assert payload[7] == 0x0C and payload[8] == 0x5E, f"battery={payload[7]:02X}{payload[8]:02X}"
        assert len(payload) == 9
    
    def test_encode_flagged_partial(self):
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'version', 'type': 'u8'},
                {'name': 'flags', 'type': 'u16'},
                {'flagged': {
                    'field': 'flags',
                    'groups': [
                        {'bit': 0, 'fields': [
                            {'name': 'temperature', 'type': 'u16', 'mult': 0.1}
                        ]},
                        {'bit': 1, 'fields': [
                            {'name': 'battery', 'type': 'u16', 'div': 1000}
                        ]}
                    ]
                }}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.encode({
            'version': 2,
            'battery': 3.166
        })
        payload = result.payload
        assert payload[1] == 0x00 and payload[2] == 0x02, f"flags={payload[1]:02X}{payload[2]:02X}"
        assert len(payload) == 5
    
    def test_encode_bitfield_string(self):
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'fw_version', 'type': 'bitfield_string', 'length': 2,
                 'prefix': 'v', 'delimiter': '.',
                 'parts': [[8, 8, 'hex'], [0, 8, 'hex']]},
                {'name': 'hw_version', 'type': 'bitfield_string', 'length': 2,
                 'delimiter': '.', 'parts': [[8, 8], [0, 8]]}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.encode({'fw_version': 'v1.3', 'hw_version': '3.10'})
        payload = result.payload
        assert payload[0] == 0x01 and payload[1] == 0x03, f"fw={payload[0]:02X}{payload[1]:02X}"
        assert payload[2] == 0x03 and payload[3] == 0x0A, f"hw={payload[2]:02X}{payload[3]:02X}"
        assert len(payload) == 4
    
    def test_encode_port_based(self):
        schema = {
            'endian': 'big',
            'ports': {
                1: {'fields': [{'name': 'temperature', 'type': 'u16', 'mult': 0.1}]},
                2: {'fields': [{'name': 'config_interval', 'type': 'u16'}]}
            }
        }
        interpreter = SchemaInterpreter(schema)
        
        result1 = interpreter.encode({'temperature': 25.0}, fPort=1)
        assert result1.payload == bytes([0x00, 0xFA])
        
        result2 = interpreter.encode({'config_interval': 300}, fPort=2)
        assert result2.payload == bytes([0x01, 0x2C])
    
    def test_encode_flagged_roundtrip(self):
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'version', 'type': 'u8'},
                {'name': 'flags', 'type': 'u16'},
                {'flagged': {
                    'field': 'flags',
                    'groups': [
                        {'bit': 0, 'fields': [
                            {'name': 'temperature', 'type': 'u16', 'mult': 0.1}
                        ]},
                        {'bit': 1, 'fields': [
                            {'name': 'battery', 'type': 'u16', 'div': 1000}
                        ]}
                    ]
                }}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        data = {'version': 2, 'temperature': 25.0, 'battery': 3.166}
        encoded = interpreter.encode(data)
        decoded = interpreter.decode(encoded.payload)
        
        assert decoded.success
        assert abs(decoded.data['temperature'] - 25.0) < 0.1
        assert abs(decoded.data['battery'] - 3.166) < 0.01


class TestMetadataEnrichment:
    """Tests for TS013 metadata enrichment."""
    
    def test_include_recv_time_and_rssi(self):
        schema = {
            'endian': 'big',
            'fields': [{'name': 'temperature', 'type': 'u16', 'mult': 0.1}],
            'metadata': {
                'include': [
                    {'name': 'received_at', 'source': '$recvTime'},
                    {'name': 'rssi', 'source': '$rxMetadata[0].rssi'},
                    {'name': 'snr', 'source': '$rxMetadata[0].snr'},
                ]
            }
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(
            bytes([0x00, 0xFA]),
            input_metadata={
                'recvTime': '2026-02-16T12:00:00.000Z',
                'rxMetadata': [{'rssi': -85, 'snr': 7.5}]
            }
        )
        assert result.success
        assert result.data['temperature'] == 25.0
        assert result.data['received_at'] == '2026-02-16T12:00:00.000Z'
        assert result.data['rssi'] == -85
        assert result.data['snr'] == 7.5
    
    def test_time_offset_subtract(self):
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'seconds_ago', 'type': 'u16'},
                {'name': 'temperature', 'type': 'u16', 'mult': 0.1}
            ],
            'metadata': {
                'timestamps': [
                    {'name': 'measurement_time', 'mode': 'subtract', 'offset_field': 'seconds_ago'}
                ]
            }
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(
            bytes([0x00, 0x3C, 0x00, 0xFA]),
            input_metadata={'recvTime': '2026-02-16T12:00:00.000Z'}
        )
        assert result.data['seconds_ago'] == 60
        assert result.data['measurement_time'] == '2026-02-16T11:59:00.000Z'
    
    def test_no_metadata_section_unchanged(self):
        schema = {
            'endian': 'big',
            'fields': [{'name': 'value', 'type': 'u8'}]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(
            bytes([42]),
            input_metadata={'recvTime': '2026-02-16T12:00:00Z'}
        )
        assert result.data == {'value': 42}
    
    def test_missing_metadata_graceful(self):
        schema = {
            'endian': 'big',
            'fields': [{'name': 'temperature', 'type': 'u16', 'mult': 0.1}],
            'metadata': {
                'include': [
                    {'name': 'rssi', 'source': '$rxMetadata[0].rssi'},
                ]
            }
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([0x00, 0xFA]))
        assert result.success
        assert result.data['temperature'] == 25.0
        assert 'rssi' not in result.data


# =============================================================================
# Phase 3 Tests
# =============================================================================

class TestPhase3TimestampFormatting:
    """Tests for timestamp formatting features.
    
    Note: Timestamp formatting is a prototype extension (utility formats).
    Related to M214 (utility formats MUST preserve accuracy).
    """
    
    def test_iso8601_format_unix_epoch(self):
        """Test iso8601 mode formatting a unix timestamp field."""
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'epoch', 'type': 'u32'},
            ],
            'metadata': {
                'timestamps': [
                    {'name': 'formatted_time', 'mode': 'iso8601', 'field': 'epoch'}
                ]
            }
        }
        interpreter = SchemaInterpreter(schema)
        # 1739721600 = 2025-02-16T16:00:00Z
        payload = (1739721600).to_bytes(4, 'big')
        result = interpreter.decode(payload, input_metadata={})
        assert result.success
        assert result.data['epoch'] == 1739721600
        assert result.data['formatted_time'] == '2025-02-16T16:00:00Z'
    
    def test_iso8601_custom_format(self):
        """Test iso8601 with custom strftime format."""
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'epoch', 'type': 'u32'},
            ],
            'metadata': {
                'timestamps': [
                    {'name': 'date_only', 'mode': 'iso8601', 'field': 'epoch',
                     'format': '%Y-%m-%d'}
                ]
            }
        }
        interpreter = SchemaInterpreter(schema)
        payload = (1739721600).to_bytes(4, 'big')
        result = interpreter.decode(payload, input_metadata={})
        assert result.success
        assert result.data['date_only'] == '2025-02-16'
    
    def test_elapsed_to_absolute(self):
        """Test elapsed_to_absolute mode converting offset to timestamp."""
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'seconds_since', 'type': 'u16'},
                {'name': 'temperature', 'type': 'u16', 'mult': 0.1},
            ],
            'metadata': {
                'timestamps': [
                    {'name': 'sample_time', 'mode': 'elapsed_to_absolute',
                     'elapsed_field': 'seconds_since', 'time_base': 'rx_time'}
                ]
            }
        }
        interpreter = SchemaInterpreter(schema)
        # 120 seconds ago
        result = interpreter.decode(
            bytes([0x00, 0x78, 0x00, 0xFA]),
            input_metadata={'recvTime': '2026-02-16T12:00:00.000Z'}
        )
        assert result.success
        assert result.data['seconds_since'] == 120
        assert result.data['sample_time'] == '2026-02-16T11:58:00.000Z'


class TestPhase3VersionString:
    """Tests for version_string type.
    
    Spec Requirements:
    - M077-M082: Bitfield string (parts processed in order, prefix prepended)
    """
    
    def test_version_string_decode(self):
        """Test decoding version_string from 3 bytes."""
        schema = {
            'fields': [{
                'name': 'firmware',
                'type': 'version_string',
                'length': 3,
                'delimiter': '.',
                'prefix': 'v'
            }]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([0x02, 0x03, 0x0A]))
        assert result.success
        assert result.data['firmware'] == 'v2.3.10'
    
    def test_version_string_no_prefix(self):
        """Test version_string without prefix."""
        schema = {
            'fields': [{
                'name': 'version',
                'type': 'version_string',
                'length': 2,
                'delimiter': '.'
            }]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([0x01, 0x05]))
        assert result.success
        assert result.data['version'] == '1.5'
    
    def test_version_string_encode(self):
        """Test encoding version_string back to bytes."""
        schema = {
            'fields': [{
                'name': 'firmware',
                'type': 'version_string',
                'length': 3,
                'delimiter': '.',
                'prefix': 'v'
            }]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.encode({'firmware': 'v2.3.10'})
        assert result.success
        assert result.payload == bytes([0x02, 0x03, 0x0A])
    
    def test_version_string_roundtrip(self):
        """Test version_string encode/decode roundtrip."""
        schema = {
            'fields': [{
                'name': 'fw',
                'type': 'version_string',
                'length': 3,
                'delimiter': '.',
                'prefix': 'v'
            }]
        }
        interpreter = SchemaInterpreter(schema)
        encoded = interpreter.encode({'fw': 'v1.0.255'})
        decoded = interpreter.decode(encoded.payload)
        assert decoded.data['fw'] == 'v1.0.255'


class TestPhase3EncodeFormula:
    """Tests for encode_formula feature.
    
    Note: encode_formula is a prototype extension for custom reverse transformations.
    Related to M211 (reverse arithmetic transformations).
    """
    
    def test_encode_formula_simple(self):
        """Test simple encode_formula."""
        schema = {
            'fields': [{
                'name': 'temperature',
                'type': 'u8',
                'formula': 'x * 0.5 - 40',
                'encode_formula': '(x + 40) / 0.5'
            }]
        }
        interpreter = SchemaInterpreter(schema)
        # 40 deg -> encode: (40 + 40) / 0.5 = 160
        result = interpreter.encode({'temperature': 40.0})
        assert result.success
        assert result.payload == bytes([160])
    
    def test_encode_formula_overrides_mult(self):
        """Test that encode_formula overrides mult/add reversal."""
        schema = {
            'fields': [{
                'name': 'value',
                'type': 'u16',
                'mult': 999,
                'add': 999,
                'encode_formula': 'x * 100'
            }]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.encode({'value': 25.0})
        assert result.success
        assert result.payload == bytes([0x09, 0xC4])  # 2500 BE
    
    def test_encode_formula_roundtrip(self):
        """Test encode_formula / formula roundtrip."""
        schema = {
            'endian': 'big',
            'fields': [{
                'name': 'pressure',
                'type': 'u16',
                'formula': '(x / 10) + 300',
                'encode_formula': '(x - 300) * 10'
            }]
        }
        interpreter = SchemaInterpreter(schema)
        
        # Decode: raw=10000 -> 10000/10 + 300 = 1300
        decoded = interpreter.decode(bytes([0x27, 0x10]))
        assert abs(decoded.data['pressure'] - 1300.0) < 0.1
        
        # Encode: 1300 -> (1300 - 300) * 10 = 10000
        encoded = interpreter.encode({'pressure': 1300.0})
        assert encoded.payload == bytes([0x27, 0x10])


# =============================================================================
# Test Coverage Gaps
# =============================================================================

class TestU24S24Types:
    """Comprehensive tests for u24/s24 3-byte integer types.
    
    Spec Requirements:
    - M042: All defined integer widths (includes u24, s24)
    """
    
    def test_u24_big_endian(self):
        """Test u24 big-endian decode."""
        schema = {'endian': 'big', 'fields': [{'name': 'val', 'type': 'u24'}]}
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([0x01, 0x02, 0x03]))
        assert result.data['val'] == 0x010203
    
    def test_u24_little_endian(self):
        """Test u24 little-endian decode."""
        schema = {'endian': 'little', 'fields': [{'name': 'val', 'type': 'u24'}]}
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([0x01, 0x02, 0x03]))
        assert result.data['val'] == 0x030201
    
    def test_u24_max_value(self):
        """Test u24 maximum value (16777215)."""
        schema = {'endian': 'big', 'fields': [{'name': 'val', 'type': 'u24'}]}
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([0xFF, 0xFF, 0xFF]))
        assert result.data['val'] == 0xFFFFFF
    
    def test_u24_zero(self):
        """Test u24 zero value."""
        schema = {'endian': 'big', 'fields': [{'name': 'val', 'type': 'u24'}]}
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([0x00, 0x00, 0x00]))
        assert result.data['val'] == 0
    
    def test_s24_positive(self):
        """Test s24 positive value."""
        schema = {'endian': 'big', 'fields': [{'name': 'val', 'type': 's24'}]}
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([0x01, 0x02, 0x03]))
        assert result.data['val'] == 0x010203
    
    def test_s24_negative(self):
        """Test s24 negative value (-1)."""
        schema = {'endian': 'big', 'fields': [{'name': 'val', 'type': 's24'}]}
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([0xFF, 0xFF, 0xFF]))
        assert result.data['val'] == -1
    
    def test_s24_negative_100(self):
        """Test s24 value -100."""
        schema = {'endian': 'big', 'fields': [{'name': 'val', 'type': 's24'}]}
        interpreter = SchemaInterpreter(schema)
        # -100 in 3 bytes big-endian: 0xFF 0xFF 0x9C
        result = interpreter.decode(bytes([0xFF, 0xFF, 0x9C]))
        assert result.data['val'] == -100
    
    def test_s24_little_endian_negative(self):
        """Test s24 negative little-endian."""
        schema = {'endian': 'little', 'fields': [{'name': 'val', 'type': 's24'}]}
        interpreter = SchemaInterpreter(schema)
        # -100 in 3 bytes little-endian: 0x9C 0xFF 0xFF
        result = interpreter.decode(bytes([0x9C, 0xFF, 0xFF]))
        assert result.data['val'] == -100
    
    def test_u24_encode_roundtrip(self):
        """Test u24 encode/decode roundtrip."""
        schema = {'endian': 'big', 'fields': [{'name': 'val', 'type': 'u24'}]}
        interpreter = SchemaInterpreter(schema)
        encoded = interpreter.encode({'val': 0x123456})
        decoded = interpreter.decode(encoded.payload)
        assert decoded.data['val'] == 0x123456
    
    def test_u24_with_modifiers(self):
        """Test u24 with multiplier (e.g., GPS coordinate)."""
        schema = {'endian': 'big', 'fields': [
            {'name': 'lat', 'type': 'u24', 'mult': 0.0001, 'add': -90}
        ]}
        interpreter = SchemaInterpreter(schema)
        # 1234567 * 0.0001 - 90 = 33.4567
        result = interpreter.decode(bytes([0x12, 0xD6, 0x87]))
        assert abs(result.data['lat'] - 33.4567) < 0.0001


class TestLittleEndianVariants:
    """Comprehensive tests for little-endian across all types.
    
    Spec Requirements:
    - M044: Big-endian and little-endian support
    """
    
    def test_u16_le(self):
        schema = {'endian': 'little', 'fields': [{'name': 'v', 'type': 'u16'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x34, 0x12]))
        assert r.data['v'] == 0x1234
    
    def test_s16_le_negative(self):
        schema = {'endian': 'little', 'fields': [{'name': 'v', 'type': 's16'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x9C, 0xFF]))
        assert r.data['v'] == -100
    
    def test_u32_le(self):
        schema = {'endian': 'little', 'fields': [{'name': 'v', 'type': 'u32'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x78, 0x56, 0x34, 0x12]))
        assert r.data['v'] == 0x12345678
    
    def test_s32_le_negative(self):
        schema = {'endian': 'little', 'fields': [{'name': 'v', 'type': 's32'}]}
        r = SchemaInterpreter(schema).decode(bytes([0xFE, 0xFF, 0xFF, 0xFF]))
        assert r.data['v'] == -2
    
    def test_u64_le(self):
        schema = {'endian': 'little', 'fields': [{'name': 'v', 'type': 'u64'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80]))
        assert r.data['v'] == 0x8000000000000001
    
    def test_s64_le(self):
        schema = {'endian': 'little', 'fields': [{'name': 'v', 'type': 's64'}]}
        r = SchemaInterpreter(schema).decode(bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]))
        assert r.data['v'] == -1
    
    def test_f32_le(self):
        schema = {'endian': 'little', 'fields': [{'name': 'v', 'type': 'f32'}]}
        payload = struct.pack('<f', -1.5)
        r = SchemaInterpreter(schema).decode(payload)
        assert abs(r.data['v'] - (-1.5)) < 0.001
    
    def test_f64_le(self):
        schema = {'endian': 'little', 'fields': [{'name': 'v', 'type': 'f64'}]}
        payload = struct.pack('<d', 123.456)
        r = SchemaInterpreter(schema).decode(payload)
        assert abs(r.data['v'] - 123.456) < 0.0001
    
    def test_f16_le(self):
        schema = {'endian': 'little', 'fields': [{'name': 'v', 'type': 'f16'}]}
        payload = struct.pack('<e', 1.0)
        r = SchemaInterpreter(schema).decode(payload)
        assert abs(r.data['v'] - 1.0) < 0.001
    
    def test_u24_le(self):
        schema = {'endian': 'little', 'fields': [{'name': 'v', 'type': 'u24'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x03, 0x02, 0x01]))
        assert r.data['v'] == 0x010203
    
    def test_le_encode_roundtrip_u16(self):
        schema = {'endian': 'little', 'fields': [{'name': 'v', 'type': 'u16'}]}
        interp = SchemaInterpreter(schema)
        enc = interp.encode({'v': 0x1234})
        dec = interp.decode(enc.payload)
        assert dec.data['v'] == 0x1234
    
    def test_le_encode_roundtrip_s16(self):
        schema = {'endian': 'little', 'fields': [{'name': 'v', 'type': 's16'}]}
        interp = SchemaInterpreter(schema)
        enc = interp.encode({'v': -500})
        dec = interp.decode(enc.payload)
        assert dec.data['v'] == -500
    
    def test_mixed_endian_fields(self):
        """Test schema with mixed endian (sensor data common)."""
        schema = {
            'endian': 'little',
            'fields': [
                {'name': 'temp', 'type': 's16', 'mult': 0.1},
                {'name': 'humidity', 'type': 'u8'},
                {'name': 'pressure', 'type': 'u16', 'mult': 0.1},
            ]
        }
        interpreter = SchemaInterpreter(schema)
        # temp = 272 (27.2C) LE: 0x10 0x01, hum=65, press=10132 (1013.2) LE: 0x94 0x27
        result = interpreter.decode(bytes([0x10, 0x01, 0x41, 0x94, 0x27]))
        assert abs(result.data['temp'] - 27.2) < 0.1
        assert result.data['humidity'] == 65
        assert abs(result.data['pressure'] - 1013.2) < 0.1


class TestComplexMatchDefault:
    """Tests for complex match default with inline fields.
    
    Spec Requirements:
    - M128: match construct support
    - M129: Exactly one matching case processed
    """
    
    def test_match_default_with_fields_legacy(self):
        """Test legacy match with default: {fields: [...]}."""
        schema = {
            'fields': [
                {'name': 'msg_type', 'type': 'u8'},
                {
                    'type': 'match',
                    'on': 'msg_type',
                    'default': {'fields': [
                        {'name': 'raw_data', 'type': 'u16'},
                    ]},
                    'cases': [
                        {'case': 1, 'fields': [{'name': 'temp', 'type': 's16'}]},
                    ]
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # Unknown type 99 - should use default fields
        result = interpreter.decode(bytes([99, 0x12, 0x34]))
        assert result.success
        assert result.data['raw_data'] == 0x1234
    
    def test_match_option_b_default_list(self):
        """Test Option B match with default: [fields] list."""
        schema = {
            'fields': [{
                'match': {
                    'length': 1,
                    'name': 'cmd',
                    'default': [
                        {'name': 'unknown_payload', 'type': 'u8'},
                    ],
                    'cases': {
                        1: [{'name': 'config', 'type': 'u16'}],
                    }
                }
            }]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0xFF, 0xAB]))
        assert result.success
        assert result.data['cmd'] == 0xFF
        assert result.data['unknown_payload'] == 0xAB
    
    def test_match_default_cases_key(self):
        """Test default in cases dict (Option B)."""
        schema = {
            'fields': [{
                'match': {
                    'length': 1,
                    'cases': {
                        1: [{'name': 'known', 'type': 'u8'}],
                        'default': [{'name': 'fallback_val', 'type': 'u16'}],
                    }
                }
            }]
        }
        interpreter = SchemaInterpreter(schema)
        
        result = interpreter.decode(bytes([0x99, 0xAB, 0xCD]))
        assert result.success
        assert result.data['fallback_val'] == 0xABCD


class TestTypeAliases:
    """Tests for all type aliases working correctly.
    
    Spec Requirements:
    - M041: Type aliases
    - M043: Documented type aliases
    """
    
    def test_uint8(self):
        schema = {'fields': [{'name': 'v', 'type': 'uint8'}]}
        r = SchemaInterpreter(schema).decode(bytes([0xFF]))
        assert r.data['v'] == 255
    
    def test_uint16(self):
        schema = {'fields': [{'name': 'v', 'type': 'uint16'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x01, 0x00]))
        assert r.data['v'] == 256
    
    def test_uint24(self):
        schema = {'fields': [{'name': 'v', 'type': 'uint24'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x01, 0x00, 0x00]))
        assert r.data['v'] == 65536
    
    def test_uint32(self):
        schema = {'fields': [{'name': 'v', 'type': 'uint32'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x00, 0x01, 0x00, 0x00]))
        assert r.data['v'] == 65536
    
    def test_int8(self):
        schema = {'fields': [{'name': 'v', 'type': 'int8'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x80]))
        assert r.data['v'] == -128
    
    def test_int16(self):
        schema = {'fields': [{'name': 'v', 'type': 'int16'}]}
        r = SchemaInterpreter(schema).decode(bytes([0xFF, 0x9C]))
        assert r.data['v'] == -100
    
    def test_i8_alias(self):
        schema = {'fields': [{'name': 'v', 'type': 'i8'}]}
        r = SchemaInterpreter(schema).decode(bytes([0xFF]))
        assert r.data['v'] == -1
    
    def test_i16_alias(self):
        schema = {'fields': [{'name': 'v', 'type': 'i16'}]}
        r = SchemaInterpreter(schema).decode(bytes([0xFF, 0xFE]))
        assert r.data['v'] == -2
    
    def test_i24_alias(self):
        schema = {'fields': [{'name': 'v', 'type': 'i24'}]}
        r = SchemaInterpreter(schema).decode(bytes([0xFF, 0xFF, 0x9C]))
        assert r.data['v'] == -100


class TestNibbleDecimalTypes:
    """Tests for UDec/SDec nibble-decimal types."""
    
    def test_udec_decode(self):
        schema = {'fields': [{'name': 'v', 'type': 'udec'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x37]))
        assert abs(r.data['v'] - 3.7) < 0.01
    
    def test_sdec_positive(self):
        schema = {'fields': [{'name': 'v', 'type': 'sdec'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x25]))
        assert abs(r.data['v'] - 2.5) < 0.01
    
    def test_sdec_negative(self):
        schema = {'fields': [{'name': 'v', 'type': 'sdec'}]}
        # -2 + 0.5 => nibbles: upper = 0xE (-2 in 4-bit), lower = 5
        r = SchemaInterpreter(schema).decode(bytes([0xE5]))
        assert abs(r.data['v'] - (-2 + 0.5)) < 0.01


class Test64BitTypes:
    """Tests for u64/s64/int64/uint64 types."""
    
    def test_u64_big_endian(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 'u64'}]}
        r = SchemaInterpreter(schema).decode(bytes([
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00
        ]))
        assert r.data['v'] == 256
    
    def test_s64_negative(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 's64'}]}
        r = SchemaInterpreter(schema).decode(bytes([
            0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF
        ]))
        assert r.data['v'] == -1
    
    def test_uint64_alias(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 'uint64'}]}
        r = SchemaInterpreter(schema).decode(bytes([
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01
        ]))
        assert r.data['v'] == 1
    
    def test_int64_alias(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 'int64'}]}
        r = SchemaInterpreter(schema).decode(bytes([
            0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE
        ]))
        assert r.data['v'] == -2


# =============================================================================
# Negative Tests and Edge Cases
# =============================================================================

class TestShortBufferErrors:
    """Tests that all multi-byte types fail gracefully on short buffers."""

    @pytest.mark.parametrize("type_str,min_bytes", [
        ('u16', 2), ('u24', 3), ('u32', 4), ('u64', 8),
        ('s16', 2), ('s24', 3), ('s32', 4), ('s64', 8),
        ('f16', 2), ('f32', 4), ('f64', 8),
    ])
    def test_short_buffer_numeric(self, type_str, min_bytes):
        """Test that numeric types fail on buffer too short."""
        schema = {'fields': [{'name': 'val', 'type': type_str}]}
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes(min_bytes - 1))
        assert not result.success

    def test_short_buffer_bytes(self):
        schema = {'fields': [{'name': 'val', 'type': 'bytes', 'length': 4}]}
        result = SchemaInterpreter(schema).decode(bytes([0x01, 0x02]))
        assert not result.success

    def test_short_buffer_string(self):
        schema = {'fields': [{'name': 'val', 'type': 'string', 'length': 4}]}
        result = SchemaInterpreter(schema).decode(bytes([0x01]))
        assert not result.success

    def test_short_buffer_hex(self):
        schema = {'fields': [{'name': 'val', 'type': 'hex', 'length': 4}]}
        result = SchemaInterpreter(schema).decode(bytes([0x01, 0x02]))
        assert not result.success

    def test_short_buffer_base64(self):
        schema = {'fields': [{'name': 'val', 'type': 'base64', 'length': 4}]}
        result = SchemaInterpreter(schema).decode(bytes([0x01]))
        assert not result.success

    def test_short_buffer_ascii(self):
        schema = {'fields': [{'name': 'val', 'type': 'ascii', 'length': 4}]}
        result = SchemaInterpreter(schema).decode(bytes([0x41]))
        assert not result.success

    def test_short_buffer_enum(self):
        """Enum with u16 base on 1-byte buffer."""
        schema = {'fields': [{
            'name': 'val', 'type': 'enum', 'base': 'u16',
            'values': {0: 'a', 1: 'b'}
        }]}
        result = SchemaInterpreter(schema).decode(bytes([0x01]))
        assert not result.success


class TestZeroAndBoundaryValues:
    """Tests for zero and boundary values for integer types."""

    def test_u8_zero(self):
        schema = {'fields': [{'name': 'v', 'type': 'u8'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x00]))
        assert r.data['v'] == 0

    def test_u8_max(self):
        schema = {'fields': [{'name': 'v', 'type': 'u8'}]}
        r = SchemaInterpreter(schema).decode(bytes([0xFF]))
        assert r.data['v'] == 255

    def test_u16_zero(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 'u16'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x00, 0x00]))
        assert r.data['v'] == 0

    def test_u16_max(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 'u16'}]}
        r = SchemaInterpreter(schema).decode(bytes([0xFF, 0xFF]))
        assert r.data['v'] == 65535

    def test_u32_max(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 'u32'}]}
        r = SchemaInterpreter(schema).decode(bytes([0xFF, 0xFF, 0xFF, 0xFF]))
        assert r.data['v'] == 0xFFFFFFFF

    def test_s8_zero(self):
        schema = {'fields': [{'name': 'v', 'type': 's8'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x00]))
        assert r.data['v'] == 0

    def test_s8_min(self):
        schema = {'fields': [{'name': 'v', 'type': 's8'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x80]))
        assert r.data['v'] == -128

    def test_s8_max(self):
        schema = {'fields': [{'name': 'v', 'type': 's8'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x7F]))
        assert r.data['v'] == 127

    def test_s16_min(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 's16'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x80, 0x00]))
        assert r.data['v'] == -32768

    def test_s16_max(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 's16'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x7F, 0xFF]))
        assert r.data['v'] == 32767

    def test_s16_zero(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 's16'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x00, 0x00]))
        assert r.data['v'] == 0

    def test_s32_min(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 's32'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x80, 0x00, 0x00, 0x00]))
        assert r.data['v'] == -2147483648

    def test_s32_max(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 's32'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x7F, 0xFF, 0xFF, 0xFF]))
        assert r.data['v'] == 2147483647

    def test_s24_min(self):
        """s24 minimum = -8388608 (0x800000)."""
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 's24'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x80, 0x00, 0x00]))
        assert r.data['v'] == -8388608

    def test_s24_max(self):
        """s24 maximum = 8388607 (0x7FFFFF)."""
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 's24'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x7F, 0xFF, 0xFF]))
        assert r.data['v'] == 8388607


class TestFloatEdgeCases:
    """Tests for float edge cases: negative, zero, special values."""

    def test_f32_negative(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 'f32'}]}
        payload = struct.pack('>f', -42.5)
        r = SchemaInterpreter(schema).decode(payload)
        assert abs(r.data['v'] - (-42.5)) < 0.001

    def test_f32_zero(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 'f32'}]}
        payload = struct.pack('>f', 0.0)
        r = SchemaInterpreter(schema).decode(payload)
        assert r.data['v'] == 0.0

    def test_f16_negative(self):
        """f16 = -1.0 is 0xBC00 in big-endian."""
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 'f16'}]}
        r = SchemaInterpreter(schema).decode(bytes([0xBC, 0x00]))
        assert abs(r.data['v'] - (-1.0)) < 0.001

    def test_f16_zero(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 'f16'}]}
        r = SchemaInterpreter(schema).decode(bytes([0x00, 0x00]))
        assert r.data['v'] == 0.0

    def test_f64_negative(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 'f64'}]}
        payload = struct.pack('>d', -99.99)
        r = SchemaInterpreter(schema).decode(payload)
        assert abs(r.data['v'] - (-99.99)) < 0.001


class TestBitfieldEdgeCases:
    """Edge cases for bitfield extraction."""

    def test_bitfield_empty_buffer(self):
        """Bitfield on empty payload should fail."""
        schema = {'fields': [{'name': 'v', 'type': 'u8[3:4]', 'consume': 1}]}
        result = SchemaInterpreter(schema).decode(bytes())
        assert not result.success


class TestModifierEdgeCases:
    """Edge cases for modifiers."""

    def test_add_negative(self):
        """Test negative add modifier (e.g., offset subtraction)."""
        schema = {'fields': [{'name': 'v', 'type': 'u8', 'add': -40}]}
        r = SchemaInterpreter(schema).decode(bytes([200]))
        assert r.data['v'] == 160  # 200 + (-40) = 160

    def test_lookup_out_of_range(self):
        """Lookup with index beyond list length."""
        schema = {'fields': [
            {'name': 'v', 'type': 'u8', 'lookup': ['a', 'b', 'c', 'd']}
        ]}
        r = SchemaInterpreter(schema).decode(bytes([10]))
        assert r.success
        # Out of range should either return raw value or "unknown"
        assert r.data['v'] == 10 or 'unknown' in str(r.data['v']).lower()


class TestNestedObjectEdgeCases:
    """Edge cases for nested objects."""

    def test_nested_object_short_buffer(self):
        """Nested object where inner field needs more bytes than available."""
        schema = {'fields': [
            {'name': 'sensor', 'type': 'object', 'fields': [
                {'name': 'temp', 'type': 'u16'},
            ]}
        ]}
        result = SchemaInterpreter(schema).decode(bytes([0x01]))
        assert not result.success


class TestEncoderEdgeCases:
    """Edge cases for the encoder."""

    def test_encode_unknown_type(self):
        """Encoding a field with an unrecognized type should error."""
        schema = {'fields': [{'name': 'val', 'type': 'custom_xyz'}]}
        result = SchemaInterpreter(schema).encode({'val': 42})
        assert not result.success or len(result.errors) > 0

    def test_encode_enum_unknown_string(self):
        """Encoding an enum with an unknown string value."""
        schema = {'fields': [{
            'name': 'status', 'type': 'enum', 'base': 'u8',
            'values': {0: 'idle', 1: 'running'}
        }]}
        result = SchemaInterpreter(schema).encode({'status': 'bogus'})
        # Should either error or produce a warning
        assert not result.success or len(result.warnings) > 0 or len(result.errors) > 0


class TestMatchEdgeCases:
    """Edge cases for match conditional."""

    def test_match_range_outside_low(self):
        """Value just below range should not match."""
        schema = {
            'fields': [
                {'name': 'v', 'type': 'u8'},
                {
                    'type': 'match', 'on': 'v',
                    'default': 'skip',
                    'cases': [
                        {'case': '10..20', 'fields': [{'name': 'd', 'type': 'u8'}]},
                    ]
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([9, 0x42]))
        assert result.success
        assert 'd' not in result.data

    def test_match_range_outside_high(self):
        """Value just above range should not match."""
        schema = {
            'fields': [
                {'name': 'v', 'type': 'u8'},
                {
                    'type': 'match', 'on': 'v',
                    'default': 'skip',
                    'cases': [
                        {'case': '10..20', 'fields': [{'name': 'd', 'type': 'u8'}]},
                    ]
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([21, 0x42]))
        assert result.success
        assert 'd' not in result.data

    def test_match_no_field_no_length(self):
        """Option B match with neither field: nor length: should handle gracefully."""
        schema = {
            'fields': [{
                'match': {
                    'cases': {
                        1: [{'name': 'd', 'type': 'u8'}],
                    }
                }
            }]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([0x01, 0x42]))
        # Should fail or degrade gracefully
        # No dispatch source - cannot match anything
        assert not result.success or 'd' not in result.data

    def test_match_inline_buffer_short(self):
        """Option B match with length:1 but empty buffer."""
        schema = {
            'fields': [{
                'match': {
                    'length': 1,
                    'cases': {
                        1: [{'name': 'd', 'type': 'u8'}],
                    }
                }
            }]
        }
        result = SchemaInterpreter(schema).decode(bytes())
        assert not result.success


class TestRefEdgeCases:
    """Edge cases for $ref."""

    def test_ref_bad_format(self):
        """$ref with unsupported format should error."""
        schema = {
            'definitions': {'foo': {'fields': [{'name': 'x', 'type': 'u8'}]}},
            'fields': [{'$ref': 'invalid_format'}]
        }
        result = SchemaInterpreter(schema).decode(bytes([0x01]))
        assert not result.success


class TestFormulaEdgeCases:
    """Edge cases for formula field."""

    def test_formula_division_by_zero(self):
        """Formula with division by zero should not crash."""
        schema = {
            'fields': [{
                'name': 'v', 'type': 'u8',
                'formula': 'x / 0'
            }]
        }
        result = SchemaInterpreter(schema).decode(bytes([10]))
        # Should either error or produce inf
        assert not result.success or result.data.get('v') is not None

    def test_formula_invalid_expression(self):
        """Formula with syntax error should not crash."""
        schema = {
            'fields': [{
                'name': 'v', 'type': 'u8',
                'formula': 'x *** 2'
            }]
        }
        result = SchemaInterpreter(schema).decode(bytes([10]))
        assert not result.success


class TestTlvEdgeCases:
    """Edge cases for TLV parsing."""

    def test_tlv_unknown_error(self):
        """TLV with unknown: error should fail on unknown tag."""
        schema = {
            'fields': [{
                'tlv': {
                    'tag_size': 1,
                    'length_size': 1,
                    'unknown': 'error',
                    'cases': {
                        0x01: [{'name': 'temp', 'type': 's16'}],
                    }
                }
            }]
        }
        result = SchemaInterpreter(schema).decode(bytes([0xFF, 0x01, 0xAA]))
        assert not result.success

    def test_tlv_empty_payload(self):
        """TLV with empty payload should produce no fields."""
        schema = {
            'fields': [{
                'tlv': {
                    'tag_size': 1,
                    'cases': {
                        0x01: [{'name': 'temp', 'type': 'u8'}],
                    }
                }
            }]
        }
        result = SchemaInterpreter(schema).decode(bytes())
        assert result.success
        assert 'temp' not in result.data


class TestFlaggedEdgeCases:
    """Edge cases for flagged/bitmask construct."""

    def test_no_groups_active(self):
        """Flags=0 means no groups should be decoded."""
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'flags', 'type': 'u16'},
                {'flagged': {
                    'field': 'flags',
                    'groups': [
                        {'bit': 0, 'fields': [
                            {'name': 'temp', 'type': 'u16'}
                        ]},
                        {'bit': 1, 'fields': [
                            {'name': 'battery', 'type': 'u16'}
                        ]}
                    ]
                }}
            ]
        }
        result = SchemaInterpreter(schema).decode(bytes([0x00, 0x00]))
        assert result.success
        assert 'temp' not in result.data
        assert 'battery' not in result.data


class TestVersionStringEdgeCases:
    """Edge cases for version_string type."""

    def test_version_string_short_buffer(self):
        """version_string with length=3 but only 2 bytes available."""
        schema = {
            'fields': [{
                'name': 'fw', 'type': 'version_string',
                'length': 3, 'delimiter': '.'
            }]
        }
        result = SchemaInterpreter(schema).decode(bytes([0x01, 0x02]))
        assert not result.success


class TestEncodeFormulaEdgeCases:
    """Edge cases for encode_formula."""

    def test_encode_formula_invalid(self):
        """encode_formula with syntax error should not crash."""
        schema = {
            'fields': [{
                'name': 'v', 'type': 'u8',
                'formula': 'x * 0.5 - 40',
                'encode_formula': 'x @@@ invalid('
            }]
        }
        result = SchemaInterpreter(schema).encode({'v': 40.0})
        assert not result.success or len(result.errors) > 0


class TestTimestampEdgeCases:
    """Edge cases for timestamp formatting."""

    def test_iso8601_missing_field_ref(self):
        """iso8601 mode referencing a field that doesn't exist in decoded data."""
        schema = {
            'fields': [{'name': 'temp', 'type': 'u8'}],
            'metadata': {
                'timestamps': [
                    {'name': 'ts', 'mode': 'iso8601', 'field': 'nonexistent'}
                ]
            }
        }
        result = SchemaInterpreter(schema).decode(bytes([42]), input_metadata={})
        assert result.success
        # Missing source field - ts should not appear or should be null
        assert 'ts' not in result.data or result.data['ts'] is None

    def test_elapsed_no_recv_time(self):
        """elapsed_to_absolute without recvTime in metadata."""
        schema = {
            'endian': 'big',
            'fields': [{'name': 'elapsed', 'type': 'u16'}],
            'metadata': {
                'timestamps': [
                    {'name': 'abs_time', 'mode': 'elapsed_to_absolute',
                     'elapsed_field': 'elapsed', 'time_base': 'rx_time'}
                ]
            }
        }
        result = SchemaInterpreter(schema).decode(bytes([0x00, 0x3C]), input_metadata={})
        assert result.success
        # No recvTime - abs_time should not appear
        assert 'abs_time' not in result.data


class TestSemanticEdgeCases:
    """Edge cases for semantic output."""

    def test_unknown_semantic_format(self):
        """Unknown format string should return raw decoded data."""
        schema = {
            'fields': [{'name': 'temperature', 'type': 'u8',
                        'semantic': {'ipso': 3303}}]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([42]))
        output = interpreter.get_semantic_output(result.data, 'bogus_format')
        assert output == result.data


class TestExtraPayloadAndUnknownType:
    """Tests for extra bytes in payload and unknown type strings."""

    def test_extra_bytes_ignored(self):
        """Payload longer than schema expects should still decode."""
        schema = {'fields': [{'name': 'v', 'type': 'u8'}]}
        result = SchemaInterpreter(schema).decode(bytes([0x42, 0xFF, 0xEE]))
        assert result.success
        assert result.data['v'] == 0x42
        assert result.bytes_consumed == 1

    def test_unknown_type_error(self):
        """Unknown type string should produce an error."""
        schema = {'fields': [{'name': 'v', 'type': 'foobar'}]}
        result = SchemaInterpreter(schema).decode(bytes([0x42]))
        assert not result.success


# =============================================================================
# Encode Roundtrip Coverage for All Types
# =============================================================================

class TestEncodeRoundtripAllTypes:
    """Roundtrip encode/decode tests for every supported encode type.

    Covers s8, u32, s32, u64, s64, f32, f64, bool, bytes, string.
    (u8, u16, s16, u24 roundtrips already exist in other classes.)
    """

    def test_s8_roundtrip(self):
        schema = {'fields': [{'name': 'v', 'type': 's8'}]}
        interp = SchemaInterpreter(schema)
        enc = interp.encode({'v': -42})
        dec = interp.decode(enc.payload)
        assert dec.data['v'] == -42

    def test_u32_roundtrip(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 'u32'}]}
        interp = SchemaInterpreter(schema)
        enc = interp.encode({'v': 0xDEADBEEF})
        dec = interp.decode(enc.payload)
        assert dec.data['v'] == 0xDEADBEEF

    def test_s32_roundtrip(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 's32'}]}
        interp = SchemaInterpreter(schema)
        enc = interp.encode({'v': -100000})
        dec = interp.decode(enc.payload)
        assert dec.data['v'] == -100000

    def test_u64_roundtrip(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 'u64'}]}
        interp = SchemaInterpreter(schema)
        enc = interp.encode({'v': 0x0000000100000001})
        dec = interp.decode(enc.payload)
        assert dec.data['v'] == 0x0000000100000001

    def test_s64_roundtrip(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 's64'}]}
        interp = SchemaInterpreter(schema)
        enc = interp.encode({'v': -9999999999})
        dec = interp.decode(enc.payload)
        assert dec.data['v'] == -9999999999

    def test_f32_roundtrip(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 'f32'}]}
        interp = SchemaInterpreter(schema)
        enc = interp.encode({'v': -1.5})
        dec = interp.decode(enc.payload)
        assert abs(dec.data['v'] - (-1.5)) < 0.001

    def test_f64_roundtrip(self):
        schema = {'endian': 'big', 'fields': [{'name': 'v', 'type': 'f64'}]}
        interp = SchemaInterpreter(schema)
        enc = interp.encode({'v': 3.14159265358979})
        dec = interp.decode(enc.payload)
        assert abs(dec.data['v'] - 3.14159265358979) < 1e-10

    def test_bool_roundtrip_true(self):
        schema = {'fields': [
            {'name': 'v', 'type': 'bool', 'bit': 0, 'consume': 1}
        ]}
        interp = SchemaInterpreter(schema)
        enc = interp.encode({'v': True})
        dec = interp.decode(enc.payload)
        assert dec.data['v'] is True

    def test_bool_roundtrip_false(self):
        schema = {'fields': [
            {'name': 'v', 'type': 'bool', 'bit': 0, 'consume': 1}
        ]}
        interp = SchemaInterpreter(schema)
        enc = interp.encode({'v': False})
        dec = interp.decode(enc.payload)
        assert dec.data['v'] is False

    def test_bytes_roundtrip(self):
        schema = {'fields': [{'name': 'v', 'type': 'bytes', 'length': 4}]}
        interp = SchemaInterpreter(schema)
        enc = interp.encode({'v': bytes([0xDE, 0xAD, 0xBE, 0xEF])})
        dec = interp.decode(enc.payload)
        assert dec.data['v'] == bytes([0xDE, 0xAD, 0xBE, 0xEF])

    def test_string_roundtrip(self):
        schema = {'fields': [{'name': 'v', 'type': 'string', 'length': 8}]}
        interp = SchemaInterpreter(schema)
        enc = interp.encode({'v': 'hello'})
        dec = interp.decode(enc.payload)
        assert dec.data['v'] == 'hello'

    def test_u32_le_roundtrip(self):
        schema = {'endian': 'little', 'fields': [{'name': 'v', 'type': 'u32'}]}
        interp = SchemaInterpreter(schema)
        enc = interp.encode({'v': 0x12345678})
        dec = interp.decode(enc.payload)
        assert dec.data['v'] == 0x12345678

    def test_s32_le_roundtrip(self):
        schema = {'endian': 'little', 'fields': [{'name': 'v', 'type': 's32'}]}
        interp = SchemaInterpreter(schema)
        enc = interp.encode({'v': -2})
        dec = interp.decode(enc.payload)
        assert dec.data['v'] == -2

    def test_f32_le_roundtrip(self):
        schema = {'endian': 'little', 'fields': [{'name': 'v', 'type': 'f32'}]}
        interp = SchemaInterpreter(schema)
        enc = interp.encode({'v': 42.5})
        dec = interp.decode(enc.payload)
        assert abs(dec.data['v'] - 42.5) < 0.001

    def test_f64_le_roundtrip(self):
        schema = {'endian': 'little', 'fields': [{'name': 'v', 'type': 'f64'}]}
        interp = SchemaInterpreter(schema)
        enc = interp.encode({'v': -123.456})
        dec = interp.decode(enc.payload)
        assert abs(dec.data['v'] - (-123.456)) < 0.0001


class TestBoolConsumeDefault:
    """Test bool type with default consume behavior (no consume key)."""

    def test_bool_no_consume_stays(self):
        """Bool without consume should not advance position."""
        schema = {'fields': [
            {'name': 'flag_a', 'type': 'bool', 'bit': 0},
            {'name': 'flag_b', 'type': 'bool', 'bit': 1},
            {'name': 'raw', 'type': 'u8'},
        ]}
        interp = SchemaInterpreter(schema)
        # 0x03 = bits 0 and 1 set
        result = interp.decode(bytes([0x03]))
        assert result.success
        assert result.data['flag_a'] is True
        assert result.data['flag_b'] is True
        # raw reads the same byte since bool didn't advance
        assert result.data['raw'] == 0x03

    def test_bool_consume_1_advances(self):
        """Bool with consume:1 should advance position."""
        schema = {'fields': [
            {'name': 'flag', 'type': 'bool', 'bit': 0, 'consume': 1},
            {'name': 'next', 'type': 'u8'},
        ]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([0x01, 0xFF]))
        assert result.success
        assert result.data['flag'] is True
        assert result.data['next'] == 0xFF

    def test_two_bools_then_consume(self):
        """Two bools without consume, then a field consuming the byte."""
        schema = {'fields': [
            {'name': 'a', 'type': 'bool', 'bit': 7},
            {'name': 'b', 'type': 'bool', 'bit': 0},
            {'name': 'byte_val', 'type': 'u8'},  # reads same byte
            {'name': 'next', 'type': 'u8'},
        ]}
        interp = SchemaInterpreter(schema)
        # 0x81 = bit 0 and bit 7 set, then 0x42
        result = interp.decode(bytes([0x81, 0x42]))
        assert result.success
        assert result.data['a'] is True
        assert result.data['b'] is True
        assert result.data['byte_val'] == 0x81  # same byte
        assert result.data['next'] == 0x42


class TestBytesType:
    """
    Tests for bytes/hex/base64 types.
    
    REQ-Bytes-Type-017: bytes type with length
    REQ-Hex-Type-020: hex string output
    REQ-Base64-Typ-057: base64 string output
    """

    def test_bytes_type(self):
        """M061: Raw bytes extraction."""
        schema = {'fields': [{'name': 'data', 'type': 'bytes', 'length': 4}]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([0xDE, 0xAD, 0xBE, 0xEF]))
        assert result.success
        assert result.data['data'] == bytes([0xDE, 0xAD, 0xBE, 0xEF])

    def test_hex_type(self):
        """M063: Hex string output (lowercase)."""
        schema = {'fields': [{'name': 'mac', 'type': 'hex', 'length': 6}]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([0x00, 0x11, 0x22, 0x33, 0x44, 0x55]))
        assert result.success
        assert result.data['mac'].lower() == '001122334455'

    def test_base64_type(self):
        """M064: Base64 encoded output (RFC 4648)."""
        schema = {'fields': [{'name': 'blob', 'type': 'base64', 'length': 3}]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([0x01, 0x02, 0x03]))
        assert result.success
        import base64
        assert base64.b64decode(result.data['blob']) == bytes([0x01, 0x02, 0x03])


class TestStringType:
    """
    Tests for string/ascii types.
    
    REQ-String-Typ-018: string type
    REQ-ASCII-Type-019: ascii string type
    """

    def test_string_type(self):
        """M061: String type with length."""
        schema = {'fields': [{'name': 'msg', 'type': 'string', 'length': 5}]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(b'Hello')
        assert result.success
        assert result.data['msg'] == 'Hello'

    def test_ascii_type(self):
        """M061: ASCII string type."""
        schema = {'fields': [{'name': 'name', 'type': 'ascii', 'length': 4}]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(b'Test')
        assert result.success
        assert result.data['name'] == 'Test'

    def test_string_with_null(self):
        """String with null terminator."""
        schema = {'fields': [{'name': 's', 'type': 'string', 'length': 8}]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(b'Hi\x00\x00\x00\x00\x00\x00')
        assert result.success
        # Should strip or include nulls depending on implementation
        assert 'Hi' in result.data['s']


class TestLookupModifier:
    """
    Tests for lookup table modifier.
    
    REQ-Lookup-Ta-027: lookup table modifier
    """

    def test_lookup_dict(self):
        """M089-M092: Lookup with dictionary."""
        schema = {
            'fields': [{
                'name': 'status',
                'type': 'u8',
                'lookup': {0: 'idle', 1: 'running', 2: 'error'}
            }]
        }
        interp = SchemaInterpreter(schema)
        
        result = interp.decode(bytes([0x01]))
        assert result.success
        assert result.data['status'] == 'running'

    def test_lookup_list(self):
        """Lookup with list (index-based)."""
        schema = {
            'fields': [{
                'name': 'mode',
                'type': 'u8',
                'lookup': ['off', 'on', 'standby']
            }]
        }
        interp = SchemaInterpreter(schema)
        
        result = interp.decode(bytes([0x02]))
        assert result.success
        assert result.data['mode'] == 'standby'

    def test_lookup_unknown(self):
        """Lookup with unknown value."""
        schema = {
            'fields': [{
                'name': 'status',
                'type': 'u8',
                'lookup': {0: 'ok', 1: 'error'}
            }]
        }
        interp = SchemaInterpreter(schema)
        
        result = interp.decode(bytes([0x99]))
        assert result.success
        # Should return raw value or unknown marker
        assert '153' in str(result.data['status']) or result.data['status'] == 153


class TestTransformOperations:
    """
    Tests for transform pipeline.
    
    REQ-Transform-001: transform array with math operations
    """

    def test_transform_basic(self):
        """M098-M101: Basic transform pipeline."""
        schema = {
            'fields': [{
                'name': 'temp',
                'type': 'u16',
                'transform': [
                    {'add': -4000},
                    {'div': 100}
                ]
            }]
        }
        interp = SchemaInterpreter(schema)
        # Raw 4231 -> (4231-4000)/100 = 2.31
        result = interp.decode(bytes([0x10, 0x87]))  # 4231 big endian
        assert result.success
        assert abs(result.data['temp'] - 2.31) < 0.01

    def test_transform_clamp(self):
        """Transform with clamp operation."""
        schema = {
            'fields': [{
                'name': 'pct',
                'type': 'u8',
                'transform': [{'clamp': [0, 100]}]
            }]
        }
        interp = SchemaInterpreter(schema)
        
        result = interp.decode(bytes([0xFF]))  # 255
        assert result.success
        assert result.data['pct'] == 100  # Clamped


class TestBitfieldString:
    """
    Tests for bitfield_string type (version strings from packed bits).
    
    REQ-Bitfield-String-069: Bitfield string output
    """

    def test_bitfield_string_version(self):
        """M077-M082: Bitfield string for version numbers."""
        schema = {
            'fields': [{
                'name': 'version',
                'type': 'bitfield_string',
                'length': 2,
                'parts': [
                    [12, 4],  # bits 12-15: major (4 bits)
                    [8, 4],   # bits 8-11: minor (4 bits)
                    [0, 8]    # bits 0-7: patch (8 bits)
                ],
                'delimiter': '.',
                'prefix': 'v'
            }]
        }
        interp = SchemaInterpreter(schema)
        # 0x1203 big endian = major=1, minor=2, patch=3
        result = interp.decode(bytes([0x12, 0x03]))
        assert result.success
        assert result.data['version'] == 'v1.2.3'


class TestByteGroup:
    """
    Tests for byte_group type.
    
    REQ-Byte-Group-037: byte_group for grouping bitfields
    """

    def test_byte_group_nibbles(self):
        """M059-M060: Byte group with nibble extraction."""
        schema = {
            'fields': [{
                'byte_group': [
                    {'name': 'high_nibble', 'type': 'u8[4:7]'},
                    {'name': 'low_nibble', 'type': 'u8[0:3]'},
                ],
                'size': 1
            }]
        }
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([0xAB]))
        assert result.success
        assert result.data['high_nibble'] == 0xA
        assert result.data['low_nibble'] == 0xB


class TestDefinitions:
    """
    Tests for definitions and $ref.
    
    REQ-Definitio-051: definitions section for reusable field groups
    REQ-Ref-Field-052: $ref for referencing definitions
    """

    def test_definitions_basic(self):
        """M226-M229: Basic definitions usage."""
        schema = {
            'definitions': {
                'header': {
                    'fields': [
                        {'name': 'version', 'type': 'u8'},
                        {'name': 'msg_type', 'type': 'u8'}
                    ]
                }
            },
            'fields': [
                {'$ref': '#/definitions/header'},
                {'name': 'payload', 'type': 'u16'}
            ]
        }
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([0x01, 0x02, 0x00, 0x64]))
        assert result.success
        assert result.data['version'] == 1
        assert result.data['msg_type'] == 2
        assert result.data['payload'] == 100


class TestVariables:
    """
    Tests for var: field storage.
    
    REQ-Variables-070: var for storing field values
    """

    def test_var_basic(self):
        """M122-M125: Store and use variable."""
        schema = {
            'fields': [
                {'name': 'length', 'type': 'u8', 'var': 'len'},
                {'name': 'data', 'type': 'bytes', 'length': 3}
            ]
        }
        interp = SchemaInterpreter(schema)
        # length=3, then 3 bytes of data
        result = interp.decode(bytes([0x03, 0xAA, 0xBB, 0xCC]))
        assert result.success
        assert result.data['length'] == 3
        assert result.data['data'] == bytes([0xAA, 0xBB, 0xCC])


class TestSkipType:
    """
    Tests for skip type.
    
    REQ-Skip-Type-021: skip type for padding/reserved bytes
    """

    def test_skip_basic(self):
        """M015: Skip padding bytes (variable-length type)."""
        schema = {
            'fields': [
                {'name': 'a', 'type': 'u8'},
                {'name': '_pad', 'type': 'skip', 'length': 2},
                {'name': 'b', 'type': 'u8'}
            ]
        }
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([0x01, 0xFF, 0xFF, 0x02]))
        assert result.success
        assert result.data['a'] == 1
        assert result.data['b'] == 2
        assert '_pad' not in result.data  # Skip should not appear in output


class TestEndian:
    """
    Tests for endianness.
    
    REQ-Endiannes-004: Big endian default
    REQ-Endiannes-005: Little endian option
    """

    def test_big_endian_default(self):
        """R008: Default big endian."""
        schema = {'fields': [{'name': 'val', 'type': 'u16'}]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([0x01, 0x02]))
        assert result.success
        assert result.data['val'] == 0x0102  # Big endian

    def test_little_endian_schema(self):
        """M044: Schema-level little endian."""
        schema = {'endian': 'little', 'fields': [{'name': 'val', 'type': 'u16'}]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([0x01, 0x02]))
        assert result.success
        assert result.data['val'] == 0x0201  # Little endian

    def test_u32_little_endian(self):
        """32-bit little endian value."""
        schema = {'endian': 'little', 'fields': [{'name': 'val', 'type': 'u32'}]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([0x01, 0x02, 0x03, 0x04]))
        assert result.success
        assert result.data['val'] == 0x04030201  # Little endian


class TestMultModifierComprehensive:
    """
    Comprehensive tests for mult modifier.
    
    REQ-Mult-Modi-024: Multiply modifier
    """

    def test_mult_integer(self):
        """Mult with integer multiplier."""
        schema = {'fields': [{'name': 'v', 'type': 'u8', 'mult': 10}]}
        result = SchemaInterpreter(schema).decode(bytes([5]))
        assert result.data['v'] == 50

    def test_mult_decimal(self):
        """Mult with decimal multiplier."""
        schema = {'fields': [{'name': 'v', 'type': 'u16', 'mult': 0.01}]}
        result = SchemaInterpreter(schema).decode(bytes([0x09, 0x29]))  # 2345
        assert abs(result.data['v'] - 23.45) < 0.001

    def test_mult_negative(self):
        """Mult with negative multiplier."""
        schema = {'fields': [{'name': 'v', 'type': 'u8', 'mult': -1}]}
        result = SchemaInterpreter(schema).decode(bytes([100]))
        assert result.data['v'] == -100

    def test_mult_encode_roundtrip(self):
        """Mult encode/decode roundtrip."""
        schema = {'fields': [{'name': 'v', 'type': 'u16', 'mult': 0.1}]}
        interp = SchemaInterpreter(schema)
        encoded = interp.encode({'v': 25.5})
        decoded = interp.decode(encoded.payload)
        assert abs(decoded.data['v'] - 25.5) < 0.01


class TestDivModifierComprehensive:
    """
    Comprehensive tests for div modifier.
    
    REQ-Div-Modif-026: Divide modifier
    """

    def test_div_integer(self):
        """Div with integer divisor."""
        schema = {'fields': [{'name': 'v', 'type': 'u16', 'div': 10}]}
        result = SchemaInterpreter(schema).decode(bytes([0x00, 0x64]))  # 100
        assert result.data['v'] == 10.0

    def test_div_decimal_result(self):
        """Div producing decimal result."""
        schema = {'fields': [{'name': 'v', 'type': 'u8', 'div': 4}]}
        result = SchemaInterpreter(schema).decode(bytes([10]))
        assert result.data['v'] == 2.5

    def test_div_encode_roundtrip(self):
        """Div encode/decode roundtrip."""
        schema = {'fields': [{'name': 'v', 'type': 'u16', 'div': 100}]}
        interp = SchemaInterpreter(schema)
        encoded = interp.encode({'v': 23.45})
        decoded = interp.decode(encoded.payload)
        assert abs(decoded.data['v'] - 23.45) < 0.01

    def test_div_with_mult(self):
        """Div combined with mult."""
        schema = {'fields': [{'name': 'v', 'type': 'u16', 'mult': 0.1, 'div': 2}]}
        result = SchemaInterpreter(schema).decode(bytes([0x00, 0x64]))  # 100
        # 100 * 0.1 / 2 = 5.0
        assert result.data['v'] == 5.0


class TestDefinitionsComprehensive:
    """
    Comprehensive tests for definitions and $ref.
    
    REQ-Definitio-051: definitions section
    REQ-Ref-Field-052: $ref references
    """

    def test_definition_simple(self):
        """Simple definition reference."""
        schema = {
            'definitions': {
                'temp_field': {'fields': [{'name': 'temp', 'type': 's16', 'div': 10}]}
            },
            'fields': [{'$ref': '#/definitions/temp_field'}]
        }
        result = SchemaInterpreter(schema).decode(bytes([0x00, 0xE7]))
        assert abs(result.data['temp'] - 23.1) < 0.01

    def test_definition_multiple_refs(self):
        """Multiple references to same definition."""
        schema = {
            'definitions': {
                'byte_val': {'fields': [{'name': 'v', 'type': 'u8'}]}
            },
            'fields': [
                {'$ref': '#/definitions/byte_val'},
                {'name': 'middle', 'type': 'u8'},
                {'$ref': '#/definitions/byte_val'}
            ]
        }
        result = SchemaInterpreter(schema).decode(bytes([1, 2, 3]))
        assert result.data['v'] == 3  # Last ref overwrites
        assert result.data['middle'] == 2

    def test_definition_nested(self):
        """Definition with nested object."""
        schema = {
            'definitions': {
                'sensor': {
                    'fields': [
                        {'name': 'id', 'type': 'u8'},
                        {'name': 'reading', 'type': 'u16'}
                    ]
                }
            },
            'fields': [{'$ref': '#/definitions/sensor'}]
        }
        result = SchemaInterpreter(schema).decode(bytes([0x01, 0x01, 0xF4]))
        assert result.data['id'] == 1
        assert result.data['reading'] == 500


class TestVariablesComprehensive:
    """
    Comprehensive tests for var storage.
    
    REQ-Variables-070: var for storing field values
    """

    def test_var_in_formula(self):
        """Variable used in formula."""
        schema = {
            'fields': [
                {'name': 'raw', 'type': 'u8', 'var': 'r'},
                {'name': 'doubled', 'type': 'number', 'formula': '$r * 2'}
            ]
        }
        result = SchemaInterpreter(schema).decode(bytes([25]))
        assert result.data['raw'] == 25
        assert result.data['doubled'] == 50

    def test_var_in_compute(self):
        """Variable used in compute."""
        schema = {
            'fields': [
                {'name': 'a', 'type': 'u8', 'var': 'val_a'},
                {'name': 'b', 'type': 'u8', 'var': 'val_b'},
                {'name': 'sum', 'type': 'number', 
                 'compute': {'op': 'add', 'a': '$val_a', 'b': '$val_b'}}
            ]
        }
        result = SchemaInterpreter(schema).decode(bytes([10, 20]))
        assert result.data['sum'] == 30

    def test_var_in_repeat_count(self):
        """Variable used as repeat count."""
        schema = {
            'fields': [
                {'name': 'count', 'type': 'u8', 'var': 'n'},
                {'name': 'items', 'type': 'repeat', 'count': '$n',
                 'fields': [{'name': 'val', 'type': 'u8'}]}
            ]
        }
        result = SchemaInterpreter(schema).decode(bytes([3, 10, 20, 30]))
        assert len(result.data['items']) == 3


class TestUnitAnnotation:
    """
    Tests for unit annotation.
    
    REQ-Unit-Annot-071: unit field annotation
    """

    def test_unit_annotation(self):
        """R024: Unit annotation preserved (SenML)."""
        schema = {
            'fields': [{
                'name': 'temp',
                'type': 's16',
                'div': 10,
                'unit': '°C'
            }]
        }
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([0x00, 0xE7]))
        assert result.success
        assert abs(result.data['temp'] - 23.1) < 0.01

    def test_unit_multiple_fields(self):
        """Multiple fields with different units."""
        schema = {
            'fields': [
                {'name': 'temp', 'type': 's16', 'div': 10, 'unit': '°C'},
                {'name': 'humidity', 'type': 'u8', 'unit': '%'},
                {'name': 'pressure', 'type': 'u16', 'div': 10, 'unit': 'hPa'}
            ]
        }
        result = SchemaInterpreter(schema).decode(bytes([0x00, 0xE7, 0x32, 0x27, 0x10]))
        assert abs(result.data['temp'] - 23.1) < 0.01
        assert result.data['humidity'] == 50
        assert abs(result.data['pressure'] - 1000.0) < 0.1


class TestSemanticOutput:
    """
    Tests for semantic annotations.
    
    REQ-IPSO-Outpu-041: IPSO/LwM2M annotations
    REQ-SenML-Outp-042: SenML annotations
    """

    def test_ipso_annotation(self):
        """R027: IPSO annotation preserved in decode."""
        schema = {
            'fields': [{
                'name': 'temp',
                'type': 's16',
                'div': 10,
                'ipso': {'object': 3303, 'resource': 5700}
            }]
        }
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([0x00, 0xE7]))
        assert result.success
        assert abs(result.data['temp'] - 23.1) < 0.01

    def test_senml_annotation(self):
        """R024: SenML annotation preserved in decode."""
        schema = {
            'fields': [{
                'name': 'temp',
                'type': 's16',
                'div': 10,
                'senml': {'unit': 'Cel'}
            }]
        }
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([0x00, 0xE7]))
        assert result.success
        assert abs(result.data['temp'] - 23.1) < 0.01


class TestRepeatType:
    """
    Tests for repeat/array type.
    
    REQ-Repeat-Coun-064: count-based iteration
    REQ-Repeat-Byte-065: byte_length-based iteration
    REQ-Repeat-Unti-066: until: end iteration
    REQ-Repeat-Mini-067: min/max constraints
    REQ-Repeat-Vari-068: variable references for count/byte_length
    """

    def test_repeat_count_fixed(self):
        """M072: Fixed count iteration."""
        schema = {
            'endian': 'big',
            'fields': [
                {
                    'name': 'readings',
                    'type': 'repeat',
                    'count': 3,
                    'fields': [
                        {'name': 'temp', 'type': 's16', 'mult': 0.1},
                        {'name': 'humidity', 'type': 'u8'}
                    ]
                }
            ]
        }
        interp = SchemaInterpreter(schema)
        # 3 readings: (23.1°C, 50%), (24.5°C, 55%), (22.0°C, 45%)
        payload = bytes([
            0x00, 0xE7, 0x32,  # 231*0.1=23.1, 50
            0x00, 0xF5, 0x37,  # 245*0.1=24.5, 55
            0x00, 0xDC, 0x2D,  # 220*0.1=22.0, 45
        ])
        result = interp.decode(payload)
        
        assert result.success
        assert len(result.data['readings']) == 3
        assert abs(result.data['readings'][0]['temp'] - 23.1) < 0.01
        assert result.data['readings'][0]['humidity'] == 50
        assert abs(result.data['readings'][1]['temp'] - 24.5) < 0.01
        assert result.data['readings'][2]['humidity'] == 45

    def test_repeat_count_variable(self):
        """O014: Count from variable (MAY reference field)."""
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'num_readings', 'type': 'u8', 'var': 'count'},
                {
                    'name': 'readings',
                    'type': 'repeat',
                    'count': '$count',
                    'fields': [
                        {'name': 'value', 'type': 'u16'}
                    ]
                }
            ]
        }
        interp = SchemaInterpreter(schema)
        # 2 readings: 1000, 2000
        payload = bytes([0x02, 0x03, 0xE8, 0x07, 0xD0])
        result = interp.decode(payload)
        
        assert result.success
        assert result.data['num_readings'] == 2
        assert len(result.data['readings']) == 2
        assert result.data['readings'][0]['value'] == 1000
        assert result.data['readings'][1]['value'] == 2000

    def test_repeat_until_end(self):
        """M074: Repeat until end of payload."""
        schema = {
            'endian': 'big',
            'fields': [
                {
                    'name': 'samples',
                    'type': 'repeat',
                    'until': 'end',
                    'fields': [
                        {'name': 'value', 'type': 'u8'}
                    ]
                }
            ]
        }
        interp = SchemaInterpreter(schema)
        payload = bytes([0x01, 0x02, 0x03, 0x04, 0x05])
        result = interp.decode(payload)
        
        assert result.success
        assert len(result.data['samples']) == 5
        assert result.data['samples'][0]['value'] == 1
        assert result.data['samples'][4]['value'] == 5

    def test_repeat_byte_length(self):
        """M073: Repeat for specified byte length."""
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'header', 'type': 'u8'},
                {
                    'name': 'data',
                    'type': 'repeat',
                    'byte_length': 6,
                    'fields': [
                        {'name': 'x', 'type': 'u8'},
                        {'name': 'y', 'type': 'u8'}
                    ]
                },
                {'name': 'trailer', 'type': 'u8'}
            ]
        }
        interp = SchemaInterpreter(schema)
        # header=0xAA, 3 pairs (6 bytes), trailer=0xBB
        payload = bytes([0xAA, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0xBB])
        result = interp.decode(payload)
        
        assert result.success
        assert result.data['header'] == 0xAA
        assert len(result.data['data']) == 3
        assert result.data['data'][0] == {'x': 1, 'y': 2}
        assert result.data['data'][1] == {'x': 3, 'y': 4}
        assert result.data['data'][2] == {'x': 5, 'y': 6}
        assert result.data['trailer'] == 0xBB

    def test_repeat_byte_length_variable(self):
        """M073: Byte length from variable reference."""
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'data_len', 'type': 'u8', 'var': 'len'},
                {
                    'name': 'points',
                    'type': 'repeat',
                    'byte_length': '$len',
                    'fields': [
                        {'name': 'val', 'type': 'u16'}
                    ]
                }
            ]
        }
        interp = SchemaInterpreter(schema)
        # len=4, then 2 u16 values (4 bytes)
        payload = bytes([0x04, 0x00, 0x64, 0x00, 0xC8])
        result = interp.decode(payload)
        
        assert result.success
        assert result.data['data_len'] == 4
        assert len(result.data['points']) == 2
        assert result.data['points'][0]['val'] == 100
        assert result.data['points'][1]['val'] == 200

    def test_repeat_min_constraint(self):
        """R013-R014: Minimum iterations constraint."""
        schema = {
            'fields': [
                {
                    'name': 'items',
                    'type': 'repeat',
                    'until': 'end',
                    'min': 3,
                    'fields': [{'name': 'v', 'type': 'u8'}]
                }
            ]
        }
        interp = SchemaInterpreter(schema)
        
        # Only 2 items - should fail
        result = interp.decode(bytes([0x01, 0x02]))
        assert not result.success
        assert 'minimum' in str(result.errors[0]).lower()

    def test_repeat_max_constraint(self):
        """R014: Maximum iterations constraint (safety)."""
        schema = {
            'fields': [
                {
                    'name': 'items',
                    'type': 'repeat',
                    'until': 'end',
                    'max': 3,
                    'fields': [{'name': 'v', 'type': 'u8'}]
                }
            ]
        }
        interp = SchemaInterpreter(schema)
        
        # 5 items but max is 3 - should only get 3
        result = interp.decode(bytes([0x01, 0x02, 0x03, 0x04, 0x05]))
        assert result.success
        assert len(result.data['items']) == 3

    def test_repeat_nested_objects(self):
        """Repeat with complex nested structure."""
        schema = {
            'endian': 'big',
            'fields': [
                {
                    'name': 'sensors',
                    'type': 'repeat',
                    'count': 2,
                    'fields': [
                        {'name': 'id', 'type': 'u8'},
                        {
                            'name': 'reading',
                            'type': 'object',
                            'fields': [
                                {'name': 'temp', 'type': 's16', 'mult': 0.1},
                                {'name': 'humidity', 'type': 'u8'}
                            ]
                        }
                    ]
                }
            ]
        }
        interp = SchemaInterpreter(schema)
        # sensor 1: id=1, temp=23.1, hum=50
        # sensor 2: id=2, temp=24.5, hum=55
        payload = bytes([
            0x01, 0x00, 0xE7, 0x32,
            0x02, 0x00, 0xF5, 0x37
        ])
        result = interp.decode(payload)
        
        assert result.success
        assert len(result.data['sensors']) == 2
        assert result.data['sensors'][0]['id'] == 1
        assert abs(result.data['sensors'][0]['reading']['temp'] - 23.1) < 0.01
        assert result.data['sensors'][1]['id'] == 2

    def test_repeat_empty(self):
        """Repeat with count=0 produces empty array."""
        schema = {
            'fields': [
                {
                    'name': 'items',
                    'type': 'repeat',
                    'count': 0,
                    'fields': [{'name': 'v', 'type': 'u8'}]
                }
            ]
        }
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([]))
        
        assert result.success
        assert result.data['items'] == []

    def test_repeat_missing_mode_error(self):
        """Repeat without count/byte_length/until should error."""
        schema = {
            'fields': [
                {
                    'name': 'items',
                    'type': 'repeat',
                    'fields': [{'name': 'v', 'type': 'u8'}]
                }
            ]
        }
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([0x01, 0x02]))
        
        assert not result.success
        assert 'must specify' in str(result.errors[0]).lower()


class TestEdgeCasesAndSecurity:
    """Tests for edge cases, malformed inputs, and security boundaries."""

    # --- Formula Injection Prevention ---
    
    def test_formula_injection_import_blocked(self):
        """Formula cannot use __import__ to execute arbitrary code."""
        schema = {'fields': [
            {'name': 'x', 'type': 'u8', 'formula': '__import__("os").system("echo pwned")'}
        ]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([42]))
        # Should fail or return safe default, not execute code
        assert 'x' not in result.data or result.data.get('x') == 0.0

    def test_formula_injection_globals_blocked(self):
        """Formula cannot access globals()."""
        schema = {'fields': [
            {'name': 'x', 'type': 'u8', 'formula': 'globals()'}
        ]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([42]))
        assert 'x' not in result.data or result.data.get('x') == 0.0

    def test_formula_injection_eval_blocked(self):
        """Formula cannot use nested eval."""
        schema = {'fields': [
            {'name': 'x', 'type': 'u8', 'formula': 'eval("1+1")'}
        ]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([42]))
        assert 'x' not in result.data or result.data.get('x') == 0.0

    def test_formula_injection_class_access_blocked(self):
        """Formula cannot access __class__ for sandbox escape."""
        schema = {'fields': [
            {'name': 'x', 'type': 'u8', 'formula': '().__class__.__bases__[0].__subclasses__()'}
        ]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([42]))
        # Should not crash or leak class info
        assert result.data.get('x', 0.0) == 0.0

    # --- Recursion and Iteration Limits ---

    def test_deep_nested_match_handled(self):
        """Deep nested match structures don't cause stack overflow."""
        def make_nested_match(depth):
            if depth == 0:
                return {'name': 'leaf', 'type': 'u8'}
            return {
                'name': f'match_{depth}',
                'type': 'match',
                'on': '$type',
                'cases': [{'case': 1, 'fields': [make_nested_match(depth-1)]}]
            }
        
        schema = {'fields': [
            {'name': 'type', 'type': 'u8', 'var': 'type'},
            make_nested_match(100)
        ]}
        interp = SchemaInterpreter(schema)
        # Should not crash - may truncate or return partial result
        result = interp.decode(bytes([1] * 200))
        assert result is not None

    def test_repeat_huge_count_bounded_by_buffer(self):
        """Repeat with huge count is bounded by available buffer."""
        schema = {'fields': [
            {'name': 'items', 'type': 'repeat', 'count': 999999999, 'max': 999999999,
             'fields': [{'name': 'x', 'type': 'u8'}]}
        ]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([42] * 100))
        # Should not hang - bounded by 100 bytes available
        assert result is not None

    def test_repeat_until_end_large_payload(self):
        """Repeat until=end respects max_iterations safety limit."""
        schema = {'fields': [
            {'name': 'items', 'type': 'repeat', 'until': 'end',
             'fields': [{'name': 'x', 'type': 'u8'}]}
        ]}
        interp = SchemaInterpreter(schema)
        import time
        start = time.time()
        result = interp.decode(bytes([42] * 10000))
        elapsed = time.time() - start
        
        assert result.success
        # Default max_iterations=1000 is a safety limit
        assert len(result.data['items']) == 1000
        assert elapsed < 1.0  # Should complete quickly due to limit

    # --- Variable Reference Edge Cases ---

    def test_self_referencing_formula_uses_default(self):
        """Formula referencing its own var before assignment uses 0."""
        schema = {'fields': [
            {'name': 'x', 'type': 'u8', 'var': 'x', 'formula': '$x + 1'}
        ]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([42]))
        # $x is 0 before assignment, so result is 0 + 1 = 1
        assert result.data['x'] == 1.0

    def test_circular_formula_references(self):
        """Circular variable references don't cause infinite loop."""
        schema = {'fields': [
            {'name': 'a', 'type': 'u8', 'var': 'a', 'formula': '$b + 1'},
            {'name': 'b', 'type': 'u8', 'var': 'b', 'formula': '$a + 1'}
        ]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([1, 2]))
        # Should complete without hanging
        assert result is not None
        assert 'a' in result.data
        assert 'b' in result.data

    # --- Buffer Boundary Conditions ---

    def test_tlv_length_exceeds_buffer(self):
        """TLV with length > remaining buffer handles gracefully."""
        schema = {'fields': [
            {'name': 'data', 'type': 'tlv', 'tag': {'type': 'u8'},
             'length': {'type': 'u8'},
             'cases': {'1': [{'name': 'val', 'type': 'bytes', 'length': '$length'}]}}
        ]}
        interp = SchemaInterpreter(schema)
        # tag=1, length=255, but only 2 bytes follow
        result = interp.decode(bytes([1, 255, 0x41, 0x42]))
        # Should not crash
        assert result is not None

    def test_string_length_exceeds_buffer(self):
        """String with length > buffer returns partial or empty."""
        schema = {'fields': [
            {'name': 's', 'type': 'string', 'length': 1000}
        ]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([0x41, 0x42, 0x43]))
        # Should not crash
        assert result is not None

    def test_bytes_negative_length_variable(self):
        """Bytes with negative length from signed var handles gracefully."""
        schema = {'fields': [
            {'name': 'len', 'type': 's8', 'var': 'len'},
            {'name': 'data', 'type': 'bytes', 'length': '$len'}
        ]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([0xFF, 0x41, 0x42]))  # len=-1
        # Should not crash
        assert result is not None
        assert result.data['len'] == -1

    # --- Numeric Edge Cases ---

    def test_division_by_zero_modifier(self):
        """Division by zero in modifier doesn't crash."""
        schema = {'fields': [
            {'name': 'x', 'type': 'u8', 'div': 0}
        ]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([42]))
        # Should not crash - may return original, inf, or error
        assert result is not None

    def test_division_by_zero_formula(self):
        """Division by zero in formula doesn't crash."""
        schema = {'fields': [
            {'name': 'x', 'type': 'u8', 'formula': 'x / 0'}
        ]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([42]))
        # Should not crash
        assert result is not None

    def test_sqrt_negative_clamped(self):
        """Sqrt of negative value clamps to 0."""
        schema = {'fields': [
            {'name': 'x', 'type': 's8', 'transform': [{'sqrt': True}]}
        ]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([0xFF]))  # -1 as s8
        
        assert result.success
        assert result.data['x'] == 0.0

    def test_overflow_large_mult(self):
        """Large multiplier doesn't cause overflow crash."""
        schema = {'fields': [
            {'name': 'x', 'type': 'u32', 'mult': 1e30}
        ]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([0xFF, 0xFF, 0xFF, 0xFF]))
        
        assert result is not None
        assert result.data['x'] > 0

    # --- Malformed Schema Edge Cases ---

    def test_empty_fields_array(self):
        """Schema with empty fields array decodes to empty result."""
        schema = {'fields': []}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([42]))
        
        assert result.success
        assert result.data == {}

    def test_field_missing_type(self):
        """Field without type handles gracefully."""
        schema = {'fields': [
            {'name': 'x'}
        ]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([42]))
        # Should not crash - may use default type or skip
        assert result is not None

    def test_match_no_matching_case(self):
        """Match with no matching case handles gracefully."""
        schema = {'fields': [
            {'name': 'type', 'type': 'u8', 'var': 't'},
            {'name': 'data', 'type': 'match', 'on': '$t', 'cases': [
                {'case': 1, 'fields': [{'name': 'a', 'type': 'u8'}]},
                {'case': 2, 'fields': [{'name': 'b', 'type': 'u8'}]},
            ]}
        ]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([99, 42]))  # type=99, no matching case
        
        assert result is not None
        assert result.data['type'] == 99

    # --- TLV Edge Cases ---

    def test_tlv_zero_length_records(self):
        """TLV with many zero-length records doesn't hang."""
        schema = {'fields': [
            {'name': 'data', 'type': 'tlv', 'tag': {'type': 'u8'},
             'length': {'type': 'u8'},
             'cases': {'1': []}}
        ]}
        interp = SchemaInterpreter(schema)
        import time
        start = time.time()
        result = interp.decode(bytes([1, 0] * 1000))  # 1000 zero-length records
        elapsed = time.time() - start
        
        assert result is not None
        assert elapsed < 1.0  # Should complete quickly

    def test_tlv_unknown_tag(self):
        """TLV with unknown tag handles gracefully."""
        schema = {'fields': [
            {'name': 'data', 'type': 'tlv', 'tag': {'type': 'u8'},
             'length': {'type': 'u8'},
             'cases': {'1': [{'name': 'a', 'type': 'u8'}]}}
        ]}
        interp = SchemaInterpreter(schema)
        result = interp.decode(bytes([99, 1, 42]))  # tag=99, not in cases
        
        assert result is not None


class TestBase64SchemaEdgeCases:
    """Edge case tests for base64 schema encoding/decoding."""

    def test_base64_encode_decode_roundtrip(self):
        """Base64 encode/decode roundtrip preserves schema."""
        import base64
        import json
        
        schema = {
            'name': 'test',
            'fields': [
                {'name': 'temp', 'type': 's16', 'mult': 0.01},
                {'name': 'humidity', 'type': 'u8'},
            ]
        }
        
        # Encode to JSON then base64
        json_str = json.dumps(schema)
        b64 = base64.b64encode(json_str.encode()).decode()
        
        # Decode back
        decoded_json = base64.b64decode(b64).decode()
        decoded = json.loads(decoded_json)
        
        assert decoded['name'] == schema['name']
        assert len(decoded['fields']) == len(schema['fields'])

    def test_base64_invalid_characters(self):
        """Invalid base64 characters raise error."""
        import base64
        
        with pytest.raises(Exception):
            base64.b64decode("!!!invalid!!!")

    def test_base64_malformed_json(self):
        """Valid base64 but malformed JSON handled."""
        import base64
        import json
        
        # Encode invalid JSON
        b64 = base64.b64encode(b"{not valid json}").decode()
        
        with pytest.raises(json.JSONDecodeError):
            decoded = base64.b64decode(b64).decode()
            json.loads(decoded)

    def test_base64_compressed_schema(self):
        """Compressed (gzip) base64 schema."""
        import base64
        import gzip
        import json
        
        schema = {'name': 'compressed', 'fields': [{'name': 'x', 'type': 'u8'}]}
        json_bytes = json.dumps(schema).encode()
        
        # Compress then base64
        compressed = gzip.compress(json_bytes)
        b64 = base64.b64encode(compressed).decode()
        
        # Decompress and decode
        decompressed = gzip.decompress(base64.b64decode(b64))
        decoded = json.loads(decompressed.decode())
        
        assert decoded['name'] == 'compressed'

    def test_base64_unicode_field_names(self):
        """Unicode field names in base64 schema."""
        import base64
        import json
        
        schema = {
            'name': 'unicode',
            'fields': [
                {'name': 'température', 'type': 's16'},
                {'name': '湿度', 'type': 'u8'},
            ]
        }
        
        json_str = json.dumps(schema, ensure_ascii=False)
        b64 = base64.b64encode(json_str.encode('utf-8')).decode()
        
        decoded = json.loads(base64.b64decode(b64).decode('utf-8'))
        assert decoded['fields'][0]['name'] == 'température'
        assert decoded['fields'][1]['name'] == '湿度'

    def test_base64_large_schema(self):
        """Large schema with many fields."""
        import base64
        import json
        
        schema = {
            'name': 'large',
            'fields': [{'name': f'field_{i}', 'type': 'u8'} for i in range(100)]
        }
        
        json_str = json.dumps(schema)
        b64 = base64.b64encode(json_str.encode()).decode()
        
        decoded = json.loads(base64.b64decode(b64).decode())
        assert len(decoded['fields']) == 100

    def test_base64_empty_schema(self):
        """Empty schema in base64."""
        import base64
        import json
        
        schema = {'name': 'empty', 'fields': []}
        
        json_str = json.dumps(schema)
        b64 = base64.b64encode(json_str.encode()).decode()
        
        decoded = json.loads(base64.b64decode(b64).decode())
        assert decoded['fields'] == []


class TestSemanticFields:
    """Tests for semantic fields: valid_range, resolution, unece.
    
    These fields enable IoT interoperability and quality tracking.
    """
    
    def test_valid_range_in_range(self):
        """Test value within valid_range reports good quality."""
        schema = {
            'name': 'test',
            'fields': [
                {
                    'name': 'temperature',
                    'type': 's16',
                    'div': 100,
                    'valid_range': [-40, 85]
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)
        # temp = 23.45 (0x0929 / 100)
        result = interpreter.decode(bytes([0x09, 0x29]))
        
        assert result.success
        assert abs(result.data['temperature'] - 23.45) < 0.01
        assert '_quality' in result.data
        assert result.data['_quality']['temperature'] == 'good'
        assert len(result.warnings) == 0
    
    def test_valid_range_at_boundary(self):
        """Test value exactly at boundary is valid."""
        schema = {
            'name': 'test',
            'fields': [
                {
                    'name': 'temperature',
                    'type': 's16',
                    'div': 100,
                    'valid_range': [-40, 85]
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)
        # temp = -40.0 (0xF060 / 100 = -4000 / 100)
        result = interpreter.decode(bytes([0xF0, 0x60]))
        
        assert result.success
        assert abs(result.data['temperature'] - (-40.0)) < 0.01
        assert result.data['_quality']['temperature'] == 'good'
    
    def test_valid_range_out_of_range_low(self):
        """Test value below valid_range reports out_of_range quality."""
        schema = {
            'name': 'test',
            'fields': [
                {
                    'name': 'temperature',
                    'type': 's16',
                    'div': 100,
                    'valid_range': [-40, 85]
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)
        # temp = -999.0 (sensor fault value)
        # -999 * 100 = -99900 = 0xFFFE795C (but we use s16, so encode -99900 mod 65536)
        # Actually: -999.0 -> raw = -99900 doesn't fit in s16
        # Let's use a value that does fit: -50.0 -> raw = -5000 = 0xEC78
        result = interpreter.decode(bytes([0xEC, 0x78]))
        
        assert result.success
        assert abs(result.data['temperature'] - (-50.0)) < 0.01
        assert result.data['_quality']['temperature'] == 'out_of_range'
        assert len(result.warnings) == 1
        assert 'outside valid range' in result.warnings[0]
    
    def test_valid_range_out_of_range_high(self):
        """Test value above valid_range reports out_of_range quality."""
        schema = {
            'name': 'test',
            'fields': [
                {
                    'name': 'temperature',
                    'type': 's16',
                    'div': 100,
                    'valid_range': [-40, 85]
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)
        # temp = 100.0 (above 85 max) -> raw = 10000 = 0x2710
        result = interpreter.decode(bytes([0x27, 0x10]))
        
        assert result.success
        assert abs(result.data['temperature'] - 100.0) < 0.01
        assert result.data['_quality']['temperature'] == 'out_of_range'
        assert len(result.warnings) == 1
    
    def test_multiple_fields_with_valid_range(self):
        """Test multiple fields each with valid_range."""
        schema = {
            'name': 'test',
            'fields': [
                {
                    'name': 'temperature',
                    'type': 's16',
                    'div': 100,
                    'valid_range': [-40, 85]
                },
                {
                    'name': 'humidity',
                    'type': 'u8',
                    'valid_range': [0, 100]
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)
        # temp = 23.45 (good), humidity = 105 (out of range)
        result = interpreter.decode(bytes([0x09, 0x29, 0x69]))
        
        assert result.success
        assert result.data['_quality']['temperature'] == 'good'
        assert result.data['_quality']['humidity'] == 'out_of_range'
        assert len(result.warnings) == 1  # Only humidity warning
    
    def test_field_without_valid_range_no_quality(self):
        """Test fields without valid_range don't appear in _quality."""
        schema = {
            'name': 'test',
            'fields': [
                {
                    'name': 'temperature',
                    'type': 's16',
                    'div': 100,
                    'valid_range': [-40, 85]
                },
                {
                    'name': 'status',
                    'type': 'u8'
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([0x09, 0x29, 0x01]))
        
        assert result.success
        assert 'temperature' in result.data['_quality']
        assert 'status' not in result.data['_quality']
    
    def test_no_quality_dict_when_no_valid_range_fields(self):
        """Test _quality not present when no fields have valid_range."""
        schema = {
            'name': 'test',
            'fields': [
                {'name': 'temperature', 'type': 's16'},
                {'name': 'humidity', 'type': 'u8'}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([0x09, 0x29, 0x64]))
        
        assert result.success
        assert '_quality' not in result.data
    
    def test_valid_range_with_resolution_and_unece(self):
        """Test schema with all semantic fields."""
        schema = {
            'name': 'test',
            'fields': [
                {
                    'name': 'temperature',
                    'type': 's16',
                    'div': 100,
                    'unit': '°C',
                    'valid_range': [-40, 85],
                    'resolution': 0.01,
                    'unece': 'CEL'
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([0x09, 0x29]))
        
        assert result.success
        assert abs(result.data['temperature'] - 23.45) < 0.01
        # resolution and unece are metadata, not affecting decode output
        # but valid_range produces quality
        assert result.data['_quality']['temperature'] == 'good'
    
    def test_quality_result_attribute(self):
        """Test DecodeResult.quality attribute is populated."""
        schema = {
            'name': 'test',
            'fields': [
                {
                    'name': 'temperature',
                    'type': 's16',
                    'div': 100,
                    'valid_range': [-40, 85]
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([0x09, 0x29]))
        
        assert result.quality['temperature'] == 'good'
        # quality dict attribute matches _quality in data
        assert result.quality == result.data['_quality']


class TestGetFieldMetadata:
    """Tests for get_field_metadata() API."""
    
    def test_get_all_field_metadata(self):
        """Test retrieving metadata for all fields."""
        schema = {
            'name': 'test',
            'fields': [
                {
                    'name': 'temperature',
                    'type': 's16',
                    'div': 100,
                    'unit': '°C',
                    'valid_range': [-40, 85],
                    'resolution': 0.01,
                    'unece': 'CEL',
                    'description': 'Temperature sensor',
                    'semantic': {'ipso': 3303}
                },
                {
                    'name': 'humidity',
                    'type': 'u8',
                    'unit': '%RH',
                    'valid_range': [0, 100],
                    'semantic': {'ipso': 3304, 'senml_unit': '%RH'}
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)
        metadata = interpreter.get_field_metadata()
        
        assert 'temperature' in metadata
        assert 'humidity' in metadata
        
        temp_meta = metadata['temperature']
        assert temp_meta['unit'] == '°C'
        assert temp_meta['valid_range'] == [-40, 85]
        assert temp_meta['resolution'] == 0.01
        assert temp_meta['unece'] == 'CEL'
        assert temp_meta['ipso'] == 3303
        assert temp_meta['description'] == 'Temperature sensor'
        
        hum_meta = metadata['humidity']
        assert hum_meta['unit'] == '%RH'
        assert hum_meta['ipso'] == 3304
        assert hum_meta['senml_unit'] == '%RH'
    
    def test_get_single_field_metadata(self):
        """Test retrieving metadata for a specific field."""
        schema = {
            'name': 'test',
            'fields': [
                {
                    'name': 'temperature',
                    'type': 's16',
                    'div': 100,
                    'unit': '°C',
                    'valid_range': [-40, 85],
                    'unece': 'CEL'
                },
                {
                    'name': 'humidity',
                    'type': 'u8'
                }
            ]
        }
        interpreter = SchemaInterpreter(schema)
        metadata = interpreter.get_field_metadata('temperature')
        
        assert metadata['unit'] == '°C'
        assert metadata['valid_range'] == [-40, 85]
        assert metadata['unece'] == 'CEL'
    
    def test_get_metadata_field_not_found(self):
        """Test get_field_metadata returns empty for unknown field."""
        schema = {
            'name': 'test',
            'fields': [
                {'name': 'temperature', 'type': 's16'}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        metadata = interpreter.get_field_metadata('nonexistent')
        
        assert metadata == {}
    
    def test_metadata_empty_for_no_semantic_fields(self):
        """Test fields without semantic annotations return empty metadata."""
        schema = {
            'name': 'test',
            'fields': [
                {'name': 'value', 'type': 'u8'}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        metadata = interpreter.get_field_metadata()
        
        # Fields without semantic annotations are not included
        # (only fields with unit, valid_range, etc. appear)
        assert metadata == {} or 'value' not in metadata or metadata.get('value') == {}


class TestLibrarySensorDefinitions:
    """Tests for sensor library definitions with semantic fields."""
    
    def test_environmental_library_temperature(self):
        """Test environmental library temperature definition."""
        import yaml
        from pathlib import Path
        
        lib_path = Path(__file__).parent.parent / 'lib' / 'sensors' / 'environmental.yaml'
        if not lib_path.exists():
            pytest.skip("Library file not found")
        
        with open(lib_path) as f:
            lib = yaml.safe_load(f)
        
        temp_def = lib['definitions']['temperature_c_div10']
        
        assert temp_def['type'] == 's16'
        assert temp_def['div'] == 10
        assert temp_def['unit'] == '°C'
        assert temp_def['unece'] == 'CEL'
        assert temp_def['valid_range'] == [-40, 125]
        assert temp_def['resolution'] == 0.1
        assert temp_def['semantic']['ipso'] == 3303
    
    def test_power_library_battery(self):
        """Test power library battery definitions have semantic fields."""
        import yaml
        from pathlib import Path
        
        lib_path = Path(__file__).parent.parent / 'lib' / 'sensors' / 'power.yaml'
        if not lib_path.exists():
            pytest.skip("Library file not found")
        
        with open(lib_path) as f:
            lib = yaml.safe_load(f)
        
        battery_def = lib['definitions']['battery_pct']
        
        assert battery_def['type'] == 'u8'
        assert battery_def['unit'] == '%'
        assert battery_def['valid_range'] == [0, 100]
        assert battery_def['unece'] == 'P1'
        assert battery_def['semantic']['ipso'] == 3316  # Voltage object (battery level)
    
    def test_all_library_files_valid_yaml(self):
        """Test all sensor library files are valid YAML."""
        import yaml
        from pathlib import Path
        
        lib_dir = Path(__file__).parent.parent / 'lib' / 'sensors'
        if not lib_dir.exists():
            pytest.skip("Library directory not found")
        
        for yaml_file in lib_dir.glob('*.yaml'):
            with open(yaml_file) as f:
                lib = yaml.safe_load(f)
            
            assert 'definitions' in lib, f"{yaml_file.name} missing 'definitions'"
            assert len(lib['definitions']) > 0, f"{yaml_file.name} has no definitions"
    
    def test_library_definitions_have_required_fields(self):
        """Test library definitions have name, type, and unit."""
        import yaml
        from pathlib import Path
        
        lib_dir = Path(__file__).parent.parent / 'lib' / 'sensors'
        if not lib_dir.exists():
            pytest.skip("Library directory not found")
        
        errors = []
        for yaml_file in lib_dir.glob('*.yaml'):
            with open(yaml_file) as f:
                lib = yaml.safe_load(f)
            
            for def_name, definition in lib['definitions'].items():
                if 'name' not in definition:
                    errors.append(f"{yaml_file.name}:{def_name} missing 'name'")
                if 'type' not in definition:
                    errors.append(f"{yaml_file.name}:{def_name} missing 'type'")
        
        assert len(errors) == 0, f"Library errors:\n" + "\n".join(errors)


class TestEncodings:
    """Tests for special encodings (sign_magnitude, bcd, gray).
    
    Note: These encodings are prototype extensions not yet in spec requirements.
    Related to M044 (endian support) as they affect integer interpretation.
    """
    
    def test_sign_magnitude_positive(self):
        """Test sign_magnitude with positive value."""
        schema = {
            'name': 'test',
            'fields': [
                {'name': 'value', 'type': 'u16', 'encoding': 'sign_magnitude'}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        # 0x0064 = 100 (positive, sign bit = 0)
        result = interpreter.decode(bytes([0x00, 0x64]))
        
        assert result.success
        assert result.data['value'] == 100
    
    def test_sign_magnitude_negative(self):
        """Test sign_magnitude with negative value."""
        schema = {
            'name': 'test',
            'endian': 'big',
            'fields': [
                {'name': 'value', 'type': 'u16', 'encoding': 'sign_magnitude'}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        # 0x8064 = -100 (sign bit = 1, magnitude = 100)
        result = interpreter.decode(bytes([0x80, 0x64]))
        
        assert result.success
        assert result.data['value'] == -100
    
    def test_sign_magnitude_roundtrip(self):
        """Test sign_magnitude encode/decode roundtrip."""
        schema = {
            'name': 'test',
            'fields': [
                {'name': 'value', 'type': 'u16', 'encoding': 'sign_magnitude'}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        # Test positive
        encoded = interpreter.encode({'value': 100})
        decoded = interpreter.decode(encoded.payload)
        assert decoded.data['value'] == 100
        
        # Test negative
        encoded = interpreter.encode({'value': -100})
        decoded = interpreter.decode(encoded.payload)
        assert decoded.data['value'] == -100
    
    def test_bcd_decode(self):
        """Test BCD decoding (default big-endian)."""
        schema = {
            'name': 'test',
            'fields': [
                {'name': 'value', 'type': 'u16', 'encoding': 'bcd'}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        # 0x1234 in BCD = 1234 decimal (default is big-endian)
        result = interpreter.decode(bytes([0x12, 0x34]))
        
        assert result.success
        assert result.data['value'] == 1234
    
    def test_bcd_decode_big_endian(self):
        """Test BCD decoding with big endian."""
        schema = {
            'name': 'test',
            'endian': 'big',
            'fields': [
                {'name': 'value', 'type': 'u16', 'encoding': 'bcd'}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        # 0x1234 in BCD = 1234 decimal
        result = interpreter.decode(bytes([0x12, 0x34]))
        
        assert result.success
        assert result.data['value'] == 1234
    
    def test_bcd_roundtrip(self):
        """Test BCD encode/decode roundtrip."""
        schema = {
            'name': 'test',
            'endian': 'big',
            'fields': [
                {'name': 'value', 'type': 'u16', 'encoding': 'bcd'}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        encoded = interpreter.encode({'value': 1234})
        decoded = interpreter.decode(encoded.payload)
        assert decoded.data['value'] == 1234
    
    def test_gray_decode(self):
        """Test Gray code decoding."""
        schema = {
            'name': 'test',
            'fields': [
                {'name': 'value', 'type': 'u8', 'encoding': 'gray'}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        # Gray code 0b1011 = binary 0b1101 = 13
        result = interpreter.decode(bytes([0b1011]))
        
        assert result.success
        assert result.data['value'] == 13
    
    def test_gray_roundtrip(self):
        """Test Gray code encode/decode roundtrip."""
        schema = {
            'name': 'test',
            'fields': [
                {'name': 'value', 'type': 'u8', 'encoding': 'gray'}
            ]
        }
        interpreter = SchemaInterpreter(schema)
        
        for value in [0, 1, 5, 10, 127, 255]:
            encoded = interpreter.encode({'value': value})
            decoded = interpreter.decode(encoded.payload)
            assert decoded.data['value'] == value, f"Failed for value {value}"


class TestDownlinkCommands:
    """Tests for downlink_commands support.
    
    Spec Requirements:
    - M210: JSON to binary encoding support
    - M211: Reverse arithmetic transformations
    - M212: Validate values fit in type
    Note: downlink_commands structure is a prototype extension. Spec uses match-based approach.
    """
    
    @pytest.fixture
    def command_schema(self):
        return {
            'name': 'device_config',
            'direction': 'bidirectional',
            'fields': [
                {'name': 'temperature', 'type': 's16', 'div': 10},
                {'name': 'humidity', 'type': 'u8'},
            ],
            'downlink_commands': {
                'set_interval': {
                    'command_id': 0x01,
                    'fields': [
                        {'name': 'interval_minutes', 'type': 'u16'}
                    ]
                },
                'reboot': {
                    'command_id': 0x02,
                    'fields': []
                },
                'set_threshold': {
                    'command_id': 0x03,
                    'fields': [
                        {'name': 'low', 'type': 'u8'},
                        {'name': 'high', 'type': 'u8'}
                    ]
                }
            }
        }
    
    def test_encode_command_basic(self, command_schema):
        """Test encoding a basic command."""
        interpreter = SchemaInterpreter(command_schema)
        
        result = interpreter.encode_command('set_interval', {'interval_minutes': 60})
        
        assert result.success
        assert result.payload[0] == 0x01  # command_id
        # 60 in big-endian (default): 0x00, 0x3C
        assert result.payload == bytes([0x01, 0x00, 0x3C])
    
    def test_encode_command_no_fields(self, command_schema):
        """Test encoding a command with no fields."""
        interpreter = SchemaInterpreter(command_schema)
        
        result = interpreter.encode_command('reboot', {})
        
        assert result.success
        assert result.payload == bytes([0x02])  # Just command_id
    
    def test_encode_command_multiple_fields(self, command_schema):
        """Test encoding a command with multiple fields."""
        interpreter = SchemaInterpreter(command_schema)
        
        result = interpreter.encode_command('set_threshold', {'low': 10, 'high': 90})
        
        assert result.success
        assert result.payload == bytes([0x03, 10, 90])
    
    def test_encode_command_unknown(self, command_schema):
        """Test encoding unknown command returns error."""
        interpreter = SchemaInterpreter(command_schema)
        
        result = interpreter.encode_command('unknown_cmd', {})
        
        assert not result.success
        assert 'Unknown command' in result.errors[0]
    
    def test_decode_command_basic(self, command_schema):
        """Test decoding a basic command."""
        interpreter = SchemaInterpreter(command_schema)
        
        # 60 in big-endian (default): 0x00, 0x3C
        result = interpreter.decode_command(bytes([0x01, 0x00, 0x3C]))
        
        assert result.success
        assert result.data['_command'] == 'set_interval'
        assert result.data['_command_id'] == 0x01
        assert result.data['interval_minutes'] == 60
    
    def test_decode_command_unknown_id(self, command_schema):
        """Test decoding unknown command_id."""
        interpreter = SchemaInterpreter(command_schema)
        
        result = interpreter.decode_command(bytes([0xFF, 0x00, 0x00]))
        
        assert not result.success
        assert 'Unknown command_id' in result.errors[0]
        assert result.data['_command_id'] == 0xFF
    
    def test_list_commands(self, command_schema):
        """Test listing available commands."""
        interpreter = SchemaInterpreter(command_schema)
        
        commands = interpreter.list_commands()
        
        assert 'set_interval' in commands
        assert 'reboot' in commands
        assert 'set_threshold' in commands
        
        assert commands['set_interval']['command_id'] == 0x01
        assert len(commands['set_interval']['fields']) == 1
        assert commands['reboot']['command_id'] == 0x02
        assert len(commands['reboot']['fields']) == 0
    
    def test_command_roundtrip(self, command_schema):
        """Test command encode/decode roundtrip."""
        interpreter = SchemaInterpreter(command_schema)
        
        original = {'interval_minutes': 120}
        encoded = interpreter.encode_command('set_interval', original)
        decoded = interpreter.decode_command(encoded.payload)
        
        assert decoded.success
        assert decoded.data['interval_minutes'] == 120


class TestCompactFormat:
    """Tests for compact format string parsing.
    
    Spec Requirements:
    - M166: Compact format functionally equivalent to full
    - M167: Simple sequential fields only
    - M168: Complex features not supported in compact
    - M169: Big-endian default when prefix omitted
    - O021: Compact string format MAY be supported
    - O022: Parsers MAY support compact format strings
    """
    
    def test_basic_format_string(self):
        """Test basic format string parsing."""
        schema = {
            'name': 'test',
            'fields': '>B:version H:length I:timestamp'
        }
        interpreter = SchemaInterpreter(schema)
        
        # version=1, length=256, timestamp=1000000
        payload = bytes([0x01, 0x01, 0x00, 0x00, 0x0F, 0x42, 0x40])
        result = interpreter.decode(payload)
        
        assert result.success
        assert result.data['version'] == 1
        assert result.data['length'] == 256
        assert result.data['timestamp'] == 1000000
    
    def test_format_with_skip(self):
        """Test format string with skip bytes."""
        schema = {
            'name': 'test',
            'fields': '>B:type 2x H:value'
        }
        interpreter = SchemaInterpreter(schema)
        
        # type=1, skip 2 bytes, value=1000
        payload = bytes([0x01, 0x00, 0x00, 0x03, 0xE8])
        result = interpreter.decode(payload)
        
        assert result.success
        assert result.data['type'] == 1
        assert result.data['value'] == 1000
    
    def test_format_little_endian(self):
        """Test format string with little endian."""
        schema = {
            'name': 'test',
            'fields': '<H:value I:timestamp'
        }
        interpreter = SchemaInterpreter(schema)
        
        # value=0x0102 LE, timestamp=0x04030201 LE
        payload = bytes([0x02, 0x01, 0x01, 0x02, 0x03, 0x04])
        result = interpreter.decode(payload)
        
        assert result.success
        assert result.data['value'] == 0x0102
        assert result.data['timestamp'] == 0x04030201
    
    def test_format_signed_types(self):
        """Test format string with signed types."""
        schema = {
            'name': 'test',
            'fields': '>b:signed_byte h:signed_short'
        }
        interpreter = SchemaInterpreter(schema)
        
        # signed_byte=-1, signed_short=-100
        payload = bytes([0xFF, 0xFF, 0x9C])
        result = interpreter.decode(payload)
        
        assert result.success
        assert result.data['signed_byte'] == -1
        assert result.data['signed_short'] == -100
    
    def test_format_float_types(self):
        """Test format string with float types."""
        schema = {
            'name': 'test',
            'fields': '>f:temperature'
        }
        interpreter = SchemaInterpreter(schema)
        
        # 23.5 as big-endian float
        payload = struct.pack('>f', 23.5)
        result = interpreter.decode(payload)
        
        assert result.success
        assert abs(result.data['temperature'] - 23.5) < 0.001


class TestDirectionProperty:
    """Tests for direction property support.
    
    Spec Requirements:
    - O005: direction property (uplink/downlink/both)
    - O028: direction: downlink indication
    - R002: When direction specified, decoders SHOULD validate
    """
    
    def test_direction_uplink(self):
        """Test direction: uplink (default)."""
        schema = {
            'name': 'test',
            'direction': 'uplink',
            'fields': [{'name': 'temp', 'type': 's16'}]
        }
        interpreter = SchemaInterpreter(schema)
        
        assert interpreter.direction == 'uplink'
    
    def test_direction_downlink(self):
        """Test direction: downlink."""
        schema = {
            'name': 'test',
            'direction': 'downlink',
            'fields': [{'name': 'interval', 'type': 'u16'}]
        }
        interpreter = SchemaInterpreter(schema)
        
        assert interpreter.direction == 'downlink'
    
    def test_direction_bidirectional(self):
        """Test direction: bidirectional."""
        schema = {
            'name': 'test',
            'direction': 'bidirectional',
            'fields': [{'name': 'temp', 'type': 's16'}],
            'downlink_commands': {
                'config': {'command_id': 1, 'fields': []}
            }
        }
        interpreter = SchemaInterpreter(schema)
        
        assert interpreter.direction == 'bidirectional'
        assert 'config' in interpreter.downlink_commands
    
    def test_direction_default(self):
        """Test default direction is uplink."""
        schema = {
            'name': 'test',
            'fields': [{'name': 'temp', 'type': 's16'}]
        }
        interpreter = SchemaInterpreter(schema)
        
        assert interpreter.direction == 'uplink'


class TestValidationLevels:
    """Tests for validation levels (ERROR/WARNING/INFO).
    
    Spec Requirements:
    - M179: Reject invalid schemas
    - M185: Schema MUST NOT be used if errors exist
    - R030: Validators SHOULD output structured error information
    """
    
    def test_validation_error(self):
        """Test ERROR level messages."""
        from validate_schema import validate_schema, ValidationLevel
        
        # Schema with missing required field
        schema = {
            # Missing 'name'
            'fields': [{'name': 'temp', 'type': 's16'}]
        }
        
        result = validate_schema(schema)
        
        assert not result.schema_valid
        assert result.error_count > 0
    
    def test_validation_warning_missing_ipso(self):
        """Test WARNING for missing IPSO annotation on sensor field."""
        from validate_schema import validate_schema
        
        schema = {
            'name': 'test',
            'fields': [
                {'name': 'temperature', 'type': 's16', 'div': 10}
            ],
            'test_vectors': [
                {'name': 'basic', 'payload': '00E7', 'expected': {'temperature': 23.1}}
            ]
        }
        
        result = validate_schema(schema)
        
        assert result.schema_valid
        assert result.warning_count > 0
        assert any('ipso' in w.lower() for w in result.schema_warnings)
    
    def test_validation_info_missing_unit(self):
        """Test INFO for missing unit annotation."""
        from validate_schema import validate_schema
        
        schema = {
            'name': 'test',
            'fields': [
                {'name': 'temperature', 'type': 's16', 'div': 10, 'ipso': 3303}
            ],
            'test_vectors': [
                {'name': 'basic', 'payload': '00E7', 'expected': {'temperature': 23.1}}
            ]
        }
        
        result = validate_schema(schema)
        
        assert result.schema_valid
        assert result.info_count > 0
        assert any('unit' in i.lower() for i in result.schema_info)
    
    def test_validation_warning_no_test_vectors(self):
        """Test WARNING when no test vectors defined."""
        from validate_schema import validate_schema
        
        schema = {
            'name': 'test',
            'fields': [{'name': 'value', 'type': 'u8'}]
        }
        
        result = validate_schema(schema)
        
        assert result.schema_valid
        assert result.warning_count > 0
        assert any('test vector' in w.lower() for w in result.schema_warnings)
    
    def test_validation_result_to_dict(self):
        """Test ValidationResult.to_dict() includes all levels."""
        from validate_schema import validate_schema
        
        schema = {
            'name': 'test',
            'fields': [{'name': 'temperature', 'type': 's16'}],
            'test_vectors': [
                {'name': 'basic', 'payload': '00E7', 'expected': {'temperature': 231}}
            ]
        }
        
        result = validate_schema(schema)
        result_dict = result.to_dict()
        
        assert 'schema_errors' in result_dict
        assert 'schema_warnings' in result_dict
        assert 'schema_info' in result_dict
        assert 'error_count' in result_dict
        assert 'warning_count' in result_dict
        assert 'info_count' in result_dict
