# Go Schema Decoder/Encoder

Reference implementation of the LoRaWAN Payload Schema decoder and encoder in Go.

## Installation

```bash
go get github.com/MultiTechSystems/lorawan-payload-schema/go/schema
```

## Usage

```go
import "github.com/MultiTechSystems/lorawan-payload-schema/go/schema"

// Parse a schema from YAML
s, err := schema.ParseSchema(`
name: temperature_sensor
endian: big
fields:
  - name: temperature
    type: u16
    div: 100
    unit: "°C"
`)

// Decode payload
decoded, err := s.Decode([]byte{0x09, 0xC4}) // 2500 -> 25.00°C

// Encode data
encoded, err := s.Encode(map[string]any{"temperature": 25.0})
```

## Phase 2 Features

This implementation supports the declarative computed value constructs:

### ref - Field Reference
```yaml
- name: temperature
  type: number
  ref: $raw_temp
  transform:
    - sub: 400
    - div: 10
```

### polynomial - Horner's Method
```yaml
- name: calibrated
  type: number
  ref: $raw_value
  polynomial: [0.1, -4, 30]  # 0.1x² - 4x + 30
```

### compute - Binary Operations
```yaml
- name: albedo
  type: number
  compute:
    op: div
    a: $reflected
    b: $incoming
```

### guard - Conditional Evaluation
```yaml
- name: temperature
  type: number
  ref: $raw_temp
  transform:
    - div: 10
  guard:
    when:
      - field: $raw_temp
        gt: 0
        lt: 2000
    else: -999
```

## Running Tests

```bash
go test -v ./...
```

## License

MIT License - Copyright (c) 2024-2026 Multitech Systems, Inc. - Author: Jason Reiss
