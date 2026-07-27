# TTN Codec Conversion Guide

Complete guide for AI-assisted conversion of The Things Network device repository
codecs to Payload Schema format.

## Overview

This guide covers the end-to-end workflow for converting TTN JavaScript codecs
to declarative Payload Schema YAML files. The process is designed for AI-assisted
development with human verification.

### Benefits of Conversion

| Before (JS) | After (YAML Schema) |
|-------------|---------------------|
| 200+ lines of hand-written JavaScript | 30-50 lines of declarative YAML |
| Platform-specific (TTN only) | Generate for any platform |
| Manual testing | Automatic test vector validation |
| No type information | Full type metadata for validation |
| Hard to review for correctness | Human-verifiable structure |

## Prerequisites

### Environment Setup

```bash
# Clone the repository
git clone https://github.com/lorawan-schema/payload-codec.git
cd payload-codec

# Create Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python tools/schema_interpreter.py --help
```

### Required Tools

| Tool | Purpose | Command |
|------|---------|---------|
| `schema_interpreter.py` | Decode payloads using schema | `python tools/schema_interpreter.py decode` |
| `generate_ts013_codec.py` | Generate JS codec from schema | `python tools/generate_ts013_codec.py` |
| `validate_schema.py` | Validate schema structure | `python tools/validate_schema.py -f` |
| `score_schema.py` | Run quality scoring | `python tools/score_schema.py` |

## Conversion Workflow

### Phase 1: Analyze Source Codec

1. **Locate the TTN codec** in the device repository:
   ```
   vendor/{vendor-name}/{device-model}/codec.js
   ```

2. **Identify key elements:**
   - Byte order (big-endian is default for LoRaWAN)
   - Field types and positions
   - Arithmetic transformations (scaling, offsets)
   - Conditional logic (message types, flags)
   - Computed fields (formulas, cross-field calculations)

3. **Extract test vectors** from existing tests or create from datasheet examples.

### Phase 2: Create Schema

#### Basic Structure

```yaml
# Device identification
name: vendor_device_model
version: 1
endian: big  # Most LoRaWAN devices use big-endian

# Field definitions
fields:
  - name: field_name
    type: u16        # Field type
    div: 100         # Arithmetic modifier
    unit: "°C"       # Optional unit

# Test vectors for validation
test_vectors:
  - name: test_name
    payload: "01 02 03 04"
    expected:
      field_name: 2.56
```

#### Field Type Reference

| JS Pattern | Schema Type | Notes |
|------------|-------------|-------|
| `bytes[i]` | `u8` | Unsigned byte |
| `(bytes[i] << 8) \| bytes[i+1]` | `u16` | Big-endian 16-bit |
| `bytes[i] \| (bytes[i+1] << 8)` | `u16` + `endian: little` | Little-endian |
| `bytes.readInt16BE(i)` | `i16` | Signed 16-bit |
| `bytes[i] & 0x0F` | `u8[0:3]` | Lower nibble |
| `(bytes[i] >> 4) & 0x0F` | `u8[4:7]` | Upper nibble |

#### Modifier Mapping

| JS Pattern | Schema Modifier |
|------------|-----------------|
| `raw / 100` | `div: 100` |
| `raw * 0.01` | `mult: 0.01` |
| `raw - 40` | `add: -40` |
| `(raw - 400) / 10` | `add: -400` then `div: 10` |

**Important:** YAML key order determines modifier application order.

```yaml
# Pattern: (raw - 400) / 10
- name: temperature
  type: u16
  add: -400
  div: 10

# Pattern: (raw / 10) - 40
- name: temperature
  type: i16
  div: 10
  add: -40
```

#### Conditional Parsing

**Flag-based groups (Decentlab pattern):**

```yaml
fields:
  - name: flags
    type: u16
    
  - flagged:
      field: flags
      groups:
        - bit: 0
          fields:
            - name: temperature
              type: i16
              div: 10
        - bit: 1
          fields:
            - name: humidity
              type: u8
```

**Message type switching:**

```yaml
fields:
  - name: message_type
    type: u8
    
  - match:
      field: $message_type
      cases:
        1:
          - name: sensor_data
            type: u16
        2:
          - name: config_data
            type: u8
```

#### Computed Fields

**Polynomial calibration (replaces complex formulas):**

```yaml
- name: raw_value
  type: u16
  div: 50

- name: calibrated_value
  type: number
  ref: $raw_value
  polynomial: [0.0000043, -0.00055, 0.0292, -0.053]
```

**Cross-field computation:**

```yaml
- name: reflected
  type: u16
  div: 10

- name: incoming
  type: u16
  div: 10

- name: ratio
  type: number
  compute:
    op: div
    a: $reflected
    b: $incoming
  guard:
    when:
      - field: $incoming
        gt: 0
    else: 0
```

**Transform operations:**

```yaml
- name: raw_power
  type: u16

- name: power_db
  type: number
  ref: $raw_power
  transform:
    - div: 1000
    - log10: true
    - mult: 10
  unit: "dB"
```

### Phase 3: Validate Schema

#### Step 1: Schema Validation

```bash
python tools/validate_schema.py -f schemas/vendor/device.yaml
```

Expected output:
```
schemas/vendor/device.yaml: OK
```

#### Step 2: Test with Sample Payload

```bash
python tools/schema_interpreter.py decode \
  schemas/vendor/device.yaml \
  "01 23 45 67 89"
```

#### Step 3: Run Quality Scoring

```bash
python tools/score_schema.py schemas/vendor/device.yaml -v
```

Target: **GOLD tier (85%+)** for production use.

### Phase 4: Generate Outputs

#### Generate TS013 JavaScript Codec

```bash
python tools/generate_ts013_codec.py schemas/vendor/device.yaml > codec.js
```

#### Generate JSON Schema for Output Validation

```bash
python -c "
import yaml, json, sys
sys.path.insert(0, 'path/to/la-payload-schema/reference-impl/python')
from payload_schema import generate_json_schema

with open('schemas/vendor/device.yaml') as f:
    schema = yaml.safe_load(f)
print(json.dumps(generate_json_schema(schema), indent=2))
" > output-schema.json
```

#### Generate C Firmware Codec

```bash
python tools/generate_firmware_codec.py schemas/vendor/device.yaml > codec.h
```

### Phase 5: Cross-Validate

Compare generated JS output with original TTN codec:

```bash
# Test with Node.js
node -e "
const orig = require('./original_codec.js');
const gen = require('./generated_codec.js');

const payload = Buffer.from('0123456789', 'hex');
const input = { bytes: payload, fPort: 1 };

console.log('Original:', JSON.stringify(orig.decodeUplink(input)));
console.log('Generated:', JSON.stringify(gen.decodeUplink(input)));
"
```

## Test Vector Guidelines

### Minimum Requirements

| Category | Minimum Vectors | Purpose |
|----------|-----------------|---------|
| Normal operation | 2-3 | Typical sensor readings |
| Edge cases | 2-3 | Zero, max, boundary values |
| Branch coverage | 1 per branch | All conditional paths |
| Error cases | 1-2 | Invalid/truncated payloads |

### Test Vector Format

```yaml
test_vectors:
  - name: normal_reading
    description: "Typical temperature and humidity"
    payload: "01 00 E7 32"
    expected:
      temperature: 23.1
      humidity: 50

  - name: zero_values
    description: "All sensors at zero"
    payload: "01 00 00 00"
    expected:
      temperature: 0.0
      humidity: 0

  - name: max_values
    description: "Maximum sensor values"
    payload: "01 FF FF FF"
    expected:
      temperature: 655.35
      humidity: 255
```

### Payload Format

- Use hex bytes separated by spaces: `"01 23 45"`
- Or continuous hex string: `"012345"`
- Expected values should match decoded output types

## Quality Tiers

| Tier | Score | Requirements |
|------|-------|--------------|
| **Platinum** | 95-100% | Full coverage, cross-validation, all edge cases |
| **Gold** | 85-94% | Strong coverage, cross-validation passing |
| **Silver** | 70-84% | Good coverage, Python tests passing |
| **Bronze** | 50-69% | Basic validation, some test vectors |

### Scoring Components

| Component | Weight | How to Improve |
|-----------|--------|----------------|
| Schema Validation | 20% | Fix structural errors |
| Test Vectors | 20% | Add more test cases |
| Python Tests | 25% | Fix failing assertions |
| JS Cross-Validation | 15% | Ensure JS codec matches |
| Branch Coverage | 10% | Test all switch/flagged branches |
| Edge Cases | 10% | Add zero/max/negative tests |

## Common Conversion Patterns

### Pattern 1: Simple Sensor

**Original JS:**
```javascript
function decodeUplink(input) {
  var data = {};
  data.temperature = ((input.bytes[0] << 8) | input.bytes[1]) / 100;
  data.humidity = input.bytes[2];
  return { data: data };
}
```

**Schema YAML:**
```yaml
name: simple_sensor
endian: big
fields:
  - name: temperature
    type: u16
    div: 100
    unit: "°C"
  - name: humidity
    type: u8
    unit: "%"
```

### Pattern 2: Signed Temperature

**Original JS:**
```javascript
var raw = (input.bytes[0] << 8) | input.bytes[1];
if (raw > 32767) raw -= 65536;  // Sign extend
data.temperature = raw / 10;
```

**Schema YAML:**
```yaml
- name: temperature
  type: i16    # Signed type handles sign extension
  div: 10
  unit: "°C"
```

### Pattern 3: Bitfield Extraction

**Original JS:**
```javascript
data.battery_low = (input.bytes[0] >> 7) & 1;
data.motion = (input.bytes[0] >> 6) & 1;
data.tamper = (input.bytes[0] >> 5) & 1;
```

**Schema YAML:**
```yaml
- byte_group:
    - name: battery_low
      type: u8[7:7]
    - name: motion
      type: u8[6:6]
    - name: tamper
      type: u8[5:5]
```

### Pattern 4: TLV (Tag-Length-Value)

**Original JS:**
```javascript
var i = 0;
while (i < input.bytes.length) {
  var tag = input.bytes[i++];
  var len = input.bytes[i++];
  var value = input.bytes.slice(i, i + len);
  // Process based on tag...
  i += len;
}
```

**Schema YAML:**
```yaml
- name: records
  type: tlv
  tag_size: 1
  length_size: 1
  tags:
    0x01:
      name: temperature
      type: i16
      div: 10
    0x02:
      name: humidity
      type: u8
```

### Pattern 5: Formula to Polynomial

**Original JS:**
```javascript
// Topp equation for soil moisture
var e = raw / 50;
data.vwc = 4.3e-6 * Math.pow(e, 3) - 5.5e-4 * Math.pow(e, 2) + 0.0292 * e - 0.053;
```

**Schema YAML:**
```yaml
- name: dielectric
  type: u16
  div: 50

- name: vwc
  type: number
  ref: $dielectric
  polynomial: [0.0000043, -0.00055, 0.0292, -0.053]
  unit: "m³/m³"
```

## AI-Assisted Workflow

### Prompt Template for AI Conversion

```
Convert this TTN JavaScript codec to Payload Schema YAML format:

```javascript
[paste original codec here]
```

Requirements:
1. Use Payload Schema YAML format
2. Include test_vectors section with at least 3 test cases
3. Use declarative constructs (polynomial, compute, guard) instead of formulas
4. Add unit annotations where known
5. Handle all conditional branches (switch, flagged)

Reference the schema language documentation for syntax.
```

### Verification Checklist

After AI generates a schema:

- [ ] Schema validates: `python tools/validate_schema.py -f schema.yaml`
- [ ] Test vectors pass: `python tools/score_schema.py schema.yaml`
- [ ] JS codec generates without errors
- [ ] Cross-validation matches original codec output
- [ ] All conditional branches have test coverage
- [ ] Edge cases (zero, max, negative) are tested

## Troubleshooting

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| "Unknown type" | Invalid field type | Use standard types (u8, u16, i16, etc.) |
| "Buffer underflow" | Payload too short | Check field positions and lengths |
| "Variable not found" | Bad field reference | Ensure `$field` references exist earlier |
| "Division by zero" | Compute without guard | Add `guard: {when: [...], else: 0}` |

### Debugging Tips

1. **Add intermediate fields** to see values at each step
2. **Use verbose decode** to trace field extraction
3. **Compare byte-by-byte** between original and generated codec
4. **Check endianness** - LoRaWAN uses big-endian by default

## Output Directory Structure

For each converted device, generate:

```
output/vendor-device/
├── schema.yaml           # Source schema definition
├── codec.js              # Generated TS013 JavaScript codec
├── output-schema.json    # JSON Schema for decoded output
└── scoring.json          # Quality scoring report
```

## Resources

- [Schema Language Reference](SCHEMA-LANGUAGE-REFERENCE.md)
- [Formula Migration Guide](FORMULA-MIGRATION-TRACKING.md)
- [TS013 Compliance Analysis](TS013-COMPLIANCE-ANALYSIS.md)
- [TTN Device Repository](https://github.com/TheThingsNetwork/lorawan-devices)
