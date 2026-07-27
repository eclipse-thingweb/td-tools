# Future Features Roadmap

Status of semantic enhancements for the Payload Schema language.

---

## Implemented Features

### `valid_range` ✓

Declarative bounds for expected output values. Unlike `clamp` (which modifies values), this validates and flags out-of-range readings.

**Schema Syntax:**
```yaml
- name: temperature
  type: s16
  div: 100
  unit: "°C"
  valid_range: [-40, 85]    # Expected operating range
```

**Interpreter Behavior:**
```python
# Decode result includes quality flags
{
    "temperature": 23.45,
    "_quality": {
        "temperature": "good"  # or "out_of_range"
    }
}

# Out-of-range example (sensor reads -999 on wire break)
{
    "temperature": -999.0,
    "_warnings": ["temperature: value -999.0 outside valid range [-40, 85]"],
    "_quality": {
        "temperature": "out_of_range"
    }
}
```

**Use Cases:**
- Detect sensor failures (broken wire reads as extreme value)
- Quality indicators in cloud platforms
- Defensive firmware that rejects bad readings

---

### `resolution` ✓

Documents the minimum detectable change. Useful for fixed-point scaling decisions.

**Schema Syntax:**
```yaml
- name: temperature
  type: s16
  div: 100
  unit: "°C"
  resolution: 0.01    # 0.01°C steps
```

**Interpreter Behavior:**
- Included in schema metadata output
- Exposed in SenML/IPSO extended attributes

---

### `unece` ✓

UNECE Recommendation 20 standardized unit codes for IoT interoperability.

**Schema Syntax:**
```yaml
- name: temperature
  type: s16
  div: 100
  unit: "°C"
  unece: "CEL"        # UNECE code for Celsius
```

**Common UNECE Codes:**
| Measurement | Code | Display |
|-------------|------|---------|
| Temperature (C) | CEL | °C |
| Temperature (F) | FAH | °F |
| Humidity | P1 | % |
| Pressure (Pa) | PAL | Pa |
| Pressure (bar) | BAR | bar |
| Voltage | VLT | V |
| Current | AMP | A |
| Distance (m) | MTR | m |
| Distance (mm) | MMT | mm |

**Use Cases:**
- Automatic unit conversion between systems
- SenML unit standardization
- LwM2M/IPSO interoperability
- Industrial IoT standards compliance

---

## Planned Features

### Embedded Code Generation Enhancements

Generate bounds checking and constants from semantic fields:

```c
// From valid_range
#define SENSOR_TEMP_MIN  (-40.0f)
#define SENSOR_TEMP_MAX  (85.0f)

typedef struct {
    float temperature;          /* °C, valid: -40 to 85 */
    uint8_t temperature_valid;  /* 1 if in range */
} sensor_t;

// From resolution
#define SENSOR_TEMP_RESOLUTION  0.01f
#define SENSOR_TEMP_SCALE       100     /* 1/resolution */
```

### Output Format Extensions

**SenML (RFC 8428 extended):**
```json
[
  {
    "n": "temperature",
    "v": 23.45,
    "u": "Cel",
    "vmin": -40,
    "vmax": 85
  }
]
```

**IPSO/LwM2M:**
```json
{
  "3303": {
    "5700": 23.45,
    "5701": "°C",
    "5603": -40,
    "5604": 85
  }
}
```
(5603 = Min Range Value, 5604 = Max Range Value per OMA registry)

---

## Out of Scope: Device Profile Metadata

The following fields are **intentionally excluded** from the payload schema. They describe static sensor characteristics that belong in device profiles/registries, not codec definitions.

### `accuracy`

Measurement accuracy (e.g., ±0.5°C) is a datasheet value that:
- Doesn't affect payload decoding
- May vary by device instance (calibration)
- Already exists in device databases (TTN Device Repository, manufacturer specs)

### `instrument_range`

Physical sensor limits (e.g., -55 to 125°C) vs operating range:
- Doesn't affect payload decoding  
- Static hardware specification
- Available from device profiles

### Rationale

**Schema scope:** Binary payload → JSON transformation (including quality flags)

**Device profile scope:** Static sensor characteristics (accuracy, instrument limits, calibration data)

This separation:
1. **Avoids bifurcation** - device metadata stays in one place
2. **Keeps schemas focused** - codec transformation, not device catalog
3. **Enables instance variation** - accuracy/calibration may differ per device
4. **Matches platform architecture** - integration layers join decoded values with device profile at runtime

---

## Implementation Notes

### Schema Validation

Implemented in `validate_schema.py`:

```yaml
valid_range:
  type: array
  items: number
  minItems: 2
  maxItems: 2

resolution:
  type: number
  exclusiveMinimum: 0

unece:
  type: string
  pattern: "^[A-Z0-9]{2,3}$"
```

### Backward Compatibility

All semantic fields are optional. Existing schemas continue to work unchanged.

---

## Status Summary

| Feature | Status | Runtime | Code Gen |
|---------|--------|---------|----------|
| `valid_range` | ✓ Implemented | Quality flags | Planned |
| `resolution` | ✓ Implemented | Metadata | Planned |
| `unece` | ✓ Implemented | Metadata | N/A |
| `accuracy` | Out of scope | N/A | N/A |
| `instrument_range` | Out of scope | N/A | N/A |

---

## Related Standards

- **UNECE Rec 20** - Codes for Units of Measure
- **OMA LwM2M** - Object 3303 (Temperature), resources 5603/5604 (Min/Max Range)
- **RFC 8428** - SenML (Sensor Measurement Lists)
- **IEEE 1451** - Smart Transducer Interface (TEDS metadata)
