// TS013 Payload Codec — rakwireless_qingping
// Schema version: 1
// Generated from: rakwireless-qingping.yaml
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
    var device_address = readU(buf, pos, 1, endian);
    pos += 1;
    vars.device_address = device_address;
    d.device_address = device_address;
    var function_code = readU(buf, pos, 1, endian);
    pos += 1;
    vars.function_code = function_code;
    d.function_code = function_code;
    var data_length = readU(buf, pos, 1, endian);
    pos += 1;
    vars.data_length = data_length;
    d.data_length = data_length;
    var data_type = readU(buf, pos, 1, endian);
    pos += 1;
    vars.data_type = data_type;
    d.data_type = data_type;
    var timestamp = readU(buf, pos, 4, endian);
    pos += 4;
    vars.timestamp = timestamp;
    d.timestamp = timestamp;
    // byte_group
    var bgStart = pos;
    var bgVal = readU(buf, pos, 3, endian);
    var _temp_raw = (bgVal >> 4) & 0xFFFFF;
    vars._temp_raw = _temp_raw;
    var _humi_raw = (bgVal >> 0) & 0xFFF;
    vars._humi_raw = _humi_raw;
    pos = bgStart + 3;
    var co2 = readU(buf, pos, 2, endian);
    pos += 2;
    vars.co2 = co2;
    d.co2 = co2;
    var battery = readU(buf, pos, 1, endian);
    pos += 1;
    vars.battery = battery;
    d.battery = battery;
  return { data: d, pos: pos };
}

function encodePayload(d, endian) {
  var buf = new Array(256);
  var pos = 0;
  endian = endian || "big";
    writeU(buf, pos, 1, Math.round((d.device_address !== undefined ? d.device_address : 0)), endian);
    pos += 1;
    writeU(buf, pos, 1, Math.round((d.function_code !== undefined ? d.function_code : 0)), endian);
    pos += 1;
    writeU(buf, pos, 1, Math.round((d.data_length !== undefined ? d.data_length : 0)), endian);
    pos += 1;
    writeU(buf, pos, 1, Math.round((d.data_type !== undefined ? d.data_type : 0)), endian);
    pos += 1;
    writeU(buf, pos, 4, Math.round((d.timestamp !== undefined ? d.timestamp : 0)), endian);
    pos += 4;
    // encode byte_group
    var bgVal = 0;
    bgVal |= ((Math.round(0)) & 0xFFFFF) << 4;
    bgVal |= ((Math.round(0)) & 0xFFF) << 0;
    writeU(buf, pos, 3, bgVal, endian);
    pos += 3;
    writeU(buf, pos, 2, Math.round((d.co2 !== undefined ? d.co2 : 0)), endian);
    pos += 2;
    writeU(buf, pos, 1, Math.round((d.battery !== undefined ? d.battery : 0)), endian);
    pos += 1;
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