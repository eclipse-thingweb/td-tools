// TS013 Payload Codec — milesight_vs373
// Schema version: 1
// Generated from: vs373.yaml
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
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[255, 11]") {
        var device_status = readU(buf, pos, 1, endian);
        pos += 1;
        vars.device_status = device_status;
        d.device_status = device_status;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[255, 15]") {
        var lorawan_class = readU(buf, pos, 1, endian);
        pos += 1;
        vars.lorawan_class = lorawan_class;
        d.lorawan_class = lorawan_class;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[255, 22]") {
        var sn = readU(buf, pos, 1, endian);
        pos += 1;
        vars.sn = sn;
        d.sn = sn;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[255, 255]") {
        var tsl_version = readU(buf, pos, 1, endian);
        pos += 1;
        vars.tsl_version = tsl_version;
        d.tsl_version = tsl_version;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[3, 248]") {
        var detection_status = readU(buf, pos, 1, endian);
        pos += 1;
        vars.detection_status = detection_status;
        d.detection_status = detection_status;
        var target_status = readU(buf, pos, 1, endian);
        pos += 1;
        vars.target_status = target_status;
        d.target_status = target_status;
        var use_time_now = readU(buf, pos, 2, endian);
        pos += 2;
        vars.use_time_now = use_time_now;
        d.use_time_now = use_time_now;
        var use_time_today = readU(buf, pos, 2, endian);
        pos += 2;
        vars.use_time_today = use_time_today;
        d.use_time_today = use_time_today;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[7, 176]") {
        var detection_status = readU(buf, pos, 1, endian);
        pos += 1;
        vars.detection_status = detection_status;
        d.detection_status = detection_status;
        var target_status = readU(buf, pos, 1, endian);
        pos += 1;
        vars.target_status = target_status;
        d.target_status = target_status;
        var use_time_now = readU(buf, pos, 1, endian);
        pos += 1;
        vars.use_time_now = use_time_now;
        d.use_time_now = use_time_now;
        var use_time_today = readU(buf, pos, 1, endian);
        pos += 1;
        vars.use_time_today = use_time_today;
        d.use_time_today = use_time_today;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[4, 249]") {
        var region_1_occupancy = readU(buf, pos, 1, endian);
        pos += 1;
        vars.region_1_occupancy = region_1_occupancy;
        d.region_1_occupancy = region_1_occupancy;
        var region_2_occupancy = readU(buf, pos, 1, endian);
        pos += 1;
        vars.region_2_occupancy = region_2_occupancy;
        d.region_2_occupancy = region_2_occupancy;
        var region_3_occupancy = readU(buf, pos, 1, endian);
        pos += 1;
        vars.region_3_occupancy = region_3_occupancy;
        d.region_3_occupancy = region_3_occupancy;
        var region_4_occupancy = readU(buf, pos, 1, endian);
        pos += 1;
        vars.region_4_occupancy = region_4_occupancy;
        d.region_4_occupancy = region_4_occupancy;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[5, 250]") {
        var region_1_out_of_bed_time = readU(buf, pos, 2, endian);
        pos += 2;
        vars.region_1_out_of_bed_time = region_1_out_of_bed_time;
        d.region_1_out_of_bed_time = region_1_out_of_bed_time;
        var region_2_out_of_bed_time = readU(buf, pos, 2, endian);
        pos += 2;
        vars.region_2_out_of_bed_time = region_2_out_of_bed_time;
        d.region_2_out_of_bed_time = region_2_out_of_bed_time;
        var region_3_out_of_bed_time = readU(buf, pos, 2, endian);
        pos += 2;
        vars.region_3_out_of_bed_time = region_3_out_of_bed_time;
        d.region_3_out_of_bed_time = region_3_out_of_bed_time;
        var region_4_out_of_bed_time = readU(buf, pos, 2, endian);
        pos += 2;
        vars.region_4_out_of_bed_time = region_4_out_of_bed_time;
        d.region_4_out_of_bed_time = region_4_out_of_bed_time;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[11, 180]") {
        var region_1_out_of_bed_time = readU(buf, pos, 1, endian);
        pos += 1;
        vars.region_1_out_of_bed_time = region_1_out_of_bed_time;
        d.region_1_out_of_bed_time = region_1_out_of_bed_time;
        var region_2_out_of_bed_time = readU(buf, pos, 1, endian);
        pos += 1;
        vars.region_2_out_of_bed_time = region_2_out_of_bed_time;
        d.region_2_out_of_bed_time = region_2_out_of_bed_time;
        var region_3_out_of_bed_time = readU(buf, pos, 1, endian);
        pos += 1;
        vars.region_3_out_of_bed_time = region_3_out_of_bed_time;
        d.region_3_out_of_bed_time = region_3_out_of_bed_time;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[12, 180]") {
        var region_4_out_of_bed_time = readU(buf, pos, 1, endian);
        pos += 1;
        vars.region_4_out_of_bed_time = region_4_out_of_bed_time;
        d.region_4_out_of_bed_time = region_4_out_of_bed_time;
        var region_5_out_of_bed_time = readU(buf, pos, 1, endian);
        pos += 1;
        vars.region_5_out_of_bed_time = region_5_out_of_bed_time;
        d.region_5_out_of_bed_time = region_5_out_of_bed_time;
        var region_6_out_of_bed_time = readU(buf, pos, 1, endian);
        pos += 1;
        vars.region_6_out_of_bed_time = region_6_out_of_bed_time;
        d.region_6_out_of_bed_time = region_6_out_of_bed_time;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[8, 177]") {
        var respiratory_status = readU(buf, pos, 1, endian);
        pos += 1;
        vars.respiratory_status = respiratory_status;
        d.respiratory_status = respiratory_status;
        var respiratory_rate = readU(buf, pos, 2, endian);
        pos += 2;
        vars.respiratory_rate = respiratory_rate;
        d.respiratory_rate = (respiratory_rate / 100);
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
    if (d.device_status !== undefined) {
      writeU(buf, pos, 1, 255, endian);
      pos += 1;
      writeU(buf, pos, 1, 11, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.device_status !== undefined ? d.device_status : 0)), endian);
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
    if (d.sn !== undefined) {
      writeU(buf, pos, 1, 255, endian);
      pos += 1;
      writeU(buf, pos, 1, 22, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.sn !== undefined ? d.sn : 0)), endian);
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
    if (d.detection_status !== undefined || d.target_status !== undefined || d.use_time_now !== undefined || d.use_time_today !== undefined) {
      writeU(buf, pos, 1, 3, endian);
      pos += 1;
      writeU(buf, pos, 1, 248, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.detection_status !== undefined ? d.detection_status : 0)), endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.target_status !== undefined ? d.target_status : 0)), endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round((d.use_time_now !== undefined ? d.use_time_now : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.use_time_today !== undefined ? d.use_time_today : 0)), endian);
      pos += 2;
    }
    if (d.detection_status !== undefined || d.target_status !== undefined || d.use_time_now !== undefined || d.use_time_today !== undefined) {
      writeU(buf, pos, 1, 7, endian);
      pos += 1;
      writeU(buf, pos, 1, 176, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.detection_status !== undefined ? d.detection_status : 0)), endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.target_status !== undefined ? d.target_status : 0)), endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.use_time_now !== undefined ? d.use_time_now : 0)), endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.use_time_today !== undefined ? d.use_time_today : 0)), endian);
      pos += 1;
    }
    if (d.region_1_occupancy !== undefined || d.region_2_occupancy !== undefined || d.region_3_occupancy !== undefined || d.region_4_occupancy !== undefined) {
      writeU(buf, pos, 1, 4, endian);
      pos += 1;
      writeU(buf, pos, 1, 249, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.region_1_occupancy !== undefined ? d.region_1_occupancy : 0)), endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.region_2_occupancy !== undefined ? d.region_2_occupancy : 0)), endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.region_3_occupancy !== undefined ? d.region_3_occupancy : 0)), endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.region_4_occupancy !== undefined ? d.region_4_occupancy : 0)), endian);
      pos += 1;
    }
    if (d.region_1_out_of_bed_time !== undefined || d.region_2_out_of_bed_time !== undefined || d.region_3_out_of_bed_time !== undefined || d.region_4_out_of_bed_time !== undefined) {
      writeU(buf, pos, 1, 5, endian);
      pos += 1;
      writeU(buf, pos, 1, 250, endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round((d.region_1_out_of_bed_time !== undefined ? d.region_1_out_of_bed_time : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.region_2_out_of_bed_time !== undefined ? d.region_2_out_of_bed_time : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.region_3_out_of_bed_time !== undefined ? d.region_3_out_of_bed_time : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.region_4_out_of_bed_time !== undefined ? d.region_4_out_of_bed_time : 0)), endian);
      pos += 2;
    }
    if (d.region_1_out_of_bed_time !== undefined || d.region_2_out_of_bed_time !== undefined || d.region_3_out_of_bed_time !== undefined) {
      writeU(buf, pos, 1, 11, endian);
      pos += 1;
      writeU(buf, pos, 1, 180, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.region_1_out_of_bed_time !== undefined ? d.region_1_out_of_bed_time : 0)), endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.region_2_out_of_bed_time !== undefined ? d.region_2_out_of_bed_time : 0)), endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.region_3_out_of_bed_time !== undefined ? d.region_3_out_of_bed_time : 0)), endian);
      pos += 1;
    }
    if (d.region_4_out_of_bed_time !== undefined || d.region_5_out_of_bed_time !== undefined || d.region_6_out_of_bed_time !== undefined) {
      writeU(buf, pos, 1, 12, endian);
      pos += 1;
      writeU(buf, pos, 1, 180, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.region_4_out_of_bed_time !== undefined ? d.region_4_out_of_bed_time : 0)), endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.region_5_out_of_bed_time !== undefined ? d.region_5_out_of_bed_time : 0)), endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.region_6_out_of_bed_time !== undefined ? d.region_6_out_of_bed_time : 0)), endian);
      pos += 1;
    }
    if (d.respiratory_status !== undefined || d.respiratory_rate !== undefined) {
      writeU(buf, pos, 1, 8, endian);
      pos += 1;
      writeU(buf, pos, 1, 177, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.respiratory_status !== undefined ? d.respiratory_status : 0)), endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round(((d.respiratory_rate !== undefined ? d.respiratory_rate : 0) * 100)), endian);
      pos += 2;
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