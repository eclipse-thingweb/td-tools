// TS013 Payload Codec — decentlab_dl_isf
// Schema version: 2
// Generated from: dl-isf.yaml
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
      var sap_flow = readU(buf, pos, 2, endian);
      pos += 2;
      vars.sap_flow = sap_flow;
      d.sap_flow = sap_flow;
      var heat_velocity_outer = readU(buf, pos, 2, endian);
      pos += 2;
      vars.heat_velocity_outer = heat_velocity_outer;
      d.heat_velocity_outer = heat_velocity_outer;
      var heat_velocity_inner = readU(buf, pos, 2, endian);
      pos += 2;
      vars.heat_velocity_inner = heat_velocity_inner;
      d.heat_velocity_inner = heat_velocity_inner;
      var alpha_outer = readU(buf, pos, 2, endian);
      pos += 2;
      vars.alpha_outer = alpha_outer;
      d.alpha_outer = alpha_outer;
      var alpha_inner = readU(buf, pos, 2, endian);
      pos += 2;
      vars.alpha_inner = alpha_inner;
      d.alpha_inner = alpha_inner;
      var beta_outer = readU(buf, pos, 2, endian);
      pos += 2;
      vars.beta_outer = beta_outer;
      d.beta_outer = beta_outer;
      var beta_inner = readU(buf, pos, 2, endian);
      pos += 2;
      vars.beta_inner = beta_inner;
      d.beta_inner = beta_inner;
      var tmax_outer = readU(buf, pos, 2, endian);
      pos += 2;
      vars.tmax_outer = tmax_outer;
      d.tmax_outer = tmax_outer;
      var tmax_inner = readU(buf, pos, 2, endian);
      pos += 2;
      vars.tmax_inner = tmax_inner;
      d.tmax_inner = tmax_inner;
      var temperature_outer = readS(buf, pos, 2, endian);
      pos += 2;
      vars.temperature_outer = temperature_outer;
      d.temperature_outer = (temperature_outer / 100);
      var max_voltage = readS(buf, pos, 2, endian);
      pos += 2;
      vars.max_voltage = max_voltage;
      d.max_voltage = (max_voltage / 1000);
      var min_voltage = readS(buf, pos, 2, endian);
      pos += 2;
      vars.min_voltage = min_voltage;
      d.min_voltage = (min_voltage / 1000);
      var diagnostic = readU(buf, pos, 4, endian);
      pos += 4;
      vars.diagnostic = diagnostic;
      d.diagnostic = diagnostic;
      var upstream_tmax_outer = readU(buf, pos, 2, endian);
      pos += 2;
      vars.upstream_tmax_outer = upstream_tmax_outer;
      d.upstream_tmax_outer = upstream_tmax_outer;
      var upstream_tmax_inner = readU(buf, pos, 2, endian);
      pos += 2;
      vars.upstream_tmax_inner = upstream_tmax_inner;
      d.upstream_tmax_inner = upstream_tmax_inner;
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
    if (d.sap_flow !== undefined || d.heat_velocity_outer !== undefined || d.heat_velocity_inner !== undefined || d.alpha_outer !== undefined || d.alpha_inner !== undefined || d.beta_outer !== undefined || d.beta_inner !== undefined || d.tmax_outer !== undefined || d.tmax_inner !== undefined || d.temperature_outer !== undefined || d.max_voltage !== undefined || d.min_voltage !== undefined || d.diagnostic !== undefined || d.upstream_tmax_outer !== undefined || d.upstream_tmax_inner !== undefined) _flags |= (1 << 0);
    if (d.battery_voltage !== undefined) _flags |= (1 << 1);
    writeU(buf, pos - 2, 2, _flags, endian);
    if (_flags & (1 << 0)) {
      writeU(buf, pos, 2, Math.round((d.sap_flow !== undefined ? d.sap_flow : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.heat_velocity_outer !== undefined ? d.heat_velocity_outer : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.heat_velocity_inner !== undefined ? d.heat_velocity_inner : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.alpha_outer !== undefined ? d.alpha_outer : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.alpha_inner !== undefined ? d.alpha_inner : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.beta_outer !== undefined ? d.beta_outer : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.beta_inner !== undefined ? d.beta_inner : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.tmax_outer !== undefined ? d.tmax_outer : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.tmax_inner !== undefined ? d.tmax_inner : 0)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.temperature_outer !== undefined ? d.temperature_outer : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.max_voltage !== undefined ? d.max_voltage : 0) * 1000)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.min_voltage !== undefined ? d.min_voltage : 0) * 1000)), endian);
      pos += 2;
      writeU(buf, pos, 4, Math.round((d.diagnostic !== undefined ? d.diagnostic : 0)), endian);
      pos += 4;
      writeU(buf, pos, 2, Math.round((d.upstream_tmax_outer !== undefined ? d.upstream_tmax_outer : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.upstream_tmax_inner !== undefined ? d.upstream_tmax_inner : 0)), endian);
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