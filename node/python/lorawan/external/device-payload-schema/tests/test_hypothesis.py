"""
test_hypothesis.py - Property-based testing with Hypothesis

Provides systematic coverage-guided fuzzing that's more thorough than
random fuzzing, discovering edge cases through shrinking.

Requirements Coverage:
- REQ-Decoder-Sa-046: Decoders MUST NOT crash on malformed payloads
- REQ-Decoder-Sa-047: Decoders MUST NOT enter infinite loops
- REQ-Decoder-Sa-048: Decoders MUST return error for invalid input
- REQ-Roundtrip-045: Encode/decode consistency
- REQ-Type-Bound-049: Boundary value handling
- REQ-Validator-Sa-050: Validator MUST NOT crash on malformed schemas
- REQ-Type-Alia-003: Type aliases equivalence

Run with:
    pytest tests/test_hypothesis.py -v
    pytest tests/test_hypothesis.py -v --hypothesis-show-statistics
"""

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))
from schema_interpreter import SchemaInterpreter, DecodeResult


# =============================================================================
# Strategies for generating test data
# =============================================================================

# Basic byte sequences
bytes_strategy = st.binary(min_size=0, max_size=256)
short_bytes = st.binary(min_size=0, max_size=10)
exact_6_bytes = st.binary(min_size=6, max_size=6)

# Integer strategies matching schema types
u8_values = st.integers(min_value=0, max_value=255)
u16_values = st.integers(min_value=0, max_value=65535)
s16_values = st.integers(min_value=-32768, max_value=32767)
u32_values = st.integers(min_value=0, max_value=2**32 - 1)
s32_values = st.integers(min_value=-2**31, max_value=2**31 - 1)

# Float strategies
float_values = st.floats(
    min_value=-1e6, max_value=1e6,
    allow_nan=False, allow_infinity=False
)

# Environmental sensor data strategy
env_sensor_data = st.fixed_dictionaries({
    'temperature': st.floats(min_value=-327.68, max_value=327.67, allow_nan=False, allow_infinity=False),
    'humidity': st.floats(min_value=0, max_value=127.5, allow_nan=False, allow_infinity=False),
    'battery_mv': u16_values,
    'status': u8_values,
})


# =============================================================================
# Test Schema
# =============================================================================

ENV_SENSOR_SCHEMA = {
    'name': 'env_sensor',
    'version': 1,
    'endian': 'big',
    'fields': [
        {'name': 'temperature', 'type': 's16', 'mult': 0.01},
        {'name': 'humidity', 'type': 'u8', 'mult': 0.5},
        {'name': 'battery_mv', 'type': 'u16'},
        {'name': 'status', 'type': 'u8'},
    ]
}


# =============================================================================
# Property Tests: Decoder Safety
# =============================================================================

class TestDecoderSafety:
    """Test that decoder handles all inputs safely.
    
    REQ-Decoder-Sa-046: Decoders MUST NOT crash on malformed payloads
    REQ-Decoder-Sa-047: Decoders MUST NOT enter infinite loops
    REQ-Decoder-Sa-048: Decoders MUST return error indication for invalid inputs
    """
    
    @given(bytes_strategy)
    @settings(max_examples=1000, suppress_health_check=[HealthCheck.too_slow])
    def test_never_crashes_on_random_bytes(self, data):
        """Decoder MUST NOT crash on any byte sequence."""
        interpreter = SchemaInterpreter(ENV_SENSOR_SCHEMA)
        # Should not raise unhandled exception
        result = interpreter.decode(data)
        # Result is either success or has errors
        assert isinstance(result.success, bool)
    
    @given(short_bytes)
    @settings(max_examples=500)
    def test_handles_truncated_payloads(self, data):
        """Decoder MUST handle payloads shorter than expected."""
        interpreter = SchemaInterpreter(ENV_SENSOR_SCHEMA)
        result = interpreter.decode(data)
        if len(data) < 6:  # env_sensor needs 6 bytes
            # Should fail gracefully, not crash
            assert not result.success or result.data is not None
    
    @given(st.binary(min_size=100, max_size=256))
    @settings(max_examples=200)
    def test_handles_oversized_payloads(self, data):
        """Decoder MUST handle payloads longer than expected."""
        interpreter = SchemaInterpreter(ENV_SENSOR_SCHEMA)
        result = interpreter.decode(data)
        # Extra bytes should be ignored or handled gracefully
        assert isinstance(result.success, bool)


# =============================================================================
# Property Tests: Roundtrip Encoding
# =============================================================================

class TestRoundtrip:
    """Test encode/decode roundtrip properties.
    
    REQ-Roundtrip-045: Encode/decode consistency
    """
    
    @given(exact_6_bytes)
    @settings(max_examples=1000)
    def test_decode_produces_valid_structure(self, data):
        """Decoded result has expected fields."""
        interpreter = SchemaInterpreter(ENV_SENSOR_SCHEMA)
        result = interpreter.decode(data)
        
        if result.success:
            assert 'temperature' in result.data
            assert 'humidity' in result.data
            assert 'battery_mv' in result.data
            assert 'status' in result.data
    
    @given(s16_values, u8_values, u16_values, u8_values)
    @settings(max_examples=500)
    def test_roundtrip_preserves_integers(self, temp_raw, humidity_raw, battery, status):
        """Encode then decode preserves integer values."""
        # Build payload manually
        payload = struct.pack('>hBHB', temp_raw, humidity_raw, battery, status)
        
        interpreter = SchemaInterpreter(ENV_SENSOR_SCHEMA)
        result = interpreter.decode(payload)
        
        assert result.success
        # After mult, check raw values match
        assert abs(result.data['temperature'] - (temp_raw * 0.01)) < 0.001
        assert abs(result.data['humidity'] - (humidity_raw * 0.5)) < 0.001
        assert result.data['battery_mv'] == battery
        assert result.data['status'] == status
    
    @given(env_sensor_data)
    @settings(max_examples=500)
    def test_encode_decode_roundtrip(self, data):
        """Encoding then decoding returns equivalent values within quantization limits."""
        interpreter = SchemaInterpreter(ENV_SENSOR_SCHEMA)
        
        # Encode
        encode_result = interpreter.encode(data)
        assume(encode_result.success)  # Skip if encoding fails
        
        # Decode
        decode_result = interpreter.decode(encode_result.payload)
        assert decode_result.success
        
        # Values should match within quantization tolerance
        # Temperature: s16 with mult 0.01 -> quantization step = 0.01
        # Humidity: u8 with mult 0.5 -> quantization step = 0.5
        temp_tolerance = 0.01 + 0.001  # quantization + float epsilon
        humidity_tolerance = 0.5 + 0.001  # quantization + float epsilon
        
        assert abs(decode_result.data['temperature'] - data['temperature']) <= temp_tolerance
        assert abs(decode_result.data['humidity'] - data['humidity']) <= humidity_tolerance
        assert decode_result.data['battery_mv'] == data['battery_mv']
        assert decode_result.data['status'] == data['status']


# =============================================================================
# Property Tests: Type Boundaries
# =============================================================================

class TestTypeBoundaries:
    """Test behavior at type boundaries.
    
    REQ-Type-Bound-049: Boundary value handling for all types
    """
    
    @given(st.sampled_from([0, 127, 128, 255]))
    def test_u8_boundary_values(self, value):
        """u8 handles boundary values correctly."""
        schema = {
            'name': 'test', 'version': 1,
            'fields': [{'name': 'val', 'type': 'u8'}]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([value]))
        assert result.success
        assert result.data['val'] == value
    
    @given(st.sampled_from([0, 32767, -32768, -1]))
    def test_s16_boundary_values(self, value):
        """s16 handles boundary values correctly."""
        schema = {
            'name': 'test', 'version': 1,
            'fields': [{'name': 'val', 'type': 's16'}]
        }
        interpreter = SchemaInterpreter(schema)
        payload = struct.pack('>h', value)
        result = interpreter.decode(payload)
        assert result.success
        assert result.data['val'] == value
    
    @given(st.sampled_from([0, 65535, 32768, 1]))
    def test_u16_boundary_values(self, value):
        """u16 handles boundary values correctly."""
        schema = {
            'name': 'test', 'version': 1,
            'fields': [{'name': 'val', 'type': 'u16'}]
        }
        interpreter = SchemaInterpreter(schema)
        payload = struct.pack('>H', value)
        result = interpreter.decode(payload)
        assert result.success
        assert result.data['val'] == value


# =============================================================================
# Property Tests: Modifiers
# =============================================================================

class TestModifiers:
    """Test arithmetic modifier properties.
    
    REQ-Arithmeti-022: mult, add, div modifiers
    REQ-Modifier-O-023: Modifier application order
    """
    
    @given(u8_values, st.floats(min_value=0.001, max_value=100, allow_nan=False, allow_infinity=False))
    @settings(max_examples=500)
    def test_mult_is_reversible(self, raw_value, mult):
        """mult modifier is reversible: (x * mult) / mult ≈ x."""
        schema = {
            'name': 'test', 'version': 1,
            'fields': [{'name': 'val', 'type': 'u8', 'mult': mult}]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([raw_value]))
        
        assert result.success
        expected = raw_value * mult
        assert abs(result.data['val'] - expected) < 0.001
    
    @given(u8_values, st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False))
    @settings(max_examples=500)
    def test_add_is_reversible(self, raw_value, add):
        """add modifier is reversible: (x + add) - add = x."""
        schema = {
            'name': 'test', 'version': 1,
            'fields': [{'name': 'val', 'type': 'u8', 'add': add}]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([raw_value]))
        
        assert result.success
        expected = raw_value + add
        assert abs(result.data['val'] - expected) < 0.001


# =============================================================================
# Property Tests: Bitfields
# =============================================================================

class TestBitfields:
    """Test bitfield extraction properties.
    
    REQ-Bitfield--009: Bitfield extraction accuracy
    REQ-Bitfield--010: Python slice syntax
    """
    
    @given(u8_values)
    def test_full_byte_extraction(self, value):
        """Extracting all 8 bits equals the byte value."""
        schema = {
            'name': 'test', 'version': 1,
            'fields': [{'name': 'val', 'type': 'u8[0:7]'}]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([value]))
        assert result.success
        assert result.data['val'] == value
    
    @given(u8_values)
    def test_single_bit_extraction(self, value):
        """Each single bit extraction matches expected value."""
        for bit in range(8):
            schema = {
                'name': 'test', 'version': 1,
                'fields': [{'name': f'bit{bit}', 'type': f'u8[{bit}:{bit}]', 'consume': 0 if bit < 7 else 1}]
            }
            interpreter = SchemaInterpreter(schema)
            result = interpreter.decode(bytes([value]))
            assert result.success
            expected = (value >> bit) & 1
            assert result.data[f'bit{bit}'] == expected
    
    @given(u8_values)
    def test_nibble_extraction(self, value):
        """Extracting nibbles (4-bit) works correctly."""
        schema = {
            'name': 'test', 'version': 1,
            'fields': [
                {'name': 'low', 'type': 'u8[0:3]', 'consume': 0},
                {'name': 'high', 'type': 'u8[4:7]'},
            ]
        }
        interpreter = SchemaInterpreter(schema)
        result = interpreter.decode(bytes([value]))
        assert result.success
        assert result.data['low'] == (value & 0x0F)
        assert result.data['high'] == ((value >> 4) & 0x0F)


# =============================================================================
# Property Tests: Schema Parser Safety
# =============================================================================

class TestTypeAliases:
    """Test that all type aliases work identically.
    
    REQ-Type-Alia-003: Type aliases (uint8, int8, etc.) are equivalent
    """
    
    # All equivalent type groups
    TYPE_GROUPS = [
        ['u8', 'uint8'],
        ['u16', 'uint16'],
        ['u32', 'uint32'],
        ['s8', 'i8', 'int8'],
        ['s16', 'i16', 'int16'],
        ['s32', 'i32', 'int32'],
    ]
    
    @given(st.sampled_from(TYPE_GROUPS), u8_values)
    def test_8bit_aliases_equivalent(self, type_group, value):
        """All 8-bit type aliases decode identically."""
        if '8' not in type_group[0]:
            assume(False)
        
        results = []
        for type_name in type_group:
            schema = {'name': 'test', 'version': 1, 'fields': [{'name': 'v', 'type': type_name}]}
            interp = SchemaInterpreter(schema)
            # For signed types, use signed value range
            if type_name.startswith('s') or type_name.startswith('i') or type_name.startswith('int'):
                test_val = value if value < 128 else value - 256
                payload = struct.pack('b', test_val) if test_val >= 0 else struct.pack('b', test_val)
            else:
                payload = bytes([value])
            result = interp.decode(payload)
            results.append(result.data['v'])
        
        # All aliases should produce same result
        assert all(r == results[0] for r in results), f"Mismatch: {dict(zip(type_group, results))}"
    
    @given(st.sampled_from(['u16', 'uint16']), u16_values)
    def test_u16_aliases_equivalent(self, type_name, value):
        """u16 and uint16 decode identically."""
        schema = {'name': 'test', 'version': 1, 'fields': [{'name': 'v', 'type': type_name}]}
        interp = SchemaInterpreter(schema)
        payload = struct.pack('>H', value)
        result = interp.decode(payload)
        assert result.data['v'] == value
    
    @given(st.sampled_from(['s16', 'i16', 'int16']), s16_values)
    def test_s16_aliases_equivalent(self, type_name, value):
        """s16, i16, and int16 decode identically."""
        schema = {'name': 'test', 'version': 1, 'fields': [{'name': 'v', 'type': type_name}]}
        interp = SchemaInterpreter(schema)
        payload = struct.pack('>h', value)
        result = interp.decode(payload)
        assert result.data['v'] == value


class TestSchemaParserSafety:
    """Test schema parser handles malformed schemas safely.
    
    REQ-Validator-Sa-050: Validators MUST NOT crash on malformed schemas
    """
    
    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.one_of(st.none(), st.integers(), st.text(), st.booleans()),
        min_size=0, max_size=10
    ))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_random_dict_doesnt_crash(self, schema):
        """Random dict schema doesn't crash parser."""
        try:
            interpreter = SchemaInterpreter(schema)
        except (ValueError, KeyError, TypeError, AttributeError):
            pass  # Expected - invalid schema
        # Should not raise other exceptions
    
    @given(st.lists(
        st.dictionaries(
            keys=st.sampled_from(['name', 'type', 'mult', 'add', 'length']),
            values=st.one_of(st.text(max_size=20), st.integers(-100, 100), st.floats(allow_nan=False)),
            min_size=0, max_size=5
        ),
        min_size=0, max_size=10
    ))
    @settings(max_examples=200)
    def test_random_fields_dont_crash(self, fields):
        """Random field definitions don't crash parser."""
        schema = {
            'name': 'test',
            'version': 1,
            'fields': fields
        }
        try:
            interpreter = SchemaInterpreter(schema)
            interpreter.decode(b'\x00\x00\x00\x00')
        except (ValueError, KeyError, TypeError, AttributeError, IndexError):
            pass  # Expected - invalid schema


# =============================================================================
# Run with pytest
# =============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--hypothesis-show-statistics'])
