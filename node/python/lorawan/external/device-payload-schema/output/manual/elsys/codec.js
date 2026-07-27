// TS013 Payload Codec — elsys_ers
// Schema version: 1
// Generated from: elsys.yaml
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
    // TLV loop
    while (pos + 0 <= buf.length) {
      var _tlvStart = pos;
      if ("[" +  + "]" === 1) {
        var temperature = readS(buf, pos, 2, endian);
        pos += 2;
        vars.temperature = temperature;
        d.temperature = (temperature / 10);
      } else if ("[" +  + "]" === 2) {
        var humidity = readU(buf, pos, 1, endian);
        pos += 1;
        vars.humidity = humidity;
        d.humidity = humidity;
      } else if ("[" +  + "]" === 3) {
        var x = readS(buf, pos, 1, endian);
        pos += 1;
        vars.x = x;
        d.x = x;
        var y = readS(buf, pos, 1, endian);
        pos += 1;
        vars.y = y;
        d.y = y;
        var z = readS(buf, pos, 1, endian);
        pos += 1;
        vars.z = z;
        d.z = z;
      } else if ("[" +  + "]" === 4) {
        var light = readU(buf, pos, 2, endian);
        pos += 2;
        vars.light = light;
        d.light = light;
      } else if ("[" +  + "]" === 5) {
        var motion = readU(buf, pos, 1, endian);
        pos += 1;
        vars.motion = motion;
        d.motion = motion;
      } else if ("[" +  + "]" === 6) {
        var co2 = readU(buf, pos, 2, endian);
        pos += 2;
        vars.co2 = co2;
        d.co2 = co2;
      } else if ("[" +  + "]" === 7) {
        var vdd = readU(buf, pos, 2, endian);
        pos += 2;
        vars.vdd = vdd;
        d.vdd = vdd;
      } else if ("[" +  + "]" === 8) {
        var analog1 = readU(buf, pos, 2, endian);
        pos += 2;
        vars.analog1 = analog1;
        d.analog1 = analog1;
      } else if ("[" +  + "]" === 9) {
        var lat = readS(buf, pos, 3, endian);
        pos += 3;
        vars.lat = lat;
        d.lat = (lat / 10000);
        var long = readS(buf, pos, 3, endian);
        pos += 3;
        vars.long = long;
        d.long = (long / 10000);
      } else if ("[" +  + "]" === 10) {
        var pulse1 = readU(buf, pos, 2, endian);
        pos += 2;
        vars.pulse1 = pulse1;
        d.pulse1 = pulse1;
      } else if ("[" +  + "]" === 11) {
        var pulseAbs = readU(buf, pos, 4, endian);
        pos += 4;
        vars.pulseAbs = pulseAbs;
        d.pulseAbs = pulseAbs;
      } else if ("[" +  + "]" === 12) {
        var externalTemperature = readS(buf, pos, 2, endian);
        pos += 2;
        vars.externalTemperature = externalTemperature;
        d.externalTemperature = (externalTemperature / 10);
      } else if ("[" +  + "]" === 13) {
        var digital = readU(buf, pos, 1, endian);
        pos += 1;
        vars.digital = digital;
        d.digital = digital;
      } else if ("[" +  + "]" === 14) {
        var distance = readU(buf, pos, 2, endian);
        pos += 2;
        vars.distance = distance;
        d.distance = distance;
      } else if ("[" +  + "]" === 15) {
        var accMotion = readU(buf, pos, 1, endian);
        pos += 1;
        vars.accMotion = accMotion;
        d.accMotion = accMotion;
      } else if ("[" +  + "]" === 16) {
        var irInternalTemperature = readS(buf, pos, 2, endian);
        pos += 2;
        vars.irInternalTemperature = irInternalTemperature;
        d.irInternalTemperature = (irInternalTemperature / 10);
        var irExternalTemperature = readS(buf, pos, 2, endian);
        pos += 2;
        vars.irExternalTemperature = irExternalTemperature;
        d.irExternalTemperature = (irExternalTemperature / 10);
      } else if ("[" +  + "]" === 17) {
        var occupancy = readU(buf, pos, 1, endian);
        pos += 1;
        vars.occupancy = occupancy;
        d.occupancy = occupancy;
      } else if ("[" +  + "]" === 18) {
        var waterleak = readU(buf, pos, 1, endian);
        pos += 1;
        vars.waterleak = waterleak;
        d.waterleak = waterleak;
      } else if ("[" +  + "]" === 20) {
        var pressure = readU(buf, pos, 4, endian);
        pos += 4;
        vars.pressure = pressure;
        d.pressure = (pressure / 1000);
      } else if ("[" +  + "]" === 21) {
        var soundPeak = readU(buf, pos, 1, endian);
        pos += 1;
        vars.soundPeak = soundPeak;
        d.soundPeak = soundPeak;
        var soundAvg = readU(buf, pos, 1, endian);
        pos += 1;
        vars.soundAvg = soundAvg;
        d.soundAvg = soundAvg;
      } else if ("[" +  + "]" === 22) {
        var pulse2 = readU(buf, pos, 2, endian);
        pos += 2;
        vars.pulse2 = pulse2;
        d.pulse2 = pulse2;
      } else if ("[" +  + "]" === 23) {
        var pulse2Abs = readU(buf, pos, 4, endian);
        pos += 4;
        vars.pulse2Abs = pulse2Abs;
        d.pulse2Abs = pulse2Abs;
      } else if ("[" +  + "]" === 24) {
        var analog2 = readU(buf, pos, 2, endian);
        pos += 2;
        vars.analog2 = analog2;
        d.analog2 = analog2;
      } else if ("[" +  + "]" === 25) {
        var externalTemperature2 = readS(buf, pos, 2, endian);
        pos += 2;
        vars.externalTemperature2 = externalTemperature2;
        d.externalTemperature2 = (externalTemperature2 / 10);
      } else if ("[" +  + "]" === 26) {
        var digital2 = readU(buf, pos, 1, endian);
        pos += 1;
        vars.digital2 = digital2;
        d.digital2 = digital2;
      } else if ("[" +  + "]" === 27) {
        var analogUv = readS(buf, pos, 4, endian);
        pos += 4;
        vars.analogUv = analogUv;
        d.analogUv = analogUv;
      } else if ("[" +  + "]" === 28) {
        var tvoc = readU(buf, pos, 2, endian);
        pos += 2;
        vars.tvoc = tvoc;
        d.tvoc = tvoc;
      } else {
        break;
      }
    }
  return { data: d, pos: pos };
}

function encodePayload(d, endian) {
  var buf = new Array(256);
  var pos = 0;
  endian = endian || "big";
    // encode TLV entries
    if (d.temperature !== undefined) {
      writeS(buf, pos, 2, Math.round(((d.temperature !== undefined ? d.temperature : 0) * 10)), endian);
      pos += 2;
    }
    if (d.humidity !== undefined) {
      writeU(buf, pos, 1, Math.round((d.humidity !== undefined ? d.humidity : 0)), endian);
      pos += 1;
    }
    if (d.x !== undefined || d.y !== undefined || d.z !== undefined) {
      writeS(buf, pos, 1, Math.round((d.x !== undefined ? d.x : 0)), endian);
      pos += 1;
      writeS(buf, pos, 1, Math.round((d.y !== undefined ? d.y : 0)), endian);
      pos += 1;
      writeS(buf, pos, 1, Math.round((d.z !== undefined ? d.z : 0)), endian);
      pos += 1;
    }
    if (d.light !== undefined) {
      writeU(buf, pos, 2, Math.round((d.light !== undefined ? d.light : 0)), endian);
      pos += 2;
    }
    if (d.motion !== undefined) {
      writeU(buf, pos, 1, Math.round((d.motion !== undefined ? d.motion : 0)), endian);
      pos += 1;
    }
    if (d.co2 !== undefined) {
      writeU(buf, pos, 2, Math.round((d.co2 !== undefined ? d.co2 : 0)), endian);
      pos += 2;
    }
    if (d.vdd !== undefined) {
      writeU(buf, pos, 2, Math.round((d.vdd !== undefined ? d.vdd : 0)), endian);
      pos += 2;
    }
    if (d.analog1 !== undefined) {
      writeU(buf, pos, 2, Math.round((d.analog1 !== undefined ? d.analog1 : 0)), endian);
      pos += 2;
    }
    if (d.lat !== undefined || d.long !== undefined) {
      writeS(buf, pos, 3, Math.round(((d.lat !== undefined ? d.lat : 0) * 10000)), endian);
      pos += 3;
      writeS(buf, pos, 3, Math.round(((d.long !== undefined ? d.long : 0) * 10000)), endian);
      pos += 3;
    }
    if (d.pulse1 !== undefined) {
      writeU(buf, pos, 2, Math.round((d.pulse1 !== undefined ? d.pulse1 : 0)), endian);
      pos += 2;
    }
    if (d.pulseAbs !== undefined) {
      writeU(buf, pos, 4, Math.round((d.pulseAbs !== undefined ? d.pulseAbs : 0)), endian);
      pos += 4;
    }
    if (d.externalTemperature !== undefined) {
      writeS(buf, pos, 2, Math.round(((d.externalTemperature !== undefined ? d.externalTemperature : 0) * 10)), endian);
      pos += 2;
    }
    if (d.digital !== undefined) {
      writeU(buf, pos, 1, Math.round((d.digital !== undefined ? d.digital : 0)), endian);
      pos += 1;
    }
    if (d.distance !== undefined) {
      writeU(buf, pos, 2, Math.round((d.distance !== undefined ? d.distance : 0)), endian);
      pos += 2;
    }
    if (d.accMotion !== undefined) {
      writeU(buf, pos, 1, Math.round((d.accMotion !== undefined ? d.accMotion : 0)), endian);
      pos += 1;
    }
    if (d.irInternalTemperature !== undefined || d.irExternalTemperature !== undefined) {
      writeS(buf, pos, 2, Math.round(((d.irInternalTemperature !== undefined ? d.irInternalTemperature : 0) * 10)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.irExternalTemperature !== undefined ? d.irExternalTemperature : 0) * 10)), endian);
      pos += 2;
    }
    if (d.occupancy !== undefined) {
      writeU(buf, pos, 1, Math.round((d.occupancy !== undefined ? d.occupancy : 0)), endian);
      pos += 1;
    }
    if (d.waterleak !== undefined) {
      writeU(buf, pos, 1, Math.round((d.waterleak !== undefined ? d.waterleak : 0)), endian);
      pos += 1;
    }
    if (d.pressure !== undefined) {
      writeU(buf, pos, 4, Math.round(((d.pressure !== undefined ? d.pressure : 0) * 1000)), endian);
      pos += 4;
    }
    if (d.soundPeak !== undefined || d.soundAvg !== undefined) {
      writeU(buf, pos, 1, Math.round((d.soundPeak !== undefined ? d.soundPeak : 0)), endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.soundAvg !== undefined ? d.soundAvg : 0)), endian);
      pos += 1;
    }
    if (d.pulse2 !== undefined) {
      writeU(buf, pos, 2, Math.round((d.pulse2 !== undefined ? d.pulse2 : 0)), endian);
      pos += 2;
    }
    if (d.pulse2Abs !== undefined) {
      writeU(buf, pos, 4, Math.round((d.pulse2Abs !== undefined ? d.pulse2Abs : 0)), endian);
      pos += 4;
    }
    if (d.analog2 !== undefined) {
      writeU(buf, pos, 2, Math.round((d.analog2 !== undefined ? d.analog2 : 0)), endian);
      pos += 2;
    }
    if (d.externalTemperature2 !== undefined) {
      writeS(buf, pos, 2, Math.round(((d.externalTemperature2 !== undefined ? d.externalTemperature2 : 0) * 10)), endian);
      pos += 2;
    }
    if (d.digital2 !== undefined) {
      writeU(buf, pos, 1, Math.round((d.digital2 !== undefined ? d.digital2 : 0)), endian);
      pos += 1;
    }
    if (d.analogUv !== undefined) {
      writeS(buf, pos, 4, Math.round((d.analogUv !== undefined ? d.analogUv : 0)), endian);
      pos += 4;
    }
    if (d.tvoc !== undefined) {
      writeU(buf, pos, 2, Math.round((d.tvoc !== undefined ? d.tvoc : 0)), endian);
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