package org.lora.schema;

public enum FieldType {
    // Unsigned integers
    U8, U16, U32, U64,
    // Signed integers
    I8, I16, I32, I64, S8, S16, S32, S64,
    // Floating point
    F16, F32, F64,
    // Boolean and bits
    BOOL, BITS,
    // String types
    ASCII, HEX, BASE64, STRING,
    // Byte types
    BYTES, SKIP,
    // Complex types
    OBJECT, MATCH, SWITCH, TLV, REPEAT,
    // Computed
    NUMBER,
    // Bitfield string
    BITFIELD_STRING,
    // Legacy names
    BYTE, UINT, SINT, BINT, FLOAT16, FLOAT32, FLOAT64;

    public static FieldType fromString(String type) {
        if (type == null || type.isEmpty()) {
            return U8;
        }
        String normalized = type.toLowerCase().replace("-", "_");
        
        return switch (normalized) {
            case "u8", "byte" -> U8;
            case "u16" -> U16;
            case "u32" -> U32;
            case "u64" -> U64;
            case "i8", "s8" -> I8;
            case "i16", "s16" -> I16;
            case "i32", "s32" -> I32;
            case "i64", "s64" -> I64;
            case "f16", "float16" -> F16;
            case "f32", "float32" -> F32;
            case "f64", "float64" -> F64;
            case "bool", "boolean" -> BOOL;
            case "bits" -> BITS;
            case "ascii" -> ASCII;
            case "hex" -> HEX;
            case "base64" -> BASE64;
            case "string" -> STRING;
            case "bytes" -> BYTES;
            case "skip" -> SKIP;
            case "object" -> OBJECT;
            case "match", "switch" -> MATCH;
            case "tlv" -> TLV;
            case "repeat" -> REPEAT;
            case "number" -> NUMBER;
            case "bitfield_string" -> BITFIELD_STRING;
            case "uint" -> UINT;
            case "sint" -> SINT;
            case "bint" -> BINT;
            default -> U8;
        };
    }

    public int defaultLength() {
        return switch (this) {
            case U8, I8, S8, BOOL, BYTE -> 1;
            case U16, I16, S16, F16 -> 2;
            case U32, I32, S32, F32, UINT, SINT, BINT -> 4;
            case U64, I64, S64, F64 -> 8;
            default -> 1;
        };
    }

    public boolean isInteger() {
        return switch (this) {
            case U8, U16, U32, U64, I8, I16, I32, I64, S8, S16, S32, S64, 
                 BYTE, UINT, SINT, BINT, BITS -> true;
            default -> false;
        };
    }

    public boolean isSigned() {
        return switch (this) {
            case I8, I16, I32, I64, S8, S16, S32, S64, SINT -> true;
            default -> false;
        };
    }

    public boolean isFloat() {
        return switch (this) {
            case F16, F32, F64, FLOAT16, FLOAT32, FLOAT64 -> true;
            default -> false;
        };
    }
}
