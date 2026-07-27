// TS013 Payload Codec — milesight_ws558
// Schema version: 1
// Generated from: ws558.yaml
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
      if ("[" + channel_id + ", " + channel_type + "]" === "[3, 116]") {
        var voltage = readU(buf, pos, 2, endian);
        pos += 2;
        vars.voltage = voltage;
        d.voltage = (voltage / 10);
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[4, 128]") {
        var active_power = readU(buf, pos, 4, endian);
        pos += 4;
        vars.active_power = active_power;
        d.active_power = active_power;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[5, 129]") {
        var power_factor = readU(buf, pos, 1, endian);
        pos += 1;
        vars.power_factor = power_factor;
        d.power_factor = power_factor;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[6, 131]") {
        var power_consumption = readU(buf, pos, 4, endian);
        pos += 4;
        vars.power_consumption = power_consumption;
        d.power_consumption = power_consumption;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[7, 201]") {
        var total_current = readU(buf, pos, 2, endian);
        pos += 2;
        vars.total_current = total_current;
        d.total_current = total_current;
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
    if (d.voltage !== undefined) {
      writeU(buf, pos, 1, 3, endian);
      pos += 1;
      writeU(buf, pos, 1, 116, endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round(((d.voltage !== undefined ? d.voltage : 0) * 10)), endian);
      pos += 2;
    }
    if (d.active_power !== undefined) {
      writeU(buf, pos, 1, 4, endian);
      pos += 1;
      writeU(buf, pos, 1, 128, endian);
      pos += 1;
      writeU(buf, pos, 4, Math.round((d.active_power !== undefined ? d.active_power : 0)), endian);
      pos += 4;
    }
    if (d.power_factor !== undefined) {
      writeU(buf, pos, 1, 5, endian);
      pos += 1;
      writeU(buf, pos, 1, 129, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.power_factor !== undefined ? d.power_factor : 0)), endian);
      pos += 1;
    }
    if (d.power_consumption !== undefined) {
      writeU(buf, pos, 1, 6, endian);
      pos += 1;
      writeU(buf, pos, 1, 131, endian);
      pos += 1;
      writeU(buf, pos, 4, Math.round((d.power_consumption !== undefined ? d.power_consumption : 0)), endian);
      pos += 4;
    }
    if (d.total_current !== undefined) {
      writeU(buf, pos, 1, 7, endian);
      pos += 1;
      writeU(buf, pos, 1, 201, endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round((d.total_current !== undefined ? d.total_current : 0)), endian);
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