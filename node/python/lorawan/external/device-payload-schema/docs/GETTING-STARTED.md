# Getting Started for Sensor Vendors

Create one schema, generate codecs for all platforms.

## What You Get

```
Your Schema (YAML)
       │
       ├──► JavaScript codec (TTN, ChirpStack, Helium)
       ├──► Python codec (testing, data pipelines)
       ├──► C header (embedded firmware)
       └──► JSON Schema (API documentation)
```

## 5-Minute Example

### 1. Create Your Schema

Create `schemas/mycompany/temp-sensor.yaml`:

```yaml
name: mycompany_temp_sensor
version: 1
description: "MyCompany Temperature Sensor v1.0"
endian: big

fields:
  - name: temperature
    type: s16
    div: 100
    unit: "°C"
  
  - name: humidity
    type: u8
    unit: "%"
  
  - name: battery
    type: u8
    div: 10
    unit: "V"

test_vectors:
  - name: "normal_reading"
    input: "09C44121"
    output:
      temperature: 25.0
      humidity: 65
      battery: 3.3
  
  - name: "cold_reading"
    input: "FF38281E"
    output:
      temperature: -2.0
      humidity: 40
      battery: 3.0
```

**Payload breakdown:**
- `09C4` = 2500 → 2500/100 = 25.0°C
- `41` = 65 → 65%
- `21` = 33 → 33/10 = 3.3V

### 2. Validate Your Schema

```bash
python tools/validate_schema.py schemas/mycompany/temp-sensor.yaml -v
```

Output:
```
✓ Schema valid
✓ Test vector 'normal_reading' passed
✓ Test vector 'cold_reading' passed
All 2 test vectors passed
```

### 3. Generate Codecs

**JavaScript (for TTN/ChirpStack):**
```bash
python tools/generate_ts013_codec.py schemas/mycompany/temp-sensor.yaml -o output/
```

**C Header (for firmware):**
```bash
python tools/generate-c.py schemas/mycompany/temp-sensor.yaml -o include/temp_sensor_codec.h
```

### 4. Check Quality Score

```bash
python tools/score_schema.py schemas/mycompany/temp-sensor.yaml
```

Output:
```
Schema: mycompany_temp_sensor
Score: 85/100 (Silver)

✓ Schema valid (12/12)
✓ Has test vectors (8/8)
✓ Python tests pass (20/20)
✓ JS tests pass (15/15)
△ Branch coverage: 80% (10/12)
△ Edge cases: partial (4/8)
✗ Semantic annotations missing (0/20)

Recommendations:
- Add negative temperature test vector
- Add minimum payload test
- Add IPSO/SenML annotations for interoperability
```

## Using the Sensor Library

Build schemas faster using pre-defined sensor types with IPSO annotations already included.

### Quick Start with Library

```yaml
name: my_env_sensor
version: 1
endian: big

fields:
  - $ref: "schemas/library/common/headers.yaml#/definitions/msg_type_header"
  - $ref: "schemas/library/profiles/env-sensor.yaml#/definitions/temp_humidity"
  - $ref: "schemas/library/sensors/power.yaml#/definitions/battery_mv"
```

### Process Schema

```bash
# Resolve library references
python tools/schema_preprocessor.py schemas/mycompany/my_env_sensor.yaml -o schemas/mycompany/my_env_sensor_resolved.yaml

# Validate the resolved schema
python tools/validate_schema.py schemas/mycompany/my_env_sensor_resolved.yaml -v
```

### Available Sensor Types

| Category | Library File | Sensors |
|----------|--------------|---------|
| Environmental | `schemas/library/sensors/environmental.yaml` | temperature, humidity, pressure, CO2, TVOC, illuminance |
| Power | `schemas/library/sensors/power.yaml` | battery_mv, battery_pct, voltage, current, power, energy |
| Position | `schemas/library/sensors/position.yaml` | latitude, longitude, altitude, accelerometer, gyroscope |
| Digital | `schemas/library/sensors/digital.yaml` | digital_input, digital_output, counter, presence |
| Distance | `schemas/library/sensors/distance.yaml` | distance_mm, level_pct, radar |
| Flow | `schemas/library/sensors/flow.yaml` | flow_rate, total_volume |

### Sensor Profiles (Pre-built Combinations)

| Profile | File | Contents |
|---------|------|----------|
| `temp_humidity` | `schemas/library/profiles/env-sensor.yaml` | Temperature + Humidity |
| `temp_humidity_pressure` | `schemas/library/profiles/env-sensor.yaml` | + Pressure |
| `indoor_air_quality` | `schemas/library/profiles/env-sensor.yaml` | + CO2 + TVOC |
| `gps_basic` | `schemas/library/profiles/tracker.yaml` | Lat + Lon + Alt |
| `full_tracker` | `schemas/library/profiles/tracker.yaml` | GPS + Speed + Heading + Battery |

### Multiple Sensors of Same Type

Use `rename:` or `prefix:` when you have multiple sensors:

```yaml
fields:
  # Two temperature sensors
  - $ref: "schemas/library/sensors/environmental.yaml#/definitions/temperature_c"
    rename:
      temperature: indoor_temp
      
  - $ref: "schemas/library/sensors/environmental.yaml#/definitions/temperature_c"
    rename:
      temperature: outdoor_temp

  # Or use prefix for groups
  - $ref: "schemas/library/profiles/env-sensor.yaml#/definitions/temp_humidity"
    prefix: "zone1_"
    
  - $ref: "schemas/library/profiles/env-sensor.yaml#/definitions/temp_humidity"
    prefix: "zone2_"
```

### Benefits of Using the Library

1. **IPSO annotations included** - Automatic interoperability scoring boost
2. **Consistent scaling** - Standard units and precision across devices
3. **Less typing** - Common patterns ready to use
4. **SenML units** - RFC 8428 compliance built-in

See `schemas/library/README.md` for the complete library reference.

## Common Patterns

### Signed vs Unsigned

```yaml
# Unsigned (0 to 65535)
- name: distance
  type: u16
  unit: "mm"

# Signed (-32768 to 32767)
- name: temperature
  type: s16
  div: 100
  unit: "°C"
```

### Scaling Values

```yaml
# Device sends 2500, decoder outputs 25.00
- name: temperature
  type: s16
  div: 100

# Device sends 33, decoder outputs 3.3
- name: battery
  type: u8
  div: 10
```

### Boolean Flags

```yaml
- name: motion_detected
  type: bool

- name: door_open
  type: bool
```

### Enumerations

```yaml
- name: status
  type: u8
  lookup:
    0: "ok"
    1: "low_battery"
    2: "sensor_error"
    3: "tamper"
```

### Optional Sensor Groups (Flagged)

When your device has optional sensors controlled by a flags byte:

```yaml
fields:
  - name: flags
    type: u8
  
  - flagged:
      field: flags
      groups:
        - bit: 0
          fields:
            - name: temperature
              type: s16
              div: 100
        - bit: 1
          fields:
            - name: humidity
              type: u8
```

Payload with both: `03 09C4 41` (flags=0x03, temp, humidity)
Payload temp only: `01 09C4` (flags=0x01, temp only)

### Computed Fields

When one value derives from others:

```yaml
- name: temp_raw
  type: u16

- name: temperature
  type: number
  ref: $temp_raw
  transform:
    - sub: 4000
    - div: 100
  unit: "°C"
```

## Adding Semantic Annotations

For interoperability with IoT platforms, add standard annotations:

```yaml
- name: temperature
  type: s16
  div: 100
  unit: "°C"
  ipso: {object: 3303, instance: 0, resource: 5700}
  senml: {name: "temp", unit: "Cel"}
  semantic: "temperature.air"
```

This enables automatic conversion to IPSO Smart Objects, SenML (RFC 8428), and TTN normalized format.

## Test Vector Best Practices

Include test vectors for:

1. **Normal operation** - Typical readings
2. **Boundary values** - Min/max sensor range
3. **Negative values** - For signed types
4. **Edge cases** - Zero, maximum, minimum payload
5. **All flag combinations** - For flagged schemas

```yaml
test_vectors:
  - name: "normal"
    input: "09C44121"
    output: {temperature: 25.0, humidity: 65, battery: 3.3}
  
  - name: "max_temp"
    input: "7FFF6428"
    output: {temperature: 327.67, humidity: 100, battery: 4.0}
  
  - name: "negative_temp"
    input: "FF38281E"
    output: {temperature: -2.0, humidity: 40, battery: 3.0}
  
  - name: "minimum_payload"
    input: "000000"
    output: {temperature: 0.0, humidity: 0, battery: 0.0}
```

## Directory Structure

```
schemas/
└── mycompany/
    ├── temp-sensor.yaml
    ├── door-sensor.yaml
    └── multi-sensor.yaml

output/
└── mycompany-temp-sensor/
    ├── codec.js          # TS013 JavaScript codec
    ├── output-schema.json # JSON Schema for decoded data
    └── scoring.json      # Quality score report
```

## Next Steps

1. **[Sensor Library](../schemas/library/README.md)** - Pre-built sensor definitions with IPSO mappings
2. **[Schema Language Reference](SCHEMA-LANGUAGE-REFERENCE.md)** - Full field type and modifier documentation
3. **[Output Formats](OUTPUT-FORMATS.md)** - IPSO, SenML, TTN normalized output
4. **[Bidirectional Codec](BIDIRECTIONAL-CODEC.md)** - Downlink encoding for device configuration
5. **[C Code Generation](C-CODE-GENERATION.md)** - Embedded firmware integration

## Getting Help

- Check existing schemas in `schemas/` for examples
- Run `python tools/validate_schema.py --help` for options
- Quality scoring tool explains what's missing
