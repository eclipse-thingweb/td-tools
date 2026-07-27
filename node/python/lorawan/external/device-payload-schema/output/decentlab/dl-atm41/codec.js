// TS013 Payload Codec — decentlab_dl_atm41
// Schema version: 2
// Generated from: dl-atm41.yaml
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
      var solar_radiation = readU(buf, pos, 2, endian);
      pos += 2;
      vars.solar_radiation = solar_radiation;
      d.solar_radiation = (solar_radiation + -32768);
      var precipitation = readS(buf, pos, 2, endian);
      pos += 2;
      vars.precipitation = precipitation;
      d.precipitation = (precipitation / 1000);
      var lightning_strike_count = readU(buf, pos, 2, endian);
      pos += 2;
      vars.lightning_strike_count = lightning_strike_count;
      d.lightning_strike_count = (lightning_strike_count + -32768);
      var lightning_average_distance = readU(buf, pos, 2, endian);
      pos += 2;
      vars.lightning_average_distance = lightning_average_distance;
      d.lightning_average_distance = (lightning_average_distance + -32768);
      var wind_speed = readS(buf, pos, 2, endian);
      pos += 2;
      vars.wind_speed = wind_speed;
      d.wind_speed = (wind_speed / 100);
      var wind_direction = readS(buf, pos, 2, endian);
      pos += 2;
      vars.wind_direction = wind_direction;
      d.wind_direction = (wind_direction / 10);
      var maximum_wind_speed = readS(buf, pos, 2, endian);
      pos += 2;
      vars.maximum_wind_speed = maximum_wind_speed;
      d.maximum_wind_speed = (maximum_wind_speed / 100);
      var air_temperature = readS(buf, pos, 2, endian);
      pos += 2;
      vars.air_temperature = air_temperature;
      d.air_temperature = (air_temperature / 10);
      var vapor_pressure = readS(buf, pos, 2, endian);
      pos += 2;
      vars.vapor_pressure = vapor_pressure;
      d.vapor_pressure = (vapor_pressure / 100);
      var atmospheric_pressure = readS(buf, pos, 2, endian);
      pos += 2;
      vars.atmospheric_pressure = atmospheric_pressure;
      d.atmospheric_pressure = (atmospheric_pressure / 100);
      var relative_humidity = readS(buf, pos, 2, endian);
      pos += 2;
      vars.relative_humidity = relative_humidity;
      d.relative_humidity = (relative_humidity / 10);
      var sensor_temperature_internal = readS(buf, pos, 2, endian);
      pos += 2;
      vars.sensor_temperature_internal = sensor_temperature_internal;
      d.sensor_temperature_internal = (sensor_temperature_internal / 10);
      var x_orientation_angle = readS(buf, pos, 2, endian);
      pos += 2;
      vars.x_orientation_angle = x_orientation_angle;
      d.x_orientation_angle = (x_orientation_angle / 10);
      var y_orientation_angle = readS(buf, pos, 2, endian);
      pos += 2;
      vars.y_orientation_angle = y_orientation_angle;
      d.y_orientation_angle = (y_orientation_angle / 10);
      var compass_heading = readU(buf, pos, 2, endian);
      pos += 2;
      vars.compass_heading = compass_heading;
      d.compass_heading = (compass_heading + -32768);
      var north_wind_speed = readS(buf, pos, 2, endian);
      pos += 2;
      vars.north_wind_speed = north_wind_speed;
      d.north_wind_speed = (north_wind_speed / 100);
      var east_wind_speed = readS(buf, pos, 2, endian);
      pos += 2;
      vars.east_wind_speed = east_wind_speed;
      d.east_wind_speed = (east_wind_speed / 100);
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
    if (d.solar_radiation !== undefined || d.precipitation !== undefined || d.lightning_strike_count !== undefined || d.lightning_average_distance !== undefined || d.wind_speed !== undefined || d.wind_direction !== undefined || d.maximum_wind_speed !== undefined || d.air_temperature !== undefined || d.vapor_pressure !== undefined || d.atmospheric_pressure !== undefined || d.relative_humidity !== undefined || d.sensor_temperature_internal !== undefined || d.x_orientation_angle !== undefined || d.y_orientation_angle !== undefined || d.compass_heading !== undefined || d.north_wind_speed !== undefined || d.east_wind_speed !== undefined) _flags |= (1 << 0);
    if (d.battery_voltage !== undefined) _flags |= (1 << 1);
    writeU(buf, pos - 2, 2, _flags, endian);
    if (_flags & (1 << 0)) {
      writeU(buf, pos, 2, Math.round(((d.solar_radiation !== undefined ? d.solar_radiation : 0) - (-32768))), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.precipitation !== undefined ? d.precipitation : 0) * 1000)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round(((d.lightning_strike_count !== undefined ? d.lightning_strike_count : 0) - (-32768))), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round(((d.lightning_average_distance !== undefined ? d.lightning_average_distance : 0) - (-32768))), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.wind_speed !== undefined ? d.wind_speed : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.wind_direction !== undefined ? d.wind_direction : 0) * 10)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.maximum_wind_speed !== undefined ? d.maximum_wind_speed : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.air_temperature !== undefined ? d.air_temperature : 0) * 10)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.vapor_pressure !== undefined ? d.vapor_pressure : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.atmospheric_pressure !== undefined ? d.atmospheric_pressure : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.relative_humidity !== undefined ? d.relative_humidity : 0) * 10)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.sensor_temperature_internal !== undefined ? d.sensor_temperature_internal : 0) * 10)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.x_orientation_angle !== undefined ? d.x_orientation_angle : 0) * 10)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.y_orientation_angle !== undefined ? d.y_orientation_angle : 0) * 10)), endian);
      pos += 2;
      writeU(buf, pos, 2, Math.round(((d.compass_heading !== undefined ? d.compass_heading : 0) - (-32768))), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.north_wind_speed !== undefined ? d.north_wind_speed : 0) * 100)), endian);
      pos += 2;
      writeS(buf, pos, 2, Math.round(((d.east_wind_speed !== undefined ? d.east_wind_speed : 0) * 100)), endian);
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