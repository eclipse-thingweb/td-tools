# C Code Generation Guide

Generate standalone C codec headers from Payload Schema YAML files.

## Overview

The `generate_firmware_codec.py` tool creates header-only C codecs that:

- Define a struct for raw wire values
- Provide `pack_<name>()` function (struct → bytes for TX)
- Provide `unpack_<name>()` function (bytes → struct for RX)
- Use no dynamic allocation (embedded-friendly)
- Require no math library

## Design Decision: Raw Values Only

**The C firmware codec works with raw wire values only.** Schema transforms
(div, mult, sqrt, polynomial, etc.) are NOT applied in the generated C code.

### Rationale

1. **Sensors produce raw values** - ADC counts, register values, fixed-point integers
   are ready to transmit without transformation
2. **Simple normalization at read time** - If a sensor needs `*10` for fixed-point,
   do it when reading the sensor, not in the codec
3. **Complex math belongs server-side** - sqrt, log, polynomial calibration curves
   require floating-point math that bloats firmware (~2-8KB for `<math.h>`)
4. **Single source of truth** - Transform logic lives in the Python/JS interpreter,
   not duplicated across C firmware
5. **Smaller firmware** - No `<math.h>`, no floating-point bloat

### Data Flow

```
UPLINK (Device → Network):
  Sensor ADC → raw value → pack_*() → bytes → Network decode() + transforms

DOWNLINK (Network → Device):  
  Network encode() (reverse transforms) → bytes → unpack_*() → raw config
```

### If You Need Transformed Values On-Device

Apply transforms manually in application code:

```c
// Schema has: div: 100, add: -40
float temp_celsius = (float)data.temperature_raw / 100.0f - 40.0f;

// Schema has: div: 1000
float voltage = (float)data.battery_mv / 1000.0f;
```

This keeps the codec simple and gives you control over when/if to apply transforms.

## Usage

```bash
python tools/generate_firmware_codec.py schema.yaml -o output.h
```

**Example:**
```bash
python tools/generate_firmware_codec.py schemas/env_sensor.yaml -o include/env_sensor_codec.h
```

## Generated Code Structure

For a schema like:

```yaml
name: env_sensor
version: "1.0"
endian: little

fields:
  - name: temperature
    type: i16
    div: 100        # Applied on decode (network-side), NOT in C
  - name: humidity
    type: u8
    div: 2          # Applied on decode (network-side), NOT in C
  - name: battery_mv
    type: u16
  - name: status
    type: u8
```

The generator creates:

```c
typedef struct {
    int16_t temperature;   // Raw value (e.g., 2345 for 23.45°C)
    uint8_t humidity;      // Raw value (e.g., 130 for 65%)
    uint16_t battery_mv;
    uint8_t status;
} env_sensor_t;

static inline int pack_env_sensor(const env_sensor_t* data, uint8_t* buf);
static inline int unpack_env_sensor(const uint8_t* buf, size_t len, env_sensor_t* data);
```

Note: Struct holds **raw wire values**. The `div: 100` transform is applied by the
network-side interpreter, not in the C code.

## Device Usage Example

### Encoding (Uplink Transmission)

```c
#include "env_sensor_codec.h"

void send_uplink(void) {
    env_sensor_t data;
    uint8_t payload[16];
    
    // Fill struct with RAW sensor values
    // Sensor already returns fixed-point: 2345 for 23.45°C
    data.temperature = read_temp_sensor_raw();
    data.humidity = read_humidity_raw();
    data.battery_mv = read_battery_mv();
    data.status = get_status_flags();
    
    int len = pack_env_sensor(&data, payload);
    if (len > 0) {
        lorawan_send(FPORT, payload, len);
    }
}
```

### Decoding (Downlink Reception)

```c
#include "env_sensor_codec.h"

void handle_downlink(const uint8_t* payload, size_t len) {
    env_sensor_t config;
    
    int consumed = unpack_env_sensor(payload, len, &config);
    if (consumed < 0) {
        // Error handling
        return;
    }
    
    // Use raw values directly, or transform if needed
    set_reporting_interval(config.interval);
    set_threshold_raw(config.threshold);  // Raw value from network
}
```

## Return Values

| Value | Meaning |
|-------|---------|
| > 0 | Success: bytes written (pack) or consumed (unpack) |
| -1 | Invalid parameters (NULL pointer) |

## Dependencies

The generated headers are self-contained with only standard C headers:

```c
#include <stdint.h>
#include <stddef.h>
#include <string.h>
```

No external dependencies. No `<math.h>`. Byte-order helpers are included inline.

## Generated vs Runtime Interpreter

| Aspect | Generated (`generate_firmware_codec.py`) | Runtime (`schema_interpreter.h`) |
|--------|------------------------------------------|----------------------------------|
| Schema changes | Requires regenerate + recompile | Load new binary schema |
| Code size | Smaller per-schema | Fixed ~2KB + schema |
| Transforms | Not applied (raw values) | Applied at decode time |
| Math library | Not required | May require for transforms |
| Performance | Fastest | Fast |
| Use case | Production devices | Development, OTA updates |

## Feature Support

| Feature | pack_*() | unpack_*() | Notes |
|---------|----------|------------|-------|
| Basic types (u8-u64, s8-s64) | ✅ | ✅ | |
| Float types (f32, f64) | ✅ | ✅ | IEEE 754 bit patterns |
| byte_group | ✅ | ✅ | Bitfield extraction |
| flagged | ✅ | ✅ | Conditional on bitmask |
| match/switch | ✅ | ✅ | C switch statement |
| TLV | ⚠️ | ⚠️ | Partial support |
| Transforms (div, sqrt, etc.) | ❌ | ❌ | By design - see above |
| Nested objects | ❌ | ❌ | Flatten in schema |

For schemas requiring runtime transform application, use the binary schema interpreter.

## Example Workflow

```bash
# 1. Create/edit schema
vim schemas/my_sensor.yaml

# 2. Generate C header
python tools/generate_firmware_codec.py schemas/my_sensor.yaml -o firmware/codecs/my_sensor_codec.h

# 3. Include in firmware
#include "codecs/my_sensor_codec.h"

# 4. Regenerate after schema changes
python tools/generate_firmware_codec.py schemas/my_sensor.yaml -o firmware/codecs/my_sensor_codec.h
```

## Batch Generation

Generate codecs for all schemas in a directory:

```bash
python tools/generate_firmware_codec.py schemas/devices/ -o generated/
```
