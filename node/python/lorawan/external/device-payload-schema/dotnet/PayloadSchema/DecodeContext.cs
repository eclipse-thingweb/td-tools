// Copyright (c) 2024-2026 Multitech Systems, Inc.
// SPDX-License-Identifier: MIT

namespace PayloadSchema;

public class DecodeContext
{
    public byte[] Data { get; }
    public int Offset { get; set; }
    public string Endian { get; }
    public Dictionary<string, object?> Variables { get; } = new();
    public Dictionary<string, string> Quality { get; } = new();
    public List<string> Warnings { get; } = new();

    public DecodeContext(byte[] data, string endian = "big")
    {
        Data = data;
        Endian = string.IsNullOrEmpty(endian) ? "big" : endian;
    }

    public int Remaining => Data.Length - Offset;

    public ReadOnlySpan<byte> Read(int n)
    {
        if (Offset + n > Data.Length)
            throw new InvalidOperationException(
                $"Buffer underflow: need {n} bytes at offset {Offset}, but only {Remaining} remaining");
        var result = Data.AsSpan(Offset, n);
        Offset += n;
        return result;
    }

    public ReadOnlySpan<byte> Peek(int n, int relativeOffset = 0)
    {
        int pos = Offset + relativeOffset;
        if (pos + n > Data.Length)
            throw new InvalidOperationException($"Buffer underflow at peek offset {pos}");
        return Data.AsSpan(pos, n);
    }

    public string CheckValidRange(object? value, SchemaField field)
    {
        if (field.ValidRange == null || field.ValidRange.Length < 2)
            return "good";

        var (ok, numVal) = Helpers.ToFloat64(value);
        if (!ok) return "good";

        double min = field.ValidRange[0], max = field.ValidRange[1];
        if (numVal < min || numVal > max)
        {
            var warning = $"{field.Name}: value {numVal} outside valid range [{min}, {max}]";
            Warnings.Add(warning);
            Quality[field.Name] = "out_of_range";
            return "out_of_range";
        }

        Quality[field.Name] = "good";
        return "good";
    }
}
