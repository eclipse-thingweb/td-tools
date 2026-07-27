# Makefile for schema FFI shared library
#
# Build:
#   make              # Build for current platform
#   make linux        # Cross-compile for Linux
#   make macos        # Build for macOS
#   make windows      # Cross-compile for Windows (requires mingw)
#   make all          # Build all platforms
#   make clean        # Remove build artifacts
#   make test         # Run quick test

CC ?= gcc
CFLAGS = -O2 -fPIC -Wall -Wextra -I../../include
LDFLAGS = -shared

# Detect platform
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
    LIBEXT = .dylib
    LDFLAGS += -dynamiclib
else ifeq ($(UNAME_S),Linux)
    LIBEXT = .so
else
    LIBEXT = .dll
endif

LIBNAME = libschema$(LIBEXT)
SRC = schema_ffi.c
HDR = schema_ffi.h ../../include/schema_interpreter.h

.PHONY: all clean test linux macos windows install

# Default target
$(LIBNAME): $(SRC) $(HDR)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $(SRC)
	@echo "Built $@"

# Platform-specific builds
linux: CC = gcc
linux: LIBEXT = .so
linux:
	$(CC) $(CFLAGS) -shared -o libschema.so $(SRC)
	@echo "Built libschema.so"

macos: CC = clang
macos: LIBEXT = .dylib
macos:
	$(CC) $(CFLAGS) -shared -dynamiclib -o libschema.dylib $(SRC)
	@echo "Built libschema.dylib"

windows: CC = x86_64-w64-mingw32-gcc
windows:
	$(CC) $(CFLAGS) -shared -DSCHEMA_FFI_EXPORTS -o schema.dll $(SRC)
	@echo "Built schema.dll"

all: linux macos

# Quick test
test: $(LIBNAME)
	@echo "Testing library load..."
	@python3 -c "import ctypes; lib = ctypes.CDLL('./$(LIBNAME)'); print('Version:', lib.schema_version().decode())"
	@echo "Test passed!"

# Install to system (Linux)
install: libschema.so
	sudo cp libschema.so /usr/local/lib/
	sudo ldconfig
	@echo "Installed to /usr/local/lib/"

clean:
	rm -f libschema.so libschema.dylib schema.dll *.o

# Static library (for embedding)
libschema.a: $(SRC) $(HDR)
	$(CC) $(CFLAGS) -c -o schema_ffi.o $(SRC)
	ar rcs $@ schema_ffi.o
	@echo "Built $@"
