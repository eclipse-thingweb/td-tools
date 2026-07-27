// hot_swap.go - Hot-swap schema example for Go
//
// Demonstrates runtime schema replacement without restart.
// Uses sync.RWMutex for concurrent read access during updates.
//
// Build: CGO_ENABLED=1 go build hot_swap.go
// Run:   ./hot_swap

package main

import (
	"fmt"
	"sync"
	"sync/atomic"
	"time"
	"unsafe"
)

// For demo purposes - in real code, import the actual bindings
// import schema_native "github.com/your-org/payload-codec/bindings/go"

// Mock schema for demo
type Schema struct {
	name       string
	fieldCount int
}

func (s *Schema) Decode(payload []byte) (map[string]interface{}, error) {
	return map[string]interface{}{"field_0": int(payload[0])}, nil
}

func FromBinary(data []byte) (*Schema, error) {
	return &Schema{fieldCount: int(data[1])}, nil
}

// SchemaRegistry provides thread-safe schema management with hot-swap.
type SchemaRegistry struct {
	mu       sync.RWMutex
	schemas  map[string]*Schema
	versions map[string]uint64
}

// NewSchemaRegistry creates a new registry.
func NewSchemaRegistry() *SchemaRegistry {
	return &SchemaRegistry{
		schemas:  make(map[string]*Schema),
		versions: make(map[string]uint64),
	}
}

// Register adds or updates a schema. Thread-safe, atomic swap.
func (r *SchemaRegistry) Register(name string, binarySchema []byte) (uint64, error) {
	// Parse new schema BEFORE acquiring write lock
	newSchema, err := FromBinary(binarySchema)
	if err != nil {
		return 0, fmt.Errorf("failed to parse schema: %w", err)
	}

	r.mu.Lock()
	defer r.mu.Unlock()

	// Atomic replacement
	r.schemas[name] = newSchema
	r.versions[name]++
	return r.versions[name], nil
}

// Get retrieves a schema by name. Thread-safe for concurrent reads.
func (r *SchemaRegistry) Get(name string) *Schema {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.schemas[name]
}

// Decode decodes payload using named schema.
// Thread-safe: schema can be hot-swapped during this call.
func (r *SchemaRegistry) Decode(name string, payload []byte) (map[string]interface{}, error) {
	schema := r.Get(name)
	if schema == nil {
		return nil, fmt.Errorf("schema '%s' not found", name)
	}
	return schema.Decode(payload)
}

// GetVersion returns current version of a schema.
func (r *SchemaRegistry) GetVersion(name string) uint64 {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.versions[name]
}

// AtomicSchema provides lock-free hot-swap using atomic.Value.
// Better for high-throughput scenarios where RWMutex contention is a concern.
type AtomicSchema struct {
	schema  atomic.Value // *Schema
	version uint64
}

// NewAtomicSchema creates a new atomic schema holder.
func NewAtomicSchema(binarySchema []byte) (*AtomicSchema, error) {
	schema, err := FromBinary(binarySchema)
	if err != nil {
		return nil, err
	}
	as := &AtomicSchema{version: 1}
	as.schema.Store(schema)
	return as, nil
}

// Swap atomically replaces the schema. Lock-free, wait-free.
func (as *AtomicSchema) Swap(binarySchema []byte) error {
	newSchema, err := FromBinary(binarySchema)
	if err != nil {
		return err
	}
	as.schema.Store(newSchema)
	atomic.AddUint64(&as.version, 1)
	return nil
}

// Decode decodes using current schema. Lock-free read.
func (as *AtomicSchema) Decode(payload []byte) (map[string]interface{}, error) {
	schema := as.schema.Load().(*Schema)
	return schema.Decode(payload)
}

// Version returns current version.
func (as *AtomicSchema) Version() uint64 {
	return atomic.LoadUint64(&as.version)
}

// SchemaPointer uses unsafe.Pointer for zero-copy hot-swap.
// Maximum performance but requires careful memory management.
type SchemaPointer struct {
	ptr     unsafe.Pointer // *Schema
	version uint64
}

// NewSchemaPointer creates a new pointer-based schema holder.
func NewSchemaPointer(binarySchema []byte) (*SchemaPointer, error) {
	schema, err := FromBinary(binarySchema)
	if err != nil {
		return nil, err
	}
	sp := &SchemaPointer{version: 1}
	atomic.StorePointer(&sp.ptr, unsafe.Pointer(schema))
	return sp, nil
}

// Swap atomically replaces schema pointer.
func (sp *SchemaPointer) Swap(binarySchema []byte) error {
	newSchema, err := FromBinary(binarySchema)
	if err != nil {
		return err
	}
	atomic.StorePointer(&sp.ptr, unsafe.Pointer(newSchema))
	atomic.AddUint64(&sp.version, 1)
	return nil
}

// Decode decodes using current schema.
func (sp *SchemaPointer) Decode(payload []byte) (map[string]interface{}, error) {
	schema := (*Schema)(atomic.LoadPointer(&sp.ptr))
	return schema.Decode(payload)
}

func main() {
	fmt.Println("=== Go Hot-Swap Schema Example ===\n")

	// Method 1: RWMutex-based registry (simple, multiple schemas)
	fmt.Println("Method 1: SchemaRegistry (RWMutex)")
	registry := NewSchemaRegistry()

	schemaV1 := []byte{0x01, 0x03, 0x00, 0x00, 0x00, 0x00}
	v, _ := registry.Register("sensor", schemaV1)
	fmt.Printf("  Registered 'sensor' v%d\n", v)

	result, _ := registry.Decode("sensor", []byte{0x02, 0x01, 0x2f})
	fmt.Printf("  Decoded: %v\n", result)

	schemaV2 := []byte{0x01, 0x04, 0x00, 0x00, 0x00, 0x00}
	v, _ = registry.Register("sensor", schemaV2)
	fmt.Printf("  Hot-swapped to v%d\n", v)

	// Method 2: atomic.Value (lock-free, single schema)
	fmt.Println("\nMethod 2: AtomicSchema (lock-free)")
	atomic, _ := NewAtomicSchema(schemaV1)
	fmt.Printf("  Created atomic schema v%d\n", atomic.Version())

	atomic.Swap(schemaV2)
	fmt.Printf("  Swapped to v%d (lock-free)\n", atomic.Version())

	// Method 3: unsafe.Pointer (maximum performance)
	fmt.Println("\nMethod 3: SchemaPointer (unsafe, max perf)")
	ptr, _ := NewSchemaPointer(schemaV1)
	fmt.Printf("  Created pointer schema\n")

	ptr.Swap(schemaV2)
	fmt.Printf("  Swapped (zero-copy)\n")

	// Benchmark comparison
	fmt.Println("\n=== Performance Comparison ===")
	payload := []byte{0x02}
	iterations := 1000000

	// RWMutex
	start := time.Now()
	for i := 0; i < iterations; i++ {
		registry.Decode("sensor", payload)
	}
	rwDuration := time.Since(start)

	// Atomic
	start = time.Now()
	for i := 0; i < iterations; i++ {
		atomic.Decode(payload)
	}
	atomicDuration := time.Since(start)

	fmt.Printf("  RWMutex:  %v (%d ns/op)\n", rwDuration, rwDuration.Nanoseconds()/int64(iterations))
	fmt.Printf("  Atomic:   %v (%d ns/op)\n", atomicDuration, atomicDuration.Nanoseconds()/int64(iterations))
	fmt.Printf("  Speedup:  %.1fx\n", float64(rwDuration)/float64(atomicDuration))

	fmt.Println("\nHot-swap complete - no restart required!")
}
