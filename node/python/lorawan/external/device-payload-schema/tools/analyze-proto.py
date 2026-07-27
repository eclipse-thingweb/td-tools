#!/usr/bin/env python3
"""
analyze-proto.py - Comprehensive protobuf file analysis tool

Analyzes .proto files for:
- Message structure and hierarchy
- Estimated wire sizes (min/typical/max)
- Field type distribution
- Enum analysis
- Coverage comparison against spec documentation
- Bandwidth and efficiency recommendations

Usage:
    analyze-proto.py <proto-file> [options]
    analyze-proto.py schemas/*.proto --spec-dir spec/sections/ --output build/reports/

Output: Markdown report with optional PDF generation
"""

import argparse
import json
import re
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Any

# Protobuf wire type sizes (in bytes): (min, typical, max)
WIRE_SIZES = {
    # Varint types (1-10 bytes, typically 1-2)
    'int32': (1, 2, 5),
    'int64': (1, 3, 10),
    'uint32': (1, 2, 5),
    'uint64': (1, 3, 10),
    'sint32': (1, 2, 5),
    'sint64': (1, 3, 10),
    'bool': (1, 1, 1),
    'enum': (1, 1, 2),
    
    # Fixed types
    'fixed32': (4, 4, 4),
    'fixed64': (8, 8, 8),
    'sfixed32': (4, 4, 4),
    'sfixed64': (8, 8, 8),
    'float': (4, 4, 4),
    'double': (8, 8, 8),
    
    # Length-delimited (variable)
    'string': (1, 20, 256),
    'bytes': (1, 50, 1024),
    'message': (2, 50, 500),
}


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}", file=sys.stderr)


def log_warn(msg: str) -> None:
    print(f"[WARN] {msg}", file=sys.stderr)


def parse_proto_file(content: str) -> dict:
    """Parse proto file and extract structure."""
    result = {
        'package': None,
        'messages': {},
        'enums': {},
        'imports': [],
        'syntax': 'proto3',
    }
    
    # Extract syntax
    syntax_match = re.search(r'syntax\s*=\s*"(proto[23])"\s*;', content)
    if syntax_match:
        result['syntax'] = syntax_match.group(1)
    
    # Extract package
    pkg_match = re.search(r'package\s+(\w+);', content)
    if pkg_match:
        result['package'] = pkg_match.group(1)
    
    # Extract imports
    for match in re.finditer(r'import\s+"([^"]+)"\s*;', content):
        result['imports'].append(match.group(1))
    
    # Extract enums (including nested)
    enum_pattern = re.compile(
        r'enum\s+(\w+)\s*\{([^}]+)\}',
        re.MULTILINE | re.DOTALL
    )
    for match in enum_pattern.finditer(content):
        enum_name = match.group(1)
        enum_body = match.group(2)
        values = []
        for line in enum_body.split('\n'):
            val_match = re.match(r'\s*(\w+)\s*=\s*(\d+)', line)
            if val_match:
                values.append({
                    'name': val_match.group(1),
                    'number': int(val_match.group(2)),
                })
        result['enums'][enum_name] = values
    
    # Extract messages
    msg_pattern = re.compile(r'message\s+(\w+)\s*\{', re.MULTILINE)
    
    for match in msg_pattern.finditer(content):
        msg_name = match.group(1)
        start = match.end()
        
        # Find matching closing brace
        depth = 1
        pos = start
        while depth > 0 and pos < len(content):
            if content[pos] == '{':
                depth += 1
            elif content[pos] == '}':
                depth -= 1
            pos += 1
        
        msg_body = content[start:pos-1]
        
        # Extract fields
        fields = []
        field_pattern = re.compile(
            r'(?:(optional|repeated|required)\s+)?'
            r'(\w+)\s+(\w+)\s*=\s*(\d+)\s*;'
            r'(?:\s*//(.*))?',
            re.MULTILINE
        )
        
        for field_match in field_pattern.finditer(msg_body):
            modifier = field_match.group(1) or ''
            field_type = field_match.group(2)
            field_name = field_match.group(3)
            field_num = int(field_match.group(4))
            comment = (field_match.group(5) or '').strip()
            
            fields.append({
                'modifier': modifier,
                'type': field_type,
                'name': field_name,
                'number': field_num,
                'comment': comment,
                'is_repeated': modifier == 'repeated',
                'is_optional': modifier == 'optional',
            })
        
        # Check for oneof
        oneof_pattern = re.compile(r'oneof\s+(\w+)\s*\{([^}]+)\}', re.DOTALL)
        oneofs = {}
        for oneof_match in oneof_pattern.finditer(msg_body):
            oneof_name = oneof_match.group(1)
            oneof_body = oneof_match.group(2)
            oneof_fields = []
            for field_match in field_pattern.finditer(oneof_body):
                oneof_fields.append({
                    'type': field_match.group(2),
                    'name': field_match.group(3),
                    'number': int(field_match.group(4)),
                })
            oneofs[oneof_name] = oneof_fields
        
        result['messages'][msg_name] = {
            'fields': fields,
            'oneofs': oneofs,
            'field_count': len(fields),
        }
    
    return result


def extract_spec_messages(spec_content: str) -> set:
    """Extract message names mentioned in spec documentation."""
    messages = set()
    
    # Pattern for message definitions in spec (protobuf-like blocks)
    msg_pattern = re.compile(r'message\s+(\w+)\s*\{?', re.MULTILINE)
    
    for match in msg_pattern.finditer(spec_content):
        msg_name = match.group(1)
        # Filter out common words that might match
        if len(msg_name) > 2 and msg_name[0].isupper():
            messages.add(msg_name)
    
    return messages


def estimate_size(field_type: str, modifier: str, messages: dict) -> tuple:
    """Estimate min/typical/max size for a field."""
    base_type = field_type.lower()
    tag_size = 1  # Most fields have number < 16
    
    if base_type in WIRE_SIZES:
        min_s, typ_s, max_s = WIRE_SIZES[base_type]
    elif field_type in messages:
        nested = messages[field_type]
        min_s, typ_s, max_s = estimate_message_size(nested, messages)
        min_s += 1
        typ_s += 1
        max_s += 2
    else:
        min_s, typ_s, max_s = 1, 2, 4
    
    if modifier == 'repeated':
        return (0, (tag_size + typ_s) * 3, (tag_size + max_s) * 10)
    elif modifier == 'optional':
        return (0, tag_size + typ_s, tag_size + max_s)
    else:
        return (tag_size + min_s, tag_size + typ_s, tag_size + max_s)


def estimate_message_size(msg: dict, all_messages: dict) -> tuple:
    """Estimate total message size."""
    min_total = 0
    typ_total = 0
    max_total = 0
    
    for field in msg.get('fields', []):
        min_s, typ_s, max_s = estimate_size(
            field['type'], 
            field['modifier'],
            all_messages
        )
        min_total += min_s
        typ_total += typ_s
        max_total += max_s
    
    return (min_total, typ_total, max_total)


def categorize_field_type(field_type: str, enums: dict, messages: dict) -> str:
    """Categorize a field type."""
    if field_type in ['int32', 'int64', 'uint32', 'uint64', 'sint32', 'sint64']:
        return 'integer'
    elif field_type in ['fixed32', 'fixed64', 'sfixed32', 'sfixed64']:
        return 'fixed'
    elif field_type in ['float', 'double']:
        return 'float'
    elif field_type == 'bool':
        return 'boolean'
    elif field_type == 'string':
        return 'string'
    elif field_type == 'bytes':
        return 'bytes'
    elif field_type in enums:
        return 'enum'
    elif field_type in messages:
        return 'message'
    else:
        return 'other'


def analyze_spec_coverage(proto_messages: dict, proto_enums: dict, 
                          spec_messages: set) -> dict:
    """Analyze coverage between proto and spec."""
    proto_msg_names = set(proto_messages.keys())
    
    return {
        'proto_only': sorted(proto_msg_names - spec_messages),
        'spec_only': sorted(spec_messages - proto_msg_names),
        'both': sorted(proto_msg_names & spec_messages),
        'proto_count': len(proto_msg_names),
        'spec_count': len(spec_messages),
        'coverage': len(proto_msg_names & spec_messages) / len(proto_msg_names) * 100 if proto_msg_names else 0,
    }


def generate_report(proto_path: Path, parsed: dict, spec_content: str = None,
                    output_dir: Path = None) -> str:
    """Generate comprehensive analysis report."""
    lines = []
    messages = parsed['messages']
    enums = parsed['enums']
    
    # Calculate sizes
    size_data = []
    for msg_name, msg in sorted(messages.items()):
        min_s, typ_s, max_s = estimate_message_size(msg, messages)
        size_data.append((msg_name, msg['field_count'], min_s, typ_s, max_s))
    
    # Field type distribution
    type_counts = defaultdict(int)
    for msg in messages.values():
        for field in msg.get('fields', []):
            category = categorize_field_type(field['type'], enums, messages)
            type_counts[category] += 1
    total_fields = sum(type_counts.values())
    
    # Header
    lines.extend([
        "# Protocol Buffer Analysis Report",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Proto File:** `{proto_path.name}`",
        f"**Package:** `{parsed['package'] or 'default'}`",
        f"**Syntax:** {parsed['syntax']}",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Messages | {len(messages)} |",
        f"| Enums | {len(enums)} |",
        f"| Total Fields | {sum(m['field_count'] for m in messages.values())} |",
        f"| Imports | {len(parsed['imports'])} |",
        "",
    ])
    
    # Spec coverage if provided
    if spec_content:
        spec_messages = extract_spec_messages(spec_content)
        coverage = analyze_spec_coverage(messages, enums, spec_messages)
        
        lines.extend([
            "### Spec Coverage",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Messages in proto | {coverage['proto_count']} |",
            f"| Messages in spec | {coverage['spec_count']} |",
            f"| Documented | {len(coverage['both'])} |",
            f"| Coverage | {coverage['coverage']:.1f}% |",
            "",
        ])
        
        if coverage['proto_only']:
            lines.extend([
                "**Undocumented messages:**",
                "",
            ])
            for msg in coverage['proto_only'][:10]:
                lines.append(f"- `{msg}`")
            if len(coverage['proto_only']) > 10:
                lines.append(f"- ... and {len(coverage['proto_only']) - 10} more")
            lines.append("")
    
    # Message Size Analysis
    lines.extend([
        "---",
        "",
        "## Message Size Analysis",
        "",
        "Estimated wire sizes in bytes (min / typical / max):",
        "",
        "| Message | Fields | Min | Typical | Max |",
        "|---------|--------|-----|---------|-----|",
    ])
    
    for name, fields, min_s, typ_s, max_s in sorted(size_data, key=lambda x: -x[3])[:20]:
        lines.append(f"| `{name}` | {fields} | {min_s} | {typ_s} | {max_s} |")
    
    if len(size_data) > 20:
        lines.append(f"| ... | | | | |")
        lines.append(f"| *({len(size_data) - 20} more messages)* | | | | |")
    
    lines.extend([
        "",
        "### Size Statistics",
        "",
        f"- **Average typical size:** {sum(s[3] for s in size_data) // len(size_data) if size_data else 0} bytes",
        f"- **Smallest:** {min(s[3] for s in size_data) if size_data else 0} bytes",
        f"- **Largest:** {max(s[3] for s in size_data) if size_data else 0} bytes",
        "",
    ])
    
    # Field Type Distribution
    lines.extend([
        "---",
        "",
        "## Field Type Distribution",
        "",
        "| Type | Count | Percentage |",
        "|------|-------|------------|",
    ])
    
    for cat, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        pct = count / total_fields * 100 if total_fields else 0
        lines.append(f"| {cat.title()} | {count} | {pct:.1f}% |")
    
    lines.append("")
    
    # Enum Analysis
    lines.extend([
        "---",
        "",
        "## Enum Analysis",
        "",
        "| Enum | Values | Range |",
        "|------|--------|-------|",
    ])
    
    for enum_name, values in sorted(enums.items()):
        if values:
            numbers = [v['number'] for v in values]
            range_str = f"{min(numbers)}-{max(numbers)}"
        else:
            range_str = "empty"
        lines.append(f"| `{enum_name}` | {len(values)} | {range_str} |")
    
    lines.append("")
    
    # Bandwidth Analysis
    avg_size = sum(s[3] for s in size_data) // len(size_data) if size_data else 50
    lines.extend([
        "---",
        "",
        "## Bandwidth Estimates",
        "",
        "| Messages/sec | Bandwidth |",
        "|--------------|-----------|",
    ])
    
    for rate in [1, 10, 100, 1000]:
        bw = avg_size * rate * 8 / 1000
        unit = "kbps" if bw < 1000 else "Mbps"
        val = bw if bw < 1000 else bw / 1000
        lines.append(f"| {rate} | {val:.1f} {unit} |")
    
    # Recommendations
    lines.extend([
        "",
        "---",
        "",
        "## Recommendations",
        "",
        "### Wire Efficiency",
        "",
    ])
    
    # Find repeated numeric fields
    repeated_numerics = []
    for msg_name, msg in messages.items():
        for field in msg.get('fields', []):
            if field.get('is_repeated') and field['type'] in ['uint32', 'uint64', 'int32', 'int64']:
                repeated_numerics.append(f"`{msg_name}.{field['name']}`")
    
    if repeated_numerics:
        lines.append("**Consider packed encoding for repeated numerics:**")
        lines.append("")
        for f in repeated_numerics[:5]:
            lines.append(f"- {f}")
        if len(repeated_numerics) > 5:
            lines.append(f"- ... and {len(repeated_numerics) - 5} more")
        lines.append("")
    
    # Large messages
    large_msgs = [s for s in size_data if s[4] > 10000]
    if large_msgs:
        lines.append("**Large messages (>10KB max) - consider streaming:**")
        lines.append("")
        for name, _, _, _, max_s in large_msgs[:5]:
            lines.append(f"- `{name}` ({max_s:,} bytes max)")
        lines.append("")
    
    # High field numbers
    high_field_msgs = []
    for msg_name, msg in messages.items():
        high = [f for f in msg.get('fields', []) if f['number'] > 15]
        if high and msg_name in ['Uplink', 'Downlink', 'Registration']:
            high_field_msgs.append((msg_name, len(high)))
    
    if high_field_msgs:
        lines.append("**High field numbers (2-byte tags) in frequent messages:**")
        lines.append("")
        for name, count in high_field_msgs:
            lines.append(f"- `{name}`: {count} fields with number > 15")
        lines.append("")
    
    lines.extend([
        "### Security",
        "",
        "- Validate string field lengths to prevent memory exhaustion",
        "- Cap repeated field counts (e.g., max 100 elements)",
        "- Validate bytes fields before processing",
        "",
        "### Monitoring",
        "",
        "Implement metrics for:",
        "- Message counts by type",
        "- Message sizes (p50, p95, p99)",
        "- Serialization/deserialization latency",
        "- Validation failure rates",
        "",
    ])
    
    return '\n'.join(lines)


def run_self_test() -> bool:
    """Run self-test."""
    print("Running self-test...")
    
    test_proto = '''
    syntax = "proto3";
    package test;
    
    enum Status {
        UNKNOWN = 0;
        OK = 1;
        ERROR = 2;
    }
    
    message TestMessage {
        uint32 id = 1;
        string name = 2;
        repeated uint64 values = 3;
        Status status = 4;
    }
    '''
    
    parsed = parse_proto_file(test_proto)
    
    assert parsed['package'] == 'test', f"Expected package 'test', got {parsed['package']}"
    assert 'TestMessage' in parsed['messages'], "Expected TestMessage"
    assert 'Status' in parsed['enums'], "Expected Status enum"
    assert len(parsed['enums']['Status']) == 3, "Expected 3 enum values"
    assert parsed['messages']['TestMessage']['field_count'] == 4, "Expected 4 fields"
    
    print("  Parsing: OK")
    
    # Test size estimation
    msg = parsed['messages']['TestMessage']
    min_s, typ_s, max_s = estimate_message_size(msg, parsed['messages'])
    assert min_s > 0, "Min size should be > 0"
    assert typ_s >= min_s, "Typical should be >= min"
    assert max_s >= typ_s, "Max should be >= typical"
    
    print("  Size estimation: OK")
    
    # Test report generation
    report = generate_report(Path("test.proto"), parsed)
    assert "Protocol Buffer Analysis Report" in report, "Report should have title"
    assert "TestMessage" in report, "Report should mention TestMessage"
    
    print("  Report generation: OK")
    
    print("[PASS] Self-test completed")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Analyze protobuf file structure, sizes, and coverage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s schemas/api.proto
  %(prog)s schemas/*.proto --spec-dir spec/sections/
  %(prog)s api.proto -o build/reports/proto-analysis.md
  %(prog)s --self-test
        """,
    )
    parser.add_argument(
        'proto_files',
        type=Path,
        nargs='*',
        help="Proto file(s) to analyze"
    )
    parser.add_argument(
        '-s', '--spec-dir',
        type=Path,
        help="Directory containing spec markdown files for coverage analysis"
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help="Output file (default: stdout)"
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help="Output raw data as JSON"
    )
    parser.add_argument(
        '--self-test',
        action='store_true',
        help="Run self-test"
    )
    
    args = parser.parse_args()
    
    if args.self_test:
        success = run_self_test()
        sys.exit(0 if success else 1)
    
    if not args.proto_files:
        parser.error("proto_files required (unless using --self-test)")
    
    # Parse all proto files
    all_content = ""
    for proto_file in args.proto_files:
        if proto_file.exists():
            all_content += proto_file.read_text() + "\n"
        else:
            log_warn(f"File not found: {proto_file}")
    
    if not all_content:
        log_warn("No proto content found")
        sys.exit(1)
    
    parsed = parse_proto_file(all_content)
    
    # Load spec content if provided
    spec_content = None
    if args.spec_dir and args.spec_dir.exists():
        spec_content = ""
        for md_file in args.spec_dir.glob("*.md"):
            spec_content += md_file.read_text() + "\n"
    
    if args.json:
        output = json.dumps({
            'package': parsed['package'],
            'syntax': parsed['syntax'],
            'messages': {k: {'field_count': v['field_count']} for k, v in parsed['messages'].items()},
            'enums': {k: len(v) for k, v in parsed['enums'].items()},
        }, indent=2)
    else:
        output = generate_report(
            args.proto_files[0] if args.proto_files else Path("proto"),
            parsed,
            spec_content,
        )
    
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output)
        log_info(f"Report written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
