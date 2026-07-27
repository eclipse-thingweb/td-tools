#!/usr/bin/env python3
"""
qr_schema.py - QR Code Schema Embedding Utilities

Implements the QR code format for self-describing LoRaWAN devices
as defined in Payload Schema Section 17.

QR Code Format:
    LW:1:JOIN_EUI:DEV_EUI:APP_KEY:SCHEMA:base64_encoded_schema
    
    or with hash reference:
    LW:1:JOIN_EUI:DEV_EUI:APP_KEY:SCHEMA_HASH:xxxxxxxx

Usage:
    from qr_schema import QRSchemaGenerator, QRSchemaParser
    
    # Generate QR code content
    gen = QRSchemaGenerator()
    qr_content = gen.generate(
        join_eui="0000000000000001",
        dev_eui="0102030405060708",
        app_key="000102030405060708090A0B0C0D0E0F",
        schema=my_schema
    )
    
    # Parse QR code content
    parser = QRSchemaParser()
    result = parser.parse(qr_content)
"""

import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
from binary_schema import (
    BinarySchemaEncoder, BinarySchemaDecoder,
    schema_to_base64, base64_to_schema, schema_hash
)


# QR Code capacity by version (alphanumeric mode, M error correction)
QR_CAPACITY = {
    1: 34,
    2: 63,
    3: 101,
    4: 149,
    5: 202,
    6: 255,
    7: 293,
    8: 365,
    9: 432,
    10: 513,
}

# Fixed overhead in QR content
# LW:1: + JOIN_EUI + : + DEV_EUI + : + APP_KEY + :SCHEMA: = 5+16+1+16+1+32+8 = 79
QR_FIXED_OVERHEAD = 79


@dataclass
class DeviceCredentials:
    """LoRaWAN OTAA device credentials."""
    join_eui: str
    dev_eui: str
    app_key: str
    
    def validate(self) -> bool:
        """Validate credential format."""
        if not re.match(r'^[0-9A-Fa-f]{16}$', self.join_eui):
            return False
        if not re.match(r'^[0-9A-Fa-f]{16}$', self.dev_eui):
            return False
        if not re.match(r'^[0-9A-Fa-f]{32}$', self.app_key):
            return False
        return True


@dataclass
class QRSchemaContent:
    """Parsed QR code content."""
    version: int
    credentials: DeviceCredentials
    schema: Optional[Dict[str, Any]] = None
    schema_hash: Optional[int] = None
    raw_content: str = ""
    
    @property
    def has_embedded_schema(self) -> bool:
        """Check if schema is embedded (vs hash reference)."""
        return self.schema is not None
    
    def to_qr_string(self) -> str:
        """Convert back to QR string format."""
        return self.raw_content


class QRSchemaGenerator:
    """Generate QR code content with embedded schema."""
    
    def __init__(self):
        self.encoder = BinarySchemaEncoder()
    
    def generate(
        self,
        join_eui: str,
        dev_eui: str,
        app_key: str,
        schema: Optional[Dict[str, Any]] = None,
        use_hash: bool = False
    ) -> str:
        """
        Generate QR code content string.
        
        Args:
            join_eui: 16 hex chars
            dev_eui: 16 hex chars
            app_key: 32 hex chars
            schema: Schema dict to embed
            use_hash: Use hash reference instead of embedding
            
        Returns:
            QR code content string
        """
        # Validate credentials
        creds = DeviceCredentials(
            join_eui=join_eui.upper(),
            dev_eui=dev_eui.upper(),
            app_key=app_key.upper()
        )
        if not creds.validate():
            raise ValueError("Invalid credential format")
        
        # Build base content
        parts = [
            "LW",
            "1",  # Format version
            creds.join_eui,
            creds.dev_eui,
            creds.app_key,
        ]
        
        if schema:
            if use_hash:
                # Use hash reference
                h = schema_hash(schema)
                parts.append("SCHEMA_HASH")
                parts.append(f"{h:08x}")
            else:
                # Embed full schema
                b64 = schema_to_base64(schema, url_safe=True)
                parts.append("SCHEMA")
                parts.append(b64)
        
        return ':'.join(parts)
    
    def estimate_qr_version(self, content: str) -> int:
        """Estimate minimum QR code version needed."""
        length = len(content)
        for version, capacity in sorted(QR_CAPACITY.items()):
            if length <= capacity:
                return version
        return max(QR_CAPACITY.keys())
    
    def max_fields_for_qr_version(self, version: int) -> int:
        """Calculate max schema fields for a QR version."""
        capacity = QR_CAPACITY.get(version, 149)
        available = capacity - QR_FIXED_OVERHEAD
        # Each field is ~4 bytes binary = ~6 chars base64
        # Plus header overhead (~3 chars)
        return max(0, (available - 3) // 6)
    
    def generate_with_qr_info(
        self,
        join_eui: str,
        dev_eui: str,
        app_key: str,
        schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate QR content with size analysis.
        
        Returns:
            Tuple of (content, info_dict)
        """
        content = self.generate(join_eui, dev_eui, app_key, schema)
        
        info = {
            'content_length': len(content),
            'qr_version': self.estimate_qr_version(content),
            'has_schema': schema is not None,
        }
        
        if schema:
            info['field_count'] = len(schema.get('fields', []))
            binary = self.encoder.encode_to_bytes(schema)
            info['schema_bytes'] = len(binary)
            info['schema_hash'] = f"0x{schema_hash(schema):08X}"
        
        return content, info


class QRSchemaParser:
    """Parse QR code content to extract credentials and schema."""
    
    def __init__(self):
        self.decoder = BinarySchemaDecoder()
    
    def parse(self, content: str) -> QRSchemaContent:
        """
        Parse QR code content string.
        
        Args:
            content: QR code content
            
        Returns:
            QRSchemaContent with parsed data
        """
        parts = content.split(':')
        
        if len(parts) < 5:
            raise ValueError("Invalid QR format: too few parts")
        
        if parts[0] != "LW":
            raise ValueError("Invalid QR format: must start with 'LW'")
        
        version = int(parts[1])
        if version != 1:
            raise ValueError(f"Unsupported QR format version: {version}")
        
        credentials = DeviceCredentials(
            join_eui=parts[2],
            dev_eui=parts[3],
            app_key=parts[4]
        )
        
        if not credentials.validate():
            raise ValueError("Invalid credentials in QR code")
        
        result = QRSchemaContent(
            version=version,
            credentials=credentials,
            raw_content=content
        )
        
        # Check for schema
        if len(parts) >= 7:
            schema_type = parts[5]
            schema_data = parts[6]
            
            if schema_type == "SCHEMA":
                # Embedded schema
                result.schema = base64_to_schema(schema_data)
            elif schema_type == "SCHEMA_HASH":
                # Hash reference
                result.schema_hash = int(schema_data, 16)
        
        return result
    
    def validate(self, content: str) -> Tuple[bool, Optional[str]]:
        """
        Validate QR code content.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            self.parse(content)
            return True, None
        except Exception as e:
            return False, str(e)


class QRCodeBuilder:
    """High-level builder for LoRaWAN device QR codes."""
    
    def __init__(self):
        self.generator = QRSchemaGenerator()
    
    def build(
        self,
        dev_eui: str,
        app_key: str,
        join_eui: str = "0000000000000000",
        schema: Optional[Dict[str, Any]] = None,
        max_qr_version: int = 4
    ) -> Dict[str, Any]:
        """
        Build optimal QR code for device.
        
        Args:
            dev_eui: Device EUI
            app_key: Application key
            join_eui: Join EUI (default: zeros)
            schema: Optional schema to embed
            max_qr_version: Maximum acceptable QR version
            
        Returns:
            Dict with 'content', 'qr_version', 'strategy', etc.
        """
        result = {
            'dev_eui': dev_eui.upper(),
            'app_key': app_key.upper(),
            'join_eui': join_eui.upper(),
        }
        
        if schema:
            # Try embedding full schema
            content = self.generator.generate(
                join_eui, dev_eui, app_key, schema, use_hash=False
            )
            qr_version = self.generator.estimate_qr_version(content)
            
            if qr_version <= max_qr_version:
                result['content'] = content
                result['qr_version'] = qr_version
                result['strategy'] = 'embedded'
                result['schema_fields'] = len(schema.get('fields', []))
            else:
                # Fall back to hash reference
                content = self.generator.generate(
                    join_eui, dev_eui, app_key, schema, use_hash=True
                )
                result['content'] = content
                result['qr_version'] = self.generator.estimate_qr_version(content)
                result['strategy'] = 'hash_reference'
                result['schema_hash'] = f"0x{schema_hash(schema):08X}"
        else:
            # No schema
            content = self.generator.generate(join_eui, dev_eui, app_key)
            result['content'] = content
            result['qr_version'] = self.generator.estimate_qr_version(content)
            result['strategy'] = 'credentials_only'
        
        result['content_length'] = len(result['content'])
        return result


def generate_qr_content(
    dev_eui: str,
    app_key: str,
    schema: Optional[Dict[str, Any]] = None,
    join_eui: str = "0000000000000000"
) -> str:
    """Convenience function to generate QR content."""
    gen = QRSchemaGenerator()
    return gen.generate(join_eui, dev_eui, app_key, schema)


def parse_qr_content(content: str) -> QRSchemaContent:
    """Convenience function to parse QR content."""
    parser = QRSchemaParser()
    return parser.parse(content)


if __name__ == '__main__':
    # Demo
    print("=== QR Schema Generator Demo ===\n")
    
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
    
    builder = QRCodeBuilder()
    result = builder.build(
        dev_eui="0102030405060708",
        app_key="000102030405060708090A0B0C0D0E0F",
        schema=example_schema
    )
    
    print("Device credentials + embedded schema:")
    print(f"  Strategy: {result['strategy']}")
    print(f"  QR Version: {result['qr_version']}")
    print(f"  Content length: {result['content_length']} chars")
    print(f"\nQR Content:\n{result['content']}")
    
    # Parse it back
    print("\n--- Parsing back ---")
    parsed = parse_qr_content(result['content'])
    print(f"Version: {parsed.version}")
    print(f"DevEUI: {parsed.credentials.dev_eui}")
    print(f"Has embedded schema: {parsed.has_embedded_schema}")
    if parsed.schema:
        print(f"Schema fields: {len(parsed.schema.get('fields', []))}")
        for f in parsed.schema['fields']:
            print(f"  - {f['name']}: {f['type']}")
    
    # Show capacity table
    print("\n--- QR Code Capacity ---")
    gen = QRSchemaGenerator()
    print("| Version | Capacity | Max Fields |")
    print("|---------|----------|------------|")
    for v in range(1, 8):
        cap = QR_CAPACITY.get(v, 0)
        max_f = gen.max_fields_for_qr_version(v)
        print(f"|    {v}    |   {cap:3d}    |     {max_f:2d}     |")
