# Device Payload Schema - Frequently Asked Questions

## General

### What is this?

A declarative schema format for defining LoRaWAN device payloads. Define your payload structure in YAML, use interpreters and generators to decode payloads and generate codecs.

### Why use schemas instead of JavaScript codecs?

| Aspect | JavaScript Codecs | Schema-Driven |
|--------|-------------------|---------------|
| File size | 2-50 KB per device | 200-500 bytes |
| Security | Arbitrary code execution | Data only |
| Portability | JS runtime required | Any language |
| Validation | Manual testing | Automatic with test vectors |
| Maintenance | Edit code | Edit data |

### What tools are included?

| Tool | Purpose |
|------|---------|
| `validate_schema.py` | Validate schema syntax and test vectors |
| `score_schema.py` | Rate schema completeness |
| `schema_preprocessor.py` | Resolve cross-file references |
| `generate_ts013_codec.py` | Generate JavaScript codec |
| `generate-c.py` | Generate C header for firmware |
| `schema_interpreter.py` | Python decoder |

---

## Schema Creation

### How do I create a schema from scratch?

Start with this template:

```yaml
name: my_sensor
version: 1
endian: big

fields:
  - name: temperature
    type: s16
    div: 10
    unit: "°C"
    
  - name: humidity
    type: u8
    unit: "%"

test_vectors:
  - name: normal
    payload: "00E7 32"
    expected:
      temperature: 23.1
      humidity: 50
```

### Can I generate a schema from a datasheet?

Use an LLM-assisted workflow:

1. Feed the datasheet payload format to an LLM (Claude, ChatGPT)
2. Reference the sensor library examples
3. Validate output with `validate_schema.py`
4. Score with `score_schema.py`
5. Iterate until passing

### How do I validate my schema?

```bash
python tools/validate_schema.py my_schema.yaml -v
```

This checks:
- YAML syntax
- Field type validity
- Test vector results

### How do I check schema quality?

```bash
python tools/score_schema.py my_schema.yaml
```

Scores based on:
- Valid schema structure
- Test vector coverage
- IPSO/SenML annotations
- Edge case coverage

---

## Sensor Library

### Is there a library of pre-built sensor definitions?

Yes. The `schemas/library/` directory contains common sensors with scaling and IPSO mappings:

| Category | File | Sensors |
|----------|------|---------|
| Environmental | `schemas/library/sensors/environmental.yaml` | temperature, humidity, pressure, CO2, TVOC |
| Power | `schemas/library/sensors/power.yaml` | battery_mv, battery_pct, voltage, current |
| Position | `schemas/library/sensors/position.yaml` | GPS, accelerometer, gyroscope |
| Digital | `schemas/library/sensors/digital.yaml` | digital I/O, counter, presence |

### How do I use library definitions?

Reference them with `$ref`:

```yaml
fields:
  - $ref: "schemas/library/sensors/environmental.yaml#/definitions/temperature_c"
  - $ref: "schemas/library/sensors/power.yaml#/definitions/battery_mv"
```

Then run the preprocessor:

```bash
python tools/schema_preprocessor.py my_schema.yaml -o my_schema_resolved.yaml
```

### How do I handle multiple sensors of the same type?

Use `rename:` or `prefix:`:

```yaml
fields:
  - $ref: "schemas/library/sensors/environmental.yaml#/definitions/temperature_c"
    rename:
      temperature: indoor_temp
      
  - $ref: "schemas/library/sensors/environmental.yaml#/definitions/temperature_c"
    rename:
      temperature: outdoor_temp
```

Or with prefix for groups:

```yaml
fields:
  - $ref: "schemas/library/profiles/env-sensor.yaml#/definitions/temp_humidity"
    prefix: "zone1_"
```

---

## Interpreters

### What interpreters are available?

| Language | File | Notes |
|----------|------|-------|
| Go | `go/schema/schema.go` | Full feature support |
| Python | `tools/schema_interpreter.py` | Full feature support |

### How do I decode a payload in Python?

```python
from schema_interpreter import SchemaInterpreter

interp = SchemaInterpreter('my_schema.yaml')
result = interp.decode(bytes.fromhex('00E732'))
print(result.data)
# {'temperature': 23.1, 'humidity': 50}
```

### How do I decode in Go?

```go
import "payload-codec-proto/go/schema"

s, _ := schema.ParseSchema(schemaYAML)
result, _ := s.Decode(payload)
```

---

## Code Generation

### How do I generate a JavaScript codec?

```bash
python tools/generate_ts013_codec.py my_schema.yaml -o output/
```

Generates a TS013-compatible codec for TTN, ChirpStack, Helium.

### How do I generate C code for firmware?

```bash
python tools/generate-c.py my_schema.yaml -o include/codec.h
```

Generates struct definitions and encode/decode functions.

### Can I generate JSON Schema for API documentation?

```bash
python tools/generate_jsonschema.py my_schema.yaml -o output/
```

---

## Data Types

### What field types are supported?

| Type | Description | Example |
|------|-------------|---------|
| `u8`, `u16`, `u32` | Unsigned integers | Counters, battery |
| `s8`, `s16`, `s32` | Signed integers | Temperature, coordinates |
| `bool` | Boolean (1 byte) | Flags |
| `bits` | Bit field extraction | Status flags |
| `float16` | IEEE 754 half-precision | Sensor readings |
| `bytes` | Raw byte array | MAC address, EUI |

### How do I handle scaling?

Use `mult`, `div`, or `add`:

```yaml
- name: temperature
  type: s16
  div: 10        # Raw 231 → 23.1

- name: humidity
  type: u8
  mult: 0.5      # Raw 100 → 50.0

- name: temp_offset
  type: u16
  div: 10
  add: -40       # With offset
```

### How do I handle enumerations?

Use `lookup`:

```yaml
- name: status
  type: u8
  lookup:
    0: "ok"
    1: "low_battery"
    2: "error"
```

---

## Complex Structures

### How do I parse TLV (Type-Length-Value) payloads?

```yaml
fields:
  - type: tlv
    tag_size: 1
    cases:
      1:
        - name: temperature
          type: s16
          div: 10
      2:
        - name: humidity
          type: u8
```

### How do I parse based on a message type header?

Use `match`:

```yaml
fields:
  - name: msg_type
    type: u8
    
  - type: match
    field: msg_type
    cases:
      1:
        - name: temperature
          type: s16
      2:
        - name: gps_lat
          type: s32
```

### How do I parse bit flags?

Use `bits`:

```yaml
- name: status_flags
  type: bits
  bits:
    - name: motion
      size: 1
    - name: tamper
      size: 1
    - name: low_battery
      size: 1
    - name: reserved
      size: 5
```

---

## Migration

### How do I convert an existing JavaScript codec?

1. Analyze the codec to identify payload structure
2. Create YAML schema matching the structure
3. Test with known payloads
4. Validate with `validate_schema.py`

Converter tools exist for some vendors:
- `convert_milesight.py` - Milesight devices
- `convert_decentlab.py` - Decentlab devices

### What codecs can't be converted?

Codecs with these features may not convert:
- Compression (Huffman, delta)
- Encryption
- CRC validation within payload
- Complex state-dependent logic

---

## Troubleshooting

### Schema validation fails

Check:
- YAML syntax (indentation, colons)
- Field type spelling (`u16` not `uint16`)
- Test vector hex format (spaces optional)

### Test vectors don't match

Verify:
- Endianness (`endian: big` or `endian: little`)
- Scaling factors (`div`, `mult`, `add`)
- Signed vs unsigned types

### Preprocessor can't find library files

Add library paths:

```bash
python tools/schema_preprocessor.py my_schema.yaml -L ../lib -o output.yaml
```

Or check that `schemas/library/` is in the expected location relative to your schema.

---

## Performance

### How fast is the schema interpreter?

Benchmarks show 200,000-400,000 decodes/second in Python, sufficient for any LoRaWAN deployment.

### What's the schema size?

| Format | Size |
|--------|------|
| YAML | 500-2000 bytes |
| JSON | 400-1500 bytes |
| Binary (compact) | 100-400 bytes |
