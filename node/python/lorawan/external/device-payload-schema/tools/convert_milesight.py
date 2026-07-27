#!/usr/bin/env python3
"""
Milesight IoT Codec → Payload Schema Schema Converter

Parses Milesight JavaScript codecs (TLV with channel_id + channel_type) and
generates YAML payload schemas with TLV construct.

Milesight pattern:
  - for (i = 0; i < bytes.length;) { channel_id = bytes[i++]; channel_type = bytes[i++]; ... }
  - Composite tag matching: if (channel_id === 0xNN && channel_type === 0xMM)
  - Fields: readUInt16LE, readInt16LE, readUInt32LE, bytes[i], etc.

Usage:
    python convert_milesight.py <codec.js>
    python convert_milesight.py --batch <vendor_dir> -o <dir>
"""

import re
import sys
import argparse
from pathlib import Path


def extract_tlv_cases(js_code):
    """Extract TLV case definitions from Milesight JS codec."""
    cases = []
    
    # Find the main decoder loop with channel_id/channel_type pattern
    # Match: if (channel_id === 0xNN && channel_type === 0xMM) { ... }
    # Also: else if (channel_id === 0xNN && channel_type === 0xMM) { ... }
    case_pattern = re.compile(
        r'(?:if|else\s+if)\s*\(\s*channel_id\s*===?\s*(0x[0-9a-fA-F]+)\s*&&\s*'
        r'channel_type\s*===?\s*(0x[0-9a-fA-F]+)\s*\)\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}',
        re.DOTALL
    )
    
    for cm in case_pattern.finditer(js_code):
        channel_id = int(cm.group(1), 16)
        channel_type = int(cm.group(2), 16)
        body = cm.group(3)
        
        # Extract field assignments from body
        fields = extract_case_fields(body)
        
        if fields:
            # Extract the comment on the line immediately before this case
            before = js_code[:cm.start()]
            comment = ''
            # Find the last comment line before the if/else if
            last_lines = before.rstrip().rsplit('\n', 3)
            for line in reversed(last_lines):
                line = line.strip()
                if line.startswith('//'):
                    comment = line.lstrip('/ ').strip()
                    break
                elif line and not line.startswith('}') and not line.startswith('else'):
                    break
            
            cases.append({
                'channel_id': channel_id,
                'channel_type': channel_type,
                'comment': comment,
                'fields': fields,
            })
    
    return cases


def extract_case_fields(body):
    """Extract field definitions from a TLV case body."""
    fields = []
    
    # Pattern: decoded.fieldName = expression (skip commented-out lines)
    field_pattern = re.compile(r'decoded\.(\w+)\s*=\s*([^;\n]+)')
    
    seen_names = set()
    for fm in field_pattern.finditer(body):
        # Skip if this assignment is inside a comment
        line_start = body.rfind('\n', 0, fm.start()) + 1
        line_prefix = body[line_start:fm.start()].strip()
        if line_prefix.startswith('//'):
            continue
        
        name = fm.group(1)
        expr = fm.group(2).strip()
        
        # Skip duplicates (e.g., Fahrenheit alternative)
        if name in seen_names:
            continue
        seen_names.add(name)
        
        field = parse_milesight_expr(name, expr)
        if field:
            fields.append(field)
    
    # Count bytes consumed (i += N)
    advance = re.findall(r'i\s*\+=\s*(\d+)', body)
    total_bytes = sum(int(a) for a in advance)
    
    return fields


def parse_milesight_expr(name, expr):
    """Parse a Milesight field expression into schema field definition."""
    field = {'name': name}
    
    # bytes[i] (single byte, unsigned)
    if re.match(r'bytes\[i\]$', expr):
        field['type'] = 'u8'
        return field
    
    # bytes[i] / N
    m = re.match(r'bytes\[i\]\s*/\s*([\d.]+)$', expr)
    if m:
        field['type'] = 'u8'
        field['div'] = _num(m.group(1))
        return field
    
    # readUInt16LE(...)
    if 'readUInt16LE' in expr:
        field['type'] = 'u16'
        # Check for division
        m = re.search(r'/\s*([\d.]+)', expr)
        if m:
            field['div'] = _num(m.group(1))
        # Check for multiplication
        m = re.search(r'\*\s*([\d.]+)', expr)
        if m:
            field['mult'] = _num(m.group(1))
        return field
    
    # readInt16LE(...)
    if 'readInt16LE' in expr:
        field['type'] = 's16'
        m = re.search(r'/\s*([\d.]+)', expr)
        if m:
            field['div'] = _num(m.group(1))
        m = re.search(r'\*\s*([\d.]+)', expr)
        if m:
            field['mult'] = _num(m.group(1))
        return field
    
    # readUInt32LE(...)
    if 'readUInt32LE' in expr:
        field['type'] = 'u32'
        m = re.search(r'/\s*([\d.]+)', expr)
        if m:
            field['div'] = _num(m.group(1))
        return field
    
    # readInt32LE(...)
    if 'readInt32LE' in expr:
        field['type'] = 's32'
        m = re.search(r'/\s*([\d.]+)', expr)
        if m:
            field['div'] = _num(m.group(1))
        return field
    
    # readFloatLE(...)
    if 'readFloatLE' in expr or 'readFloat' in expr:
        field['type'] = 'f32'
        return field
    
    # Multi-byte assembly: (bytes[i+1] << 8) | bytes[i]  (LE u16)
    if '<<' in expr and 'bytes[i' in expr:
        shifts = re.findall(r'<<\s*(\d+)', expr)
        if shifts:
            max_shift = max(int(s) for s in shifts)
            size = (max_shift // 8) + 1
            if size <= 2:
                field['type'] = 'u16'
            elif size <= 4:
                field['type'] = 'u32'
            else:
                field['type'] = f'u{size * 8}'
        else:
            field['type'] = 'u16'
        
        # Check for sign extension
        if '0x8000' in expr or '0x80' in expr or 'readInt' in expr:
            field['type'] = field['type'].replace('u', 's')
        
        m = re.search(r'/\s*([\d.]+)', expr)
        if m:
            field['div'] = _num(m.group(1))
        return field
    
    # Single byte with operations: bytes[i] & 0x0F, bytes[i] >> 4, etc.
    if re.match(r'bytes\[i(?:\s*\+\s*\d+)?\]', expr):
        field['type'] = 'u8'
        m = re.search(r'&\s*0x([0-9a-fA-F]+)', expr)
        if m:
            mask_val = int(m.group(1), 16)
            bits = bin(mask_val).count('1')
            field['_mask'] = mask_val
        m = re.search(r'/\s*([\d.]+)', expr)
        if m:
            field['div'] = _num(m.group(1))
        return field
    
    # Ternary or complex expression → just store raw
    field['type'] = 'u8'
    field['_raw'] = expr
    return field


def _num(s):
    f = float(s)
    if f == int(f) and '.' not in s:
        return int(f)
    return f


def detect_endian(js_code):
    """Detect endianness from helper functions."""
    if 'readUInt16LE' in js_code or 'readInt16LE' in js_code:
        return 'little'
    if 'readUInt16BE' in js_code or 'readInt16BE' in js_code:
        return 'big'
    # Check for LE assembly pattern: bytes[i] + (bytes[i+1] << 8) = LE
    if re.search(r'bytes\[i\]\s*(?:\+|\|)\s*\(?\s*bytes\[i\s*\+\s*1\]\s*<<\s*8', js_code):
        return 'little'
    return 'little'  # Milesight default is LE


def detect_product(js_code, filename):
    """Detect product name from code comments or filename."""
    m = re.search(r'@product\s+(.+)', js_code)
    if m:
        return m.group(1).strip()
    return Path(filename).stem


def generate_schema(js_code, filename):
    """Generate a Payload Schema YAML schema from a Milesight codec."""
    cases = extract_tlv_cases(js_code)
    if not cases:
        return None
    
    stem = Path(filename).stem
    product = detect_product(js_code, filename)
    endian = detect_endian(js_code)
    
    lines = []
    lines.append(f'# Milesight IoT {product}')
    lines.append(f'name: milesight_{stem.replace("-", "_")}')
    lines.append('version: 1')
    lines.append(f'endian: {endian}')
    lines.append('')
    lines.append('fields:')
    lines.append('  - tlv:')
    lines.append('      tag_fields:')
    lines.append('        - name: channel_id')
    lines.append('          type: u8')
    lines.append('        - name: channel_type')
    lines.append('          type: u8')
    lines.append('      tag_key: [channel_id, channel_type]')
    lines.append('      cases:')
    
    for case in cases:
        tag_key = f'[{case["channel_id"]}, {case["channel_type"]}]'
        comment = case.get('comment', '')
        if comment:
            lines.append(f'        # {comment}')
        lines.append(f'        "{tag_key}":')
        
        for field in case['fields']:
            lines.append(f'          - name: {field["name"]}')
            lines.append(f'            type: {field["type"]}')
            if 'div' in field:
                lines.append(f'            div: {field["div"]}')
            if 'mult' in field:
                lines.append(f'            mult: {field["mult"]}')
            if field.get('unit'):
                lines.append(f'            unit: "{field["unit"]}"')
            if '_raw' in field:
                lines.append(f'            # raw: {field["_raw"]}')
    
    lines.append('')
    return '\n'.join(lines)


def batch_convert(vendor_dir, output_dir):
    """Batch convert all Milesight codecs."""
    milesight_dir = Path(vendor_dir) / 'milesight-iot'
    if not milesight_dir.exists():
        print(f"ERROR: {milesight_dir} does not exist", file=sys.stderr)
        return
    
    js_files = sorted(f for f in milesight_dir.glob('*.js') if 'encoder' not in f.name.lower())
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    success = 0
    fail = 0
    
    for js_file in js_files:
        with open(js_file, 'r', encoding='utf-8', errors='ignore') as f:
            js_code = f.read()
        
        schema = generate_schema(js_code, js_file.name)
        if schema is None:
            print(f"  SKIP  {js_file.name} (no TLV cases found)")
            fail += 1
            continue
        
        yaml_name = js_file.stem + '.yaml'
        yaml_path = out_path / yaml_name
        with open(yaml_path, 'w') as f:
            f.write(schema)
        
        case_count = schema.count('- name:')
        print(f"  OK    {js_file.name} → {yaml_name} ({case_count} fields)")
        success += 1
    
    print(f"\nResults: {success} converted, {fail} skipped")
    return success, fail


def main():
    parser = argparse.ArgumentParser(description='Convert Milesight codecs to Payload Schema schemas')
    parser.add_argument('codec_file', nargs='?', help='Single JS codec file to convert')
    parser.add_argument('--batch', metavar='VENDOR_DIR', help='Batch convert all Milesight codecs')
    parser.add_argument('-o', '--output', default='./milesight-schemas', help='Output directory')
    args = parser.parse_args()
    
    if args.batch:
        print(f"Batch converting Milesight codecs from {args.batch}")
        print(f"Output: {args.output}\n")
        batch_convert(args.batch, args.output)
    elif args.codec_file:
        with open(args.codec_file, 'r') as f:
            js_code = f.read()
        schema = generate_schema(js_code, args.codec_file)
        if schema:
            print(schema)
        else:
            print("ERROR: Could not parse Milesight codec", file=sys.stderr)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
