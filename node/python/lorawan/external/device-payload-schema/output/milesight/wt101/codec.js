// TS013 Payload Codec — milesight_wt101
// Schema version: 1
// Generated from: wt101.yaml
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
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[1, 117]") {
        var battery = readU(buf, pos, 1, endian);
        pos += 1;
        vars.battery = battery;
        d.battery = battery;
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
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[5, 146]") {
        var valve_opening = readU(buf, pos, 1, endian);
        pos += 1;
        vars.valve_opening = valve_opening;
        d.valve_opening = valve_opening;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[6, 0]") {
        var tamper_status = readU(buf, pos, 1, endian);
        pos += 1;
        vars.tamper_status = tamper_status;
        d.tamper_status = tamper_status;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[7, 0]") {
        var window_detection = readU(buf, pos, 1, endian);
        pos += 1;
        vars.window_detection = window_detection;
        d.window_detection = window_detection;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[8, 229]") {
        var motor_calibration_result = readU(buf, pos, 1, endian);
        pos += 1;
        vars.motor_calibration_result = motor_calibration_result;
        d.motor_calibration_result = motor_calibration_result;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[9, 144]") {
        var motor_stroke = readU(buf, pos, 2, endian);
        pos += 2;
        vars.motor_stroke = motor_stroke;
        d.motor_stroke = motor_stroke;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[10, 0]") {
        var freeze_protection = readU(buf, pos, 1, endian);
        pos += 1;
        vars.freeze_protection = freeze_protection;
        d.freeze_protection = freeze_protection;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[11, 144]") {
        var motor_position = readU(buf, pos, 2, endian);
        pos += 2;
        vars.motor_position = motor_position;
        d.motor_position = motor_position;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[249, 51]") {
        var heating_date = readU(buf, pos, 1, endian);
        pos += 1;
        vars.heating_date = heating_date;
        d.heating_date = heating_date;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[249, 52]") {
        var heating_schedule = readU(buf, pos, 1, endian);
        pos += 1;
        vars.heating_schedule = heating_schedule;
        d.heating_schedule = heating_schedule;
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
    if (d.battery !== undefined) {
      writeU(buf, pos, 1, 1, endian);
      pos += 1;
      writeU(buf, pos, 1, 117, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.battery !== undefined ? d.battery : 0)), endian);
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
    if (d.valve_opening !== undefined) {
      writeU(buf, pos, 1, 5, endian);
      pos += 1;
      writeU(buf, pos, 1, 146, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.valve_opening !== undefined ? d.valve_opening : 0)), endian);
      pos += 1;
    }
    if (d.tamper_status !== undefined) {
      writeU(buf, pos, 1, 6, endian);
      pos += 1;
      writeU(buf, pos, 1, 0, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.tamper_status !== undefined ? d.tamper_status : 0)), endian);
      pos += 1;
    }
    if (d.window_detection !== undefined) {
      writeU(buf, pos, 1, 7, endian);
      pos += 1;
      writeU(buf, pos, 1, 0, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.window_detection !== undefined ? d.window_detection : 0)), endian);
      pos += 1;
    }
    if (d.motor_calibration_result !== undefined) {
      writeU(buf, pos, 1, 8, endian);
      pos += 1;
      writeU(buf, pos, 1, 229, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.motor_calibration_result !== undefined ? d.motor_calibration_result : 0)), endian);
      pos += 1;
    }
    if (d.motor_stroke !== undefined) {
      writeU(buf, pos, 1, 9, endian);
      pos += 1;
      writeU(buf, pos, 1, 144, endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round((d.motor_stroke !== undefined ? d.motor_stroke : 0)), endian);
      pos += 2;
    }
    if (d.freeze_protection !== undefined) {
      writeU(buf, pos, 1, 10, endian);
      pos += 1;
      writeU(buf, pos, 1, 0, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.freeze_protection !== undefined ? d.freeze_protection : 0)), endian);
      pos += 1;
    }
    if (d.motor_position !== undefined) {
      writeU(buf, pos, 1, 11, endian);
      pos += 1;
      writeU(buf, pos, 1, 144, endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round((d.motor_position !== undefined ? d.motor_position : 0)), endian);
      pos += 2;
    }
    if (d.heating_date !== undefined) {
      writeU(buf, pos, 1, 249, endian);
      pos += 1;
      writeU(buf, pos, 1, 51, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.heating_date !== undefined ? d.heating_date : 0)), endian);
      pos += 1;
    }
    if (d.heating_schedule !== undefined) {
      writeU(buf, pos, 1, 249, endian);
      pos += 1;
      writeU(buf, pos, 1, 52, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.heating_schedule !== undefined ? d.heating_schedule : 0)), endian);
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