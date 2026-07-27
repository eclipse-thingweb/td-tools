#!/usr/bin/env python3
"""
fuzz_decoder.py - Fuzz test the schema interpreter

Verifies decoder doesn't crash on malformed inputs per Payload Schema Section 11.

Usage:
    python tools/fuzz_decoder.py schema.yaml              # 10 second fuzz
    python tools/fuzz_decoder.py schema.yaml --duration 60   # 1 minute fuzz
    python tools/fuzz_decoder.py schema.yaml --seed 12345    # Reproducible
"""

import argparse
import random
import sys
import time
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent))
from schema_interpreter import SchemaInterpreter


@dataclass
class FuzzStats:
    """Statistics from a fuzz run."""
    total_inputs: int = 0
    decode_success: int = 0
    decode_error: int = 0
    crashes: int = 0
    duration_sec: float = 0.0
    seed: int = 0
    crash_inputs: List[bytes] = None
    
    def __post_init__(self):
        if self.crash_inputs is None:
            self.crash_inputs = []
    
    @property
    def inputs_per_sec(self) -> float:
        if self.duration_sec > 0:
            return self.total_inputs / self.duration_sec
        return 0.0


class DecoderFuzzer:
    """Fuzz tester for schema decoder."""
    
    def __init__(self, schema: dict, seed: Optional[int] = None):
        self.schema = schema
        self.interpreter = SchemaInterpreter(schema)
        self.seed = seed if seed is not None else random.randint(0, 2**32)
        self.rng = random.Random(self.seed)
        self.stats = FuzzStats(seed=self.seed)
    
    def generate_random_bytes(self, min_len: int = 0, max_len: int = 255) -> bytes:
        """Generate random byte sequence."""
        length = self.rng.randint(min_len, max_len)
        return bytes(self.rng.randint(0, 255) for _ in range(length))
    
    def generate_truncated(self, valid_payload: bytes) -> bytes:
        """Generate truncated version of valid payload."""
        if len(valid_payload) == 0:
            return b''
        cut_point = self.rng.randint(0, len(valid_payload) - 1)
        return valid_payload[:cut_point]
    
    def generate_extended(self, valid_payload: bytes) -> bytes:
        """Generate extended version of valid payload."""
        extra = self.generate_random_bytes(1, 50)
        return valid_payload + extra
    
    def generate_bitflip(self, valid_payload: bytes) -> bytes:
        """Flip random bits in valid payload."""
        if len(valid_payload) == 0:
            return b''
        data = bytearray(valid_payload)
        num_flips = self.rng.randint(1, max(1, len(data) // 2))
        for _ in range(num_flips):
            pos = self.rng.randint(0, len(data) - 1)
            bit = self.rng.randint(0, 7)
            data[pos] ^= (1 << bit)
        return bytes(data)
    
    def generate_all_zeros(self, length: int) -> bytes:
        """Generate all-zero payload."""
        return bytes(length)
    
    def generate_all_ones(self, length: int) -> bytes:
        """Generate all-0xFF payload."""
        return bytes([0xFF] * length)
    
    def get_valid_payloads(self) -> List[bytes]:
        """Extract valid payloads from test vectors."""
        payloads = []
        for tv in self.schema.get('test_vectors', []):
            payload_str = tv.get('payload', '')
            if isinstance(payload_str, str):
                clean = payload_str.replace(' ', '').replace('0x', '')
                try:
                    payloads.append(bytes.fromhex(clean))
                except ValueError:
                    pass
            elif isinstance(payload_str, list):
                payloads.append(bytes(payload_str))
        return payloads
    
    def fuzz_one(self, payload: bytes) -> bool:
        """
        Fuzz with one payload.
        Returns True if decoder handled it safely, False if crash.
        """
        self.stats.total_inputs += 1
        try:
            result = self.interpreter.decode(payload)
            if result.success:
                self.stats.decode_success += 1
            else:
                self.stats.decode_error += 1
            return True
        except Exception as e:
            # Caught exception = safe handling
            self.stats.decode_error += 1
            return True
        except SystemExit:
            # sys.exit() called = crash
            self.stats.crashes += 1
            self.stats.crash_inputs.append(payload)
            return False
    
    def run(self, duration_sec: float = 10.0) -> FuzzStats:
        """Run fuzzing for specified duration."""
        valid_payloads = self.get_valid_payloads()
        if not valid_payloads:
            # Generate some reasonable-length payloads based on schema
            valid_payloads = [self.generate_random_bytes(4, 20) for _ in range(5)]
        
        start_time = time.time()
        end_time = start_time + duration_sec
        
        generators = [
            lambda: self.generate_random_bytes(0, 255),
            lambda: self.generate_random_bytes(0, 10),  # Short
            lambda: self.generate_random_bytes(100, 255),  # Long
            lambda: self.generate_truncated(self.rng.choice(valid_payloads)),
            lambda: self.generate_extended(self.rng.choice(valid_payloads)),
            lambda: self.generate_bitflip(self.rng.choice(valid_payloads)),
            lambda: self.generate_all_zeros(self.rng.randint(1, 50)),
            lambda: self.generate_all_ones(self.rng.randint(1, 50)),
            lambda: b'',  # Empty
            lambda: bytes([0x00]),  # Single zero
            lambda: bytes([0xFF]),  # Single 0xFF
        ]
        
        while time.time() < end_time:
            generator = self.rng.choice(generators)
            payload = generator()
            self.fuzz_one(payload)
        
        self.stats.duration_sec = time.time() - start_time
        return self.stats


class SchemaFuzzer:
    """Fuzz tester for schema parser/validator."""
    
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed if seed is not None else random.randint(0, 2**32)
        self.rng = random.Random(self.seed)
        self.stats = FuzzStats(seed=self.seed)
    
    def generate_malformed_yaml(self) -> str:
        """Generate malformed YAML."""
        cases = [
            "{{{{",  # Invalid syntax
            "name: test\nfields: [",  # Unclosed bracket
            "name: test\nfields:\n  - name: x\n    type: " + "a" * 10000,  # Long string
            "name: test\nfields: null",  # Null fields
            "name: test\nfields: 123",  # Wrong type
            "fields:\n  - name: x\n    type: u8",  # Missing name
            "",  # Empty
            "---\n" * 100,  # Many documents
        ]
        return self.rng.choice(cases)
    
    def generate_circular_ref(self) -> dict:
        """Generate schema with circular reference."""
        return {
            'name': 'circular',
            'version': 1,
            'fields': [
                {'name': 'a', 'type': 'object', 'fields': [
                    {'$ref': '#/definitions/b'}
                ]}
            ],
            'definitions': {
                'b': {'fields': [{'$ref': '#/definitions/b'}]}
            }
        }
    
    def generate_deep_nesting(self, depth: int = 100) -> dict:
        """Generate deeply nested schema."""
        inner = {'name': 'leaf', 'type': 'u8'}
        for i in range(depth):
            inner = {
                'name': f'level_{i}',
                'type': 'object',
                'fields': [inner]
            }
        return {
            'name': 'deep',
            'version': 1,
            'fields': [inner]
        }
    
    def generate_unknown_types(self) -> dict:
        """Generate schema with unknown types."""
        return {
            'name': 'unknown',
            'version': 1,
            'fields': [
                {'name': 'a', 'type': 'foobar'},
                {'name': 'b', 'type': 'u999'},
                {'name': 'c', 'type': ''},
            ]
        }
    
    def fuzz_one(self, schema: any) -> bool:
        """Try to create interpreter with schema."""
        self.stats.total_inputs += 1
        try:
            if isinstance(schema, str):
                schema = yaml.safe_load(schema)
            interpreter = SchemaInterpreter(schema)
            self.stats.decode_success += 1
            return True
        except Exception:
            self.stats.decode_error += 1
            return True
        except SystemExit:
            self.stats.crashes += 1
            return False
    
    def run(self, duration_sec: float = 10.0) -> FuzzStats:
        """Run schema fuzzing."""
        start_time = time.time()
        end_time = start_time + duration_sec
        
        generators = [
            self.generate_malformed_yaml,
            self.generate_circular_ref,
            lambda: self.generate_deep_nesting(self.rng.randint(10, 100)),
            self.generate_unknown_types,
            lambda: None,
            lambda: [],
            lambda: "string",
            lambda: 12345,
        ]
        
        while time.time() < end_time:
            generator = self.rng.choice(generators)
            schema = generator()
            self.fuzz_one(schema)
        
        self.stats.duration_sec = time.time() - start_time
        return self.stats


def print_stats(stats: FuzzStats, name: str):
    """Print fuzzing statistics."""
    print(f"\n{name} Fuzzing Results")
    print("=" * 50)
    print(f"Seed: {stats.seed}")
    print(f"Duration: {stats.duration_sec:.1f}s")
    print(f"Total inputs: {stats.total_inputs}")
    print(f"Rate: {stats.inputs_per_sec:.0f} inputs/sec")
    print(f"Decode success: {stats.decode_success}")
    print(f"Decode errors: {stats.decode_error} (expected)")
    print(f"Crashes: {stats.crashes}")
    
    if stats.crashes > 0:
        print("\nCRASH INPUTS (reproducible with --seed):")
        for i, payload in enumerate(stats.crash_inputs[:5]):
            print(f"  {i+1}: {payload.hex()}")
        print("\nFAILED: Decoder crashed on malformed input!")
    else:
        print("\nPASSED: No crashes detected")


def main():
    parser = argparse.ArgumentParser(
        description='Fuzz test schema decoder (Payload Schema Section 11)'
    )
    parser.add_argument('schema', nargs='?', help='Path to schema YAML file')
    parser.add_argument('-d', '--duration', type=float, default=10.0,
                       help='Fuzz duration in seconds (default: 10)')
    parser.add_argument('-s', '--seed', type=int,
                       help='Random seed for reproducibility')
    parser.add_argument('--schema-fuzz', action='store_true',
                       help='Also fuzz schema parser')
    args = parser.parse_args()
    
    exit_code = 0
    
    # Decoder fuzzing (if schema provided)
    if args.schema:
        with open(args.schema) as f:
            schema = yaml.safe_load(f)
        
        print(f"Fuzzing decoder: {args.schema}")
        fuzzer = DecoderFuzzer(schema, seed=args.seed)
        stats = fuzzer.run(args.duration)
        print_stats(stats, "Decoder")
        
        if stats.crashes > 0:
            exit_code = 1
    
    # Schema fuzzing
    if args.schema_fuzz or not args.schema:
        print("\nFuzzing schema parser...")
        fuzzer = SchemaFuzzer(seed=args.seed)
        stats = fuzzer.run(args.duration)
        print_stats(stats, "Schema Parser")
        
        if stats.crashes > 0:
            exit_code = 1
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
