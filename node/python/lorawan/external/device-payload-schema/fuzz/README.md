# Fuzz Testing

This directory contains fuzz testing harnesses for the Payload Schema decoder implementations.

Per the Payload Schema specification, decoders MUST NOT crash on any input.

## Quick Start

```bash
# Python random fuzzing (10 sec)
make fuzz-quick

# Python Hypothesis property-based testing
make fuzz-hypothesis

# Full Python fuzz suite
make fuzz-all

# Go fuzzing (requires Go 1.18+)
make fuzz-go

# C fuzzing with libFuzzer (requires clang)
make fuzz-c
```

## Fuzz Methods

### 1. Python Random Fuzzing (`fuzz_decoder.py`)

Fast random input generation targeting the Python interpreter.

```bash
# Quick test (10 seconds)
python tools/fuzz_decoder.py examples/env_sensor.yaml --duration 10

# Full test (10 minutes per schema)
python tools/fuzz_decoder.py examples/env_sensor.yaml --duration 600

# Schema parser fuzzing
python tools/fuzz_decoder.py --schema-fuzz --duration 60

# Reproducible (for debugging crashes)
python tools/fuzz_decoder.py examples/env_sensor.yaml --seed 12345
```

**Inputs generated:**
- Random byte sequences (0-255 bytes)
- Truncated valid payloads
- Extended valid payloads
- Bit-flipped valid payloads
- All zeros / all 0xFF
- Empty payload

**Typical rate:** ~90,000 inputs/sec

### 2. Python Hypothesis (`test_hypothesis.py`)

Property-based testing with intelligent input generation and shrinking.

```bash
# Run with pytest
PYTHONPATH=tools pytest tests/test_hypothesis.py -v

# Show statistics
PYTHONPATH=tools pytest tests/test_hypothesis.py -v --hypothesis-show-statistics

# Profiles: default, ci, dev, debug
HYPOTHESIS_PROFILE=ci pytest tests/test_hypothesis.py -v
```

**Properties tested:**
- Decoder safety (never crashes)
- Roundtrip preservation (encode → decode)
- Type boundary values
- Modifier reversibility
- Bitfield extraction correctness
- Schema parser safety

### 3. Go Fuzzing (`go/decoder_test.go`)

Native Go fuzzing with coverage-guided input generation.

```bash
cd fuzz/go

# Run fuzz tests
go test -fuzz=FuzzDecode -fuzztime=60s
go test -fuzz=FuzzDecodeEncode -fuzztime=60s

# Run unit tests
go test -v
```

**Fuzz functions:**
- `FuzzDecode` - Decoder doesn't panic on any input
- `FuzzDecodeEncode` - Roundtrip preservation
- `FuzzSchemaInterpreter` - Generic type handling

### 4. C Fuzzing with libFuzzer (`fuzz_decoder.c`)

Coverage-guided fuzzing for generated C codecs.

**Build with clang:**
```bash
# Generate codec header first
python tools/generate-c.py examples/env_sensor.yaml -o include/env_sensor_codec.h

# Build with libFuzzer
clang -g -fsanitize=fuzzer,address -I include fuzz/fuzz_decoder.c -o fuzz_decoder

# Run
mkdir -p corpus
./fuzz_decoder corpus/ -max_len=256 -runs=1000000
```

**Build with AFL:**
```bash
afl-clang-fast -g -I include fuzz/fuzz_decoder.c -o fuzz_decoder_afl
mkdir -p corpus findings
echo -ne '\x09\x29\x82\x0C\xE4\x00' > corpus/seed1
afl-fuzz -i corpus -o findings ./fuzz_decoder_afl
```

## CI Integration

The `.github/workflows/fuzz.yml` workflow runs:

| Event | Python Random | Hypothesis | Go Fuzz | C Fuzz |
|-------|--------------|------------|---------|--------|
| PR | 10 sec | default profile | - | - |
| Push to main | 10 min/schema | ci profile | 60 sec | 10 min |
| Nightly schedule | 10 min/schema | ci profile | 60 sec | 10 min |

## Interpreting Results

**PASS:** No crashes detected
```
Decoder Fuzzing Results
==================================================
Total inputs: 916040
Crashes: 0
PASSED: No crashes detected
```

**FAIL:** Crash detected - needs investigation
```
Crashes: 1
CRASH INPUTS (reproducible with --seed):
  1: 0a0b0c...
FAILED: Decoder crashed on malformed input!
```

## Minimum Requirements

- **Per commit:** 10 seconds of fuzzing
- **Per release:** 1 hour of fuzzing
- **Coverage:** All input sources must be tested

## Adding New Schemas

1. Add test vectors to schema YAML
2. Validate: `make validate-schema SCHEMA=path/to/schema.yaml`
3. Fuzz: `python tools/fuzz_decoder.py path/to/schema.yaml --duration 600`
