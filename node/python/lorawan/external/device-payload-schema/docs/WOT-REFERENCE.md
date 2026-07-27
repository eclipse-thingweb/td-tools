# W3C Web of Things (WoT) Semantic Reference

Reference for mapping LoRaWAN payload schema fields to W3C WoT Thing Descriptions
and SAREF ontology types.

Sources:
- [W3C WoT Thing Description 1.1](https://www.w3.org/TR/wot-thing-description11/)
- [SAREF Core Ontology v3.2.1](https://saref.etsi.org/core/)
- [SAREF4ENVI (Environment)](https://saref.etsi.org/saref4envi/)
- [SAREF4BLDG (Building)](https://saref.etsi.org/saref4bldg/)

## Architecture

WoT Thing Descriptions are generated at the **integration layer**, not in the
device schema. The device schema provides the raw material (field types, units,
IPSO mappings); the integration profile adds WoT identity, security, and
ontology annotations.

```
Device Schema (manufacturer)          Integration Layer (deployer)
┌────────────────────────────┐        ┌────────────────────────────┐
│ name: temperature          │        │ @context: wot-td/v1.1      │
│ type: s16, div: 10         │───────▶│ @type: saref:TemperatureSe │
│ unit: "°C"                 │        │ id: urn:dev:lorawan:...     │
│ ipso: 3303                 │        │ security, forms, ...        │
└────────────────────────────┘        └────────────────────────────┘
```

## Thing Description Structure

A WoT Thing Description (TD) for a LoRaWAN sensor:

```json
{
  "@context": [
    "https://www.w3.org/2022/wot/td/v1.1",
    {"saref": "https://saref.etsi.org/core/"}
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
      "type": "number",
      "unit": "CEL",
      "readOnly": true,
      "forms": [{"href": "/api/devices/0011223344556677/temperature"}]
    },
    "humidity": {
      "@type": "saref:Humidity",
      "type": "number",
      "unit": "P1",
      "readOnly": true,
      "forms": [{"href": "/api/devices/0011223344556677/humidity"}]
    }
  }
}
```

LoRaWAN sensors are read-only (uplink telemetry), so all properties have
`"readOnly": true`. Devices with downlink commands could expose WoT actions.

## SAREF Ontology Mapping

### Core Sensor Properties (saref:)

Maps IPSO object IDs to SAREF classes. The IPSO ID from the device schema
determines the SAREF `@type` in the TD.

| IPSO | Sensor Type | SAREF @type | SAREF Property | UNECE Unit |
|------|-------------|-------------|----------------|------------|
| 3303 | Temperature | `saref:Temperature` | `saref:hasValue` | CEL, FAH |
| 3304 | Humidity | `saref:Humidity` | `saref:hasValue` | P1 |
| 3315 | Barometer | `saref:Pressure` | `saref:hasValue` | A97 (hPa), PAL |
| 3316 | Voltage | `saref:Energy` | `saref:hasValue` | VLT |
| 3317 | Current | `saref:Energy` | `saref:hasValue` | AMP |
| 3301 | Illuminance | `saref:Light` | `saref:hasValue` | LUX |
| 3302 | Presence | `saref:Occupancy` | `saref:hasValue` | — |
| 3305 | Power Measurement | `saref:Power` | `saref:hasValue` | WTT |
| 3313 | Accelerometer | `saref:Motion` | `saref:hasValue` | — |
| 3322 | Load | `saref:Weight` | `saref:hasValue` | KGM |
| 3323 | Pressure | `saref:Pressure` | `saref:hasValue` | PAL, BAR |
| 3325 | Concentration | `saref4envi:CO2` | `saref:hasValue` | 59 (ppm) |
| 3328 | Power | `saref:Power` | `saref:hasValue` | WTT |
| 3330 | Distance | `saref:Measurement` | `saref:hasValue` | MTR |
| 3331 | Energy | `saref:Energy` | `saref:hasValue` | KWH |
| 3336 | Location | `saref:Location` | `saref:hasValue` | — |
| 3347 | Push Button | `saref:Command` | `saref:hasValue` | — |

### Environmental Extensions (saref4envi:)

For air quality and environmental monitoring:

| Measurement | SAREF @type | Notes |
|-------------|-------------|-------|
| CO2 | `saref4envi:CO2` | ppm concentration |
| CO | `saref4envi:CO` | ppm concentration |
| PM2.5 | `saref4envi:PM2_5` | µg/m³ |
| PM10 | `saref4envi:PM10` | µg/m³ |
| NO2 | `saref4envi:NO2` | ppb |
| O3 | `saref4envi:O3` | ppb |
| TVOC | `saref4envi:TVOC` | ppb or index |
| Noise | `saref4envi:Noise` | dB |

### Building Extensions (saref4bldg:)

For building automation sensors:

| Measurement | SAREF @type | Notes |
|-------------|-------------|-------|
| Room temperature | `saref4bldg:TemperatureSensor` | Indoor/zone |
| Occupancy | `saref4bldg:OccupancySensor` | PIR, radar |
| Valve position | `saref4bldg:Valve` | % open |
| Light control | `saref4bldg:LightingDevice` | On/off, dimmer |

## WoT Unit Codes

WoT TDs use UNECE unit codes (same as the schema `unece:` field). Common
mappings from human units:

| Display Unit | UNECE Code | WoT `unit` |
|-------------|------------|------------|
| °C | CEL | `"CEL"` |
| °F | FAH | `"FAH"` |
| %RH | P1 | `"P1"` |
| hPa | A97 | `"A97"` |
| Pa | PAL | `"PAL"` |
| V | VLT | `"VLT"` |
| mV | D82 | `"D82"` |
| A | AMP | `"AMP"` |
| mA | B22 | `"B22"` |
| W | WTT | `"WTT"` |
| kWh | KWH | `"KWH"` |
| lx | LUX | `"LUX"` |
| dB | 2N | `"2N"` |
| ppm | 59 | `"59"` |
| m | MTR | `"MTR"` |
| mm | MMT | `"MMT"` |
| cm | CMT | `"CMT"` |
| kg | KGM | `"KGM"` |
| Hz | HTZ | `"HTZ"` |
| m/s | MTS | `"MTS"` |
| Ω | OHM | `"OHM"` |
| L | LTR | `"LTR"` |

Source: [UNECE Recommendation 20](https://unece.org/trade/uncefact/cl-recommendations)

## Integration Profile WoT Section

The integration profile configures WoT TD generation per device deployment:

```yaml
integrations:
  - id: wot_directory
    protocol: wot_td
    endpoint: https://wot.example.com/things
    wot:
      context:
        - "https://www.w3.org/2022/wot/td/v1.1"
        - "https://saref.etsi.org/core/v3.2.1/"
      id: "urn:dev:lorawan:${device_eui}"
      title: "${device_name} - ${zone}"
      security_scheme:
        type: bearer
        in: header
      semantic_types:
        _thing: "saref:Sensor"
        temperature: "saref:Temperature"
        humidity: "saref:Humidity"
        co2: "saref4envi:CO2"
        battery_voltage: "saref:Energy"
      property_affordances:
        temperature:
          title: "Ambient Temperature"
          observable: true
        humidity:
          title: "Relative Humidity"
          observable: true
```

### What the Schema Provides vs. What the Integration Adds

| TD Field | Source | Example |
|----------|--------|---------|
| `properties.*.type` | Schema field type | `"number"` from `s16` |
| `properties.*.unit` | Schema `unece:` | `"CEL"` |
| `properties.*.readOnly` | Schema direction | `true` (uplink-only) |
| `@context` | Integration profile | WoT + SAREF URLs |
| `id` | Integration profile | `urn:dev:lorawan:...` |
| `title` | Integration profile | Deployment-specific name |
| `@type` | Integration profile | `saref:Temperature` |
| `security` | Integration profile | Auth scheme |
| `forms` | Integration profile | API endpoint URLs |

## Mapping from IPSO to SAREF (Automated)

A protocol converter can derive SAREF types from IPSO object IDs already
present in the schema. This table drives automatic mapping:

```
IPSO 3303 → saref:Temperature
IPSO 3304 → saref:Humidity
IPSO 3315 → saref:Pressure
IPSO 3316 → saref:Energy       (voltage)
IPSO 3301 → saref:Light
IPSO 3302 → saref:Occupancy
IPSO 3325 → saref4envi:CO2     (or generic saref:Measurement)
IPSO 3328 → saref:Power
IPSO 3330 → saref:Measurement  (distance)
IPSO 3331 → saref:Energy
IPSO 3336 → saref:Location
```

Fields without IPSO mappings fall back to `saref:Measurement` with the unit
from the schema.

## Example: Full TD from Schema

Given this device schema:

```yaml
name: env_sensor
fields:
  - name: temperature
    type: s16
    div: 10
    unit: "°C"
    ipso: 3303
    senml: {unit: "Cel"}
  - name: humidity
    type: u8
    unit: "%RH"
    ipso: 3304
  - name: co2
    type: u16
    unit: "ppm"
    ipso: 3325
  - name: battery_voltage
    type: u16
    div: 1000
    unit: "V"
    ipso: 3316
```

The integration layer generates:

```json
{
  "@context": [
    "https://www.w3.org/2022/wot/td/v1.1",
    {"saref": "https://saref.etsi.org/core/"},
    {"saref4envi": "https://saref.etsi.org/saref4envi/"}
  ],
  "id": "urn:dev:lorawan:0011223344556677",
  "title": "Environmental Sensor - Campus North Bldg 3",
  "@type": "saref:Sensor",
  "securityDefinitions": {
    "bearer_sc": {"scheme": "bearer", "in": "header"}
  },
  "security": "bearer_sc",
  "properties": {
    "temperature": {
      "@type": "saref:Temperature",
      "type": "number",
      "unit": "CEL",
      "readOnly": true,
      "forms": [{"href": "/properties/temperature", "contentType": "application/json"}]
    },
    "humidity": {
      "@type": "saref:Humidity",
      "type": "number",
      "unit": "P1",
      "readOnly": true,
      "forms": [{"href": "/properties/humidity", "contentType": "application/json"}]
    },
    "co2": {
      "@type": "saref4envi:CO2",
      "type": "number",
      "unit": "59",
      "readOnly": true,
      "forms": [{"href": "/properties/co2", "contentType": "application/json"}]
    },
    "battery_voltage": {
      "@type": "saref:Energy",
      "type": "number",
      "unit": "VLT",
      "readOnly": true,
      "forms": [{"href": "/properties/battery_voltage", "contentType": "application/json"}]
    }
  }
}
```

## Relationship to Other Output Formats

| Format | Standard | Layer | Spec Section |
|--------|----------|-------|--------------|
| Plain JSON | — | Decoder output | `OUTPUT-FORMATS.md` |
| IPSO | OMA LwM2M | Decoder or integration | `IPSO-REFERENCE.md` |
| SenML | IETF RFC 8428 | Decoder or integration | `OUTPUT-FORMATS.md` |
| **WoT TD** | **W3C** | **Integration only** | **This document** |
| TTN Normalized | TTI | Integration | `OUTPUT-FORMATS.md` |

WoT TDs differ from the other formats: they describe the **device capability**
(what properties exist, their types and units), not individual measurement
values. A TD is registered once per device in a Thing Directory; subsequent
uplinks update the property values via the `forms` endpoints.

## Version History

- v1.0: Initial reference — SAREF core mapping, UNECE units, integration profile structure
