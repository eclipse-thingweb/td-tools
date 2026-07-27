# Java Schema Interpreter

Pure Java implementation of the LoRaWAN payload schema interpreter.

## Features

- **YAML Schema Support**: Parse and decode using YAML schema definitions
- **Binary Schema Support**: Fast parsing of compact binary schema format (v2)
- **Formula Evaluation**: Recursive descent parser for computed fields
- **All Field Types**: Integers, floats, bits, strings, bytes, TLV, match, repeat, object
- **Low Overhead**: Only 3x slower than hand-coded decoders (best among high-level languages)

## Requirements

- Java 17+
- Maven 3.6+

## Building

```bash
cd bindings/java
mvn package
```

This produces:
- `target/payload-schema-1.0.0.jar` - Uber JAR with all dependencies

## Usage

### Basic Decoding

```java
import org.lora.schema.Schema;
import java.util.Map;

// Load schema from YAML file
Schema schema = Schema.fromYamlFile("schemas/devices/milesight/em310-udl.yaml");

// Decode payload
byte[] payload = new byte[] { 0x01, 0x75, 0x64 };
Map<String, Object> result = schema.decode(payload);

System.out.println(result);
// {battery: 100}
```

### Port-Based Decoding

```java
// Decode with fPort for port-specific schemas
Map<String, Object> result = schema.decodeWithPort(payload, 85);
```

### Binary Schema (Faster Parsing)

```java
// Load pre-compiled binary schema
byte[] binarySchema = Files.readAllBytes(Path.of("schema.bin"));
Schema schema = Schema.fromBinary(binarySchema);

// Decode as usual
Map<String, Object> result = schema.decode(payload);
```

## Performance

Benchmarked on AMD Ryzen 9 7950X3D with Milesight EM310-UDL schema:

| Implementation | Throughput | Latency | vs Traditional |
|----------------|------------|---------|----------------|
| **Traditional (hand-coded)** | 11.2M msg/s | 0.09 µs | 1x |
| **Schema Interpreter (YAML)** | 3.7M msg/s | 0.27 µs | 3.0x slower |
| **Cold Parse + Decode** | 21.6K msg/s | 46 µs | 519x slower |

### Comparison with Other Languages

| Language | Schema Throughput | Overhead |
|----------|-------------------|----------|
| **Java** | 3.7M msg/s | 3.0x |
| Go Binary | 2.1M msg/s | 2.5x |
| Go YAML | 1.3M msg/s | 5.2x |
| JS (Node) | 638K msg/s | 35x |
| Python | 184K msg/s | 24x |

Java has the **lowest schema overhead** among high-level languages, thanks to JIT optimization of the interpreter loop after warmup.

## Architecture

```
org.lora.schema/
├── Schema.java           # Main entry point, YAML/binary parsing
├── Field.java            # Field definition with all properties
├── FieldType.java        # Enum of supported field types
├── DecodeContext.java    # Byte buffer and variable state
├── FormulaEvaluator.java # Math expression parser
├── BinarySchemaParser.java # Binary format v2 parser
├── Varint.java           # Variable-length integer encoding
└── SchemaException.java  # Custom exceptions

org.lora.benchmark/
└── Benchmark.java        # Performance benchmark runner
```

## Supported Field Types

| Type | Description | Example |
|------|-------------|---------|
| `u8`, `u16`, `u32` | Unsigned integers | `type: u16` |
| `i8`, `i16`, `i32` | Signed integers | `type: i16` |
| `float32`, `float64` | IEEE 754 floats | `type: float32` |
| `bits` | Bit extraction | `type: u8, bits: [0, 4]` |
| `string` | ASCII/UTF-8 string | `type: string, length: 10` |
| `bytes` | Raw byte array | `type: bytes, length: 4` |
| `tlv` | Tag-Length-Value | `type: tlv, tags: {...}` |
| `match` | Conditional parsing | `type: match, field: type` |
| `repeat` | Array/loop | `type: repeat, count: 3` |
| `object` | Nested structure | `type: object, fields: [...]` |

## Arithmetic Modifiers

```yaml
fields:
  - name: temperature
    type: i16
    div: 10        # Divide by 10
    add: -40       # Add offset
    unit: "°C"
```

## Formula Support

```yaml
fields:
  - name: raw_adc
    type: u16
  - name: voltage
    type: computed
    formula: "$raw_adc * 3.3 / 4096"
```

Supported operations: `+`, `-`, `*`, `/`, `^`, `%`, `pow()`, `abs()`, `sqrt()`, `min()`, `max()`

## Running Benchmarks

```bash
# Build and run benchmark
mvn package -DskipTests
java -jar target/payload-schema-1.0.0.jar
```

Or via Docker (with other language benchmarks):

```bash
cd reference-impl/benchmarks
docker build -t schema-benchmark .
docker run --rm schema-benchmark java
```

## Testing

```bash
mvn test
```

## Dependencies

- [SnakeYAML](https://bitbucket.org/snakeyaml/snakeyaml) 2.2 - YAML parsing
- JUnit 5.10.2 - Testing (test scope only)

## License

MIT License - see repository root for details.
