# TTN Codec Analysis Notes

Analysis of complex codecs from lorawan-devices repository to identify schema language gaps.

---

## 1. Digital Matter Oyster (GPS Tracker)

**Source:** `vendor/digital-matter/oyster.js`

### Message Types (by fPort)

| Port | Type | Size | Description |
|------|------|------|-------------|
| 1 | Position | 11 bytes | Full precision GPS (32-bit signed lat/lon) |
| 2 | Downlink ACK | 3 bytes | Sequence, accepted flag, firmware version |
| 3 | Stats | 11 bytes | Counters with complex bit-packing |
| 4 | Position Compact | 9 bytes | Reduced precision GPS (24-bit signed lat/lon) |

### Port 1: Position (Full Precision)

```
Bytes 0-3: latitude (s32 LE) / 1e7 = degrees
Bytes 4-7: longitude (s32 LE) / 1e7 = degrees  
Byte 8[0]: inTrip flag
Byte 8[1]: fixFailed flag
Byte 8[2:7]: heading / 5.625 = degrees (0-360)
Byte 9: speed (km/h)
Byte 10: battery * 0.025 = volts
```

### Port 4: Position (Compact)

```
Bytes 0-2: latitude (s24 LE) * 256e-7 = degrees
Bytes 3-5: longitude (s24 LE) * 256e-7 = degrees
Byte 6[0:2]: heading * 45 = degrees (0-315, 8 directions)
Byte 6[3:7]: speed * 5 = km/h (0-155 in steps of 5)
Byte 7: battery * 0.025 = volts
Byte 8[0]: inTrip flag
Byte 8[1]: fixFailed flag
Byte 8[2]: manDown flag
```

### Port 3: Stats (Complex Bit-Packing)

Values span byte boundaries - complex to express in schema:
```
initialBatV = 4.0 + 0.1 * (bytes[0] & 0xF)
txCount = 32 * ((bytes[0] >> 4) + (bytes[1] & 0x7F) * 16)
tripCount = 32 * ((bytes[1] >> 7) + (bytes[2] & 0xFF) * 2 + (bytes[3] & 0x0F) * 512)
...
```

### Schema Language Gaps Identified

| Gap | Description | Severity |
|-----|-------------|----------|
| **s24/u24 types** | 24-bit signed/unsigned integers | HIGH |
| **Cross-byte bitfields** | Values spanning multiple bytes | MEDIUM |
| **Conditional output placement** | `cached` vs top-level based on flag | LOW |
| **Port-based parsing** | Different schemas per fPort | Supported via `ports:` |

### IPSO Mappings

| Field | IPSO | SenML |
|-------|------|-------|
| latitudeDeg | 3336 | lat |
| longitudeDeg | 3336 | lon |
| speedKmph | 3346 | km/h |
| headingDeg | 3332 | deg |
| batV | 3316 | V |

### Test Vectors Needed

```yaml
test_vectors:
  - name: position_port1_positive_coords
    port: 1
    payload: "80 84 1E 00 40 42 0F 00 A4 32 78"  # ~30°, ~15°
    expected:
      latitudeDeg: 30.0
      longitudeDeg: 15.0
      
  - name: position_port1_negative_coords  
    port: 1
    payload: "..."  # Southern hemisphere
    expected:
      latitudeDeg: -33.86
      longitudeDeg: 151.21
```

### Recommendation

1. Add `s24`/`u24` types to interpreter
2. Port 3 stats may require `formula` or be out-of-scope (too complex)
3. Implement Port 1 and Port 4 position messages first

---

## 2. Dragino LAQ4 (Air Quality Sensor)

**Source:** `vendor/dragino/laq4.js`

### Overview

Single port (2) with mode-based parsing. Mode extracted from byte 2 bits 2-6.

| Mode | Name | Description |
|------|------|-------------|
| 1 | CO2 | Actual sensor readings |
| 31 | ALARM | Alarm threshold configuration |

### Mode 1 (CO2) - 11 bytes

```
Bytes 0-1: battery (u16 BE) / 1000 = volts
Byte 2[0]: alarm_status (0=FALSE, 1=TRUE)
Byte 2[2:6]: mode (value: 1)
Bytes 3-4: TVOC (u16 BE) ppb
Bytes 5-6: CO2 (u16 BE) ppm
Bytes 7-8: temperature (s16 BE) / 10 = °C
Bytes 9-10: humidity (u16 BE) / 10 = %
```

### Mode 31 (ALARM) - 11 bytes

```
Bytes 0-1: battery (u16 BE) / 1000 = volts
Byte 2[2:6]: mode (value: 31)
Byte 3: temp_min (s8) °C
Byte 4: temp_max (s8) °C
Byte 5: humidity_min (u8) %
Byte 6: humidity_max (u8) %
Bytes 7-8: CO2_min (u16 BE) ppm
Bytes 9-10: CO2_max (u16 BE) ppm
```

### Schema Approach

Use `match` on mode field:

```yaml
endian: big
fields:
  - name: battery
    type: u16
    div: 1000
    unit: "V"
    
  - byte_group:
      size: 1
      fields:
        - name: alarm_status
          type: u8[0:0]
        - name: mode
          type: u8[2:6]

  - match:
      field: $mode
      cases:
        1:  # CO2 mode
          - name: work_mode
            type: enum
            value: "CO2"
          - name: tvoc
            type: u16
            unit: "ppb"
          - name: co2
            type: u16
            unit: "ppm"
          - name: temperature
            type: s16
            div: 10
            unit: "°C"
          - name: humidity
            type: u16
            div: 10
            unit: "%"
            
        31:  # ALARM mode
          - name: work_mode
            type: enum
            value: "ALARM"
          - name: temp_min
            type: s8
            unit: "°C"
          - name: temp_max
            type: s8
            unit: "°C"
          - name: humidity_min
            type: u8
            unit: "%"
          - name: humidity_max
            type: u8
            unit: "%"
          - name: co2_min
            type: u16
            unit: "ppm"
          - name: co2_max
            type: u16
            unit: "ppm"
```

### Schema Language Gaps

| Gap | Description | Severity |
|-----|-------------|----------|
| **None significant** | Well-supported by match/switch | - |
| String enum output | `work_mode: "CO2"` vs numeric | LOW |

### IPSO Mappings

| Field | IPSO | SenML |
|-------|------|-------|
| battery | 3316 | V |
| tvoc | 3325 | ppb |
| co2 | 3325 | ppm |
| temperature | 3303 | Cel |
| humidity | 3304 | %RH |

### Test Vectors

```yaml
test_vectors:
  - name: co2_mode_normal
    port: 2
    payload: "0B B8 04 00 C8 03 E8 00 FA 02 58"
    # battery=3.0V, mode=1, tvoc=200, co2=1000, temp=25.0, hum=60.0
    expected:
      battery: 3.0
      mode: 1
      tvoc: 200
      co2: 1000
      temperature: 25.0
      humidity: 60.0
      
  - name: alarm_mode
    port: 2
    payload: "0B B8 7C 0A 1E 14 50 01 F4 07 D0"
    # battery=3.0V, mode=31, temp_min=10, temp_max=30, hum_min=20, hum_max=80, co2_min=500, co2_max=2000
    expected:
      battery: 3.0
      mode: 31
      temp_min: 10
      temp_max: 30
```

### Recommendation

Straightforward to implement. Good test case for `match` on computed bitfield value.

---

## 3. Sensative Strips (Multi-Sensor)

**Source:** `vendor/sensative/strips.js`

### Overview

TLV-like codec with implicit length (determined by type). Multiple frames per message.

| Port | Description |
|------|-------------|
| 1 | Current data - sequence number + frame(s) |
| 2 | Historical data - sequence + timestamp + frame(s) |

### Frame Types (32 types)

| Type | Name | Size | Format | IPSO |
|------|------|------|--------|------|
| 0 | Empty | 0 | - | - |
| 1 | Battery | 1 | u8 (0-100%) | 3316 |
| 2 | Temperature | 2 | s16 BE / 10 °C | 3303 |
| 3 | TempAlarm | 1 | bit0=high, bit1=low | - |
| 4 | AvgTemperature | 2 | s16 BE / 10 °C | 3303 |
| 5 | AvgTempAlarm | 1 | bit0=high, bit1=low | - |
| 6 | Humidity | 1 | u8 / 2 (0.5% steps) | 3304 |
| 7 | Lux | 2 | u16 BE | 3301 |
| 8 | Lux2 | 2 | u16 BE | 3301 |
| 9 | Door | 1 | bool (closed=true) | 3342 |
| 10 | DoorAlarm | 1 | bool | - |
| 11 | TamperReport | 1 | bool | 3302 |
| 12 | TamperAlarm | 1 | bool | - |
| 13 | Flood | 1 | u8 (0-100%) | 3320 (Percentage) |
| 14 | FloodAlarm | 1 | bool | - |
| 15 | OilAlarm | 1 | u8 | - |
| 16 | UserSwitch1Alarm | 1 | bool | - |
| 17 | DoorCount | 2 | u16 BE | - |
| 18 | Presence | 1 | bool | 3302 |
| 19 | IRProximity | 2 | u16 BE | 3330 |
| 20 | IRCloseProximity | 2 | u16 BE | 3330 |
| 21 | CloseProximityAlarm | 1 | bool | - |
| 22 | DisinfectAlarm | 1 | enum 0-3 | - |
| 80 | Humidity+Temp | 3 | combo | - |
| 81 | Humidity+AvgTemp | 3 | combo | - |
| 82 | Door+Temp | 3 | combo | - |
| 110 | (skip) | 8 | reserved | - |
| 112 | CapacitanceFlood | 2 | u16 BE | - |
| 113 | CapacitancePad | 2 | u16 BE | - |
| 114 | CapacitanceEnd | 2 | u16 BE | - |

### Message Structure (Port 1)

```
Bytes 0-1: historySeqNr (u16 BE)
Remaining: [type (1 byte)][data (N bytes)] repeated
```

Type byte bit 7: 0=current, 1=historical (decrements sequence)

### Schema Approach

This requires **implicit-length TLV** - length determined by type lookup table.

```yaml
fields:
  - name: historySeqNr
    type: u16
    endian: big
    
  - tlv:
      type_field: u8
      length: implicit  # NEW: length from type lookup
      type_lengths:     # NEW: map type -> size
        0: 0
        1: 1
        2: 2
        3: 1
        # ... etc
      cases:
        1:
          - name: battery
            type: u8
            unit: "%"
        2:
          - name: temperature
            type: s16
            div: 10
            unit: "°C"
        # ... etc
```

### Schema Language Gaps

| Gap | Description | Severity |
|-----|-------------|----------|
| **Implicit-length TLV** | Length from type lookup table | HIGH |
| **Repeated TLV frames** | Multiple frames in one message | MEDIUM |
| **Combo frame types** | Types 80-82 have multiple outputs | LOW |
| **Bit 7 flag** | Historical marker in type byte | LOW |

### Recommendation

1. Extend TLV to support `length: implicit` with `type_lengths` map
2. Or: Consider this "too complex" - would need custom codec
3. Alternatively: Restrict schema to single-frame messages (most common case)

---

## 4. Decentlab DL-5TM (Soil Sensor)

**Source:** `vendor/decentlab/dl-5tm.js`
**Schema:** `schemas/devices/decentlab/dl-5tm.yaml` (EXISTING)

### Overview

Flagged sensor groups with polynomial calibration. **Already implemented** in our schema.

### Message Structure

```
Byte 0: protocol_version (u8, must be 2)
Bytes 1-2: device_id (u16 BE)
Bytes 3-4: flags (u16 BE) - bitmask of present sensor groups
Remaining: sensor data based on flags
```

### Sensor Groups

| Bit | Group | Size | Fields |
|-----|-------|------|--------|
| 0 | Soil sensor | 4 bytes | dielectric (u16), temperature (u16) |
| 1 | Battery | 2 bytes | voltage (u16) |

### Key Features Already Supported

| Feature | Schema Syntax | Notes |
|---------|---------------|-------|
| **Flagged groups** | `flagged: { field: flags, groups: [...] }` | ✅ Works |
| **Polynomial** | `polynomial: [a, b, c, d]` | ✅ Cubic VWC formula |
| **Transform chain** | `transform: [{ add: -400 }, { div: 10 }]` | ✅ Temperature |
| **Computed fields** | `type: number, ref: $field` | ✅ VWC from permittivity |

### Polynomial Formula

Volumetric Water Content (VWC) from dielectric permittivity:
```
VWC = 0.0000043 * ε³ - 0.00055 * ε² + 0.0292 * ε - 0.053
```

Schema representation:
```yaml
- name: volumetric_water_content
  type: number
  ref: $dielectric_permittivity
  polynomial: [0.0000043, -0.00055, 0.0292, -0.053]
```

### Test Coverage

- 7 test vectors covering: typical, dry soil, battery only, sensor only, zero, max, minimum payload
- All passing ✅

### Schema Language Gaps

**None** - This codec is fully supported and serves as a good reference implementation.

### Recommendation

Use as reference for `flagged` and `polynomial` features. Good example of complex calibration curves.

---

## 5. Tektelic Agriculture (Data-Driven TLV)

**Source:** `vendor/tektelic/decoder_agriculture_sensor.js` (~1900 lines)

### Overview

Meta-codec with data-driven sensor definitions. Sensor parameters stored as JSON object, generic decoder interprets them.

### Architecture

```javascript
var sensor = {
  "10": {                         // Port 10 (sensor data)
    "0x00 0xBA": [                 // 2-byte tag
      {
        "data_size": "1",          // Bytes to read
        "bit_start": "6",          // Bit extraction
        "bit_end": "0",
        "type": "unsigned",
        "parameter_name": "level",
        "group_name": "Battery Status",
        "coefficient": "0.01",     // value * coef
        "addition": "2.5",         // + addition
        "round": "2"               // decimal places
      }
    ]
  },
  "100": { ... }                   // Port 100 (configuration)
}
```

### Tag Types (Port 10)

| Tag | Name | Size | Fields |
|-----|------|------|--------|
| 0x00 0xBA | Battery | 1 | level, eos_alert |
| 0x01 0x04 | Input1 Freq | 2 | frequency |
| 0x02 0x02 | Input2 Voltage | 2 | voltage |
| 0x03 0x02 | Input3 Voltage | 2 | voltage |
| 0x04 0x02 | Input4 Voltage | 2 | voltage |
| 0x05 0x04 | Input5 Freq | 2 | frequency |
| 0x06 0x04 | Input6 Freq | 2 | frequency |
| 0x09 0x65 | Light | 2 | intensity |
| 0x09 0x00 | Light Alarm | 1 | alarm |
| 0x0A 0x71 | Accelerometer | 6 | x, y, z |
| 0x0A 0x00 | Orientation Alarm | 1 | alarm |
| 0x0B 0x67 | Ambient Temp | 2 | temperature |
| 0x0B 0x68 | Humidity | 1 | humidity |
| 0x0C 0x67 | MCU Temp | 2 | temperature |

### Post-Processing Functions

Soil moisture calculations with temperature compensation:
```javascript
freqToWatermark(freq)    // Piecewise linear: freq -> kPa
voltageToTemp(voltage)   // NTC thermistor: voltage -> °C
adj_watermark = watermark * (1 - 0.019 * (temperature - 24))
```

### Schema Approach

Could convert to YAML with 2-byte TLV tags:

```yaml
fields:
  - tlv:
      tag_size: 2        # 2-byte tags
      length: explicit   # From field definition
      cases:
        0x00BA:
          - byte_group:
              size: 1
              fields:
                - name: battery_level
                  type: u8[0:6]
                  mult: 0.01
                  add: 2.5
                  transform: [{op: round, decimals: 2}]
                - name: battery_eos_alert
                  type: u8[7:7]
        0x0B67:
          - name: ambient_temperature
            type: s16
            mult: 0.1
            transform: [{op: round, decimals: 1}]
```

### Schema Language Gaps

| Gap | Description | Severity |
|-----|-------------|----------|
| **2-byte TLV tags** | Currently only u8 tags supported? | HIGH |
| **Piecewise linear** | freqToWatermark calibration | MEDIUM |
| **Post-processing** | Computed fields from multiple sources | MEDIUM |

### Recommendation

1. Verify TLV supports multi-byte tags
2. Piecewise linear could use `lookup` with interpolation, or `formula`
3. Large schema but structurally compatible
4. Consider auto-converter from Tektelic JSON format to YAML

---

## Summary: Schema Language Gaps

### Priority HIGH - Blocks common use cases

| Gap | Affected Codecs | Status |
|-----|-----------------|--------|
| **s24/u24 types** | Digital Matter (GPS coords) | ✅ ALREADY SUPPORTED |
| **Implicit-length TLV** | Sensative Strips | ❌ Needs implementation |
| **2-byte TLV tags** | Tektelic | ✅ ALREADY SUPPORTED (`tag_size: 2`) |

### Priority MEDIUM - Workarounds exist

| Gap | Affected Codecs | Workaround |
|-----|-----------------|------------|
| **Cross-byte bitfields** | Digital Matter (stats) | Use formula or mark as out-of-scope |
| **Piecewise linear** | Tektelic (watermark) | Use lookup with interpolation or formula |
| **Post-processing** | Tektelic (temperature comp) | Use compute with multiple refs |

### Priority LOW - Edge cases

| Gap | Affected Codecs | Notes |
|-----|-----------------|-------|
| **Conditional output placement** | Digital Matter (cached) | Rare pattern |
| **Historical data with timestamps** | Sensative Strips | Complex, consider out-of-scope |
| **Combo frame types** | Sensative Strips | Can decompose in schema |

### Feature Coverage Matrix

| Feature | Status | Tested In |
|---------|--------|-----------|
| `match`/`switch` | ✅ Supported | MClimate Vicki, Dragino LAQ4 |
| `flagged` | ✅ Supported | Decentlab DL-5TM |
| `polynomial` | ✅ Supported | Decentlab DL-5TM |
| `byte_group` | ✅ Supported | MClimate Vicki |
| `tlv` | ✅ Supported | Need to verify multi-byte tags |
| `transform` chain | ✅ Supported | Decentlab DL-5TM |
| `compute` | ✅ Supported | Various |
| Signed integers | ✅ s8/s16/s24/s32/s64 | Multiple |
| Big-endian | ✅ Supported | Decentlab, Dragino |
| Enum output | ✅ Supported | Various |
| **s24/u24** | ✅ Supported | Digital Matter Oyster |
| **2-byte TLV tags** | ✅ Supported (`tag_size: 2`) | Tektelic-style |
| **Implicit TLV length** | ❌ Missing | Sensative Strips |

### IPSO Coverage for Analyzed Codecs

| Sensor Type | IPSO | Status |
|-------------|------|--------|
| GPS Location | 3336 | Documented |
| Speed | 3346 | Documented |
| Direction/Heading | 3332 | Need to add |
| Temperature | 3303 | Documented |
| Humidity | 3304 | Documented |
| Battery | 3316 | Documented |
| Illuminance | 3301 | Documented |
| Presence | 3302 | Documented |
| Door/Pushbutton | 3342 | Documented |
| Flood (wetness %) | 3320 | Use Percentage object |
| Distance/Proximity | 3330 | Documented |
| Accelerometer | 3313 | Documented |
| CO2 | 3325 (Concentration) | Documented |
| TVOC | 3325 (Concentration) | Documented |
| Dielectric/VWC | - | No standard IPSO |

### Completed Actions

1. ✅ **s24/u24 types** - Already supported, verified working
2. ✅ **2-byte TLV tags** - Already supported via `tag_size: 2`
3. ✅ **Digital Matter Oyster schema** - Created, 100% PLATINUM score
4. ✅ **Dragino LAQ4 schema** - Created, 96% PLATINUM score
5. ✅ **Fixed JS codec s32 bug** - `1 << 31` -> `Math.pow(2, 31)` in generator
6. ✅ **Fixed fport/fPort inconsistency** - score_schema.py now handles both

### Remaining Next Steps

1. **Implement implicit-length TLV** - For Sensative-style repeated frames (type determines length)
2. **Consider Tektelic schema** - Large but structurally compatible with current TLV
3. **Add piecewise linear support** - For complex calibration curves like watermark sensors

