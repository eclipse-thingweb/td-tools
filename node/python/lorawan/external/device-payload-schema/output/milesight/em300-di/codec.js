// TS013 Payload Codec — milesight_em300_di
// Schema version: 1
// Generated from: em300-di.yaml
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
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[3, 103]") {
        var temperature = readS(buf, pos, 2, endian);
        pos += 2;
        vars.temperature = temperature;
        d.temperature = (temperature / 10);
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[4, 104]") {
        var humidity = readU(buf, pos, 1, endian);
        pos += 1;
        vars.humidity = humidity;
        d.humidity = (humidity / 2);
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[5, 0]") {
        var gpio = readU(buf, pos, 1, endian);
        pos += 1;
        vars.gpio = gpio;
        d.gpio = gpio;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[5, 200]") {
        var pulse = readU(buf, pos, 4, endian);
        pos += 4;
        vars.pulse = pulse;
        d.pulse = pulse;
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
    if (d.temperature !== undefined) {
      writeU(buf, pos, 1, 3, endian);
      pos += 1;
      writeU(buf, pos, 1, 103, endian);
      pos += 1;
      writeS(buf, pos, 2, Math.round(((d.temperature !== undefined ? d.temperature : 0) * 10)), endian);
      pos += 2;
    }
    if (d.humidity !== undefined) {
      writeU(buf, pos, 1, 4, endian);
      pos += 1;
      writeU(buf, pos, 1, 104, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round(((d.humidity !== undefined ? d.humidity : 0) * 2)), endian);
      pos += 1;
    }
    if (d.gpio !== undefined) {
      writeU(buf, pos, 1, 5, endian);
      pos += 1;
      writeU(buf, pos, 1, 0, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.gpio !== undefined ? d.gpio : 0)), endian);
      pos += 1;
    }
    if (d.pulse !== undefined) {
      writeU(buf, pos, 1, 5, endian);
      pos += 1;
      writeU(buf, pos, 1, 200, endian);
      pos += 1;
      writeU(buf, pos, 4, Math.round((d.pulse !== undefined ? d.pulse : 0)), endian);
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