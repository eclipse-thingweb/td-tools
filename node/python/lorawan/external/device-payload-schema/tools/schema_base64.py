#!/usr/bin/env python3
"""
schema_base64.py - Encode/decode Payload Schemas to/from base64

Useful for:
- OTA schema transfer
- QR code embedding
- URL-safe schema sharing
- Binary schema storage

Usage:
  # Encode YAML to base64
  python schema_base64.py encode schema.yaml
  python schema_base64.py encode schema.yaml -o schema.b64
  python schema_base64.py encode schema.yaml --compress
  
  # Decode base64 to YAML
  python schema_base64.py decode schema.b64
  python schema_base64.py decode schema.b64 -o schema.yaml
  python schema_base64.py decode "SGVsbG8gV29ybGQ="  # inline string
  
  # Info about encoded schema
  python schema_base64.py info schema.b64
"""

import argparse
import base64
import gzip
import json
import sys
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def encode_schema(input_path: Path, compress: bool = False, 
                  output_format: str = 'yaml') -> tuple[str, dict]:
    """Encode a schema file to base64."""
    content = input_path.read_text()
    
    # Parse to validate and get stats
    if HAS_YAML and input_path.suffix in ['.yaml', '.yml']:
        schema = yaml.safe_load(content)
        # Re-serialize for consistent formatting
        if output_format == 'json':
            content = json.dumps(schema, separators=(',', ':'))  # compact JSON
        else:
            content = yaml.dump(schema, default_flow_style=False)
    elif input_path.suffix == '.json':
        schema = json.loads(content)
        if output_format == 'json':
            content = json.dumps(schema, separators=(',', ':'))
    else:
        schema = {}
    
    raw_bytes = content.encode('utf-8')
    raw_size = len(raw_bytes)
    
    if compress:
        data = gzip.compress(raw_bytes, compresslevel=9)
        compressed_size = len(data)
    else:
        data = raw_bytes
        compressed_size = raw_size
    
    encoded = base64.b64encode(data).decode('ascii')
    
    stats = {
        'name': schema.get('name', 'unknown'),
        'raw_size': raw_size,
        'compressed_size': compressed_size,
        'base64_size': len(encoded),
        'compression_ratio': raw_size / compressed_size if compress else 1.0,
        'compressed': compress,
        'format': output_format,
    }
    
    return encoded, stats


def decode_schema(input_data: str, decompress: bool = None) -> tuple[str, dict]:
    """Decode base64 to schema content."""
    # Handle file path or inline base64
    if Path(input_data).exists():
        encoded = Path(input_data).read_text().strip()
    else:
        encoded = input_data.strip()
    
    data = base64.b64decode(encoded)
    
    # Auto-detect gzip
    is_gzipped = data[:2] == b'\x1f\x8b'
    if decompress is None:
        decompress = is_gzipped
    
    if decompress and is_gzipped:
        data = gzip.decompress(data)
    
    content = data.decode('utf-8')
    
    # Try to parse and get stats
    stats = {
        'base64_size': len(encoded),
        'decoded_size': len(content),
        'was_compressed': is_gzipped,
    }
    
    # Try YAML first, then JSON
    try:
        if HAS_YAML:
            schema = yaml.safe_load(content)
        else:
            schema = json.loads(content)
        stats['name'] = schema.get('name', 'unknown')
        stats['fields'] = len(schema.get('fields', []))
        stats['valid'] = True
    except:
        stats['valid'] = False
    
    return content, stats


def get_info(input_data: str) -> dict:
    """Get information about an encoded schema."""
    content, stats = decode_schema(input_data)
    
    if stats.get('valid') and HAS_YAML:
        schema = yaml.safe_load(content)
        stats['version'] = schema.get('version', 'unknown')
        stats['description'] = schema.get('description', '')[:100]
        
        # Count features
        def count_features(fields, counts=None):
            if counts is None:
                counts = {'fields': 0, 'matches': 0, 'lookups': 0, 'objects': 0}
            for f in (fields or []):
                counts['fields'] += 1
                if f.get('type') == 'match':
                    counts['matches'] += 1
                    for case in f.get('cases', []):
                        count_features(case.get('fields'), counts)
                elif f.get('type') == 'object':
                    counts['objects'] += 1
                    count_features(f.get('fields'), counts)
                if f.get('lookup'):
                    counts['lookups'] += 1
            return counts
        
        stats['features'] = count_features(schema.get('fields', []))
        stats['test_vectors'] = len(schema.get('test_vectors', []))
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Encode/decode Payload Schemas to/from base64'
    )
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Encode command
    enc = subparsers.add_parser('encode', help='Encode schema to base64')
    enc.add_argument('input', type=Path, help='Input schema file (YAML/JSON)')
    enc.add_argument('-o', '--output', type=Path, help='Output file (default: stdout)')
    enc.add_argument('-c', '--compress', action='store_true', help='Gzip compress before encoding')
    enc.add_argument('-j', '--json', action='store_true', help='Convert to compact JSON first')
    enc.add_argument('-q', '--quiet', action='store_true', help='Only output base64')
    
    # Decode command
    dec = subparsers.add_parser('decode', help='Decode base64 to schema')
    dec.add_argument('input', help='Input file or base64 string')
    dec.add_argument('-o', '--output', type=Path, help='Output file (default: stdout)')
    dec.add_argument('-j', '--json', action='store_true', help='Output as JSON')
    
    # Info command
    inf = subparsers.add_parser('info', help='Show info about encoded schema')
    inf.add_argument('input', help='Input file or base64 string')
    
    args = parser.parse_args()
    
    if args.command == 'encode':
        if not args.input.exists():
            print(f"Error: {args.input} not found", file=sys.stderr)
            sys.exit(1)
        
        fmt = 'json' if args.json else 'yaml'
        encoded, stats = encode_schema(args.input, args.compress, fmt)
        
        if args.output:
            args.output.write_text(encoded)
            if not args.quiet:
                print(f"Encoded to {args.output}", file=sys.stderr)
        else:
            if not args.quiet:
                print(f"# Schema: {stats['name']}", file=sys.stderr)
                print(f"# Raw: {stats['raw_size']} bytes", file=sys.stderr)
                if args.compress:
                    print(f"# Compressed: {stats['compressed_size']} bytes ({stats['compression_ratio']:.1f}x)", file=sys.stderr)
                print(f"# Base64: {stats['base64_size']} bytes", file=sys.stderr)
                print(file=sys.stderr)
            print(encoded)
    
    elif args.command == 'decode':
        content, stats = decode_schema(args.input)
        
        if args.json and HAS_YAML:
            schema = yaml.safe_load(content)
            content = json.dumps(schema, indent=2)
        
        if args.output:
            args.output.write_text(content)
            print(f"Decoded to {args.output}", file=sys.stderr)
        else:
            print(content)
    
    elif args.command == 'info':
        stats = get_info(args.input)
        print(f"Schema: {stats.get('name', 'unknown')}")
        print(f"Valid: {stats.get('valid', False)}")
        print(f"Base64 size: {stats.get('base64_size', 0)} bytes")
        print(f"Decoded size: {stats.get('decoded_size', 0)} bytes")
        print(f"Was compressed: {stats.get('was_compressed', False)}")
        if 'features' in stats:
            f = stats['features']
            print(f"Fields: {f['fields']} (matches: {f['matches']}, lookups: {f['lookups']}, objects: {f['objects']})")
        if stats.get('test_vectors'):
            print(f"Test vectors: {stats['test_vectors']}")


if __name__ == '__main__':
    main()
