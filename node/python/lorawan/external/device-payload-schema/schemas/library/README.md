# Payload Schema Library

Reusable sensor type definitions for building LoRaWAN payload schemas.

## Usage

Use the preprocessor to resolve cross-file references:

```bash
python tools/schema_preprocessor.py my_sensor.yaml -o my_sensor_resolved.yaml
```

Then use the resolved schema with any interpreter.

## Library Structure

```
schemas/library/
├── sensors/           # Individual sensor type definitions
│   ├── environmental.yaml   # Temperature, humidity, pressure, CO2, etc.
│   ├── power.yaml          # Battery, voltage, current, energy
│   ├── position.yaml       # GPS, accelerometer, gyroscope
│   ├── distance.yaml       # Ultrasonic, radar, level sensors
│   ├── digital.yaml        # Digital I/O, counters, presence
│   └── flow.yaml           # Water/gas meters, flow rates
│
├── lorawan/           # LoRaWAN L2 protocol (TS001)
│   ├── lorawan_frames.yaml        # Frame structures (MHDR, FHDR, Join)
│   └── lorawan_mac_commands.yaml  # MAC commands (1.0.0-1.1.0)
│
├── gateway/           # Gateway-to-server protocols
│   ├── udp_packet_forwarder.yaml  # Semtech UDP protocol (JSON)
│   └── basic_station.yaml         # LoRa Basic Station (JSON)
│
├── commands/          # Application layer commands
│   ├── ts003_clock_sync.yaml      # TS003 clock synchronization (FPort 202)
│   ├── ts004_fragmentation.yaml   # TS004 fragmented data block (FPort 201)
│   ├── ts005_multicast.yaml       # TS005 remote multicast setup (FPort 200)
│   ├── ts006_firmware_mgmt.yaml   # TS006 firmware management (FPort 203)
│   ├── ts007_multi_package.yaml   # TS007 multi-package access (FPort 225)
│   └── app_control_plane.yaml     # Proposed app control plane (no FPort assigned)
│
├── profiles/          # Pre-built sensor combinations
│   ├── env-sensor.yaml     # Environmental sensor profiles
│   └── tracker.yaml        # GPS tracker profiles
│
└── common/            # Headers and utilities
    └── headers.yaml        # Message headers, timestamps, device info
```

## Payload Size Targets (RP002)

Design payloads to fit within these FRMPayload limits:

| Target | Compatibility |
|--------|---------------|
| **11 bytes** | Universal - works everywhere including US915 DR0 |
| **51 bytes** | EU868/CN470/IN865 all DRs, US915 DR1+ |
| **115 bytes** | DR3+ in most regions |
| **242 bytes** | DR4+ only (max payload) |

## Example Schema

```yaml
name: my_env_sensor
version: 1
endian: big

fields:
  # Use library definitions
  - $ref: "schemas/library/common/headers.yaml#/definitions/msg_type_header"
  - $ref: "schemas/library/profiles/env-sensor.yaml#/definitions/temp_humidity"
  - $ref: "schemas/library/sensors/power.yaml#/definitions/battery_mv"
  - $ref: "schemas/library/sensors/power.yaml#/definitions/battery_pct_from_mv"
  
  # Add device-specific fields
  - name: custom_status
    type: u8

test_vectors:
  - name: normal_reading
    payload: "01 00E7 32 0BB8"
    expected:
      msg_type: 1
      temperature: 23.1
      humidity: 25.0
      battery_mv: 3000
      battery_percent: 83.3
      custom_status: 0
```

## Field Renaming

Use `rename:` to change field names when including definitions. Useful for multiple sensors of the same type:

```yaml
fields:
  # Two temperature sensors with different names
  - $ref: "schemas/library/sensors/environmental.yaml#/definitions/temperature_c"
    rename:
      temperature: indoor_temp
      
  - $ref: "schemas/library/sensors/environmental.yaml#/definitions/temperature_c"
    rename:
      temperature: outdoor_temp
```

Use `prefix:` to add a prefix to all field names:

```yaml
fields:
  # Add "zone1_" prefix to all fields
  - $ref: "schemas/library/profiles/env-sensor.yaml#/definitions/temp_humidity"
    prefix: "zone1_"
    
  # Results in: zone1_temperature, zone1_humidity
  
  - $ref: "schemas/library/profiles/env-sensor.yaml#/definitions/temp_humidity"
    prefix: "zone2_"
    
  # Results in: zone2_temperature, zone2_humidity
```

Combine both (prefix applied first, then renames):

```yaml
fields:
  - $ref: "schemas/library/profiles/env-sensor.yaml#/definitions/temp_humidity"
    prefix: "room_"
    rename:
      room_temperature: room_temp  # Shorten after prefix
```

## Available Definitions

### Environmental (`schemas/library/sensors/environmental.yaml`)

| Definition | Type | Description |
|------------|------|-------------|
| `temperature_c` | s16/10 | Temperature °C, 0.1° resolution |
| `temperature_c_hp` | s16/100 | Temperature °C, 0.01° resolution |
| `temperature_c_offset` | u16/10-40 | Temperature with -40° offset |
| `humidity_pct` | u8*0.5 | Humidity %, 0.5% resolution |
| `humidity_pct_hp` | u16/10 | Humidity %, 0.1% resolution |
| `pressure_hpa` | u16/10 | Pressure hPa |
| `co2_ppm` | u16 | CO2 concentration ppm |
| `tvoc_ppb` | u16 | TVOC ppb |
| `pm25` | u16 | PM2.5 μg/m³ |
| `illuminance_lux` | u16 | Light level lux |

### Power (`schemas/library/sensors/power.yaml`)

| Definition | Type | Description |
|------------|------|-------------|
| `battery_mv` | u16 | Battery voltage mV |
| `battery_v` | u16/100 | Battery voltage V |
| `battery_pct` | u8 | Battery percentage |
| `battery_pct_from_mv` | computed | Battery % from mV (2.0-3.2V) |
| `power_w` | u16 | Power Watts |
| `energy_kwh` | u32/1000 | Energy kWh |
| `current_ma` | u16 | Current mA |
| `voltage_v` | u16/100 | Voltage V |

### Position (`schemas/library/sensors/position.yaml`)

| Definition | Type | Description |
|------------|------|-------------|
| `latitude` | s32/10M | Latitude degrees |
| `longitude` | s32/10M | Longitude degrees |
| `altitude` | s32/100 | Altitude meters |
| `gps_position` | composite | Lat + Lon + Alt |
| `gps_position_compact` | s24/10k | Reduced precision GPS |
| `accelerometer_g` | s16/1000 | Accel XYZ in g |
| `gyroscope_dps` | s16/100 | Gyro XYZ °/s |

### Profiles (`schemas/library/profiles/`)

| Definition | Contents |
|------------|----------|
| `temp_humidity` | Temperature + Humidity |
| `temp_humidity_pressure` | + Pressure |
| `indoor_air_quality` | + CO2 + TVOC |
| `gps_basic` | Lat + Lon + Alt |
| `full_tracker` | GPS + Speed + Heading + Battery |

## LoRaWAN Protocol Definitions

Standardized LoRa Alliance protocol definitions for prototyping and codec development.

### TS001 L2 Layer

#### Frame Structures (`schemas/library/lorawan/lorawan_frames.yaml`)

| Structure | Description |
|-----------|-------------|
| `MHDR` | MAC header (MType, RFU, Major) |
| `FHDR` | Frame header (DevAddr, FCtrl, FCnt, FOpts) |
| `FCtrl_Uplink` | Frame control for uplink |
| `FCtrl_Downlink` | Frame control for downlink |
| `JoinRequest` | OTAA join request |
| `JoinAccept` | OTAA join accept |
| `RejoinRequest` | 1.1.0+ rejoin messages |
| `CFList` | Channel frequency list |

#### MAC Commands (`schemas/library/lorawan/lorawan_mac_commands.yaml`)

| CID | Command | Versions | Description |
|-----|---------|----------|-------------|
| 0x02 | `LinkCheckReq/Ans` | 1.0.0+ | Link quality check |
| 0x03 | `LinkADRReq/Ans` | 1.0.0+ | Data rate / TX power |
| 0x04 | `DutyCycleReq/Ans` | 1.0.0+ | Max duty cycle |
| 0x05 | `RXParamSetupReq/Ans` | 1.0.0+ | RX2 window params |
| 0x06 | `DevStatusReq/Ans` | 1.0.0+ | Battery / margin |
| 0x07 | `NewChannelReq/Ans` | 1.0.0+ | Create/modify channel |
| 0x08 | `RXTimingSetupReq/Ans` | 1.0.0+ | RX1 delay |
| 0x09 | `TxParamSetupReq/Ans` | 1.0.2+ | Max EIRP / dwell time |
| 0x0A | `DlChannelReq/Ans` | 1.0.2+ | DL channel frequency |
| 0x0B | `RekeyInd/Conf` | 1.1.0+ | Rekey confirmation |
| 0x0C | `ADRParamSetupReq/Ans` | 1.1.0+ | ADR parameters |
| 0x0D | `DeviceTimeReq/Ans` | 1.1.0+ | GPS time request |
| 0x0E | `ForceRejoinReq` | 1.1.0+ | Force rejoin |
| 0x0F | `RejoinParamSetupReq/Ans` | 1.1.0+ | Rejoin params |

### Gateway Protocols

#### UDP Packet Forwarder (`schemas/library/gateway/udp_packet_forwarder.yaml`)

| Packet Type | Value | Direction | Description |
|-------------|-------|-----------|-------------|
| PUSH_DATA | 0x00 | GW → NS | Uplink + status |
| PUSH_ACK | 0x01 | NS → GW | Acknowledge PUSH_DATA |
| PULL_DATA | 0x02 | GW → NS | Keepalive / request downlink |
| PULL_RESP | 0x03 | NS → GW | Downlink data |
| PULL_ACK | 0x04 | NS → GW | Acknowledge PULL_DATA |
| TX_ACK | 0x05 | GW → NS | Downlink TX result |

#### LoRa Basic Station (`schemas/library/gateway/basic_station.yaml`)

| Message | Direction | Description |
|---------|-----------|-------------|
| `version` | GW → LNS | Gateway announces capabilities |
| `router_config` | LNS → GW | LNS configures gateway |
| `jreq` | GW → LNS | Join request |
| `updf` | GW → LNS | Uplink data frame |
| `dnmsg` | LNS → GW | Downlink message |
| `dntxed` | GW → LNS | Downlink TX confirmation |
| `timesync` | Both | Time synchronization |

**Also includes:** CUPS protocol, feature flags, region codes

### Application Layer Specs

#### TS003 Clock Sync (`schemas/library/commands/ts003_clock_sync.yaml`)

| CID | Command | Direction | Description |
|-----|---------|-----------|-------------|
| 0x00 | `PackageVersionReq/Ans` | Down/Up | Version discovery |
| 0x01 | `AppTimeReq/Ans` | Up/Down | Clock correction request |
| 0x02 | `DeviceAppTimePeriodicityReq/Ans` | Down/Up | Set sync periodicity |
| 0x03 | `ForceDeviceResyncCmd` | Down | Force resync |

#### TS004 Fragmentation (`schemas/library/commands/ts004_fragmentation.yaml`)

| CID | Command | Direction | Description |
|-----|---------|-----------|-------------|
| 0x00 | `PackageVersionReq/Ans` | Down/Up | Version discovery |
| 0x01 | `FragSessionStatusReq/Ans` | Down/Up | Query session status |
| 0x02 | `FragSessionSetupReq/Ans` | Down/Up | Create session |
| 0x03 | `FragSessionDeleteReq/Ans` | Down/Up | Delete session |
| 0x04 | `DataBlockReceivedReq/Ans` | Up/Down | Signal completion |
| 0x08 | `DataFragment` | Down | Fragment payload |

#### TS005 Multicast (`schemas/library/commands/ts005_multicast.yaml`)

| CID | Command | Direction | Description |
|-----|---------|-----------|-------------|
| 0x00 | `PackageVersionReq/Ans` | Down/Up | Version discovery |
| 0x01 | `McGroupStatusReq/Ans` | Down/Up | Query group status |
| 0x02 | `McGroupSetupReq/Ans` | Down/Up | Setup multicast group |
| 0x03 | `McGroupDeleteReq/Ans` | Down/Up | Delete multicast group |
| 0x04 | `McClassCSessionReq/Ans` | Down/Up | Create Class C session |
| 0x05 | `McClassBSessionReq/Ans` | Down/Up | Create Class B session |

#### TS006 Firmware Mgmt (`schemas/library/commands/ts006_firmware_mgmt.yaml`)

| CID | Command | Direction | Description |
|-----|---------|-----------|-------------|
| 0x00 | `PackageVersionReq/Ans` | Down/Up | Version discovery |
| 0x01 | `DevVersionReq/Ans` | Down/Up | Query FW/HW version |
| 0x02 | `DevRebootTimeReq/Ans` | Down/Up | Schedule reboot at time |
| 0x03 | `DevRebootCountdownReq/Ans` | Down/Up | Schedule reboot after delay |
| 0x04 | `DevUpgradeImageReq/Ans` | Down/Up | Query upgrade image |
| 0x05 | `DevDeleteImageReq/Ans` | Down/Up | Delete upgrade image |

#### TS007 Multi-Package (`schemas/library/commands/ts007_multi_package.yaml`)

| CID | Command | Direction | Description |
|-----|---------|-----------|-------------|
| 0x00 | `PackageVersionReq/Ans` | Down/Up | Discover all packages |

### Proposed: App Control Plane (`schemas/library/commands/app_control_plane.yaml`)

**Status:** Proposal based on TTN lorawan-devices codec library patterns. No FPort officially assigned.

Commands are organized by CID ranges:

| CID Range | Category | Note |
|-----------|----------|------|
| 0x00-0x0F | Device Management | Could extend TS006 |
| 0x10-0x1F | Data Logging | Could extend TS004 |
| 0x20-0x2F | Sensor Configuration | |
| 0x30-0x3F | Alarm/Threshold Config | |
| 0x40-0x4F | Utility Meter | |
| 0x50-0x5F | GPS/Tracker | |
| 0x60-0x7F | Reserved | |

**Device Management (0x00-0x0F):**

| CID | Command | Description |
|-----|---------|-------------|
| 0x00 | `DevFactoryResetReq/Ans` | Factory reset device |
| 0x01 | `DevConfigReq/Ans` | Request config dump |
| 0x02 | `DevIdentifyReq/Ans` | Blink LED / beep |

**Data Logging (0x10-0x1F):**

| CID | Command | Description |
|-----|---------|-------------|
| 0x10 | `DataLogConfigReq/Ans` | Configure on-device logging |
| 0x11 | `DataLogFetchReq/Ans` | Request historical data |
| 0x12 | `DataLogClearReq/Ans` | Clear stored data |
| 0x13 | `DataLogStatusReq/Ans` | Query storage status |

**Sensor Configuration (0x20-0x2F):**

| CID | Command | Description |
|-----|---------|-------------|
| 0x20 | `SensorIntervalReq/Ans` | Set reporting interval |
| 0x21 | `SensorReadReq/Ans` | Request immediate reading |
| 0x22 | `SensorCalibReq/Ans` | Set calibration offset |
| 0x23 | `SensorEnableReq/Ans` | Enable/disable fields |
| 0x24 | `SensorProfileReq/Ans` | Switch sensor profile |
| 0x25 | `SensorConfigReq/Ans` | Query sensor config |

**Alarm/Threshold (0x30-0x3F):**

| CID | Command | Description |
|-----|---------|-------------|
| 0x30 | `SensorThresholdReq/Ans` | Set change-on-delta threshold |
| 0x31 | `SensorAlarmReq/Ans` | Set alarm thresholds |

**Utility Meter (0x40-0x4F):**

| CID | Command | Description |
|-----|---------|-------------|
| 0x40 | `MeterSetTariffReq/Ans` | Set active tariff |
| 0x41 | `MeterResetCounterReq/Ans` | Reset energy counter |
| 0x42 | `MeterSetCTRatioReq/Ans` | Set CT ratio |

**GPS/Tracker (0x50-0x5F):**

| CID | Command | Description |
|-----|---------|-------------|
| 0x50 | `GpsSetGeofenceReq/Ans` | Set geofence |
| 0x51 | `GpsClearGeofenceReq/Ans` | Clear geofence |
| 0x52 | `GpsSetMotionModeReq/Ans` | Configure motion behavior |
| 0x53 | `GpsRequestPositionReq/Ans` | Force GPS fix |

## IPSO Mappings

All sensor definitions include IPSO Smart Object mappings where applicable:

| Sensor Type | IPSO Object |
|-------------|-------------|
| Temperature | 3303 |
| Humidity | 3304 |
| Pressure | 3315 |
| Illuminance | 3301 |
| Voltage/Battery | 3316 |
| Current | 3317 |
| Power | 3328 |
| Energy | 3331 |
| GPS Location | 3336 |
| Accelerometer | 3313 |
| Gyroscope | 3334 |
| Digital Input | 3200 |
| Digital Output | 3201 |
| Presence | 3302 |

## Extending the Library

Add new definitions to the appropriate category file:

```yaml
# schemas/library/sensors/environmental.yaml
definitions:
  # ... existing definitions ...
  
  my_custom_sensor:
    - name: soil_moisture
      type: u16
      div: 10
      unit: "%"
      ipso: {object: 3323, resource: 5700}
```

Or create a new category file and reference it in your schemas.
