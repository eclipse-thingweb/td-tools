// TS013 Payload Codec — milesight_wt201v2
// Schema version: 1
// Generated from: wt201v2.yaml
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
  endian = endian || "little";
    // TLV loop
    while (pos + 2 <= buf.length) {
      var _tlvStart = pos;
      var channel_id = readU(buf, pos, 1, endian);
      pos += 1;
      var channel_type = readU(buf, pos, 1, endian);
      pos += 1;
      if ("[" + channel_id + ", " + channel_type + "]" === "[255, 1]") {
        var ipso_version = readU(buf, pos, 1, endian);
        pos += 1;
        vars.ipso_version = ipso_version;
        d.ipso_version = ipso_version;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[255, 9]") {
        var hardware_version = readU(buf, pos, 1, endian);
        pos += 1;
        vars.hardware_version = hardware_version;
        d.hardware_version = hardware_version;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[255, 10]") {
        var firmware_version = readU(buf, pos, 1, endian);
        pos += 1;
        vars.firmware_version = firmware_version;
        d.firmware_version = firmware_version;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[255, 255]") {
        var tsl_version = readU(buf, pos, 1, endian);
        pos += 1;
        vars.tsl_version = tsl_version;
        d.tsl_version = tsl_version;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[255, 22]") {
        var sn = readU(buf, pos, 1, endian);
        pos += 1;
        vars.sn = sn;
        d.sn = sn;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[255, 15]") {
        var lorawan_class = readU(buf, pos, 1, endian);
        pos += 1;
        vars.lorawan_class = lorawan_class;
        d.lorawan_class = lorawan_class;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[255, 254]") {
        var reset_event = readU(buf, pos, 1, endian);
        pos += 1;
        vars.reset_event = reset_event;
        d.reset_event = reset_event;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[255, 11]") {
        var device_status = readU(buf, pos, 1, endian);
        pos += 1;
        vars.device_status = device_status;
        d.device_status = device_status;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[3, 103]") {
        var temperature = readS(buf, pos, 2, endian);
        pos += 2;
        vars.temperature = temperature;
        d.temperature = (temperature / 10);
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[4, 103]") {
        var target_temperature = readS(buf, pos, 2, endian);
        pos += 2;
        vars.target_temperature = target_temperature;
        d.target_temperature = (target_temperature / 10);
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[11, 103]") {
        var target_temperature_2 = readS(buf, pos, 2, endian);
        pos += 2;
        vars.target_temperature_2 = target_temperature_2;
        d.target_temperature_2 = (target_temperature_2 / 10);
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[5, 231]") {
        var temperature_control_mode = readU(buf, pos, 1, endian);
        pos += 1;
        vars.temperature_control_mode = temperature_control_mode;
        d.temperature_control_mode = temperature_control_mode;
        var temperature_control_status = readU(buf, pos, 1, endian);
        pos += 1;
        vars.temperature_control_status = temperature_control_status;
        d.temperature_control_status = temperature_control_status;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[6, 232]") {
        var fan_mode = readU(buf, pos, 1, endian);
        pos += 1;
        vars.fan_mode = fan_mode;
        d.fan_mode = fan_mode;
        var fan_status = readU(buf, pos, 1, endian);
        pos += 1;
        vars.fan_status = fan_status;
        d.fan_status = fan_status;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[7, 188]") {
        var plan_type = readU(buf, pos, 1, endian);
        pos += 1;
        vars.plan_type = plan_type;
        d.plan_type = plan_type;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[8, 142]") {
        var system_status = readU(buf, pos, 1, endian);
        pos += 1;
        vars.system_status = system_status;
        d.system_status = system_status;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[9, 104]") {
        var humidity = readU(buf, pos, 1, endian);
        pos += 1;
        vars.humidity = humidity;
        d.humidity = humidity;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[10, 110]") {
        var wires_relay = readU(buf, pos, 1, endian);
        pos += 1;
        vars.wires_relay = wires_relay;
        d.wires_relay = wires_relay;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[255, 203]") {
        var temperature_control_support_mode = readU(buf, pos, 1, endian);
        pos += 1;
        vars.temperature_control_support_mode = temperature_control_support_mode;
        d.temperature_control_support_mode = temperature_control_support_mode;
        var temperature_control_support_status = readU(buf, pos, 1, endian);
        pos += 1;
        vars.temperature_control_support_status = temperature_control_support_status;
        d.temperature_control_support_status = temperature_control_support_status;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[131, 103]") {
        var temperature = readS(buf, pos, 2, endian);
        pos += 2;
        vars.temperature = temperature;
        d.temperature = (temperature / 10);
        var temperature_alarm = readU(buf, pos, 1, endian);
        pos += 1;
        vars.temperature_alarm = temperature_alarm;
        d.temperature_alarm = temperature_alarm;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[179, 103]") {
        var temperature_sensor_status = readU(buf, pos, 1, endian);
        pos += 1;
        vars.temperature_sensor_status = temperature_sensor_status;
        d.temperature_sensor_status = temperature_sensor_status;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[185, 104]") {
        var humidity_sensor_status = readU(buf, pos, 1, endian);
        pos += 1;
        vars.humidity_sensor_status = humidity_sensor_status;
        d.humidity_sensor_status = humidity_sensor_status;
      } else {
        break;
      }
    }
  return { data: d, pos: pos };
}

function encodePayload(d, endian) {
  var buf = new Array(256);
  var pos = 0;
  endian = endian || "little";
    // encode TLV entries
    if (d.ipso_version !== undefined) {
      writeU(buf, pos, 1, 255, endian);
      pos += 1;
      writeU(buf, pos, 1, 1, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.ipso_version !== undefined ? d.ipso_version : 0)), endian);
      pos += 1;
    }
    if (d.hardware_version !== undefined) {
      writeU(buf, pos, 1, 255, endian);
      pos += 1;
      writeU(buf, pos, 1, 9, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.hardware_version !== undefined ? d.hardware_version : 0)), endian);
      pos += 1;
    }
    if (d.firmware_version !== undefined) {
      writeU(buf, pos, 1, 255, endian);
      pos += 1;
      writeU(buf, pos, 1, 10, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.firmware_version !== undefined ? d.firmware_version : 0)), endian);
      pos += 1;
    }
    if (d.tsl_version !== undefined) {
      writeU(buf, pos, 1, 255, endian);
      pos += 1;
      writeU(buf, pos, 1, 255, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.tsl_version !== undefined ? d.tsl_version : 0)), endian);
      pos += 1;
    }
    if (d.sn !== undefined) {
      writeU(buf, pos, 1, 255, endian);
      pos += 1;
      writeU(buf, pos, 1, 22, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.sn !== undefined ? d.sn : 0)), endian);
      pos += 1;
    }
    if (d.lorawan_class !== undefined) {
      writeU(buf, pos, 1, 255, endian);
      pos += 1;
      writeU(buf, pos, 1, 15, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.lorawan_class !== undefined ? d.lorawan_class : 0)), endian);
      pos += 1;
    }
    if (d.reset_event !== undefined) {
      writeU(buf, pos, 1, 255, endian);
      pos += 1;
      writeU(buf, pos, 1, 254, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.reset_event !== undefined ? d.reset_event : 0)), endian);
      pos += 1;
    }
    if (d.device_status !== undefined) {
      writeU(buf, pos, 1, 255, endian);
      pos += 1;
      writeU(buf, pos, 1, 11, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.device_status !== undefined ? d.device_status : 0)), endian);
      pos += 1;
    }
    if (d.temperature !== undefined) {
      writeU(buf, pos, 1, 3, endian);
      pos += 1;
      writeU(buf, pos, 1, 103, endian);
      pos += 1;
      writeS(buf, pos, 2, Math.round(((d.temperature !== undefined ? d.temperature : 0) * 10)), endian);
      pos += 2;
    }
    if (d.target_temperature !== undefined) {
      writeU(buf, pos, 1, 4, endian);
      pos += 1;
      writeU(buf, pos, 1, 103, endian);
      pos += 1;
      writeS(buf, pos, 2, Math.round(((d.target_temperature !== undefined ? d.target_temperature : 0) * 10)), endian);
      pos += 2;
    }
    if (d.target_temperature_2 !== undefined) {
      writeU(buf, pos, 1, 11, endian);
      pos += 1;
      writeU(buf, pos, 1, 103, endian);
      pos += 1;
      writeS(buf, pos, 2, Math.round(((d.target_temperature_2 !== undefined ? d.target_temperature_2 : 0) * 10)), endian);
      pos += 2;
    }
    if (d.temperature_control_mode !== undefined || d.temperature_control_status !== undefined) {
      writeU(buf, pos, 1, 5, endian);
      pos += 1;
      writeU(buf, pos, 1, 231, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.temperature_control_mode !== undefined ? d.temperature_control_mode : 0)), endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.temperature_control_status !== undefined ? d.temperature_control_status : 0)), endian);
      pos += 1;
    }
    if (d.fan_mode !== undefined || d.fan_status !== undefined) {
      writeU(buf, pos, 1, 6, endian);
      pos += 1;
      writeU(buf, pos, 1, 232, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.fan_mode !== undefined ? d.fan_mode : 0)), endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.fan_status !== undefined ? d.fan_status : 0)), endian);
      pos += 1;
    }
    if (d.plan_type !== undefined) {
      writeU(buf, pos, 1, 7, endian);
      pos += 1;
      writeU(buf, pos, 1, 188, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.plan_type !== undefined ? d.plan_type : 0)), endian);
      pos += 1;
    }
    if (d.system_status !== undefined) {
      writeU(buf, pos, 1, 8, endian);
      pos += 1;
      writeU(buf, pos, 1, 142, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.system_status !== undefined ? d.system_status : 0)), endian);
      pos += 1;
    }
    if (d.humidity !== undefined) {
      writeU(buf, pos, 1, 9, endian);
      pos += 1;
      writeU(buf, pos, 1, 104, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.humidity !== undefined ? d.humidity : 0)), endian);
      pos += 1;
    }
    if (d.wires_relay !== undefined) {
      writeU(buf, pos, 1, 10, endian);
      pos += 1;
      writeU(buf, pos, 1, 110, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.wires_relay !== undefined ? d.wires_relay : 0)), endian);
      pos += 1;
    }
    if (d.temperature_control_support_mode !== undefined || d.temperature_control_support_status !== undefined) {
      writeU(buf, pos, 1, 255, endian);
      pos += 1;
      writeU(buf, pos, 1, 203, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.temperature_control_support_mode !== undefined ? d.temperature_control_support_mode : 0)), endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.temperature_control_support_status !== undefined ? d.temperature_control_support_status : 0)), endian);
      pos += 1;
    }
    if (d.temperature !== undefined || d.temperature_alarm !== undefined) {
      writeU(buf, pos, 1, 131, endian);
      pos += 1;
      writeU(buf, pos, 1, 103, endian);
      pos += 1;
      writeS(buf, pos, 2, Math.round(((d.temperature !== undefined ? d.temperature : 0) * 10)), endian);
      pos += 2;
      writeU(buf, pos, 1, Math.round((d.temperature_alarm !== undefined ? d.temperature_alarm : 0)), endian);
      pos += 1;
    }
    if (d.temperature_sensor_status !== undefined) {
      writeU(buf, pos, 1, 179, endian);
      pos += 1;
      writeU(buf, pos, 1, 103, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.temperature_sensor_status !== undefined ? d.temperature_sensor_status : 0)), endian);
      pos += 1;
    }
    if (d.humidity_sensor_status !== undefined) {
      writeU(buf, pos, 1, 185, endian);
      pos += 1;
      writeU(buf, pos, 1, 104, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.humidity_sensor_status !== undefined ? d.humidity_sensor_status : 0)), endian);
      pos += 1;
    }
  return buf.slice(0, pos);
}

function decodeUplink(input) {
  try {
    var r = decodePayload(input.bytes, "little");
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
    var bytes = encodePayload(input.data, "little");
    return { bytes: bytes, fPort: 1, warnings: [], errors: [] };
  } catch (e) {
    return { bytes: [], fPort: 1, warnings: [], errors: [e.message] };
  }
}