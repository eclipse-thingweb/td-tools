// TS013 Payload Codec — milesight_uc300
// Schema version: 1
// Generated from: uc300.yaml
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
      if ("[" + channel_id + ", " + channel_type + "]" === "[3, 0]") {
        var digital_input_1 = readU(buf, pos, 1, endian);
        pos += 1;
        vars.digital_input_1 = digital_input_1;
        d.digital_input_1 = digital_input_1;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[4, 0]") {
        var digital_input_2 = readU(buf, pos, 1, endian);
        pos += 1;
        vars.digital_input_2 = digital_input_2;
        d.digital_input_2 = digital_input_2;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[5, 0]") {
        var digital_input_3 = readU(buf, pos, 1, endian);
        pos += 1;
        vars.digital_input_3 = digital_input_3;
        d.digital_input_3 = digital_input_3;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[6, 0]") {
        var digital_input_4 = readU(buf, pos, 1, endian);
        pos += 1;
        vars.digital_input_4 = digital_input_4;
        d.digital_input_4 = digital_input_4;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[7, 1]") {
        var digital_output_1 = readU(buf, pos, 1, endian);
        pos += 1;
        vars.digital_output_1 = digital_output_1;
        d.digital_output_1 = digital_output_1;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[8, 1]") {
        var digital_output_2 = readU(buf, pos, 1, endian);
        pos += 1;
        vars.digital_output_2 = digital_output_2;
        d.digital_output_2 = digital_output_2;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[3, 200]") {
        var pulse_count_1 = readU(buf, pos, 4, endian);
        pos += 4;
        vars.pulse_count_1 = pulse_count_1;
        d.pulse_count_1 = pulse_count_1;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[4, 200]") {
        var pulse_count_2 = readU(buf, pos, 4, endian);
        pos += 4;
        vars.pulse_count_2 = pulse_count_2;
        d.pulse_count_2 = pulse_count_2;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[5, 200]") {
        var pulse_count_3 = readU(buf, pos, 4, endian);
        pos += 4;
        vars.pulse_count_3 = pulse_count_3;
        d.pulse_count_3 = pulse_count_3;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[6, 200]") {
        var pulse_count_4 = readU(buf, pos, 4, endian);
        pos += 4;
        vars.pulse_count_4 = pulse_count_4;
        d.pulse_count_4 = pulse_count_4;
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[9, 103]") {
        var pt100_1 = readS(buf, pos, 2, endian);
        pos += 2;
        vars.pt100_1 = pt100_1;
        d.pt100_1 = (pt100_1 / 10);
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[10, 103]") {
        var pt100_2 = readS(buf, pos, 2, endian);
        pos += 2;
        vars.pt100_2 = pt100_2;
        d.pt100_2 = (pt100_2 / 10);
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[11, 2]") {
        var analog_input_adc_1 = readU(buf, pos, 4, endian);
        pos += 4;
        vars.analog_input_adc_1 = analog_input_adc_1;
        d.analog_input_adc_1 = (analog_input_adc_1 / 100);
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[12, 2]") {
        var analog_input_adc_2 = readU(buf, pos, 4, endian);
        pos += 4;
        vars.analog_input_adc_2 = analog_input_adc_2;
        d.analog_input_adc_2 = (analog_input_adc_2 / 100);
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[13, 2]") {
        var analog_input_adv_1 = readU(buf, pos, 4, endian);
        pos += 4;
        vars.analog_input_adv_1 = analog_input_adv_1;
        d.analog_input_adv_1 = (analog_input_adv_1 / 100);
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[14, 2]") {
        var analog_input_adv_2 = readU(buf, pos, 4, endian);
        pos += 4;
        vars.analog_input_adv_2 = analog_input_adv_2;
        d.analog_input_adv_2 = (analog_input_adv_2 / 100);
      } else if ("[" + channel_id + ", " + channel_type + "]" === "[255, 25]") {
        var modbus_channels = readU(buf, pos, 1, endian);
        pos += 1;
        vars.modbus_channels = modbus_channels;
        d.modbus_channels = modbus_channels;
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
    if (d.digital_input_1 !== undefined) {
      writeU(buf, pos, 1, 3, endian);
      pos += 1;
      writeU(buf, pos, 1, 0, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.digital_input_1 !== undefined ? d.digital_input_1 : 0)), endian);
      pos += 1;
    }
    if (d.digital_input_2 !== undefined) {
      writeU(buf, pos, 1, 4, endian);
      pos += 1;
      writeU(buf, pos, 1, 0, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.digital_input_2 !== undefined ? d.digital_input_2 : 0)), endian);
      pos += 1;
    }
    if (d.digital_input_3 !== undefined) {
      writeU(buf, pos, 1, 5, endian);
      pos += 1;
      writeU(buf, pos, 1, 0, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.digital_input_3 !== undefined ? d.digital_input_3 : 0)), endian);
      pos += 1;
    }
    if (d.digital_input_4 !== undefined) {
      writeU(buf, pos, 1, 6, endian);
      pos += 1;
      writeU(buf, pos, 1, 0, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.digital_input_4 !== undefined ? d.digital_input_4 : 0)), endian);
      pos += 1;
    }
    if (d.digital_output_1 !== undefined) {
      writeU(buf, pos, 1, 7, endian);
      pos += 1;
      writeU(buf, pos, 1, 1, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.digital_output_1 !== undefined ? d.digital_output_1 : 0)), endian);
      pos += 1;
    }
    if (d.digital_output_2 !== undefined) {
      writeU(buf, pos, 1, 8, endian);
      pos += 1;
      writeU(buf, pos, 1, 1, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.digital_output_2 !== undefined ? d.digital_output_2 : 0)), endian);
      pos += 1;
    }
    if (d.pulse_count_1 !== undefined) {
      writeU(buf, pos, 1, 3, endian);
      pos += 1;
      writeU(buf, pos, 1, 200, endian);
      pos += 1;
      writeU(buf, pos, 4, Math.round((d.pulse_count_1 !== undefined ? d.pulse_count_1 : 0)), endian);
      pos += 4;
    }
    if (d.pulse_count_2 !== undefined) {
      writeU(buf, pos, 1, 4, endian);
      pos += 1;
      writeU(buf, pos, 1, 200, endian);
      pos += 1;
      writeU(buf, pos, 4, Math.round((d.pulse_count_2 !== undefined ? d.pulse_count_2 : 0)), endian);
      pos += 4;
    }
    if (d.pulse_count_3 !== undefined) {
      writeU(buf, pos, 1, 5, endian);
      pos += 1;
      writeU(buf, pos, 1, 200, endian);
      pos += 1;
      writeU(buf, pos, 4, Math.round((d.pulse_count_3 !== undefined ? d.pulse_count_3 : 0)), endian);
      pos += 4;
    }
    if (d.pulse_count_4 !== undefined) {
      writeU(buf, pos, 1, 6, endian);
      pos += 1;
      writeU(buf, pos, 1, 200, endian);
      pos += 1;
      writeU(buf, pos, 4, Math.round((d.pulse_count_4 !== undefined ? d.pulse_count_4 : 0)), endian);
      pos += 4;
    }
    if (d.pt100_1 !== undefined) {
      writeU(buf, pos, 1, 9, endian);
      pos += 1;
      writeU(buf, pos, 1, 103, endian);
      pos += 1;
      writeS(buf, pos, 2, Math.round(((d.pt100_1 !== undefined ? d.pt100_1 : 0) * 10)), endian);
      pos += 2;
    }
    if (d.pt100_2 !== undefined) {
      writeU(buf, pos, 1, 10, endian);
      pos += 1;
      writeU(buf, pos, 1, 103, endian);
      pos += 1;
      writeS(buf, pos, 2, Math.round(((d.pt100_2 !== undefined ? d.pt100_2 : 0) * 10)), endian);
      pos += 2;
    }
    if (d.analog_input_adc_1 !== undefined) {
      writeU(buf, pos, 1, 11, endian);
      pos += 1;
      writeU(buf, pos, 1, 2, endian);
      pos += 1;
      writeU(buf, pos, 4, Math.round(((d.analog_input_adc_1 !== undefined ? d.analog_input_adc_1 : 0) * 100)), endian);
      pos += 4;
    }
    if (d.analog_input_adc_2 !== undefined) {
      writeU(buf, pos, 1, 12, endian);
      pos += 1;
      writeU(buf, pos, 1, 2, endian);
      pos += 1;
      writeU(buf, pos, 4, Math.round(((d.analog_input_adc_2 !== undefined ? d.analog_input_adc_2 : 0) * 100)), endian);
      pos += 4;
    }
    if (d.analog_input_adv_1 !== undefined) {
      writeU(buf, pos, 1, 13, endian);
      pos += 1;
      writeU(buf, pos, 1, 2, endian);
      pos += 1;
      writeU(buf, pos, 4, Math.round(((d.analog_input_adv_1 !== undefined ? d.analog_input_adv_1 : 0) * 100)), endian);
      pos += 4;
    }
    if (d.analog_input_adv_2 !== undefined) {
      writeU(buf, pos, 1, 14, endian);
      pos += 1;
      writeU(buf, pos, 1, 2, endian);
      pos += 1;
      writeU(buf, pos, 4, Math.round(((d.analog_input_adv_2 !== undefined ? d.analog_input_adv_2 : 0) * 100)), endian);
      pos += 4;
    }
    if (d.modbus_channels !== undefined) {
      writeU(buf, pos, 1, 255, endian);
      pos += 1;
      writeU(buf, pos, 1, 25, endian);
      pos += 1;
      writeU(buf, pos, 1, Math.round((d.modbus_channels !== undefined ? d.modbus_channels : 0)), endian);
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