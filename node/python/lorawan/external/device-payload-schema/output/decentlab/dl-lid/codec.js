// TS013 Payload Codec — decentlab_dl_lid
// Schema version: 2
// Generated from: dl-lid.yaml
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
      var distance_average = readU(buf, pos, 2, endian);
      pos += 2;
      vars.distance_average = distance_average;
      d.distance_average = distance_average;
      var distance_minimum = readU(buf, pos, 2, endian);
      pos += 2;
      vars.distance_minimum = distance_minimum;
      d.distance_minimum = distance_minimum;
      var distance_maximum = readU(buf, pos, 2, endian);
      pos += 2;
      vars.distance_maximum = distance_maximum;
      d.distance_maximum = distance_maximum;
      var distance_median = readU(buf, pos, 2, endian);
      pos += 2;
      vars.distance_median = distance_median;
      d.distance_median = distance_median;
      var distance_10th_percentile = readU(buf, pos, 2, endian);
      pos += 2;
      vars.distance_10th_percentile = distance_10th_percentile;
      d.distance_10th_percentile = distance_10th_percentile;
      var distance_25th_percentile = readU(buf, pos, 2, endian);
      pos += 2;
      vars.distance_25th_percentile = distance_25th_percentile;
      d.distance_25th_percentile = distance_25th_percentile;
      var distance_75th_percentile = readU(buf, pos, 2, endian);
      pos += 2;
      vars.distance_75th_percentile = distance_75th_percentile;
      d.distance_75th_percentile = distance_75th_percentile;
      var distance_90th_percentile = readU(buf, pos, 2, endian);
      pos += 2;
      vars.distance_90th_percentile = distance_90th_percentile;
      d.distance_90th_percentile = distance_90th_percentile;
      var distance_most_frequent_value = readU(buf, pos, 2, endian);
      pos += 2;
      vars.distance_most_frequent_value = distance_most_frequent_value;
      d.distance_most_frequent_value = distance_most_frequent_value;
      var number_of_samples = readU(buf, pos, 2, endian);
      pos += 2;
      vars.number_of_samples = number_of_samples;
      d.number_of_samples = number_of_samples;
      var total_acquisition_time = readU(buf, pos, 2, endian);
      pos += 2;
      vars.total_acquisition_time = total_acquisition_time;
      d.total_acquisition_time = (total_acquisition_time / 1.024);
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
    if (d.distance_average !== undefined || d.distance_minimum !== undefined || d.distance_maximum !== undefined || d.distance_median !== undefined || d.distance_10th_percentile !== undefined || d.distance_25th_percentile !== undefined || d.distance_75th_percentile !== undefined || d.distance_90th_percentile !== undefined || d.distance_most_frequent_value !== undefined || d.number_of_samples !== undefined || d.total_acquisition_time !== undefined) _flags |= (1 << 0);
    if (d.battery_voltage !== undefined) _flags |= (1 << 1);
    writeU(buf, pos - 2, 2, _flags, endian);
    if (_flags & (1 << 0)) {
      writeU(buf, pos, 2, Math.round((d.distance_average !== undefined ? d.distance_average : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.distance_minimum !== undefined ? d.distance_minimum : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.distance_maximum !== undefined ? d.distance_maximum : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.distance_median !== undefined ? d.distance_median : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.distance_10th_percentile !== undefined ? d.distance_10th_percentile : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.distance_25th_percentile !== undefined ? d.distance_25th_percentile : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.distance_75th_percentile !== undefined ? d.distance_75th_percentile : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.distance_90th_percentile !== undefined ? d.distance_90th_percentile : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.distance_most_frequent_value !== undefined ? d.distance_most_frequent_value : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round((d.number_of_samples !== undefined ? d.number_of_samples : 0)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round(((d.total_acquisition_time !== undefined ? d.total_acquisition_time : 0) * 1.024)), endian);
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