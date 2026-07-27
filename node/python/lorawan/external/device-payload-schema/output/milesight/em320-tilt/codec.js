// TS013 Payload Codec — milesight_em320_tilt
// Schema version: 1
// Generated from: em320-tilt.yaml
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
      if ("[" + channel_id + ", " + channel_type + "]" === "[1, 117]") {
        var battery = readU(buf, pos, 1, endian);
        pos += 1;
        vars.battery = battery;
        d.battery = battery;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[3, 212]") {
        var angle_x = readS(buf, pos, 2, endian);
        pos += 2;
        vars.angle_x = angle_x;
        d.angle_x = (angle_x / 100);
        var angle_y = readS(buf, pos, 2, endian);
        pos += 2;
        vars.angle_y = angle_y;
        d.angle_y = (angle_y / 100);
        var angle_z = readS(buf, pos, 2, endian);
        pos += 2;
        vars.angle_z = angle_z;
        d.angle_z = (angle_z / 100);
        var threshold_x = readU(buf, pos, 1, endian);
        pos += 1;
        vars.threshold_x = threshold_x;
        d.threshold_x = threshold_x;
        var threshold_y = readU(buf, pos, 1, endian);
        pos += 1;
        vars.threshold_y = threshold_y;
        d.threshold_y = threshold_y;
        var threshold_z = readU(buf, pos, 1, endian);
        pos += 1;
        vars.threshold_z = threshold_z;
        d.threshold_z = threshold_z;
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
    if (d.battery !== undefined) {
      writeU(buf, pos, 1, 1, endian);
      pos += 1;
      writeU(buf, pos, 1, 117, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.battery !== undefined ? d.battery : 0)), endian);
      pos += 1;
    }
    if (d.angle_x !== undefined || d.angle_y !== undefined || d.angle_z !== undefined || d.threshold_x !== undefined || d.threshold_y !== undefined || d.threshold_z !== undefined) {
      writeU(buf, pos, 1, 3, endian);
      pos += 1;
      writeU(buf, pos, 1, 212, endian);
      pos += 1;
      writeS(buf, pos, 2, Math.round(((d.angle_x !== undefined ? d.angle_x : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.angle_y !== undefined ? d.angle_y : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.angle_z !== undefined ? d.angle_z : 0) * 100)), endian);
      pos += 2;
      writeU(buf, pos, 1, Math.round((d.threshold_x !== undefined ? d.threshold_x : 0)), endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.threshold_y !== undefined ? d.threshold_y : 0)), endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.threshold_z !== undefined ? d.threshold_z : 0)), endian);
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