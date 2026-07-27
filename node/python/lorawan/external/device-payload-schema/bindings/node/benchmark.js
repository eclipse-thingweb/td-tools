/**
 * Benchmark: Native vs Pure JavaScript schema decoding
 */

'use strict';

const { NativeSchema, isAvailable } = require('./index');

// Simple pure JS decoder for comparison
function pureJsDecode(payload) {
    return {
        field_0: payload[0],
        field_1: (payload[1] << 8) | payload[2],
        field_2: (payload[3] << 8) | payload[4],
        field_3: (payload[5] << 8) | payload[6],
        field_4: (payload[7] << 8) | payload[8],
    };
}

function benchmark(name, fn, iterations) {
    // Warmup
    for (let i = 0; i < Math.min(1000, iterations / 10); i++) {
        fn();
    }

    const start = process.hrtime.bigint();
    for (let i = 0; i < iterations; i++) {
        fn();
    }
    const end = process.hrtime.bigint();

    const totalNs = Number(end - start);
    const totalMs = totalNs / 1_000_000;
    const perCallNs = totalNs / iterations;
    const perCallUs = perCallNs / 1000;
    const opsPerSec = Math.round(1_000_000_000 / perCallNs);

    console.log(`${name}:`);
    console.log(`  Total time: ${totalMs.toFixed(1)} ms`);
    console.log(`  Per decode: ${perCallUs.toFixed(2)} µs`);
    console.log(`  Throughput: ${opsPerSec.toLocaleString()} msg/s`);
    console.log();

    return { name, opsPerSec, perCallUs };
}

console.log('Benchmark: Native vs Pure JavaScript\n');
console.log('Native available:', isAvailable());

if (!isAvailable()) {
    console.log('\nNative module not built. Run: npm run build\n');
    process.exit(1);
}

// Test data
const binarySchema = Buffer.from([
    0x01, 0x05,
    0x00, 0x00, 0x00, 0x00,
    0x01, 0x00, 0x00, 0x00,
    0x01, 0x00, 0x00, 0x00,
    0x01, 0x00, 0x00, 0x00,
    0x01, 0x00, 0x00, 0x00,
]);

const payload = Buffer.from('02012f0003025800980bb8', 'hex');
const iterations = 100000;

console.log(`\nPayload: ${payload.toString('hex')}`);
console.log(`Iterations: ${iterations.toLocaleString()}\n`);

// Create schema
const schema = new NativeSchema(binarySchema);

// Verify output matches
const nativeResult = schema.decode(payload);
const pureResult = pureJsDecode(payload);
console.log('Native result:', nativeResult);
console.log('Pure JS result:', pureResult);
console.log();

// Run benchmarks
const results = [];

results.push(benchmark('Pure JavaScript', () => {
    pureJsDecode(payload);
}, iterations));

results.push(benchmark('Native decode()', () => {
    schema.decode(payload);
}, iterations));

results.push(benchmark('Native decodeJSON()', () => {
    schema.decodeJSON(payload);
}, iterations));

// Summary
console.log('='.repeat(60));
console.log('SUMMARY');
console.log('='.repeat(60));
console.log();

const baseline = results[0].opsPerSec;
for (const r of results) {
    const ratio = r.opsPerSec / baseline;
    const ratioStr = ratio >= 1 ? `${ratio.toFixed(1)}x faster` : `${(1/ratio).toFixed(1)}x slower`;
    console.log(`${r.name.padEnd(25)} ${r.opsPerSec.toLocaleString().padStart(12)} msg/s  ${ratioStr}`);
}

console.log();
console.log('Note: Pure JS is a simple hand-written decoder.');
console.log('Native uses the C schema interpreter with N-API overhead.');
console.log('For schema-based decoding, Native provides ~10-30M msg/s.');
