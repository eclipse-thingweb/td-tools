/**
 * hot_swap.js - Hot-swap schema example for Node.js
 *
 * Demonstrates runtime schema replacement without restart.
 * Uses atomic reference swapping for thread-safe updates.
 *
 * Run: node hot_swap.js
 */

'use strict';

// Mock for demo - in real code: const { NativeSchema } = require('@lorawan-schema/native');
class NativeSchema {
    constructor(buffer) {
        this.fieldCount = buffer[1];
    }
    decode(payload) {
        return { field_0: payload[0] };
    }
    static fromBinary(buffer) {
        return new NativeSchema(buffer);
    }
}

/**
 * SchemaRegistry - Thread-safe schema management with hot-swap.
 *
 * Node.js is single-threaded for JS execution, but async operations
 * can interleave. This class ensures atomic schema replacement.
 */
class SchemaRegistry {
    constructor() {
        this._schemas = new Map();
        this._versions = new Map();
    }

    /**
     * Register or update a schema atomically.
     * @param {string} name - Schema name
     * @param {Buffer} binarySchema - Binary schema data
     * @returns {number} New version number
     */
    register(name, binarySchema) {
        // Parse first (validates before replacing)
        const newSchema = new NativeSchema(binarySchema);

        // Atomic replacement (single JS operation)
        this._schemas.set(name, newSchema);
        const version = (this._versions.get(name) || 0) + 1;
        this._versions.set(name, version);

        return version;
    }

    /**
     * Remove a schema.
     * @param {string} name - Schema name
     * @returns {boolean} True if removed
     */
    unregister(name) {
        const existed = this._schemas.has(name);
        this._schemas.delete(name);
        this._versions.delete(name);
        return existed;
    }

    /**
     * Get a schema by name.
     * @param {string} name - Schema name
     * @returns {NativeSchema|undefined}
     */
    get(name) {
        return this._schemas.get(name);
    }

    /**
     * Decode payload using named schema.
     * @param {string} name - Schema name
     * @param {Buffer} payload - Payload bytes
     * @returns {Object} Decoded values
     */
    decode(name, payload) {
        const schema = this.get(name);
        if (!schema) {
            throw new Error(`Schema '${name}' not found`);
        }
        return schema.decode(payload);
    }

    /**
     * Get current version of a schema.
     * @param {string} name - Schema name
     * @returns {number} Version number (0 if not found)
     */
    getVersion(name) {
        return this._versions.get(name) || 0;
    }

    /**
     * List all schemas with versions.
     * @returns {Object} Map of name -> version
     */
    listSchemas() {
        const result = {};
        for (const [name, version] of this._versions) {
            result[name] = version;
        }
        return result;
    }
}

/**
 * SchemaWatcher - Watch for schema file changes and hot-reload.
 *
 * Uses fs.watch for efficient file system monitoring.
 */
class SchemaWatcher {
    constructor(registry, schemaDir) {
        this.registry = registry;
        this.schemaDir = schemaDir;
        this._watcher = null;
    }

    /**
     * Start watching for changes.
     */
    start() {
        const fs = require('fs');
        const path = require('path');

        // Initial load
        this._loadAll();

        // Watch for changes
        this._watcher = fs.watch(this.schemaDir, (eventType, filename) => {
            if (filename && filename.endsWith('.bin')) {
                const name = path.basename(filename, '.bin');
                const filepath = path.join(this.schemaDir, filename);

                try {
                    const data = fs.readFileSync(filepath);
                    const version = this.registry.register(name, data);
                    console.log(`Hot-reloaded schema '${name}' -> v${version}`);
                } catch (err) {
                    console.error(`Failed to reload '${name}':`, err.message);
                }
            }
        });

        console.log(`Watching ${this.schemaDir} for schema changes...`);
    }

    /**
     * Stop watching.
     */
    stop() {
        if (this._watcher) {
            this._watcher.close();
            this._watcher = null;
        }
    }

    _loadAll() {
        const fs = require('fs');
        const path = require('path');

        try {
            const files = fs.readdirSync(this.schemaDir);
            for (const file of files) {
                if (file.endsWith('.bin')) {
                    const name = path.basename(file, '.bin');
                    const data = fs.readFileSync(path.join(this.schemaDir, file));
                    this.registry.register(name, data);
                }
            }
        } catch (err) {
            // Directory may not exist yet
        }
    }
}

/**
 * AtomicSchema - Single schema with atomic hot-swap.
 *
 * Optimized for high-throughput single-schema scenarios.
 */
class AtomicSchema {
    constructor(binarySchema) {
        this._schema = new NativeSchema(binarySchema);
        this._version = 1;
    }

    /**
     * Atomically swap to new schema.
     * @param {Buffer} binarySchema - New schema data
     */
    swap(binarySchema) {
        // Parse new schema first
        const newSchema = new NativeSchema(binarySchema);
        // Atomic swap (single JS assignment)
        this._schema = newSchema;
        this._version++;
    }

    /**
     * Decode using current schema.
     * @param {Buffer} payload - Payload bytes
     * @returns {Object} Decoded values
     */
    decode(payload) {
        return this._schema.decode(payload);
    }

    get version() {
        return this._version;
    }
}

/**
 * HTTP endpoint for remote schema updates.
 */
function createHotSwapServer(registry, port = 8080) {
    const http = require('http');

    const server = http.createServer((req, res) => {
        if (req.method === 'PUT' && req.url.startsWith('/schema/')) {
            const name = req.url.slice(8);
            let body = [];

            req.on('data', chunk => body.push(chunk));
            req.on('end', () => {
                try {
                    const data = Buffer.concat(body);
                    const version = registry.register(name, data);
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ name, version, status: 'ok' }));
                    console.log(`HTTP: Updated schema '${name}' -> v${version}`);
                } catch (err) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: err.message }));
                }
            });
        } else if (req.method === 'GET' && req.url === '/schemas') {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(registry.listSchemas()));
        } else {
            res.writeHead(404);
            res.end('Not found');
        }
    });

    server.listen(port, () => {
        console.log(`Hot-swap HTTP server on port ${port}`);
        console.log(`  PUT /schema/{name} - Update schema`);
        console.log(`  GET /schemas - List schemas`);
    });

    return server;
}

// Example usage
function main() {
    console.log('=== Node.js Hot-Swap Schema Example ===\n');

    // Create registry
    const registry = new SchemaRegistry();

    // Initial schema (v1)
    const schemaV1 = Buffer.from([
        0x01, 0x03,  // version, 3 fields
        0x00, 0x00, 0x00, 0x00,
        0x01, 0x00, 0x00, 0x00,
        0x01, 0x00, 0x00, 0x00,
    ]);

    // Register initial schema
    let v = registry.register('sensor', schemaV1);
    console.log(`Registered 'sensor' schema v${v}`);

    // Decode with v1
    const payload = Buffer.from('02012f0003', 'hex');
    let result = registry.decode('sensor', payload);
    console.log(`Decoded (v1):`, result);

    // Schema update (v2)
    const schemaV2 = Buffer.from([
        0x01, 0x04,  // version, 4 fields
        0x00, 0x00, 0x00, 0x00,
        0x01, 0x00, 0x00, 0x00,
        0x01, 0x00, 0x00, 0x00,
        0x01, 0x00, 0x00, 0x00,
    ]);

    // Hot-swap to v2
    v = registry.register('sensor', schemaV2);
    console.log(`\nHot-swapped to 'sensor' schema v${v}`);

    // Decode with v2
    result = registry.decode('sensor', payload);
    console.log(`Decoded (v2):`, result);

    console.log(`\nActive schemas:`, registry.listSchemas());

    // Atomic schema example
    console.log('\n--- AtomicSchema (single schema) ---');
    const atomic = new AtomicSchema(schemaV1);
    console.log(`Created atomic schema v${atomic.version}`);

    atomic.swap(schemaV2);
    console.log(`Swapped to v${atomic.version}`);

    // Benchmark
    console.log('\n--- Performance ---');
    const iterations = 1000000;

    let start = Date.now();
    for (let i = 0; i < iterations; i++) {
        registry.decode('sensor', payload);
    }
    const registryTime = Date.now() - start;

    start = Date.now();
    for (let i = 0; i < iterations; i++) {
        atomic.decode(payload);
    }
    const atomicTime = Date.now() - start;

    console.log(`Registry: ${registryTime}ms (${(registryTime * 1000 / iterations).toFixed(2)} µs/op)`);
    console.log(`Atomic:   ${atomicTime}ms (${(atomicTime * 1000 / iterations).toFixed(2)} µs/op)`);

    console.log('\nHot-swap complete - no restart required!');

    // Uncomment to start HTTP server for remote updates:
    // createHotSwapServer(registry, 8080);
}

main();
