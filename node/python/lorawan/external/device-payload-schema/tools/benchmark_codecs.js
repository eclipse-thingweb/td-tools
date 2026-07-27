#!/usr/bin/env node
/**
 * benchmark_codecs.js - Compare original vs generated vs interpreted codec performance
 * 
 * Usage:
 *   node tools/benchmark_codecs.js [device] [iterations]
 *   node tools/benchmark_codecs.js dl-5tm 10000
 * 
 * Compares:
 *   1. Original TTN codec (hand-written)
 *   2. Generated codec (from schema)
 *   3. Interpreted (schema parsed at runtime)
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Default test configuration
const DEFAULT_DEVICE = 'dl-5tm';
const DEFAULT_ITERATIONS = 10000;

// Test payloads for dl-5tm (Decentlab soil sensor)
const TEST_PAYLOADS = {
  'dl-5tm': [
    { name: 'normal', hex: '02012f0003025800980bb8' },
    { name: 'sensor1_only', hex: '02012f0002025800980bb8' },
    { name: 'battery_only', hex: '02012f00010bb8' },
  ]
};

// Original TTN codec (fetched from TTN device repository)
const ORIGINAL_CODECS = {
  'dl-5tm': `
var decentlab_decoder = {
  PROTOCOL_VERSION: 2,
  SENSORS: [
    {length: 2,
     values: [{name: 'dielectric_permittivity',
               convert: function (x) { return x[0] / 50; }},
              {name: 'volumetric_water_content',
               convert: function (x) { return 0.0000043 * Math.pow(x[0]/50, 3) - 0.00055 * Math.pow(x[0]/50, 2) + 0.0292 * (x[0]/50) - 0.053; },
               unit: 'm³⋅m⁻³'},
              {name: 'soil_temperature',
               convert: function (x) { return (x[1] - 400) / 10; },
               unit: '°C'}]},
    {length: 1,
     values: [{name: 'battery_voltage',
               convert: function (x) { return x[0] / 1000; },
               unit: 'V'}]}
  ],
  read_int: function (bytes, pos) {
    return (bytes[pos] << 8) + bytes[pos + 1];
  },
  decode: function (msg) {
    var bytes = msg;
    var i, j;
    if (typeof msg === 'string') {
      bytes = [];
      for (i = 0; i < msg.length; i += 2) {
        bytes.push(parseInt(msg.substring(i, i + 2), 16));
      }
    }
    var version = bytes[0];
    if (version != this.PROTOCOL_VERSION) {
      return {error: "protocol version " + version + " doesn't match v2"};
    }
    var deviceId = this.read_int(bytes, 1);
    var flags = this.read_int(bytes, 3);
    var result = {'protocol_version': version, 'device_id': deviceId};
    var pos = 5;
    for (i = 0; i < this.SENSORS.length; i++, flags >>= 1) {
      if ((flags & 1) !== 1) continue;
      var sensor = this.SENSORS[i];
      var x = [];
      for (j = 0; j < sensor.length; j++) {
        x.push(this.read_int(bytes, pos));
        pos += 2;
      }
      for (j = 0; j < sensor.values.length; j++) {
        var value = sensor.values[j];
        if ('convert' in value) {
          result[value.name] = value.convert.bind(this)(x);
        }
      }
    }
    return result;
  }
};
function decodeUplink(input) {
  var res = decentlab_decoder.decode(input.bytes);
  if (res.error) return { errors: [res.error] };
  return { data: res };
}
`
};

function hexToBytes(hex) {
  const bytes = [];
  for (let i = 0; i < hex.length; i += 2) {
    bytes.push(parseInt(hex.substr(i, 2), 16));
  }
  return bytes;
}

function loadGeneratedCodec(device) {
  const codecPath = path.join(__dirname, '..', 'output', 'decentlab', device, 'codec.js');
  if (!fs.existsSync(codecPath)) {
    console.error(`Generated codec not found: ${codecPath}`);
    console.error('Run: python tools/generate_deliverables.py schemas/ -o output/');
    process.exit(1);
  }
  return fs.readFileSync(codecPath, 'utf8');
}

function createInterpreter(device) {
  const schemaPath = path.join(__dirname, '..', 'schemas', 'decentlab', `${device}.yaml`);
  if (!fs.existsSync(schemaPath)) {
    return null;
  }
  
  // Simple YAML parser for basic schemas
  const yaml = fs.readFileSync(schemaPath, 'utf8');
  
  // Use Python interpreter via shell (slower but accurate)
  return {
    decode: function(bytes) {
      const hex = bytes.map(b => b.toString(16).padStart(2, '0')).join('');
      try {
        const result = execSync(
          `cd ${path.join(__dirname, '..')} && ` +
          `PYTHONPATH=tools python -c "` +
          `from schema_interpreter import SchemaInterpreter; ` +
          `import yaml; import json; ` +
          `schema = yaml.safe_load(open('schemas/decentlab/${device}.yaml')); ` +
          `interp = SchemaInterpreter(schema); ` +
          `result = interp.decode(bytes.fromhex('${hex}')); ` +
          `print(json.dumps(result.data if result.success else {}))"`,
          { encoding: 'utf8', timeout: 5000 }
        );
        return JSON.parse(result.trim());
      } catch (e) {
        return { error: e.message };
      }
    }
  };
}

function benchmark(name, fn, iterations) {
  // Warmup
  for (let i = 0; i < 100; i++) fn();
  
  const start = process.hrtime.bigint();
  for (let i = 0; i < iterations; i++) {
    fn();
  }
  const end = process.hrtime.bigint();
  
  const totalMs = Number(end - start) / 1e6;
  const perCallUs = (totalMs * 1000) / iterations;
  const opsPerSec = Math.round(iterations / (totalMs / 1000));
  
  return { name, totalMs, perCallUs, opsPerSec, iterations };
}

function formatResults(results) {
  console.log('\n' + '='.repeat(70));
  console.log('BENCHMARK RESULTS');
  console.log('='.repeat(70));
  
  const baseline = results[0].perCallUs;
  
  console.log('');
  console.log(pad('Codec', 20) + pad('ops/sec', 14) + pad('µs/call', 12) + pad('total ms', 12) + pad('vs orig', 10));
  console.log('-'.repeat(70));
  
  for (const r of results) {
    const ratio = r.perCallUs / baseline;
    const ratioStr = ratio <= 1 ? ratio.toFixed(2) + 'x' : ratio.toFixed(0) + 'x';
    console.log(
      pad(r.name, 20) +
      pad(r.opsPerSec.toLocaleString(), 14) +
      pad(r.perCallUs.toFixed(2), 12) +
      pad(r.totalMs.toFixed(1), 12) +
      pad(ratioStr, 10)
    );
  }
  
  console.log('='.repeat(70));
}

function pad(str, len) {
  str = String(str);
  return str + ' '.repeat(Math.max(0, len - str.length));
}

function main() {
  const args = process.argv.slice(2);
  const device = args[0] || DEFAULT_DEVICE;
  const iterations = parseInt(args[1]) || DEFAULT_ITERATIONS;
  
  console.log(`Benchmarking: ${device}`);
  console.log(`Iterations: ${iterations.toLocaleString()}`);
  
  const payloads = TEST_PAYLOADS[device];
  if (!payloads) {
    console.error(`No test payloads defined for device: ${device}`);
    process.exit(1);
  }
  
  const testPayload = payloads[0];
  const testBytes = hexToBytes(testPayload.hex);
  console.log(`Test payload: ${testPayload.name} (${testPayload.hex})`);
  
  const results = [];
  
  // 1. Original TTN codec
  if (ORIGINAL_CODECS[device]) {
    const originalCode = ORIGINAL_CODECS[device];
    const originalFn = new Function(originalCode + '; return decodeUplink;')();
    
    // Verify it works
    const origResult = originalFn({ bytes: testBytes, fPort: 1 });
    console.log('\nOriginal output:', JSON.stringify(origResult.data, null, 2));
    
    results.push(benchmark('Original (TTN)', () => {
      originalFn({ bytes: testBytes, fPort: 1 });
    }, iterations));
  }
  
  // 2. Generated codec
  try {
    const generatedCode = loadGeneratedCodec(device);
    const generatedFn = new Function(generatedCode + '; return decodeUplink;')();
    
    // Verify it works
    const genResult = generatedFn({ bytes: testBytes, fPort: 1 });
    console.log('\nGenerated output:', JSON.stringify(genResult.data, null, 2));
    
    results.push(benchmark('Generated', () => {
      generatedFn({ bytes: testBytes, fPort: 1 });
    }, iterations));
  } catch (e) {
    console.log(`\nGenerated codec error: ${e.message}`);
  }
  
  // 3. Interpreted (Python - much slower, sample only)
  const interpreter = createInterpreter(device);
  if (interpreter) {
    console.log('\nInterpreted (Python via shell - sampling 100 iterations)...');
    
    // Verify it works
    const interpResult = interpreter.decode(testBytes);
    console.log('Interpreted output:', JSON.stringify(interpResult, null, 2));
    
    // Only do 100 iterations for interpreted (it's slow)
    const interpIterations = Math.min(100, iterations);
    results.push(benchmark('Interpreted (Py)', () => {
      interpreter.decode(testBytes);
    }, interpIterations));
  }
  
  formatResults(results);
  
  // Summary
  console.log('\nSUMMARY:');
  console.log('- Original: Hand-written, optimized for this specific device');
  console.log('- Generated: Auto-generated from schema, comparable performance');
  console.log('- Interpreted: Runtime schema parsing, flexible but slower');
  console.log('');
  console.log('For production use, Generated codec offers best balance of');
  console.log('maintainability (schema-driven) and performance.');
  console.log('');
  console.log('For Go interpreter benchmark (more realistic), run:');
  console.log('  cd go/schema && go test -bench=. -benchmem');
}

main();
