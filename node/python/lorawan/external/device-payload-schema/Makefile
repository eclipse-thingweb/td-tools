# LoRaWAN Payload Schema Build System
# Portable C code targeting Linux, Zephyr, FreeRTOS

# Platform selection
PLATFORM ?= linux
VARIANT ?= debug

# Build directory
BUILD_DIR = build-$(PLATFORM)-$(VARIANT)

# Compiler settings
ifeq ($(PLATFORM),linux)
    CC = gcc
    CFLAGS = -std=c11 -Wall -Wextra -Werror
    CFLAGS += -DPLATFORM_LINUX
    LDFLAGS = -lm
    SYS_SRC = sys_linux.c
endif

ifeq ($(PLATFORM),zephyr)
    # Zephyr uses its own build system (west/cmake)
    # This is for reference; actual build uses west build
    $(error Zephyr builds use: west build -b <board>)
endif

# Variant settings
ifeq ($(VARIANT),debug)
    CFLAGS += -g -O0 -DDEBUG
endif

ifeq ($(VARIANT),release)
    CFLAGS += -O2 -DNDEBUG
endif

ifeq ($(VARIANT),coverage)
    CFLAGS += -g -O0 --coverage -fprofile-arcs -ftest-coverage
    LDFLAGS += --coverage
endif

# Include paths
CFLAGS += -Iinclude

# Source files - selftest framework only
SELFTEST_SRCS = src/selftests.c src/selftest_codec.c src/selftest_protocol.c src/sys_linux.c
SELFTEST_OBJS = $(patsubst src/%.c,$(BUILD_DIR)/%.o,$(SELFTEST_SRCS))

# Test binary
TEST_BIN = $(BUILD_DIR)/bin/selftest

# Codec binaries
CODEC_TEST_BIN = $(BUILD_DIR)/bin/test_codec
BENCHMARK_BIN = $(BUILD_DIR)/bin/benchmark

# Protocol buffer sources (if any)
PROTO_SRCS = $(wildcard proto/*.proto)
PROTO_C = $(patsubst proto/%.proto,src/%.pb.c,$(PROTO_SRCS))

# C++ compiler
CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -O3 -Iinclude

.PHONY: all clean test selftest coverage proto help codec benchmark generate-codec pytest pytest-cov coverage-html coverage-all validate fuzz fuzz-quick fuzz-hypothesis fuzz-go fuzz-c

all: $(TEST_BIN)

# Create build directories
$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)/bin

# Compile C sources
$(BUILD_DIR)/%.o: src/%.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

# Build selftests.o with SELFTEST_MAIN for standalone executable
$(BUILD_DIR)/selftests.o: src/selftests.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -DSELFTEST_MAIN -c $< -o $@

# Link selftest binary
$(TEST_BIN): $(SELFTEST_OBJS) | $(BUILD_DIR)
	mkdir -p $(BUILD_DIR)/bin
	$(CC) $(SELFTEST_OBJS) $(LDFLAGS) -o $@

# Run self-tests
selftest: $(TEST_BIN)
	$(TEST_BIN)

test: selftest pytest
	@echo "All tests complete."

# Python virtual environment
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
PYTEST = $(VENV)/bin/pytest

$(VENV)/bin/activate:
	python3 -m venv $(VENV)
	$(PIP) install --quiet pytest pytest-cov pyyaml

# Python tests
pytest: $(VENV)/bin/activate
	@echo "Running Python tests..."
	PYTHONPATH=tools $(PYTEST) tests/ -v

# Python tests with coverage
pytest-cov: $(VENV)/bin/activate
	@echo "Running Python tests with coverage..."
	PYTHONPATH=tools $(PYTEST) tests/ -v --cov=tools --cov-report=term-missing --cov-report=html:coverage-html

# Generate HTML coverage report
coverage-html: pytest-cov
	@echo "Coverage report generated: coverage-html/index.html"
	@echo "Open with: xdg-open coverage-html/index.html"

# Combined C and Python coverage
coverage-all: coverage pytest-cov
	@echo "=== Coverage Summary ==="
	@echo "C coverage: see *.gcov files"
	@echo "Python coverage: see coverage-html/index.html"

# Generated codec test
$(CODEC_TEST_BIN): src/test_codec.c include/env_sensor_codec.h | $(BUILD_DIR)
	mkdir -p $(BUILD_DIR)/bin
	$(CC) $(CFLAGS) src/test_codec.c -o $@

codec: $(CODEC_TEST_BIN)
	$(CODEC_TEST_BIN)

# C++ Benchmark
$(BENCHMARK_BIN): src/benchmark.cpp include/env_sensor_codec.h | $(BUILD_DIR)
	mkdir -p $(BUILD_DIR)/bin
	$(CXX) $(CXXFLAGS) src/benchmark.cpp -o $@

benchmark: $(BENCHMARK_BIN)
	$(BENCHMARK_BIN)

# Generate C codec from schema (old single-file generator)
generate-codec:
	python3 tools/generate-c.py examples/env_sensor.yaml -o include/env_sensor_codec.h
	@echo "Generated: include/env_sensor_codec.h"

# Generate codec + tests from schema (new comprehensive generator)
generate: $(VENV)/bin/activate
	$(PYTHON) tools/generate_codec.py examples/env_sensor.yaml -o generated/
	@echo "Generated codec and tests in generated/"

# Run generated tests
test-generated: generate
	@echo "=== C Tests ==="
	gcc -Wall -Wextra -o generated/env_sensor_test generated/env_sensor_test.c -lm
	./generated/env_sensor_test
	@echo ""
	@echo "=== Python Tests ==="
	PYTHONPATH=tools $(PYTEST) generated/test_env_sensor.py -v

# Validate schema and run test vectors
validate: $(VENV)/bin/activate
	@for schema in examples/*.yaml; do \
		echo ""; \
		$(PYTHON) tools/validate_schema.py $$schema; \
	done

# Validate single schema
validate-schema: $(VENV)/bin/activate
	@if [ -z "$(SCHEMA)" ]; then \
		echo "Usage: make validate-schema SCHEMA=path/to/schema.yaml"; \
		exit 1; \
	fi
	$(PYTHON) tools/validate_schema.py $(SCHEMA) -v

# Fuzz testing (10 min per schema - CI/release)
fuzz: $(VENV)/bin/activate
	@echo "Fuzzing decoder (10 min per schema)..."
	@for schema in examples/*.yaml; do \
		$(PYTHON) tools/fuzz_decoder.py $$schema --duration 600; \
	done
	@echo ""
	@echo "Fuzzing schema parser (10 min)..."
	$(PYTHON) tools/fuzz_decoder.py --schema-fuzz --duration 600

# Quick fuzz (10 sec - per commit)
fuzz-quick: $(VENV)/bin/activate
	@echo "Quick fuzz test (10 sec)..."
	$(PYTHON) tools/fuzz_decoder.py examples/env_sensor.yaml --duration 10 --schema-fuzz

# Hypothesis property-based testing
fuzz-hypothesis: $(VENV)/bin/activate
	@echo "Running Hypothesis property-based tests..."
	$(PIP) install --quiet hypothesis
	PYTHONPATH=tools $(PYTEST) tests/test_hypothesis.py -v --hypothesis-show-statistics

# Go fuzz (requires Go 1.18+)
fuzz-go:
	@echo "Running Go fuzz tests (60 sec each)..."
	cd fuzz/go && go test -fuzz=FuzzDecode -fuzztime=60s
	cd fuzz/go && go test -fuzz=FuzzDecodeEncode -fuzztime=60s

# C fuzz with libFuzzer (requires clang)
fuzz-c: generate-codec
	@echo "Building and running C fuzzer..."
	mkdir -p fuzz/corpus
	echo -n -e '\x09\x29\x82\x0C\xE4\x00' > fuzz/corpus/normal
	echo -n -e '\x00\x00\x00\x00\x00\x00' > fuzz/corpus/zeros
	clang -g -O1 -fsanitize=fuzzer,address -Iinclude fuzz/fuzz_decoder.c -o fuzz/fuzz_decoder
	./fuzz/fuzz_decoder fuzz/corpus/ -max_len=256 -max_total_time=60 -print_final_stats=1

# Full fuzz suite (all methods)
fuzz-all: fuzz-quick fuzz-hypothesis
	@echo "Note: Run 'make fuzz-go' and 'make fuzz-c' separately (require Go/clang)"

# Generate coverage report
coverage: VARIANT=coverage
coverage: clean $(TEST_BIN)
	$(TEST_BIN)
	gcov -o $(BUILD_DIR) src/*.c
	@echo "Coverage files generated. Use lcov for HTML report."

# Generate protobuf C files (requires nanopb)
proto: $(PROTO_C)

src/%.pb.c: proto/%.proto
	nanopb_generator -I proto -D src $<

# Python simulation
simulation:
	python simulation/run_simulation.py

# Clean build artifacts
clean:
	rm -rf build-*
	rm -f src/*.pb.c src/*.pb.h
	rm -f *.gcov *.gcda *.gcno
	rm -rf coverage-html .coverage .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Clean including venv
distclean: clean
	rm -rf $(VENV)

# Help
help:
	@echo "LoRaWAN Payload Schema Build System"
	@echo ""
	@echo "Usage: make [target] [PLATFORM=<platform>] [VARIANT=<variant>]"
	@echo ""
	@echo "Platforms:"
	@echo "  linux     Linux/POSIX (default)"
	@echo "  zephyr    Zephyr RTOS (use west build instead)"
	@echo ""
	@echo "Variants:"
	@echo "  debug     Debug build with symbols (default)"
	@echo "  release   Optimized release build"
	@echo "  coverage  Debug with coverage instrumentation"
	@echo ""
	@echo "Targets:"
	@echo "  all           Build test binary (default)"
	@echo "  selftest      Build and run C self-tests"
	@echo "  test          Run all tests (C + Python)"
	@echo "  pytest        Run Python tests only"
	@echo "  pytest-cov    Run Python tests with coverage"
	@echo "  coverage-html Generate HTML coverage report"
	@echo "  coverage-all  Run all coverage (C + Python)"
	@echo "  coverage      Build and run C with coverage"
	@echo "  proto         Generate protobuf C files"
	@echo "  codec         Build and test generated codec"
	@echo "  benchmark     Run C++ benchmark"
	@echo "  generate-codec Generate C codec from schema"
	@echo "  generate      Generate codec + tests from schema"
	@echo "  test-generated Build and run generated tests"
	@echo "  validate      Validate all example schemas"
	@echo "  validate-schema SCHEMA=path Validate single schema"
	@echo "  fuzz          Full fuzz test (10 min/schema - release)"
	@echo "  fuzz-quick    Quick fuzz test (10 sec - per commit)"
	@echo "  fuzz-hypothesis Hypothesis property-based testing"
	@echo "  fuzz-go       Go fuzz tests (requires Go 1.18+)"
	@echo "  fuzz-c        C libFuzzer tests (requires clang)"
	@echo "  fuzz-all      Run all Python fuzz methods"
	@echo "  clean         Remove build artifacts"
	@echo "  help          Show this help"
	@echo ""
	@echo "Examples:"
	@echo "  make                          # Build debug"
	@echo "  make selftest                 # Build and run C tests"
	@echo "  make pytest                   # Run Python tests"
	@echo "  make pytest-cov               # Python tests + coverage"
	@echo "  make VARIANT=release          # Release build"
	@echo "  make coverage-all             # Full coverage report"
