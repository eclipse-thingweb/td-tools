# IPSO Smart Objects Reference

Complete reference for IPSO Smart Objects (OMA LwM2M) used in LoRaWAN payload schemas.

Source: [OMA LwM2M Registry](https://technical.openmobilealliance.org/OMNA/LwM2M/LwM2MRegistry.html)

## Common Sensor Objects (3300-3350)

| ID | Name | Description | Common Fields |
|----|------|-------------|---------------|
| 3300 | Generic Sensor | General-purpose sensor | value, unit, min, max |
| 3301 | Illuminance | Light level (lux) | value (lx) |
| 3302 | Presence | Motion/occupancy detection | value (boolean) |
| 3303 | Temperature | Temperature sensor | value (Cel) |
| 3304 | Humidity | Relative humidity | value (%RH) |
| 3305 | Power Measurement | Power monitoring | value (W) |
| 3306 | Actuation | On/off control, dimmer | on/off, dimmer (%) |
| 3308 | Set Point | Target/setpoint values | value |
| 3310 | Load Control | Load management | event |
| 3311 | Light Control | Light on/off/dimmer | on/off, dimmer |
| 3312 | Power Control | Power on/off | on/off |
| 3313 | Accelerometer | 3-axis acceleration | x, y, z (m/s²) |
| 3314 | Magnetometer | Magnetic field | x, y, z (T) |
| 3315 | Barometer | Atmospheric pressure | value (Pa) |
| 3316 | Voltage | Voltage measurement | value (V) |
| 3317 | Current | Current measurement | value (A) |
| 3318 | Frequency | Frequency measurement | value (Hz) |
| 3319 | Depth | Depth/level measurement | value (m) |
| 3320 | Percentage | Generic percentage | value (%) |
| 3321 | Altitude | Altitude measurement | value (m) |
| 3322 | Load | Weight/force sensor | value (kg) |
| 3323 | Pressure | Pressure sensor | value (Pa) |
| 3324 | Loudness | Sound level | value (dB) |
| 3325 | Concentration | Gas concentration (CO2, etc.) | value (ppm) |
| 3326 | Acidity | pH measurement | value (pH) |
| 3327 | Conductivity | Electrical conductivity | value (S/m) |
| 3328 | Power | Power measurement | value (W) |
| 3329 | Power Factor | Power factor | value |
| 3330 | Distance | Distance/range sensor | value (m) |
| 3331 | Energy | Energy consumption | value (Wh) |
| 3332 | Direction | Compass heading | value (deg) |
| 3333 | Time | Time value | value (s) |
| 3334 | Gyrometer | Angular velocity | x, y, z (deg/s) |
| 3335 | Colour | RGB color | r, g, b |
| 3336 | Location | GPS coordinates | lat, lon, alt |
| 3337 | Positioner | Position actuator | value (%) |
| 3338 | Buzzer | Audio alert | on/off |
| 3339 | Audio Clip | Audio playback | clip |
| 3340 | Timer | Timer/countdown | remaining (s) |
| 3341 | Addressable Text Display | Text display | text |
| 3342 | On/Off Switch | Binary switch | state |
| 3343 | Dimmer | Dimmer control | level (%) |
| 3344 | Up/Down Control | Increment/decrement | - |
| 3345 | Multiple Axis Joystick | Joystick input | x, y, z |
| 3346 | Rate | Speed/rate measurement | value (m/s, RPM) |
| 3347 | Push Button | Button press | count, state |
| 3348 | Multi-state Selector | Multi-position selector | state |

## Usage in Schema

```yaml
fields:
  - name: temperature
    type: s16
    div: 100
    unit: "°C"
    ipso: 3303
    senml: {unit: "Cel"}
    semantic: "temperature.ambient"
```

## Adding New IPSO Objects

When converting a TTN codec that uses an IPSO object not in this list:

1. Look up the object in the [OMA Registry](https://github.com/OpenMobileAlliance/lwm2m-registry)
2. Add to this reference document
3. Add keyword mapping to `tools/score_schema.py` (STANDARD_SENSOR_IPSO)
4. Add SenML unit mapping if applicable (SENML_UNITS)

## Keyword Detection

The schema scorer auto-detects sensors by field name keywords:

| Keyword | IPSO | SenML Unit |
|---------|------|------------|
| temperature | 3303 | Cel |
| humidity | 3304 | %RH |
| pressure | 3323 | Pa |
| illuminance, light, lux | 3301 | lx |
| voltage, battery | 3316 | V |
| current | 3317 | A |
| power | 3328 | W |
| energy | 3331 | J |
| frequency | 3318 | Hz |
| distance | 3330 | m |
| co2, concentration | 3325 | ppm |
| conductivity | 3327 | - |
| acidity, ph | 3326 | - |
| gps, location, latitude, longitude | 3336 | lat/lon |
| accelerometer, acceleration | 3313 | - |
| gyroscope | 3334 | - |
| magnetometer | 3314 | - |
| setpoint, target | 3308 | Cel |
| valve, openness | 3337 | % |
| presence, motion, occupancy | 3302 | - |
| load, weight | 3322 | kg |
| button | 3347 | - |

## Complex Codec Examples (from TTN lorawan-devices)

These codecs demonstrate edge cases and features to consider:

| Device | Features | Schema Challenges |
|--------|----------|-------------------|
| Sensative Strips | 32 message types, door/flood/tamper | Large switch statement |
| Digital Matter Oyster | GPS, signed coords, speed/heading | 24-bit signed integers |
| Dragino LAQ4 | CO2, TVOC, mode-based | Conditional field parsing |
| Tektelic Agriculture | TLV, coefficients | Data-driven decoding |
| Decentlab DL-5TM | Flag-based, polynomial | Sensor presence bitmask |

## Version History

- v1.0: Initial 21 common objects
- v1.1: Added 27 additional objects (3318-3348)
- v1.2: Added complex codec examples from TTN
