// Copyright (c) 2024-2026 Multitech Systems, Inc.
// SPDX-License-Identifier: MIT

using System.Buffers.Binary;

namespace PayloadSchema;

public static class Helpers
{
    public static ulong DecodeUint(ReadOnlySpan<byte> data, string endian)
    {
        ulong val = 0;
        if (endian == "little")
        {
            for (int i = data.Length - 1; i >= 0; i--)
                val = (val << 8) | data[i];
        }
        else
        {
            for (int i = 0; i < data.Length; i++)
                val = (val << 8) | data[i];
        }
        return val;
    }

    public static long DecodeSint(ReadOnlySpan<byte> data, string endian)
    {
        ulong uval = DecodeUint(data, endian);
        int bits = data.Length * 8;
        ulong signBit = 1UL << (bits - 1);
        if (uval >= signBit)
            return (long)uval - (1L << bits);
        return (long)uval;
    }

    public static double DecodeFloat(ReadOnlySpan<byte> data, int size, string endian)
    {
        return size switch
        {
            2 => Float16ToFloat64(endian == "little"
                ? BinaryPrimitives.ReadUInt16LittleEndian(data)
                : BinaryPrimitives.ReadUInt16BigEndian(data)),
            4 => (double)BitConverter.Int32BitsToSingle(
                (int)(endian == "little"
                    ? BinaryPrimitives.ReadUInt32LittleEndian(data)
                    : BinaryPrimitives.ReadUInt32BigEndian(data))),
            8 => BitConverter.Int64BitsToDouble(
                (long)(endian == "little"
                    ? BinaryPrimitives.ReadUInt64LittleEndian(data)
                    : BinaryPrimitives.ReadUInt64BigEndian(data))),
            _ => throw new ArgumentException($"Unsupported float size: {size}")
        };
    }

    public static double Float16ToFloat64(ushort u16)
    {
        int sign = (u16 >> 15) & 1;
        int exp = (u16 >> 10) & 0x1f;
        int mant = u16 & 0x3ff;

        double val;
        if (exp == 0)
            val = Math.Pow(2, -14) * mant / 1024.0;
        else if (exp == 31)
            return mant != 0 ? double.NaN : double.PositiveInfinity * (sign == 1 ? -1 : 1);
        else
            val = Math.Pow(2, exp - 15) * (1.0 + mant / 1024.0);

        return sign == 1 ? -val : val;
    }

    public static int DecodeBits(byte byteVal, int bitOffset, int bits)
    {
        int mask = (1 << bits) - 1;
        return (byteVal >> bitOffset) & mask;
    }

    public static byte[] EncodeUint(ulong val, int length, string endian)
    {
        var buf = new byte[length];
        if (endian == "little")
        {
            for (int i = 0; i < length; i++)
            {
                buf[i] = (byte)(val & 0xFF);
                val >>= 8;
            }
        }
        else
        {
            for (int i = length - 1; i >= 0; i--)
            {
                buf[i] = (byte)(val & 0xFF);
                val >>= 8;
            }
        }
        return buf;
    }

    public static byte[] EncodeSint(long val, int length, string endian)
    {
        if (val < 0)
            val = (1L << (length * 8)) + val;
        return EncodeUint((ulong)val, length, endian);
    }

    public static byte[] EncodeFloat32(float val, string endian)
    {
        var buf = new byte[4];
        uint bits = BitConverter.SingleToUInt32Bits(val);
        if (endian == "little")
            BinaryPrimitives.WriteUInt32LittleEndian(buf, bits);
        else
            BinaryPrimitives.WriteUInt32BigEndian(buf, bits);
        return buf;
    }

    public static byte[] EncodeFloat64(double val, string endian)
    {
        var buf = new byte[8];
        ulong bits = BitConverter.DoubleToUInt64Bits(val);
        if (endian == "little")
            BinaryPrimitives.WriteUInt64LittleEndian(buf, bits);
        else
            BinaryPrimitives.WriteUInt64BigEndian(buf, bits);
        return buf;
    }

    public static int InferLengthFromType(FieldType type) => type switch
    {
        FieldType.U8 or FieldType.S8 => 1,
        FieldType.U16 or FieldType.S16 or FieldType.F16 => 2,
        FieldType.U24 or FieldType.S24 => 3,
        FieldType.U32 or FieldType.S32 or FieldType.F32 => 4,
        FieldType.U64 or FieldType.S64 or FieldType.F64 => 8,
        _ => 1
    };

    public static (bool ok, double value) ToFloat64(object? v)
    {
        return v switch
        {
            double d => (true, d),
            float f => (true, f),
            int i => (true, i),
            long l => (true, l),
            ulong u => (true, u),
            uint ui => (true, ui),
            short s => (true, s),
            ushort us => (true, us),
            byte b => (true, b),
            sbyte sb => (true, sb),
            decimal dec => (true, (double)dec),
            _ => (false, 0)
        };
    }

    public static (bool ok, int value) ToInt(object? v)
    {
        var (ok, d) = ToFloat64(v);
        return ok ? (true, (int)d) : (false, 0);
    }

    public static object FormatBytes(byte[] data, string? format, string? separator)
    {
        format ??= "hex";
        return format switch
        {
            "hex" or "hex:lower" => separator != null
                ? string.Join(separator, data.Select(b => b.ToString("x2")))
                : Convert.ToHexString(data).ToLowerInvariant(),
            "hex:upper" => separator != null
                ? string.Join(separator, data.Select(b => b.ToString("X2")))
                : Convert.ToHexString(data),
            "base64" => Convert.ToBase64String(data),
            "array" => data.Select(b => (object)(double)b).ToList(),
            _ => Convert.ToHexString(data).ToLowerInvariant()
        };
    }

    public static FieldType ParseFieldType(string typeStr)
    {
        var baseType = typeStr.Contains('[') ? typeStr[..typeStr.IndexOf('[')] : typeStr;
        if (baseType.StartsWith("le_") || baseType.StartsWith("be_"))
            baseType = baseType[3..];

        return baseType.ToLowerInvariant() switch
        {
            "u8" or "byte" or "uint" => FieldType.U8,
            "u16" => FieldType.U16,
            "u24" => FieldType.U24,
            "u32" => FieldType.U32,
            "u64" => FieldType.U64,
            "s8" or "i8" => FieldType.S8,
            "s16" or "i16" => FieldType.S16,
            "s24" => FieldType.S24,
            "s32" or "i32" => FieldType.S32,
            "s64" or "i64" => FieldType.S64,
            "f16" or "float16" => FieldType.F16,
            "f32" or "float32" => FieldType.F32,
            "f64" or "float64" => FieldType.F64,
            "bool" => FieldType.Bool,
            "bits" => FieldType.Bits,
            "ascii" => FieldType.Ascii,
            "hex" => FieldType.Hex,
            "bytes" => FieldType.Bytes,
            "skip" => FieldType.Skip,
            "string" => FieldType.String,
            "number" => FieldType.Number,
            "object" => FieldType.Object,
            "match" or "ctrl-switch" or "switch" => FieldType.Match,
            "tlv" => FieldType.TLV,
            "repeat" => FieldType.Repeat,
            "enum" => FieldType.Enum,
            "bitfield_string" or "version_string" => FieldType.BitfieldString,
            _ => FieldType.Unknown
        };
    }

    /// <summary>Parse bitfield range from type string like "u8[3:7]" -> (3, 7)</summary>
    public static (int start, int end)? ParseBitRange(string typeStr)
    {
        int idx = typeStr.IndexOf('[');
        if (idx < 0) return null;
        var range = typeStr[(idx + 1)..typeStr.IndexOf(']')];
        var parts = range.Split(':');
        if (parts.Length != 2) return null;
        return (int.Parse(parts[0]), int.Parse(parts[1]));
    }

    /// <summary>Parse endian prefix from type like "le_u16" -> ("little", "u16")</summary>
    public static (string? endian, string baseType) ParseEndianPrefix(string typeStr)
    {
        if (typeStr.StartsWith("le_"))
            return ("little", typeStr[3..]);
        if (typeStr.StartsWith("be_"))
            return ("big", typeStr[3..]);
        return (null, typeStr);
    }

    public static double EvaluatePolynomial(double[] coeffs, double x)
    {
        if (coeffs.Length == 0) return 0;
        double result = coeffs[0];
        for (int i = 1; i < coeffs.Length; i++)
            result = result * x + coeffs[i];
        return result;
    }
}
