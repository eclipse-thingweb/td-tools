// Copyright (c) 2024-2026 Multitech Systems, Inc.
// SPDX-License-Identifier: MIT

namespace PayloadSchema;

public enum FieldType
{
    Unknown,
    U8, U16, U24, U32, U64,
    S8, S16, S24, S32, S64,
    F16, F32, F64,
    Bool,
    Bits,
    Ascii,
    Hex,
    Bytes,
    Skip,
    String,
    Number,
    Object,
    Match,
    TLV,
    Repeat,
    Enum,
    BitfieldString,
}

public class TransformStage
{
    public double? Add { get; set; }
    public double? Sub { get; set; }
    public double? Mult { get; set; }
    public double? Div { get; set; }
}

public class MatchCase
{
    public object? CaseValue { get; set; }
    public bool IsDefault { get; set; }
    public List<SchemaField> Fields { get; set; } = new();
}

public class ComputeDef
{
    public string Op { get; set; } = "";
    public string A { get; set; } = "";
    public string B { get; set; } = "";
}

public class GuardCondition
{
    public string Field { get; set; } = "";
    public double? Gt { get; set; }
    public double? Gte { get; set; }
    public double? Lt { get; set; }
    public double? Lte { get; set; }
    public double? Eq { get; set; }
}

public class GuardDef
{
    public List<GuardCondition> When { get; set; } = new();
    public double ElseValue { get; set; }
}

public class FlaggedGroup
{
    public int Bit { get; set; }
    public List<SchemaField> Fields { get; set; } = new();
}

public class FlaggedDef
{
    public string Field { get; set; } = "";
    public List<FlaggedGroup> Groups { get; set; } = new();
}

public class SchemaField
{
    public string Name { get; set; } = "";
    public FieldType Type { get; set; }
    public string RawType { get; set; } = "";
    public int Length { get; set; }
    public int ByteOffset { get; set; }
    public int BitOffset { get; set; }
    public int BitCount { get; set; }
    public string? Endian { get; set; }

    // Modifiers
    public double? Add { get; set; }
    public double? Mult { get; set; }
    public double? Div { get; set; }
    public List<string> ModOrder { get; set; } = new();
    public List<TransformStage> Transform { get; set; } = new();
    public Dictionary<int, string>? Lookup { get; set; }

    // Variable
    public string? Var { get; set; }
    public object? Value { get; set; }

    // Nested / conditional
    public List<SchemaField> Fields { get; set; } = new();
    public string? On { get; set; }
    public List<MatchCase> Cases { get; set; } = new();

    // Repeat
    public object? Count { get; set; }
    public object? ByteLength { get; set; }
    public string? Until { get; set; }
    public int Max { get; set; }
    public int Min { get; set; }

    // Bytes format
    public string? Format { get; set; }
    public string? Separator { get; set; }

    // Bool
    public int Bit { get; set; }
    public int Consume { get; set; }

    // Enum
    public string? Base { get; set; }
    public Dictionary<int, string>? Values { get; set; }

    // Byte group
    public List<SchemaField> ByteGroup { get; set; } = new();
    public int Size { get; set; }

    // $ref
    public string? Ref2 { get; set; }

    // TLV
    public int TagSize { get; set; }
    public int LengthSize { get; set; }
    public List<SchemaField> TagFields { get; set; } = new();
    public object? TagKey { get; set; }
    public bool? Merge { get; set; }
    public string? UnknownMode { get; set; }
    public Dictionary<string, List<SchemaField>>? TLVCases { get; set; }

    // Bitfield string
    public List<List<object>> Parts { get; set; } = new();
    public string? Delimiter { get; set; }
    public string? Prefix { get; set; }

    // Formula (deprecated)
    public string? Formula { get; set; }

    // Semantic
    public double[]? ValidRange { get; set; }
    public double? Resolution { get; set; }
    public string? UNECE { get; set; }
    public string? Unit { get; set; }
    public IpsoDef? Ipso { get; set; }
    public SenmlDef? Senml { get; set; }
    public string? SemanticId { get; set; }

    // Computed fields
    public string? Ref { get; set; }
    public double[]? Polynomial { get; set; }
    public ComputeDef? Compute { get; set; }
    public GuardDef? Guard { get; set; }

    // Inline constructs
    public FlaggedDef? Flagged { get; set; }
    public SchemaField? TLVInline { get; set; }
    public SchemaField? MatchInline { get; set; }
}

public class PortDef
{
    public string? Direction { get; set; }
    public string? Description { get; set; }
    public List<SchemaField> Fields { get; set; } = new();
}

public class DefinitionDef
{
    public List<SchemaField> Fields { get; set; } = new();
}

public class IpsoDef
{
    public int Object { get; set; }
    public int Instance { get; set; }
    public int Resource { get; set; } = 5700;
}

public class SenmlDef
{
    public string? Name { get; set; }
    public string? Unit { get; set; }
}

public class PayloadSchemaDefinition
{
    public string Name { get; set; } = "";
    public int Version { get; set; }
    public string? Description { get; set; }
    public string Endian { get; set; } = "big";
    public List<SchemaField> Header { get; set; } = new();
    public List<SchemaField> Fields { get; set; } = new();
    public Dictionary<string, PortDef>? Ports { get; set; }
    public Dictionary<string, DefinitionDef>? Definitions { get; set; }
}
