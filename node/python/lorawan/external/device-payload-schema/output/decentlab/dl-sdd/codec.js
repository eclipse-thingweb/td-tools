// TS013 Payload Codec — decentlab_dl_sdd
// Schema version: 2
// Generated from: dl-sdd.yaml
// DO NOT EDIT — regenerate from schema

// --- Binary helpers ---
function readU(buf, pos, size, endian) {
  var v = 0;
  if (endian === 'big') {
    for (var i = 0; i < size; i++) v = (v * 256) + (buf[pos + i] || 0);
  } else {
    for (var i = size - 1; i >= 0; i--) v = (v * 256) + (buf[pos + i] || 0);
  }
  return v;
}

function readS(buf, pos, size, endian) {
  var v = readU(buf, pos, size, endian);
  var sign = 1 << (size * 8 - 1);
  if (v >= sign) v -= sign * 2;
  return v;
}

function readF32(buf, pos, endian) {
  var b = buf.slice(pos, pos + 4);
  if (endian === 'little') b = [b[3], b[2], b[1], b[0]];
  var ab = new ArrayBuffer(4);
  var dv = new DataView(ab);
  for (var i = 0; i < 4; i++) dv.setUint8(i, b[i] || 0);
  return dv.getFloat32(0, false);
}

function readF64(buf, pos, endian) {
  var b = buf.slice(pos, pos + 8);
  if (endian === 'little') b = [b[7], b[6], b[5], b[4], b[3], b[2], b[1], b[0]];
  var ab = new ArrayBuffer(8);
  var dv = new DataView(ab);
  for (var i = 0; i < 8; i++) dv.setUint8(i, b[i] || 0);
  return dv.getFloat64(0, false);
}

function writeU(buf, pos, size, value, endian) {
  value = Math.round(value) >>> 0;
  if (endian === 'big') {
    for (var i = size - 1; i >= 0; i--) { buf[pos + i] = value & 0xFF; value = (value >>> 8); }
  } else {
    for (var i = 0; i < size; i++) { buf[pos + i] = value & 0xFF; value = (value >>> 8); }
  }
}

function writeS(buf, pos, size, value, endian) {
  if (value < 0) value += (1 << (size * 8));
  writeU(buf, pos, size, value, endian);
}

function decodePayload(buf, endian) {
  var pos = 0, d = {}, vars = {};
  endian = endian || "big";
    var protocol_version = readU(buf, pos, 1, endian);
    pos += 1;
    vars.protocol_version = protocol_version;
    d.protocol_version = protocol_version;
    var device_id = readU(buf, pos, 2, endian);
    pos += 2;
    vars.device_id = device_id;
    d.device_id = device_id;
    var flags = readU(buf, pos, 2, endian);
    pos += 2;
    vars.flags = flags;
    d.flags = flags;
    // flagged on flags
    if (vars.flags & (1 << 0)) {
      var moisture_at_level_0 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.moisture_at_level_0 = moisture_at_level_0;
      d.moisture_at_level_0 = (moisture_at_level_0 / 100);
      var moisture_at_level_1 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.moisture_at_level_1 = moisture_at_level_1;
      d.moisture_at_level_1 = (moisture_at_level_1 / 100);
      var moisture_at_level_2 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.moisture_at_level_2 = moisture_at_level_2;
      d.moisture_at_level_2 = (moisture_at_level_2 / 100);
      var moisture_at_level_3 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.moisture_at_level_3 = moisture_at_level_3;
      d.moisture_at_level_3 = (moisture_at_level_3 / 100);
      var moisture_at_level_4 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.moisture_at_level_4 = moisture_at_level_4;
      d.moisture_at_level_4 = (moisture_at_level_4 / 100);
      var moisture_at_level_5 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.moisture_at_level_5 = moisture_at_level_5;
      d.moisture_at_level_5 = (moisture_at_level_5 / 100);
      var temperature_at_level_0 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.temperature_at_level_0 = temperature_at_level_0;
      d.temperature_at_level_0 = (temperature_at_level_0 / 100);
      var temperature_at_level_1 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.temperature_at_level_1 = temperature_at_level_1;
      d.temperature_at_level_1 = (temperature_at_level_1 / 100);
      var temperature_at_level_2 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.temperature_at_level_2 = temperature_at_level_2;
      d.temperature_at_level_2 = (temperature_at_level_2 / 100);
      var temperature_at_level_3 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.temperature_at_level_3 = temperature_at_level_3;
      d.temperature_at_level_3 = (temperature_at_level_3 / 100);
      var temperature_at_level_4 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.temperature_at_level_4 = temperature_at_level_4;
      d.temperature_at_level_4 = (temperature_at_level_4 / 100);
      var temperature_at_level_5 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.temperature_at_level_5 = temperature_at_level_5;
      d.temperature_at_level_5 = (temperature_at_level_5 / 100);
      var salinity_at_level_0 = readU(buf, pos, 2, endian);
      pos += 2;
      vars.salinity_at_level_0 = salinity_at_level_0;
      d.salinity_at_level_0 = (salinity_at_level_0 + -100);
      var salinity_at_level_1 = readU(buf, pos, 2, endian);
      pos += 2;
      vars.salinity_at_level_1 = salinity_at_level_1;
      d.salinity_at_level_1 = (salinity_at_level_1 + -100);
      var salinity_at_level_2 = readU(buf, pos, 2, endian);
      pos += 2;
      vars.salinity_at_level_2 = salinity_at_level_2;
      d.salinity_at_level_2 = (salinity_at_level_2 + -100);
      var salinity_at_level_3 = readU(buf, pos, 2, endian);
      pos += 2;
      vars.salinity_at_level_3 = salinity_at_level_3;
      d.salinity_at_level_3 = (salinity_at_level_3 + -100);
      var salinity_at_level_4 = readU(buf, pos, 2, endian);
      pos += 2;
      vars.salinity_at_level_4 = salinity_at_level_4;
      d.salinity_at_level_4 = (salinity_at_level_4 + -100);
      var salinity_at_level_5 = readU(buf, pos, 2, endian);
      pos += 2;
      vars.salinity_at_level_5 = salinity_at_level_5;
      d.salinity_at_level_5 = (salinity_at_level_5 + -100);
    }
    if (vars.flags & (1 << 1)) {
      var moisture_at_level_6 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.moisture_at_level_6 = moisture_at_level_6;
      d.moisture_at_level_6 = (moisture_at_level_6 / 100);
      var moisture_at_level_7 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.moisture_at_level_7 = moisture_at_level_7;
      d.moisture_at_level_7 = (moisture_at_level_7 / 100);
      var moisture_at_level_8 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.moisture_at_level_8 = moisture_at_level_8;
      d.moisture_at_level_8 = (moisture_at_level_8 / 100);
      var moisture_at_level_9 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.moisture_at_level_9 = moisture_at_level_9;
      d.moisture_at_level_9 = (moisture_at_level_9 / 100);
      var moisture_at_level_10 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.moisture_at_level_10 = moisture_at_level_10;
      d.moisture_at_level_10 = (moisture_at_level_10 / 100);
      var moisture_at_level_11 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.moisture_at_level_11 = moisture_at_level_11;
      d.moisture_at_level_11 = (moisture_at_level_11 / 100);
      var temperature_at_level_6 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.temperature_at_level_6 = temperature_at_level_6;
      d.temperature_at_level_6 = (temperature_at_level_6 / 100);
      var temperature_at_level_7 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.temperature_at_level_7 = temperature_at_level_7;
      d.temperature_at_level_7 = (temperature_at_level_7 / 100);
      var temperature_at_level_8 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.temperature_at_level_8 = temperature_at_level_8;
      d.temperature_at_level_8 = (temperature_at_level_8 / 100);
      var temperature_at_level_9 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.temperature_at_level_9 = temperature_at_level_9;
      d.temperature_at_level_9 = (temperature_at_level_9 / 100);
      var temperature_at_level_10 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.temperature_at_level_10 = temperature_at_level_10;
      d.temperature_at_level_10 = (temperature_at_level_10 / 100);
      var temperature_at_level_11 = readS(buf, pos, 2, endian);
      pos += 2;
      vars.temperature_at_level_11 = temperature_at_level_11;
      d.temperature_at_level_11 = (temperature_at_level_11 / 100);
      var salinity_at_level_6 = readU(buf, pos, 2, endian);
      pos += 2;
      vars.salinity_at_level_6 = salinity_at_level_6;
      d.salinity_at_level_6 = (salinity_at_level_6 + -100);
      var salinity_at_level_7 = readU(buf, pos, 2, endian);
      pos += 2;
      vars.salinity_at_level_7 = salinity_at_level_7;
      d.salinity_at_level_7 = (salinity_at_level_7 + -100);
      var salinity_at_level_8 = readU(buf, pos, 2, endian);
      pos += 2;
      vars.salinity_at_level_8 = salinity_at_level_8;
      d.salinity_at_level_8 = (salinity_at_level_8 + -100);
      var salinity_at_level_9 = readU(buf, pos, 2, endian);
      pos += 2;
      vars.salinity_at_level_9 = salinity_at_level_9;
      d.salinity_at_level_9 = (salinity_at_level_9 + -100);
      var salinity_at_level_10 = readU(buf, pos, 2, endian);
      pos += 2;
      vars.salinity_at_level_10 = salinity_at_level_10;
      d.salinity_at_level_10 = (salinity_at_level_10 + -100);
      var salinity_at_level_11 = readU(buf, pos, 2, endian);
      pos += 2;
      vars.salinity_at_level_11 = salinity_at_level_11;
      d.salinity_at_level_11 = (salinity_at_level_11 + -100);
    }
    if (vars.flags & (1 << 2)) {
      var battery_voltage = readU(buf, pos, 2, endian);
      pos += 2;
      vars.battery_voltage = battery_voltage;
      d.battery_voltage = (battery_voltage / 1000);
    }
  return { data: d, pos: pos };
}

function encodePayload(d, endian) {
  var buf = new Array(256);
  var pos = 0;
  endian = endian || "big";
    writeU(buf, pos, 1, Math.round((d.protocol_version !== undefined ? d.protocol_version : 0)), endian);
    pos += 1;
    writeU(buf, pos, 2, Math.round((d.device_id !== undefined ? d.device_id : 0)), endian);
    pos += 2;
    writeU(buf, pos, 2, Math.round((d.flags !== undefined ? d.flags : 0)), endian);
    pos += 2;
    // encode flagged
    var _flags = 0;
    if (d.moisture_at_level_0 !== undefined || d.moisture_at_level_1 !== undefined || d.moisture_at_level_2 !== undefined || d.moisture_at_level_3 !== undefined || d.moisture_at_level_4 !== undefined || d.moisture_at_level_5 !== undefined || d.temperature_at_level_0 !== undefined || d.temperature_at_level_1 !== undefined || d.temperature_at_level_2 !== undefined || d.temperature_at_level_3 !== undefined || d.temperature_at_level_4 !== undefined || d.temperature_at_level_5 !== undefined || d.salinity_at_level_0 !== undefined || d.salinity_at_level_1 !== undefined || d.salinity_at_level_2 !== undefined || d.salinity_at_level_3 !== undefined || d.salinity_at_level_4 !== undefined || d.salinity_at_level_5 !== undefined) _flags |= (1 << 0);
    if (d.moisture_at_level_6 !== undefined || d.moisture_at_level_7 !== undefined || d.moisture_at_level_8 !== undefined || d.moisture_at_level_9 !== undefined || d.moisture_at_level_10 !== undefined || d.moisture_at_level_11 !== undefined || d.temperature_at_level_6 !== undefined || d.temperature_at_level_7 !== undefined || d.temperature_at_level_8 !== undefined || d.temperature_at_level_9 !== undefined || d.temperature_at_level_10 !== undefined || d.temperature_at_level_11 !== undefined || d.salinity_at_level_6 !== undefined || d.salinity_at_level_7 !== undefined || d.salinity_at_level_8 !== undefined || d.salinity_at_level_9 !== undefined || d.salinity_at_level_10 !== undefined || d.salinity_at_level_11 !== undefined) _flags |= (1 << 1);
    if (d.battery_voltage !== undefined) _flags |= (1 << 2);
    writeU(buf, pos - 2, 2, _flags, endian);
    if (_flags & (1 << 0)) {
      writeS(buf, pos, 2, Math.round(((d.moisture_at_level_0 !== undefined ? d.moisture_at_level_0 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.moisture_at_level_1 !== undefined ? d.moisture_at_level_1 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.moisture_at_level_2 !== undefined ? d.moisture_at_level_2 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.moisture_at_level_3 !== undefined ? d.moisture_at_level_3 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.moisture_at_level_4 !== undefined ? d.moisture_at_level_4 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.moisture_at_level_5 !== undefined ? d.moisture_at_level_5 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.temperature_at_level_0 !== undefined ? d.temperature_at_level_0 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.temperature_at_level_1 !== undefined ? d.temperature_at_level_1 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.temperature_at_level_2 !== undefined ? d.temperature_at_level_2 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.temperature_at_level_3 !== undefined ? d.temperature_at_level_3 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.temperature_at_level_4 !== undefined ? d.temperature_at_level_4 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.temperature_at_level_5 !== undefined ? d.temperature_at_level_5 : 0) * 100)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round(((d.salinity_at_level_0 !== undefined ? d.salinity_at_level_0 : 0) - (-100))), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round(((d.salinity_at_level_1 !== undefined ? d.salinity_at_level_1 : 0) - (-100))), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round(((d.salinity_at_level_2 !== undefined ? d.salinity_at_level_2 : 0) - (-100))), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round(((d.salinity_at_level_3 !== undefined ? d.salinity_at_level_3 : 0) - (-100))), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round(((d.salinity_at_level_4 !== undefined ? d.salinity_at_level_4 : 0) - (-100))), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round(((d.salinity_at_level_5 !== undefined ? d.salinity_at_level_5 : 0) - (-100))), endian);
      pos += 2;
    }
    if (_flags & (1 << 1)) {
      writeS(buf, pos, 2, Math.round(((d.moisture_at_level_6 !== undefined ? d.moisture_at_level_6 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.moisture_at_level_7 !== undefined ? d.moisture_at_level_7 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.moisture_at_level_8 !== undefined ? d.moisture_at_level_8 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.moisture_at_level_9 !== undefined ? d.moisture_at_level_9 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.moisture_at_level_10 !== undefined ? d.moisture_at_level_10 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.moisture_at_level_11 !== undefined ? d.moisture_at_level_11 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.temperature_at_level_6 !== undefined ? d.temperature_at_level_6 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.temperature_at_level_7 !== undefined ? d.temperature_at_level_7 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.temperature_at_level_8 !== undefined ? d.temperature_at_level_8 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.temperature_at_level_9 !== undefined ? d.temperature_at_level_9 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.temperature_at_level_10 !== undefined ? d.temperature_at_level_10 : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.temperature_at_level_11 !== undefined ? d.temperature_at_level_11 : 0) * 100)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round(((d.salinity_at_level_6 !== undefined ? d.salinity_at_level_6 : 0) - (-100))), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round(((d.salinity_at_level_7 !== undefined ? d.salinity_at_level_7 : 0) - (-100))), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round(((d.salinity_at_level_8 !== undefined ? d.salinity_at_level_8 : 0) - (-100))), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round(((d.salinity_at_level_9 !== undefined ? d.salinity_at_level_9 : 0) - (-100))), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round(((d.salinity_at_level_10 !== undefined ? d.salinity_at_level_10 : 0) - (-100))), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round(((d.salinity_at_level_11 !== undefined ? d.salinity_at_level_11 : 0) - (-100))), endian);
      pos += 2;
    }
    if (_flags & (1 << 2)) {
      writeU(buf, pos, 2, Math.round(((d.battery_voltage !== undefined ? d.battery_voltage : 0) * 1000)), endian);
      pos += 2;
    }
  return buf.slice(0, pos);
}

function decodeUplink(input) {
  try {
    var r = decodePayload(input.bytes, "big");
    return { data: r.data, warnings: [], errors: [] };
  } catch (e) {
    return { data: {}, warnings: [], errors: [e.message] };
  }
}

function decodeDownlink(input) {
  return decodeUplink(input);
}

function encodeDownlink(input) {
  try {
    var bytes = encodePayload(input.data, "big");
    return { bytes: bytes, fPort: 1, warnings: [], errors: [] };
  } catch (e) {
    return { bytes: [], fPort: 1, warnings: [], errors: [e.message] };
  }
}