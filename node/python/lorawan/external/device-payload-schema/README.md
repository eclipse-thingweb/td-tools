# Device Payload Schema

Declarative payload schema definitions for IoT device codecs.

**New to this toolkit?** Start with the [Getting Started Guide](docs/GETTING-STARTED.md).

## Overview

This repository provides:

- **YAML Schema Language**: Declarative payload definitions for binary-to-JSON decoding
- **Reference Interpreters**: Python, JavaScript, Java, Go, C implementations
- **Code Generators**: Generate TS013-compliant codec code from schemas
- **Device Schemas**: Ready-to-use schemas for common devices (Decentlab, Milesight, etc.)

The schema language enables device manufacturers and integrators to define payload
structures once, then automatically generate decoders for multiple platforms.

## Quick Start

### Prerequisites

```bash
# Python development
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Decode a Payload

```bash
# Using the Python interpreter
python tools/schema_interpreter.py decode \
  schemas/devices/decentlab/dl-5tm.yaml \
  "02 1234 0003 01F4 0190 0C1C"
```

### Generate a Codec

```bash
# Generate JavaScript decoder
python tools/generate_ts013_codec.py schemas/decentlab/dl-5tm.yaml

# Generate C header
python tools/generate_firmware_codec.py schemas/decentlab/dl-5tm.yaml
```

### Run Tests

```bash
pytest tests/ -v
```

### Score a Schema

```bash
# Check schema quality and scoring tier
python tools/score_schema.py schemas/devices/decentlab/dl-5tm.yaml --verbose

# Output: PLATINUM (95.0%) with recommendations
```

Quality tiers: Bronze (50-69%), Silver (70-84%), Gold (85-94%), Platinum (95-100%)

Scoring includes: schema validity, test vectors, Python/JS cross-validation, branch coverage, edge cases, and semantic annotations (IPSO, SenML, TTN normalized).

## Repository Structure

```
payload-codec-proto/
├── schemas/                     # Device payload schemas
│   ├── devices/                # Device-specific schemas (YAML)
│   ├── payload-schema.json     # Meta-schema for YAML validation
│   ├── ipso-output.schema.json # IPSO format output validation
│   ├── senml-output.schema.json # SenML format output validation
│   └── ttn-output.schema.json  # TTN normalized output validation
│
├── tools/                       # Interpreters and generators
│   ├── schema_interpreter.py   # Reference Python decoder
│   ├── generate_ts013_codec.py # TS013 JavaScript generator
│   ├── generate_output_schema.py # Output JSON Schema generator
│   ├── generate_firmware_codec.py # C code generator
│   ├── validate_schema.py      # Schema validator
│   ├── score_schema.py         # Quality scoring tool
│   └── convert_*.py            # Converter utilities
│
├── include/                     # C reference implementation
│   └── schema_interpreter.h    # Header-only C decoder
│
├── tests/                       # Test suite
│   └── test_schema_interpreter.py
│
├── docs/                        # Documentation
│   ├── LANGUAGE-ANALYSIS.md    # Schema language design
│   └── SPEC-IMPLEMENTATION-STATUS.md
│
└── examples/                    # Usage examples
```

## Schema Language

### Basic Example

```yaml
name: temperature_sensor
version: 1
endian: big

fields:
  - name: temperature
    type: i16
    div: 10
    unit: "°C"
    
  - name: humidity
    type: u8
    unit: "%"
```

### Features

- **Field Types**: u8, u16, u32, i8, i16, i32, float32, bool, string, bytes
- **Bit Fields**: `u8[0:3]` for bit extraction
- **Arithmetic**: `add`, `mult`, `div` modifiers
- **Polynomial**: Calibration curves with `polynomial: [a, b, c, d]`
- **Computed Fields**: Cross-field arithmetic with `compute: {op: div, a: $x, b: $y}`
- **Guards**: Conditional evaluation with `guard: {when: [...], else: 0}`
- **Conditional Parsing**: `switch` and `flagged` for dynamic structures
- **TLV/LTV**: Tag-Length-Value parsing

See the schema language documentation for complete reference.

## Performance & Security

### Why Declarative Schemas?

Traditional LoRaWAN(R) codecs use JavaScript with `eval()` or `new Function()`, creating security risks on shared infrastructure. Declarative schemas eliminate this attack surface entirely.

### Performance Comparison

| Implementation | Throughput | Security | Use Case |
|----------------|------------|----------|----------|
| **C Interpreter** | 33M msg/s | ✅ No eval | High-performance backends |
| **Java Schema** | 3.7M msg/s | ✅ No eval | JVM backends (best high-level perf) |
| **Go Binary Schema** | 2.1M msg/s | ✅ No eval | Cloud platforms |
| **Go YAML Schema** | 1.3M msg/s | ✅ No eval | Go backends |
| **JS Schema (Node)** | 638K msg/s | ✅ No eval | Node.js backends |
| **JS Traditional** | 22M msg/s | ⚠️ eval risk | Legacy compatibility |
| **Python Schema** | 184K msg/s | ✅ No eval | Prototyping |

### Backend Recommendations

| Scenario | Recommended | Why |
|----------|-------------|-----|
| **Multi-tenant LNS** | C Interpreter | 33M msg/s, no code execution |
| **JVM backend** | Java Schema | 3.7M msg/s, lowest overhead (3x) |
| **Cloud platform (Go)** | Go Binary Schema | 2.1M msg/s, easy deployment |
| **Edge gateway** | C or QuickJS | Embedded-friendly |
| **Development** | Python/YAML | Human-readable, fast iteration |

### Headroom

Even Python (184K msg/s) handles 1,800x typical gateway traffic. Java at 3.7M msg/s has 370,000x headroom for single-gateway loads.

See [benchmarks documentation](docs/BENCHMARKS.md) for detailed results.

## Code Generation

### TS013-Compliant JavaScript

```bash
python tools/generate_ts013_codec.py schemas/devices/decentlab/dl-5tm.yaml > dl_5tm_codec.js
```

Generates decoders compatible with The Things Network, ChirpStack, and other
LoRaWAN network servers that support the TS013 Payload Codec API.

### Output JSON Schema

```bash
python tools/generate_output_schema.py schemas/devices/decentlab/dl-5tm.yaml > dl_5tm_output.schema.json
```

Generates a JSON Schema describing the decoded payload structure. This schema
enables validation of decoder output with standard JSON Schema tools.

### Embedded C

```bash
python tools/generate_firmware_codec.py schemas/devices/decentlab/dl-5tm.yaml > dl_5tm_codec.h
```

Generates header-only C decoders for embedded systems (Arduino, ESP32, STM32, etc.).

## Compatibility

### TS013 Payload Codec API

Generated codecs implement the TS013 interface:

```javascript
function decodeUplink(input) {
  return {
    data: { /* decoded fields */ },
    warnings: [],
    errors: []
  };
}
```

### TTN Device Repository

Schemas can be converted to/from The Things Network device repository format.
See `tools/convert_ttn.py` for conversion utilities.

## Contributing

Contributions welcome! Please:

1. Add test vectors for new schemas
2. Ensure `pytest` passes
3. Run `python tools/validate_schema.py` on new schemas

## License

MIT License

Copyright (c) 2024-2026 Multitech Systems, Inc.
Author: Jason Reiss

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Documentation

- [Language Analysis](docs/LANGUAGE-ANALYSIS.md) - Schema language design rationale
- [Implementation Status](docs/SPEC-IMPLEMENTATION-STATUS.md) - Feature support matrix
- [Formula Migration](docs/FORMULA-MIGRATION-TRACKING.md) - Migration to declarative constructs
