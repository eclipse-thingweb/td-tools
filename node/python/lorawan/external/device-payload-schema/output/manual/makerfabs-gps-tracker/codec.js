// TS013 Payload Codec — makerfabs_gps_tracker
// Schema version: 1
// Generated from: makerfabs-gps-tracker.yaml
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
    var num = readU(buf, pos, 2, endian);
    pos += 2;
    vars.num = num;
    d.num = num;
    var battery = readU(buf, pos, 1, endian);
    pos += 1;
    vars.battery = battery;
    d.battery = (battery / 10);
    var gSensorState = readU(buf, pos, 1, endian);
    pos += 1;
    vars.gSensorState = gSensorState;
    d.gSensorState = gSensorState;
    var gpsStatus = readU(buf, pos, 1, endian);
    pos += 1;
    vars.gpsStatus = gpsStatus;
    d.gpsStatus = gpsStatus;
    var year = readU(buf, pos, 2, endian);
    pos += 2;
    vars.year = year;
    d.year = year;
    var month = readU(buf, pos, 1, endian);
    pos += 1;
    vars.month = month;
    d.month = month;
    var date = readU(buf, pos, 1, endian);
    pos += 1;
    vars.date = date;
    d.date = date;
    var hour = readU(buf, pos, 1, endian);
    pos += 1;
    vars.hour = hour;
    d.hour = hour;
    var minute = readU(buf, pos, 1, endian);
    pos += 1;
    vars.minute = minute;
    d.minute = minute;
    var second = readU(buf, pos, 1, endian);
    pos += 1;
    vars.second = second;
    d.second = second;
    var latitude = readU(buf, pos, 4, endian);
    pos += 4;
    vars.latitude = latitude;
    d.latitude = (latitude / 100000);
    var nsHemi = readU(buf, pos, 1, endian);
    pos += 1;
    vars.nsHemi = nsHemi;
    d.nsHemi = (({"0": "N", "1": "S"})[nsHemi] !== undefined ? ({"0": "N", "1": "S"})[nsHemi] : nsHemi);
    var longitude = readU(buf, pos, 4, endian);
    pos += 4;
    vars.longitude = longitude;
    d.longitude = (longitude / 100000);
    var ewHemi = readU(buf, pos, 1, endian);
    pos += 1;
    vars.ewHemi = ewHemi;
    d.ewHemi = (({"0": "E", "1": "W"})[ewHemi] !== undefined ? ({"0": "E", "1": "W"})[ewHemi] : ewHemi);
    var gsensor_onoff = readU(buf, pos, 1, endian);
    pos += 1;
    vars.gsensor_onoff = gsensor_onoff;
    d.gsensor_onoff = gsensor_onoff;
    var gsensor_sensitivity = readU(buf, pos, 1, endian);
    pos += 1;
    vars.gsensor_sensitivity = gsensor_sensitivity;
    d.gsensor_sensitivity = gsensor_sensitivity;
  return { data: d, pos: pos };
}

function encodePayload(d, endian) {
  var buf = new Array(256);
  var pos = 0;
  endian = endian || "big";
    writeU(buf, pos, 2, Math.round((d.num !== undefined ? d.num : 0)), endian);
    pos += 2;
    writeU(buf, pos, 1, Math.round(((d.battery !== undefined ? d.battery : 0) * 10)), endian);
    pos += 1;
    writeU(buf, pos, 1, Math.round((d.gSensorState !== undefined ? d.gSensorState : 0)), endian);
    pos += 1;
    writeU(buf, pos, 1, Math.round((d.gpsStatus !== undefined ? d.gpsStatus : 0)), endian);
    pos += 1;
    writeU(buf, pos, 2, Math.round((d.year !== undefined ? d.year : 0)), endian);
    pos += 2;
    writeU(buf, pos, 1, Math.round((d.month !== undefined ? d.month : 0)), endian);
    pos += 1;
    writeU(buf, pos, 1, Math.round((d.date !== undefined ? d.date : 0)), endian);
    pos += 1;
    writeU(buf, pos, 1, Math.round((d.hour !== undefined ? d.hour : 0)), endian);
    pos += 1;
    writeU(buf, pos, 1, Math.round((d.minute !== undefined ? d.minute : 0)), endian);
    pos += 1;
    writeU(buf, pos, 1, Math.round((d.second !== undefined ? d.second : 0)), endian);
    pos += 1;
    writeU(buf, pos, 4, Math.round(((d.latitude !== undefined ? d.latitude : 0) * 100000)), endian);
    pos += 4;
    writeU(buf, pos, 1, Math.round((d.nsHemi !== undefined ? d.nsHemi : 0)), endian);
    pos += 1;
    writeU(buf, pos, 4, Math.round(((d.longitude !== undefined ? d.longitude : 0) * 100000)), endian);
    pos += 4;
    writeU(buf, pos, 1, Math.round((d.ewHemi !== undefined ? d.ewHemi : 0)), endian);
    pos += 1;
    writeU(buf, pos, 1, Math.round((d.gsensor_onoff !== undefined ? d.gsensor_onoff : 0)), endian);
    pos += 1;
    writeU(buf, pos, 1, Math.round((d.gsensor_sensitivity !== undefined ? d.gsensor_sensitivity : 0)), endian);
    pos += 1;
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