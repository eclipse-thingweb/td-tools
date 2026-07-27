# @lorawan-schema/native

Native Node.js bindings for the LoRaWAN payload schema interpreter.

Uses N-API to call the high-performance C implementation directly, providing ~20-30M msg/s decode throughput.

## Installation

```bash
npm install
npm run build
```

### Requirements

- Node.js 14+
- C++ compiler (gcc, clang, or MSVC)
- node-gyp dependencies:
  - **Linux:** `build-essential`
  - **macOS:** Xcode Command Line Tools
  - **Windows:** Visual Studio Build Tools

## Usage

```javascript
const { NativeSchema, fromBinary } = require('@lorawan-schema/native');

// Load binary schema
const binarySchema = Buffer.from([
    0x01, 0x05,  // version, field count
    // ... field definitions
]);

const schema = new NativeSchema(binarySchema);

// Decode payload
const payload = Buffer.from('02012f0003', 'hex');
const result = schema.decode(payload);
console.log(result);
// { field_0: 2, field_1: 303, field_2: 3 }

// Or get JSON directly (more efficient for serialization)
const json = schema.decodeJSON(payload);
console.log(json);
// '{"field_0":2,"field_1":303,"field_2":3}'
```

## API

### `new NativeSchema(binarySchema)`

Create a schema from binary data.

- `binarySchema` {Buffer} - Binary schema data
- Returns: NativeSchema instance
- Throws: Error if parsing fails

### `schema.decode(payload)`

Decode a payload using the schema.

- `payload` {Buffer} - Raw payload bytes
- Returns: {Object} - Decoded field values
- Throws: Error if decoding fails

### `schema.decodeJSON(payload)`

Decode and return JSON string directly (more efficient than `JSON.stringify(decode())`).

- `payload` {Buffer} - Raw payload bytes
- Returns: {string} - JSON string
- Throws: Error if decoding fails

### `schema.name`

Schema name (string, read-only).

### `schema.fieldCount`

Number of fields in schema (number, read-only).

### `version()`

Get native library version string.

### `isAvailable()`

Check if native module is loaded (boolean).

## Performance

```
Benchmark: Native vs Pure JavaScript

Pure JavaScript:          45,000,000 msg/s  (hand-written decoder)
Native decode():          25,000,000 msg/s  (schema interpreter)
Native decodeJSON():      28,000,000 msg/s  (direct JSON output)
```

The native bindings are slightly slower than hand-written JavaScript for simple payloads due to N-API crossing overhead. However, they provide:

1. **Security** - No eval/exec, pure data-driven decoding
2. **Consistency** - Same decoder as C/Go/Python implementations
3. **Complex schemas** - Better performance for TLV, flagged, nested structures

## Testing

```bash
npm test
```

## Benchmarking

```bash
npm run benchmark
```

## Troubleshooting

### Build fails with "node-gyp not found"

```bash
npm install -g node-gyp
```

### Build fails on Linux

```bash
sudo apt install build-essential
```

### Build fails on macOS

```bash
xcode-select --install
```

### Build fails on Windows

Install Visual Studio Build Tools with C++ workload.

## License

MIT
