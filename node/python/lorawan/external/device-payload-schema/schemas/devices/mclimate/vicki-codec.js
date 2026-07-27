// TS013 Payload Codec — mclimate_vicki
// Schema version: 2
// Generated from: mclimate-vicki.yaml
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
    var reason = readU(buf, pos, 1, endian);
    pos += 1;
    vars.reason = reason;
    d.reason = reason;
    var targetTemperature = readU(buf, pos, 1, endian);
    pos += 1;
    vars.targetTemperature = targetTemperature;
    d.targetTemperature = targetTemperature;
    var sensorTemperatureRaw = readU(buf, pos, 1, endian);
    pos += 1;
    vars.sensorTemperatureRaw = sensorTemperatureRaw;
    d.sensorTemperatureRaw = sensorTemperatureRaw;
    d._tempStandard = (d.reason !== 129) ? ((d.sensorTemperatureRaw * 0.64453125) + -40) : 0;
    d._tempFw35 = (d.reason === 129) ? ((d.sensorTemperatureRaw + -28.33333) / 5.66666) : 0;
    d.sensorTemperature = (Math.round((d._tempStandard + d._tempFw35) * 100) / 100);
    var relativeHumidityRaw = readU(buf, pos, 1, endian);
    pos += 1;
    vars.relativeHumidityRaw = relativeHumidityRaw;
    d.relativeHumidityRaw = relativeHumidityRaw;
    d.relativeHumidity = (Math.round((d.relativeHumidityRaw * 0.390625) * 100) / 100);
    var motorPositionLow = readU(buf, pos, 1, endian);
    pos += 1;
    vars.motorPositionLow = motorPositionLow;
    d.motorPositionLow = motorPositionLow;
    var motorRangeLow = readU(buf, pos, 1, endian);
    pos += 1;
    vars.motorRangeLow = motorRangeLow;
    d.motorRangeLow = motorRangeLow;
    // byte_group
    var bgStart = pos;
    var bgVal = readU(buf, pos, 1, endian);
    var motorPositionHigh = (bgVal >> 4) & 0xF;
    d.motorPositionHigh = motorPositionHigh;
    vars.motorPositionHigh = motorPositionHigh;
    var motorRangeHigh = (bgVal >> 0) & 0xF;
    d.motorRangeHigh = motorRangeHigh;
    vars.motorRangeHigh = motorRangeHigh;
    pos = bgStart + 1;
    // byte_group
    var bgStart = pos;
    var bgVal = readU(buf, pos, 1, endian);
    var batteryLevel = (bgVal >> 4) & 0xF;
    d.batteryLevel = batteryLevel;
    vars.batteryLevel = batteryLevel;
    var openWindow = (bgVal >> 3) & 0x1;
    d.openWindow = openWindow;
    vars.openWindow = openWindow;
    var highMotorConsumption = (bgVal >> 2) & 0x1;
    d.highMotorConsumption = highMotorConsumption;
    vars.highMotorConsumption = highMotorConsumption;
    var lowMotorConsumption = (bgVal >> 1) & 0x1;
    d.lowMotorConsumption = lowMotorConsumption;
    vars.lowMotorConsumption = lowMotorConsumption;
    var brokenSensor = (bgVal >> 0) & 0x1;
    d.brokenSensor = brokenSensor;
    vars.brokenSensor = brokenSensor;
    pos = bgStart + 1;
    // byte_group
    var bgStart = pos;
    var bgVal = readU(buf, pos, 1, endian);
    var childLock = (bgVal >> 7) & 0x1;
    d.childLock = childLock;
    vars.childLock = childLock;
    var calibrationFailed = (bgVal >> 6) & 0x1;
    d.calibrationFailed = calibrationFailed;
    vars.calibrationFailed = calibrationFailed;
    var attachedBackplate = (bgVal >> 5) & 0x1;
    d.attachedBackplate = attachedBackplate;
    vars.attachedBackplate = attachedBackplate;
    var perceiveAsOnline = (bgVal >> 4) & 0x1;
    d.perceiveAsOnline = perceiveAsOnline;
    vars.perceiveAsOnline = perceiveAsOnline;
    var antiFreezeProtection = (bgVal >> 3) & 0x1;
    d.antiFreezeProtection = antiFreezeProtection;
    vars.antiFreezeProtection = antiFreezeProtection;
    pos = bgStart + 1;
    d.batteryVoltage = (Math.round(((d.batteryLevel * 0.1) + 2) * 100) / 100);
    d._motorRangeHigh256 = (d.motorRangeHigh * 256);
    d.motorRange = (d._motorRangeHigh256 + d.motorRangeLow);
    d._motorPositionHigh256 = (d.motorPositionHigh * 256);
    d.motorPosition = (d._motorPositionHigh256 + d.motorPositionLow);
    d._motorPosPercent = (d.motorPosition * 100);
    d._motorPosRatio = (d.motorRange > 0) ? (d.motorRange !== 0 ? d._motorPosPercent / d.motorRange : NaN) : 100;
    d.valveOpenness = Math.round(((d._motorPosRatio * -1) + 100));
    d.targetTemperatureFloat = d.targetTemperature;
  return { data: d, pos: pos };
}

function encodePayload(d, endian) {
  var buf = new Array(256);
  var pos = 0;
  endian = endian || "big";
    writeU(buf, pos, 1, Math.round((d.reason !== undefined ? d.reason : 0)), endian);
    pos += 1;
    writeU(buf, pos, 1, Math.round((d.targetTemperature !== undefined ? d.targetTemperature : 0)), endian);
    pos += 1;
    writeU(buf, pos, 1, Math.round((d.sensorTemperatureRaw !== undefined ? d.sensorTemperatureRaw : 0)), endian);
    pos += 1;
    // skip computed field _tempStandard
    // skip computed field _tempFw35
    // skip computed field sensorTemperature
    writeU(buf, pos, 1, Math.round((d.relativeHumidityRaw !== undefined ? d.relativeHumidityRaw : 0)), endian);
    pos += 1;
    // skip computed field relativeHumidity
    writeU(buf, pos, 1, Math.round((d.motorPositionLow !== undefined ? d.motorPositionLow : 0)), endian);
    pos += 1;
    writeU(buf, pos, 1, Math.round((d.motorRangeLow !== undefined ? d.motorRangeLow : 0)), endian);
    pos += 1;
    // encode byte_group
    var bgVal = 0;
    bgVal |= ((Math.round((d.motorPositionHigh || 0))) & 0xF) << 4;
    bgVal |= ((Math.round((d.motorRangeHigh || 0))) & 0xF) << 0;
    writeU(buf, pos, 1, bgVal, endian);
    pos += 1;
    // encode byte_group
    var bgVal = 0;
    bgVal |= ((Math.round((d.batteryLevel || 0))) & 0xF) << 4;
    bgVal |= ((Math.round((d.openWindow || 0))) & 0x1) << 3;
    bgVal |= ((Math.round((d.highMotorConsumption || 0))) & 0x1) << 2;
    bgVal |= ((Math.round((d.lowMotorConsumption || 0))) & 0x1) << 1;
    bgVal |= ((Math.round((d.brokenSensor || 0))) & 0x1) << 0;
    writeU(buf, pos, 1, bgVal, endian);
    pos += 1;
    // encode byte_group
    var bgVal = 0;
    bgVal |= ((Math.round((d.childLock || 0))) & 0x1) << 7;
    bgVal |= ((Math.round((d.calibrationFailed || 0))) & 0x1) << 6;
    bgVal |= ((Math.round((d.attachedBackplate || 0))) & 0x1) << 5;
    bgVal |= ((Math.round((d.perceiveAsOnline || 0))) & 0x1) << 4;
    bgVal |= ((Math.round((d.antiFreezeProtection || 0))) & 0x1) << 3;
    writeU(buf, pos, 1, bgVal, endian);
    pos += 1;
    // skip computed field batteryVoltage
    // skip computed field _motorRangeHigh256
    // skip computed field motorRange
    // skip computed field _motorPositionHigh256
    // skip computed field motorPosition
    // skip computed field _motorPosPercent
    // skip computed field _motorPosRatio
    // skip computed field valveOpenness
    // skip computed field targetTemperatureFloat
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