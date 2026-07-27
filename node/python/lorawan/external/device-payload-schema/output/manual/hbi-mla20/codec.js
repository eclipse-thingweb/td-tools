// TS013 Payload Codec — hbi_mla20
// Schema version: 1
// Generated from: hbi-mla20.yaml
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
    var version_major = readU(buf, pos, 1, endian);
    pos += 1;
    vars.version_major = version_major;
    d.version_major = version_major;
    var version_minor = readU(buf, pos, 1, endian);
    pos += 1;
    vars.version_minor = version_minor;
    d.version_minor = version_minor;
    var version_patch = readU(buf, pos, 1, endian);
    pos += 1;
    vars.version_patch = version_patch;
    d.version_patch = version_patch;
    var _reserved = readU(buf, pos, 1, endian);
    pos += 1;
    vars._reserved = _reserved;
    // TLV loop
    while (pos + 0 <= buf.length) {
      var _tlvStart = pos;
      if ("[" +  + "]" === 32) {
        // byte_group
        var bgStart = pos;
        var bgVal = readU(buf, pos, 1, endian);
        var charger_status = (bgVal >> 0) & 0x3;
        d.charger_status = charger_status;
        vars.charger_status = charger_status;
        var device_status = (bgVal >> 4) & 0xF;
        d.device_status = device_status;
        vars.device_status = device_status;
        pos = bgStart + 1;
        // byte_group
        var bgStart = pos;
        var bgVal = readU(buf, pos, 1, endian);
        var radar_switch = (bgVal >> 0) & 0x1;
        d.radar_switch = radar_switch;
        vars.radar_switch = radar_switch;
        var daylight_switch = (bgVal >> 1) & 0x1;
        d.daylight_switch = daylight_switch;
        vars.daylight_switch = daylight_switch;
        var emergency_switch = (bgVal >> 2) & 0x1;
        d.emergency_switch = emergency_switch;
        vars.emergency_switch = emergency_switch;
        var intensity_switch = (bgVal >> 3) & 0x1;
        d.intensity_switch = intensity_switch;
        vars.intensity_switch = intensity_switch;
        var l2 = (bgVal >> 6) & 0x1;
        d.l2 = l2;
        vars.l2 = l2;
        var l1 = (bgVal >> 7) & 0x1;
        d.l1 = l1;
        vars.l1 = l1;
        pos = bgStart + 1;
        var led_intensity = readU(buf, pos, 1, endian);
        pos += 1;
        vars.led_intensity = led_intensity;
        d.led_intensity = led_intensity;
        var battery_voltage = readU(buf, pos, 2, endian);
        pos += 2;
        vars.battery_voltage = battery_voltage;
        d.battery_voltage = battery_voltage;
        var board_temperature = readU(buf, pos, 1, endian);
        pos += 1;
        vars.board_temperature = board_temperature;
        d.board_temperature = board_temperature;
        var days_since_function_test = readU(buf, pos, 1, endian);
        pos += 1;
        vars.days_since_function_test = days_since_function_test;
        d.days_since_function_test = days_since_function_test;
        var days_since_duration_test = readU(buf, pos, 2, endian);
        pos += 2;
        vars.days_since_duration_test = days_since_duration_test;
        d.days_since_duration_test = days_since_duration_test;
        var latest_duration_test = readU(buf, pos, 1, endian);
        pos += 1;
        vars.latest_duration_test = latest_duration_test;
        d.latest_duration_test = latest_duration_test;
      } else {
        break;
      }
    }
  return { data: d, pos: pos };
}

function encodePayload(d, endian) {
  var buf = new Array(256);
  var pos = 0;
  endian = endian || "big";
    writeU(buf, pos, 1, Math.round((d.version_major !== undefined ? d.version_major : 0)), endian);
    pos += 1;
    writeU(buf, pos, 1, Math.round((d.version_minor !== undefined ? d.version_minor : 0)), endian);
    pos += 1;
    writeU(buf, pos, 1, Math.round((d.version_patch !== undefined ? d.version_patch : 0)), endian);
    pos += 1;
    writeU(buf, pos, 1, 0, endian);
    pos += 1;
    // encode TLV entries
    if (d.led_intensity !== undefined || d.battery_voltage !== undefined || d.board_temperature !== undefined || d.days_since_function_test !== undefined || d.days_since_duration_test !== undefined || d.latest_duration_test !== undefined) {
      // encode byte_group
      var bgVal = 0;
      bgVal |= ((Math.round((d.charger_status || 0))) & 0x3) << 0;
      bgVal |= ((Math.round((d.device_status || 0))) & 0xF) << 4;
      writeU(buf, pos, 1, bgVal, endian);
      pos += 1;
      // encode byte_group
      var bgVal = 0;
      bgVal |= ((Math.round((d.radar_switch || 0))) & 0x1) << 0;
      bgVal |= ((Math.round((d.daylight_switch || 0))) & 0x1) << 1;
      bgVal |= ((Math.round((d.emergency_switch || 0))) & 0x1) << 2;
      bgVal |= ((Math.round((d.intensity_switch || 0))) & 0x1) << 3;
      bgVal |= ((Math.round((d.l2 || 0))) & 0x1) << 6;
      bgVal |= ((Math.round((d.l1 || 0))) & 0x1) << 7;
      writeU(buf, pos, 1, bgVal, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.led_intensity !== undefined ? d.led_intensity : 0)), endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round((d.battery_voltage !== undefined ? d.battery_voltage : 0)), endian);
      pos += 2;
      writeU(buf, pos, 1, Math.round((d.board_temperature !== undefined ? d.board_temperature : 0)), endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.days_since_function_test !== undefined ? d.days_since_function_test : 0)), endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round((d.days_since_duration_test !== undefined ? d.days_since_duration_test : 0)), endian);
      pos += 2;
      writeU(buf, pos, 1, Math.round((d.latest_duration_test !== undefined ? d.latest_duration_test : 0)), endian);
      pos += 1;
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