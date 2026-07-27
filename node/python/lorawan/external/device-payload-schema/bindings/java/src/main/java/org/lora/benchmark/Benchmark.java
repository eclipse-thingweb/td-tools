package org.lora.benchmark;

import org.lora.schema.*;
import java.io.*;
import java.nio.*;
import java.nio.file.*;
import java.util.*;

public class Benchmark {
    
    private static final int NUM_PAYLOADS = 10000;
    private static final int WARMUP_ITERATIONS = 10;
    private static final int BENCHMARK_ITERATIONS = 100;
    
    public static void main(String[] args) throws Exception {
        System.out.println("=".repeat(70));
        System.out.println("JAVA BENCHMARK: Schema vs Traditional Codec");
        System.out.println("=".repeat(70));
        
        // Load schema
        String schemaPath = findSchemaPath();
        Schema schema = Schema.fromYamlFile(schemaPath);
        System.out.println("✓ Loaded schema: " + schema.getName());
        
        // Generate test payloads
        System.out.println("✓ Generating " + String.format("%,d", NUM_PAYLOADS) + " test payloads...");
        byte[][] payloads = generateTestPayloads(NUM_PAYLOADS);
        
        // Verify correctness
        System.out.println("\nVerifying correctness...");
        int mismatches = verifyCorrectness(payloads, schema);
        if (mismatches == 0) {
            System.out.println("✓ All 100 test payloads decoded identically!");
        } else {
            System.out.println("✗ Found " + mismatches + " mismatches");
            System.exit(1);
        }
        
        // Warm-up
        System.out.println("\nWarming up...");
        for (int i = 0; i < WARMUP_ITERATIONS; i++) {
            for (int j = 0; j < 100; j++) {
                decodeTraditional(payloads[j]);
                schema.decode(payloads[j]);
            }
        }
        
        // Benchmark
        System.out.println("\nBenchmarking...");
        long totalDecodes = (long) NUM_PAYLOADS * BENCHMARK_ITERATIONS;
        
        // Traditional codec
        System.out.println("\n1. Traditional Codec (" + String.format("%,d", totalDecodes) + " decodes)");
        long tradStart = System.nanoTime();
        for (int i = 0; i < BENCHMARK_ITERATIONS; i++) {
            for (byte[] payload : payloads) {
                decodeTraditional(payload);
            }
        }
        long tradTime = System.nanoTime() - tradStart;
        double tradSeconds = tradTime / 1_000_000_000.0;
        double tradPerMsg = tradTime / (double) totalDecodes / 1000.0; // microseconds
        double tradThroughput = totalDecodes / tradSeconds;
        
        System.out.printf("   Total time:  %.3fs%n", tradSeconds);
        System.out.printf("   Per message: %.2fµs%n", tradPerMsg);
        System.out.printf("   Throughput:  %,.0f msg/s%n", tradThroughput);
        
        // Schema-based (YAML, pre-parsed)
        System.out.println("\n2. Schema-based Interpreter (" + String.format("%,d", totalDecodes) + " decodes)");
        long schemaStart = System.nanoTime();
        for (int i = 0; i < BENCHMARK_ITERATIONS; i++) {
            for (byte[] payload : payloads) {
                schema.decode(payload);
            }
        }
        long schemaTime = System.nanoTime() - schemaStart;
        double schemaSeconds = schemaTime / 1_000_000_000.0;
        double schemaPerMsg = schemaTime / (double) totalDecodes / 1000.0;
        double schemaThroughput = totalDecodes / schemaSeconds;
        
        System.out.printf("   Total time:  %.3fs%n", schemaSeconds);
        System.out.printf("   Per message: %.2fµs%n", schemaPerMsg);
        System.out.printf("   Throughput:  %,.0f msg/s%n", schemaThroughput);
        
        // YAML cold parse benchmark
        System.out.println("\n3. YAML Parse + Decode (" + String.format("%,d", NUM_PAYLOADS) + " cold parses)");
        String yamlContent = Files.readString(Path.of(schemaPath));
        long yamlColdStart = System.nanoTime();
        for (int i = 0; i < NUM_PAYLOADS; i++) {
            Schema coldSchema = Schema.fromYaml(yamlContent);
            coldSchema.decode(payloads[i]);
        }
        long yamlColdTime = System.nanoTime() - yamlColdStart;
        double yamlColdSeconds = yamlColdTime / 1_000_000_000.0;
        double yamlColdPerMsg = yamlColdTime / (double) NUM_PAYLOADS / 1000.0;
        double yamlColdThroughput = NUM_PAYLOADS / yamlColdSeconds;
        
        System.out.printf("   Total time:  %.3fs%n", yamlColdSeconds);
        System.out.printf("   Per message: %.2fµs%n", yamlColdPerMsg);
        System.out.printf("   Throughput:  %,.0f msg/s%n", yamlColdThroughput);
        
        // Try binary schema if available
        String binarySchemaPath = schemaPath.replace(".yaml", ".bin");
        if (Files.exists(Path.of(binarySchemaPath))) {
            byte[] binaryData = Files.readAllBytes(Path.of(binarySchemaPath));
            Schema binarySchema = new BinarySchemaParser().parse(binaryData);
            
            // Binary warm
            System.out.println("\n4. Binary Schema (pre-parsed) (" + String.format("%,d", totalDecodes) + " decodes)");
            long binaryWarmStart = System.nanoTime();
            for (int i = 0; i < BENCHMARK_ITERATIONS; i++) {
                for (byte[] payload : payloads) {
                    binarySchema.decode(payload);
                }
            }
            long binaryWarmTime = System.nanoTime() - binaryWarmStart;
            double binaryWarmSeconds = binaryWarmTime / 1_000_000_000.0;
            double binaryWarmPerMsg = binaryWarmTime / (double) totalDecodes / 1000.0;
            double binaryWarmThroughput = totalDecodes / binaryWarmSeconds;
            
            System.out.printf("   Total time:  %.3fs%n", binaryWarmSeconds);
            System.out.printf("   Per message: %.2fµs%n", binaryWarmPerMsg);
            System.out.printf("   Throughput:  %,.0f msg/s%n", binaryWarmThroughput);
            
            // Binary cold
            System.out.println("\n5. Binary Schema (parse + decode) (" + String.format("%,d", NUM_PAYLOADS) + " cold parses)");
            long binaryColdStart = System.nanoTime();
            for (int i = 0; i < NUM_PAYLOADS; i++) {
                Schema coldBinarySchema = new BinarySchemaParser().parse(binaryData);
                coldBinarySchema.decode(payloads[i]);
            }
            long binaryColdTime = System.nanoTime() - binaryColdStart;
            double binaryColdSeconds = binaryColdTime / 1_000_000_000.0;
            double binaryColdPerMsg = binaryColdTime / (double) NUM_PAYLOADS / 1000.0;
            double binaryColdThroughput = NUM_PAYLOADS / binaryColdSeconds;
            
            System.out.printf("   Total time:  %.3fs%n", binaryColdSeconds);
            System.out.printf("   Per message: %.2fµs%n", binaryColdPerMsg);
            System.out.printf("   Throughput:  %,.0f msg/s%n", binaryColdThroughput);
        }
        
        // Summary
        System.out.println("\n" + "=".repeat(70));
        System.out.println("SUMMARY");
        System.out.println("=".repeat(70));
        
        double slowdown = schemaSeconds / tradSeconds;
        System.out.printf("Schema is %.2fx slower than traditional codec%n", slowdown);
        System.out.printf("  (%.1fµs vs %.1fµs per message)%n", schemaPerMsg, tradPerMsg);
        
        System.out.println("\nBut schema provides:");
        System.out.println("  ✓ Portability (Java, Python, JavaScript, Go)");
        System.out.println("  ✓ Maintainability (declarative YAML)");
        System.out.println("  ✓ Documentation (schema IS docs)");
        System.out.println("  ✓ Validation (catches errors early)");
        
        if (slowdown < 10.0) {
            System.out.println("\n✓ Performance penalty is reasonable (<10x)");
        } else {
            System.out.println("\n⚠ Performance penalty is high (>10x)");
        }
    }
    
    private static String findSchemaPath() {
        String[] candidates = {
            "milesight_sensor.yaml",
            "../benchmarks/milesight_sensor.yaml",
            "reference-impl/benchmarks/milesight_sensor.yaml",
            "/app/benchmarks/milesight_sensor.yaml"
        };
        
        for (String path : candidates) {
            if (Files.exists(Path.of(path))) {
                return path;
            }
        }
        
        throw new RuntimeException("Could not find milesight_sensor.yaml schema file");
    }
    
    private static byte[][] generateTestPayloads(int count) {
        Random random = new Random(42); // Fixed seed for reproducibility
        byte[][] payloads = new byte[count][];
        
        for (int i = 0; i < count; i++) {
            payloads[i] = generateSinglePayload(random);
        }
        
        return payloads;
    }
    
    private static byte[] generateSinglePayload(Random random) {
        // Match the milesight_sensor.yaml format (10 bytes, little-endian):
        // s16: temperature (div 100)
        // u8: humidity (mult 0.5)
        // u16: battery (div 1000)
        // u32: timestamp
        // bits: alarm, battery_low, sensor_fault (in 1 byte)
        
        ByteBuffer buffer = ByteBuffer.allocate(10);
        buffer.order(ByteOrder.LITTLE_ENDIAN);
        
        short temperature = (short) (random.nextInt(13001) - 5000); // -50°C to 80°C in 0.01°C
        byte humidity = (byte) random.nextInt(201); // 0-100% in 0.5% steps
        short battery = (short) (random.nextInt(2201) + 2000); // 2.0V to 4.2V in 0.001V
        int timestamp = random.nextInt(100000000) + 1700000000; // 2023-2024
        byte flags = (byte) random.nextInt(8); // 3 bits of flags
        
        buffer.putShort(temperature);
        buffer.put(humidity);
        buffer.putShort(battery);
        buffer.putInt(timestamp);
        buffer.put(flags);
        
        return buffer.array();
    }
    
    private static Map<String, Object> decodeTraditional(byte[] payload) {
        if (payload.length != 10) {
            throw new IllegalArgumentException("Invalid payload length");
        }
        
        ByteBuffer buffer = ByteBuffer.wrap(payload);
        buffer.order(ByteOrder.LITTLE_ENDIAN);
        
        short tempRaw = buffer.getShort();
        int humidityRaw = buffer.get() & 0xFF;
        int batteryRaw = buffer.getShort() & 0xFFFF;
        int timestamp = buffer.getInt();
        int flags = buffer.get() & 0xFF;
        
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("temperature", tempRaw / 100.0);
        result.put("humidity", humidityRaw * 0.5);
        result.put("battery", batteryRaw / 1000.0);
        result.put("timestamp", (long) timestamp);
        result.put("alarm", (flags & 0x01) != 0);
        result.put("battery_low", (flags & 0x02) != 0);
        result.put("sensor_fault", (flags & 0x04) != 0);
        
        return result;
    }
    
    private static int verifyCorrectness(byte[][] payloads, Schema schema) {
        int mismatches = 0;
        
        for (int i = 0; i < Math.min(100, payloads.length); i++) {
            Map<String, Object> traditional = decodeTraditional(payloads[i]);
            Map<String, Object> schemaResult = schema.decode(payloads[i]);
            
            for (String key : traditional.keySet()) {
                if (!schemaResult.containsKey(key)) {
                    System.out.println("  ✗ Mismatch #" + i + ": " + key + " missing in schema result");
                    mismatches++;
                    continue;
                }
                
                Object tradVal = traditional.get(key);
                Object schemaVal = schemaResult.get(key);
                
                // Handle type conversions for comparison
                if (tradVal instanceof Boolean && schemaVal instanceof Number) {
                    schemaVal = ((Number) schemaVal).intValue() != 0;
                }
                if (tradVal instanceof Boolean && schemaVal instanceof Long) {
                    schemaVal = ((Long) schemaVal) != 0;
                }
                
                if (tradVal instanceof Number && schemaVal instanceof Number) {
                    double tradNum = ((Number) tradVal).doubleValue();
                    double schemaNum = ((Number) schemaVal).doubleValue();
                    if (Math.abs(tradNum - schemaNum) > 0.0001) {
                        System.out.println("  ✗ Mismatch #" + i + ": " + key + " = " + tradVal + " vs " + schemaVal);
                        mismatches++;
                    }
                } else if (!Objects.equals(tradVal, schemaVal)) {
                    System.out.println("  ✗ Mismatch #" + i + ": " + key + " = " + tradVal + " vs " + schemaVal);
                    mismatches++;
                }
            }
        }
        
        return mismatches;
    }
}
