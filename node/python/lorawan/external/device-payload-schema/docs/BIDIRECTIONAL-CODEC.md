# Bidirectional Codec Architecture

The Payload Schema codec is symmetric - both devices and networks use the same encode/decode functions, just for opposite link directions.

## Device vs Network Responsibilities

**Important:** Devices do NOT need knowledge of semantic formats (IPSO, SenML, TTN). 
The device codec only handles byte-level encoding/decoding. Semantic transformation 
happens on the network side.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ DEVICE (Resource Constrained)          NETWORK (Resource Rich)              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Encoder                               Decoder                              │
│  ┌─────────────────────┐               ┌─────────────────────────────────┐  │
│  │ temp=23.45 → 0x0929 │───────────────│ 0x0929 → temp=23.45             │  │
│  │ hum=65.0  → 0x82    │   payload     │            │                    │  │
│  │                     │               │            ├──► Raw JSON        │  │
│  │ • Field types       │               │            ├──► IPSO /3303/0/   │  │
│  │ • Modifiers         │               │            ├──► SenML [{n,v,u}] │  │
│  │ • Byte order        │               │            └──► TTN normalized  │  │
│  │                     │               │                                 │  │
│  │ NO IPSO knowledge   │               │ • Semantic mapping              │  │
│  │ NO SenML knowledge  │               │ • Output format conversion      │  │
│  │ Just bytes          │               │ • Unit annotations              │  │
│  └─────────────────────┘               └─────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

This separation keeps devices simple and small. All "smart" formatting happens 
server-side where memory and CPU are plentiful.

**This applies to BOTH directions:**

```
UPLINK (Device → Network)
┌──────────────────┐                    ┌─────────────────────────────┐
│ Device Encoder   │                    │ Network Decoder             │
│                  │                    │                             │
│ temp=23.45       │                    │ 0x0929                      │
│ → 0x0929         │────── payload ────▶│ → temp=23.45                │
│                  │                    │   → IPSO/SenML/JSON/TTN     │
│ Just bytes       │                    │                             │
└──────────────────┘                    └─────────────────────────────┘

DOWNLINK (Network → Device)
┌─────────────────────────────┐         ┌──────────────────┐
│ Network Encoder             │         │ Device Decoder   │
│                             │         │                  │
│ App config (any format):    │         │ 0x0E10           │
│ • IPSO: /3308/0/5900: 3600  │         │ → interval=3600  │
│ • JSON: {interval: 3600}    │         │                  │
│ • Dashboard form            │         │ set_interval()   │
│         │                   │         │                  │
│         ▼                   │         │ Just bytes       │
│ interval=3600 → 0x0E10      │─────────▶                  │
└─────────────────────────────┘         └──────────────────┘
```

The device never sees or cares about IPSO, SenML, or any semantic format.
It only converts between values and bytes in both directions.

## Overview

```
┌─────────────────────┐                         ┌─────────────────────┐
│       DEVICE        │                         │      NETWORK        │
├─────────────────────┤                         ├─────────────────────┤
│                     │                         │                     │
│  ┌───────────────┐  │      Uplink Payload     │  ┌───────────────┐  │
│  │    ENCODER    │──┼─────────────────────────┼─▶│    DECODER    │  │
│  │ sensors→bytes │  │                         │  │ bytes→JSON    │  │
│  └───────────────┘  │                         │  └───────────────┘  │
│                     │                         │                     │
│  ┌───────────────┐  │     Downlink Payload    │  ┌───────────────┐  │
│  │    DECODER    │◀─┼─────────────────────────┼──│    ENCODER    │  │
│  │ bytes→config  │  │                         │  │ config→bytes  │  │
│  └───────────────┘  │                         │  └───────────────┘  │
│                     │                         │                     │
└─────────────────────┘                         └─────────────────────┘
```

## Link Directions

| Direction | Device Role | Network Role | Typical Content |
|-----------|-------------|--------------|-----------------|
| **Uplink** | Encode | Decode | Sensor readings, status, alarms |
| **Downlink** | Decode | Encode | Configuration, commands, ACKs |

## Schema Types

A device typically has two schemas:

### 1. Uplink Schema (Sensor Data)

```yaml
name: sensor_uplink
version: 1
endian: big
fields:
  - name: temperature
    type: s16
    mult: 0.01
  - name: humidity
    type: u8
    mult: 0.5
  - name: battery
    type: u16
```

**Device encodes:**
```c
encode_inputs_t inputs;
encode_inputs_add_double(&inputs, "temperature", 23.45);
encode_inputs_add_double(&inputs, "humidity", 65.0);
encode_inputs_add_double(&inputs, "battery", 3300);

encode_result_t result;
schema_encode(&uplink_schema, &inputs, &result);
// result.data = {0x09, 0x29, 0x82, 0x0C, 0xE4}
```

**Network decodes:**
```python
result = interpreter.decode(payload)
# {"temperature": 23.45, "humidity": 65.0, "battery": 3300}
```

### 2. Downlink Schema (Commands)

```yaml
name: device_config
version: 1
endian: big
fields:
  - name: command
    type: u8
    lookup:
      0x01: set_interval
      0x02: reboot
      0x03: set_threshold
  - name: parameter
    type: u16
```

**Network encodes:**
```python
payload = interpreter.encode({
    "command": 0x01,
    "parameter": 3600  # Set reporting interval to 1 hour
})
# payload = bytes([0x01, 0x0E, 0x10])
```

**Device decodes:**
```c
decode_result_t result;
schema_decode(&downlink_schema, payload, len, &result);

uint8_t cmd = result_get_int(&result, "command", 0);
uint16_t param = result_get_int(&result, "parameter", 0);

switch (cmd) {
    case 0x01: set_reporting_interval(param); break;
    case 0x02: system_reboot(); break;
    case 0x03: set_alarm_threshold(param); break;
}
```

## Binary Schema Benefits

With binary schemas, the codec is separated from schema data:

```
┌────────────────────────────────────────────────────────┐
│                    DEVICE FIRMWARE                      │
├────────────────────────────────────────────────────────┤
│  Generic Codec Library (~2KB)                          │
│  ├── schema_encode()                                   │
│  ├── schema_decode()                                   │
│  └── schema_load_binary()                              │
├────────────────────────────────────────────────────────┤
│  Uplink Schema (binary, ~30 bytes)   ← Flash/EEPROM   │
│  Downlink Schema (binary, ~20 bytes) ← Flash/EEPROM   │
└────────────────────────────────────────────────────────┘
```

**Advantages:**
- Same firmware binary across product variants
- Schema updates without reflashing
- OTA schema updates possible
- Schemas can be embedded in QR codes for provisioning

## C API Reference

### Decoding (Bytes → Values)

```c
#include "schema_interpreter.h"

// Load schema from binary
schema_t schema;
schema_load_binary(&schema, binary_data, binary_len);

// Decode payload
decode_result_t result;
int rc = schema_decode(&schema, payload, payload_len, &result);

// Access values
double temp = result_get_double(&result, "temperature", 0.0);
int64_t status = result_get_int(&result, "status", 0);
```

### Encoding (Values → Bytes)

```c
#include "schema_interpreter.h"

// Prepare input values
encode_inputs_t inputs;
encode_inputs_init(&inputs);
encode_inputs_add_double(&inputs, "temperature", 23.45);
encode_inputs_add_double(&inputs, "humidity", 65.0);
encode_inputs_add_double(&inputs, "battery", 3300);

// Encode to payload
encode_result_t result;
int rc = schema_encode(&schema, &inputs, &result);

// Send result.data (result.len bytes)
lora_send(result.data, result.len);
```

## Python API Reference

### Decoding

```python
from schema_interpreter import SchemaInterpreter

interpreter = SchemaInterpreter(schema_dict)
result = interpreter.decode(payload_bytes)
print(result.data)  # {"temperature": 23.45, ...}
```

### Encoding

```python
from schema_interpreter import SchemaInterpreter

interpreter = SchemaInterpreter(schema_dict)
result = interpreter.encode({
    "temperature": 23.45,
    "humidity": 65.0,
    "battery": 3300
})
payload = result.payload  # bytes
```

## Performance

| Operation | Python | C |
|-----------|--------|---|
| Decode | 5.8 µs | 0.04 µs |
| Encode | 4.2 µs | 0.03 µs |
| Schema load (binary) | 5 µs | 0.4 µs |

## Modifier Handling

Modifiers are applied in opposite directions:

| Direction | Operation | Modifier Order |
|-----------|-----------|----------------|
| **Decode** | bytes → value | raw × mult ÷ div + add |
| **Encode** | value → bytes | (value - add) × div ÷ mult |

Example with `mult: 0.01`:
- Decode: raw `2345` → `23.45`
- Encode: value `23.45` → raw `2345`

## Schema Distribution

```
                    ┌──────────────────┐
                    │  Schema Source   │
                    │  (YAML/JSON)     │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │  Binary  │  │  Device  │  │  Network │
        │  Schema  │  │  Catalog │  │  Server  │
        │  (.pbs)  │  │  (JSON)  │  │  Config  │
        └────┬─────┘  └──────────┘  └──────────┘
             │
    ┌────────┼────────┐
    │        │        │
    ▼        ▼        ▼
┌───────┐ ┌─────┐ ┌───────┐
│ Flash │ │ QR  │ │ OTA   │
│EEPROM │ │Code │ │Update │
└───────┘ └─────┘ └───────┘
```

## Example: Complete Device Implementation

```c
// device_codec.c - Minimal bidirectional codec

#include "schema_interpreter.h"

// Binary schemas (generated by schema_binary.py)
static const uint8_t UPLINK_SCHEMA[] = {
    0x50, 0x53, 0x01, 0x00, 0x03,  // Header
    0x12, 0xFE, 0xE7, 0x0C,        // temperature: s16, mult=0.01
    0x01, 0x81, 0xE8, 0x0C,        // humidity: u8, mult=0.5
    0x02, 0x00, 0xF4, 0x0C,        // battery: u16
};

static const uint8_t DOWNLINK_SCHEMA[] = {
    0x50, 0x53, 0x01, 0x00, 0x02,  // Header
    0x01, 0x00, 0x00, 0x80,        // command: u8
    0x02, 0x00, 0x01, 0x80,        // parameter: u16
};

static schema_t uplink_schema;
static schema_t downlink_schema;

void codec_init(void) {
    schema_load_binary(&uplink_schema, UPLINK_SCHEMA, sizeof(UPLINK_SCHEMA));
    schema_load_binary(&downlink_schema, DOWNLINK_SCHEMA, sizeof(DOWNLINK_SCHEMA));
}

int create_uplink(float temp, float hum, uint16_t bat, uint8_t* buf) {
    encode_inputs_t inputs;
    encode_inputs_init(&inputs);
    encode_inputs_add_double(&inputs, "temperature", temp);
    encode_inputs_add_double(&inputs, "humidity", hum);
    encode_inputs_add_double(&inputs, "voltage", bat);
    
    encode_result_t result;
    schema_encode(&uplink_schema, &inputs, &result);
    
    memcpy(buf, result.data, result.len);
    return result.len;
}

void handle_downlink(const uint8_t* payload, int len) {
    decode_result_t result;
    schema_decode(&downlink_schema, payload, len, &result);
    
    int cmd = result_get_int(&result, "command", 0);
    int param = result_get_int(&result, "parameter", 0);
    
    execute_command(cmd, param);
}
```

## See Also

- [C-INTERPRETER-STATUS.md](C-INTERPRETER-STATUS.md) - Implementation status
- [OTA-SCHEMA-TRANSFER.md](../la-payload-schema/docs/features/OTA-SCHEMA-TRANSFER.md) - Schema transfer protocol
- [Binary Schema Format](../tools/schema_binary.py) - Binary encoding tool
