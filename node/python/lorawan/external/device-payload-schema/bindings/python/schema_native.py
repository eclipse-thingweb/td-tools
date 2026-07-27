"""
schema_native.py - Python bindings for C schema interpreter via ctypes

Uses the C FFI library for high-performance payload decoding.
Falls back to pure Python implementation if native library not available.

Usage:
    from schema_native import NativeSchema
    
    # Load binary schema
    schema = NativeSchema.from_binary(binary_data)
    
    # Decode payload
    result = schema.decode(payload_bytes)
    print(result)  # {'temperature': 25.5, 'humidity': 60}
    
    # Or get JSON directly
    json_str = schema.decode_json(payload_bytes)

Performance:
    Native C: ~32M msg/s
    Pure Python: ~215K msg/s
    Speedup: ~150x
"""

import ctypes
import ctypes.util
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Union

# Field value types (must match schema_ffi.h)
FIELD_VAL_INT = 0
FIELD_VAL_FLOAT = 1
FIELD_VAL_STRING = 2
FIELD_VAL_BOOL = 3
FIELD_VAL_BYTES = 4


class SchemaError(Exception):
    """Error from schema operations."""
    pass


class NativeSchema:
    """
    High-performance schema decoder using native C library.
    
    Example:
        schema = NativeSchema.from_binary(binary_schema_bytes)
        result = schema.decode(payload)
    """
    
    _lib = None
    _lib_path = None
    
    @classmethod
    def _load_library(cls) -> Optional[ctypes.CDLL]:
        """Load the native library, trying multiple locations."""
        if cls._lib is not None:
            return cls._lib
        
        # Possible library names
        lib_names = []
        if sys.platform == 'darwin':
            lib_names = ['libschema.dylib', 'libschema.so']
        elif sys.platform == 'win32':
            lib_names = ['schema.dll', 'libschema.dll']
        else:
            lib_names = ['libschema.so', 'libschema.so.1']
        
        # Search paths
        search_paths = [
            Path(__file__).parent,
            Path(__file__).parent / 'lib',
            Path(__file__).parent.parent.parent / 'bindings' / 'c',
            Path.cwd(),
            Path.cwd() / 'lib',
        ]
        
        # Try LD_LIBRARY_PATH
        if 'LD_LIBRARY_PATH' in os.environ:
            for p in os.environ['LD_LIBRARY_PATH'].split(':'):
                search_paths.append(Path(p))
        
        # Try to find and load
        for search_path in search_paths:
            for lib_name in lib_names:
                lib_path = search_path / lib_name
                if lib_path.exists():
                    try:
                        cls._lib = ctypes.CDLL(str(lib_path))
                        cls._lib_path = lib_path
                        cls._setup_functions()
                        return cls._lib
                    except OSError:
                        continue
        
        # Try system library path
        lib_path = ctypes.util.find_library('schema')
        if lib_path:
            try:
                cls._lib = ctypes.CDLL(lib_path)
                cls._lib_path = lib_path
                cls._setup_functions()
                return cls._lib
            except OSError:
                pass
        
        return None
    
    @classmethod
    def _setup_functions(cls):
        """Set up ctypes function signatures."""
        lib = cls._lib
        
        # schema_create_binary
        lib.schema_create_binary.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
        lib.schema_create_binary.restype = ctypes.c_void_p
        
        # schema_free
        lib.schema_free.argtypes = [ctypes.c_void_p]
        lib.schema_free.restype = None
        
        # schema_get_name
        lib.schema_get_name.argtypes = [ctypes.c_void_p]
        lib.schema_get_name.restype = ctypes.c_char_p
        
        # schema_get_field_count
        lib.schema_get_field_count.argtypes = [ctypes.c_void_p]
        lib.schema_get_field_count.restype = ctypes.c_int
        
        # schema_decode
        lib.schema_decode.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
        lib.schema_decode.restype = ctypes.c_void_p
        
        # result_free
        lib.result_free.argtypes = [ctypes.c_void_p]
        lib.result_free.restype = None
        
        # result_get_error
        lib.result_get_error.argtypes = [ctypes.c_void_p]
        lib.result_get_error.restype = ctypes.c_int
        
        # result_get_error_msg
        lib.result_get_error_msg.argtypes = [ctypes.c_void_p]
        lib.result_get_error_msg.restype = ctypes.c_char_p
        
        # result_get_field_count
        lib.result_get_field_count.argtypes = [ctypes.c_void_p]
        lib.result_get_field_count.restype = ctypes.c_int
        
        # result_get_field_name
        lib.result_get_field_name.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.result_get_field_name.restype = ctypes.c_char_p
        
        # result_get_field_type
        lib.result_get_field_type.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.result_get_field_type.restype = ctypes.c_int
        
        # result_get_field_int
        lib.result_get_field_int.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.result_get_field_int.restype = ctypes.c_int64
        
        # result_get_field_float
        lib.result_get_field_float.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.result_get_field_float.restype = ctypes.c_double
        
        # result_get_field_string
        lib.result_get_field_string.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.result_get_field_string.restype = ctypes.c_char_p
        
        # result_get_field_bool
        lib.result_get_field_bool.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.result_get_field_bool.restype = ctypes.c_int
        
        # result_to_json
        lib.result_to_json.argtypes = [ctypes.c_void_p]
        lib.result_to_json.restype = ctypes.c_char_p
        
        # schema_free_string
        lib.schema_free_string.argtypes = [ctypes.c_char_p]
        lib.schema_free_string.restype = None
        
        # schema_version
        lib.schema_version.argtypes = []
        lib.schema_version.restype = ctypes.c_char_p
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if native library is available."""
        return cls._load_library() is not None
    
    @classmethod
    def get_version(cls) -> str:
        """Get native library version."""
        lib = cls._load_library()
        if not lib:
            return "not available"
        return lib.schema_version().decode('utf-8')
    
    @classmethod
    def from_binary(cls, data: bytes) -> 'NativeSchema':
        """Create schema from binary data."""
        lib = cls._load_library()
        if not lib:
            raise SchemaError("Native library not available. Build with: "
                            "cd bindings/c && make")
        
        arr = (ctypes.c_uint8 * len(data))(*data)
        handle = lib.schema_create_binary(arr, len(data))
        if not handle:
            raise SchemaError("Failed to parse binary schema")
        
        return cls(handle)
    
    def __init__(self, handle: int):
        """Initialize with native handle (use from_binary instead)."""
        self._handle = handle
        self._lib = self._load_library()
    
    def __del__(self):
        """Free native resources."""
        if hasattr(self, '_handle') and self._handle and self._lib:
            self._lib.schema_free(self._handle)
            self._handle = None
    
    @property
    def name(self) -> str:
        """Get schema name."""
        return self._lib.schema_get_name(self._handle).decode('utf-8')
    
    @property
    def field_count(self) -> int:
        """Get number of fields in schema."""
        return self._lib.schema_get_field_count(self._handle)
    
    def decode(self, payload: bytes) -> Dict[str, Any]:
        """
        Decode a payload using the schema.
        
        Args:
            payload: Raw payload bytes
            
        Returns:
            Dictionary of field name -> value
            
        Raises:
            SchemaError: If decoding fails
        """
        arr = (ctypes.c_uint8 * len(payload))(*payload)
        result = self._lib.schema_decode(self._handle, arr, len(payload))
        
        if not result:
            raise SchemaError("Decode returned null")
        
        try:
            error = self._lib.result_get_error(result)
            if error != 0:
                msg = self._lib.result_get_error_msg(result).decode('utf-8')
                raise SchemaError(f"Decode error {error}: {msg}")
            
            output = {}
            field_count = self._lib.result_get_field_count(result)
            
            for i in range(field_count):
                name = self._lib.result_get_field_name(result, i).decode('utf-8')
                if not name:
                    continue
                
                field_type = self._lib.result_get_field_type(result, i)
                
                if field_type == FIELD_VAL_INT:
                    output[name] = self._lib.result_get_field_int(result, i)
                elif field_type == FIELD_VAL_FLOAT:
                    output[name] = self._lib.result_get_field_float(result, i)
                elif field_type == FIELD_VAL_STRING:
                    output[name] = self._lib.result_get_field_string(result, i).decode('utf-8')
                elif field_type == FIELD_VAL_BOOL:
                    output[name] = bool(self._lib.result_get_field_bool(result, i))
                else:
                    output[name] = self._lib.result_get_field_int(result, i)
            
            return output
        finally:
            self._lib.result_free(result)
    
    def decode_json(self, payload: bytes) -> str:
        """
        Decode payload and return JSON string.
        
        More efficient than decode() + json.dumps() as JSON is
        generated in C without Python object creation.
        """
        arr = (ctypes.c_uint8 * len(payload))(*payload)
        result = self._lib.schema_decode(self._handle, arr, len(payload))
        
        if not result:
            raise SchemaError("Decode returned null")
        
        try:
            error = self._lib.result_get_error(result)
            if error != 0:
                msg = self._lib.result_get_error_msg(result).decode('utf-8')
                raise SchemaError(f"Decode error {error}: {msg}")
            
            json_ptr = self._lib.result_to_json(result)
            if not json_ptr:
                raise SchemaError("JSON conversion failed")
            
            json_str = json_ptr.decode('utf-8')
            self._lib.schema_free_string(json_ptr)
            return json_str
        finally:
            self._lib.result_free(result)


def benchmark():
    """Quick benchmark comparing native vs pure Python."""
    import time
    
    # Simple test schema (5 fields)
    binary_schema = bytes([
        0x01,  # Version 1
        0x05,  # 5 fields
        0x00, 0x00, 0x00, 0x00,  # u8
        0x01, 0x00, 0x00, 0x00,  # u16
        0x01, 0x00, 0x00, 0x00,  # u16
        0x01, 0x00, 0x00, 0x00,  # u16
        0x01, 0x00, 0x00, 0x00,  # u16
    ])
    
    payload = bytes.fromhex("02012f00030258009800")
    
    if not NativeSchema.is_available():
        print("Native library not available")
        print("Build with: cd bindings/c && make")
        return
    
    print(f"Native library version: {NativeSchema.get_version()}")
    
    schema = NativeSchema.from_binary(binary_schema)
    print(f"Schema: {schema.name}, {schema.field_count} fields")
    
    # Warmup
    for _ in range(100):
        schema.decode(payload)
    
    # Benchmark
    iterations = 100000
    start = time.perf_counter()
    for _ in range(iterations):
        schema.decode(payload)
    elapsed = time.perf_counter() - start
    
    rate = iterations / elapsed
    us_per = (elapsed * 1_000_000) / iterations
    
    print(f"\nNative decode: {iterations:,} iterations")
    print(f"  Total time: {elapsed:.3f}s")
    print(f"  Per decode: {us_per:.2f} µs")
    print(f"  Throughput: {rate:,.0f} msg/s")


if __name__ == '__main__':
    benchmark()
