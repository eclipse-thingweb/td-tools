#!/usr/bin/env python3
"""
Batch analyze TTN Device Repository codecs.

Scans the lorawan-devices vendor directory and produces:
1. Summary statistics on codec patterns
2. Categorization by complexity/convertibility
3. Draft schemas for simple codecs

Usage:
    python batch_analyze_codecs.py /path/to/lorawan-devices/vendor
    python batch_analyze_codecs.py /path/to/lorawan-devices/vendor --output-dir ./drafts
"""

import argparse
import json
import os
import sys
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent))
from analyze_ttn_codec import analyze_codec, generate_yaml_draft, CodecAnalysis


@dataclass
class BatchStats:
    total: int = 0
    simple_fixed: int = 0      # Easy conversion
    complex_fixed: int = 0     # Needs conditionals
    tlv_format: int = 0        # Needs schema extension
    parse_errors: int = 0
    
    # Field stats
    total_fields: int = 0
    fields_with_multiplier: int = 0
    fields_with_offset: int = 0
    fields_with_bitfield: int = 0
    fields_signed: int = 0
    
    # Pattern detection
    has_lookups: int = 0
    has_conditionals: int = 0
    multi_fport: int = 0


def categorize_codec(analysis: CodecAnalysis) -> str:
    """Categorize codec by conversion difficulty."""
    if analysis.is_tlv:
        return "tlv"
    
    if len(analysis.conditionals) > 3 or len(analysis.fields) > 20:
        return "complex"
    
    # Check for complex conditions
    complex_conditions = sum(1 for f in analysis.fields if f.condition)
    if complex_conditions > 5:
        return "complex"
    
    return "simple"


def analyze_vendor_directory(vendor_path: Path, output_dir: Path = None) -> dict:
    """Analyze all codecs in a vendor directory."""
    stats = BatchStats()
    results = {
        'simple': [],
        'complex': [],
        'tlv': [],
        'errors': []
    }
    
    js_files = list(vendor_path.rglob("*.js"))
    stats.total = len(js_files)
    
    print(f"Found {stats.total} JavaScript codec files")
    print("Analyzing...\n")
    
    for js_file in js_files:
        try:
            with open(js_file, 'r', encoding='utf-8', errors='ignore') as f:
                js_code = f.read()
            
            # Skip very short files (likely not codecs)
            if len(js_code) < 100:
                continue
            
            # Skip files that don't look like codecs
            if 'decodeUplink' not in js_code and 'Decoder' not in js_code:
                continue
            
            analysis = analyze_codec(js_code, str(js_file))
            category = categorize_codec(analysis)
            
            # Update stats
            if category == "simple":
                stats.simple_fixed += 1
            elif category == "complex":
                stats.complex_fixed += 1
            elif category == "tlv":
                stats.tlv_format += 1
            
            stats.total_fields += len(analysis.fields)
            
            for field in analysis.fields:
                if field.multiplier:
                    stats.fields_with_multiplier += 1
                if field.offset:
                    stats.fields_with_offset += 1
                if field.bit_mask or field.bit_shift:
                    stats.fields_with_bitfield += 1
                if field.signed:
                    stats.fields_signed += 1
            
            if analysis.lookups:
                stats.has_lookups += 1
            if analysis.conditionals:
                stats.has_conditionals += 1
            if len(analysis.fports) > 1:
                stats.multi_fport += 1
            
            # Store result
            rel_path = js_file.relative_to(vendor_path)
            result_entry = {
                'file': str(rel_path),
                'category': category,
                'fields': len(analysis.fields),
                'fports': analysis.fports,
                'is_tlv': analysis.is_tlv,
                'warnings': analysis.warnings
            }
            results[category].append(result_entry)
            
            # Generate draft for simple codecs
            if output_dir and category == "simple" and len(analysis.fields) > 0:
                draft_path = output_dir / rel_path.with_suffix('.yaml')
                draft_path.parent.mkdir(parents=True, exist_ok=True)
                with open(draft_path, 'w') as f:
                    f.write(generate_yaml_draft(analysis))
        
        except Exception as e:
            stats.parse_errors += 1
            results['errors'].append({
                'file': str(js_file.relative_to(vendor_path)),
                'error': str(e)
            })
    
    return {
        'stats': stats,
        'results': results
    }


def print_summary(stats: BatchStats, results: dict):
    """Print analysis summary."""
    print("=" * 60)
    print("BATCH ANALYSIS SUMMARY")
    print("=" * 60)
    
    actual_codecs = stats.simple_fixed + stats.complex_fixed + stats.tlv_format
    
    print(f"\n📊 CODEC CATEGORIES:")
    print(f"   Total JS files scanned: {stats.total}")
    print(f"   Actual codec files: {actual_codecs}")
    print(f"   Parse errors: {stats.parse_errors}")
    print()
    print(f"   ✅ Simple (easy conversion):     {stats.simple_fixed:4d} ({100*stats.simple_fixed/max(1,actual_codecs):.1f}%)")
    print(f"   ⚠️  Complex (needs review):       {stats.complex_fixed:4d} ({100*stats.complex_fixed/max(1,actual_codecs):.1f}%)")
    print(f"   🔄 TLV format (needs extension): {stats.tlv_format:4d} ({100*stats.tlv_format/max(1,actual_codecs):.1f}%)")
    
    print(f"\n📈 FIELD STATISTICS:")
    print(f"   Total fields detected: {stats.total_fields}")
    print(f"   With multiplier/divisor: {stats.fields_with_multiplier}")
    print(f"   With offset: {stats.fields_with_offset}")
    print(f"   With bitfield: {stats.fields_with_bitfield}")
    print(f"   Signed integers: {stats.fields_signed}")
    
    print(f"\n🔧 PATTERN USAGE:")
    print(f"   Codecs with lookup tables: {stats.has_lookups}")
    print(f"   Codecs with conditionals: {stats.has_conditionals}")
    print(f"   Codecs with multiple fPorts: {stats.multi_fport}")
    
    print(f"\n📁 SAMPLE SIMPLE CODECS (first 10):")
    for entry in results['simple'][:10]:
        print(f"   - {entry['file']} ({entry['fields']} fields)")
    
    print(f"\n📁 SAMPLE TLV CODECS (first 10):")
    for entry in results['tlv'][:10]:
        print(f"   - {entry['file']}")
    
    # Time estimate
    simple_time = stats.simple_fixed * 1  # 1 min review
    complex_time = stats.complex_fixed * 5  # 5 min conversion
    total_hours = (simple_time + complex_time) / 60
    
    print(f"\n⏱️  ESTIMATED CONVERSION TIME:")
    print(f"   Simple codecs ({stats.simple_fixed} × 1 min): {simple_time} min")
    print(f"   Complex codecs ({stats.complex_fixed} × 5 min): {complex_time} min")
    print(f"   Total (excluding TLV): {total_hours:.1f} hours")
    print(f"   TLV codecs require schema extension first")


def main():
    parser = argparse.ArgumentParser(description='Batch analyze TTN codecs')
    parser.add_argument('vendor_path', help='Path to lorawan-devices/vendor directory')
    parser.add_argument('--output-dir', '-o', help='Output directory for draft schemas')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    args = parser.parse_args()
    
    vendor_path = Path(args.vendor_path)
    if not vendor_path.exists():
        print(f"Error: {vendor_path} does not exist")
        sys.exit(1)
    
    output_dir = Path(args.output_dir) if args.output_dir else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    data = analyze_vendor_directory(vendor_path, output_dir)
    
    if args.json:
        # Convert stats to dict for JSON
        stats_dict = {
            'total': data['stats'].total,
            'simple_fixed': data['stats'].simple_fixed,
            'complex_fixed': data['stats'].complex_fixed,
            'tlv_format': data['stats'].tlv_format,
            'parse_errors': data['stats'].parse_errors,
            'total_fields': data['stats'].total_fields,
        }
        print(json.dumps({'stats': stats_dict, 'results': data['results']}, indent=2))
    else:
        print_summary(data['stats'], data['results'])


if __name__ == '__main__':
    main()
