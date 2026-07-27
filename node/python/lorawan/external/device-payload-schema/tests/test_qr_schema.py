"""
Tests for QR code schema utilities.
"""

import pytest
import sys
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))

from qr_schema import (
    QRSchemaGenerator, QRSchemaParser, QRCodeBuilder,
    DeviceCredentials, QRSchemaContent,
    generate_qr_content, parse_qr_content,
    QR_CAPACITY, QR_FIXED_OVERHEAD
)


class TestDeviceCredentials:
    """Tests for DeviceCredentials class."""
    
    def test_valid_credentials(self):
        """Test valid credential validation."""
        creds = DeviceCredentials(
            join_eui="0000000000000001",
            dev_eui="0102030405060708",
            app_key="000102030405060708090A0B0C0D0E0F"
        )
        assert creds.validate()
    
    def test_invalid_join_eui_short(self):
        """Test validation fails for short JoinEUI."""
        creds = DeviceCredentials(
            join_eui="00000001",  # Too short
            dev_eui="0102030405060708",
            app_key="000102030405060708090A0B0C0D0E0F"
        )
        assert not creds.validate()
    
    def test_invalid_dev_eui_non_hex(self):
        """Test validation fails for non-hex DevEUI."""
        creds = DeviceCredentials(
            join_eui="0000000000000001",
            dev_eui="010203040506070G",  # G is not hex
            app_key="000102030405060708090A0B0C0D0E0F"
        )
        assert not creds.validate()
    
    def test_invalid_app_key_long(self):
        """Test validation fails for long AppKey."""
        creds = DeviceCredentials(
            join_eui="0000000000000001",
            dev_eui="0102030405060708",
            app_key="000102030405060708090A0B0C0D0E0F00"  # Too long
        )
        assert not creds.validate()
    
    def test_lowercase_valid(self):
        """Test lowercase hex is valid."""
        creds = DeviceCredentials(
            join_eui="0000000000000001",
            dev_eui="0102030405060708",
            app_key="000102030405060708090a0b0c0d0e0f"  # Lowercase
        )
        assert creds.validate()


class TestQRSchemaGenerator:
    """Tests for QRSchemaGenerator class."""
    
    @pytest.fixture
    def generator(self):
        return QRSchemaGenerator()
    
    @pytest.fixture
    def test_schema(self):
        return {
            'name': 'env_sensor',
            'fields': [
                {'name': 'temperature', 'type': 's16', 'mult': 0.01,
                 'semantic': {'ipso': 3303}},
                {'name': 'humidity', 'type': 'u8',
                 'semantic': {'ipso': 3304}},
            ]
        }
    
    def test_generate_credentials_only(self, generator):
        """Test generating QR with credentials only."""
        content = generator.generate(
            join_eui="0000000000000001",
            dev_eui="0102030405060708",
            app_key="000102030405060708090A0B0C0D0E0F"
        )
        
        assert content.startswith("LW:1:")
        assert "0000000000000001" in content
        assert "0102030405060708" in content
        assert "SCHEMA" not in content
    
    def test_generate_with_embedded_schema(self, generator, test_schema):
        """Test generating QR with embedded schema."""
        content = generator.generate(
            join_eui="0000000000000001",
            dev_eui="0102030405060708",
            app_key="000102030405060708090A0B0C0D0E0F",
            schema=test_schema
        )
        
        assert ":SCHEMA:" in content
        parts = content.split(':')
        assert len(parts) == 7
    
    def test_generate_with_hash_reference(self, generator, test_schema):
        """Test generating QR with schema hash reference."""
        content = generator.generate(
            join_eui="0000000000000001",
            dev_eui="0102030405060708",
            app_key="000102030405060708090A0B0C0D0E0F",
            schema=test_schema,
            use_hash=True
        )
        
        assert ":SCHEMA_HASH:" in content
        parts = content.split(':')
        assert len(parts[6]) == 8  # 8 hex chars for hash
    
    def test_generate_uppercase_credentials(self, generator):
        """Test that credentials are uppercased."""
        content = generator.generate(
            join_eui="0000000000000001",
            dev_eui="0102030405060708",
            app_key="000102030405060708090a0b0c0d0e0f"  # Lowercase
        )
        
        assert "000102030405060708090A0B0C0D0E0F" in content
    
    def test_generate_invalid_credentials_raises(self, generator):
        """Test that invalid credentials raise error."""
        with pytest.raises(ValueError, match="Invalid credential"):
            generator.generate(
                join_eui="invalid",
                dev_eui="0102030405060708",
                app_key="000102030405060708090A0B0C0D0E0F"
            )
    
    def test_estimate_qr_version(self, generator, test_schema):
        """Test QR version estimation."""
        content = generator.generate(
            join_eui="0000000000000001",
            dev_eui="0102030405060708",
            app_key="000102030405060708090A0B0C0D0E0F",
            schema=test_schema
        )
        
        version = generator.estimate_qr_version(content)
        assert 1 <= version <= 10
    
    def test_max_fields_for_qr_version(self, generator):
        """Test max fields calculation."""
        max_v4 = generator.max_fields_for_qr_version(4)
        max_v5 = generator.max_fields_for_qr_version(5)
        
        assert max_v5 > max_v4
        assert max_v4 > 0
    
    def test_generate_with_qr_info(self, generator, test_schema):
        """Test generating with QR info."""
        content, info = generator.generate_with_qr_info(
            join_eui="0000000000000001",
            dev_eui="0102030405060708",
            app_key="000102030405060708090A0B0C0D0E0F",
            schema=test_schema
        )
        
        assert 'content_length' in info
        assert 'qr_version' in info
        assert 'has_schema' in info
        assert info['has_schema'] is True
        assert 'field_count' in info


class TestQRSchemaParser:
    """Tests for QRSchemaParser class."""
    
    @pytest.fixture
    def parser(self):
        return QRSchemaParser()
    
    @pytest.fixture
    def valid_content(self):
        return "LW:1:0000000000000001:0102030405060708:000102030405060708090A0B0C0D0E0F"
    
    def test_parse_credentials_only(self, parser, valid_content):
        """Test parsing credentials-only QR."""
        result = parser.parse(valid_content)
        
        assert result.version == 1
        assert result.credentials.join_eui == "0000000000000001"
        assert result.credentials.dev_eui == "0102030405060708"
        assert result.schema is None
        assert result.schema_hash is None
    
    def test_parse_with_embedded_schema(self, parser):
        """Test parsing QR with embedded schema."""
        # Generate a valid content with schema
        gen = QRSchemaGenerator()
        schema = {'fields': [{'name': 'temp', 'type': 'u16'}]}
        content = gen.generate(
            join_eui="0000000000000001",
            dev_eui="0102030405060708",
            app_key="000102030405060708090A0B0C0D0E0F",
            schema=schema
        )
        
        result = parser.parse(content)
        
        assert result.has_embedded_schema
        assert result.schema is not None
        assert 'fields' in result.schema
    
    def test_parse_with_hash_reference(self, parser):
        """Test parsing QR with hash reference."""
        content = "LW:1:0000000000000001:0102030405060708:000102030405060708090A0B0C0D0E0F:SCHEMA_HASH:a1b2c3d4"
        
        result = parser.parse(content)
        
        assert not result.has_embedded_schema
        assert result.schema is None
        assert result.schema_hash == 0xa1b2c3d4
    
    def test_parse_invalid_format_short(self, parser):
        """Test parsing invalid short content."""
        with pytest.raises(ValueError, match="too few parts"):
            parser.parse("LW:1:ABC")
    
    def test_parse_invalid_format_prefix(self, parser):
        """Test parsing invalid prefix."""
        with pytest.raises(ValueError, match="must start with 'LW'"):
            parser.parse("XX:1:0000000000000001:0102030405060708:000102030405060708090A0B0C0D0E0F")
    
    def test_parse_invalid_version(self, parser):
        """Test parsing unsupported version."""
        with pytest.raises(ValueError, match="Unsupported"):
            parser.parse("LW:2:0000000000000001:0102030405060708:000102030405060708090A0B0C0D0E0F")
    
    def test_parse_invalid_credentials(self, parser):
        """Test parsing invalid credentials."""
        with pytest.raises(ValueError, match="Invalid credentials"):
            parser.parse("LW:1:INVALID:0102030405060708:000102030405060708090A0B0C0D0E0F")
    
    def test_validate_valid(self, parser, valid_content):
        """Test validation of valid content."""
        is_valid, error = parser.validate(valid_content)
        assert is_valid
        assert error is None
    
    def test_validate_invalid(self, parser):
        """Test validation of invalid content."""
        is_valid, error = parser.validate("invalid content")
        assert not is_valid
        assert error is not None


class TestQRCodeBuilder:
    """Tests for QRCodeBuilder class."""
    
    @pytest.fixture
    def builder(self):
        return QRCodeBuilder()
    
    @pytest.fixture
    def test_schema(self):
        return {
            'fields': [
                {'name': 'temp', 'type': 's16'},
                {'name': 'hum', 'type': 'u8'},
            ]
        }
    
    def test_build_credentials_only(self, builder):
        """Test building credentials-only QR."""
        result = builder.build(
            dev_eui="0102030405060708",
            app_key="000102030405060708090A0B0C0D0E0F"
        )
        
        assert result['strategy'] == 'credentials_only'
        assert 'content' in result
        assert 'qr_version' in result
    
    def test_build_with_schema_embedded(self, builder, test_schema):
        """Test building with embedded schema."""
        result = builder.build(
            dev_eui="0102030405060708",
            app_key="000102030405060708090A0B0C0D0E0F",
            schema=test_schema
        )
        
        assert result['strategy'] == 'embedded'
        assert result['schema_fields'] == 2
    
    def test_build_falls_back_to_hash(self, builder):
        """Test fallback to hash for large schemas."""
        # Create large schema that won't fit in version 1
        large_schema = {
            'fields': [
                {'name': f'field_{i}', 'type': 'u16', 'semantic': {'ipso': 3300+i}}
                for i in range(50)
            ]
        }
        
        result = builder.build(
            dev_eui="0102030405060708",
            app_key="000102030405060708090A0B0C0D0E0F",
            schema=large_schema,
            max_qr_version=3  # Force small version
        )
        
        assert result['strategy'] == 'hash_reference'
        assert 'schema_hash' in result
    
    def test_build_uppercase_euis(self, builder):
        """Test that EUIs are uppercased."""
        result = builder.build(
            dev_eui="0102030405060708",
            app_key="000102030405060708090a0b0c0d0e0f"  # Lowercase
        )
        
        assert result['app_key'] == "000102030405060708090A0B0C0D0E0F"


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""
    
    @pytest.fixture
    def test_schema(self):
        return {
            'fields': [
                {'name': 'value', 'type': 'u16'}
            ]
        }
    
    def test_generate_qr_content(self, test_schema):
        """Test generate_qr_content function."""
        content = generate_qr_content(
            dev_eui="0102030405060708",
            app_key="000102030405060708090A0B0C0D0E0F",
            schema=test_schema
        )
        
        assert content.startswith("LW:1:")
        assert ":SCHEMA:" in content
    
    def test_parse_qr_content(self):
        """Test parse_qr_content function."""
        content = "LW:1:0000000000000001:0102030405060708:000102030405060708090A0B0C0D0E0F"
        result = parse_qr_content(content)
        
        assert isinstance(result, QRSchemaContent)
        assert result.credentials.dev_eui == "0102030405060708"
    
    def test_roundtrip(self, test_schema):
        """Test generate/parse roundtrip."""
        content = generate_qr_content(
            dev_eui="0102030405060708",
            app_key="000102030405060708090A0B0C0D0E0F",
            schema=test_schema,
            join_eui="AAAAAAAAAAAAAAAA"
        )
        
        result = parse_qr_content(content)
        
        assert result.credentials.join_eui == "AAAAAAAAAAAAAAAA"
        assert result.credentials.dev_eui == "0102030405060708"
        assert result.has_embedded_schema
        assert len(result.schema['fields']) == 1


class TestQRCapacity:
    """Tests for QR code capacity calculations."""
    
    def test_qr_capacity_defined(self):
        """Test QR capacity constants are defined."""
        assert QR_CAPACITY[1] == 34
        assert QR_CAPACITY[4] == 149
    
    def test_fixed_overhead(self):
        """Test fixed overhead constant."""
        # LW:1: + 16 + : + 16 + : + 32 + :SCHEMA: = 79
        assert QR_FIXED_OVERHEAD == 79
    
    def test_capacity_increases_with_version(self):
        """Test capacity increases with version."""
        for v in range(1, 10):
            assert QR_CAPACITY.get(v+1, 999) >= QR_CAPACITY.get(v, 0)


class TestQRSchemaContentMethods:
    """Tests for QRSchemaContent methods."""
    
    def test_has_embedded_schema_true(self):
        """Test has_embedded_schema property when schema present."""
        content = QRSchemaContent(
            version=1,
            credentials=DeviceCredentials("A"*16, "B"*16, "C"*32),
            schema={'fields': []},
            raw_content=""
        )
        assert content.has_embedded_schema is True
    
    def test_has_embedded_schema_false(self):
        """Test has_embedded_schema property when schema absent."""
        content = QRSchemaContent(
            version=1,
            credentials=DeviceCredentials("A"*16, "B"*16, "C"*32),
            schema_hash=0x12345678,
            raw_content=""
        )
        assert content.has_embedded_schema is False
    
    def test_to_qr_string(self):
        """Test to_qr_string returns raw content."""
        raw = "LW:1:test:content"
        content = QRSchemaContent(
            version=1,
            credentials=DeviceCredentials("A"*16, "B"*16, "C"*32),
            raw_content=raw
        )
        assert content.to_qr_string() == raw
