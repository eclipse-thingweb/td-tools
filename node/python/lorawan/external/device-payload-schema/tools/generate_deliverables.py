#!/usr/bin/env python3
"""
generate_deliverables.py - Generate all TS013 deliverables from Payload Schema YAML

For each schema, generates:
  output/{vendor}/{device}/
    ├── schema.yaml          # PRIMARY: Payload Schema definition + test vectors
    ├── device.yaml          # Device metadata (TTN compatible)
    ├── codec.js             # TS013 JavaScript codec
    └── decoded.schema.json  # JSON Schema for decoded output

Usage:
    python tools/generate_deliverables.py schemas/decentlab/dl-5tm.yaml -o output/
    python tools/generate_deliverables.py schemas/ -o output/  # Process all
"""

import argparse
import json
import re
import shutil
import sys
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Import the TS013 generator
sys.path.insert(0, str(Path(__file__).parent))
from generate_ts013_codec import TS013Generator, load_schema


def extract_vendor_device(schema_path: Path) -> tuple:
    """Extract vendor and device from schema path."""
    parts = schema_path.parts
    if len(parts) >= 2:
        return parts[-2], schema_path.stem
    return "unknown", schema_path.stem


def infer_sensors_from_fields(schema: dict) -> List[str]:
    """Infer sensor types from field names."""
    sensors = set()
    field_sensor_map = {
        'temperature': 'temperature',
        'temp': 'temperature',
        'humidity': 'humidity',
        'hum': 'humidity',
        'pressure': 'barometer',
        'co2': 'co2',
        'battery': 'battery',
        'voltage': 'voltage',
        'current': 'current',
        'power': 'power',
        'light': 'light',
        'lux': 'light',
        'motion': 'motion',
        'pir': 'motion',
        'door': 'door',
        'water': 'water',
        'moisture': 'moisture',
        'soil': 'soil_moisture',
        'distance': 'distance',
        'level': 'level',
        'wind': 'wind',
        'rain': 'rain',
        'uv': 'uv',
        'gps': 'gps',
        'accelerometer': 'accelerometer',
        'gyroscope': 'gyroscope',
        'magnetometer': 'magnetometer',
    }
    
    def scan_fields(fields: list):
        for f in fields:
            name = f.get('name', '').lower()
            for key, sensor in field_sensor_map.items():
                if key in name:
                    sensors.add(sensor)
            # Recurse into nested structures
            if 'fields' in f:
                scan_fields(f['fields'])
            if 'flagged' in f:
                for group in f['flagged'].get('groups', []):
                    scan_fields(group.get('fields', []))
            if 'match' in f:
                for case_fields in f['match'].get('cases', {}).values():
                    if isinstance(case_fields, list):
                        scan_fields(case_fields)
    
    if 'fields' in schema:
        scan_fields(schema['fields'])
    elif 'ports' in schema:
        for port_def in schema['ports'].values():
            scan_fields(port_def.get('fields', []))
    
    return sorted(sensors) or ['sensor']


def generate_device_yaml(schema: dict, vendor: str, device: str) -> dict:
    """Generate TTN-compatible device.yaml metadata."""
    name = schema.get('name', device).replace('_', ' ').title()
    description = schema.get('description', f'{vendor.title()} {name} sensor')
    
    sensors = infer_sensors_from_fields(schema)
    
    device_meta = {
        'name': name,
        'description': description,
        'hardwareVersions': [
            {'version': '1', 'numeric': 1}
        ],
        'firmwareVersions': [
            {
                'version': '1.0.0',
                'numeric': 100,
                'hardwareVersions': ['1'],
                'profiles': {
                    'EU863-870': {
                        'id': f'profile-eu868',
                        'codec': f'{device}-codec'
                    },
                    'US902-928': {
                        'id': f'profile-us915',
                        'codec': f'{device}-codec'
                    },
                    'AS923': {
                        'id': f'profile-as923',
                        'codec': f'{device}-codec'
                    },
                    'AU915-928': {
                        'id': f'profile-au915',
                        'codec': f'{device}-codec'
                    }
                }
            }
        ],
        'sensors': sensors,
    }
    
    return device_meta


def collect_output_fields(schema: dict) -> Dict[str, dict]:
    """Collect all output field names and their metadata from schema."""
    fields_info = {}
    
    def add_field(name, field: dict):
        if not isinstance(name, str):
            return
        if name.startswith('_'):
            return
        
        info = {'type': 'number'}  # default
        
        ftype = field.get('type', 'u8')
        if ftype in ('ascii', 'hex', 'string', 'bytes'):
            info['type'] = 'string'
        elif ftype == 'bool':
            info['type'] = 'boolean'
        elif ftype == 'enum':
            values = field.get('values', {})
            if isinstance(values, dict):
                info['enum'] = list(values.values())
            elif isinstance(values, list):
                info['enum'] = values
        elif 'lookup' in field:
            info['enum'] = field['lookup']
        
        if 'unit' in field:
            info['unit'] = field['unit']
        if 'description' in field:
            info['description'] = field['description']
        
        fields_info[name] = info
    
    def scan_fields(fields: list):
        for f in fields:
            name = f.get('name')
            if name:
                add_field(name, f)
            
            # Recurse
            if 'fields' in f:
                scan_fields(f['fields'])
            if 'flagged' in f:
                for group in f['flagged'].get('groups', []):
                    scan_fields(group.get('fields', []))
            if 'match' in f:
                for case_fields in f['match'].get('cases', {}).values():
                    if isinstance(case_fields, list):
                        scan_fields(case_fields)
            if 'tlv' in f:
                for case_fields in f['tlv'].get('cases', {}).values():
                    if isinstance(case_fields, list):
                        scan_fields(case_fields)
            if 'byte_group' in f:
                bg = f['byte_group']
                if isinstance(bg, list):
                    scan_fields(bg)
                elif isinstance(bg, dict) and 'fields' in bg:
                    scan_fields(bg['fields'])
    
    if 'fields' in schema:
        scan_fields(schema['fields'])
    elif 'ports' in schema:
        for port_def in schema['ports'].values():
            scan_fields(port_def.get('fields', []))
    
    return fields_info


def generate_decoded_schema(schema: dict, name: str) -> dict:
    """Generate JSON Schema for decoded output validation."""
    fields_info = collect_output_fields(schema)
    
    properties = {}
    for field_name, info in fields_info.items():
        prop = {}
        
        if 'enum' in info:
            prop['enum'] = info['enum']
        elif info['type'] == 'string':
            prop['type'] = 'string'
        elif info['type'] == 'boolean':
            prop['type'] = 'boolean'
        else:
            prop['type'] = 'number'
        
        if 'unit' in info:
            prop['description'] = f"Unit: {info['unit']}"
        if 'description' in info:
            prop['description'] = info.get('description', '')
        
        properties[field_name] = prop
    
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": f"https://lorawan-schema.org/decoded/{name}",
        "title": f"{name} Decoded Output",
        "description": f"JSON Schema for validating decoded output from {name} sensor",
        "type": "object",
        "properties": properties,
        "additionalProperties": True
    }


def process_schema(schema_path: Path, output_dir: Path, verbose: bool = True) -> bool:
    """Process a single schema file and generate all deliverables."""
    try:
        schema = load_schema(schema_path)
        if not isinstance(schema, dict):
            return False
        if 'fields' not in schema and 'ports' not in schema:
            return False
        
        vendor, device = extract_vendor_device(schema_path)
        
        # Create output directory
        out_path = output_dir / vendor / device
        out_path.mkdir(parents=True, exist_ok=True)
        
        # 1. Copy schema.yaml (the primary deliverable)
        schema_out = out_path / 'schema.yaml'
        shutil.copy2(schema_path, schema_out)
        if verbose:
            print(f"  schema.yaml")
        
        # 2. Generate device.yaml
        device_meta = generate_device_yaml(schema, vendor, device)
        device_out = out_path / 'device.yaml'
        with open(device_out, 'w') as f:
            yaml.dump(device_meta, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        if verbose:
            print(f"  device.yaml")
        
        # 3. Generate codec.js
        gen = TS013Generator(schema, schema_path.name)
        js_code = gen.generate()
        codec_out = out_path / 'codec.js'
        codec_out.write_text(js_code)
        if verbose:
            print(f"  codec.js")
        
        # 4. Generate decoded.schema.json
        decoded_schema = generate_decoded_schema(schema, schema.get('name', device))
        decoded_out = out_path / 'decoded.schema.json'
        with open(decoded_out, 'w') as f:
            json.dump(decoded_schema, f, indent=2)
            f.write('\n')
        if verbose:
            print(f"  decoded.schema.json")
        
        return True
        
    except Exception as e:
        print(f"Error processing {schema_path}: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Generate TS013 deliverables from Payload Schema YAML'
    )
    parser.add_argument('input', help='Schema file or directory')
    parser.add_argument('-o', '--output', required=True, help='Output directory')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be generated')
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_dir = Path(args.output)
    
    if input_path.is_file():
        files = [input_path]
    else:
        # Recursively find all YAML files
        files = sorted(list(input_path.rglob('*.yaml')) + list(input_path.rglob('*.yml')))
        # Filter out non-schema files
        files = [f for f in files if f.stem.lower() not in ('readme', 'index')]
    
    if args.dry_run:
        print(f"Would process {len(files)} schema files:")
        for f in files:
            vendor, device = extract_vendor_device(f)
            print(f"  {vendor}/{device}/")
        return
    
    success = 0
    failed = 0
    
    for schema_path in files:
        vendor, device = extract_vendor_device(schema_path)
        print(f"{vendor}/{device}/")
        
        if process_schema(schema_path, output_dir, verbose=args.verbose):
            success += 1
        else:
            failed += 1
    
    print(f"\nProcessed: {success} success, {failed} failed")


if __name__ == '__main__':
    main()
