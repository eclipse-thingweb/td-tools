// TS013 Payload Codec — decentlab_dl_gmm
// Schema version: 2
// Generated from: dl-gmm.yaml
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
      var photosynthetically_active_radiation = readS(buf, pos, 2, endian);
      pos += 2;
      vars.photosynthetically_active_radiation = photosynthetically_active_radiation;
      d.photosynthetically_active_radiation = (photosynthetically_active_radiation / 10);
      var air_temperature = readS(buf, pos, 2, endian);
      pos += 2;
      vars.air_temperature = air_temperature;
      d.air_temperature = (air_temperature / 100);
      var air_humidity = readS(buf, pos, 2, endian);
      pos += 2;
      vars.air_humidity = air_humidity;
      d.air_humidity = (air_humidity / 10);
      var co2_concentration = readS(buf, pos, 2, endian);
      pos += 2;
      vars.co2_concentration = co2_concentration;
      d.co2_concentration = (co2_concentration / 1);
      var atmospheric_pressure = readS(buf, pos, 2, endian);
      pos += 2;
      vars.atmospheric_pressure = atmospheric_pressure;
      d.atmospheric_pressure = (atmospheric_pressure / 100);
      var vapor_pressure_deficit = readS(buf, pos, 2, endian);
      pos += 2;
      vars.vapor_pressure_deficit = vapor_pressure_deficit;
      d.vapor_pressure_deficit = (vapor_pressure_deficit / 100);
      var dew_point = readS(buf, pos, 2, endian);
      pos += 2;
      vars.dew_point = dew_point;
      d.dew_point = (dew_point / 100);
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
    if (d.photosynthetically_active_radiation !== undefined || d.air_temperature !== undefined || d.air_humidity !== undefined || d.co2_concentration !== undefined || d.atmospheric_pressure !== undefined || d.vapor_pressure_deficit !== undefined || d.dew_point !== undefined) _flags |= (1 << 0);
    if (d.battery_voltage !== undefined) _flags |= (1 << 1);
    writeU(buf, pos - 2, 2, _flags, endian);
    if (_flags & (1 << 0)) {
      writeS(buf, pos, 2, Math.round(((d.photosynthetically_active_radiation !== undefined ? d.photosynthetically_active_radiation : 0) * 10)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.air_temperature !== undefined ? d.air_temperature : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.air_humidity !== undefined ? d.air_humidity : 0) * 10)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.co2_concentration !== undefined ? d.co2_concentration : 0) * 1)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.atmospheric_pressure !== undefined ? d.atmospheric_pressure : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.vapor_pressure_deficit !== undefined ? d.vapor_pressure_deficit : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.dew_point !== undefined ? d.dew_point : 0) * 100)), endian);
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