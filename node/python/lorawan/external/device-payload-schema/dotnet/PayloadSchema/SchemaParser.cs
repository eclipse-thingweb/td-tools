// Copyright (c) 2024-2026 Multitech Systems, Inc.
// SPDX-License-Identifier: MIT

using System.Globalization;
using YamlDotNet.RepresentationModel;

namespace PayloadSchema;

public static class SchemaParser
{
    public static PayloadSchemaDefinition Parse(string yamlOrJson)
    {
        var yaml = new YamlStream();
        yaml.Load(new StringReader(yamlOrJson));
        var root = (YamlMappingNode)yaml.Documents[0].RootNode;
        return ParseRoot(root);
    }

    static PayloadSchemaDefinition ParseRoot(YamlMappingNode root)
    {
        var schema = new PayloadSchemaDefinition();

        if (root.TryGetValue("name", out var name))
            schema.Name = Scalar(name);
        if (root.TryGetValue("version", out var ver))
            schema.Version = Int(ver);
        if (root.TryGetValue("description", out var desc))
            schema.Description = Scalar(desc);
        if (root.TryGetValue("endian", out var endian))
            schema.Endian = Scalar(endian);
        if (string.IsNullOrEmpty(schema.Endian))
            schema.Endian = "big";

        if (root.TryGetValue("header", out var header) && header is YamlSequenceNode headerSeq)
            schema.Header = ParseFields(headerSeq);

        if (root.TryGetValue("fields", out var fields) && fields is YamlSequenceNode fieldsSeq)
            schema.Fields = ParseFields(fieldsSeq);

        if (root.TryGetValue("definitions", out var defs) && defs is YamlMappingNode defsMap)
        {
            schema.Definitions = new Dictionary<string, DefinitionDef>();
            foreach (var kv in defsMap.Children)
            {
                var defName = Scalar(kv.Key);
                if (kv.Value is YamlMappingNode defMap)
                {
                    var dd = new DefinitionDef();
                    if (defMap.TryGetValue("fields", out var defFields) && defFields is YamlSequenceNode defFieldsSeq)
                        dd.Fields = ParseFields(defFieldsSeq);
                    schema.Definitions[defName] = dd;
                }
            }
        }

        if (root.TryGetValue("ports", out var ports) && ports is YamlMappingNode portsMap)
        {
            schema.Ports = new Dictionary<string, PortDef>();
            foreach (var kv in portsMap.Children)
            {
                var portKey = Scalar(kv.Key);
                if (kv.Value is YamlMappingNode portMap)
                {
                    var pd = new PortDef();
                    if (portMap.TryGetValue("direction", out var dir))
                        pd.Direction = Scalar(dir);
                    if (portMap.TryGetValue("description", out var pdesc))
                        pd.Description = Scalar(pdesc);
                    if (portMap.TryGetValue("fields", out var pf) && pf is YamlSequenceNode pfSeq)
                        pd.Fields = ParseFields(pfSeq);
                    schema.Ports[portKey] = pd;
                }
            }
        }

        return schema;
    }

    static List<SchemaField> ParseFields(YamlSequenceNode seq)
    {
        var fields = new List<SchemaField>();
        foreach (var item in seq.Children)
        {
            if (item is YamlMappingNode fieldMap)
                fields.Add(ParseField(fieldMap));
        }
        return fields;
    }

    static SchemaField ParseField(YamlMappingNode fm)
    {
        var f = new SchemaField();

        if (fm.TryGetValue("name", out var name))
            f.Name = Scalar(name);

        if (fm.TryGetValue("type", out var typeNode))
        {
            f.RawType = Scalar(typeNode);
            var (endianPrefix, baseType) = Helpers.ParseEndianPrefix(f.RawType);
            if (endianPrefix != null)
                f.Endian = endianPrefix;

            var bitRange = Helpers.ParseBitRange(f.RawType);
            if (bitRange != null)
            {
                f.BitOffset = bitRange.Value.start;
                f.BitCount = bitRange.Value.end - bitRange.Value.start + 1;
            }

            f.Type = Helpers.ParseFieldType(f.RawType);
        }

        if (fm.TryGetValue("length", out var len))
            f.Length = Int(len);
        if (fm.TryGetValue("endian", out var endian))
            f.Endian = Scalar(endian);

        // Modifiers -- track YAML key order
        foreach (var kv in fm.Children)
        {
            var key = Scalar(kv.Key);
            if (key is "add" or "mult" or "div")
                f.ModOrder.Add(key);
        }
        if (fm.TryGetValue("add", out var addV))
            f.Add = Double(addV);
        if (fm.TryGetValue("mult", out var multV))
            f.Mult = Double(multV);
        if (fm.TryGetValue("div", out var divV))
            f.Div = Double(divV);

        // Transform array
        if (fm.TryGetValue("transform", out var transformNode) && transformNode is YamlSequenceNode transformSeq)
        {
            foreach (var tItem in transformSeq.Children)
            {
                if (tItem is YamlMappingNode tMap)
                {
                    var stage = new TransformStage();
                    if (tMap.TryGetValue("add", out var ta)) stage.Add = Double(ta);
                    if (tMap.TryGetValue("sub", out var ts)) stage.Sub = Double(ts);
                    if (tMap.TryGetValue("mult", out var tm)) stage.Mult = Double(tm);
                    if (tMap.TryGetValue("div", out var td)) stage.Div = Double(td);
                    f.Transform.Add(stage);
                }
            }
        }

        if (fm.TryGetValue("var", out var varNode))
            f.Var = Scalar(varNode);
        if (fm.TryGetValue("on", out var onNode))
            f.On = Scalar(onNode);
        if (fm.TryGetValue("value", out var valueNode))
            f.Value = ParseScalarValue(valueNode);

        // Lookup table
        if (fm.TryGetValue("lookup", out var lookupNode))
        {
            if (lookupNode is YamlMappingNode lookupMap)
            {
                f.Lookup = new Dictionary<int, string>();
                foreach (var kv in lookupMap.Children)
                {
                    if (int.TryParse(Scalar(kv.Key), out int key))
                        f.Lookup[key] = Scalar(kv.Value);
                }
            }
            else if (lookupNode is YamlSequenceNode lookupArr)
            {
                f.Lookup = new Dictionary<int, string>();
                for (int i = 0; i < lookupArr.Children.Count; i++)
                    f.Lookup[i] = Scalar(lookupArr.Children[i]);
            }
        }

        // Nested fields
        if (fm.TryGetValue("fields", out var fieldsNode) && fieldsNode is YamlSequenceNode fieldsSeq)
            f.Fields = ParseFields(fieldsSeq);

        // Match cases (array format)
        if (fm.TryGetValue("cases", out var casesNode))
        {
            if (f.Type == FieldType.TLV)
            {
                if (casesNode is YamlMappingNode tlvCasesMap)
                {
                    f.TLVCases = new Dictionary<string, List<SchemaField>>();
                    foreach (var kv in tlvCasesMap.Children)
                    {
                        var rawKey = Scalar(kv.Key);
                        // Normalize hex keys: "0x01" -> "1", "[1, 117]" stays as-is
                        string caseKey;
                        if (rawKey.StartsWith("0x", StringComparison.OrdinalIgnoreCase) &&
                            int.TryParse(rawKey[2..], System.Globalization.NumberStyles.HexNumber, null, out int hexVal))
                            caseKey = hexVal.ToString();
                        else
                            caseKey = rawKey;
                        if (kv.Value is YamlSequenceNode caseFieldsSeq)
                            f.TLVCases[caseKey] = ParseFields(caseFieldsSeq);
                    }
                }
            }
            else if (casesNode is YamlSequenceNode casesSeq)
            {
                foreach (var cItem in casesSeq.Children)
                {
                    if (cItem is YamlMappingNode cMap)
                    {
                        var c = new MatchCase();
                        if (cMap.TryGetValue("case", out var cv))
                            c.CaseValue = ParseScalarValue(cv);
                        else if (cMap.TryGetValue("match", out var mv))
                            c.CaseValue = ParseScalarValue(mv);
                        if (cMap.TryGetValue("default", out var dv))
                            c.IsDefault = Scalar(dv) == "true" || Scalar(dv) == "True";
                        if (cMap.TryGetValue("fields", out var cf) && cf is YamlSequenceNode cfSeq)
                            c.Fields = ParseFields(cfSeq);
                        f.Cases.Add(c);
                    }
                }
            }
            else if (casesNode is YamlMappingNode casesMap)
            {
                // Option B: map-style cases for match
                foreach (var kv in casesMap.Children)
                {
                    var c = new MatchCase();
                    var keyStr = Scalar(kv.Key);
                    c.CaseValue = int.TryParse(keyStr, out int ki) ? (object)ki : keyStr;
                    if (kv.Value is YamlSequenceNode cfSeq)
                        c.Fields = ParseFields(cfSeq);
                    f.Cases.Add(c);
                }
            }
        }

        // TLV fields
        if (fm.TryGetValue("tag_size", out var ts2)) f.TagSize = Int(ts2);
        if (fm.TryGetValue("length_size", out var ls)) f.LengthSize = Int(ls);
        if (fm.TryGetValue("tag_fields", out var tf) && tf is YamlSequenceNode tfSeq2)
            f.TagFields = ParseFields(tfSeq2);
        if (fm.TryGetValue("tag_key", out var tk)) f.TagKey = ParseScalarValue(tk);
        if (fm.TryGetValue("merge", out var mg)) f.Merge = Scalar(mg) == "true" || Scalar(mg) == "True";
        if (fm.TryGetValue("unknown", out var uk)) f.UnknownMode = Scalar(uk);

        // Repeat
        if (fm.TryGetValue("count", out var cnt))
        {
            var cntStr = Scalar(cnt);
            f.Count = int.TryParse(cntStr, out int ci) ? (object)ci : cntStr;
        }
        if (fm.TryGetValue("byte_length", out var bl))
        {
            var blStr = Scalar(bl);
            f.ByteLength = int.TryParse(blStr, out int bli) ? (object)bli : blStr;
        }
        if (fm.TryGetValue("until", out var until)) f.Until = Scalar(until);
        if (fm.TryGetValue("max", out var maxV)) f.Max = Int(maxV);
        if (fm.TryGetValue("min", out var minV)) f.Min = Int(minV);

        // Bytes format
        if (fm.TryGetValue("format", out var fmt)) f.Format = Scalar(fmt);
        if (fm.TryGetValue("separator", out var sep)) f.Separator = Scalar(sep);

        // Bool
        if (fm.TryGetValue("bit", out var bitNode)) f.Bit = Int(bitNode);
        if (fm.TryGetValue("consume", out var cons)) f.Consume = Int(cons);

        // Enum
        if (fm.TryGetValue("base", out var baseNode)) f.Base = Scalar(baseNode);
        if (fm.TryGetValue("values", out var valuesNode) && valuesNode is YamlMappingNode valuesMap)
        {
            f.Values = new Dictionary<int, string>();
            foreach (var kv in valuesMap.Children)
            {
                if (int.TryParse(Scalar(kv.Key), out int vk))
                    f.Values[vk] = Scalar(kv.Value);
            }
        }

        // Byte group
        if (fm.TryGetValue("byte_group", out var bgNode))
        {
            if (bgNode is YamlSequenceNode bgSeq)
            {
                f.ByteGroup = ParseFields(bgSeq);
            }
            else if (bgNode is YamlMappingNode bgMap)
            {
                if (bgMap.TryGetValue("size", out var bgSize)) f.Size = Int(bgSize);
                if (bgMap.TryGetValue("fields", out var bgf) && bgf is YamlSequenceNode bgfSeq)
                    f.ByteGroup = ParseFields(bgfSeq);
            }
        }
        if (fm.TryGetValue("size", out var sizeNode)) f.Size = Int(sizeNode);

        // $ref
        if (fm.TryGetValue("$ref", out var refNode)) f.Ref2 = Scalar(refNode);

        // Bitfield string
        if (fm.TryGetValue("delimiter", out var delim)) f.Delimiter = Scalar(delim);
        if (fm.TryGetValue("prefix", out var prefix)) f.Prefix = Scalar(prefix);
        if (fm.TryGetValue("parts", out var partsNode) && partsNode is YamlSequenceNode partsSeq)
        {
            foreach (var pItem in partsSeq.Children)
            {
                if (pItem is YamlSequenceNode partArr)
                {
                    var part = new List<object>();
                    foreach (var elem in partArr.Children)
                        part.Add(ParseScalarValue(elem)!);
                    f.Parts.Add(part);
                }
            }
        }

        // Formula (deprecated)
        if (fm.TryGetValue("formula", out var formula)) f.Formula = Scalar(formula);

        // Semantic
        if (fm.TryGetValue("valid_range", out var vrNode) && vrNode is YamlSequenceNode vrSeq)
        {
            f.ValidRange = vrSeq.Children.Select(n => Double(n)).ToArray();
        }
        if (fm.TryGetValue("resolution", out var res)) f.Resolution = Double(res);
        if (fm.TryGetValue("unece", out var unece)) f.UNECE = Scalar(unece);
        if (fm.TryGetValue("unit", out var unit)) f.Unit = Scalar(unit);
        if (fm.TryGetValue("semantic", out var semId)) f.SemanticId = Scalar(semId);
        if (fm.TryGetValue("ipso", out var ipsoNode) && ipsoNode is YamlMappingNode ipsoMap)
        {
            f.Ipso = new IpsoDef();
            if (ipsoMap.TryGetValue("object", out var io)) f.Ipso.Object = Int(io);
            if (ipsoMap.TryGetValue("instance", out var ii)) f.Ipso.Instance = Int(ii);
            if (ipsoMap.TryGetValue("resource", out var ir)) f.Ipso.Resource = Int(ir);
        }
        if (fm.TryGetValue("senml", out var senmlNode) && senmlNode is YamlMappingNode senmlMap)
        {
            f.Senml = new SenmlDef();
            if (senmlMap.TryGetValue("name", out var sn)) f.Senml.Name = Scalar(sn);
            if (senmlMap.TryGetValue("unit", out var su)) f.Senml.Unit = Scalar(su);
        }

        // Computed fields
        if (fm.TryGetValue("ref", out var refVal)) f.Ref = Scalar(refVal);
        if (fm.TryGetValue("polynomial", out var polyNode) && polyNode is YamlSequenceNode polySeq)
        {
            f.Polynomial = polySeq.Children.Select(n => Double(n)).ToArray();
        }

        // Compute
        if (fm.TryGetValue("compute", out var compNode) && compNode is YamlMappingNode compMap)
        {
            var cd = new ComputeDef();
            if (compMap.TryGetValue("op", out var op)) cd.Op = Scalar(op);
            if (compMap.TryGetValue("a", out var a)) cd.A = Scalar(a);
            if (compMap.TryGetValue("b", out var b)) cd.B = Scalar(b);
            f.Compute = cd;
        }

        // Guard
        if (fm.TryGetValue("guard", out var guardNode) && guardNode is YamlMappingNode guardMap)
        {
            var gd = new GuardDef();
            if (guardMap.TryGetValue("else", out var elseVal))
                gd.ElseValue = Double(elseVal);
            if (guardMap.TryGetValue("when", out var whenNode) && whenNode is YamlSequenceNode whenSeq)
            {
                foreach (var w in whenSeq.Children)
                {
                    if (w is YamlMappingNode wm)
                    {
                        var gc = new GuardCondition();
                        if (wm.TryGetValue("field", out var gf)) gc.Field = Scalar(gf);
                        if (wm.TryGetValue("gt", out var gt)) gc.Gt = Double(gt);
                        if (wm.TryGetValue("gte", out var gte)) gc.Gte = Double(gte);
                        if (wm.TryGetValue("lt", out var lt)) gc.Lt = Double(lt);
                        if (wm.TryGetValue("lte", out var lte)) gc.Lte = Double(lte);
                        if (wm.TryGetValue("eq", out var eq)) gc.Eq = Double(eq);
                        gd.When.Add(gc);
                    }
                }
            }
            f.Guard = gd;
        }

        // Flagged construct (inline)
        if (fm.TryGetValue("flagged", out var flaggedNode) && flaggedNode is YamlMappingNode flaggedMap)
        {
            var fd = new FlaggedDef();
            if (flaggedMap.TryGetValue("field", out var ff)) fd.Field = Scalar(ff);
            if (flaggedMap.TryGetValue("groups", out var groups) && groups is YamlSequenceNode groupsSeq)
            {
                foreach (var g in groupsSeq.Children)
                {
                    if (g is YamlMappingNode gMap)
                    {
                        var fg = new FlaggedGroup();
                        if (gMap.TryGetValue("bit", out var gBit)) fg.Bit = Int(gBit);
                        if (gMap.TryGetValue("fields", out var gf) && gf is YamlSequenceNode gfSeq)
                            fg.Fields = ParseFields(gfSeq);
                        fd.Groups.Add(fg);
                    }
                }
            }
            f.Flagged = fd;
        }

        // TLV inline -- set type first so cases are parsed as TLV cases
        if (fm.TryGetValue("tlv", out var tlvNode) && tlvNode is YamlMappingNode tlvMap)
        {
            // Temporarily inject type so ParseField parses cases as TLV
            var syntheticMap = new YamlMappingNode();
            syntheticMap.Add("type", "tlv");
            foreach (var kv in tlvMap.Children)
                syntheticMap.Add(kv.Key, kv.Value);
            var tlvField = ParseField(syntheticMap);
            tlvField.Type = FieldType.TLV;
            f.TLVInline = tlvField;
        }

        // Match inline (Option B: `- match: { field: $var, cases: {...} }`)
        if (fm.TryGetValue("match", out var matchNode) && matchNode is YamlMappingNode matchMap)
        {
            var matchField = new SchemaField { Type = FieldType.Match };
            if (matchMap.TryGetValue("field", out var mf)) matchField.On = Scalar(mf);
            if (matchMap.TryGetValue("cases", out var mc) && mc is YamlMappingNode mcMap)
            {
                foreach (var kv in mcMap.Children)
                {
                    var c = new MatchCase();
                    var keyStr = Scalar(kv.Key);
                    c.CaseValue = int.TryParse(keyStr, out int ki) ? (object)ki : keyStr;
                    if (kv.Value is YamlSequenceNode cfSeq)
                        c.Fields = ParseFields(cfSeq);
                    matchField.Cases.Add(c);
                }
            }
            f.MatchInline = matchField;
        }

        return f;
    }

    // Helper: get scalar string value from a YAML node
    static string Scalar(YamlNode node) => node is YamlScalarNode s ? s.Value ?? "" : node.ToString() ?? "";

    static int Int(YamlNode node)
    {
        var s = Scalar(node);
        if (s.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
            return int.Parse(s[2..], NumberStyles.HexNumber);
        return int.TryParse(s, out int v) ? v : 0;
    }

    static double Double(YamlNode node)
    {
        var s = Scalar(node);
        return double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out double v) ? v : 0;
    }

    static object? ParseScalarValue(YamlNode node)
    {
        if (node is YamlScalarNode scalar)
        {
            var s = scalar.Value ?? "";
            if (s.StartsWith("0x", StringComparison.OrdinalIgnoreCase) &&
                int.TryParse(s[2..], NumberStyles.HexNumber, CultureInfo.InvariantCulture, out int hex))
                return hex;
            if (int.TryParse(s, out int i)) return i;
            if (double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out double d)) return d;
            if (s == "true" || s == "True") return true;
            if (s == "false" || s == "False") return false;
            return s;
        }
        if (node is YamlSequenceNode seq)
        {
            return seq.Children.Select(ParseScalarValue).ToList();
        }
        return null;
    }
}

file static class YamlMappingNodeExtensions
{
    public static bool TryGetValue(this YamlMappingNode map, string key, out YamlNode value)
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
