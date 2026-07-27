// Copyright (c) 2024-2026 Multitech Systems, Inc.
// SPDX-License-Identifier: MIT

using Xunit;

namespace PayloadSchema.Tests;

public class DecodeUintTests
{
    [Theory]
    [InlineData(new byte[] { 0xFF }, "big", 255UL)]
    [InlineData(new byte[] { 0x01, 0x00 }, "big", 256UL)]
    [InlineData(new byte[] { 0x00, 0x01 }, "little", 256UL)]
    [InlineData(new byte[] { 0x00, 0x01, 0x00, 0x00 }, "big", 65536UL)]
    public void DecodeUint(byte[] data, string endian, ulong expected)
    {
        Assert.Equal(expected, Helpers.DecodeUint(data, endian));
    }
}

public class DecodeSintTests
{
    [Theory]
    [InlineData(new byte[] { 0x7F }, "big", 127L)]
    [InlineData(new byte[] { 0xFF }, "big", -1L)]
    [InlineData(new byte[] { 0xFF, 0xFE }, "big", -2L)]
    public void DecodeSint(byte[] data, string endian, long expected)
    {
        Assert.Equal(expected, Helpers.DecodeSint(data, endian));
    }
}

public class DecodeBitsTests
{
    [Theory]
    [InlineData(0xB4, 0, 2, 0)]
    [InlineData(0xB4, 2, 4, 13)]
    [InlineData(0xB4, 6, 2, 2)]
    public void DecodeBits(byte val, int offset, int bits, int expected)
    {
        Assert.Equal(expected, Helpers.DecodeBits(val, offset, bits));
    }
}

public class DecodeSimpleSchemaTests
{
    [Fact]
    public void DecodeU16AndU8()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: temperature
    type: u16
  - name: humidity
    type: u8
");
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x01, 0xF4, 0x32 });
        Assert.Equal(500.0, result["temperature"]);
        Assert.Equal(50.0, result["humidity"]);
    }

    [Fact]
    public void DecodeLittleEndianU16()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: little
fields:
  - name: value
    type: u16
");
        var result = SchemaDecoder.Decode(schema, new byte[] { 0xF4, 0x01 });
        Assert.Equal(500.0, result["value"]);
    }

    [Fact]
    public void DecodeSigned()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: temp
    type: s16
");
        // -100 in big-endian s16: 0xFF9C
        var result = SchemaDecoder.Decode(schema, new byte[] { 0xFF, 0x9C });
        Assert.Equal(-100.0, result["temp"]);
    }

    [Fact]
    public void DecodeU24()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: val
    type: u24
");
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x01, 0x00, 0x00 });
        Assert.Equal(65536.0, result["val"]);
    }

    [Fact]
    public void DecodeFloat32()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: temp
    type: f32
");
        // 23.45 as IEEE 754 big-endian
        var bytes = BitConverter.GetBytes(23.45f);
        if (BitConverter.IsLittleEndian)
            Array.Reverse(bytes);
        var result = SchemaDecoder.Decode(schema, bytes);
        Assert.Equal(23.45, (double)result["temp"]!, 2);
    }

    [Fact]
    public void DecodeBool()
    {
        var schema = SchemaParser.Parse(@"
name: test
fields:
  - name: flag0
    type: bool
    bit: 0
    consume: 0
  - name: flag1
    type: bool
    bit: 1
    consume: 0
  - name: flag7
    type: bool
    bit: 7
    consume: 1
");
        // 0x83 = 10000011
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x83 });
        Assert.True((bool)result["flag0"]!);
        Assert.True((bool)result["flag1"]!);
        Assert.True((bool)result["flag7"]!);
    }

    [Fact]
    public void DecodeEnum()
    {
        var schema = SchemaParser.Parse(@"
name: test
fields:
  - name: status
    type: enum
    base: u8
    values:
      0: 'off'
      1: 'on'
      2: 'error'
");
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x01 });
        Assert.Equal("on", result["status"]);
    }

    [Fact]
    public void DecodeHex()
    {
        var schema = SchemaParser.Parse(@"
name: test
fields:
  - name: eui
    type: hex
    length: 8
");
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x00, 0x80, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03 });
        Assert.Equal("0080000000010203", result["eui"]);
    }

    [Fact]
    public void DecodeAscii()
    {
        var schema = SchemaParser.Parse(@"
name: test
fields:
  - name: label
    type: ascii
    length: 5
");
        var result = SchemaDecoder.Decode(schema, "Hello"u8.ToArray());
        Assert.Equal("Hello", result["label"]);
    }

    [Fact]
    public void DecodeSkip()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: _pad
    type: skip
    length: 2
  - name: value
    type: u8
");
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x00, 0x00, 0x42 });
        Assert.Equal(66.0, result["value"]);
        Assert.False(result.ContainsKey("_pad"));
    }

    [Fact]
    public void DecodeEndianPrefix()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: le_val
    type: le_u16
  - name: be_val
    type: be_u16
");
        var result = SchemaDecoder.Decode(schema, new byte[] { 0xF4, 0x01, 0x01, 0xF4 });
        Assert.Equal(500.0, result["le_val"]);
        Assert.Equal(500.0, result["be_val"]);
    }
}

public class ModifierTests
{
    [Fact]
    public void DivModifier()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: temp
    type: u16
    div: 10
");
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x00, 0xE7 }); // 231
        Assert.Equal(23.1, (double)result["temp"]!, 10);
    }

    [Fact]
    public void MultModifier()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: temp
    type: u16
    mult: 0.01
");
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x09, 0x29 }); // 2345
        Assert.Equal(23.45, (double)result["temp"]!, 10);
    }

    [Fact]
    public void YamlKeyOrderMatters()
    {
        // div then add: (raw / 10) + (-40)
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: temp
    type: s16
    div: 10
    add: -40
");
        // raw = 634  -> 634/10 - 40 = 23.4
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x02, 0x7A }); // 634
        Assert.Equal(23.4, (double)result["temp"]!, 10);
    }

    [Fact]
    public void TransformArray()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: temp
    type: u16
    transform:
      - add: -400
      - div: 10
");
        // raw=630  -> (630-400)/10 = 23.0
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x02, 0x76 }); // 630
        Assert.Equal(23.0, (double)result["temp"]!, 10);
    }

    [Fact]
    public void LookupTable()
    {
        var schema = SchemaParser.Parse(@"
name: test
fields:
  - name: status
    type: u8
    lookup:
      0: 'off'
      1: 'on'
      2: 'error'
");
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x02 });
        Assert.Equal("error", result["status"]);
    }
}

public class ConditionalTests
{
    [Fact]
    public void MatchSwitch()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: msg_type
    type: u8
    var: msg_type
  - type: match
    on: $msg_type
    cases:
      - case: 1
        fields:
          - name: temperature
            type: s16
      - case: 2
        fields:
          - name: humidity
            type: u8
");
        // msg_type=1, temp=-10 (0xFFF6)
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x01, 0xFF, 0xF6 });
        Assert.Equal(1.0, result["msg_type"]);
        Assert.Equal(-10.0, result["temperature"]);
        Assert.False(result.ContainsKey("humidity"));
    }

    [Fact]
    public void FlaggedConstruct()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: flags
    type: u8
  - flagged:
      field: flags
      groups:
        - bit: 0
          fields:
            - name: temperature
              type: s16
        - bit: 1
          fields:
            - name: humidity
              type: u8
");
        // flags=0x03 (both bits set), temp=250, hum=65
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x03, 0x00, 0xFA, 0x41 });
        Assert.Equal(3.0, result["flags"]);
        Assert.Equal(250.0, result["temperature"]);
        Assert.Equal(65.0, result["humidity"]);
    }

    [Fact]
    public void FlaggedPartial()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: flags
    type: u8
  - flagged:
      field: flags
      groups:
        - bit: 0
          fields:
            - name: temperature
              type: s16
        - bit: 1
          fields:
            - name: humidity
              type: u8
");
        // flags=0x02 (only bit 1), hum=65
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x02, 0x41 });
        Assert.Equal(2.0, result["flags"]);
        Assert.False(result.ContainsKey("temperature"));
        Assert.Equal(65.0, result["humidity"]);
    }
}

public class RepeatTests
{
    [Fact]
    public void CountBased()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: readings
    type: repeat
    count: 3
    fields:
      - name: value
        type: u16
");
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x00, 0x01, 0x00, 0x02, 0x00, 0x03 });
        var readings = (List<object?>)result["readings"]!;
        Assert.Equal(3, readings.Count);
        var r0 = (Dictionary<string, object?>)readings[0]!;
        Assert.Equal(1.0, r0["value"]);
    }

    [Fact]
    public void CountFromVariable()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: count
    type: u8
  - name: items
    type: repeat
    count: $count
    fields:
      - name: val
        type: u8
");
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x02, 0x0A, 0x0B });
        var items = (List<object?>)result["items"]!;
        Assert.Equal(2, items.Count);
    }

    [Fact]
    public void UntilEnd()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: entries
    type: repeat
    until: end
    fields:
      - name: val
        type: u16
");
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x00, 0x01, 0x00, 0x02 });
        var entries = (List<object?>)result["entries"]!;
        Assert.Equal(2, entries.Count);
    }
}

public class ComputedFieldTests
{
    [Fact]
    public void RefWithPolynomial()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: raw
    type: u16
    div: 50
  - name: calibrated
    type: number
    ref: $raw
    polynomial: [0.0000043, -0.00055, 0.0292, -0.053]
");
        // raw = 500 -> /50 = 10.0 -> polynomial(10.0)
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x01, 0xF4 });
        Assert.Equal(10.0, (double)result["raw"]!);
        var cal = (double)result["calibrated"]!;
        // polynomial: 0.0000043*1000 - 0.00055*100 + 0.0292*10 - 0.053
        //           = 0.0043 - 0.055 + 0.292 - 0.053 = 0.1883
        Assert.Equal(0.1883, cal, 3);
    }

    [Fact]
    public void RefWithTransform()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: raw
    type: u16
  - name: adjusted
    type: number
    ref: $raw
    transform:
      - add: -400
      - div: 10
");
        // raw=550 -> (550 - 400) / 10 = 15.0
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x02, 0x26 });
        Assert.Equal(15.0, (double)result["adjusted"]!);
    }

    [Fact]
    public void ComputeDiv()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: a
    type: u16
  - name: b
    type: u16
  - name: ratio
    type: number
    compute:
      op: div
      a: $a
      b: $b
");
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x00, 0x64, 0x00, 0x0A }); // 100, 10
        Assert.Equal(10.0, (double)result["ratio"]!);
    }

    [Fact]
    public void GuardCondition()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: denom
    type: u16
  - name: numer
    type: u16
  - name: ratio
    type: number
    compute:
      op: div
      a: $numer
      b: $denom
    guard:
      when:
        - field: $denom
          gt: 0
      else: 0
");
        // denom=0, numer=100 -> guard returns 0
        var result = SchemaDecoder.Decode(schema, new byte[] { 0x00, 0x00, 0x00, 0x64 });
        Assert.Equal(0.0, (double)result["ratio"]!);
    }
}

public class ObjectTests
{
    [Fact]
    public void NestedObject()
    {
        var schema = SchemaParser.Parse(@"
name: test
endian: big
fields:
  - name: gps
    type: object
    fields:
      - name: latitude
        type: s32
        div: 10000000
      - name: longitude
        type: s32
        div: 10000000
");
        // lat = 43.6532 * 10000000 = 436532000 = 0x1A04A620
        // lon = -79.3832 * 10000000 = -793832000
        var buf = new byte[8];
        Array.Copy(Helpers.EncodeUint(436532000, 4, "big"), 0, buf, 0, 4);
        long lonRaw = -793832000;
        Array.Copy(Helpers.EncodeSint(lonRaw, 4, "big"), 0, buf, 4, 4);

        var result = SchemaDecoder.Decode(schema, buf);
        var gps = (Dictionary<string, object?>)result["gps"]!;
        Assert.Equal(43.6532, (double)gps["latitude"]!, 4);
        Assert.Equal(-79.3832, (double)gps["longitude"]!, 4);
    }
}

public class PortTests
{
    [Fact]
    public void PortBasedRouting()
    {
        var schema = SchemaParser.Parse(@"
name: test
ports:
  1:
    description: Sensor data
    fields:
      - name: temperature
        type: s16
  2:
    description: Status
    fields:
      - name: battery
        type: u8
");
        var r1 = SchemaDecoder.DecodeWithPort(schema, new byte[] { 0x00, 0xE7 }, 1);
        Assert.Equal(231.0, r1["temperature"]);

        var r2 = SchemaDecoder.DecodeWithPort(schema, new byte[] { 0x64 }, 2);
        Assert.Equal(100.0, r2["battery"]);
    }
}
