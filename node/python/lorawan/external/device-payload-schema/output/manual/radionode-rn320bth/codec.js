// TS013 Payload Codec — radionode_rn320bth
// Schema version: 1
// Generated from: radionode-rn320bth.yaml
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
    var head = readU(buf, pos, 1, endian);
    pos += 1;
    vars.head = head;
    vars.head = head;
    d.head = head;
    var model = readU(buf, pos, 1, endian);
    pos += 1;
    vars.model = model;
    d.model = model;
    // match on head
    if (vars.head === 11) {
      var timestamp = readU(buf, pos, 4, endian);
      pos += 4;
      vars.timestamp = timestamp;
      d.timestamp = timestamp;
      var interval = readU(buf, pos, 2, endian);
      pos += 2;
      vars.interval = interval;
      d.interval = interval;
      var battery = readU(buf, pos, 1, endian);
      pos += 1;
      vars.battery = battery;
      d.battery = battery;
      var millivolt = readU(buf, pos, 2, endian);
      pos += 2;
      vars.millivolt = millivolt;
      d.millivolt = millivolt;
      var freqband = readU(buf, pos, 1, endian);
      pos += 1;
      vars.freqband = freqband;
      d.freqband = freqband;
      var subband = readU(buf, pos, 1, endian);
      pos += 1;
      vars.subband = subband;
      d.subband = subband;
    } else if (vars.head === 12) {
      var tsmode = readU(buf, pos, 1, endian);
      pos += 1;
      vars.tsmode = tsmode;
      d.tsmode = tsmode;
      var timestamp = readU(buf, pos, 4, endian);
      pos += 4;
      vars.timestamp = timestamp;
      d.timestamp = timestamp;
      var splfmt = readU(buf, pos, 1, endian);
      pos += 1;
      vars.splfmt = splfmt;
      d.splfmt = splfmt;
      var temperature = readF32(buf, pos, endian);
      pos += 4;
      d.temperature = temperature;
      vars.temperature = temperature;
      var humidity = readF32(buf, pos, endian);
      pos += 4;
      d.humidity = humidity;
      vars.humidity = humidity;
    }
  return { data: d, pos: pos };
}

function encodePayload(d, endian) {
  var buf = new Array(256);
  var pos = 0;
  endian = endian || "little";
    writeU(buf, pos, 1, Math.round((d.head !== undefined ? d.head : 0)), endian);
    pos += 1;
    writeU(buf, pos, 1, Math.round((d.model !== undefined ? d.model : 0)), endian);
    pos += 1;
    // TODO: match encoding requires case selection
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