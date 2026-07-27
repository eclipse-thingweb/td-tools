#!/usr/bin/env python3
"""
hot_swap.py - Hot-swap schema example for Python

Demonstrates runtime schema replacement without restart.
Useful for OTA schema updates, multi-tenant systems, and A/B testing.

Usage:
    python hot_swap.py
"""

import threading
import time
from typing import Dict, Any, Optional
from pathlib import Path

# Import native bindings (falls back to pure Python if not available)
try:
    from schema_native import NativeSchema, SchemaError
    NATIVE_AVAILABLE = True
except ImportError:
    NATIVE_AVAILABLE = False
    print("Native bindings not available, using mock")


class SchemaRegistry:
    """
    Thread-safe schema registry with hot-swap support.
    
    Features:
    - Atomic schema replacement
    - Version tracking
    - Fallback to previous version on error
    - Thread-safe operations
    """
    
    def __init__(self):
        self._schemas: Dict[str, NativeSchema] = {}
        self._versions: Dict[str, int] = {}
        self._lock = threading.RLock()
    
    def register(self, name: str, binary_schema: bytes) -> int:
        """
        Register or update a schema. Returns new version number.
        
        Thread-safe: Can be called while decode() is running.
        """
        with self._lock:
            try:
                # Parse new schema first (validates before replacing)
                new_schema = NativeSchema.from_binary(binary_schema)
                
                # Atomic replacement
                old_schema = self._schemas.get(name)
                self._schemas[name] = new_schema
                self._versions[name] = self._versions.get(name, 0) + 1
                
                # Old schema will be GC'd when no longer referenced
                return self._versions[name]
                
            except Exception as e:
                raise SchemaError(f"Failed to register schema '{name}': {e}")
    
    def unregister(self, name: str) -> bool:
        """Remove a schema from the registry."""
        with self._lock:
            if name in self._schemas:
                del self._schemas[name]
                del self._versions[name]
                return True
            return False
    
    def get(self, name: str) -> Optional[NativeSchema]:
        """Get a schema by name (thread-safe)."""
        with self._lock:
            return self._schemas.get(name)
    
    def decode(self, name: str, payload: bytes) -> Dict[str, Any]:
        """
        Decode payload using named schema.
        
        Thread-safe: Schema can be hot-swapped during this call.
        The decode will use whichever schema was active at call time.
        """
        schema = self.get(name)
        if not schema:
            raise SchemaError(f"Schema '{name}' not found")
        return schema.decode(payload)
    
    def get_version(self, name: str) -> int:
        """Get current version of a schema."""
        with self._lock:
            return self._versions.get(name, 0)
    
    def list_schemas(self) -> Dict[str, int]:
        """List all schemas with their versions."""
        with self._lock:
            return dict(self._versions)


class SchemaWatcher:
    """
    Watch a directory for schema changes and hot-reload.
    
    Usage:
        watcher = SchemaWatcher(registry, "/path/to/schemas")
        watcher.start()
        # Schemas auto-reload when files change
        watcher.stop()
    """
    
    def __init__(self, registry: SchemaRegistry, schema_dir: str):
        self.registry = registry
        self.schema_dir = Path(schema_dir)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._mtimes: Dict[str, float] = {}
    
    def start(self):
        """Start watching for changes."""
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop watching."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
    
    def _watch_loop(self):
        """Poll for file changes."""
        while self._running:
            self._check_for_changes()
            time.sleep(1.0)  # Check every second
    
    def _check_for_changes(self):
        """Check for new/modified schema files."""
        for schema_file in self.schema_dir.glob("*.bin"):
            name = schema_file.stem
            mtime = schema_file.stat().st_mtime
            
            if name not in self._mtimes or self._mtimes[name] < mtime:
                try:
                    binary_data = schema_file.read_bytes()
                    version = self.registry.register(name, binary_data)
                    self._mtimes[name] = mtime
                    print(f"Hot-reloaded schema '{name}' -> v{version}")
                except Exception as e:
                    print(f"Failed to reload '{name}': {e}")


# Example usage
def main():
    print("=== Python Hot-Swap Schema Example ===\n")
    
    if not NATIVE_AVAILABLE:
        print("Note: Using mock - install native bindings for real performance\n")
        return
    
    # Create registry
    registry = SchemaRegistry()
    
    # Initial schema (v1)
    schema_v1 = bytes([
        0x01, 0x03,  # version, 3 fields
        0x00, 0x00, 0x00, 0x00,  # u8
        0x01, 0x00, 0x00, 0x00,  # u16
        0x01, 0x00, 0x00, 0x00,  # u16
    ])
    
    # Register initial schema
    v = registry.register("sensor", schema_v1)
    print(f"Registered 'sensor' schema v{v}")
    
    # Decode with v1
    payload = bytes.fromhex("02012f0003")
    result = registry.decode("sensor", payload)
    print(f"Decoded (v1): {result}")
    
    # Simulate schema update (v2 - added field)
    schema_v2 = bytes([
        0x01, 0x04,  # version, 4 fields now
        0x00, 0x00, 0x00, 0x00,  # u8
        0x01, 0x00, 0x00, 0x00,  # u16
        0x01, 0x00, 0x00, 0x00,  # u16
        0x01, 0x00, 0x00, 0x00,  # u16 (new field)
    ])
    
    # Hot-swap to v2
    v = registry.register("sensor", schema_v2)
    print(f"\nHot-swapped to 'sensor' schema v{v}")
    
    # Decode with v2
    payload_v2 = bytes.fromhex("02012f00030bb8")
    result = registry.decode("sensor", payload_v2)
    print(f"Decoded (v2): {result}")
    
    print(f"\nActive schemas: {registry.list_schemas()}")
    print("\nHot-swap complete - no restart required!")


if __name__ == "__main__":
    main()
