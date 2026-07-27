#!/usr/bin/env python3
"""
Generate standalone TTN-compatible JavaScript decoders from Payload Schema YAML.

Creates self-contained decoder files that can be uploaded directly to TTN Console.
"""

import json
import sys
import yaml
from pathlib import Path
from typing import Dict, Any

JS_TEMPLATE = '''// TTN Payload Decoder - {name}
// Schema Version: {version}
// Generated from: {source}
// 
// Upload this file to TTN Console > Applications > Payload Formatters

// Embedded schema
var SCHEMA = {schema_json};

// ============================================================================
// Decoder Implementation
// ============================================================================

function decodeUplink(input) {{
  try {{
    var decoded = decode(input.bytes, SCHEMA);
    return {{
      data: decoded,
      warnings: [],
      errors: []
    }};
  }} catch (e) {{
    return {{
      data: {{}},
      warnings: [],
      errors: [e.message]
    }};
  }}
}}

function decode(bytes, schema) {{
  var buf = new ByteBuffer(bytes, schema.endian || 'big');
  var result = {{}};
  
  if (schema.fields) {{
    decodeFields(buf, schema.fields, result, schema);
  }}
  
  return result;
}}

function decodeFields(buf, fields, result, schema) {{
  var variables = {{}};
  
  for (var i = 0; i < fields.length; i++) {{
    var field = fields[i];
    
    // Handle $ref
    if (field['$ref']) {{
      var refPath = field['$ref'].replace('#/definitions/', '');
      var refDef = schema.definitions && schema.definitions[refPath];
      if (refDef && refDef.fields) {{
        decodeFields(buf, refDef.fields, result, schema);
      }}
      continue;
    }}
    
    // Handle byte_group
    if (field.byte_group) {{
      var groupStart = buf.pos;
      for (var j = 0; j < field.byte_group.length; j++) {{
        var gf = field.byte_group[j];
        var gval = decodeField(buf, gf, variables, schema);
        if (!gf.name.startsWith('_')) {{
          result[gf.name] = gval;
        }}
        // Don't advance position for grouped fields
        buf.pos = groupStart;
      }}
      buf.pos = groupStart + (field.size || 1);
      continue;
    }}
    
    // Handle match/conditional
    if (field.type === 'match') {{
      var matchVal = variables[field.on.replace('$', '')];
      var cases = field.cases || [];
      var matched = false;
      
      for (var c = 0; c < cases.length; c++) {{
        var caseItem = cases[c];
        if (matchCase(matchVal, caseItem['case'])) {{
          if (caseItem.fields) {{
            decodeFields(buf, caseItem.fields, result, schema);
          }}
          matched = true;
          break;
        }}
      }}
      
      if (!matched && field['default'] === 'skip') {{
        // Skip unknown
      }} else if (!matched && field['default'] === 'error') {{
        throw new Error('No matching case for value: ' + matchVal);
      }}
      continue;
    }}
    
    // Regular field
    var rawValue = decodeFieldRaw(buf, field, variables, schema);
    var value = applyModifiers(rawValue, field);
    
    // Store variable (use raw value for match comparisons)
    if (field['var']) {{
      variables[field['var']] = rawValue;
    }}
    
    // Skip internal fields
    if (field.name && !field.name.startsWith('_')) {{
      result[field.name] = value;
    }}
  }}
}}

function matchCase(value, pattern) {{
  if (pattern === undefined || pattern === null) return false;
  if (typeof pattern === 'number') return value === pattern;
  if (Array.isArray(pattern)) return pattern.indexOf(value) >= 0;
  if (typeof pattern === 'string' && pattern.indexOf('..') >= 0) {{
    var parts = pattern.split('..');
    var lo = parseInt(parts[0]);
    var hi = parseInt(parts[1]);
    return value >= lo && value <= hi;
  }}
  return value === pattern;
}}

function decodeFieldRaw(buf, field, variables, schema) {{
  var fieldType = field.type;
  var consume = field.consume !== undefined ? field.consume : null;
  
  // Handle nested object - return as-is (no modifiers apply)
  if (fieldType === 'object') {{
    var obj = {{}};
    decodeFields(buf, field.fields || [], obj, schema);
    return obj;
  }}
  
  // Handle enum - return raw value, let applyModifiers handle lookup
  if (fieldType === 'enum') {{
    var base = field.base || 'u8';
    return readType(buf, base, consume);
  }}
  
  // Handle skip
  if (fieldType === 'skip') {{
    buf.pos += field.length || 1;
    return undefined;
  }}
  
  // Parse bitfield syntax
  var bitInfo = parseBitfield(fieldType);
  if (bitInfo) {{
    var byteVal = buf.peekByte();
    var extracted = (byteVal >> bitInfo.start) & ((1 << bitInfo.width) - 1);
    if (consume === 1 || (consume === null && bitInfo.consumeDefault)) {{
      buf.pos += 1;
    }}
    return extracted;
  }}
  
  // Standard types
  return readType(buf, fieldType, consume, field.length);
}}

function parseBitfield(type) {{
  // u8[3:4] - Python slice
  var m = type.match(/^u(\\d+)\\[(\\d+):(\\d+)\\]$/);
  if (m) {{
    return {{ start: parseInt(m[2]), width: parseInt(m[3]) - parseInt(m[2]) + 1, consumeDefault: false }};
  }}
  
  // u8[3+:2] - Verilog part-select
  m = type.match(/^u(\\d+)\\[(\\d+)\\+:(\\d+)\\]$/);
  if (m) {{
    return {{ start: parseInt(m[2]), width: parseInt(m[3]), consumeDefault: false }};
  }}
  
  // bits<3,2> - C++ template
  m = type.match(/^bits<(\\d+),(\\d+)>$/);
  if (m) {{
    return {{ start: parseInt(m[1]), width: parseInt(m[2]), consumeDefault: false }};
  }}
  
  // bits:2@3 - @ notation
  m = type.match(/^bits:(\\d+)@(\\d+)$/);
  if (m) {{
    return {{ start: parseInt(m[2]), width: parseInt(m[1]), consumeDefault: false }};
  }}
  
  // u8:2 - Sequential
  m = type.match(/^u(\\d+):(\\d+)$/);
  if (m) {{
    return {{ start: 0, width: parseInt(m[2]), consumeDefault: false }};
  }}
  
  return null;
}}

function readType(buf, type, consume, length) {{
  var typeMap = {{
    'u8': [1, false], 'uint8': [1, false],
    's8': [1, true], 'i8': [1, true], 'int8': [1, true],
    'u16': [2, false], 'uint16': [2, false],
    's16': [2, true], 'i16': [2, true], 'int16': [2, true],
    'u24': [3, false],
    's24': [3, true],
    'u32': [4, false], 'uint32': [4, false],
    's32': [4, true], 'i32': [4, true], 'int32': [4, true],
    'f32': [4, 'float'], 'float': [4, 'float'],
    'f64': [8, 'double'], 'double': [8, 'double'],
    'bool': [1, 'bool'],
  }};
  
  var info = typeMap[type];
  if (info) {{
    var size = info[0];
    var signed = info[1];
    
    if (signed === 'float') {{
      return buf.readFloat32();
    }} else if (signed === 'double') {{
      return buf.readFloat64();
    }} else if (signed === 'bool') {{
      return buf.readByte() !== 0;
    }} else {{
      return buf.readInt(size, signed);
    }}
  }}
  
  // String types
  if (type === 'ascii' || type === 'string') {{
    return buf.readString(length || 1);
  }}
  
  if (type === 'hex') {{
    return buf.readHex(length || 1);
  }}
  
  if (type === 'bytes') {{
    return buf.readBytes(length || 1);
  }}
  
  // Unknown type, try as u8
  return buf.readByte();
}}

function applyModifiers(value, field) {{
  if (field.formula) {{
    var x = value;
    try {{ value = eval(field.formula); }} catch(e) {{}}
    return value;
  }}
  
  if (field.mult !== undefined) value = value * field.mult;
  if (field.div !== undefined) value = value / field.div;
  if (field.add !== undefined) value = value + field.add;
  
  // Handle lookup tables
  if (field.lookup) {{
    if (Array.isArray(field.lookup)) {{
      value = field.lookup[value] !== undefined ? field.lookup[value] : value;
    }} else {{
      value = field.lookup[value] !== undefined ? field.lookup[value] : value;
    }}
  }}
  
  // Handle enum values (for enum type fields)
  if (field.values) {{
    if (Array.isArray(field.values)) {{
      value = field.values[value] !== undefined ? field.values[value] : ('unknown(' + value + ')');
    }} else {{
      value = field.values[value] !== undefined ? field.values[value] : ('unknown(' + value + ')');
    }}
  }}
  
  return value;
}}

// ============================================================================
// ByteBuffer - Binary parsing utility
// ============================================================================

function ByteBuffer(bytes, endian) {{
  this.bytes = bytes;
  this.pos = 0;
  this.endian = endian || 'big';
}}

ByteBuffer.prototype.peekByte = function() {{
  return this.bytes[this.pos] || 0;
}};

ByteBuffer.prototype.readByte = function() {{
  return this.bytes[this.pos++] || 0;
}};

ByteBuffer.prototype.readInt = function(size, signed) {{
  var value = 0;
  if (this.endian === 'big') {{
    for (var i = 0; i < size; i++) {{
      value = (value << 8) | (this.bytes[this.pos++] || 0);
    }}
  }} else {{
    for (var i = 0; i < size; i++) {{
      value = value | ((this.bytes[this.pos++] || 0) << (8 * i));
    }}
  }}
  
  if (signed && size < 5) {{
    var signBit = 1 << (size * 8 - 1);
    if (value & signBit) {{
      value = value - (signBit << 1);
    }}
  }}
  
  return value;
}};

ByteBuffer.prototype.readFloat32 = function() {{
  var bytes = [];
  for (var i = 0; i < 4; i++) bytes.push(this.bytes[this.pos++] || 0);
  if (this.endian === 'little') bytes.reverse();
  var buf = new ArrayBuffer(4);
  var view = new DataView(buf);
  for (var i = 0; i < 4; i++) view.setUint8(i, bytes[i]);
  return view.getFloat32(0, false);
}};

ByteBuffer.prototype.readFloat64 = function() {{
  var bytes = [];
  for (var i = 0; i < 8; i++) bytes.push(this.bytes[this.pos++] || 0);
  if (this.endian === 'little') bytes.reverse();
  var buf = new ArrayBuffer(8);
  var view = new DataView(buf);
  for (var i = 0; i < 8; i++) view.setUint8(i, bytes[i]);
  return view.getFloat64(0, false);
}};

ByteBuffer.prototype.readString = function(len) {{
  var s = '';
  for (var i = 0; i < len && this.pos < this.bytes.length; i++) {{
    var c = this.bytes[this.pos++];
    if (c === 0) break;
    s += String.fromCharCode(c);
  }}
  return s;
}};

ByteBuffer.prototype.readHex = function(len) {{
  var s = '';
  for (var i = 0; i < len && this.pos < this.bytes.length; i++) {{
    var b = this.bytes[this.pos++];
    s += ('0' + b.toString(16)).slice(-2).toUpperCase();
  }}
  return s;
}};

ByteBuffer.prototype.readBytes = function(len) {{
  var arr = [];
  for (var i = 0; i < len && this.pos < this.bytes.length; i++) {{
    arr.push(this.bytes[this.pos++]);
  }}
  return arr;
}};
'''


def fix_yaml_booleans(obj):
    """Fix YAML 1.1 boolean keys (on/off/yes/no interpreted as True/False)."""
    if isinstance(obj, dict):
        fixed = {}
        for k, v in obj.items():
            # YAML 1.1 interprets 'on' as True, 'off' as False
            if k is True:
                k = 'on'
            elif k is False:
                k = 'off'
            fixed[k] = fix_yaml_booleans(v)
        return fixed
    elif isinstance(obj, list):
        return [fix_yaml_booleans(item) for item in obj]
    return obj


def load_schema(path: Path) -> Dict[str, Any]:
    """Load schema from YAML or JSON file."""
    content = path.read_text()
    if path.suffix in ['.yaml', '.yml']:
        schema = yaml.safe_load(content)
        return fix_yaml_booleans(schema)
    else:
        return json.loads(content)


def generate_decoder(schema: Dict[str, Any], source_name: str) -> str:
    """Generate standalone JavaScript decoder from schema."""
    name = schema.get('name', 'unknown')
    version = schema.get('version', 1)
    
    # Clean schema for embedding (remove test_vectors, metadata, etc.)
    clean_schema = {
        'name': name,
        'version': version,
        'endian': schema.get('endian', 'big'),
        'fields': schema.get('fields', []),
    }
    
    if 'definitions' in schema:
        clean_schema['definitions'] = schema['definitions']
    
    schema_json = json.dumps(clean_schema, indent=2)
    
    return JS_TEMPLATE.format(
        name=name,
        version=version,
        source=source_name,
        schema_json=schema_json
    )


def main():
    """Generate decoders for all schemas in a directory."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate TTN decoders from schemas')
    parser.add_argument('input', help='Schema file or directory')
    parser.add_argument('-o', '--output', default='generated-decoders',
                        help='Output directory')
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    if input_path.is_file():
        files = [input_path]
    else:
        files = list(input_path.glob('*.yaml')) + list(input_path.glob('*.json'))
        # Exclude README and other non-schema files
        files = [f for f in files if f.stem.lower() != 'readme']
    
    for schema_path in sorted(files):
        try:
            schema = load_schema(schema_path)
            if not isinstance(schema, dict) or 'fields' not in schema:
                print(f"Skipping {schema_path.name}: not a valid schema")
                continue
            
            js_code = generate_decoder(schema, schema_path.name)
            
            out_name = schema_path.stem.replace('-', '_') + '_decoder.js'
            out_path = output_dir / out_name
            out_path.write_text(js_code)
            
            print(f"Generated: {out_path}")
            
        except Exception as e:
            print(f"Error processing {schema_path.name}: {e}")
    
    print(f"\nDecoders written to: {output_dir}/")


if __name__ == '__main__':
    main()
