#!/usr/bin/env python3
"""
generate_ts013_codec.py - Generate TS013-compliant JavaScript codec from Payload Schema YAML.

Generates a self-contained JS file implementing:
  - decodeUplink(input)   → { data, warnings, errors }
  - encodeDownlink(input)  → { bytes, fPort, warnings, errors }
  - decodeDownlink(input)  → { data, warnings, errors }

Supports all Phase 2 features: flagged, ports, tlv, bitfield_string, formula,
match, byte_group, modifiers, enum, repeat.

Usage:
    python tools/generate_ts013_codec.py schema.yaml [-o output.js]
    python tools/generate_ts013_codec.py schemas/ -o generated/
"""

import argparse
import json
import re
import sys
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def to_js_name(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_]', '_', name)


def type_size(t: str) -> Optional[int]:
    m = re.match(r'^(?:be_|le_)?([usif])(\d+)$', t)
    if m:
        return int(m.group(2)) // 8
    basic = {
        'u8': 1, 's8': 1, 'i8': 1, 'uint8': 1, 'int8': 1,
        'u16': 2, 's16': 2, 'i16': 2, 'uint16': 2, 'int16': 2,
        'u24': 3, 's24': 3, 'i24': 3,
        'u32': 4, 's32': 4, 'i32': 4, 'uint32': 4, 'int32': 4,
        'u64': 8, 's64': 8, 'i64': 8, 'uint64': 8, 'int64': 8,
        'f16': 2, 'f32': 4, 'f64': 8,
    }
    return basic.get(t)


def parse_bit_slice_type(t: str) -> Optional[Tuple[str, int, int]]:
    """Parse bit-slice type syntax.

    Supports:
      - u8[3:4]   -> start=3, width=2
      - u8[3+:2]  -> start=3, width=2
    Returns (base_type, bit_start, bit_width) or None.
    """
    m = re.match(r'^((?:be_|le_)?[usif]\d+)\[(\d+):(\d+)\]$', t)
    if m:
        base_t = m.group(1)
        lo = int(m.group(2))
        hi = int(m.group(3))
        if hi < lo:
            return None
        return base_t, lo, (hi - lo + 1)

    m = re.match(r'^((?:be_|le_)?[usif]\d+)\[(\d+)\+:(\d+)\]$', t)
    if m:
        base_t = m.group(1)
        start = int(m.group(2))
        width = int(m.group(3))
        if width <= 0:
            return None
        return base_t, start, width

    return None


def is_signed(t: str) -> bool:
    clean = re.sub(r'^(?:be_|le_)?', '', t)
    return clean.startswith('s') or clean.startswith('i')


def is_float(t: str) -> bool:
    clean = re.sub(r'^(?:be_|le_)?', '', t)
    return clean.startswith('f')


def field_endian_override(t: str) -> Optional[str]:
    if t.startswith('be_'):
        return 'big'
    if t.startswith('le_'):
        return 'little'
    return None


def formula_to_js(formula: str) -> str:
    """Convert formula syntax to JavaScript (DEPRECATED)."""
    js = formula
    js = re.sub(r'\bpow\b', 'Math.pow', js)
    js = re.sub(r'\babs\b', 'Math.abs', js)
    js = re.sub(r'\bsqrt\b', 'Math.sqrt', js)
    js = re.sub(r'\bmin\b', 'Math.min', js)
    js = re.sub(r'\bmax\b', 'Math.max', js)
    js = re.sub(r'\bround\b', 'Math.round', js)
    js = re.sub(r'\bfloor\b', 'Math.floor', js)
    js = re.sub(r'\bceil\b', 'Math.ceil', js)
    js = re.sub(r'\blog\b', 'Math.log', js)
    js = re.sub(r'\bexp\b', 'Math.exp', js)
    js = re.sub(r'\bPI\b', 'Math.PI', js)
    js = re.sub(r'\band\b', '&&', js)
    js = re.sub(r'\bor\b', '||', js)
    js = re.sub(r'\bnot\b', '!', js)
    # $field_name → d.field_name
    js = re.sub(r'\$([a-zA-Z_][a-zA-Z0-9_]*)', r'd.\1', js)
    # C-style ternary: cond ? a : b (already JS)
    return js


def polynomial_to_js(coeffs: List[float], input_expr: str) -> str:
    """Generate JS for polynomial evaluation using Horner's method."""
    if not coeffs:
        return '0'
    if len(coeffs) == 1:
        return str(coeffs[0])
    # Horner's method: ((a_n * x + a_{n-1}) * x + ...) * x + a_0
    result = str(coeffs[0])
    for coef in coeffs[1:]:
        if coef >= 0:
            result = f'({result} * {input_expr} + {coef})'
        else:
            result = f'({result} * {input_expr} - {abs(coef)})'
    return result


def compute_to_js(compute: Dict[str, Any]) -> str:
    """Generate JS for cross-field binary operation."""
    op = compute.get('op', 'add')
    a = compute.get('a', 0)
    b = compute.get('b', 0)
    
    def operand_to_js(spec):
        if isinstance(spec, str) and spec.startswith('$'):
            return f'd.{spec[1:]}'
        return str(spec)
    
    a_js = operand_to_js(a)
    b_js = operand_to_js(b)
    
    if op == 'add':
        return f'({a_js} + {b_js})'
    elif op == 'sub':
        return f'({a_js} - {b_js})'
    elif op == 'mul':
        return f'({a_js} * {b_js})'
    elif op == 'div':
        return f'({b_js} !== 0 ? {a_js} / {b_js} : NaN)'
    elif op == 'mod':
        return f'({b_js} !== 0 ? Math.trunc({a_js}) % Math.trunc({b_js}) : NaN)'
    elif op == 'idiv':
        return f'({b_js} !== 0 ? Math.trunc({a_js} / {b_js}) : NaN)'
    return '0'


def guard_to_js(guard: Dict[str, Any], value_expr: str) -> str:
    """Generate JS for guard conditional evaluation."""
    when_conditions = guard.get('when', [])
    else_value = guard.get('else', 'NaN')
    
    conditions = []
    for cond in when_conditions:
        field_ref = cond.get('field', '')
        if isinstance(field_ref, str) and field_ref.startswith('$'):
            field_js = f'd.{field_ref[1:]}'
        else:
            continue
        
        if 'gt' in cond:
            conditions.append(f'{field_js} > {cond["gt"]}')
        elif 'gte' in cond:
            conditions.append(f'{field_js} >= {cond["gte"]}')
        elif 'lt' in cond:
            conditions.append(f'{field_js} < {cond["lt"]}')
        elif 'lte' in cond:
            conditions.append(f'{field_js} <= {cond["lte"]}')
        elif 'eq' in cond:
            conditions.append(f'{field_js} === {cond["eq"]}')
        elif 'ne' in cond:
            conditions.append(f'{field_js} !== {cond["ne"]}')
    
    if not conditions:
        return value_expr
    
    cond_js = ' && '.join(conditions)
    return f'({cond_js}) ? {value_expr} : {else_value}'


def transform_to_js(transform_ops: List[Dict[str, Any]], input_expr: str) -> str:
    """Generate JS for transform array operations."""
    result = input_expr
    for op in transform_ops:
        if 'sqrt' in op and op['sqrt']:
            result = f'Math.sqrt(Math.max(0, {result}))'
        elif 'abs' in op and op['abs']:
            result = f'Math.abs({result})'
        elif 'pow' in op:
            result = f'Math.pow({result}, {op["pow"]})'
        elif 'floor' in op:  # Clamp lower bound
            result = f'Math.max({result}, {op["floor"]})'
        elif 'ceiling' in op:  # Clamp upper bound
            result = f'Math.min({result}, {op["ceiling"]})'
        elif 'clamp' in op:
            bounds = op['clamp']
            if isinstance(bounds, list) and len(bounds) >= 2:
                result = f'Math.max({bounds[0]}, Math.min({bounds[1]}, {result}))'
        elif 'log10' in op and op['log10']:
            result = f'Math.log10(Math.max(1e-10, {result}))'
        elif 'log' in op and op['log']:
            result = f'Math.log(Math.max(1e-10, {result}))'
        elif 'add' in op:
            result = f'({result} + {op["add"]})'
        elif 'mult' in op:
            result = f'({result} * {op["mult"]})'
        elif 'div' in op and op['div'] != 0:
            result = f'({result} / {op["div"]})'
        elif 'round' in op:
            decimals = op['round']
            if decimals is True or decimals == 0:
                result = f'Math.round({result})'
            else:
                factor = 10 ** int(decimals)
                result = f'(Math.round({result} * {factor}) / {factor})'
        elif 'op' in op:
            # Handle {op: 'name', ...} syntax
            op_name = op['op']
            if op_name == 'round':
                decimals = op.get('decimals', 0)
                if decimals == 0:
                    result = f'Math.round({result})'
                else:
                    factor = 10 ** int(decimals)
                    result = f'(Math.round({result} * {factor}) / {factor})'
            elif op_name == 'floor':
                result = f'Math.floor({result})'
            elif op_name in ('ceiling', 'ceil'):
                result = f'Math.ceil({result})'
    return result


def ref_to_js(ref: str) -> str:
    """Convert ref to JS expression."""
    if isinstance(ref, str) and ref.startswith('$'):
        return f'd.{ref[1:]}'
    return str(ref)


class TS013Generator:
    def __init__(self, schema: Dict[str, Any], source: str = ''):
        self.schema = schema
        self.source = source
        self.name = schema.get('name', 'unknown')
        self.version = schema.get('version', 1)
        self.endian = schema.get('endian', 'big')
        self.has_ports = 'ports' in schema
        self.has_commands = 'downlink_commands' in schema
        self.downlink_commands = schema.get('downlink_commands', {})
        self.indent = 0

    def _i(self) -> str:
        return '  ' * self.indent

    def generate(self) -> str:
        lines = []
        lines.append(f'// TS013 Payload Codec — {self.name}')
        lines.append(f'// Schema version: {self.version}')
        if self.source:
            lines.append(f'// Generated from: {self.source}')
        lines.append(f'// DO NOT EDIT — regenerate from schema')
        lines.append('')
        lines.append(self._gen_helpers())
        lines.append('')
        lines.append(self._gen_decode_fields())
        encode_fields = self._gen_encode_fields()
        if encode_fields:
            lines.append('')
            lines.append(encode_fields)
        if self.has_commands:
            lines.append('')
            lines.append(self._gen_command_functions())
        lines.append('')
        lines.append(self._gen_entry_points())
        return '\n'.join(lines)

    def _gen_helpers(self) -> str:
        return '''// --- Binary helpers ---
function readU(buf, pos, size, endian) {
  var v = 0;
  if (endian === 'big') {
    for (var i = 0; i < size; i++) v = (v * 256) + (buf[pos + i] || 0);
  } else {
    for (var i = size - 1; i >= 0; i--) v = (v * 256) + (buf[pos + i] || 0);
  }
  return v;
}

function readS(buf, pos, size, endian) {
  var v = readU(buf, pos, size, endian);
  var sign = Math.pow(2, size * 8 - 1);
  if (v >= sign) v -= sign * 2;
  return v;
}

function readF32(buf, pos, endian) {
  var b = buf.slice(pos, pos + 4);
  if (endian === 'little') b = [b[3], b[2], b[1], b[0]];
  var ab = new ArrayBuffer(4);
  var dv = new DataView(ab);
  for (var i = 0; i < 4; i++) dv.setUint8(i, b[i] || 0);
  return dv.getFloat32(0, false);
}

function readF64(buf, pos, endian) {
  var b = buf.slice(pos, pos + 8);
  if (endian === 'little') b = [b[7], b[6], b[5], b[4], b[3], b[2], b[1], b[0]];
  var ab = new ArrayBuffer(8);
  var dv = new DataView(ab);
  for (var i = 0; i < 8; i++) dv.setUint8(i, b[i] || 0);
  return dv.getFloat64(0, false);
}

function writeU(buf, pos, size, value, endian) {
  value = Math.round(value) >>> 0;
  if (endian === 'big') {
    for (var i = size - 1; i >= 0; i--) { buf[pos + i] = value & 0xFF; value = (value >>> 8); }
  } else {
    for (var i = 0; i < size; i++) { buf[pos + i] = value & 0xFF; value = (value >>> 8); }
  }
}

function writeS(buf, pos, size, value, endian) {
  if (value < 0) value += (1 << (size * 8));
  writeU(buf, pos, size, value, endian);
}'''

    def _gen_decode_fields(self) -> str:
        parts = []
        if self.has_ports:
            for port_key, port_def in self.schema['ports'].items():
                fname = f'decodePort{port_key}'
                fields = port_def.get('fields', [])
                parts.append(self._gen_decode_fn(fname, fields))
        else:
            fields = self.schema.get('fields', [])
            parts.append(self._gen_decode_fn('decodePayload', fields))
        return '\n\n'.join(parts)

    def _gen_decode_fn(self, fname: str, fields: List[Dict]) -> str:
        lines = [f'function {fname}(buf, endian) {{']
        lines.append(f'  var pos = 0, d = {{}}, vars = {{}};')
        lines.append(f'  endian = endian || "{self.endian}";')
        self.indent = 1
        for field in fields:
            lines.extend(self._gen_decode_field(field))
        lines.append('  return { data: d, pos: pos };')
        lines.append('}')
        return '\n'.join(lines)

    def _gen_decode_field(self, field: Dict) -> List[str]:
        lines = []
        i = self._i()

        # byte_group
        if 'byte_group' in field:
            bg = field['byte_group']
            bg_fields = bg if isinstance(bg, list) else bg.get('fields', bg)
            bg_size = field.get('size', 1) if isinstance(bg, dict) else 1
            if isinstance(bg, dict):
                bg_size = bg.get('size', 1)
            lines.append(f'{i}  // byte_group')
            lines.append(f'{i}  var bgStart = pos;')
            lines.append(f'{i}  var bgVal = readU(buf, pos, {bg_size}, endian);')
            for bf in (bg_fields if isinstance(bg_fields, list) else []):
                bname = bf.get('name', '_')
                btype = bf.get('type', 'u8')
                bit_m = re.match(r'u\d+\[(\d+):(\d+)\]', btype)
                if bit_m:
                    lo, hi = int(bit_m.group(1)), int(bit_m.group(2))
                    width = hi - lo + 1
                    mask = (1 << width) - 1
                    lines.append(f'{i}  var {to_js_name(bname)} = (bgVal >> {lo}) & 0x{mask:X};')
                    if not bname.startswith('_'):
                        val_expr = self._apply_modifiers_expr(to_js_name(bname), bf)
                        lines.append(f'{i}  d.{to_js_name(bname)} = {val_expr};')
                    lines.append(f'{i}  vars.{to_js_name(bname)} = {to_js_name(bname)};')
            lines.append(f'{i}  pos = bgStart + {bg_size};')
            return lines

        # flagged
        if 'flagged' in field:
            fg = field['flagged']
            flag_field = fg['field']
            lines.append(f'{i}  // flagged on {flag_field}')
            for group in fg.get('groups', []):
                bit = group['bit']
                lines.append(f'{i}  if (vars.{to_js_name(flag_field)} & (1 << {bit})) {{')
                self.indent += 1
                for gf in group.get('fields', []):
                    lines.extend(self._gen_decode_field(gf))
                self.indent -= 1
                lines.append(f'{i}  }}')
            return lines

        # tlv
        if 'tlv' in field:
            return self._gen_decode_tlv(field['tlv'])

        # match
        if 'match' in field:
            return self._gen_decode_match(field['match'])

        # type: number (computed, decode-only)
        if field.get('type') == 'number':
            name = to_js_name(field['name'])
            
            # Deprecated: formula field
            if 'formula' in field:
                js_formula = formula_to_js(field['formula'])
                lines.append(f'{i}  d.{name} = {js_formula};')
                return lines
            
            # New: ref + polynomial/transform/modifiers
            if 'ref' in field:
                ref_expr = ref_to_js(field['ref'])
                value_expr = ref_expr
                
                # Apply polynomial if present
                if 'polynomial' in field:
                    value_expr = polynomial_to_js(field['polynomial'], ref_expr)
                
                # Apply basic modifiers (mult, div, add) in field key order
                for key in field:
                    if key == 'mult' and field['mult'] is not None:
                        value_expr = f'({value_expr} * {field["mult"]})'
                    elif key == 'div' and field['div'] is not None and field['div'] != 0:
                        value_expr = f'({value_expr} / {field["div"]})'
                    elif key == 'add' and field['add'] is not None:
                        value_expr = f'({value_expr} + {field["add"]})'
                
                # Apply transform array if present
                if 'transform' in field:
                    value_expr = transform_to_js(field['transform'], value_expr)
                
                # Apply guard if present
                if 'guard' in field:
                    value_expr = guard_to_js(field['guard'], value_expr)
                
                lines.append(f'{i}  d.{name} = {value_expr};')
                return lines
            
            # New: compute with optional guard and transform
            if 'compute' in field:
                value_expr = compute_to_js(field['compute'])
                
                # Apply transform if present
                if 'transform' in field:
                    value_expr = transform_to_js(field['transform'], value_expr)
                
                # Apply guard if present
                if 'guard' in field:
                    value_expr = guard_to_js(field['guard'], value_expr)
                
                lines.append(f'{i}  d.{name} = {value_expr};')
                return lines
            
            # Literal value
            if 'value' in field:
                lines.append(f'{i}  d.{name} = {field["value"]};')
                return lines
            
            # Default to 0 if no source specified
            lines.append(f'{i}  d.{name} = 0;')
            return lines

        # regular field
        name = field.get('name', '_unknown')
        ftype = field.get('type', 'u8')
        js_name = to_js_name(name)

        # bitfield_string
        if ftype == 'bitfield_string':
            return self._gen_decode_bitfield_string(field)

        # bit-slice integer (e.g., u8[0:6], u8[7:7], u8[3+:2])
        bit_slice = parse_bit_slice_type(ftype)
        if bit_slice is not None:
            base_type, bit_start, bit_width = bit_slice
            base_size = type_size(base_type)
            if base_size is None:
                lines.append(f'{i}  // TODO: unsupported base type for {ftype}')
                return lines

            eo = field_endian_override(base_type)
            endian_arg = f'"{eo}"' if eo else 'endian'
            mask = (1 << bit_width) - 1
            consume = field.get('consume', 1)

            lines.append(f'{i}  var {js_name}_raw = readU(buf, pos, {base_size}, {endian_arg});')
            lines.append(f'{i}  var {js_name} = ({js_name}_raw >> {bit_start}) & 0x{mask:X};')
            if consume:
                lines.append(f'{i}  pos += {base_size};')

            if field.get('var'):
                lines.append(f'{i}  vars.{to_js_name(field["var"])} = {js_name};')
            lines.append(f'{i}  vars.{js_name} = {js_name};')

            if not name.startswith('_'):
                val_expr = self._apply_modifiers_expr(js_name, field)
                lines.append(f'{i}  d.{js_name} = {val_expr};')

            return lines

        # enum
        if ftype == 'enum':
            base = field.get('base', 'u8')
            sz = type_size(base) or 1
            signed = is_signed(base)
            read_fn = 'readS' if signed else 'readU'
            lines.append(f'{i}  var {js_name}_raw = {read_fn}(buf, pos, {sz}, endian);')
            lines.append(f'{i}  pos += {sz};')
            vals = field.get('values', {})
            val_json = json.dumps({str(k): v for k, v in vals.items()})
            default = field.get('default', None)
            default_js = json.dumps(default) if default else f'{js_name}_raw'
            lines.append(f'{i}  var {js_name}_map = {val_json};')
            lines.append(f'{i}  d.{js_name} = {js_name}_map[{js_name}_raw] !== undefined ? {js_name}_map[{js_name}_raw] : {default_js};')
            lines.append(f'{i}  vars.{js_name} = {js_name}_raw;')
            return lines

        # skip
        if ftype == 'skip':
            length = field.get('length', 1)
            lines.append(f'{i}  pos += {length};')
            return lines

        # string types
        if ftype in ('ascii', 'hex', 'bytes'):
            length = field.get('length', 1)
            if ftype == 'ascii':
                lines.append(f'{i}  var {js_name} = "";')
                lines.append(f'{i}  for (var _si = 0; _si < {length} && pos < buf.length; _si++) {{ {js_name} += String.fromCharCode(buf[pos++]); }}')
            elif ftype == 'hex':
                lines.append(f'{i}  var {js_name} = "";')
                lines.append(f'{i}  for (var _si = 0; _si < {length} && pos < buf.length; _si++) {{ {js_name} += ("0" + buf[pos++].toString(16)).slice(-2); }}')
            else:
                lines.append(f'{i}  var {js_name} = [];')
                lines.append(f'{i}  for (var _si = 0; _si < {length} && pos < buf.length; _si++) {{ {js_name}.push(buf[pos++]); }}')
            if not name.startswith('_'):
                lines.append(f'{i}  d.{js_name} = {js_name};')
            return lines

        # float
        if is_float(ftype):
            sz = type_size(ftype) or 4
            eo = field_endian_override(ftype)
            endian_arg = f'"{eo}"' if eo else 'endian'
            if sz == 4:
                lines.append(f'{i}  var {js_name} = readF32(buf, pos, {endian_arg});')
            else:
                lines.append(f'{i}  var {js_name} = readF64(buf, pos, {endian_arg});')
            lines.append(f'{i}  pos += {sz};')
            if not name.startswith('_'):
                val_expr = self._apply_modifiers_expr(js_name, field)
                lines.append(f'{i}  d.{js_name} = {val_expr};')
            lines.append(f'{i}  vars.{js_name} = {js_name};')
            return lines

        # integer
        sz = type_size(ftype)
        if sz is None:
            lines.append(f'{i}  // TODO: unsupported type {ftype}')
            return lines

        signed = is_signed(ftype)
        read_fn = 'readS' if signed else 'readU'
        eo = field_endian_override(ftype)
        endian_arg = f'"{eo}"' if eo else 'endian'

        lines.append(f'{i}  var {js_name} = {read_fn}(buf, pos, {sz}, {endian_arg});')
        lines.append(f'{i}  pos += {sz};')

        if field.get('var'):
            lines.append(f'{i}  vars.{to_js_name(field["var"])} = {js_name};')
        lines.append(f'{i}  vars.{js_name} = {js_name};')

        if not name.startswith('_'):
            val_expr = self._apply_modifiers_expr(js_name, field)
            lines.append(f'{i}  d.{js_name} = {val_expr};')

        return lines

    def _apply_modifiers_expr(self, raw_var: str, field: Dict) -> str:
        # Deprecated formula takes precedence
        if 'formula' in field:
            js = formula_to_js(field['formula'])
            js = re.sub(r'\bx\b', raw_var, js)
            return js
        
        expr = raw_var
        # Apply modifiers in YAML key order (dict preserves insertion order)
        for key in field:
            if key == 'mult':
                expr = f'({expr} * {field["mult"]})'
            elif key == 'div':
                expr = f'({expr} / {field["div"]})'
            elif key == 'add':
                expr = f'({expr} + {field["add"]})'
        
        # Apply transform array if present (new declarative approach)
        if 'transform' in field:
            expr = transform_to_js(field['transform'], expr)
        
        if 'lookup' in field:
            lk = json.dumps(field['lookup'])
            expr = f'(({lk})[{expr}] !== undefined ? ({lk})[{expr}] : {expr})'
        return expr

    def _reverse_modifiers_expr(self, val_var: str, field: Dict) -> str:
        """Reverse modifier chain in opposite YAML key order: value → raw integer."""
        # Collect modifier keys in YAML order, then reverse
        mod_keys = [k for k in field if k in ('add', 'mult', 'div')]
        expr = val_var
        for key in reversed(mod_keys):
            if key == 'add':
                expr = f'({expr} - ({field["add"]}))'
            elif key == 'div':
                expr = f'({expr} * {field["div"]})'
            elif key == 'mult':
                expr = f'({expr} / {field["mult"]})'
        return f'Math.round({expr})'

    def _gen_decode_bitfield_string(self, field: Dict) -> List[str]:
        i = self._i()
        lines = []
        name = to_js_name(field['name'])
        length = field.get('length', 2)
        parts = field.get('parts', [])
        delim = field.get('delimiter', '.')
        prefix = field.get('prefix', '')

        lines.append(f'{i}  var {name}_raw = readU(buf, pos, {length}, endian);')
        lines.append(f'{i}  pos += {length};')
        seg_exprs = []
        for part in parts:
            offset = part[0]
            width = part[1]
            fmt = part[2] if len(part) > 2 else 'decimal'
            mask = (1 << width) - 1
            extract = f'(({name}_raw >> {offset}) & 0x{mask:X})'
            if fmt == 'hex':
                seg_exprs.append(f'{extract}.toString(16)')
            else:
                seg_exprs.append(f'{extract}.toString()')
        joined = f' + "{delim}" + '.join(seg_exprs)
        if prefix:
            joined = f'"{prefix}" + {joined}'
        lines.append(f'{i}  d.{name} = {joined};')
        return lines

    def _gen_decode_tlv(self, tlv: Dict) -> List[str]:
        i = self._i()
        lines = []
        tag_fields = tlv.get('tag_fields', [])
        cases = tlv.get('cases', {})

        tag_size = sum(type_size(tf.get('type', 'u8')) or 1 for tf in tag_fields)
        lines.append(f'{i}  // TLV loop')
        lines.append(f'{i}  while (pos + {tag_size} <= buf.length) {{')
        lines.append(f'{i}    var _tlvStart = pos;')

        # Read tag fields
        for tf in tag_fields:
            tfname = to_js_name(tf['name'])
            tfsz = type_size(tf.get('type', 'u8')) or 1
            lines.append(f'{i}    var {tfname} = readU(buf, pos, {tfsz}, endian);')
            lines.append(f'{i}    pos += {tfsz};')

        # Build tag key for matching
        if len(tag_fields) == 1:
            tag_key_expr = to_js_name(tag_fields[0]['name'])
            tag_is_composite = False
        else:
            parts = [to_js_name(tf['name']) for tf in tag_fields]
            tag_key_expr = '"[" + ' + ' + ", " + '.join(parts) + ' + "]"'
            tag_is_composite = True

        first = True
        for case_key, case_fields in cases.items():
            # Parse case key (convert to string if needed)
            case_key_str = str(case_key)
            if case_key_str.startswith('['):
                cond = f'{tag_key_expr} === {json.dumps(case_key_str)}'
            else:
                cond = f'{tag_key_expr} === {case_key}'

            kw = 'if' if first else '} else if'
            first = False
            lines.append(f'{i}    {kw} ({cond}) {{')

            self.indent += 2
            for cf in case_fields:
                lines.extend(self._gen_decode_field(cf))
            self.indent -= 2

        if not first:
            lines.append(f'{i}    }} else {{')
            lines.append(f'{i}      break;')
            lines.append(f'{i}    }}')

        lines.append(f'{i}  }}')
        return lines

    def _gen_decode_match(self, match: Dict) -> List[str]:
        i = self._i()
        lines = []
        match_field = match.get('field', '')
        if match_field.startswith('$'):
            match_field = match_field[1:]
        match_var = to_js_name(match_field)
        cases = match.get('cases', {})

        lines.append(f'{i}  // match on {match_var}')
        first = True
        for case_val, case_fields in cases.items():
            kw = 'if' if first else '} else if'
            first = False
            lines.append(f'{i}  {kw} (vars.{match_var} === {case_val}) {{')
            self.indent += 1
            if isinstance(case_fields, list):
                for cf in case_fields:
                    lines.extend(self._gen_decode_field(cf))
            self.indent -= 1
        if not first:
            lines.append(f'{i}  }}')
        return lines

    # ---------------------------------------------------------------
    # Encoder generation
    # ---------------------------------------------------------------
    def _gen_encode_fields(self) -> str:
        parts = []
        if self.has_ports:
            for port_key, port_def in self.schema['ports'].items():
                fname = f'encodePort{port_key}'
                fields = port_def.get('fields', [])
                parts.append(self._gen_encode_fn(fname, fields))
        elif self.has_commands:
            fields = self.schema.get('fields', [])
            parts.append(self._gen_encode_fn('encodePayload', fields))
        return '\n\n'.join(parts)

    def _gen_encode_fn(self, fname: str, fields: List[Dict]) -> str:
        lines = [f'function {fname}(d, endian) {{']
        lines.append(f'  var buf = new Array(256);')
        lines.append(f'  var pos = 0;')
        lines.append(f'  endian = endian || "{self.endian}";')
        self.indent = 1
        for field in fields:
            lines.extend(self._gen_encode_field(field))
        lines.append('  return buf.slice(0, pos);')
        lines.append('}')
        return '\n'.join(lines)

    def _gen_encode_field(self, field: Dict) -> List[str]:
        lines = []
        i = self._i()

        # skip computed fields (formula, ref, or compute)
        if field.get('type') == 'number':
            is_computed = any(k in field for k in ('formula', 'ref', 'compute'))
            if is_computed:
                lines.append(f'{i}  // skip computed field {field.get("name", "")}')
                return lines

        # byte_group
        if 'byte_group' in field:
            bg = field['byte_group']
            bg_fields = bg if isinstance(bg, list) else bg.get('fields', bg)
            bg_size = 1
            if isinstance(bg, dict):
                bg_size = bg.get('size', 1)
            lines.append(f'{i}  // encode byte_group')
            lines.append(f'{i}  var bgVal = 0;')
            for bf in (bg_fields if isinstance(bg_fields, list) else []):
                bname = bf.get('name', '_')
                btype = bf.get('type', 'u8')
                bit_m = re.match(r'u\d+\[(\d+):(\d+)\]', btype)
                if bit_m:
                    lo, hi = int(bit_m.group(1)), int(bit_m.group(2))
                    width = hi - lo + 1
                    mask = (1 << width) - 1
                    src = f'(d.{to_js_name(bname)} || 0)' if not bname.startswith('_') else '0'
                    rev = self._reverse_modifiers_expr(src, bf)
                    lines.append(f'{i}  bgVal |= (({rev}) & 0x{mask:X}) << {lo};')
            lines.append(f'{i}  writeU(buf, pos, {bg_size}, bgVal, endian);')
            lines.append(f'{i}  pos += {bg_size};')
            return lines

        # flagged
        if 'flagged' in field:
            fg = field['flagged']
            flag_field = fg['field']
            groups = fg.get('groups', [])
            lines.append(f'{i}  // encode flagged')
            lines.append(f'{i}  var _flags = 0;')
            # Pre-scan: determine which groups have data
            for group in groups:
                bit = group['bit']
                group_names = [f.get('name') for f in group.get('fields', []) if f.get('name') and not f['name'].startswith('_')]
                if group_names:
                    checks = ' || '.join(f'd.{to_js_name(n)} !== undefined' for n in group_names)
                    lines.append(f'{i}  if ({checks}) _flags |= (1 << {bit});')
            lines.append(f'{i}  writeU(buf, pos - {type_size("u16") or 2}, 2, _flags, endian);')
            # Encode each present group
            for group in groups:
                bit = group['bit']
                lines.append(f'{i}  if (_flags & (1 << {bit})) {{')
                self.indent += 1
                for gf in group.get('fields', []):
                    lines.extend(self._gen_encode_field(gf))
                self.indent -= 1
                lines.append(f'{i}  }}')
            return lines

        # tlv
        if 'tlv' in field:
            return self._gen_encode_tlv(field['tlv'])

        # match — skip during encoding (would need case selection)
        if 'match' in field:
            lines.append(f'{i}  // TODO: match encoding requires case selection')
            return lines

        name = field.get('name', '_unknown')
        ftype = field.get('type', 'u8')
        js_name = to_js_name(name)

        # bitfield_string
        if ftype == 'bitfield_string':
            return self._gen_encode_bitfield_string(field)

        # skip type
        if ftype == 'skip':
            length = field.get('length', 1)
            lines.append(f'{i}  for (var _i = 0; _i < {length}; _i++) buf[pos++] = 0;')
            return lines

        # enum — reverse lookup
        if ftype == 'enum':
            base = field.get('base', 'u8')
            sz = type_size(base) or 1
            vals = field.get('values', {})
            rev = {str(v): k for k, v in vals.items()}
            rev_json = json.dumps(rev)
            lines.append(f'{i}  var {js_name}_rev = {rev_json};')
            lines.append(f'{i}  var {js_name}_val = typeof d.{js_name} === "string" ? parseInt({js_name}_rev[d.{js_name}] || 0) : (d.{js_name} || 0);')
            lines.append(f'{i}  writeU(buf, pos, {sz}, {js_name}_val, endian);')
            lines.append(f'{i}  pos += {sz};')
            return lines

        # string types — skip for now
        if ftype in ('ascii', 'hex', 'bytes'):
            lines.append(f'{i}  // TODO: encode string field {js_name}')
            return lines

        # integer / float
        sz = type_size(ftype)
        if sz is None:
            lines.append(f'{i}  // TODO: unsupported encode type {ftype}')
            return lines

        signed = is_signed(ftype)
        eo = field_endian_override(ftype)
        endian_arg = f'"{eo}"' if eo else 'endian'
        write_fn = 'writeS' if signed else 'writeU'

        if name.startswith('_'):
            const_val = field.get('value', 0)
            lines.append(f'{i}  {write_fn}(buf, pos, {sz}, {const_val}, {endian_arg});')
        elif 'value' in field:
            lines.append(f'{i}  {write_fn}(buf, pos, {sz}, {field["value"]}, {endian_arg});')
        elif 'formula' in field:
            lines.append(f'{i}  // formula field — encode reversal needed')
            lines.append(f'{i}  // formula: {field["formula"]}')
            lines.append(f'{i}  // Provide raw value directly or use modifiers instead')
            lines.append(f'{i}  {write_fn}(buf, pos, {sz}, d.{js_name} || 0, {endian_arg});')
        else:
            src = f'd.{js_name} !== undefined ? d.{js_name} : 0'
            rev = self._reverse_modifiers_expr(f'({src})', field)
            lines.append(f'{i}  {write_fn}(buf, pos, {sz}, {rev}, {endian_arg});')

        lines.append(f'{i}  pos += {sz};')
        return lines

    def _gen_encode_tlv(self, tlv: Dict) -> List[str]:
        i = self._i()
        lines = []
        tag_fields = tlv.get('tag_fields', [])
        cases = tlv.get('cases', {})

        lines.append(f'{i}  // encode TLV entries')
        for case_key, case_fields in cases.items():
            # Parse tag values from case key (convert to string if needed)
            case_key_str = str(case_key)
            if case_key_str.startswith('['):
                tag_vals = json.loads(case_key_str)
            else:
                tag_vals = [int(case_key)]

            # Determine which data fields this case has
            data_names = [cf.get('name') for cf in case_fields if cf.get('name') and not cf['name'].startswith('_')]
            if not data_names:
                continue
            checks = ' || '.join(f'd.{to_js_name(n)} !== undefined' for n in data_names)

            lines.append(f'{i}  if ({checks}) {{')
            # Write tag bytes
            for idx, (tf, tv) in enumerate(zip(tag_fields, tag_vals)):
                tfsz = type_size(tf.get('type', 'u8')) or 1
                lines.append(f'{i}    writeU(buf, pos, {tfsz}, {tv}, endian);')
                lines.append(f'{i}    pos += {tfsz};')
            # Write value fields
            self.indent += 1
            for cf in case_fields:
                lines.extend(self._gen_encode_field(cf))
            self.indent -= 1
            lines.append(f'{i}  }}')

        return lines

    def _gen_encode_bitfield_string(self, field: Dict) -> List[str]:
        i = self._i()
        lines = []
        name = to_js_name(field['name'])
        length = field.get('length', 2)
        parts = field.get('parts', [])
        delim = field.get('delimiter', '.')
        prefix = field.get('prefix', '')

        lines.append(f'{i}  // encode bitfield_string {name}')
        lines.append(f'{i}  var {name}_str = d.{name} || "";')
        if prefix:
            lines.append(f'{i}  if ({name}_str.indexOf("{prefix}") === 0) {name}_str = {name}_str.slice({len(prefix)});')
        lines.append(f'{i}  var {name}_segs = {name}_str.split("{delim}");')
        lines.append(f'{i}  var {name}_val = 0;')
        for idx, part in enumerate(parts):
            offset = part[0]
            width = part[1]
            fmt = part[2] if len(part) > 2 else 'decimal'
            mask = (1 << width) - 1
            radix = 16 if fmt == 'hex' else 10
            lines.append(f'{i}  if ({name}_segs[{idx}]) {name}_val |= (parseInt({name}_segs[{idx}], {radix}) & 0x{mask:X}) << {offset};')
        lines.append(f'{i}  writeU(buf, pos, {length}, {name}_val, endian);')
        lines.append(f'{i}  pos += {length};')
        return lines

    # ---------------------------------------------------------------
    # Downlink Commands
    # ---------------------------------------------------------------
    def _gen_command_functions(self) -> str:
        """Generate functions for encoding/decoding downlink commands."""
        lines = []
        
        # Command ID lookup table
        cmd_ids = {}
        for cmd_name, cmd_def in self.downlink_commands.items():
            cmd_id = cmd_def.get('command_id', 0)
            if isinstance(cmd_id, str) and cmd_id.startswith('0x'):
                cmd_id = int(cmd_id, 16)
            cmd_ids[cmd_name] = cmd_id
        
        lines.append('// --- Downlink Commands ---')
        lines.append(f'var COMMANDS = {json.dumps(cmd_ids)};')
        lines.append('')
        
        # Generate encodeCommand function
        lines.append('function encodeCommand(cmdName, data, endian) {')
        lines.append('  var buf = [];')
        lines.append('  var pos = 0;')
        lines.append('  if (!(cmdName in COMMANDS)) {')
        lines.append('    throw new Error("Unknown command: " + cmdName);')
        lines.append('  }')
        lines.append('  var cmdId = COMMANDS[cmdName];')
        lines.append('  buf[pos++] = cmdId & 0xFF;')
        lines.append('')
        
        # Generate case for each command
        first = True
        for cmd_name, cmd_def in self.downlink_commands.items():
            prefix = 'if' if first else '} else if'
            first = False
            lines.append(f'  {prefix} (cmdName === "{cmd_name}") {{')
            
            fields = cmd_def.get('fields', [])
            for field in fields:
                fname = field.get('name', '')
                ftype = field.get('type', 'u8')
                if fname and not fname.startswith('_'):
                    sz = type_size(ftype) or 1
                    signed = is_signed(ftype)
                    write_fn = 'writeS' if signed else 'writeU'
                    js_name = to_js_name(fname)
                    
                    # Handle modifiers
                    src = f'data.{js_name} !== undefined ? data.{js_name} : 0'
                    rev = self._reverse_modifiers_expr(f'({src})', field)
                    
                    lines.append(f'    {write_fn}(buf, pos, {sz}, {rev}, endian);')
                    lines.append(f'    pos += {sz};')
        
        if self.downlink_commands:
            lines.append('  }')
        
        lines.append('  return buf;')
        lines.append('}')
        lines.append('')
        
        # Generate decodeCommand function
        lines.append('function decodeCommand(buf, endian) {')
        lines.append('  var d = {};')
        lines.append('  var pos = 0;')
        lines.append('  if (buf.length < 1) {')
        lines.append('    throw new Error("Payload too short for command_id");')
        lines.append('  }')
        lines.append('  var cmdId = buf[pos++];')
        lines.append('  d._command_id = cmdId;')
        lines.append('')
        
        # Generate case for each command
        first = True
        for cmd_name, cmd_def in self.downlink_commands.items():
            cmd_id = cmd_def.get('command_id', 0)
            if isinstance(cmd_id, str) and cmd_id.startswith('0x'):
                cmd_id = int(cmd_id, 16)
            
            prefix = 'if' if first else '} else if'
            first = False
            lines.append(f'  {prefix} (cmdId === {cmd_id}) {{')
            lines.append(f'    d._command = "{cmd_name}";')
            
            fields = cmd_def.get('fields', [])
            for field in fields:
                fname = field.get('name', '')
                ftype = field.get('type', 'u8')
                if fname and not fname.startswith('_'):
                    sz = type_size(ftype) or 1
                    signed = is_signed(ftype)
                    read_fn = 'readS' if signed else 'readU'
                    js_name = to_js_name(fname)
                    
                    lines.append(f'    d.{js_name} = {read_fn}(buf, pos, {sz}, endian);')
                    lines.append(f'    pos += {sz};')
                    
                    # Apply modifiers
                    if any(k in field for k in ('mult', 'add', 'div')):
                        mod_expr = f'd.{js_name}'
                        for key in ['mult', 'add', 'div']:
                            if key in field:
                                if key == 'mult':
                                    mod_expr = f'({mod_expr} * {field[key]})'
                                elif key == 'add':
                                    mod_expr = f'({mod_expr} + {field[key]})'
                                elif key == 'div':
                                    mod_expr = f'({mod_expr} / {field[key]})'
                        lines.append(f'    d.{js_name} = {mod_expr};')
        
        if self.downlink_commands:
            lines.append('  } else {')
            lines.append('    d._command = "unknown";')
            lines.append('  }')
        
        lines.append('  return { data: d, pos: pos };')
        lines.append('}')
        
        return '\n'.join(lines)

    # ---------------------------------------------------------------
    # TS013 Entry Points
    # ---------------------------------------------------------------
    def _gen_entry_points(self) -> str:
        lines = []

        if self.has_ports:
            port_map = {}
            for port_key, port_def in self.schema['ports'].items():
                port_map[int(port_key)] = {
                    'direction': port_def.get('direction', 'uplink'),
                }

            # decodeUplink
            lines.append('function decodeUplink(input) {')
            lines.append('  try {')
            lines.append(f'    var endian = "{self.endian}";')
            for port_key in self.schema['ports']:
                direction = self.schema['ports'][port_key].get('direction', 'uplink')
                if direction == 'uplink':
                    lines.append(f'    if (input.fPort === {port_key}) {{')
                    lines.append(f'      var r = decodePort{port_key}(input.bytes, endian);')
                    lines.append(f'      return {{ data: r.data, warnings: [], errors: [] }};')
                    lines.append(f'    }}')
            lines.append(f'    return {{ data: {{}}, warnings: ["Unknown fPort: " + input.fPort], errors: [] }};')
            lines.append('  } catch (e) {')
            lines.append('    return { data: {}, warnings: [], errors: [e.message] };')
            lines.append('  }')
            lines.append('}')
            lines.append('')

            # decodeDownlink
            lines.append('function decodeDownlink(input) {')
            lines.append('  try {')
            lines.append(f'    var endian = "{self.endian}";')
            for port_key in self.schema['ports']:
                direction = self.schema['ports'][port_key].get('direction', 'uplink')
                if direction == 'downlink':
                    lines.append(f'    if (input.fPort === {port_key}) {{')
                    lines.append(f'      var r = decodePort{port_key}(input.bytes, endian);')
                    lines.append(f'      return {{ data: r.data, warnings: [], errors: [] }};')
                    lines.append(f'    }}')
            lines.append(f'    return {{ data: {{}}, warnings: ["Unknown fPort: " + input.fPort], errors: [] }};')
            lines.append('  } catch (e) {')
            lines.append('    return { data: {}, warnings: [], errors: [e.message] };')
            lines.append('  }')
            lines.append('}')
            lines.append('')

            # encodeDownlink
            lines.append('function encodeDownlink(input) {')
            lines.append('  try {')
            lines.append(f'    var endian = "{self.endian}";')
            dl_ports = [pk for pk, pd in self.schema['ports'].items() if pd.get('direction') == 'downlink']
            if dl_ports:
                port = dl_ports[0]
                lines.append(f'    var bytes = encodePort{port}(input.data, endian);')
                lines.append(f'    return {{ bytes: bytes, fPort: {port}, warnings: [], errors: [] }};')
            else:
                lines.append(f'    return {{ bytes: [], fPort: 1, warnings: ["No downlink port defined"], errors: [] }};')
            lines.append('  } catch (e) {')
            lines.append('    return { bytes: [], fPort: 1, warnings: [], errors: [e.message] };')
            lines.append('  }')
            lines.append('}')

        else:
            # No ports — single decode/encode
            lines.append('function decodeUplink(input) {')
            lines.append('  try {')
            lines.append(f'    var r = decodePayload(input.bytes, "{self.endian}");')
            lines.append('    return { data: r.data, warnings: [], errors: [] };')
            lines.append('  } catch (e) {')
            lines.append('    return { data: {}, warnings: [], errors: [e.message] };')
            lines.append('  }')
            lines.append('}')
            lines.append('')

            if self.has_commands:
                # Use command decoding for downlinks
                lines.append('function decodeDownlink(input) {')
                lines.append('  try {')
                lines.append(f'    var r = decodeCommand(input.bytes, "{self.endian}");')
                lines.append('    return { data: r.data, warnings: [], errors: [] };')
                lines.append('  } catch (e) {')
                lines.append('    return { data: {}, warnings: [], errors: [e.message] };')
                lines.append('  }')
                lines.append('}')
                lines.append('')

                lines.append('function encodeDownlink(input) {')
                lines.append('  try {')
                lines.append('    var cmdName = input.data._command;')
                lines.append('    if (!cmdName) {')
                lines.append('      return { bytes: [], fPort: 1, warnings: ["No _command specified"], errors: [] };')
                lines.append('    }')
                lines.append(f'    var bytes = encodeCommand(cmdName, input.data, "{self.endian}");')
                lines.append('    return { bytes: bytes, fPort: 1, warnings: [], errors: [] };')
                lines.append('  } catch (e) {')
                lines.append('    return { bytes: [], fPort: 1, warnings: [], errors: [e.message] };')
                lines.append('  }')
                lines.append('}')
            else:
                lines.append('function decodeDownlink(input) {')
                lines.append('  return { data: {}, warnings: ["No downlink encoding defined"], errors: [] };')
                lines.append('}')
                lines.append('')

                lines.append('function encodeDownlink(input) {')
                lines.append('  return { bytes: [], fPort: 1, warnings: ["No downlink encoding defined"], errors: [] };')
                lines.append('}')

        return '\n'.join(lines)


def fix_yaml_booleans(obj):
    if isinstance(obj, dict):
        return {('on' if k is True else 'off' if k is False else k): fix_yaml_booleans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [fix_yaml_booleans(i) for i in obj]
    return obj


def load_schema(path: Path) -> Dict[str, Any]:
    with open(path) as f:
        schema = yaml.safe_load(f)
    return fix_yaml_booleans(schema)


def main():
    parser = argparse.ArgumentParser(description='Generate TS013 JS codec from Payload Schema YAML')
    parser.add_argument('input', help='Schema file or directory')
    parser.add_argument('-o', '--output', help='Output file or directory')
    args = parser.parse_args()

    input_path = Path(args.input)
    if input_path.is_file():
        files = [input_path]
    else:
        files = sorted(list(input_path.glob('*.yaml')) + list(input_path.glob('*.yml')))
        files = [f for f in files if f.stem.lower() != 'readme']

    output_path = Path(args.output) if args.output else None

    for schema_path in files:
        try:
            schema = load_schema(schema_path)
            if not isinstance(schema, dict):
                continue
            if 'fields' not in schema and 'ports' not in schema:
                continue

            gen = TS013Generator(schema, schema_path.name)
            js = gen.generate()

            if output_path:
                if output_path.suffix == '.js':
                    out = output_path
                else:
                    output_path.mkdir(parents=True, exist_ok=True)
                    out = output_path / (schema_path.stem.replace('-', '_') + '_codec.js')
                out.write_text(js)
                print(f'Generated: {out}')
            else:
                print(js)
        except Exception as e:
            print(f'Error: {schema_path.name}: {e}', file=sys.stderr)


if __name__ == '__main__':
    main()
