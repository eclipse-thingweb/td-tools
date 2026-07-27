#!/usr/bin/env python3
"""
Decentlab Protocol V2 Codec → Payload Schema Schema Converter

Parses Decentlab JavaScript codecs (standard protocol v2 format) and generates
YAML payload schemas with flagged bitmask groups.

All Decentlab sensors follow the same pattern:
  - u8 protocol_version (always 2)
  - u16 device_id
  - u16 flags (bitmask for sensor group presence)
  - SENSORS[]: array of groups, each with length (count of u16 values) and convert functions

Usage:
    python convert_decentlab.py <codec.js>                    # Single file
    python convert_decentlab.py --batch <vendor_dir> -o <dir> # All Decentlab codecs
"""

import re
import sys
import os
import json
import argparse
from pathlib import Path


def extract_sensor_groups(js_code):
    """Extract SENSORS array from Decentlab JS codec."""
    groups = []
    
    # Find SENSORS array
    sensors_match = re.search(r'SENSORS:\s*\[(.*?)\]\s*,\s*\n\s*read_int', js_code, re.DOTALL)
    if not sensors_match:
        return None
    
    sensors_block = sensors_match.group(1)
    
    # Split into sensor group blocks by finding {length: N, values: [...]}
    group_pattern = re.compile(
        r'\{length:\s*(\d+)\s*,\s*values:\s*\[(.*?)\]\}',
        re.DOTALL
    )
    
    for gm in group_pattern.finditer(sensors_block):
        length = int(gm.group(1))
        values_block = gm.group(2)
        
        fields = []
        # Extract individual field definitions
        field_pattern = re.compile(
            r"\{name:\s*'([^']+)'\s*,"
            r"\s*displayName:\s*'([^']+)'\s*,"
            r"\s*convert:\s*function\s*\(x\)\s*\{\s*return\s*([^}]+)\}\s*"
            r"(?:,\s*unit:\s*'([^']*)')?\s*\}",
            re.DOTALL
        )
        
        for fm in field_pattern.finditer(values_block):
            name = fm.group(1)
            display_name = fm.group(2)
            convert_expr = fm.group(3).strip().rstrip(';').strip()
            unit = fm.group(4) if fm.group(4) else None
            
            field = parse_convert_expression(name, display_name, convert_expr, unit, length)
            fields.append(field)
        
        groups.append({
            'length': length,
            'fields': fields,
        })
    
    return groups


def parse_convert_expression(name, display_name, expr, unit, group_length):
    """Parse a Decentlab convert function expression into schema field definition."""
    field = {
        'name': name,
        'description': display_name,
    }
    if unit:
        field['unit'] = unit
    
    # Common patterns:
    # x[0] / 1000                           → u16, div: 1000
    # (x[0] - 32768) / 100                  → u16, add: -32768, div: 100  (or: s16, div: 100)
    # x[0] / 10 - 273.15                    → u16, div: 10, add: -273.15
    # (x[0] - 32768) / 10                   → s16, div: 10
    # x[0]                                  → u16 (raw)
    # x[0] + x[1] * 65536                   → u32 (two u16s combined)
    # (x[0] - 32768) / 100 * ... complex    → formula
    
    # Determine which x[i] indices are used
    indices = [int(m) for m in re.findall(r'x\[(\d+)\]', expr)]
    field['_x_indices'] = indices
    
    # Simple: x[N] / divisor
    m = re.match(r'x\[\d+\]\s*/\s*([\d.]+)\s*$', expr)
    if m:
        field['type'] = 'u16'
        field['div'] = _num(m.group(1))
        return field
    
    # Simple: x[N] * multiplier
    m = re.match(r'x\[\d+\]\s*\*\s*([\d.]+)\s*$', expr)
    if m:
        field['type'] = 'u16'
        field['mult'] = _num(m.group(1))
        return field
    
    # (x[N] - 32768) / divisor → signed interpretation
    m = re.match(r'\(x\[\d+\]\s*-\s*32768\)\s*/\s*([\d.]+)\s*$', expr)
    if m:
        field['type'] = 's16'
        field['div'] = _num(m.group(1))
        return field
    
    # (x[N] - 32768) / divisor * multiplier
    m = re.match(r'\(x\[\d+\]\s*-\s*32768\)\s*/\s*([\d.]+)\s*\*\s*([\d.]+)\s*$', expr)
    if m:
        field['type'] = 's16'
        d = _num(m.group(1))
        mult = _num(m.group(2))
        field['mult'] = mult / d if d != 0 else mult
        return field
    
    # x[N] / divisor - offset (e.g., x[0] / 10 - 273.15 for Kelvin→Celsius)
    m = re.match(r'x\[\d+\]\s*/\s*([\d.]+)\s*-\s*([\d.]+)\s*$', expr)
    if m:
        field['type'] = 'u16'
        field['div'] = _num(m.group(1))
        field['add'] = -_num(m.group(2))
        return field
    
    # x[N] / divisor + offset
    m = re.match(r'x\[\d+\]\s*/\s*([\d.]+)\s*\+\s*([\d.]+)\s*$', expr)
    if m:
        field['type'] = 'u16'
        field['div'] = _num(m.group(1))
        field['add'] = _num(m.group(2))
        return field
    
    # x[N] * multiplier - offset
    m = re.match(r'x\[\d+\]\s*\*\s*([\d.]+)\s*-\s*([\d.]+)\s*$', expr)
    if m:
        field['type'] = 'u16'
        field['mult'] = _num(m.group(1))
        field['add'] = -_num(m.group(2))
        return field
    
    # x[N] - offset (simple subtraction)
    m = re.match(r'x\[\d+\]\s*-\s*([\d.]+)\s*$', expr)
    if m:
        field['type'] = 'u16'
        field['add'] = -_num(m.group(1))
        return field
    
    # x[N] raw
    m = re.match(r'x\[\d+\]\s*$', expr)
    if m:
        field['type'] = 'u16'
        return field
    
    # Two-word combination: x[0] + x[1] * 65536 (u32 from two u16s)
    m = re.match(r'x\[\d+\]\s*\+\s*x\[\d+\]\s*\*\s*65536', expr)
    if m:
        field['type'] = 'u32'
        # Check for additional operations after the combination
        rest = expr[m.end():].strip()
        if rest:
            field['_formula'] = expr
        return field
    
    # Complex expression → use formula
    field['type'] = 'u16'
    field['_formula'] = expr
    return field


def _num(s):
    """Parse a number, returning int or float as appropriate."""
    f = float(s)
    if f == int(f) and '.' not in s:
        return int(f)
    return f


def extract_product_url(js_code):
    """Extract product URL from comment."""
    m = re.search(r'/\*\s*(https://[^\s*]+)', js_code)
    return m.group(1) if m else None


def generate_schema(js_code, filename):
    """Generate a Payload Schema YAML schema from a Decentlab codec."""
    groups = extract_sensor_groups(js_code)
    if groups is None:
        return None
    
    stem = Path(filename).stem
    product_url = extract_product_url(js_code)
    
    lines = []
    if product_url:
        lines.append(f'# {product_url}')
    lines.append(f'name: decentlab_{stem.replace("-", "_")}')
    lines.append('version: 2')
    lines.append('endian: big')
    lines.append('')
    lines.append('fields:')
    lines.append('  - name: protocol_version')
    lines.append('    type: u8')
    lines.append('  - name: device_id')
    lines.append('    type: u16')
    lines.append('  - name: flags')
    lines.append('    type: u16')
    lines.append('')
    lines.append('  - flagged:')
    lines.append('      field: flags')
    lines.append('      groups:')
    
    for bit, group in enumerate(groups):
        lines.append(f'        - bit: {bit}')
        lines.append(f'          fields:')
        
        for field in group['fields']:
            lines.append(f'            - name: {field["name"]}')
            lines.append(f'              type: {field["type"]}')
            
            if 'mult' in field:
                lines.append(f'              mult: {field["mult"]}')
            if 'div' in field:
                lines.append(f'              div: {field["div"]}')
            if 'add' in field:
                lines.append(f'              add: {field["add"]}')
            if field.get('unit'):
                lines.append(f'              unit: "{field["unit"]}"')
            if '_formula' in field:
                # Convert x[N] to $field_name references for simple cases,
                # or emit as formula comment
                formula = field['_formula']
                lines.append(f'              # formula: {formula}')
    
    lines.append('')
    return '\n'.join(lines)


def convert_single(js_path):
    """Convert a single Decentlab codec file."""
    with open(js_path, 'r') as f:
        js_code = f.read()
    
    schema = generate_schema(js_code, js_path)
    if schema is None:
        print(f"ERROR: Could not parse Decentlab codec from {js_path}", file=sys.stderr)
        return None
    return schema


def batch_convert(vendor_dir, output_dir):
    """Batch convert all Decentlab codecs in vendor directory."""
    decentlab_dir = Path(vendor_dir) / 'decentlab'
    if not decentlab_dir.exists():
        print(f"ERROR: {decentlab_dir} does not exist", file=sys.stderr)
        return
    
    js_files = sorted(decentlab_dir.glob('*.js'))
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    success = 0
    fail = 0
    formulas = 0
    
    for js_file in js_files:
        with open(js_file, 'r') as f:
            js_code = f.read()
        
        schema = generate_schema(js_code, js_file.name)
        if schema is None:
            print(f"  SKIP  {js_file.name} (not standard Decentlab v2 format)")
            fail += 1
            continue
        
        yaml_name = js_file.stem + '.yaml'
        yaml_path = out_path / yaml_name
        with open(yaml_path, 'w') as f:
            f.write(schema)
        
        has_formula = '# formula:' in schema
        if has_formula:
            formulas += 1
        
        print(f"  OK    {js_file.name} → {yaml_name}" + (" (has formulas)" if has_formula else ""))
        success += 1
    
    print(f"\nResults: {success} converted, {fail} skipped, {formulas} with formulas needing review")
    return success, fail


def main():
    parser = argparse.ArgumentParser(description='Convert Decentlab codecs to Payload Schema schemas')
    parser.add_argument('codec_file', nargs='?', help='Single JS codec file to convert')
    parser.add_argument('--batch', metavar='VENDOR_DIR', help='Batch convert all Decentlab codecs')
    parser.add_argument('-o', '--output', default='./decentlab-schemas', help='Output directory for batch mode')
    args = parser.parse_args()
    
    if args.batch:
        print(f"Batch converting Decentlab codecs from {args.batch}")
        print(f"Output: {args.output}\n")
        batch_convert(args.batch, args.output)
    elif args.codec_file:
        schema = convert_single(args.codec_file)
        if schema:
            print(schema)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
