#!/usr/bin/env python3
"""
payload_size_calc.py - Calculate payload sizes for all flag/port combinations.

Enumerates every possible flag combination for flagged schemas and calculates
exact payload sizes. Essential for firmware developers to set LORA_PAYLOAD_SIZE.

Usage:
    python tools/payload_size_calc.py schema.yaml
"""

import argparse
import itertools
import json
import re
import sys
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def type_size(t: str) -> Optional[int]:
    basic = {
        'u8': 1, 's8': 1, 'i8': 1, 'uint8': 1, 'int8': 1,
        'u16': 2, 's16': 2, 'i16': 2, 'uint16': 2, 'int16': 2,
        'u24': 3, 's24': 3, 'i24': 3,
        'u32': 4, 's32': 4, 'i32': 4, 'uint32': 4, 'int32': 4,
        'u64': 8, 's64': 8, 'i64': 8, 'uint64': 8, 'int64': 8,
        'f16': 2, 'f32': 4, 'f64': 8,
    }
    clean = re.sub(r'^(?:be_|le_)?', '', t)
    return basic.get(clean)


def field_size(field: Dict) -> int:
    """Calculate fixed size of a single field."""
    ftype = field.get('type', 'u8')
    if ftype == 'skip':
        return field.get('length', 1)
    if ftype in ('ascii', 'hex', 'bytes'):
        return field.get('length', 1)
    if ftype == 'bitfield_string':
        return field.get('length', 2)
    if ftype == 'number':
        return 0  # computed, not on wire
    if ftype == 'enum':
        base = field.get('base', 'u8')
        return type_size(base) or 1
    return type_size(ftype) or 0


def fields_size(fields: List[Dict]) -> int:
    """Calculate total fixed size of a list of fields (no flagged/tlv)."""
    total = 0
    for f in fields:
        if 'byte_group' in f:
            bg = f['byte_group']
            if isinstance(bg, dict):
                total += bg.get('size', 1)
            else:
                total += 1
        elif 'match' in f:
            # Take max case size
            match = f['match']
            max_case = 0
            for case_fields in match.get('cases', {}).values():
                if isinstance(case_fields, list):
                    max_case = max(max_case, fields_size(case_fields))
            total += max_case
        elif 'tlv' in f or 'flagged' in f:
            pass  # handled separately
        else:
            total += field_size(f)
    return total


def analyze_schema(schema: Dict[str, Any]) -> None:
    name = schema.get('name', 'unknown')
    print(f"Schema: {name}")
    print(f"Endian: {schema.get('endian', 'big')}")
    print()

    if 'ports' in schema:
        for port_key, port_def in schema['ports'].items():
            direction = port_def.get('direction', 'uplink')
            desc = port_def.get('description', '')
            fields = port_def.get('fields', [])
            print(f"  Port {port_key} ({direction}): {desc}")
            analyze_fields(fields, '    ')
            print()
    else:
        fields = schema.get('fields', [])
        analyze_fields(fields, '  ')

    # LoRa airtime estimates (SF7-SF12, 125kHz, EU868)
    print("  LoRa Airtime Estimates (EU868, 125kHz):")
    print("  ┌──────┬────────────┬────────────┐")
    print("  │  SF  │  Min (ms)  │  Max (ms)  │")
    print("  ├──────┼────────────┼────────────┤")
    for sf in range(7, 13):
        # Simplified airtime: T_packet ≈ T_preamble + T_payload
        # Using LoRaWAN calculator approximation
        bw = 125000
        cr = 1  # 4/5
        n_preamble = 8
        de = 1 if sf >= 11 else 0
        ih = 0  # explicit header

        t_sym = (2 ** sf) / bw * 1000  # ms
        t_preamble = (n_preamble + 4.25) * t_sym

        if 'ports' in schema:
            sizes = []
            for pd in schema['ports'].values():
                sizes.append(fields_size(pd.get('fields', [])))
            min_pl = min(sizes) if sizes else 0
            max_pl = max(sizes) if sizes else 0
        else:
            fields = schema.get('fields', [])
            min_pl, max_pl = get_min_max(fields)

        for pl_size in [min_pl, max_pl]:
            pl_size += 13  # LoRaWAN overhead (MHDR + DevAddr + FCtrl + FCnt + FOpts + MIC)
            n_payload = 8 + max(0, (8 * pl_size - 4 * sf + 28 + 16 - 20 * ih + 7) // (4 * (sf - 2 * de))) * (cr + 4)
            t_payload = n_payload * t_sym

        t_min = t_preamble + 8 * t_sym + max(0, (8 + max(0, (8 * (min_pl + 13) - 4 * sf + 28 + 16 + 7) // (4 * (sf - 2 * de)))) * (cr + 4)) * t_sym
        t_max = t_preamble + 8 * t_sym + max(0, (8 + max(0, (8 * (max_pl + 13) - 4 * sf + 28 + 16 + 7) // (4 * (sf - 2 * de)))) * (cr + 4)) * t_sym

        print(f"  │  {sf:2d}  │  {t_min:8.1f}  │  {t_max:8.1f}  │")
    print("  └──────┴────────────┴────────────┘")


def get_min_max(fields: List[Dict]) -> Tuple[int, int]:
    """Get min/max payload sizes considering flagged groups."""
    fixed = 0
    flag_groups = []

    for f in fields:
        if 'flagged' in f:
            fg = f['flagged']
            for group in fg.get('groups', []):
                group_sz = fields_size(group.get('fields', []))
                flag_groups.append(group_sz)
        elif 'tlv' in f:
            # TLV is variable; min=0, max=all cases
            tlv = f['tlv']
            tag_sz = sum(type_size(tf.get('type', 'u8')) or 1 for tf in tlv.get('tag_fields', []))
            total = 0
            for case_fields in tlv.get('cases', {}).values():
                total += tag_sz + fields_size(case_fields)
            flag_groups.append(total)  # treat like optional
        elif 'byte_group' in f:
            bg = f['byte_group']
            fixed += bg.get('size', 1) if isinstance(bg, dict) else 1
        elif 'match' in f:
            pass  # variable
        else:
            fixed += field_size(f)

    min_sz = fixed  # no optional groups
    max_sz = fixed + sum(flag_groups)
    return min_sz, max_sz


def analyze_fields(fields: List[Dict], indent: str) -> None:
    fixed = 0
    flag_groups = []

    for f in fields:
        if 'flagged' in f:
            fg = f['flagged']
            for group in fg.get('groups', []):
                group_sz = fields_size(group.get('fields', []))
                bit = group['bit']
                names = [gf.get('name', '?') for gf in group.get('fields', []) if gf.get('name')]
                flag_groups.append((bit, group_sz, names))
        elif 'tlv' in f:
            tlv = f['tlv']
            tag_sz = sum(type_size(tf.get('type', 'u8')) or 1 for tf in tlv.get('tag_fields', []))
            print(f"{indent}TLV (tag: {tag_sz} bytes):")
            for case_key, case_fields in tlv.get('cases', {}).items():
                cs = fields_size(case_fields)
                print(f"{indent}  case {case_key}: {tag_sz + cs} bytes ({tag_sz} tag + {cs} data)")
        elif 'byte_group' in f:
            bg = f['byte_group']
            sz = bg.get('size', 1) if isinstance(bg, dict) else 1
            fixed += sz
        elif 'match' in f:
            pass
        else:
            sz = field_size(f)
            fixed += sz

    min_sz = fixed
    max_sz = fixed + sum(g[1] for g in flag_groups)

    print(f"{indent}Fixed header: {fixed} bytes")

    if flag_groups:
        print(f"{indent}Flagged groups:")
        for bit, sz, names in flag_groups:
            print(f"{indent}  bit {bit}: +{sz} bytes ({', '.join(names)})")
        print()

        # Enumerate all combinations
        n = len(flag_groups)
        print(f"{indent}All {2**n} flag combinations:")
        print(f"{indent}┌{'─'*12}┬{'─'*10}┬{'─'*30}┐")
        print(f"{indent}│ {'Flags':^10} │ {'Size':^8} │ {'Groups':^28} │")
        print(f"{indent}├{'─'*12}┼{'─'*10}┼{'─'*30}┤")
        for combo in range(2**n):
            total = fixed
            group_names = []
            flag_val = 0
            for i, (bit, sz, names) in enumerate(flag_groups):
                if combo & (1 << i):
                    total += sz
                    flag_val |= (1 << bit)
                    group_names.extend(names)
            names_str = ', '.join(group_names) if group_names else '(none)'
            if len(names_str) > 28:
                names_str = names_str[:25] + '...'
            print(f"{indent}│ 0x{flag_val:04X}     │ {total:>6}   │ {names_str:<28} │")
        print(f"{indent}└{'─'*12}┴{'─'*10}┴{'─'*30}┘")
    else:
        print(f"{indent}Fixed payload: {fixed} bytes (no optional groups)")

    print()
    print(f"{indent}Min payload: {min_sz} bytes")
    print(f"{indent}Max payload: {max_sz} bytes")


def fix_yaml_booleans(obj):
    if isinstance(obj, dict):
        return {('on' if k is True else 'off' if k is False else k): fix_yaml_booleans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [fix_yaml_booleans(i) for i in obj]
    return obj


def main():
    parser = argparse.ArgumentParser(description='Calculate payload sizes from Payload Schema YAML schema')
    parser.add_argument('schema', help='Schema YAML file')
    args = parser.parse_args()

    with open(args.schema) as f:
        schema = yaml.safe_load(f)
    schema = fix_yaml_booleans(schema)

    analyze_schema(schema)


if __name__ == '__main__':
    main()
