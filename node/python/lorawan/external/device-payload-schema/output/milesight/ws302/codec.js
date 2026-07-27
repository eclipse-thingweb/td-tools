// TS013 Payload Codec — milesight_ws302
// Schema version: 1
// Generated from: ws302.yaml
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
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[5, 91]") {
        var freq_weight = readU(buf, pos, 1, endian);
        pos += 1;
        vars.freq_weight = freq_weight;
        d.freq_weight = freq_weight;
        var time_weight = readU(buf, pos, 1, endian);
        pos += 1;
        vars.time_weight = time_weight;
        d.time_weight = time_weight;
        var la = readU(buf, pos, 2, endian);
        pos += 2;
        vars.la = la;
        d.la = (la / 10);
        var laeq = readU(buf, pos, 2, endian);
        pos += 2;
        vars.laeq = laeq;
        d.laeq = (laeq / 10);
        var lamax = readU(buf, pos, 2, endian);
        pos += 2;
        vars.lamax = lamax;
        d.lamax = (lamax / 10);
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[255, 15]") {
        var class_type = readU(buf, pos, 1, endian);
        pos += 1;
        vars.class_type = class_type;
        d.class_type = class_type;
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
    if (d.freq_weight !== undefined || d.time_weight !== undefined || d.la !== undefined || d.laeq !== undefined || d.lamax !== undefined) {
      writeU(buf, pos, 1, 5, endian);
      pos += 1;
      writeU(buf, pos, 1, 91, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.freq_weight !== undefined ? d.freq_weight : 0)), endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.time_weight !== undefined ? d.time_weight : 0)), endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round(((d.la !== undefined ? d.la : 0) * 10)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round(((d.laeq !== undefined ? d.laeq : 0) * 10)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round(((d.lamax !== undefined ? d.lamax : 0) * 10)), endian);
      pos += 2;
    }
    if (d.class_type !== undefined) {
      writeU(buf, pos, 1, 255, endian);
      pos += 1;
      writeU(buf, pos, 1, 15, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.class_type !== undefined ? d.class_type : 0)), endian);
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