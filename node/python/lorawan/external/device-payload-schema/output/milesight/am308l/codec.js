// TS013 Payload Codec — milesight_am308l
// Schema version: 1
// Generated from: am308l.yaml
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
        var pir = readU(buf, pos, 1, endian);
        pos += 1;
        vars.pir = pir;
        d.pir = pir;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[6, 203]") {
        var light_level = readU(buf, pos, 1, endian);
        pos += 1;
        vars.light_level = light_level;
        d.light_level = light_level;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[7, 125]") {
        var co2 = readU(buf, pos, 2, endian);
        pos += 2;
        vars.co2 = co2;
        d.co2 = co2;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[8, 125]") {
        var tvoc = readU(buf, pos, 2, endian);
        pos += 2;
        vars.tvoc = tvoc;
        d.tvoc = (tvoc / 100);
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[8, 230]") {
        var tvoc = readU(buf, pos, 2, endian);
        pos += 2;
        vars.tvoc = tvoc;
        d.tvoc = tvoc;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[9, 115]") {
        var pressure = readU(buf, pos, 2, endian);
        pos += 2;
        vars.pressure = pressure;
        d.pressure = (pressure / 10);
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[10, 125]") {
        var hcho = readU(buf, pos, 2, endian);
        pos += 2;
        vars.hcho = hcho;
        d.hcho = (hcho / 100);
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[11, 125]") {
        var pm2_5 = readU(buf, pos, 2, endian);
        pos += 2;
        vars.pm2_5 = pm2_5;
        d.pm2_5 = pm2_5;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[12, 125]") {
        var pm10 = readU(buf, pos, 2, endian);
        pos += 2;
        vars.pm10 = pm10;
        d.pm10 = pm10;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[13, 125]") {
        var o3 = readU(buf, pos, 2, endian);
        pos += 2;
        vars.o3 = o3;
        d.o3 = (o3 / 100);
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[14, 1]") {
        var beep = readU(buf, pos, 1, endian);
        pos += 1;
        vars.beep = beep;
        d.beep = beep;
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
    if (d.pir !== undefined) {
      writeU(buf, pos, 1, 5, endian);
      pos += 1;
      writeU(buf, pos, 1, 0, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.pir !== undefined ? d.pir : 0)), endian);
      pos += 1;
    }
    if (d.light_level !== undefined) {
      writeU(buf, pos, 1, 6, endian);
      pos += 1;
      writeU(buf, pos, 1, 203, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.light_level !== undefined ? d.light_level : 0)), endian);
      pos += 1;
    }
    if (d.co2 !== undefined) {
      writeU(buf, pos, 1, 7, endian);
      pos += 1;
      writeU(buf, pos, 1, 125, endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round((d.co2 !== undefined ? d.co2 : 0)), endian);
      pos += 2;
    }
    if (d.tvoc !== undefined) {
      writeU(buf, pos, 1, 8, endian);
      pos += 1;
      writeU(buf, pos, 1, 125, endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round(((d.tvoc !== undefined ? d.tvoc : 0) * 100)), endian);
      pos += 2;
    }
    if (d.tvoc !== undefined) {
      writeU(buf, pos, 1, 8, endian);
      pos += 1;
      writeU(buf, pos, 1, 230, endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round((d.tvoc !== undefined ? d.tvoc : 0)), endian);
      pos += 2;
    }
    if (d.pressure !== undefined) {
      writeU(buf, pos, 1, 9, endian);
      pos += 1;
      writeU(buf, pos, 1, 115, endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round(((d.pressure !== undefined ? d.pressure : 0) * 10)), endian);
      pos += 2;
    }
    if (d.hcho !== undefined) {
      writeU(buf, pos, 1, 10, endian);
      pos += 1;
      writeU(buf, pos, 1, 125, endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round(((d.hcho !== undefined ? d.hcho : 0) * 100)), endian);
      pos += 2;
    }
    if (d.pm2_5 !== undefined) {
      writeU(buf, pos, 1, 11, endian);
      pos += 1;
      writeU(buf, pos, 1, 125, endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round((d.pm2_5 !== undefined ? d.pm2_5 : 0)), endian);
      pos += 2;
    }
    if (d.pm10 !== undefined) {
      writeU(buf, pos, 1, 12, endian);
      pos += 1;
      writeU(buf, pos, 1, 125, endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round((d.pm10 !== undefined ? d.pm10 : 0)), endian);
      pos += 2;
    }
    if (d.o3 !== undefined) {
      writeU(buf, pos, 1, 13, endian);
      pos += 1;
      writeU(buf, pos, 1, 125, endian);
      pos += 1;
      writeU(buf, pos, 2, Math.round(((d.o3 !== undefined ? d.o3 : 0) * 100)), endian);
      pos += 2;
    }
    if (d.beep !== undefined) {
      writeU(buf, pos, 1, 14, endian);
      pos += 1;
      writeU(buf, pos, 1, 1, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.beep !== undefined ? d.beep : 0)), endian);
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