#!/usr/bin/env node
/**
 * Analyze a TTN codec and generate comprehensive test vectors.
 * 
 * Usage:
 *   node analyze_codec.js <codec.js> [--output vectors.yaml]
 * 
 * This tool:
 * 1. Loads the original codec
 * 2. Generates test payloads for all code paths
 * 3. Runs them through the decoder
 * 4. Outputs test vectors in YAML format
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

// Load and execute codec in sandbox
function loadCodec(codecPath) {
    const code = fs.readFileSync(codecPath, 'utf8');
    const sandbox = {
        console: console,
        Math: Math,
        Number: Number,
        parseInt: parseInt,
        parseFloat: parseFloat,
        String: String,
        Array: Array,
        Object: Object,
        JSON: JSON,
    };
    
    vm.createContext(sandbox);
    vm.runInContext(code, sandbox);
    
    return sandbox.decodeUplink;
}

// Convert hex string to byte array
function hexToBytes(hex) {
    hex = hex.replace(/\s+/g, '');
    const bytes = [];
    for (let i = 0; i < hex.length; i += 2) {
        bytes.push(parseInt(hex.substr(i, 2), 16));
    }
    return bytes;
}

// Convert byte array to hex string
function bytesToHex(bytes) {
    return bytes.map(b => ('0' + b.toString(16)).slice(-2).toUpperCase()).join(' ');
}

// Generate test vectors for Vicki codec
function generateVickiTestVectors(decodeUplink) {
    const vectors = [];
    
    // === KEEPALIVE MESSAGES (reason 0x01, 0x51, 0x81) ===
    
    // Basic keepalive - reason 0x01
    vectors.push({
        name: 'keepalive_standard',
        description: 'Standard keepalive with reason=0x01',
        payload: '01 15 60 80 20 00 14 A4 90',
        category: 'keepalive'
    });
    
    // Keepalive with alternate temp formula - reason 0x51 (81 decimal)
    vectors.push({
        name: 'keepalive_alt_temp',
        description: 'Keepalive with alternate temperature formula (reason=0x51)',
        payload: '51 16 60 80 20 00 14 A4 90',
        category: 'keepalive'
    });
    
    // Extended keepalive - reason 0x81 (129 decimal)
    vectors.push({
        name: 'keepalive_extended',
        description: 'Extended keepalive (reason=0x81)',
        payload: '81 17 70 90 30 10 24 B4 A0',
        category: 'keepalive'
    });
    
    // Edge cases for keepalive
    vectors.push({
        name: 'keepalive_min_values',
        description: 'Keepalive with minimum values',
        payload: '01 00 00 00 00 00 00 00 00',
        category: 'keepalive'
    });
    
    vectors.push({
        name: 'keepalive_max_values',
        description: 'Keepalive with maximum values (0xFF)',
        payload: '01 FF FF FF FF FF FF FF FF',
        category: 'keepalive'
    });
    
    vectors.push({
        name: 'keepalive_motor_range_zero',
        description: 'Keepalive with motorRange=0 (valve openness edge case)',
        payload: '01 15 60 80 FF 00 F0 A4 90',
        category: 'keepalive'
    });
    
    // === COMMAND RESPONSES ===
    // Format: [command bytes...] + [9-byte keepalive suffix]
    
    const keepaliveSuffix = '01 15 60 80 20 00 14 A4 90';
    
    // Command 0x04 - Device versions (2 bytes: hw, sw)
    vectors.push({
        name: 'cmd_device_versions',
        description: 'Command 0x04: Device hardware/software versions',
        payload: '04 02 05 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x12 - Keep alive time (1 byte)
    vectors.push({
        name: 'cmd_keepalive_time',
        description: 'Command 0x12: Keep alive time setting',
        payload: '12 3C ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x13 - Open window params (4 bytes)
    vectors.push({
        name: 'cmd_open_window_params',
        description: 'Command 0x13: Open window detection parameters',
        payload: '13 01 06 20 15 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x14 - Child lock (1 byte)
    vectors.push({
        name: 'cmd_child_lock',
        description: 'Command 0x14: Child lock status',
        payload: '14 01 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x15 - Temperature range settings (2 bytes: min, max)
    vectors.push({
        name: 'cmd_temp_range',
        description: 'Command 0x15: Temperature range settings',
        payload: '15 05 1E ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x16 - Internal algo params (3 bytes)
    vectors.push({
        name: 'cmd_internal_algo_params',
        description: 'Command 0x16: Internal algorithm parameters',
        payload: '16 0A 14 1E ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x17 - Internal algo Tdiff params (2 bytes)
    vectors.push({
        name: 'cmd_tdiff_params',
        description: 'Command 0x17: Temperature difference parameters',
        payload: '17 02 03 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x18 - Operational mode (1 byte)
    vectors.push({
        name: 'cmd_operational_mode',
        description: 'Command 0x18: Operational mode',
        payload: '18 02 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x19 - Join retry period (1 byte)
    vectors.push({
        name: 'cmd_join_retry_period',
        description: 'Command 0x19: Join retry period',
        payload: '19 18 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x1b - Uplink type (1 byte)
    vectors.push({
        name: 'cmd_uplink_type',
        description: 'Command 0x1b: Uplink type setting',
        payload: '1B 01 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x1d - Watchdog params (2 bytes)
    vectors.push({
        name: 'cmd_watchdog_params',
        description: 'Command 0x1d: Watchdog parameters',
        payload: '1D 05 0A ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x1f - Primary operational mode (1 byte)
    vectors.push({
        name: 'cmd_primary_op_mode',
        description: 'Command 0x1f: Primary operational mode',
        payload: '1F 01 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x21 - Battery ranges boundaries (6 bytes)
    vectors.push({
        name: 'cmd_battery_boundaries',
        description: 'Command 0x21: Battery voltage range boundaries',
        payload: '21 0B B8 0C 1C 0C 80 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x23 - Battery ranges over voltage (4 bytes)
    vectors.push({
        name: 'cmd_battery_overvoltage',
        description: 'Command 0x23: Battery over-voltage ranges',
        payload: '23 00 0A 14 1E ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x27 - OVAC (1 byte)
    vectors.push({
        name: 'cmd_ovac',
        description: 'Command 0x27: OVAC setting',
        payload: '27 05 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x28 - Manual target temperature update (1 byte)
    vectors.push({
        name: 'cmd_manual_temp_update',
        description: 'Command 0x28: Manual target temperature update flag',
        payload: '28 01 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x29 - Proportional algo params (2 bytes)
    vectors.push({
        name: 'cmd_proportional_algo',
        description: 'Command 0x29: Proportional algorithm parameters',
        payload: '29 0A 3C ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x2b - Algo type (1 byte)
    vectors.push({
        name: 'cmd_algo_type',
        description: 'Command 0x2b: Algorithm type',
        payload: '2B 02 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x36 - Proportional gain Kp (3 bytes)
    vectors.push({
        name: 'cmd_proportional_gain',
        description: 'Command 0x36: Proportional gain (Kp)',
        payload: '36 01 00 00 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x3d - Integral gain Ki (3 bytes)
    vectors.push({
        name: 'cmd_integral_gain',
        description: 'Command 0x3d: Integral gain (Ki)',
        payload: '3D 00 80 00 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x3f - Integral value (2 bytes)
    vectors.push({
        name: 'cmd_integral_value',
        description: 'Command 0x3f: Integral value',
        payload: '3F 00 64 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x40 - PI run period (1 byte)
    vectors.push({
        name: 'cmd_pi_run_period',
        description: 'Command 0x40: PI controller run period',
        payload: '40 0A ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x42 - Temperature hysteresis (1 byte)
    vectors.push({
        name: 'cmd_temp_hysteresis',
        description: 'Command 0x42: Temperature hysteresis',
        payload: '42 05 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x44 - External sensor temperature (2 bytes)
    vectors.push({
        name: 'cmd_ext_sensor_temp',
        description: 'Command 0x44: External sensor temperature',
        payload: '44 00 E6 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x46 - Open window params v2 (3 bytes)
    vectors.push({
        name: 'cmd_open_window_v2',
        description: 'Command 0x46: Open window parameters v2',
        payload: '46 01 06 14 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x48 - Force attach (1 byte)
    vectors.push({
        name: 'cmd_force_attach',
        description: 'Command 0x48: Force attach setting',
        payload: '48 01 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x4a - Anti-freeze params (3 bytes)
    vectors.push({
        name: 'cmd_antifreeze_params',
        description: 'Command 0x4a: Anti-freeze protection parameters',
        payload: '4A 32 50 07 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x4d - PI max integrated error (2 bytes)
    vectors.push({
        name: 'cmd_pi_max_error',
        description: 'Command 0x4d: PI controller max integrated error',
        payload: '4D 01 F4 ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x50 - Effective motor range (2 bytes)
    vectors.push({
        name: 'cmd_effective_motor_range',
        description: 'Command 0x50: Effective motor range (valve openness limits)',
        payload: '50 0A 5A ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x52 - Target temperature float (2 bytes)
    vectors.push({
        name: 'cmd_target_temp_float',
        description: 'Command 0x52: Target temperature with decimal precision',
        payload: '52 00 DC ' + keepaliveSuffix,
        category: 'command'
    });
    
    // Command 0x54 - Temperature offset (1 byte)
    vectors.push({
        name: 'cmd_temp_offset',
        description: 'Command 0x54: Temperature sensor offset',
        payload: '54 1C ' + keepaliveSuffix,
        category: 'command'
    });
    
    // === MULTIPLE COMMANDS IN ONE MESSAGE ===
    vectors.push({
        name: 'multi_cmd_versions_and_mode',
        description: 'Multiple commands: device versions + operational mode',
        payload: '04 02 05 18 02 ' + keepaliveSuffix,
        category: 'multi_command'
    });
    
    vectors.push({
        name: 'multi_cmd_temp_settings',
        description: 'Multiple commands: temp range + hysteresis + target float',
        payload: '15 05 1E 42 05 52 00 DC ' + keepaliveSuffix,
        category: 'multi_command'
    });
    
    return vectors;
}

// Run vectors through codec and capture output
function runVectors(decodeUplink, vectors) {
    const results = [];
    
    for (const vector of vectors) {
        const bytes = hexToBytes(vector.payload);
        try {
            const result = decodeUplink({ bytes: bytes, fPort: 2 });
            results.push({
                name: vector.name,
                description: vector.description,
                category: vector.category,
                payload: vector.payload,
                expected: result.data,
                warnings: result.warnings || [],
                errors: result.errors || []
            });
        } catch (e) {
            results.push({
                name: vector.name,
                description: vector.description,
                category: vector.category,
                payload: vector.payload,
                error: e.message
            });
        }
    }
    
    return results;
}

// Format results as YAML
function formatAsYaml(results) {
    let yaml = 'test_vectors:\n';
    
    for (const r of results) {
        yaml += `  - name: ${r.name}\n`;
        yaml += `    description: "${r.description}"\n`;
        yaml += `    payload: "${r.payload}"\n`;
        
        if (r.error) {
            yaml += `    # ERROR: ${r.error}\n`;
            continue;
        }
        
        yaml += '    expected:\n';
        for (const [key, value] of Object.entries(r.expected)) {
            if (typeof value === 'object' && value !== null) {
                yaml += `      ${key}:\n`;
                for (const [k2, v2] of Object.entries(value)) {
                    if (typeof v2 === 'object' && v2 !== null) {
                        yaml += `        ${k2}:\n`;
                        for (const [k3, v3] of Object.entries(v2)) {
                            yaml += `          ${k3}: ${formatValue(v3)}\n`;
                        }
                    } else {
                        yaml += `        ${k2}: ${formatValue(v2)}\n`;
                    }
                }
            } else {
                yaml += `      ${key}: ${formatValue(value)}\n`;
            }
        }
        yaml += '\n';
    }
    
    return yaml;
}

function formatValue(v) {
    if (typeof v === 'boolean') return v;
    if (typeof v === 'string') return `"${v}"`;
    if (typeof v === 'number') {
        if (Number.isInteger(v)) return v;
        return v;
    }
    return JSON.stringify(v);
}

// Main
function main() {
    const args = process.argv.slice(2);
    if (args.length < 1) {
        console.error('Usage: node analyze_codec.js <codec.js> [--output vectors.yaml]');
        process.exit(1);
    }
    
    const codecPath = args[0];
    let outputPath = null;
    
    if (args.includes('--output') && args.indexOf('--output') + 1 < args.length) {
        outputPath = args[args.indexOf('--output') + 1];
    }
    
    console.error(`Loading codec: ${codecPath}`);
    const decodeUplink = loadCodec(codecPath);
    
    console.error('Generating test vectors...');
    const vectors = generateVickiTestVectors(decodeUplink);
    
    console.error(`Running ${vectors.length} test vectors...`);
    const results = runVectors(decodeUplink, vectors);
    
    const yaml = formatAsYaml(results);
    
    if (outputPath) {
        fs.writeFileSync(outputPath, yaml);
        console.error(`Written to: ${outputPath}`);
    } else {
        console.log(yaml);
    }
    
    // Summary
    const errors = results.filter(r => r.error);
    console.error(`\nSummary: ${results.length} vectors, ${errors.length} errors`);
    if (errors.length > 0) {
        console.error('Errors:');
        for (const e of errors) {
            console.error(`  ${e.name}: ${e.error}`);
        }
    }
}

main();
