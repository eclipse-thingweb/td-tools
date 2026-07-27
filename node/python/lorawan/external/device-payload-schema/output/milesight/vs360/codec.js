// TS013 Payload Codec — milesight_vs360
// Schema version: 1
// Generated from: vs360.yaml
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
        var battery_main = readU(buf, pos, 1, endian);
        pos += 1;
        vars.battery_main = battery_main;
        d.battery_main = battery_main;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[2, 117]") {
        var battery_node = readU(buf, pos, 1, endian);
        pos += 1;
        vars.battery_node = battery_node;
        d.battery_node = battery_node;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[4, 204]") {
        var total_in = readU(buf, pos, 2, endian);
        pos += 2;
        vars.total_in = total_in;
        d.total_in = total_in;
        var total_out = readU(buf, pos, 2, endian);
        pos += 2;
        vars.total_out = total_out;
        d.total_out = total_out;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[5, 204]") {
        var period_in = readU(buf, pos, 2, endian);
        pos += 2;
        vars.period_in = period_in;
        d.period_in = period_in;
        var period_out = readU(buf, pos, 2, endian);
        pos += 2;
        vars.period_out = period_out;
        d.period_out = period_out;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[132, 204]") {
        var total_in = readU(buf, pos, 2, endian);
        pos += 2;
        vars.total_in = total_in;
        d.total_in = total_in;
        var total_out = readU(buf, pos, 2, endian);
        pos += 2;
        vars.total_out = total_out;
        d.total_out = total_out;
        var total_count_alarm = readU(buf, pos, 1, endian);
        pos += 1;
        vars.total_count_alarm = total_count_alarm;
        d.total_count_alarm = total_count_alarm;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[133, 204]") {
        var period_in = readU(buf, pos, 2, endian);
        pos += 2;
        vars.period_in = period_in;
        d.period_in = period_in;
        var period_out = readU(buf, pos, 2, endian);
        pos += 2;
        vars.period_out = period_out;
        d.period_out = period_out;
        var period_count_alarm = readU(buf, pos, 1, endian);
        pos += 1;
        vars.period_count_alarm = period_count_alarm;
        d.period_count_alarm = period_count_alarm;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[10, 239]") {
        var timestamp = readU(buf, pos, 4, endian);
        pos += 4;
        vars.timestamp = timestamp;
        d.timestamp = timestamp;
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
    if (d.battery_main !== undefined) {
      writeU(buf, pos, 1, 1, endian);
      pos += 1;
      writeU(buf, pos, 1, 117, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.battery_main !== undefined ? d.battery_main : 0)), endian);
      pos += 1;
    }
    if (d.battery_node !== undefined) {
      writeU(buf, pos, 1, 2, endian);
      pos += 1;
      writeU(buf, pos, 1, 117, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.battery_node !== undefined ? d.battery_node : 0)), endian);
      pos += 1;
    }
    if (d.total_in !== undefined || d.total_out !== undefined) {
      writeU(buf, pos, 1, 4, endian);
      pos += 1;
      writeU(buf, pos, 1, 204, endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round((d.total_in !== undefined ? d.total_in : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.total_out !== undefined ? d.total_out : 0)), endian);
      pos += 2;
    }
    if (d.period_in !== undefined || d.period_out !== undefined) {
      writeU(buf, pos, 1, 5, endian);
      pos += 1;
      writeU(buf, pos, 1, 204, endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round((d.period_in !== undefined ? d.period_in : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.period_out !== undefined ? d.period_out : 0)), endian);
      pos += 2;
    }
    if (d.total_in !== undefined || d.total_out !== undefined || d.total_count_alarm !== undefined) {
      writeU(buf, pos, 1, 132, endian);
      pos += 1;
      writeU(buf, pos, 1, 204, endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round((d.total_in !== undefined ? d.total_in : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.total_out !== undefined ? d.total_out : 0)), endian);
      pos += 2;
      writeU(buf, pos, 1, Math.round((d.total_count_alarm !== undefined ? d.total_count_alarm : 0)), endian);
      pos += 1;
    }
    if (d.period_in !== undefined || d.period_out !== undefined || d.period_count_alarm !== undefined) {
      writeU(buf, pos, 1, 133, endian);
      pos += 1;
      writeU(buf, pos, 1, 204, endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round((d.period_in !== undefined ? d.period_in : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.period_out !== undefined ? d.period_out : 0)), endian);
      pos += 2;
      writeU(buf, pos, 1, Math.round((d.period_count_alarm !== undefined ? d.period_count_alarm : 0)), endian);
      pos += 1;
    }
    if (d.timestamp !== undefined) {
      writeU(buf, pos, 1, 10, endian);
      pos += 1;
      writeU(buf, pos, 1, 239, endian);
      pos += 1;
      writeU(buf, pos, 4, Math.round((d.timestamp !== undefined ? d.timestamp : 0)), endian);
      pos += 4;
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