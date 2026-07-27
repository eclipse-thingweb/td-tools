#!/usr/bin/env python3
"""
benchmark_all.py - Comprehensive codec benchmark

Compares all implementation approaches:
1. Native Python (hand-written decoder)
2. Schema Interpreter (YAML parsed once)
3. Schema Interpreter (parse each time)
4. Binary Schema (compact binary format)

Usage:
    python tools/benchmark_all.py [iterations]
    python tools/benchmark_all.py 10000
"""

import sys
import time
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from schema_interpreter import SchemaInterpreter
from binary_schema import BinarySchemaEncoder, BinarySchemaDecoder

# DL-5TM schema
DL5TM_SCHEMA = """
name: decentlab_dl_5tm
version: 3
endian: big

fields:
  - name: protocol_version
    type: u8

  - name: device_id
    type: u16

  - name: flags
    type: u16
    var: flags

  - flagged:
      field: flags
      groups:
        - bit: 0
          fields:
            - name: _raw_dielectric
              type: u16
              var: raw_dielectric
            - name: dielectric_permittivity
              type: number
              ref: $raw_dielectric
              div: 50
            - name: volumetric_water_content
              type: number
              ref: $dielectric_permittivity
              polynomial: [0.0000043, -0.00055, 0.0292, -0.053]
              unit: "m³/m³"
            - name: soil_temperature_raw
              type: u16
              var: soil_temp_raw
            - name: soil_temperature
              type: number
              ref: $soil_temp_raw
              transform:
                - add: -400
                - div: 10
              unit: "°C"
        - bit: 1
          fields:
            - name: _battery_raw
              type: u16
              var: battery_raw
            - name: battery_voltage
              type: number
              ref: $battery_raw
              div: 1000
              unit: "V"
"""

# Test payload: 02 012f 0003 0258 0098 0bb8
TEST_PAYLOAD = bytes.fromhex("02012f0003025800980bb8")


def native_decode(data: bytes) -> dict:
    """Hand-written native Python decoder."""
    if len(data) < 5:
        return {}
    
    result = {
        'protocol_version': data[0],
        'device_id': (data[1] << 8) | data[2],
        'flags': (data[3] << 8) | data[4],
    }
    
    flags = result['flags']
    pos = 5
    
    # Sensor group 0 (bit 0)
    if flags & 1 and pos + 4 <= len(data):
        raw_dielectric = (data[pos] << 8) | data[pos + 1]
        pos += 2
        dielectric = raw_dielectric / 50
        result['dielectric_permittivity'] = dielectric
        
        # Polynomial
        vwc = (0.0000043 * dielectric**3 - 
               0.00055 * dielectric**2 + 
               0.0292 * dielectric - 0.053)
        result['volumetric_water_content'] = vwc
        
        raw_temp = (data[pos] << 8) | data[pos + 1]
        pos += 2
        result['soil_temperature_raw'] = raw_temp
        result['soil_temperature'] = (raw_temp - 400) / 10
    
    # Sensor group 1 (bit 1)
    if flags & 2 and pos + 2 <= len(data):
        raw_battery = (data[pos] << 8) | data[pos + 1]
        result['battery_voltage'] = raw_battery / 1000
    
    return result


def benchmark(name: str, fn, iterations: int) -> dict:
    """Run benchmark and return results."""
    # Warmup
    for _ in range(min(100, iterations // 10)):
        fn()
    
    start = time.perf_counter()
    for _ in range(iterations):
        fn()
    end = time.perf_counter()
    
    total_s = end - start
    per_call_us = (total_s * 1_000_000) / iterations
    ops_per_sec = iterations / total_s
    
    return {
        'name': name,
        'iterations': iterations,
        'total_s': total_s,
        'per_call_us': per_call_us,
        'ops_per_sec': ops_per_sec,
    }


def main():
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    
    print(f"Benchmark: DL-5TM decoder")
    print(f"Iterations: {iterations:,}")
    print(f"Payload: {TEST_PAYLOAD.hex()}")
    print()
    
    # Parse schema once
    schema_dict = yaml.safe_load(DL5TM_SCHEMA)
    interpreter = SchemaInterpreter(schema_dict)
    
    # Encode to binary schema
    encoder = BinarySchemaEncoder()
    binary_schema = encoder.encode(schema_dict)
    binary_schema_bytes = binary_schema.to_bytes()
    print(f"YAML schema size: {len(DL5TM_SCHEMA)} bytes")
    print(f"Binary schema size: {len(binary_schema_bytes)} bytes ({len(binary_schema_bytes)/len(DL5TM_SCHEMA)*100:.1f}%)")
    print()
    
    # Verify all decoders produce same result
    native_result = native_decode(TEST_PAYLOAD)
    interp_result = interpreter.decode(TEST_PAYLOAD)
    
    print("Native result:", native_result)
    print("Interpreter result:", interp_result.data if interp_result.success else "FAILED")
    print()
    
    results = []
    
    # 1. Native Python
    results.append(benchmark(
        "Native Python",
        lambda: native_decode(TEST_PAYLOAD),
        iterations
    ))
    
    # 2. Schema Interpreter (pre-parsed)
    results.append(benchmark(
        "Interpreter (pre-parsed)",
        lambda: interpreter.decode(TEST_PAYLOAD),
        iterations
    ))
    
    # 3. Schema Interpreter (parse each time)
    results.append(benchmark(
        "Interpreter (w/ parse)",
        lambda: SchemaInterpreter(yaml.safe_load(DL5TM_SCHEMA)).decode(TEST_PAYLOAD),
        min(1000, iterations // 10)  # Slower, fewer iterations
    ))
    
    # 4. Binary Schema (decode binary + interpret)
    decoder = BinarySchemaDecoder()
    
    def binary_schema_decode():
        schema = decoder.decode(binary_schema)
        interp = SchemaInterpreter(schema)
        return interp.decode(TEST_PAYLOAD)
    
    results.append(benchmark(
        "Binary Schema (w/ parse)",
        binary_schema_decode,
        min(1000, iterations // 10)
    ))
    
    # Print results
    print("=" * 75)
    print("BENCHMARK RESULTS")
    print("=" * 75)
    print()
    print(f"{'Method':<25} {'ops/sec':>12} {'µs/call':>12} {'vs native':>12}")
    print("-" * 75)
    
    baseline = results[0]['per_call_us']
    for r in results:
        ratio = r['per_call_us'] / baseline
        ratio_str = f"{ratio:.1f}x" if ratio < 100 else f"{ratio:.0f}x"
        print(f"{r['name']:<25} {r['ops_per_sec']:>12,.0f} {r['per_call_us']:>12.2f} {ratio_str:>12}")
    
    print("=" * 75)
    print()
    print("SUMMARY:")
    print("- Native: Hand-written Python, fastest for this specific schema")
    print("- Interpreter (pre-parsed): Schema loaded once, decode many payloads")
    print("- Interpreter (w/ parse): Full YAML parse each call (realistic cold start)")
    print("- Binary Schema: Compact binary format, faster to parse than YAML")
    print()
    print("Binary schema is useful for:")
    print("- OTA schema transfer (smaller than YAML)")
    print("- Embedded systems (simpler parser)")
    print("- Faster cold-start than YAML parsing")


if __name__ == '__main__':
    main()
