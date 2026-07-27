// TS013 Payload Codec — decentlab_dl_optod
// Schema version: 2
// Generated from: dl-optod.yaml
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
      var status = readU(buf, pos, 2, endian);
      pos += 2;
      vars.status = status;
      d.status = status;
      var temperature = readS(buf, pos, 2, endian);
      pos += 2;
      vars.temperature = temperature;
      d.temperature = (temperature / 100);
      var oxygen_saturation = readS(buf, pos, 2, endian);
      pos += 2;
      vars.oxygen_saturation = oxygen_saturation;
      d.oxygen_saturation = (oxygen_saturation / 100);
      var oxygen_concentration = readS(buf, pos, 2, endian);
      pos += 2;
      vars.oxygen_concentration = oxygen_concentration;
      d.oxygen_concentration = (oxygen_concentration / 100);
      var oxygen_concentration_alt = readS(buf, pos, 2, endian);
      pos += 2;
      vars.oxygen_concentration_alt = oxygen_concentration_alt;
      d.oxygen_concentration_alt = (oxygen_concentration_alt / 100);
    }
    if (vars.flags & (1 << 1)) {
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
    if (d.status !== undefined || d.temperature !== undefined || d.oxygen_saturation !== undefined || d.oxygen_concentration !== undefined || d.oxygen_concentration_alt !== undefined) _flags |= (1 << 0);
    if (d.battery_voltage !== undefined) _flags |= (1 << 1);
    writeU(buf, pos - 2, 2, _flags, endian);
    if (_flags & (1 << 0)) {
      writeU(buf, pos, 2, Math.round((d.status !== undefined ? d.status : 0)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.temperature !== undefined ? d.temperature : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.oxygen_saturation !== undefined ? d.oxygen_saturation : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.oxygen_concentration !== undefined ? d.oxygen_concentration : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.oxygen_concentration_alt !== undefined ? d.oxygen_concentration_alt : 0) * 100)), endian);
      pos += 2;
    }
    if (_flags & (1 << 1)) {
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