# Output Format Comparison

The Payload Schema decoder can output data in multiple formats for different platforms and standards.

> **Note:** Output formats (IPSO, SenML, TTN) are a **network-side concern only**. 
> This applies to BOTH directions:
> - **Uplink:** Device encodes values→bytes, Network decodes bytes→JSON→IPSO/SenML
> - **Downlink:** Network encodes config→bytes, Device decodes bytes→values
>
> The device never sees semantic formats - it only converts between values and bytes.
> This keeps device firmware simple and small (~2KB).

## Example

**Schema:** Environmental sensor with temperature, humidity, pressure, CO2, battery  
**Payload:** `092982140C03520D` (8 bytes)

---

## 1. Raw Format (Default)

Simple flat dictionary - easiest to use in applications.

```json
{
  "temperature": 23.45,
  "humidity": 65.0,
  "pressure": 1013.2,
  "co2": 850,
  "battery": 3.3
}
```

**Use case:** Direct application use, custom backends, simple integrations.

---

## 2. IPSO Smart Objects Format

OMA LwM2M standard object IDs - interoperable with LwM2M servers.

```json
{
  "3303": {
    "value": 23.45,
    "unit": "°C"
  },
  "3304": {
    "value": 65.0,
    "unit": "%RH"
  },
  "3315": {
    "value": 1013.2,
    "unit": "hPa"
  },
  "3325": {
    "value": 850,
    "unit": "ppm"
  },
  "3316": {
    "value": 3.3,
    "unit": "V"
  }
}
```

**IPSO Object Reference:**
| Object ID | Name | Typical Use |
|-----------|------|-------------|
| 3200 | Digital Input | Binary sensors, switches |
| 3202 | Analog Input | Generic analog readings |
| 3301 | Illuminance | Light sensors (lux) |
| 3302 | Presence | Motion/occupancy sensors |
| 3303 | Temperature | Temperature sensors (°C) |
| 3304 | Humidity | Relative humidity (%) |
| 3308 | Set Point | Thermostat targets, setpoints |
| 3314 | Magnetometer | Compass, magnetic field |
| 3315 | Barometer | Atmospheric pressure |
| 3316 | Voltage | Battery voltage, power supply |
| 3317 | Current | Electrical current (A) |
| 3322 | Load | Weight, force sensors |
| 3323 | Pressure | Pressure sensors (Pa, bar) |
| 3325 | Concentration | CO2, gas sensors (ppm) |
| 3328 | Power | Power measurement (W) |
| 3330 | Distance | Range, level sensors (m) |
| 3331 | Energy | Energy consumption (Wh, kWh) |
| 3334 | Gyrometer | Angular velocity |
| 3336 | Location | GPS coordinates |
| 3337 | Positioner | Valve position, actuators (%) |
| 3347 | Push Button | Button press events |

**Use case:** LwM2M platforms (Leshan, Wakaama), cloud IoT services, OMA-compliant systems.

---

## 3. SenML Format (RFC 8428)

IETF Sensor Measurement Lists standard.

```json
[
  {
    "n": "temperature",
    "v": 23.45,
    "u": "°C"
  },
  {
    "n": "humidity",
    "v": 65.0,
    "u": "%RH"
  },
  {
    "n": "pressure",
    "v": 1013.2,
    "u": "hPa"
  },
  {
    "n": "co2",
    "v": 850,
    "u": "ppm"
  },
  {
    "n": "battery",
    "v": 3.3,
    "u": "V"
  }
]
```

**SenML Fields:**
- `n` - name
- `v` - value (numeric)
- `vs` - value (string)
- `vb` - value (boolean)
- `u` - unit
- `t` - time (optional)
- `bt` - base time (optional)

**Use case:** CoAP integration, CBOR encoding, RFC-compliant systems.

---

## 4. TTN Normalized Format

The Things Network v3 payload format with `normalized_payload`.

```json
{
  "decoded_payload": {
    "temperature": 23.45,
    "humidity": 65.0,
    "pressure": 1013.2,
    "co2": 850,
    "battery": 3.3
  },
  "normalized_payload": [
    {
      "measurement": {
        "temperature": {
          "value": 23.45,
          "unit": "°C"
        }
      }
    },
    {
      "measurement": {
        "humidity": {
          "value": 65.0,
          "unit": "%RH"
        }
      }
    },
    {
      "measurement": {
        "pressure": {
          "value": 1013.2,
          "unit": "hPa"
        }
      }
    },
    {
      "measurement": {
        "co2": {
          "value": 850,
          "unit": "ppm"
        }
      }
    },
    {
      "measurement": {
        "battery": {
          "value": 3.3,
          "unit": "V"
        }
      }
    }
  ]
}
```

**Use case:** The Things Network, TTN Console, TTN integrations, Cayenne LPP compatibility.

---

## Format Comparison

| Format | Structure | Size | Interoperability | Best For |
|--------|-----------|------|------------------|----------|
| **Raw** | Flat dict | Smallest | Application-specific | Custom backends |
| **IPSO** | Object-based | Medium | High (OMA/LwM2M) | LwM2M platforms |
| **SenML** | Record array | Medium | High (IETF/CoAP) | RFC-compliant systems |
| **TTN** | Normalized | Largest | TTN ecosystem | TTN integrations |

---

## Schema Definition

To enable semantic output formats, add `semantic` annotations to fields:

```yaml
fields:
  - name: temperature
    type: s16
    mult: 0.01
    unit: "°C"
    semantic:
      ipso: 3303
      senml: "urn:dev:ow:temp"
      
  - name: humidity
    type: u8
    mult: 0.5
    unit: "%RH"
    semantic:
      ipso: 3304
```

---

## API Usage

### Python

```python
from schema_interpreter import SchemaInterpreter

interpreter = SchemaInterpreter(schema)
result = interpreter.decode(payload)

# Raw format (default)
raw = result.data

# IPSO format
ipso = interpreter.get_semantic_output(result.data, 'ipso')

# SenML format
senml = interpreter.get_semantic_output(result.data, 'senml')

# TTN format
ttn = interpreter.get_semantic_output(result.data, 'ttn')
```

### Network Server Integration

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  LoRaWAN Device │────▶│  Network Server │────▶│  Application    │
│                 │     │                 │     │                 │
│  Uplink Payload │     │  Decode + Format│     │  IPSO/SenML/TTN │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

The network server can:
1. Decode payload using schema
2. Transform to target format based on application requirements
3. Forward to appropriate backend (LwM2M, MQTT, HTTP, etc.)

---

## Output JSON Schema

Each device schema can generate a corresponding **Output JSON Schema** that describes
the structure of the decoded payload. This enables validation of decoder output with
standard JSON Schema tools.

### Generation

```bash
python tools/generate_output_schema.py schemas/my-device.yaml > my-device-output.schema.json
```

### Example Output Schema

For a temperature/humidity sensor:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://lorawan-schema.org/devices/temp_humidity/v1/output",
  "title": "temp_humidity Decoded Payload",
  "description": "Temperature and humidity sensor",
  "type": "object",
  "properties": {
    "temperature": {
      "type": "number",
      "description": "Unit: °C. Valid range: [-40, 85]"
    },
    "humidity": {
      "type": "number",
      "description": "Unit: %. Valid range: [0, 100]"
    },
    "battery": {
      "type": "number",
      "description": "Unit: V. Valid range: [2.0, 3.6]"
    }
  },
  "additionalProperties": true
}
```

### Validation Usage

```javascript
const Ajv = require('ajv');
const ajv = new Ajv();

const outputSchema = require('./my-device-output.schema.json');
const validate = ajv.compile(outputSchema);

const decoded = decodeUplink(input);
const valid = validate(decoded.data);

if (!valid) {
  console.error('Decoder output validation failed:', validate.errors);
}
```

### Benefits

| Benefit | Description |
|---------|-------------|
| **Type Safety** | Ensures decoder output matches expected types |
| **Documentation** | Schema serves as API documentation |
| **Integration** | Standard format for API contracts |
| **Testing** | Automated validation in CI/CD pipelines |
| **Tooling** | IDE autocomplete from schema |

### Deliverables per Device

For each device schema, the following artifacts SHOULD be generated:

1. **YAML Schema** (`device.yaml`) - Source payload definition
2. **JS Codec** (`device-codec.js`) - TS013-compliant decoder/encoder
3. **Output Schema** (`device-output.schema.json`) - JSON Schema for decoded payload

---

## Format-Specific JSON Schemas

Different output formats have different validation schemas:

| Format | Schema | Scope |
|--------|--------|-------|
| **Raw** | Per-device generated | Device-specific fields |
| **IPSO** | `schemas/ipso-output.schema.json` | Generic structure |
| **SenML** | `schemas/senml-output.schema.json` | RFC 8428 compliant |
| **TTN** | `schemas/ttn-output.schema.json` | TTN normalized format |

### Raw Format Schema (Per-Device)

Generated by `generate_output_schema.py` - validates device-specific field names and types.

```bash
python tools/generate_output_schema.py device.yaml -o device-output.schema.json
```

### IPSO Format Schema (Generic)

Validates the IPSO object structure (object IDs as keys, value/unit properties):

```json
{
  "3303": {"value": 23.45, "unit": "Cel"},
  "3304": {"value": 65.0, "unit": "%RH"}
}
```

Location: `schemas/ipso-output.schema.json`

### SenML Format Schema (RFC 8428)

Validates SenML record arrays per IETF RFC 8428:

```json
[
  {"n": "temperature", "v": 23.45, "u": "Cel"},
  {"n": "humidity", "v": 65.0, "u": "%RH"}
]
```

Location: `schemas/senml-output.schema.json`

### TTN Normalized Format Schema

Validates The Things Network v3 format with `decoded_payload` and `normalized_payload`:

```json
{
  "decoded_payload": {"temperature": 23.45},
  "normalized_payload": [
    {"measurement": {"temperature": {"value": 23.45, "unit": "Cel"}}}
  ]
}
```

Location: `schemas/ttn-output.schema.json`

### Multi-Format Validation Example

```javascript
const Ajv = require('ajv');
const ajv = new Ajv();

// Load schemas
const rawSchema = require('./device-output.schema.json');
const ipsoSchema = require('./schemas/ipso-output.schema.json');
const senmlSchema = require('./schemas/senml-output.schema.json');
const ttnSchema = require('./schemas/ttn-output.schema.json');

// Validate based on output format
function validateOutput(data, format) {
  const schemas = {
    'raw': rawSchema,
    'ipso': ipsoSchema,
    'senml': senmlSchema,
    'ttn': ttnSchema
  };
  
  const validate = ajv.compile(schemas[format]);
  return validate(data) ? null : validate.errors;
}
```
