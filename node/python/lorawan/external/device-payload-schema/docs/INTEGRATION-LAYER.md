# Integration Layer Design

How decoded payloads are transformed into WoT Thing Descriptions, SenML, IPSO,
and other output formats by adding deployment-specific context.

## The Problem

The device schema produces decoded JSON:

```json
{"temperature": 23.45, "humidity": 65.0, "battery_voltage": 3.276}
```

Different consumers need this same data in different shapes:

| Consumer | Needs | Example |
|----------|-------|---------|
| LwM2M server | IPSO object paths | `{"3303/0/5700": 23.45}` |
| Time-series DB | SenML with site URN | `[{"bn":"urn:site:farm_a:","n":"temperature","v":23.45}]` |
| WoT directory | Thing Description | `{"@type":"saref:Temperature","unit":"CEL"}` |
| Legacy SCADA | Renamed fields | `{"ZONE_TEMP_01": 23.45}` |
| Azure Digital Twins | DTDL model | `{"modelId":"dtmi:example:Sensor;1"}` |

The device manufacturer cannot know all of these at schema design time.
The deployer knows them at installation time.

## Two-Layer Architecture

```
DEVICE SCHEMA (manufacturer defines at design time)
┌──────────────────────────────────────────────────┐
│  Binary structure    type: s16, div: 10           │
│  Physical units      unit: "°C", unece: "CEL"     │
│  IPSO object type    ipso: 3303                   │
│  Device-local inst.  instance: 0, 1, 2            │
│  Field names         temperature, soil_temp_10cm   │
└──────────────────────┬───────────────────────────┘
                       │
              Decoded JSON + field metadata
                       │
                       ▼
INTEGRATION LAYER (deployer configures at install time)
┌──────────────────────────────────────────────────┐
│  Output format       senml, ipso, wot_td, json    │
│  Identity            URNs, base names, thing IDs  │
│  Field mapping       temperature → ZONE_TEMP_01   │
│  Semantic types      saref:Temperature             │
│  Security            bearer tokens, API keys       │
│  Routing             per-destination endpoints     │
└──────────────────────────────────────────────────┘
```

## Decoder Output: The Integration Boundary

The TS013 decoder outputs plain JSON. The interpreter also exposes field
metadata via `get_field_metadata()`:

```python
interpreter = SchemaInterpreter(schema)
result = interpreter.decode(payload)
metadata = interpreter.get_field_metadata()
```

**Decoded values:**
```json
{
  "temperature": 23.45,
  "humidity": 65.0,
  "battery_voltage": 3.276
}
```

**Field metadata** (from schema annotations):
```json
{
  "temperature": {
    "unit": "°C",
    "unece": "CEL",
    "ipso": 3303,
    "valid_range": [-40, 125],
    "resolution": 0.1
  },
  "humidity": {
    "unit": "%RH",
    "unece": "P1",
    "ipso": 3304
  },
  "battery_voltage": {
    "unit": "V",
    "unece": "VLT",
    "ipso": 3316
  }
}
```

This is the contract between the decoder and the integration layer. The
integration layer consumes both the decoded values and the metadata to
produce format-specific outputs.

## Integration Profile

Each device deployment has an integration profile that configures one or more
output destinations:

```yaml
device_eui: "0011223344556677"
schema: schemas/env_sensor.yaml

variables:
  site: "campus_north"
  zone: "bldg_3_floor_2"

destinations:
  - id: lwm2m_server
    format: ipso
    endpoint: coap://leshan.example.com

  - id: analytics
    format: senml
    endpoint: mqtt://broker.example.com/sensors
    context:
      base_name: "urn:site:${site}:${zone}:"

  - id: wot_directory
    format: wot_td
    endpoint: https://wot.example.com/things
    context:
      thing_id: "urn:dev:lorawan:${device_eui}"
      title: "Env Sensor - ${zone}"
      security: {scheme: bearer, in: header}
      semantic_types:
        _thing: "saref:Sensor"
        temperature: "saref:Temperature"
        humidity: "saref:Humidity"

  - id: scada
    format: json
    endpoint: https://bas.example.com/api
    context:
      field_map:
        temperature: "ZONE_TEMP_01"
        humidity: "ZONE_RH_01"
        battery_voltage: "SENSOR_VBAT"
```

## Protocol Converters

Each output format has a protocol converter that combines decoded values,
field metadata, and integration context into the target format:

```
                    decoded JSON
                        │
                    field metadata
                        │
                  integration context
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │  SenML   │  │  WoT TD  │  │  IPSO    │  ...
    │converter │  │converter │  │converter │
    └────┬─────┘  └────┬─────┘  └────┬─────┘
         │             │             │
         ▼             ▼             ▼
    SenML JSON    Thing Desc.   IPSO JSON
```

Each converter has built-in knowledge of its target format. The integration
profile provides only configuration — never format-specific syntax.

### What Each Converter Needs

| Converter | From Schema | From Integration Profile |
|-----------|-------------|--------------------------|
| **IPSO** | `ipso` object ID, instance | instance offset (optional) |
| **SenML** | `unit`, `unece`, field names | `base_name`, field name overrides, `base_time` |
| **WoT TD** | `ipso`, `unit`, `unece`, types | `@context`, `id`, `title`, `security`, `@type` per field |
| **JSON** | field names | `field_map` rename table |
| **TTN** | `unit`, field names | (uses schema names directly) |
| **Azure DTDL** | types, units | `model_id`, `twin_id`, `component`, property map |

---

## Format Details

### Plain JSON

No additional context needed. The decoder output is used directly, optionally
with field renaming.

**Integration context:**
```yaml
context:
  field_map:
    temperature: "ZONE_TEMP_01"
```

**Output:**
```json
{"ZONE_TEMP_01": 23.45, "ZONE_RH_01": 65.0, "SENSOR_VBAT": 3.276}
```

### IPSO / LwM2M

Uses `ipso` object ID and device-local instance from the schema. The
integration layer can apply an instance offset for solution-level namespacing.

**Integration context:**
```yaml
context:
  instance_offset: 0
```

**Converter logic:**
```
for each field with ipso metadata:
    object_id = metadata.ipso
    instance  = metadata.instance + context.instance_offset
    resource  = 5700  (Sensor Value)
    output["{object_id}/{instance}/{resource}"] = value
```

**Output:**
```json
{
  "3303/0/5700": 23.45,
  "3304/0/5700": 65.0,
  "3316/0/5700": 3.276
}
```

### SenML (RFC 8428)

Uses `unece` or `unit` from schema for the `u` field. The integration layer
provides base name (device/site identity) and optional field name overrides.

**Integration context:**
```yaml
context:
  base_name: "urn:site:campus_north:bldg_3:"
  base_time: rx_time
  field_names:
    battery_voltage: "vbat"
```

**Converter logic:**
```
records = []
records.append({bn: context.base_name, bt: timestamp})
for each field:
    name = context.field_names.get(field) or field.name
    unit = senml_unit(metadata.unece or metadata.unit)
    records.append({n: name, v: value, u: unit})
```

**Output:**
```json
[
  {"bn": "urn:site:campus_north:bldg_3:", "bt": 1716215400},
  {"n": "temperature", "u": "Cel", "v": 23.45},
  {"n": "humidity", "u": "%RH", "v": 65.0},
  {"n": "vbat", "u": "V", "v": 3.276}
]
```

### WoT Thing Description

The most context-rich format. The schema provides field types and units; the
integration layer adds everything that makes it a valid TD.

**Integration context:**
```yaml
context:
  td_context:
    - "https://www.w3.org/2022/wot/td/v1.1"
    - prefix: saref
      href: "https://saref.etsi.org/core/"
    - prefix: saref4envi
      href: "https://saref.etsi.org/saref4envi/"
  thing_id: "urn:dev:lorawan:${device_eui}"
  title: "Environmental Sensor - Building 3"
  thing_type: "saref:Sensor"
  security:
    scheme: bearer
    in: header
  semantic_types:
    temperature: "saref:Temperature"
    humidity: "saref:Humidity"
    battery_voltage: "saref:Energy"
  property_overrides:
    temperature:
      title: "Ambient Temperature"
      description: "Indoor air temperature"
      observable: true
    humidity:
      title: "Relative Humidity"
      observable: true
    battery_voltage:
      title: "Battery Voltage"
      observable: false
  forms_template:
    href: "/api/devices/${device_eui}/{property}"
    contentType: "application/json"
```

**Converter logic:**

The WoT converter builds a TD by merging three sources:

```
1. STRUCTURE (built-in to converter)
   @context, securityDefinitions, properties structure,
   readOnly: true for uplink-only schemas

2. FIELD METADATA (from schema)
   For each field → property affordance:
     type:  inferred from schema type (s16→number, bool→boolean)
     unit:  from metadata.unece
     readOnly: true (LoRaWAN uplink)

3. DEPLOYMENT CONTEXT (from integration profile)
   id, title, thing @type
   security scheme
   @type per property (SAREF classes)
   forms (API endpoints)
   title/description overrides
```

**Output:**
```json
{
  "@context": [
    "https://www.w3.org/2022/wot/td/v1.1",
    {"saref": "https://saref.etsi.org/core/"},
    {"saref4envi": "https://saref.etsi.org/saref4envi/"}
  ],
  "id": "urn:dev:lorawan:0011223344556677",
  "title": "Environmental Sensor - Building 3",
  "@type": "saref:Sensor",
  "securityDefinitions": {
    "bearer_sc": {"scheme": "bearer", "in": "header"}
  },
  "security": "bearer_sc",
  "properties": {
    "temperature": {
      "@type": "saref:Temperature",
      "title": "Ambient Temperature",
      "description": "Indoor air temperature",
      "type": "number",
      "unit": "CEL",
      "readOnly": true,
      "observable": true,
      "forms": [{
        "href": "/api/devices/0011223344556677/temperature",
        "contentType": "application/json"
      }]
    },
    "humidity": {
      "@type": "saref:Humidity",
      "title": "Relative Humidity",
      "type": "number",
      "unit": "P1",
      "readOnly": true,
      "observable": true,
      "forms": [{
        "href": "/api/devices/0011223344556677/humidity",
        "contentType": "application/json"
      }]
    },
    "battery_voltage": {
      "@type": "saref:Energy",
      "title": "Battery Voltage",
      "type": "number",
      "unit": "VLT",
      "readOnly": true,
      "observable": false,
      "forms": [{
        "href": "/api/devices/0011223344556677/battery_voltage",
        "contentType": "application/json"
      }]
    }
  }
}
```

**Key point:** The TD is not generated on every uplink. It is registered once
when the device is provisioned (or when the schema changes). Subsequent uplinks
update property values via the `forms` endpoints.

#### Automatic IPSO → SAREF Fallback

When the integration profile does not specify `semantic_types` for a field, the
converter can derive a SAREF type from the IPSO object ID in the schema:

| IPSO | SAREF @type | Automatic |
|------|-------------|-----------|
| 3303 | `saref:Temperature` | Yes |
| 3304 | `saref:Humidity` | Yes |
| 3315 | `saref:Pressure` | Yes |
| 3316 | `saref:Energy` | Yes |
| 3301 | `saref:Light` | Yes |
| 3302 | `saref:Occupancy` | Yes |
| 3325 | `saref4envi:CO2` | Yes |
| 3328 | `saref:Power` | Yes |
| 3336 | `saref:Location` | Yes |
| (other) | `saref:Measurement` | Fallback |

This means a minimal integration profile can produce a valid TD:

```yaml
format: wot_td
context:
  thing_id: "urn:dev:lorawan:${device_eui}"
  title: "Sensor ${device_eui}"
  security: {scheme: nosec}
```

The converter fills in `@type` for each property from the IPSO mapping table,
and uses `unece` codes for units. The deployer only needs to provide identity
and security.

### TTN Normalized Payload

Uses field names and units from the schema directly.

**Integration context:** (minimal — TTN format is prescriptive)
```yaml
context: {}
```

**Output:**
```json
{
  "decoded_payload": {
    "temperature": 23.45,
    "humidity": 65.0,
    "battery_voltage": 3.276
  },
  "normalized_payload": [
    {"measurement": {"temperature": {"value": 23.45, "unit": "Cel"}}},
    {"measurement": {"humidity": {"value": 65.0, "unit": "%RH"}}},
    {"measurement": {"battery_voltage": {"value": 3.276, "unit": "V"}}}
  ]
}
```

### Azure Digital Twins (DTDL)

**Integration context:**
```yaml
context:
  model_id: "dtmi:example:EnvSensor;1"
  twin_id: "${site}-${device_eui}"
  component: "sensors"
  property_map:
    temperature: "ambientTemperature"
    humidity: "relativeHumidity"
```

**Output** (patch update):
```json
{
  "$dtId": "campus_north-0011223344556677",
  "$metadata": {
    "$model": "dtmi:example:EnvSensor;1"
  },
  "sensors": {
    "ambientTemperature": 23.45,
    "relativeHumidity": 65.0,
    "battery_voltage": 3.276
  }
}
```

---

## Context Layering

Each format adds different amounts of context on top of the decoded values:

```
                 Decoded JSON           ← schema only
                     │
              ┌──────┴──────┐
              ▼              ▼
          Plain JSON      + field_map   ← rename only
              │
              ├── + IPSO IDs            ← from schema metadata
              │
              ├── + base_name           ← SenML identity
              │   + units
              │
              ├── + @context            ← WoT: most context
              │   + id, title
              │   + security
              │   + @type per field
              │   + forms
              │   + observable
              │
              └── + model_id            ← DTDL identity
                  + twin_id
                  + component
```

The formats form a spectrum from "almost no additional context" (plain JSON
with rename) to "substantial additional context" (WoT TD with ontology types,
security, and interaction affordances).

## Where the Integration Layer Runs

| Location | Pros | Cons |
|----------|------|------|
| **LNS** | Central, all devices route through it | LNS must support profile format |
| **Application server** | Flexible, per-application | Extra deployment component |
| **Cloud function** | Scalable, event-driven | Cold start latency, cost |
| **Edge gateway** | Low latency, works offline | Per-gateway configuration |

The integration layer is a logical component. Physically it may be built into
the LNS, run as a sidecar, or be a standalone service.

## Relationship to TS013

TS013-compliant decoders output plain JSON. The integration layer sits between
the decoder and downstream consumers:

```
Device → Gateway → LNS → TS013 Decoder → Integration Layer → Destinations
                              │                    │
                           Schema            Integration Profile
                        (manufacturer)          (deployer)
```

The TS013 decoder is the same regardless of output format. Format conversion
is a separate concern that uses the decoder's output plus the schema's metadata.

## What Belongs Where

| Property | Device Schema | Integration Profile |
|----------|---------------|---------------------|
| Binary field type (`s16`) | Yes | — |
| Arithmetic (`div: 10`) | Yes | — |
| Physical unit (`unit: "°C"`) | Yes | — |
| UNECE code (`unece: "CEL"`) | Yes | — |
| IPSO object type (`ipso: 3303`) | Yes | — |
| Device-local instance (`instance: 0`) | Yes | — |
| Output format | — | Yes |
| SenML base name | — | Yes |
| WoT thing ID | — | Yes |
| WoT security scheme | — | Yes |
| SAREF @type | — | Yes (or auto from IPSO) |
| Field name overrides | — | Yes |
| API endpoint forms | — | Yes |
| Solution-level instance offset | — | Yes |

**Rule of thumb:** If the manufacturer knows it at design time, it goes in the
schema. If the deployer knows it at installation time, it goes in the
integration profile.

## Version History

- v1.0: Initial design — converter architecture, all format details, context layering
