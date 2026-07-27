# Sensor Library Semantic Mapping

Coverage of IPSO, SenML, UNECE, and TTN sensor types.

## Coverage Summary

| Standard | Definitions | Notes |
|----------|-------------|-------|
| TTN sensor types | 100% | All 70+ TTN types covered |
| IPSO Object IDs | 43 refs | Core sensor objects |
| UNECE codes | 60 refs | Standard unit identifiers |
| SenML units | via unit field | RFC 8428 compatible |

## IPSO Object ID Reference

| IPSO ID | Object Name | Library Definition |
|---------|-------------|-------------------|
| 3200 | Digital Input | `digital.yaml: digital_input` |
| 3201 | Digital Output | (actuator) |
| 3202 | Analog Input | `industrial.yaml: analog_4_20ma` |
| 3301 | Illuminance | `environmental.yaml: illuminance_lux` |
| 3302 | Presence | `motion.yaml: pir`, `occupancy` |
| 3303 | Temperature | `environmental.yaml: temperature_*` |
| 3304 | Humidity | `environmental.yaml: humidity_*` |
| 3313 | Accelerometer | `motion.yaml: accel_x/y/z` |
| 3314 | Magnetometer | `magnetic.yaml: mag_x/y/z` |
| 3315 | Barometer | `environmental.yaml: pressure_*` |
| 3316 | Voltage | `power.yaml: supply_voltage` |
| 3317 | Current | `power.yaml: current_ma` |
| 3318 | Frequency | `industrial.yaml: frequency_hz` |
| 3319 | Depth | `distance.yaml: depth_m` |
| 3320 | Percentage | `power.yaml: battery_pct` |
| 3321 | Altitude | `position.yaml: altitude_m` |
| 3322 | Load | `industrial.yaml: load_kg` |
| 3323 | Pressure | `environmental.yaml: pressure_*` |
| 3324 | Loudness | `environmental.yaml: noise_db` |
| 3325 | Concentration | `environmental.yaml: co2_ppm`, `air_quality.yaml: co_ppm` |
| 3326 | Acidity | `flow.yaml: ph` |
| 3327 | Conductivity | `flow.yaml: ec_uscm` |
| 3328 | Power | `metering.yaml: active_power_w` |
| 3330 | Distance | `distance.yaml: distance_*` |
| 3331 | Energy | `metering.yaml: energy_kwh` |
| 3332 | Direction | `weather.yaml: wind_direction` |
| 3334 | Gyrometer | `magnetic.yaml: gyro_x/y/z` |
| 3336 | GPS Location | `position.yaml: latitude, longitude` |
| 3347 | Push Button | `user_input.yaml: button_pressed` |

## UNECE Code Reference

| UNECE | Unit | Library Usage |
|-------|------|---------------|
| CEL | °C | temperature_* |
| FAH | °F | temperature_f_* |
| P1 | % | humidity_*, battery_pct |
| PAL | Pa | pressure_pa |
| A97 | hPa | pressure_hpa_* |
| BAR | bar | (industrial pressure) |
| VLT | V | supply_voltage, battery_v |
| AMP | A | (high current) |
| WTT | W | active_power_w |
| KWH | kWh | energy_kwh |
| WHR | Wh | energy_wh |
| MTR | m | distance_m, altitude_m |
| MMT | mm | distance_mm |
| CMT | cm | distance_cm |
| LUX | lx | illuminance_lux |
| LTR | L | volume_liters |
| MTQ | m³ | volume_m3 |
| GLL | gal | volume_gallons |
| KGM | kg | load_kg |
| NEW | N | load_n |
| HTZ | Hz | frequency_hz |
| MTS | m/s | wind_speed_ms |
| KMH | km/h | wind_speed_kmh |
| OHM | Ω | resistance_ohm |
| 2N | dB | noise_db |
| 59 | ppm | co2_ppm |

## SenML Unit Mapping

The `unit` field in definitions uses SenML-compatible units per RFC 8428:

| SenML Unit | Library Field |
|------------|---------------|
| Cel | temperature (°C) |
| %RH | humidity |
| Pa, hPa | pressure |
| lx | illuminance |
| dB | noise |
| m, mm, cm | distance |
| V, mV | voltage |
| A, mA | current |
| W | power |
| lat, lon | GPS coordinates |

## TTN Sensor Type Coverage

All TTN lorawan-devices sensor types mapped:

| TTN Type | Library File | Definition(s) |
|----------|--------------|---------------|
| temperature | environmental | temperature_c_div10, temperature_c_div100 |
| humidity | environmental | humidity_pct, humidity_pct_half |
| pressure/barometer | environmental | pressure_hpa_div10, pressure_pa |
| co2 | environmental | co2_ppm |
| tvoc/bvoc | environmental | tvoc_ppb, tvoc_index |
| pm2.5/pm10/dust | environmental | pm1_0, pm2_5, pm10 |
| light | environmental | illuminance_lux |
| sound | environmental | noise_db |
| battery | power | battery_pct, battery_mv, battery_v |
| voltage | power | supply_voltage |
| current | power | current_ma |
| power | power, metering | power_w, active_power_w |
| energy | metering | energy_kwh, energy_wh |
| gps | position | latitude, longitude, altitude_m |
| accelerometer | motion | accel_x, accel_y, accel_z |
| gyroscope | magnetic | gyro_x, gyro_y, gyro_z |
| magnetometer | magnetic | mag_x, mag_y, mag_z |
| tilt | motion | tilt_angle, tilt_x, tilt_y |
| pir/motion/occupancy | motion | pir, motion, occupancy, people_count |
| distance/level | distance | distance_mm, level_pct |
| water | flow, digital | water_volume, water_leak |
| pulse count | digital | pulse_count |
| digital input | digital | digital_input, gpio_state |
| button | user_input | button_pressed, button_action |
| switch | user_input | switch_state |
| wind speed/direction | weather | wind_speed_ms, wind_direction |
| rainfall/precipitation | weather | rainfall_mm |
| solar radiation | weather | solar_radiation_wm2, par_umol |
| uv | weather | uv_index |
| moisture | soil | soil_moisture_pct |
| conductivity | flow, soil | ec_uscm, soil_ec |
| ph | flow | ph |
| turbidity | flow | turbidity_ntu |
| dissolved oxygen | flow | dissolved_oxygen |
| co | air_quality | co_ppm |
| no/no2 | air_quality | no_ppb, no2_ppb |
| o3 | air_quality | ozone_ppb |
| so2 | air_quality | so2_ppb |
| h2s | air_quality | h2s_ppm |
| smoke | safety | smoke_detected |
| proximity | safety | proximity_mm |
| radar | safety | radar_presence |
| lightning | safety | lightning_distance_km |
| vibration | industrial | vibration_mms, vibration_g |
| strain | industrial | strain_ustrain |
| 4-20 ma | industrial | analog_4_20ma |
| analog input | industrial | analog_0_10v, adc_raw |
| reed switch | magnetic | reed_switch |
| hall effect | magnetic | hall_effect |
| potentiometer | user_input | potentiometer_pct |
| leaf wetness | soil | leaf_wetness |
| sap flow | soil | sap_flow |
| salinity | flow | salinity_ppt |

## Adding Semantics to Your Schema

Reference library definitions to inherit semantic metadata:

```yaml
fields:
  - $ref: "schemas/library/sensors/environmental.yaml#/definitions/temperature_c_div10"
  - $ref: "schemas/library/sensors/environmental.yaml#/definitions/humidity_pct"
  - $ref: "schemas/library/sensors/power.yaml#/definitions/battery_pct"
```

The interpreter's `get_field_metadata()` returns all semantic fields:

```python
metadata = interpreter.get_field_metadata()
# Returns: {
#   'temperature': {
#     'unit': '°C',
#     'valid_range': [-40, 125],
#     'resolution': 0.1,
#     'unece': 'CEL',
#     'ipso': 3303
#   },
#   ...
# }
```
