// TS013 Payload Codec — mclimate_t_valve
// Schema version: 1
// Generated from: mclimate-t-valve.yaml
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
    // byte_group
    var bgStart = pos;
    var bgVal = readU(buf, pos, 1, endian);
    var reason = (bgVal >> 5) & 0x7;
    d.reason = (({"0": "keepalive", "1": "testButtonPressed", "2": "floodDetected", "3": "controlButtonPressed", "4": "fraudDetected"})[reason] !== undefined ? ({"0": "keepalive", "1": "testButtonPressed", "2": "floodDetected", "3": "controlButtonPressed", "4": "fraudDetected"})[reason] : reason);
    vars.reason = reason;
    var boxTamper = (bgVal >> 3) & 0x1;
    d.boxTamper = boxTamper;
    vars.boxTamper = boxTamper;
    var floodDetectionWireState = (bgVal >> 2) & 0x1;
    d.floodDetectionWireState = floodDetectionWireState;
    vars.floodDetectionWireState = floodDetectionWireState;
    var flood = (bgVal >> 1) & 0x1;
    d.flood = flood;
    vars.flood = flood;
    var magnet = (bgVal >> 0) & 0x1;
    d.magnet = magnet;
    vars.magnet = magnet;
    pos = bgStart + 1;
    // byte_group
    var bgStart = pos;
    var bgVal = readU(buf, pos, 1, endian);
    var alarmValidated = (bgVal >> 7) & 0x1;
    d.alarmValidated = alarmValidated;
    vars.alarmValidated = alarmValidated;
    var manualOpenIndicator = (bgVal >> 6) & 0x1;
    d.manualOpenIndicator = manualOpenIndicator;
    vars.manualOpenIndicator = manualOpenIndicator;
    var manualCloseIndicator = (bgVal >> 5) & 0x1;
    d.manualCloseIndicator = manualCloseIndicator;
    vars.manualCloseIndicator = manualCloseIndicator;
    pos = bgStart + 1;
    var closeTime = readU(buf, pos, 1, endian);
    pos += 1;
    vars.closeTime = closeTime;
    d.closeTime = closeTime;
    var openTime = readU(buf, pos, 1, endian);
    pos += 1;
    vars.openTime = openTime;
    d.openTime = openTime;
    var battery = readU(buf, pos, 1, endian);
    pos += 1;
    vars.battery = battery;
    d.battery = ((battery * 0.008) + 1.6);
  return { data: d, pos: pos };
}

function encodePayload(d, endian) {
  var buf = new Array(256);
  var pos = 0;
  endian = endian || "big";
    // encode byte_group
    var bgVal = 0;
    bgVal |= ((Math.round((d.reason || 0))) & 0x7) << 5;
    bgVal |= ((Math.round((d.boxTamper || 0))) & 0x1) << 3;
    bgVal |= ((Math.round((d.floodDetectionWireState || 0))) & 0x1) << 2;
    bgVal |= ((Math.round((d.flood || 0))) & 0x1) << 1;
    bgVal |= ((Math.round((d.magnet || 0))) & 0x1) << 0;
    writeU(buf, pos, 1, bgVal, endian);
    pos += 1;
    // encode byte_group
    var bgVal = 0;
    bgVal |= ((Math.round((d.alarmValidated || 0))) & 0x1) << 7;
    bgVal |= ((Math.round((d.manualOpenIndicator || 0))) & 0x1) << 6;
    bgVal |= ((Math.round((d.manualCloseIndicator || 0))) & 0x1) << 5;
    writeU(buf, pos, 1, bgVal, endian);
    pos += 1;
    writeU(buf, pos, 1, Math.round((d.closeTime !== undefined ? d.closeTime : 0)), endian);
    pos += 1;
    writeU(buf, pos, 1, Math.round((d.openTime !== undefined ? d.openTime : 0)), endian);
    pos += 1;
    writeU(buf, pos, 1, Math.round((((d.battery !== undefined ? d.battery : 0) - (1.6)) / 0.008)), endian);
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