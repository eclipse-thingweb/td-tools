// Copyright (c) 2024-2026 Multitech Systems, Inc.
// SPDX-License-Identifier: MIT

using System.Globalization;
using Xunit;
using Xunit.Abstractions;
using YamlDotNet.RepresentationModel;

namespace PayloadSchema.Tests;

/// <summary>
/// Conformance tests that load real device YAML schemas and run their
/// embedded test_vectors. This is the gold-standard cross-language test:
/// same schemas, same test vectors, same expected results as Python/Go/C.
/// </summary>
public class DeviceSchemaTests
{
    private readonly ITestOutputHelper _output;

    public DeviceSchemaTests(ITestOutputHelper output) => _output = output;

    static string SchemasRoot => FindSchemasRoot();

    static string FindSchemasRoot()
    {
        // Walk up from test assembly to find payload-codec-proto/schemas
        var dir = AppContext.BaseDirectory;
        for (int i = 0; i < 10; i++)
        {
            var candidate = Path.Combine(dir, "schemas", "devices");
            if (Directory.Exists(candidate)) return Path.Combine(dir, "schemas");
            var candidate2 = Path.Combine(dir, "..", "..", "..", "..", "..", "schemas");
            if (Directory.Exists(Path.Combine(candidate2, "devices")))
                return Path.GetFullPath(candidate2);
            dir = Path.GetDirectoryName(dir)!;
        }
        // Fallback: relative from workspace
        var fallback = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "schemas"));
        if (Directory.Exists(fallback)) return fallback;
        throw new DirectoryNotFoundException("Cannot find schemas directory");
    }

    [Fact]
    public void Decentlab_DL5TM_AllVectors()
    {
        RunSchemaTestVectors(Path.Combine(SchemasRoot, "devices", "decentlab", "dl-5tm.yaml"));
    }

    [Fact]
    public void Elsys_ERS_AllVectors()
    {
        RunSchemaTestVectors(Path.Combine(SchemasRoot, "devices", "elsys", "ers.yaml"));
    }

    void RunSchemaTestVectors(string schemaPath)
    {
        if (!File.Exists(schemaPath))
        {
            _output.WriteLine($"Schema file not found, skipping: {schemaPath}");
            return;
        }

        var yamlText = File.ReadAllText(schemaPath);
        var schema = SchemaParser.Parse(yamlText);

        // Parse test_vectors from raw YAML
        var yaml = new YamlStream();
        yaml.Load(new StringReader(yamlText));
        var root = (YamlMappingNode)yaml.Documents[0].RootNode;

        if (!TryGetValue(root, "test_vectors", out var tvNode) || tvNode is not YamlSequenceNode tvSeq)
        {
            _output.WriteLine("No test_vectors found in schema");
            return;
        }

        int passed = 0;
        foreach (var tv in tvSeq.Children)
        {
            if (tv is not YamlMappingNode tvMap) continue;
            var testName = TryGetValue(tvMap, "name", out var n) ? Scalar(n) : "unnamed";
            var payloadHex = TryGetValue(tvMap, "payload", out var p) ? Scalar(p) : "";
            if (!TryGetValue(tvMap, "expected", out var expNode) || expNode is not YamlMappingNode expectedMap)
                continue;

            // Parse fPort if present
            int fPort = 0;
            if (TryGetValue(tvMap, "fport", out var fp) || TryGetValue(tvMap, "fPort", out fp))
                fPort = int.TryParse(Scalar(fp), out int fpi) ? fpi : 0;

            var payloadBytes = ParseHexPayload(payloadHex);
            _output.WriteLine($"Running test vector: {testName} ({payloadBytes.Length} bytes)");

            Dictionary<string, object?> result;
            if (fPort > 0)
                result = SchemaDecoder.DecodeWithPort(schema, payloadBytes, fPort);
            else
                result = SchemaDecoder.Decode(schema, payloadBytes);

            // Compare each expected field
            foreach (var kv in expectedMap.Children)
            {
                var fieldName = Scalar(kv.Key);
                var expectedValue = ParseExpectedValue(kv.Value);

                Assert.True(result.ContainsKey(fieldName),
                    $"[{testName}] Missing field '{fieldName}' in decoded result. Got: {string.Join(", ", result.Keys)}");

                var actual = result[fieldName];
                AssertValueEqual(expectedValue, actual, fieldName, testName);
            }

            passed++;
            _output.WriteLine($"  PASS: {testName}");
        }

        _output.WriteLine($"\n{passed} test vectors passed for {Path.GetFileName(schemaPath)}");
        Assert.True(passed > 0, "No test vectors were executed");
    }

    void AssertValueEqual(object? expected, object? actual, string fieldName, string testName)
    {
        if (expected is double expD)
        {
            var (ok, actD) = Helpers.ToFloat64(actual);
            Assert.True(ok, $"[{testName}] Field '{fieldName}': expected numeric {expD} but got {actual?.GetType().Name}");

            // Use relative tolerance for very small values, absolute for larger
            double tolerance = Math.Max(Math.Abs(expD) * 0.01, 0.005);
            Assert.True(Math.Abs(expD - actD) < tolerance,
                $"[{testName}] Field '{fieldName}': expected {expD} but got {actD} (tolerance {tolerance})");
        }
        else if (expected is int expI)
        {
            var (ok, actD) = Helpers.ToFloat64(actual);
            Assert.True(ok, $"[{testName}] Field '{fieldName}': expected {expI} but got {actual?.GetType().Name}");
            Assert.Equal((double)expI, actD);
        }
        else if (expected is string expS)
        {
            Assert.Equal(expS, actual?.ToString());
        }
        else if (expected is bool expB)
        {
            Assert.Equal(expB, actual);
        }
    }

    static int CountDecimalPlaces(double d)
    {
        var s = d.ToString(CultureInfo.InvariantCulture);
        int idx = s.IndexOf('.');
        return idx < 0 ? 0 : s.Length - idx - 1;
    }

    static byte[] ParseHexPayload(string hex)
    {
        hex = hex.Replace(" ", "").Replace("-", "").Replace(":", "");
        if (hex.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
            hex = hex[2..];
        var bytes = new byte[hex.Length / 2];
        for (int i = 0; i < bytes.Length; i++)
            bytes[i] = byte.Parse(hex.Substring(i * 2, 2), NumberStyles.HexNumber);
        return bytes;
    }

    static object? ParseExpectedValue(YamlNode node)
    {
        if (node is YamlScalarNode scalar)
        {
            var s = scalar.Value ?? "";
            if (s.StartsWith("0x", StringComparison.OrdinalIgnoreCase) &&
                int.TryParse(s[2..], NumberStyles.HexNumber, CultureInfo.InvariantCulture, out int hex))
                return (double)hex;
            if (int.TryParse(s, out int i)) return i;
            if (double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out double d)) return d;
            if (s == "true") return true;
            if (s == "false") return false;
            return s;
        }
        return null;
    }

    static string Scalar(YamlNode node) => node is YamlScalarNode s ? s.Value ?? "" : "";

    static bool TryGetValue(YamlMappingNode map, string key, out YamlNode value)
    {
        foreach (var kv in map.Children)
        {
            if (kv.Key is YamlScalarNode scalar && scalar.Value == key)
            {
                value = kv.Value;
                return true;
            }
        }
        value = null!;
        return false;
    }
}
