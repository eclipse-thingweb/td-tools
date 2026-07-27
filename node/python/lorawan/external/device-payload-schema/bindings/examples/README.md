# Hot-Swap Schema Examples

Runtime schema replacement without service restart.

## Overview

All examples demonstrate:
1. **Atomic schema replacement** - No partial updates
2. **Thread-safe operation** - Safe concurrent access
3. **Version tracking** - Know which schema is active
4. **Zero downtime** - Update while processing messages

## Quick Reference

### Python

```python
from schema_registry import SchemaRegistry

registry = SchemaRegistry()

# Register schema
registry.register("sensor", binary_schema_v1)

# Decode (uses current schema)
result = registry.decode("sensor", payload)

# Hot-swap to new version (atomic)
registry.register("sensor", binary_schema_v2)

# Next decode uses v2 - no restart needed
result = registry.decode("sensor", payload)
```

### Go

```go
// Method 1: RWMutex registry (multiple schemas)
registry := NewSchemaRegistry()
registry.Register("sensor", schemaV1)
registry.Register("sensor", schemaV2)  // Hot-swap

// Method 2: atomic.Value (single schema, lock-free)
schema := NewAtomicSchema(schemaV1)
schema.Swap(schemaV2)  // Lock-free swap

// Method 3: unsafe.Pointer (maximum performance)
ptr := NewSchemaPointer(schemaV1)
ptr.Swap(schemaV2)  // Zero-copy swap
```

### Node.js

```javascript
const registry = new SchemaRegistry();

// Register and hot-swap
registry.register('sensor', schemaV1);
registry.register('sensor', schemaV2);  // Atomic replace

// Or use AtomicSchema for single schema
const schema = new AtomicSchema(schemaV1);
schema.swap(schemaV2);

// HTTP endpoint for remote updates
createHotSwapServer(registry, 8080);
// PUT /schema/sensor with binary body
```

## Hot-Swap Methods by Language

| Method | Python | Go | Node.js | Thread-Safe | Lock-Free |
|--------|--------|-----|---------|-------------|-----------|
| **Registry + Lock** | `threading.RLock` | `sync.RWMutex` | N/A (single-threaded) | ✅ | ❌ |
| **Atomic Value** | N/A | `atomic.Value` | Object assignment | ✅ | ✅ |
| **Unsafe Pointer** | N/A | `unsafe.Pointer` | N/A | ✅ | ✅ |
| **File Watcher** | `SchemaWatcher` | fsnotify | `fs.watch` | ✅ | ❌ |
| **HTTP Endpoint** | Flask/FastAPI | net/http | http module | ✅ | ❌ |

## Performance Comparison (Go)

```
RWMutex registry:  ~50 ns/decode (lock overhead)
atomic.Value:      ~10 ns/decode (lock-free)
unsafe.Pointer:    ~5 ns/decode  (zero-copy)
```

For high-throughput (>1M msg/s), use atomic or unsafe methods.

## Update Strategies

### 1. File-Based (Development)

```bash
# Update schema file
cp new_schema.bin /schemas/sensor.bin
# Watcher auto-reloads
```

### 2. HTTP API (Production)

```bash
# Push new schema
curl -X PUT http://localhost:8080/schema/sensor \
  --data-binary @new_schema.bin

# Verify
curl http://localhost:8080/schemas
# {"sensor": 2}
```

### 3. Message Queue (Distributed)

```python
# Subscribe to schema updates
def on_schema_update(name, binary_data):
    registry.register(name, binary_data)
    
mqtt.subscribe("schemas/+", on_schema_update)
```

### 4. Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sensor-schemas
data:
  sensor.bin: |
    AQQAAAAAAQAAAAEAAAABAAAA
---
# Pod watches ConfigMap for changes
```

## Error Handling

```python
try:
    registry.register("sensor", invalid_schema)
except SchemaError as e:
    # Old schema still active - no corruption
    print(f"Update failed: {e}")
    # Continue using previous version
```

Key principle: **Parse new schema before replacing old one.**

## Graceful Degradation

```python
class ResilientRegistry:
    def decode(self, name, payload):
        try:
            return self.registry.decode(name, payload)
        except SchemaError:
            # Try previous version
            return self.registry.decode(name, payload, version=-1)
```

## Monitoring

Track these metrics:
- `schema_version{name="sensor"}` - Current version
- `schema_update_total` - Update count
- `schema_update_errors` - Failed updates
- `schema_decode_latency` - Decode time

## Files

| File | Language | Features |
|------|----------|----------|
| `hot_swap.py` | Python | Registry, Watcher, threading |
| `hot_swap.go` | Go | RWMutex, atomic.Value, unsafe.Pointer |
| `hot_swap.js` | Node.js | Registry, Watcher, HTTP server |
