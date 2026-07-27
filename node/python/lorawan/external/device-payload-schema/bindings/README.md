# Language Bindings for Schema Decoder

High-performance bindings for the schema decoder in multiple languages: Java, Go, Python, Node.js, and C FFI.

## Two Approaches

### 1. Interpreted (Runtime Schema)
Load schema at runtime, decode with interpreter. Flexible but slower.

### 2. Precompiled (Generated Code)
Generate optimized C from schema at build time. Faster but schema baked in.

## Performance Comparison

| Implementation | Throughput | Use Case |
|----------------|------------|----------|
| **C Precompiled** | 259M msg/s | Max performance, fixed schema |
| **C Interpreted** | 33M msg/s | Runtime schema flexibility |
| **Go + CGO (precompiled)** | ~180M msg/s | Go backend, fixed schema |
| **Go + CGO (interpreted)** | ~30M msg/s | Go backend, runtime schema |
| **Node + N-API** | ~25M msg/s | Node.js backend |
| **Python + ctypes** | ~25M msg/s | Python backend |
| **Java Schema (YAML)** | 3.7M msg/s | Pure Java, lowest overhead |
| **Go Binary Schema** | 2.1M msg/s | Pure Go, no CGO |
| **Go YAML Schema** | 1.3M msg/s | Pure Go, YAML |
| **JS Schema (Node)** | 638K msg/s | Pure Node.js |
| **Pure Python** | 184K msg/s | Development |

**Precompiled is 6x faster** than interpreted because:
- No schema parsing at runtime
- Direct struct field access
- Compiler optimizations (inlining, SIMD)

## Quick Start

### Option A: Interpreted (Runtime Schema)

#### 1. Build the Shared Library

```bash
cd bindings/c
make
```

This produces:
- Linux: `libschema.so`
- macOS: `libschema.dylib`
- Windows: `schema.dll`

### Option B: Precompiled (Maximum Performance)

#### 1. Generate C Code from Schema

```bash
python bindings/tools/generate_native_codec.py schemas/mydevice.yaml -o mydevice_codec.h
```

#### 2. Include in Your Application

```c
#include "schema_precompiled.h"
#include "mydevice_codec.h"

// Direct decode - 200M msg/s
mydevice_t result;
int bytes = decode_mydevice(payload, len, &result);
printf("Temperature: %d\n", result.temperature);
```

#### 3. Or Use with FFI Registry

```c
// Register at startup
register_mydevice_codec();

// Decode via FFI (for language bindings)
codec_entry_t* codec = codec_find("mydevice");
mydevice_t decoded;
codec->decode(payload, len, &decoded);

// Convert to field array for FFI
codec_result_t result;
codec->to_fields(&decoded, &result);
```

### 2. Use from Java

```bash
cd bindings/java
mvn package
```

```java
import org.lora.schema.Schema;
import java.util.Map;

// Load schema from YAML
Schema schema = Schema.fromYamlFile("schemas/devices/milesight/em310-udl.yaml");

// Decode payload
byte[] payload = new byte[] { 0x01, 0x75, 0x64 };
Map<String, Object> result = schema.decode(payload);
// result: {battery: 100}
```

Java provides the **best pure-language performance** at 3.7M msg/s with only 3x overhead vs hand-coded decoders.

### 3. Use from Python

```python
from bindings.python.schema_native import NativeSchema

# Load binary schema
schema = NativeSchema.from_binary(binary_schema_bytes)

# Decode payload
result = schema.decode(payload)
print(result)  # {'temperature': 25.5, 'humidity': 60}

# Or get JSON directly (faster, no Python object creation)
json_str = schema.decode_json(payload)
```

### 4. Use from Go

```go
import "github.com/your-org/payload-codec/bindings/go/schema_native"

// Load binary schema
schema, err := schema_native.FromBinary(binaryData)
if err != nil {
    log.Fatal(err)
}
defer schema.Free()

// Decode payload
result, err := schema.Decode(payload)
// result is map[string]interface{}
```

Build with CGO enabled:

```bash
CGO_ENABLED=1 go build
```

### 5. Use from Node.js

```bash
cd bindings/node
npm install && npm run build
```

```javascript
const { NativeSchema } = require('@lorawan-schema/native');

const schema = new NativeSchema(binarySchemaBuffer);
const result = schema.decode(payloadBuffer);
console.log(result);  // ~25M msg/s

// Or JSON directly
const json = schema.decodeJSON(payloadBuffer);
```

## Directory Structure

```
bindings/
├── README.md                 # This file
├── c/
│   ├── schema_ffi.h          # FFI header for interpreted
│   ├── schema_ffi.c          # FFI implementation
│   ├── schema_precompiled.h  # FFI header for precompiled
│   └── Makefile              # Build shared library
├── java/
│   ├── pom.xml               # Maven build config
│   ├── src/main/java/org/lora/schema/
│   │   ├── Schema.java       # Main interpreter
│   │   ├── Field.java        # Field definitions
│   │   ├── DecodeContext.java # Decode state
│   │   ├── FormulaEvaluator.java # Math parser
│   │   └── BinarySchemaParser.java # Binary format
│   └── README.md             # Java documentation
├── tools/
│   └── generate_native_codec.py  # Generate precompiled codec
├── python/
│   └── schema_native.py      # Python ctypes bindings
├── go/
│   └── schema_native.go      # Go CGO bindings
└── node/
    ├── package.json          # npm package config
    ├── binding.gyp           # node-gyp build config
    ├── index.js              # JavaScript wrapper
    ├── src/
    │   └── schema_native.cc  # N-API C++ addon
    ├── test.js               # Quick test
    ├── benchmark.js          # Performance benchmark
    └── README.md             # Node.js documentation
```

## When to Use Which Approach

| Scenario | Approach | Why |
|----------|----------|-----|
| **Fixed schema, max perf** | Precompiled | 200M msg/s, schema at compile time |
| **Multiple schemas** | Interpreted | Load any schema at runtime |
| **OTA schema updates** | Interpreted | Schema can change without rebuild |
| **Embedded, tight loop** | Precompiled | Smallest code, fastest decode |
| **Cloud LNS** | Interpreted | Flexibility, 32M msg/s is enough |
| **Development** | Interpreted | Easy iteration, no recompile |

---

## For Extreme Eyes Only: Hot-Swap Schemas

Runtime schema replacement without service restart. See `examples/` for full code.

### Quick Reference

**Python:**
```python
registry = SchemaRegistry()  # threading.RLock
registry.register("sensor", schema_v1)
registry.register("sensor", schema_v2)  # Atomic hot-swap
result = registry.decode("sensor", payload)  # Uses v2
```

**Go (3 methods):**
```go
// 1. RWMutex - simple, multiple schemas
registry.Register("sensor", schemaV2)

// 2. atomic.Value - lock-free, 5x faster
atomic := NewAtomicSchema(schemaV1)
atomic.Swap(schemaV2)

// 3. unsafe.Pointer - maximum performance
ptr := NewSchemaPointer(schemaV1)
ptr.Swap(schemaV2)  // Zero-copy
```

**Node.js:**
```javascript
registry.register('sensor', schemaV2);  // Atomic (single-threaded)

// HTTP API for remote updates
createHotSwapServer(registry, 8080);
// curl -X PUT http://localhost:8080/schema/sensor --data-binary @schema.bin
```

### Performance

| Method | Overhead | Lock-Free |
|--------|----------|-----------|
| RWMutex (Go) | ~50 ns | No |
| atomic.Value (Go) | ~10 ns | Yes |
| unsafe.Pointer (Go) | ~5 ns | Yes |
| threading.RLock (Python) | ~100 ns | No |
| Object assign (Node.js) | ~1 ns | Yes (single-threaded) |

### Update Strategies

| Strategy | Command |
|----------|---------|
| **File watcher** | `cp new.bin /schemas/sensor.bin` |
| **HTTP API** | `curl -X PUT .../schema/sensor --data-binary @new.bin` |
| **MQTT** | Publish to `schemas/sensor` topic |
| **K8s ConfigMap** | Update ConfigMap, pod watches |

### Safety

```python
try:
    registry.register("sensor", new_schema)  # Parse first
except SchemaError:
    pass  # Old schema still active - no corruption
```

Key principle: **Parse before swap** - failures leave old schema active.

## API Reference

### C FFI API

```c
// Create schema from binary data
schema_t_ffi schema_create_binary(const uint8_t* data, size_t len);

// Free schema
void schema_free(schema_t_ffi schema);

// Decode payload
result_t_ffi schema_decode(schema_t_ffi schema, const uint8_t* payload, size_t len);

// Get decoded field values
int result_get_field_count(result_t_ffi result);
const char* result_get_field_name(result_t_ffi result, int index);
int64_t result_get_field_int(result_t_ffi result, int index);
double result_get_field_float(result_t_ffi result, int index);

// Convert result to JSON
char* result_to_json(result_t_ffi result);
void schema_free_string(char* str);
```

### Python API

```python
class NativeSchema:
    @classmethod
    def from_binary(cls, data: bytes) -> 'NativeSchema'
    
    def decode(self, payload: bytes) -> Dict[str, Any]
    def decode_json(self, payload: bytes) -> str
    
    @property
    def name(self) -> str
    
    @property
    def field_count(self) -> int
```

### Go API

```go
func FromBinary(data []byte) (*Schema, error)
func (s *Schema) Decode(payload []byte) (map[string]interface{}, error)
func (s *Schema) DecodeJSON(payload []byte) (string, error)
func (s *Schema) Free()
func Version() string
```

## When to Use Which Binding

| Scenario | Recommendation |
|----------|----------------|
| **High-throughput LNS** | Use C/CGO for 33M msg/s |
| **JVM backend** | Java schema (3.7M msg/s) - best pure-language perf |
| **Cloud platform (Go)** | Go binary schema (2.1M msg/s) usually sufficient |
| **Cloud platform (Node)** | JS schema (638K msg/s) or N-API bindings |
| **Python hot path** | Native bindings for 100x speedup |
| **Development** | Pure implementations for easier debugging |

## Security

Native bindings maintain the security properties of declarative schemas:

- **No eval/exec** - Schema is data, not code
- **Memory bounded** - Fixed allocation limits in C
- **Validated input** - Binary schema format is checked before use

## Building for Different Platforms

### Linux (x86_64)

```bash
cd bindings/c
make linux
```

### macOS (arm64/x86_64)

```bash
cd bindings/c
make macos
```

### Windows (cross-compile from Linux)

```bash
# Install mingw
sudo apt install mingw-w64

cd bindings/c
make windows
```

### Static Linking

For embedded use without shared library dependencies:

```bash
cd bindings/c
make libschema.a
```

Then link with `-lschema` or include the `.a` file directly.

## Benchmarking

### Python

```bash
cd bindings/python
python schema_native.py
```

### Go

```bash
cd bindings/go
CGO_ENABLED=1 go test -bench=.
```

## Troubleshooting

### Library not found

```bash
# Linux: Add to library path
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/path/to/bindings/c

# Or install system-wide
sudo cp libschema.so /usr/local/lib/
sudo ldconfig
```

### CGO disabled

```bash
# Enable CGO for Go builds
CGO_ENABLED=1 go build
```

### Symbol not found

Ensure you're using the correct library version. Check with:

```bash
nm -D libschema.so | grep schema_version
```
