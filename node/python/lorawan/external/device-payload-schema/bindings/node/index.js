/**
 * @lorawan-schema/native - Native Node.js bindings for schema interpreter
 *
 * High-performance payload decoding using the C schema interpreter via N-API.
 *
 * @example
 * const { NativeSchema } = require('@lorawan-schema/native');
 *
 * // Load binary schema
 * const schema = new NativeSchema(binarySchemaBuffer);
 *
 * // Decode payload
 * const result = schema.decode(payloadBuffer);
 * console.log(result); // { temperature: 25.5, humidity: 60 }
 *
 * // Or get JSON directly (faster for serialization)
 * const json = schema.decodeJSON(payloadBuffer);
 *
 * @module @lorawan-schema/native
 */

'use strict';

let native;
try {
    native = require('./build/Release/schema_native.node');
} catch (e) {
    try {
        native = require('./build/Debug/schema_native.node');
    } catch (e2) {
        throw new Error(
            'Native module not found. Run `npm run build` to compile.\n' +
            'Original error: ' + e.message
        );
    }
}

/**
 * Native schema decoder using C implementation.
 *
 * @class NativeSchema
 * @param {Buffer} binarySchema - Binary schema data
 * @throws {Error} If schema parsing fails
 *
 * @example
 * const schema = new NativeSchema(Buffer.from([0x01, 0x05, ...]));
 * const result = schema.decode(payloadBuffer);
 */
class NativeSchema extends native.NativeSchema {
    /**
     * Create a NativeSchema from binary data.
     *
     * @param {Buffer} binarySchema - Binary schema data
     * @throws {TypeError} If argument is not a Buffer
     * @throws {Error} If schema parsing fails
     */
    constructor(binarySchema) {
        if (!Buffer.isBuffer(binarySchema)) {
            throw new TypeError('binarySchema must be a Buffer');
        }
        super(binarySchema);
    }

    /**
     * Decode a payload using this schema.
     *
     * @param {Buffer} payload - Raw payload bytes
     * @returns {Object} Decoded field values as key-value pairs
     * @throws {TypeError} If payload is not a Buffer
     * @throws {Error} If decoding fails
     *
     * @example
     * const result = schema.decode(Buffer.from('02012f0003', 'hex'));
     * // { protocol_version: 2, device_id: 303, flags: 3 }
     */
    decode(payload) {
        if (!Buffer.isBuffer(payload)) {
            throw new TypeError('payload must be a Buffer');
        }
        return super.decode(payload);
    }

    /**
     * Decode a payload and return JSON string directly.
     *
     * More efficient than decode() + JSON.stringify() when you need
     * JSON output, as the string is built in C without creating
     * intermediate JavaScript objects.
     *
     * @param {Buffer} payload - Raw payload bytes
     * @returns {string} JSON string of decoded values
     * @throws {TypeError} If payload is not a Buffer
     * @throws {Error} If decoding fails
     *
     * @example
     * const json = schema.decodeJSON(payloadBuffer);
     * // '{"temperature":25.5,"humidity":60}'
     */
    decodeJSON(payload) {
        if (!Buffer.isBuffer(payload)) {
            throw new TypeError('payload must be a Buffer');
        }
        return super.decodeJSON(payload);
    }
}

/**
 * Create a NativeSchema from binary data.
 *
 * @param {Buffer} binarySchema - Binary schema data
 * @returns {NativeSchema} Schema instance
 *
 * @example
 * const schema = fromBinary(fs.readFileSync('schema.bin'));
 */
function fromBinary(binarySchema) {
    return new NativeSchema(binarySchema);
}

/**
 * Get the native library version.
 *
 * @returns {string} Version string
 */
function version() {
    return native.version();
}

/**
 * Check if the native module is available.
 *
 * @returns {boolean} True if native module loaded successfully
 */
function isAvailable() {
    return typeof native !== 'undefined' && typeof native.NativeSchema === 'function';
}

module.exports = {
    NativeSchema,
    fromBinary,
    version,
    isAvailable,
};
