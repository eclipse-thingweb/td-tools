/**
 * Quick test for native Node.js bindings
 */

'use strict';

const { NativeSchema, version, isAvailable } = require('./index');

console.log('Testing @lorawan-schema/native bindings\n');

// Check availability
console.log('Native available:', isAvailable());
console.log('Version:', version());

// Create test schema (5 fields: u8, u16, u16, u16, u16)
const binarySchema = Buffer.from([
    0x01,       // Version 1
    0x05,       // 5 fields
    0x00, 0x00, 0x00, 0x00,  // field 0: u8
    0x01, 0x00, 0x00, 0x00,  // field 1: u16
    0x01, 0x00, 0x00, 0x00,  // field 2: u16
    0x01, 0x00, 0x00, 0x00,  // field 3: u16
    0x01, 0x00, 0x00, 0x00,  // field 4: u16
]);

// Test payload
const payload = Buffer.from('02012f0003025800980bb8', 'hex');

try {
    // Create schema
    const schema = new NativeSchema(binarySchema);
    console.log('\nSchema created:');
    console.log('  Name:', schema.name || '(unnamed)');
    console.log('  Fields:', schema.fieldCount);

    // Decode
    console.log('\nDecoding payload:', payload.toString('hex'));
    const result = schema.decode(payload);
    console.log('Result:', result);

    // JSON output
    const json = schema.decodeJSON(payload);
    console.log('JSON:', json);

    console.log('\n✓ All tests passed!');
} catch (err) {
    console.error('\n✗ Test failed:', err.message);
    process.exit(1);
}
