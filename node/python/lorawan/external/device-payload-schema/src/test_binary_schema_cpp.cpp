/*
 * test_binary_schema_cpp.cpp - Test binary schema loading in C++ interpreter
 *
 * Compile: g++ -std=c++17 -O2 -I../include -o test_binary_schema_cpp test_binary_schema_cpp.cpp
 */

#include <iostream>
#include <iomanip>
#include <chrono>
#include <vector>
#include "schema_interpreter.hpp"

using namespace payload_schema;

// Binary schema for temperature, humidity, battery
static const std::vector<uint8_t> binary_schema = {
    0x50, 0x53,       // Magic: 'PS'
    0x01,             // Version: 1
    0x00,             // Flags: big-endian
    0x03,             // Field count: 3
    
    // Field 0: temperature (s16, mult=0.01)
    0x12,             // Type: SINT(1), Size: 2
    0xFE,             // Mult exp: -2 -> 0.01
    0xE7, 0x0C,       // Field ID: 3303 (temperature)
    
    // Field 1: humidity (u8, mult=0.5)
    0x01,             // Type: UINT(0), Size: 1
    0x81,             // Mult exp: special 0.5
    0xE8, 0x0C,       // Field ID: 3304 (humidity)
    
    // Field 2: battery (u16)
    0x02,             // Type: UINT(0), Size: 2
    0x00,             // Mult exp: 0 -> 1.0
    0xF4, 0x0C,       // Field ID: 3316 (voltage)
};

void test_binary_loading() {
    std::cout << "=== C++ Binary Schema Loading Test ===\n\n";
    
    try {
        auto schema = Schema::loadBinary(binary_schema);
        
        // Decode test payload
        // temp=0x0929=2345 -> 23.45, hum=0x82=130 -> 65.0, bat=0x0CE4=3300
        std::vector<uint8_t> payload = {0x09, 0x29, 0x82, 0x0C, 0xE4};
        
        auto result = schema.decode(payload);
        
        if (!result.ok()) {
            std::cout << "Decode error: " << result.error << "\n";
            return;
        }
        
        std::cout << "Decoded " << result.fields.size() << " fields:\n";
        for (const auto& f : result.fields) {
            std::visit([&](const auto& val) {
                using T = std::decay_t<decltype(val)>;
                if constexpr (std::is_same_v<T, double>) {
                    std::cout << "  " << f.name << ": " << std::fixed 
                              << std::setprecision(2) << val << "\n";
                } else if constexpr (std::is_arithmetic_v<T>) {
                    std::cout << "  " << f.name << ": " << val << "\n";
                }
            }, f.value);
        }
        
        std::cout << "\nExpected: temperature=23.45, humidity=65.00, voltage=3300\n";
        
        // Verify
        auto temp = result.get<double>("temperature");
        auto hum = result.get<double>("humidity");
        auto volt = result.get<double>("voltage");
        
        std::cout << "\nUsing typed accessors:\n";
        std::cout << "  temperature: " << (temp ? *temp : 0.0) << "\n";
        std::cout << "  humidity: " << (hum ? *hum : 0.0) << "\n";
        std::cout << "  voltage: " << (volt ? *volt : 0.0) << "\n";
        
    } catch (const std::exception& e) {
        std::cout << "Exception: " << e.what() << "\n";
    }
}

void benchmark_binary_vs_programmatic() {
    std::cout << "\n=== C++ Benchmark: Binary vs Programmatic ===\n\n";
    
    constexpr int iterations = 10'000'000;
    std::vector<uint8_t> payload = {0x09, 0x29, 0x82, 0x0C, 0xE4};
    
    // Programmatic schema
    Schema prog_schema("programmatic");
    prog_schema.addField<int16_t>("temperature").mult(0.01);
    prog_schema.addField<uint8_t>("humidity").mult(0.5);
    prog_schema.addField<uint16_t>("battery");
    
    // Binary schema
    auto bin_schema = Schema::loadBinary(binary_schema);
    
    // Warmup
    for (int i = 0; i < 1000; i++) {
        prog_schema.decode(payload);
        bin_schema.decode(payload);
    }
    
    // Benchmark programmatic
    auto start = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < iterations; i++) {
        auto result = prog_schema.decode(payload);
    }
    auto prog_time = std::chrono::high_resolution_clock::now() - start;
    double prog_us = std::chrono::duration<double, std::micro>(prog_time).count() / iterations;
    
    // Benchmark binary
    start = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < iterations; i++) {
        auto result = bin_schema.decode(payload);
    }
    auto bin_time = std::chrono::high_resolution_clock::now() - start;
    double bin_us = std::chrono::duration<double, std::micro>(bin_time).count() / iterations;
    
    std::cout << "Iterations: " << iterations << "\n";
    std::cout << "Programmatic schema: " << std::fixed << std::setprecision(4) 
              << prog_us << " µs/decode\n";
    std::cout << "Binary schema:       " << bin_us << " µs/decode\n";
    std::cout << "Difference: " << std::setprecision(2) 
              << ((prog_us - bin_us) / prog_us * 100) << "%\n";
    
    // Schema loading benchmark
    std::cout << "\nSchema loading (1000 iterations):\n";
    start = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < 1000; i++) {
        auto s = Schema::loadBinary(binary_schema);
    }
    auto load_time = std::chrono::high_resolution_clock::now() - start;
    double load_us = std::chrono::duration<double, std::micro>(load_time).count() / 1000;
    std::cout << "Binary load: " << std::setprecision(2) << load_us << " µs\n";
}

int main() {
    test_binary_loading();
    benchmark_binary_vs_programmatic();
    return 0;
}
