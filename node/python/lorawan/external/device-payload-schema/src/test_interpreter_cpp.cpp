/*
 * test_interpreter_cpp.cpp - Test C++ Schema Interpreter
 *
 * Compile: g++ -std=c++17 -O2 -I../include -o test_interpreter_cpp test_interpreter_cpp.cpp
 */

#include <iostream>
#include <iomanip>
#include <chrono>
#include <vector>
#include "schema_interpreter.hpp"

using namespace payload_schema;
using namespace std::chrono;

void test_env_sensor() {
    std::cout << "--- Environment Sensor (C++) ---\n";
    
    Schema schema("env_sensor");
    schema.addField<int16_t>("temperature").mult(0.01);
    schema.addField<uint8_t>("humidity").mult(0.5);
    schema.addField<uint16_t>("battery_mv");
    schema.addField<uint8_t>("status");
    
    // temp=23.45°C, humidity=65%, battery=3300mV, status=0
    std::vector<uint8_t> payload = {0x09, 0x29, 0x82, 0x0C, 0xE4, 0x00};
    
    auto result = schema.decode(payload);
    
    if (result.ok()) {
        std::cout << "Decoded " << result.fields.size() << " fields:\n";
        for (const auto& field : result) {
            std::cout << "  " << field.name << ": ";
            std::visit([](auto&& v) {
                using T = std::decay_t<decltype(v)>;
                if constexpr (std::is_same_v<T, std::string>)
                    std::cout << v;
                else if constexpr (std::is_same_v<T, bool>)
                    std::cout << (v ? "true" : "false");
                else if constexpr (std::is_same_v<T, std::vector<uint8_t>>)
                    std::cout << "[bytes]";
                else
                    std::cout << std::fixed << std::setprecision(2) << v;
            }, field.value);
            std::cout << "\n";
        }
        
        std::cout << "\nTyped access:\n";
        std::cout << "  Temperature: " << result.get<double>("temperature", 0) << "°C\n";
        std::cout << "  Humidity: " << result.get<double>("humidity", 0) << "%\n";
        std::cout << "  Battery: " << result.get<int>("battery_mv", 0) << " mV\n";
    } else {
        std::cout << "Error: " << result.error << "\n";
    }
}

void test_radio_bridge() {
    std::cout << "\n--- Radio Bridge (C++) ---\n";
    
    Schema schema("radio_bridge");
    schema.addBitfield("protocol_version", 4, 4, false);
    schema.addBitfield("packet_counter", 0, 4, true);
    schema.addField<uint8_t>("event_type")
        .var("evt")
        .lookup(0, "reset")
        .lookup(1, "supervisory")
        .lookup(2, "tamper")
        .lookup(3, "door_window")
        .lookup(6, "button")
        .lookup(7, "contact")
        .lookup(8, "water");
    schema.addField<uint8_t>("state")
        .lookup(0, "Closed")
        .lookup(1, "Open");
    
    // Door open event
    std::vector<uint8_t> payload = {0x10, 0x03, 0x01};
    
    auto result = schema.decode(payload);
    
    if (result.ok()) {
        std::cout << "Decoded:\n";
        for (const auto& field : result) {
            std::cout << "  " << field.name << ": ";
            std::visit([](auto&& v) {
                using T = std::decay_t<decltype(v)>;
                if constexpr (std::is_same_v<T, std::string>)
                    std::cout << v;
                else if constexpr (std::is_same_v<T, bool>)
                    std::cout << (v ? "true" : "false");
                else if constexpr (std::is_same_v<T, std::vector<uint8_t>>)
                    std::cout << "[bytes]";
                else
                    std::cout << v;
            }, field.value);
            std::cout << "\n";
        }
    }
}

template<typename Func>
void benchmark(const std::string& name, Func fn, int iterations) {
    // Warmup
    for (int i = 0; i < 1000; i++) fn();
    
    auto start = high_resolution_clock::now();
    for (int i = 0; i < iterations; i++) {
        fn();
    }
    auto end = high_resolution_clock::now();
    
    auto elapsed = duration_cast<microseconds>(end - start).count();
    double avg_us = static_cast<double>(elapsed) / iterations;
    
    std::cout << "\n" << name << " Benchmark:\n";
    std::cout << "  Iterations: " << iterations << "\n";
    std::cout << "  Total time: " << elapsed / 1000.0 << " ms\n";
    std::cout << "  Per decode: " << std::fixed << std::setprecision(4) << avg_us << " µs\n";
    std::cout << "  Throughput: " << std::fixed << std::setprecision(0) 
              << (iterations / (elapsed / 1e6)) << " decodes/sec\n";
}

int main() {
    std::cout << "=== C++ Schema Interpreter Test ===\n\n";
    
    test_env_sensor();
    test_radio_bridge();
    
    std::cout << "\n=== Benchmarks ===\n";
    
    // Env sensor benchmark
    Schema env_schema("env_sensor");
    env_schema.addField<int16_t>("temperature").mult(0.01);
    env_schema.addField<uint8_t>("humidity").mult(0.5);
    env_schema.addField<uint16_t>("battery_mv");
    env_schema.addField<uint8_t>("status");
    std::vector<uint8_t> env_payload = {0x09, 0x29, 0x82, 0x0C, 0xE4, 0x00};
    
    benchmark("Env Sensor (C++)", [&]() {
        auto result = env_schema.decode(env_payload);
        (void)result;
    }, 1000000);
    
    // Radio bridge benchmark
    Schema rb_schema("radio_bridge");
    rb_schema.addBitfield("protocol_version", 4, 4, false);
    rb_schema.addBitfield("packet_counter", 0, 4, true);
    rb_schema.addField<uint8_t>("event_type")
        .lookup(3, "door_window");
    rb_schema.addField<uint8_t>("state")
        .lookup(1, "Open");
    std::vector<uint8_t> rb_payload = {0x10, 0x03, 0x01};
    
    benchmark("Radio Bridge (C++)", [&]() {
        auto result = rb_schema.decode(rb_payload);
        (void)result;
    }, 1000000);
    
    return 0;
}
