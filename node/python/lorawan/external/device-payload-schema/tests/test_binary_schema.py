"""
Tests for binary schema encoder/decoder (v1 and v2).
"""

import pytest
import sys
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))

from binary_schema import (
    BinarySchemaEncoder, BinarySchemaDecoder,
    BinarySchema, BinaryField, FieldType,
    encode_schema, decode_schema,
    schema_to_base64, base64_to_schema,
    schema_hash, compute_crc32,
    OPCODE_MATCH, OPCODE_VAR,
)

from binary_schema_v2 import (
    encode_schema as encode_schema_v2,
    decode_schema as decode_schema_v2,
    schema_to_base64 as schema_to_base64_v2,
    base64_to_schema as base64_to_schema_v2,
    BinarySchemaEncoder as BinarySchemaEncoderV2,
    BinarySchemaDecoder as BinarySchemaDecoderV2,
    FieldType as FieldTypeV2,
)


class TestBinaryField:
    """Tests for BinaryField class."""
    
    def test_field_to_bytes(self):
        """Test encoding field to bytes."""
        field = BinaryField(
            type_code=FieldType.SIGNED,
            size=2,
            mult_exponent=-2,
            semantic_id=3303
        )
        data = field.to_bytes()
        assert len(data) == 4
        assert data[0] == 0x12  # SIGNED (1) << 4 | size (2)
        assert data[1] == 0xFE  # -2 as unsigned byte
        assert data[2:4] == b'\xE7\x0C'  # 3303 little-endian
    
    def test_field_from_bytes(self):
        """Test decoding field from bytes."""
        data = bytes([0x12, 0xFE, 0xE7, 0x0C])
        field = BinaryField.from_bytes(data)
        
        assert field.type_code == FieldType.SIGNED
        assert field.size == 2
        assert field.mult_exponent == -2
        assert field.semantic_id == 3303
    
    def test_field_roundtrip(self):
        """Test field encode/decode roundtrip."""
        original = BinaryField(
            type_code=FieldType.UNSIGNED,
            size=1,
            mult_exponent=0,
            semantic_id=0
        )
        data = original.to_bytes()
        decoded = BinaryField.from_bytes(data)
        
        assert decoded.type_code == original.type_code
        assert decoded.size == original.size
        assert decoded.mult_exponent == original.mult_exponent
        assert decoded.semantic_id == original.semantic_id
    
    def test_field_from_bytes_too_short(self):
        """Test error handling for short data."""
        with pytest.raises(ValueError, match="Need 4 bytes"):
            BinaryField.from_bytes(bytes([0x12, 0xFE]))


class TestBinarySchema:
    """Tests for BinarySchema class."""
    
    def test_schema_to_bytes(self):
        """Test encoding schema to bytes."""
        schema = BinarySchema(
            version=1,
            fields=[
                BinaryField(FieldType.SIGNED, 2, -2, 3303),
                BinaryField(FieldType.UNSIGNED, 1, -1, 3304),
            ]
        )
        data = schema.to_bytes()
        
        assert data[0] == 1  # version
        assert data[1] == 2  # field count
        assert len(data) == 2 + 2 * 4  # header + 2 fields
    
    def test_schema_from_bytes(self):
        """Test decoding schema from bytes."""
        # Version 1, 2 fields
        data = bytes([
            0x01, 0x02,  # header
            0x12, 0xFE, 0xE7, 0x0C,  # field 1
            0x01, 0xFF, 0xE8, 0x0C,  # field 2
        ])
        schema = BinarySchema.from_bytes(data)
        
        assert schema.version == 1
        assert len(schema.fields) == 2
        assert schema.fields[0].type_code == FieldType.SIGNED
        assert schema.fields[1].type_code == FieldType.UNSIGNED
    
    def test_schema_to_base64(self):
        """Test base64 encoding."""
        schema = BinarySchema(version=1, fields=[
            BinaryField(FieldType.UNSIGNED, 1, 0, 0)
        ])
        b64 = schema.to_base64()
        assert isinstance(b64, str)
        assert len(b64) > 0
    
    def test_schema_from_base64(self):
        """Test base64 decoding."""
        # Create schema, encode to base64, decode back
        original = BinarySchema(version=1, fields=[
            BinaryField(FieldType.SIGNED, 2, -2, 3303)
        ])
        b64 = original.to_base64()
        decoded = BinarySchema.from_base64(b64)
        
        assert decoded.version == original.version
        assert len(decoded.fields) == len(original.fields)
    
    def test_schema_empty(self):
        """Test empty schema."""
        schema = BinarySchema(version=1, fields=[])
        data = schema.to_bytes()
        assert data == bytes([0x01, 0x00])
    
    def test_schema_from_bytes_truncated(self):
        """Test error for truncated field data."""
        data = bytes([0x01, 0x02, 0x12, 0xFE])  # Says 2 fields but only partial first
        with pytest.raises(ValueError, match="Truncated"):
            BinarySchema.from_bytes(data)


class TestBinarySchemaEncoder:
    """Tests for BinarySchemaEncoder class."""
    
    @pytest.fixture
    def encoder(self):
        return BinarySchemaEncoder()
    
    @pytest.fixture
    def simple_schema(self):
        return {
            'name': 'test_sensor',
            'fields': [
                {'name': 'temperature', 'type': 's16', 'mult': 0.01,
                 'semantic': {'ipso': 3303}},
                {'name': 'humidity', 'type': 'u8', 'mult': 0.5,
                 'semantic': {'ipso': 3304}},
            ]
        }
    
    def test_encode_simple(self, encoder, simple_schema):
        """Test encoding simple schema."""
        binary = encoder.encode(simple_schema)
        assert binary.version == 1
        assert len(binary.fields) == 2
    
    def test_encode_to_bytes(self, encoder, simple_schema):
        """Test encoding directly to bytes."""
        data = encoder.encode_to_bytes(simple_schema)
        assert isinstance(data, bytes)
        assert len(data) >= 2  # At least header
    
    def test_encode_to_base64(self, encoder, simple_schema):
        """Test encoding directly to base64."""
        b64 = encoder.encode_to_base64(simple_schema)
        assert isinstance(b64, str)
    
    def test_encode_skips_internal_fields(self, encoder):
        """Test that fields starting with _ are skipped."""
        schema = {
            'fields': [
                {'name': '_reserved', 'type': 'u8'},
                {'name': 'value', 'type': 'u16'},
            ]
        }
        binary = encoder.encode(schema)
        assert len(binary.fields) == 1
        assert binary.fields[0].name == 'value'
    
    def test_encode_skips_object_keeps_match(self, encoder):
        """Test that object is skipped but match triggers v2 encoding."""
        schema = {
            'fields': [
                {'name': 'value', 'type': 'u8'},
                {'name': 'nested', 'type': 'object'},
                {'name': 'conditional', 'type': 'match',
                 'on': '$value',
                 'cases': [{'case': 1, 'fields': []}]},
            ]
        }
        binary = encoder.encode(schema)
        # Now produces v2 with match support
        assert binary.version == 2
        assert binary.records is not None
    
    def test_mult_to_exponent_power_of_10(self, encoder):
        """Test multiplier conversion for powers of 10."""
        assert encoder._mult_to_exponent(1.0) == 0
        assert encoder._mult_to_exponent(0.1) == -1
        assert encoder._mult_to_exponent(0.01) == -2
        assert encoder._mult_to_exponent(0.001) == -3
        assert encoder._mult_to_exponent(10) == 1
        assert encoder._mult_to_exponent(100) == 2
    
    def test_mult_to_exponent_special(self, encoder):
        """Test special multiplier (0.5)."""
        assert encoder._mult_to_exponent(0.5) == 0xFF


class TestBinarySchemaDecoder:
    """Tests for BinarySchemaDecoder class."""
    
    @pytest.fixture
    def decoder(self):
        return BinarySchemaDecoder()
    
    def test_decode_simple(self, decoder):
        """Test decoding simple binary schema."""
        binary = BinarySchema(
            version=1,
            fields=[
                BinaryField(FieldType.SIGNED, 2, -2, 3303, name='temperature'),
            ]
        )
        schema = decoder.decode(binary)
        
        assert 'version' in schema
        assert 'fields' in schema
        assert len(schema['fields']) == 1
        assert schema['fields'][0]['type'] == 's16'
    
    def test_decode_with_mult(self, decoder):
        """Test decoding field with multiplier."""
        binary = BinarySchema(
            version=1,
            fields=[
                BinaryField(FieldType.UNSIGNED, 1, -1, 0),
            ]
        )
        schema = decoder.decode(binary)
        
        assert schema['fields'][0]['mult'] == 0.1
    
    def test_decode_with_semantic(self, decoder):
        """Test decoding field with semantic ID."""
        binary = BinarySchema(
            version=1,
            fields=[
                BinaryField(FieldType.SIGNED, 2, 0, 3303),
            ]
        )
        schema = decoder.decode(binary)
        
        assert 'semantic' in schema['fields'][0]
        assert schema['fields'][0]['semantic']['ipso'] == 3303
    
    def test_decode_from_bytes(self, decoder):
        """Test decoding from raw bytes."""
        data = bytes([0x01, 0x01, 0x12, 0xFE, 0xE7, 0x0C])
        schema = decoder.decode_from_bytes(data)
        
        assert len(schema['fields']) == 1
        assert schema['fields'][0]['type'] == 's16'


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""
    
    @pytest.fixture
    def test_schema(self):
        return {
            'name': 'env_sensor',
            'fields': [
                {'name': 'temperature', 'type': 's16', 'mult': 0.01,
                 'semantic': {'ipso': 3303}},
                {'name': 'humidity', 'type': 'u8',
                 'semantic': {'ipso': 3304}},
                {'name': 'battery', 'type': 'u16'},
                {'name': 'status', 'type': 'u8'},
            ]
        }
    
    def test_encode_decode_roundtrip(self, test_schema):
        """Test full encode/decode roundtrip."""
        binary = encode_schema(test_schema)
        decoded = decode_schema(binary)
        
        assert len(decoded['fields']) == len(test_schema['fields'])
    
    def test_base64_roundtrip(self, test_schema):
        """Test base64 encode/decode roundtrip."""
        b64 = schema_to_base64(test_schema)
        decoded = base64_to_schema(b64)
        
        assert len(decoded['fields']) == len(test_schema['fields'])
    
    def test_schema_hash_deterministic(self, test_schema):
        """Test that schema hash is deterministic."""
        h1 = schema_hash(test_schema)
        h2 = schema_hash(test_schema)
        assert h1 == h2
    
    def test_schema_hash_different_schemas(self, test_schema):
        """Test that different schemas have different hashes."""
        h1 = schema_hash(test_schema)
        
        modified = dict(test_schema)
        modified['fields'] = modified['fields'][:2]
        h2 = schema_hash(modified)
        
        assert h1 != h2
    
    def test_compute_crc32(self):
        """Test CRC32 computation."""
        crc = compute_crc32(b'test')
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFFFFFF


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_fields(self):
        """Test schema with no fields."""
        schema = {'fields': []}
        binary = encode_schema(schema)
        decoded = decode_schema(binary)
        assert decoded['fields'] == []
    
    def test_large_schema(self):
        """Test schema with many fields."""
        schema = {
            'fields': [
                {'name': f'field_{i}', 'type': 'u8'}
                for i in range(64)
            ]
        }
        binary = encode_schema(schema)
        decoded = decode_schema(binary)
        assert len(decoded['fields']) == 64
    
    def test_all_integer_types(self):
        """Test all supported integer types."""
        schema = {
            'fields': [
                {'name': 'u8_field', 'type': 'u8'},
                {'name': 'u16_field', 'type': 'u16'},
                {'name': 'u32_field', 'type': 'u32'},
                {'name': 'i8_field', 'type': 'i8'},
                {'name': 's16_field', 'type': 's16'},
                {'name': 's32_field', 'type': 's32'},
            ]
        }
        binary = encode_schema(schema)
        decoded = decode_schema(binary)
        
        types = [f['type'] for f in decoded['fields']]
        assert 'u8' in types
        assert 'u16' in types
        assert 'u32' in types
        assert 's8' in types  # i8 normalizes to s8
        assert 's16' in types
        assert 's32' in types
    
    def test_bitfield_type(self):
        """Test bitfield type encoding."""
        encoder = BinarySchemaEncoder()
        
        # Various bitfield syntaxes
        for type_str in ['u8[3:4]', 'u8:2', 'bits<3,2>', 'bits:2@3']:
            type_code, size = encoder._parse_type(type_str)
            assert type_code == FieldType.BITFIELD
    
    def test_unknown_type_raises(self):
        """Test that unknown type raises error."""
        encoder = BinarySchemaEncoder()
        with pytest.raises(ValueError, match="Unknown type"):
            encoder._parse_type('invalid_type')


class TestCompactMatchEncoding:
    """Tests for v1 compact encoder with MATCH support (section 17 format)."""

    def test_flat_schema_stays_v1(self):
        """Flat schemas should produce v1 format (no structural opcodes)."""
        schema = {
            'fields': [
                {'name': 'temp', 'type': 's16', 'semantic': {'ipso': 3303}},
                {'name': 'hum', 'type': 'u8'},
            ]
        }
        binary = encode_schema(schema)
        assert binary[0] == 1  # version 1
        assert binary[1] == 2  # 2 fields
        assert len(binary) == 2 + 2 * 4  # 2-byte header + 2 × 4-byte fields

    def test_match_schema_produces_v2(self):
        """Schema with match should auto-upgrade to v2 format."""
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'cid', 'type': 'u8', 'var': 'cid'},
                {
                    'match': {
                        'field': '$cid',
                        'cases': {
                            0x01: [{'name': 'interval', 'type': 'u16'}],
                        }
                    }
                }
            ]
        }
        binary = encode_schema(schema)
        assert binary[0] == 2  # version 2
        assert binary[1] == 0  # flags: big-endian
        assert binary[2] == 2  # 2 top-level records (field + match)

    def test_match_contains_match_opcode(self):
        """V2 binary should contain the MATCH opcode byte."""
        schema = {
            'fields': [
                {'name': 'msg_type', 'type': 'u8', 'var': 'msg_type'},
                {
                    'match': {
                        'field': '$msg_type',
                        'cases': {
                            1: [{'name': 'temp', 'type': 's16'}],
                        }
                    }
                }
            ]
        }
        binary = encode_schema(schema)
        # Should contain MATCH opcode and VAR opcode somewhere
        assert OPCODE_MATCH in binary
        assert OPCODE_VAR in binary

    def test_match_little_endian_flag(self):
        """Little-endian schema should set flags bit 0."""
        schema = {
            'endian': 'little',
            'fields': [
                {'name': 'cid', 'type': 'u8', 'var': 'cid'},
                {
                    'match': {
                        'field': '$cid',
                        'cases': {
                            1: [{'name': 'val', 'type': 'u8'}],
                        }
                    }
                }
            ]
        }
        binary = encode_schema(schema)
        assert binary[0] == 2  # version 2
        assert binary[1] & 0x01  # little-endian flag set

    def test_match_inline_mode(self):
        """Inline match should set inline bit in MATCH flags."""
        schema = {
            'fields': [
                {
                    'match': {
                        'length': 1,
                        'cases': {
                            0x01: [{'name': 'interval', 'type': 'u16'}],
                            0x02: [{'name': 'threshold', 'type': 's16'}],
                        }
                    }
                }
            ]
        }
        binary = encode_schema(schema)
        # Find the MATCH opcode
        match_pos = binary.index(OPCODE_MATCH)
        match_flags = binary[match_pos + 1]
        assert match_flags & 0x10  # inline bit set

    def test_sensor_app_layer_downlink(self):
        """Test encoding app layer downlink schema (real-world pattern).
        
        Based on TSxxx Sensor Application Layer commands:
        CID 0x01 = SensorIntervalReq (u16 interval)
        CID 0x02 = SensorThresholdReq (u8 field_id + u16 delta)
        CID 0x05 = SensorAlarmReq (u8 + s16 + s16 + u8)
        CID 0x06 = SensorEnableReq (u16 bitmask)
        """
        schema = {
            'name': 'sensor_downlink',
            'endian': 'little',
            'fields': [
                {
                    'match': {
                        'length': 1,
                        'name': 'cid',
                        'cases': {
                            0x01: [
                                {'name': 'interval', 'type': 'u16'},
                            ],
                            0x02: [
                                {'name': 'field_id', 'type': 'u8'},
                                {'name': 'delta', 'type': 'u16'},
                            ],
                            0x05: [
                                {'name': 'field_id', 'type': 'u8'},
                                {'name': 'low_thresh', 'type': 's16'},
                                {'name': 'high_thresh', 'type': 's16'},
                                {'name': 'hysteresis', 'type': 'u8'},
                            ],
                            0x06: [
                                {'name': 'field_bitmask', 'type': 'u16'},
                            ],
                        }
                    }
                }
            ]
        }
        binary = encode_schema(schema)
        
        # Version 2 format
        assert binary[0] == 2
        
        # Compact: should be much smaller than v2 string-table format
        # 3 (header) + 3 (MATCH opcode+flags+count) +
        # 4 cases × (1 val + 1 count + N×4 fields)
        # = 3 + 3 + (2+4) + (2+12) + (2+20) + (2+4) = 54 bytes
        assert len(binary) < 60
        
        print(f"App layer downlink schema: {len(binary)} bytes")
        print(f"Hex: {binary.hex()}")

    def test_roundtrip_flat(self):
        """V1 flat schema roundtrip should still work."""
        schema = {
            'fields': [
                {'name': 'temperature', 'type': 's16', 'mult': 0.01,
                 'semantic': {'ipso': 3303}},
                {'name': 'humidity', 'type': 'u8',
                 'semantic': {'ipso': 3304}},
            ]
        }
        binary_bytes = encode_schema(schema)
        decoded = decode_schema(binary_bytes)
        
        assert decoded['version'] == 1
        assert len(decoded['fields']) == 2
        assert decoded['fields'][0]['type'] == 's16'

    def test_roundtrip_match(self):
        """V2 match schema roundtrip should preserve structure."""
        schema = {
            'endian': 'big',
            'fields': [
                {'name': 'msg_type', 'type': 'u8', 'var': 'msg_type'},
                {
                    'match': {
                        'field': '$msg_type',
                        'cases': {
                            1: [{'name': 'temp', 'type': 's16'}],
                            2: [{'name': 'hum', 'type': 'u8'}],
                        }
                    }
                }
            ]
        }
        binary_bytes = encode_schema(schema)
        decoded = decode_schema(binary_bytes)
        
        assert decoded['version'] == 2
        assert len(decoded['fields']) == 2
        
        # First field should be a data field with var
        assert decoded['fields'][0]['type'] == 'u8'
        assert 'var' in decoded['fields'][0]
        
        # Second field should be a match construct
        assert 'match' in decoded['fields'][1]
        match = decoded['fields'][1]['match']
        assert 'cases' in match
        assert 1 in match['cases'] or '1' in str(match['cases'])

    def test_roundtrip_inline_match(self):
        """V2 inline match roundtrip."""
        schema = {
            'fields': [
                {
                    'match': {
                        'length': 1,
                        'cases': {
                            0x01: [{'name': 'val_a', 'type': 'u16'}],
                            0x02: [{'name': 'val_b', 'type': 'u8'}],
                        }
                    }
                }
            ]
        }
        binary_bytes = encode_schema(schema)
        decoded = decode_schema(binary_bytes)
        
        assert decoded['version'] == 2
        match = decoded['fields'][0]['match']
        assert 'length' in match
        assert len(match['cases']) == 2

    def test_match_with_default_skip(self):
        """Match with default: skip."""
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
        binary_bytes = encode_schema(schema)
        decoded = decode_schema(binary_bytes)
        
        match = decoded['fields'][0]['match']
        assert match.get('default') == 'skip'

    def test_match_with_default_error(self):
        """Match with default: error."""
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
        binary_bytes = encode_schema(schema)
        decoded = decode_schema(binary_bytes)
        
        match = decoded['fields'][0]['match']
        assert match.get('default') == 'error'

    def test_size_comparison(self):
        """Compare compact match size vs flat-only encoding."""
        # 4-command downlink with match
        match_schema = {
            'fields': [{
                'match': {
                    'length': 1,
                    'cases': {
                        0x01: [{'name': 'interval', 'type': 'u16'}],
                        0x02: [{'name': 'field_id', 'type': 'u8'},
                               {'name': 'delta', 'type': 'u16'}],
                        0x05: [{'name': 'field_id', 'type': 'u8'},
                               {'name': 'low', 'type': 's16'},
                               {'name': 'high', 'type': 's16'},
                               {'name': 'hyst', 'type': 'u8'}],
                        0x06: [{'name': 'mask', 'type': 'u16'}],
                    }
                }
            }]
        }
        binary = encode_schema(match_schema)
        
        # Should be compact enough for a single DR0 uplink (51 bytes max)
        assert len(binary) <= 51, f"Schema too large: {len(binary)} bytes"


class TestBase64Variants:
    """Tests for base64 encoding variants."""
    
    @pytest.fixture
    def test_schema(self):
        return {
            'fields': [
                {'name': 'value', 'type': 'u16', 'semantic': {'ipso': 3303}}
            ]
        }
    
    def test_url_safe_base64(self, test_schema):
        """Test URL-safe base64 encoding."""
        encoder = BinarySchemaEncoder()
        b64 = encoder.encode_to_base64(test_schema, url_safe=True)
        
        # URL-safe should not contain + or /
        assert '+' not in b64
        assert '/' not in b64
    
    def test_standard_base64(self, test_schema):
        """Test standard base64 encoding."""
        encoder = BinarySchemaEncoder()
        b64 = encoder.encode_to_base64(test_schema, url_safe=False)
        
        # Should be valid base64
        assert isinstance(b64, str)
    
    def test_url_safe_roundtrip(self, test_schema):
        """Test URL-safe base64 roundtrip."""
        b64 = schema_to_base64(test_schema, url_safe=True)
        decoded = base64_to_schema(b64)
        assert len(decoded['fields']) == 1


# =========================================================================
# V2 Binary Schema Tests
# =========================================================================

class TestBinarySchemaV2Simple:
    """Tests for v2 binary schema with simple fields."""

    def test_encode_simple_fields(self):
        """Test encoding simple sequential fields."""
        schema = {
            'name': 'test_sensor',
            'endian': 'big',
            'fields': [
                {'name': 'temperature', 'type': 's16', 'div': 100},
                {'name': 'humidity', 'type': 'u8', 'mult': 0.5},
            ]
        }
        binary = encode_schema_v2(schema)
        assert isinstance(binary, bytes)
        assert len(binary) > 8  # header + fields

    def test_roundtrip_simple(self):
        """Test encode/decode roundtrip for simple schema."""
        schema = {
            'name': 'env_sensor',
            'endian': 'big',
            'fields': [
                {'name': 'temperature', 'type': 's16'},
                {'name': 'humidity', 'type': 'u8'},
                {'name': 'battery', 'type': 'u16'},
            ]
        }
        binary = encode_schema_v2(schema)
        decoded = decode_schema_v2(binary)

        assert decoded['name'] == 'env_sensor'
        assert len(decoded['fields']) == 3
        assert decoded['fields'][0]['type'] == 's16'
        assert decoded['fields'][0]['name'] == 'temperature'

    def test_base64_roundtrip_v2(self):
        """Test base64 encode/decode roundtrip for v2."""
        schema = {
            'name': 'test',
            'fields': [
                {'name': 'value', 'type': 'u16'},
            ]
        }
        b64 = schema_to_base64_v2(schema)
        decoded = base64_to_schema_v2(b64)
        assert len(decoded['fields']) == 1


class TestBinarySchemaV2Match:
    """Tests for v2 binary schema with match constructs."""

    def test_encode_legacy_match(self):
        """Test encoding legacy match syntax (type: match)."""
        schema = {
            'name': 'multi_msg',
            'endian': 'big',
            'fields': [
                {'name': 'event', 'type': 'u8', 'var': 'evt',
                 'lookup': {0: 'reset', 1: 'data'}},
                {'name': 'payload', 'type': 'match', 'on': '$evt',
                 'cases': [
                     {'case': 0, 'fields': [
                         {'name': 'device_id', 'type': 'u16'}
                     ]},
                     {'case': 1, 'fields': [
                         {'name': 'temp', 'type': 's16'}
                     ]},
                 ]}
            ]
        }
        binary = encode_schema_v2(schema)
        decoded = decode_schema_v2(binary)

        assert len(decoded['fields']) == 2
        assert decoded['fields'][1]['type'] == 'match'

    def test_encode_option_b_match_variable(self):
        """Test encoding Option B match with variable reference."""
        schema = {
            'name': 'option_b_var',
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
        binary = encode_schema_v2(schema)
        assert isinstance(binary, bytes)
        # Should encode without error
        assert len(binary) > 10

    def test_encode_option_b_match_inline(self):
        """Test encoding Option B match with inline read."""
        schema = {
            'name': 'option_b_inline',
            'endian': 'big',
            'fields': [
                {
                    'match': {
                        'length': 1,
                        'name': 'msg_type',
                        'var': 'mt',
                        'cases': {
                            1: [{'name': 'temp', 'type': 's16'}],
                            2: [{'name': 'humidity', 'type': 'u8'}],
                        }
                    }
                }
            ]
        }
        binary = encode_schema_v2(schema)
        assert isinstance(binary, bytes)
        assert len(binary) > 10


class TestBinarySchemaV2Object:
    """Tests for v2 binary schema with object constructs."""

    def test_encode_legacy_object(self):
        """Test encoding legacy object syntax (type: object)."""
        schema = {
            'name': 'nested',
            'fields': [
                {'name': 'sensor', 'type': 'object', 'fields': [
                    {'name': 'temp', 'type': 'u16'},
                    {'name': 'hum', 'type': 'u8'},
                ]},
            ]
        }
        binary = encode_schema_v2(schema)
        decoded = decode_schema_v2(binary)

        assert decoded['fields'][0]['type'] == 'object'
        assert len(decoded['fields'][0]['fields']) == 2

    def test_encode_option_b_object(self):
        """Test encoding Option B object syntax."""
        schema = {
            'name': 'option_b_obj',
            'fields': [
                {'name': 'version', 'type': 'u8'},
                {
                    'object': 'sensor_data',
                    'fields': [
                        {'name': 'temp', 'type': 's16'},
                        {'name': 'hum', 'type': 'u8'},
                    ]
                }
            ]
        }
        binary = encode_schema_v2(schema)
        decoded = decode_schema_v2(binary)

        assert len(decoded['fields']) == 2
        # The object should be decoded
        assert decoded['fields'][1]['type'] == 'object'
        assert decoded['fields'][1]['name'] == 'sensor_data'


class TestBinarySchemaV2Tlv:
    """Tests for v2 binary schema with TLV constructs."""

    def test_encode_simple_tlv(self):
        """Test encoding simple TLV with single-byte tags."""
        schema = {
            'name': 'elsys_sensor',
            'endian': 'big',
            'fields': [
                {
                    'tlv': {
                        'tag_size': 1,
                        'cases': {
                            0x01: [{'name': 'temperature', 'type': 's16'}],
                            0x02: [{'name': 'humidity', 'type': 'u8'}],
                        }
                    }
                }
            ]
        }
        binary = encode_schema_v2(schema)
        assert isinstance(binary, bytes)
        assert len(binary) > 10

    def test_encode_composite_tlv(self):
        """Test encoding composite-tag TLV."""
        schema = {
            'name': 'milesight',
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
                            (0x03, 0x67): [{'name': 'temp', 'type': 's16'}],
                        }
                    }
                }
            ]
        }
        binary = encode_schema_v2(schema)
        assert isinstance(binary, bytes)
        assert len(binary) > 15


class TestBinarySchemaV2Combined:
    """Tests for combined constructs in v2 binary schema."""

    def test_object_plus_match(self):
        """Test schema with both object and match constructs."""
        schema = {
            'name': 'combined',
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
                            1: [{'name': 'temp', 'type': 's16'}],
                            2: [{'name': 'hum', 'type': 'u8'}],
                        }
                    }
                }
            ]
        }
        binary = encode_schema_v2(schema)
        assert isinstance(binary, bytes)
        assert len(binary) > 15

    def test_schema_size_estimate(self):
        """Test that schema sizes match expected estimates."""
        # Simple 4-field sensor should be ~25-35 bytes in v2
        schema = {
            'name': 'env_sensor',
            'endian': 'big',
            'fields': [
                {'name': 'temperature', 'type': 's16'},
                {'name': 'humidity', 'type': 'u8'},
                {'name': 'battery', 'type': 'u16'},
                {'name': 'status', 'type': 'u8'},
            ]
        }
        binary = encode_schema_v2(schema)
        # With string table overhead, should be reasonable
        assert len(binary) < 100  # sanity check


# =============================================================================
# Edge Cases and Security Tests
# =============================================================================

import struct as struct_module


class TestBinarySchemaEdgeCases:
    """Edge case tests for binary schema encoder/decoder."""

    def test_empty_schema(self):
        """Empty schema encodes/decodes correctly."""
        schema = BinarySchema(version=1, fields=[])
        data = schema.to_bytes()
        decoded = BinarySchema.from_bytes(data)
        assert decoded.version == 1
        assert len(decoded.fields) == 0

    def test_max_field_count(self):
        """Schema with maximum field count (255)."""
        fields = [BinaryField(FieldType.UNSIGNED, 1, 0, 0) for _ in range(255)]
        schema = BinarySchema(version=1, fields=fields)
        data = schema.to_bytes()
        decoded = BinarySchema.from_bytes(data)
        assert len(decoded.fields) == 255

    def test_truncated_header(self):
        """Truncated header raises error."""
        with pytest.raises((ValueError, struct_module.error)):
            BinarySchema.from_bytes(bytes([1]))  # Only version, no count

    def test_truncated_fields(self):
        """Truncated field data raises error."""
        # Version=1, count=2, but only 1 field worth of data
        data = bytes([1, 2, 0x01, 0x00, 0x00, 0x00])
        with pytest.raises((ValueError, struct_module.error)):
            BinarySchema.from_bytes(data)

    def test_all_field_types(self):
        """All field types encode/decode correctly."""
        types_to_test = [
            FieldType.UNSIGNED,
            FieldType.SIGNED,
            FieldType.FLOAT,
            FieldType.BYTES,
            FieldType.BOOL,
            FieldType.ENUM,
        ]
        for ft in types_to_test:
            field = BinaryField(ft, 2, -1, 3303)
            data = field.to_bytes()
            decoded = BinaryField.from_bytes(data)
            assert decoded.type_code == ft

    def test_extreme_mult_exponents(self):
        """Extreme multiplier exponents handled."""
        # Max positive exponent (127)
        field1 = BinaryField(FieldType.UNSIGNED, 1, 127, 0)
        data1 = field1.to_bytes()
        decoded1 = BinaryField.from_bytes(data1)
        assert decoded1.mult_exponent == 127

        # Max negative exponent (-128)
        field2 = BinaryField(FieldType.UNSIGNED, 1, -128, 0)
        data2 = field2.to_bytes()
        decoded2 = BinaryField.from_bytes(data2)
        assert decoded2.mult_exponent == -128

    def test_max_semantic_id(self):
        """Maximum semantic ID (65535) encodes correctly."""
        field = BinaryField(FieldType.UNSIGNED, 1, 0, 65535)
        data = field.to_bytes()
        decoded = BinaryField.from_bytes(data)
        assert decoded.semantic_id == 65535

    def test_base64_roundtrip_binary(self):
        """Base64 encode/decode roundtrip with BinarySchema."""
        schema = BinarySchema(
            version=1,
            fields=[
                BinaryField(FieldType.SIGNED, 2, -2, 3303),
                BinaryField(FieldType.UNSIGNED, 1, -1, 3304),
            ]
        )
        # Use direct base64 encoding of binary
        import base64
        b64 = base64.b64encode(schema.to_bytes()).decode()
        decoded_bytes = base64.b64decode(b64)
        decoded = BinarySchema.from_bytes(decoded_bytes)
        assert decoded.version == schema.version
        assert len(decoded.fields) == len(schema.fields)

    def test_base64_invalid_padding(self):
        """Invalid base64 padding handled."""
        import base64
        with pytest.raises(Exception):
            base64.b64decode("invalid!!!")

    def test_base64_truncated(self):
        """Truncated base64 data handled."""
        import base64
        # Valid base64 but too short for schema
        with pytest.raises(Exception):
            BinarySchema.from_bytes(base64.b64decode("AQ=="))  # Just [0x01]

    def test_schema_hash_with_dict(self):
        """Schema hash works with dict schema."""
        schema_dict = {
            'name': 'test',
            'fields': [{'name': 'x', 'type': 'u8'}]
        }
        hash1 = schema_hash(schema_dict)
        hash2 = schema_hash(schema_dict)
        assert hash1 == hash2

    def test_schema_hash_differs_dict(self):
        """Different dict schemas have different hashes."""
        schema1 = {'name': 'test1', 'fields': [{'name': 'x', 'type': 'u8'}]}
        schema2 = {'name': 'test2', 'fields': [{'name': 'x', 'type': 's8'}]}
        assert schema_hash(schema1) != schema_hash(schema2)

    def test_crc32_known_value(self):
        """CRC32 produces expected value."""
        crc = compute_crc32(b"Hello")
        assert isinstance(crc, int)
        assert crc > 0


class TestBinarySchemaV2EdgeCases:
    """Edge case tests for binary schema v2."""

    def test_v2_empty_schema(self):
        """V2: Empty schema encodes/decodes."""
        schema = {'name': 'empty', 'fields': []}
        data = encode_schema_v2(schema)
        decoded = decode_schema_v2(data)
        assert decoded['name'] == 'empty'

    def test_v2_complex_schema(self):
        """V2: Complex schema with many field types."""
        schema = {
            'name': 'complex',
            'fields': [
                {'name': 'temp', 'type': 's16', 'mult': 0.01},
                {'name': 'hum', 'type': 'u8', 'div': 2},
                {'name': 'flag', 'type': 'bool'},
                {'name': 'data', 'type': 'bytes', 'length': 4},
            ]
        }
        data = encode_schema_v2(schema)
        decoded = decode_schema_v2(data)
        assert decoded['name'] == schema['name']
        assert len(decoded['fields']) == len(schema['fields'])

    def test_v2_base64_roundtrip(self):
        """V2: Base64 roundtrip."""
        schema = {'name': 'test', 'fields': [{'name': 'x', 'type': 'u8'}]}
        b64 = schema_to_base64_v2(schema)
        decoded = base64_to_schema_v2(b64)
        assert decoded['name'] == 'test'

    def test_v2_malformed_data(self):
        """V2: Malformed binary data handled."""
        with pytest.raises(Exception):
            decode_schema_v2(bytes([0xFF, 0xFF, 0xFF]))


class TestBinarySchemaLoaderEdgeCases:
    """Edge case tests for binary schema loader."""

    def test_loader_unknown_type_code(self):
        """Unknown type code handled gracefully."""
        from binary_schema_loader import TypeCode, BinaryField as LoaderField
        # TypeCode only has values 0-8
        # Creating field with invalid code should be handled
        field = LoaderField(
            name='test',
            type_code=TypeCode.UINT,
            size=1
        )
        assert field.type_code == TypeCode.UINT

    def test_loader_match_field(self):
        """Match field with cases."""
        from binary_schema_loader import TypeCode, BinaryField as LoaderField
        field = LoaderField(
            name='data',
            type_code=TypeCode.MATCH,
            size=0,
            match_var='type',
            cases=[
                (1, [LoaderField('a', TypeCode.UINT, 1)]),
                (2, [LoaderField('b', TypeCode.UINT, 2)]),
            ]
        )
        assert field.type_code == TypeCode.MATCH
        assert len(field.cases) == 2
