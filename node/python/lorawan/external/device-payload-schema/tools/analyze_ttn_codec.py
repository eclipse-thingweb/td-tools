#!/usr/bin/env python3
"""
TTN Codec Analyzer

Analyzes JavaScript codec files from TTN Device Repository and extracts
information to assist with schema conversion.

Extracts:
- Field names and byte positions
- Bitwise operations (masks, shifts)
- Math operations (mult, div, add)
- Lookup tables / enums
- Conditional structures (switch/if)
- Data types (signed, unsigned, sizes)

Usage:
    python analyze_ttn_codec.py <codec.js>
    python analyze_ttn_codec.py <codec.js> --yaml  # Output draft schema
"""

import re
import sys
import json
import argparse
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class FieldInfo:
    """Extracted field information."""
    name: str
    byte_indices: list = field(default_factory=list)
    bit_mask: Optional[int] = None
    bit_shift: Optional[int] = None
    multiplier: Optional[float] = None
    divisor: Optional[float] = None
    offset: Optional[float] = None
    signed: bool = False
    size: int = 1
    lookup: Optional[dict] = None
    condition: Optional[str] = None
    raw_expression: str = ""
    confidence: str = "high"  # high, medium, low
    notes: list = field(default_factory=list)


@dataclass
class CodecAnalysis:
    """Complete codec analysis result."""
    filename: str
    fports: list = field(default_factory=list)
    fields: list = field(default_factory=list)
    conditionals: list = field(default_factory=list)
    lookups: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    is_tlv: bool = False
    endian: str = "big"


def analyze_codec(js_code: str, filename: str = "codec.js") -> CodecAnalysis:
    """Analyze a TTN JavaScript codec."""
    analysis = CodecAnalysis(filename=filename)
    
    # Detect TLV pattern
    if re.search(r'channel_id|channel_type|data\[i\+\+\]|for\s*\([^)]*i\s*<\s*bytes\.length', js_code):
        analysis.is_tlv = True
        analysis.warnings.append("TLV/variable-length format detected - requires schema extension")
    
    # Detect endianness
    if 'LE' in js_code or 'little' in js_code.lower():
        analysis.endian = "little"
    
    # Extract fPort cases
    fport_matches = re.findall(r'case\s+(\d+):', js_code)
    analysis.fports = [int(p) for p in fport_matches]
    
    # Extract field assignments
    extract_fields(js_code, analysis)
    
    # Extract lookup tables
    extract_lookups(js_code, analysis)
    
    # Extract conditionals
    extract_conditionals(js_code, analysis)
    
    return analysis


def extract_fields(js_code: str, analysis: CodecAnalysis):
    """Extract field definitions from JS code."""
    
    # Pattern 1: decoded.fieldName = expression
    # or: data.fieldName = expression
    field_pattern = r'(?:decoded|data|obj)\.(\w+)\s*=\s*([^;]+);'
    
    for match in re.finditer(field_pattern, js_code):
        name = match.group(1)
        expr = match.group(2).strip()
        
        field = FieldInfo(name=name, raw_expression=expr)
        
        # Analyze the expression
        analyze_expression(expr, field)
        
        # Check for conditions
        context = get_context(js_code, match.start(), lines_before=5)
        if 'if' in context or 'case' in context or 'else' in context:
            field.condition = extract_condition(context)
            field.confidence = "medium"
        
        analysis.fields.append(field)
    
    # Pattern 2: Inline object syntax - fieldName: expression,
    # Common in return { data: { field: value, ... } }
    inline_pattern = r'^\s*(\w+):\s*([^,\n]+)[,\n]'
    
    for match in re.finditer(inline_pattern, js_code, re.MULTILINE):
        name = match.group(1)
        expr = match.group(2).strip()
        
        # Skip common non-field keys
        if name in ['data', 'errors', 'warnings', 'fPort', 'bytes', 'input', 'return']:
            continue
        
        # Skip if expression doesn't reference bytes
        if 'bytes[' not in expr and 'data[' not in expr:
            # Could be a literal or reference - still useful
            if not re.search(r'bytes|data|input', expr):
                continue
        
        field = FieldInfo(name=name, raw_expression=expr)
        analyze_expression(expr, field)
        
        # Check for conditions
        context = get_context(js_code, match.start(), lines_before=5)
        if 'if' in context or 'case' in context or 'else' in context:
            field.condition = extract_condition(context)
            field.confidence = "medium"
        
        # Avoid duplicates
        if not any(f.name == name and f.raw_expression == expr for f in analysis.fields):
            analysis.fields.append(field)


def analyze_expression(expr: str, field: FieldInfo):
    """Analyze a JavaScript expression to extract field properties."""
    
    # Detect byte access patterns
    # bytes[n], bytes[i + n], input.bytes[n]
    byte_matches = re.findall(r'bytes\[(\d+)\]', expr)
    field.byte_indices = [int(b) for b in byte_matches]
    
    # Detect multi-byte assembly: (bytes[n] << 8) | bytes[n+1]
    if '<<' in expr and '|' in expr:
        shifts = re.findall(r'<<\s*(\d+)', expr)
        if shifts:
            max_shift = max(int(s) for s in shifts)
            field.size = (max_shift // 8) + 1
    
    # Detect signed conversion patterns
    if any(p in expr for p in ['>> 16', '>> 24', '0x8000', '0x80', 'bin16dec', 'bin8dec', 'readInt16']):
        field.signed = True
    
    # Detect bit masking: & 0xFF, & 0x0F, etc.
    mask_match = re.search(r'&\s*0x([0-9A-Fa-f]+)', expr)
    if mask_match:
        field.bit_mask = int(mask_match.group(1), 16)
        # Calculate bit width from mask
        mask_val = field.bit_mask
        if mask_val in [0x01, 0x03, 0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF]:
            field.notes.append(f"Mask 0x{mask_val:X} = {bin(mask_val).count('1')} bits")
    
    # Detect bit shifting: >> n
    shift_match = re.search(r'>>\s*(\d+)', expr)
    if shift_match:
        field.bit_shift = int(shift_match.group(1))
    
    # Detect division: / 10, / 100, / 1000
    div_match = re.search(r'/\s*([\d.]+)', expr)
    if div_match:
        val = float(div_match.group(1))
        if val != 0:
            field.multiplier = 1.0 / val
            field.notes.append(f"Division by {val} → mult: {field.multiplier}")
    
    # Detect multiplication: * 0.01, * 0.1
    mult_match = re.search(r'\*\s*([\d.]+)', expr)
    if mult_match:
        field.multiplier = float(mult_match.group(1))
    
    # Detect offset/addition: + 25, - 32
    add_match = re.search(r'([+-])\s*(\d+)(?!\s*\])', expr)  # Avoid matching array indices
    if add_match:
        sign = 1 if add_match.group(1) == '+' else -1
        field.offset = sign * int(add_match.group(2))
    
    # Detect ternary/lookup inline
    if '?' in expr and ':' in expr:
        field.notes.append("Contains ternary - may need lookup table")
        field.confidence = "medium"
    
    # Detect parseFloat/toFixed
    if 'parseFloat' in expr or 'toFixed' in expr:
        field.notes.append("Floating point formatting detected")


def extract_lookups(js_code: str, analysis: CodecAnalysis):
    """Extract lookup tables and enums."""
    
    # Pattern: value === n ? "string" : ...
    ternary_pattern = r'(\w+)\s*===?\s*(\d+)\s*\?\s*["\']([^"\']+)["\']'
    
    lookups = {}
    for match in re.finditer(ternary_pattern, js_code):
        var_name = match.group(1)
        value = int(match.group(2))
        label = match.group(3)
        
        if var_name not in lookups:
            lookups[var_name] = {}
        lookups[var_name][value] = label
    
    # Pattern: case n: ... = "string"
    case_string_pattern = r'case\s+(\d+):[^}]*?["\']([^"\']+)["\']'
    for match in re.finditer(case_string_pattern, js_code, re.DOTALL):
        value = int(match.group(1))
        label = match.group(2)
        if 'switch_lookup' not in lookups:
            lookups['switch_lookup'] = {}
        lookups['switch_lookup'][value] = label
    
    analysis.lookups = lookups


def extract_conditionals(js_code: str, analysis: CodecAnalysis):
    """Extract conditional structures."""
    
    # switch statements
    switch_pattern = r'switch\s*\(([^)]+)\)\s*\{'
    for match in re.finditer(switch_pattern, js_code):
        var = match.group(1).strip()
        analysis.conditionals.append({
            'type': 'switch',
            'variable': var,
            'position': match.start()
        })
    
    # if statements with byte comparisons
    if_pattern = r'if\s*\(([^)]*bytes\[\d+\][^)]*)\)'
    for match in re.finditer(if_pattern, js_code):
        condition = match.group(1).strip()
        analysis.conditionals.append({
            'type': 'if',
            'condition': condition,
            'position': match.start()
        })


def get_context(js_code: str, position: int, lines_before: int = 3) -> str:
    """Get surrounding context for a position in code."""
    start = js_code.rfind('\n', 0, position)
    for _ in range(lines_before):
        prev = js_code.rfind('\n', 0, start)
        if prev == -1:
            break
        start = prev
    return js_code[start:position]


def extract_condition(context: str) -> Optional[str]:
    """Extract condition from context."""
    # Look for if conditions
    if_match = re.search(r'if\s*\(([^)]+)\)', context)
    if if_match:
        return if_match.group(1).strip()
    
    # Look for case values
    case_match = re.search(r'case\s+([^:]+):', context)
    if case_match:
        return f"case {case_match.group(1).strip()}"
    
    return None


def generate_yaml_draft(analysis: CodecAnalysis) -> str:
    """Generate a draft YAML schema from analysis."""
    lines = [
        f"# Draft schema generated from {analysis.filename}",
        f"# Review required - confidence varies by field",
        f"# Warnings: {len(analysis.warnings)}",
        "",
        f"name: {Path(analysis.filename).stem}",
        "version: 1",
        f"endian: {analysis.endian}",
        "",
        "fields:"
    ]
    
    for field in analysis.fields:
        lines.append(f"  # {field.raw_expression[:60]}...")
        if field.notes:
            for note in field.notes:
                lines.append(f"  # NOTE: {note}")
        if field.confidence != "high":
            lines.append(f"  # CONFIDENCE: {field.confidence}")
        if field.condition:
            lines.append(f"  # CONDITION: {field.condition}")
        
        lines.append(f"  - name: {field.name}")
        
        # Determine type
        type_str = "u8"
        if field.signed:
            type_str = f"s{field.size * 8}"
        elif field.size > 1:
            type_str = f"u{field.size * 8}"
        
        # Add bitfield notation if needed
        if field.bit_mask and field.bit_shift is not None:
            width = bin(field.bit_mask).count('1')
            end_bit = field.bit_shift + width - 1
            type_str = f"u8[{field.bit_shift}:{end_bit}]"
        
        lines.append(f"    type: {type_str}")
        
        if field.multiplier:
            lines.append(f"    mult: {field.multiplier}")
        if field.offset:
            lines.append(f"    add: {field.offset}")
        
        lines.append("")
    
    # Add lookups
    if analysis.lookups:
        lines.append("# Detected lookup tables:")
        for name, table in analysis.lookups.items():
            lines.append(f"# {name}:")
            for k, v in table.items():
                lines.append(f"#   {k}: {v}")
    
    # Add warnings
    if analysis.warnings:
        lines.append("")
        lines.append("# WARNINGS:")
        for w in analysis.warnings:
            lines.append(f"# - {w}")
    
    return "\n".join(lines)


def print_analysis(analysis: CodecAnalysis):
    """Print analysis in human-readable format."""
    print(f"\n{'='*60}")
    print(f"CODEC ANALYSIS: {analysis.filename}")
    print(f"{'='*60}")
    
    if analysis.warnings:
        print("\n⚠️  WARNINGS:")
        for w in analysis.warnings:
            print(f"   - {w}")
    
    print(f"\n📋 SUMMARY:")
    print(f"   Endianness: {analysis.endian}")
    print(f"   fPorts: {analysis.fports or 'not detected'}")
    print(f"   Fields: {len(analysis.fields)}")
    print(f"   Conditionals: {len(analysis.conditionals)}")
    print(f"   Lookup tables: {len(analysis.lookups)}")
    print(f"   TLV format: {analysis.is_tlv}")
    
    print(f"\n📊 FIELDS:")
    for f in analysis.fields:
        conf_icon = "✓" if f.confidence == "high" else "?" if f.confidence == "medium" else "⚠"
        print(f"\n   {conf_icon} {f.name}")
        print(f"      Bytes: {f.byte_indices or '?'}")
        if f.size > 1:
            print(f"      Size: {f.size} bytes")
        if f.signed:
            print(f"      Signed: yes")
        if f.bit_mask:
            print(f"      Mask: 0x{f.bit_mask:X}")
        if f.bit_shift:
            print(f"      Shift: >> {f.bit_shift}")
        if f.multiplier:
            print(f"      Multiplier: {f.multiplier}")
        if f.offset:
            print(f"      Offset: {f.offset:+}")
        if f.condition:
            print(f"      Condition: {f.condition}")
        if f.notes:
            for note in f.notes:
                print(f"      Note: {note}")
        print(f"      Expression: {f.raw_expression[:50]}...")
    
    if analysis.lookups:
        print(f"\n📖 LOOKUP TABLES:")
        for name, table in analysis.lookups.items():
            print(f"\n   {name}:")
            for k, v in sorted(table.items()):
                print(f"      {k}: {v}")
    
    if analysis.conditionals:
        print(f"\n🔀 CONDITIONALS:")
        for c in analysis.conditionals:
            print(f"   - {c['type']}: {c.get('variable') or c.get('condition')}")


def main():
    parser = argparse.ArgumentParser(description='Analyze TTN codec for schema conversion')
    parser.add_argument('codec_file', help='JavaScript codec file to analyze')
    parser.add_argument('--yaml', action='store_true', help='Output draft YAML schema')
    parser.add_argument('--json', action='store_true', help='Output JSON analysis')
    args = parser.parse_args()
    
    with open(args.codec_file, 'r') as f:
        js_code = f.read()
    
    analysis = analyze_codec(js_code, args.codec_file)
    
    if args.yaml:
        print(generate_yaml_draft(analysis))
    elif args.json:
        # Convert to JSON-serializable format
        result = {
            'filename': analysis.filename,
            'fports': analysis.fports,
            'fields': [
                {
                    'name': f.name,
                    'byte_indices': f.byte_indices,
                    'bit_mask': f.bit_mask,
                    'bit_shift': f.bit_shift,
                    'multiplier': f.multiplier,
                    'divisor': f.divisor,
                    'offset': f.offset,
                    'signed': f.signed,
                    'size': f.size,
                    'lookup': f.lookup,
                    'condition': f.condition,
                    'confidence': f.confidence,
                    'notes': f.notes,
                }
                for f in analysis.fields
            ],
            'conditionals': analysis.conditionals,
            'lookups': analysis.lookups,
            'warnings': analysis.warnings,
            'is_tlv': analysis.is_tlv,
            'endian': analysis.endian,
        }
        print(json.dumps(result, indent=2))
    else:
        print_analysis(analysis)


if __name__ == '__main__':
    main()
