package org.lora.schema;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.*;

public class BinarySchemaParser {
    
    private static final int FIELD_TYPE_UNSIGNED = 0x0;
    private static final int FIELD_TYPE_SIGNED = 0x1;
    private static final int FIELD_TYPE_FLOAT = 0x2;
    private static final int FIELD_TYPE_BYTES = 0x3;
    private static final int FIELD_TYPE_BOOL = 0x4;
    private static final int FIELD_TYPE_ENUM = 0x5;
    private static final int FIELD_TYPE_BITFIELD = 0x6;
    private static final int FIELD_TYPE_SKIP = 0x7;
    private static final int FIELD_TYPE_OBJECT = 0x8;
    private static final int FIELD_TYPE_MATCH = 0x9;
    private static final int FIELD_TYPE_LITERAL = 0xA;
    private static final int FIELD_TYPE_TLV = 0xC;
    
    private static final int FLAG_HAS_MULT = 0x01;
    private static final int FLAG_HAS_DIV = 0x02;
    private static final int FLAG_HAS_ADD = 0x04;
    private static final int FLAG_HAS_LOOKUP = 0x08;
    private static final int FLAG_HAS_VAR = 0x10;
    private static final int FLAG_CONSUME = 0x20;
    private static final int FLAG_MERGE = 0x40;
    
    private byte[] data;
    private int pos;
    private List<String> strings;
    private List<Map<Integer, Object>> lookups;
    private boolean bigEndian;
    
    public Schema parse(byte[] binaryData) {
        this.data = binaryData;
        this.pos = 0;
        this.strings = new ArrayList<>();
        this.lookups = new ArrayList<>();
        
        // Read header
        if (data.length < 8) {
            throw new SchemaException.ParseException("Binary schema too short");
        }
        
        char magic1 = (char) data[0];
        char magic2 = (char) data[1];
        if (magic1 != 'P' || magic2 != 'S') {
            throw new SchemaException.ParseException("Invalid binary schema magic: " + magic1 + magic2);
        }
        
        int version = data[2] & 0xFF;
        int flags = data[3] & 0xFF;
        int stringsOffset = (data[4] & 0xFF) | ((data[5] & 0xFF) << 8);
        int lookupsOffset = (data[6] & 0xFF) | ((data[7] & 0xFF) << 8);
        
        this.bigEndian = (flags & 0x01) != 0;
        
        // Parse string table first
        this.pos = stringsOffset;
        parseStringTable();
        
        // Parse lookup tables
        this.pos = lookupsOffset;
        parseLookupTables();
        
        // Parse fields
        this.pos = 8;
        Varint.DecodeResult fieldCountResult = Varint.decode(data, pos);
        int fieldCount = (int) fieldCountResult.value;
        pos = fieldCountResult.newPos;
        
        List<Field> fields = new ArrayList<>();
        for (int i = 0; i < fieldCount; i++) {
            fields.add(parseField());
        }
        
        Schema schema = new Schema();
        schema.setName(strings.isEmpty() ? "unknown" : strings.get(0));
        schema.setVersion(version);
        schema.setEndian(bigEndian ? "big" : "little");
        schema.setFields(fields);
        
        return schema;
    }
    
    public static Schema fromBase64(String base64) {
        byte[] data = Base64.getDecoder().decode(base64);
        return new BinarySchemaParser().parse(data);
    }
    
    public static Schema fromGzipBase64(String gzipBase64) {
        try {
            byte[] compressed = Base64.getDecoder().decode(gzipBase64);
            java.io.ByteArrayInputStream bais = new java.io.ByteArrayInputStream(compressed);
            java.util.zip.GZIPInputStream gzis = new java.util.zip.GZIPInputStream(bais);
            byte[] data = gzis.readAllBytes();
            return new BinarySchemaParser().parse(data);
        } catch (Exception e) {
            throw new SchemaException.ParseException("Failed to decompress gzip schema", e);
        }
    }
    
    private void parseStringTable() {
        Varint.DecodeResult countResult = Varint.decode(data, pos);
        int count = (int) countResult.value;
        pos = countResult.newPos;
        
        for (int i = 0; i < count; i++) {
            Varint.DecodeResult lengthResult = Varint.decode(data, pos);
            int length = (int) lengthResult.value;
            pos = lengthResult.newPos;
            
            StringBuilder sb = new StringBuilder();
            for (int j = 0; j < length; j++) {
                sb.append((char) data[pos++]);
            }
            strings.add(sb.toString());
        }
    }
    
    private void parseLookupTables() {
        Varint.DecodeResult countResult = Varint.decode(data, pos);
        int count = (int) countResult.value;
        pos = countResult.newPos;
        
        for (int i = 0; i < count; i++) {
            Varint.DecodeResult entryCountResult = Varint.decode(data, pos);
            int entryCount = (int) entryCountResult.value;
            pos = entryCountResult.newPos;
            
            Map<Integer, Object> table = new HashMap<>();
            for (int j = 0; j < entryCount; j++) {
                Varint.DecodeResult keyResult = Varint.decodeSigned(data, pos);
                int key = (int) keyResult.value;
                pos = keyResult.newPos;
                
                int valueType = data[pos++] & 0xFF;
                Object value;
                if (valueType == 0x01) {
                    // String value
                    Varint.DecodeResult strIdxResult = Varint.decode(data, pos);
                    int strIdx = (int) strIdxResult.value;
                    pos = strIdxResult.newPos;
                    value = strings.get(strIdx);
                } else {
                    // Number value
                    Varint.DecodeResult numResult = Varint.decodeSigned(data, pos);
                    pos = numResult.newPos;
                    value = numResult.value;
                }
                table.put(key, value);
            }
            lookups.add(table);
        }
    }
    
    private Field parseField() {
        int typeByte = data[pos++] & 0xFF;
        int fieldType = (typeByte >> 4) & 0x0F;
        int size = typeByte & 0x0F;
        
        if (fieldType == FIELD_TYPE_MATCH) {
            return parseMatch();
        }
        
        if (fieldType == FIELD_TYPE_TLV) {
            return parseTLV();
        }
        
        if (fieldType == FIELD_TYPE_OBJECT) {
            if (size == 0x01) {
                return parseByteGroup();
            }
            return parseObject();
        }
        
        if (fieldType == FIELD_TYPE_BITFIELD) {
            return parseBitfield();
        }
        
        // Standard field
        int flags = data[pos++] & 0xFF;
        int nameIdx = (data[pos] & 0xFF) | ((data[pos + 1] & 0xFF) << 8);
        pos += 2;
        
        String name = nameIdx != 0xFFFF ? strings.get(nameIdx) : null;
        
        Field field = new Field();
        field.setType(getFieldType(fieldType, size));
        if (name != null) field.setName(name);
        
        // Variable length types
        if (fieldType == FIELD_TYPE_BYTES || fieldType == FIELD_TYPE_SKIP) {
            Varint.DecodeResult lengthResult = Varint.decode(data, pos);
            field.setLength((int) lengthResult.value);
            pos = lengthResult.newPos;
        } else {
            field.setLength(getDefaultLength(fieldType, size));
        }
        
        // Modifiers
        if ((flags & FLAG_HAS_MULT) != 0) {
            field.setMult((double) readFloat32());
        }
        if ((flags & FLAG_HAS_DIV) != 0) {
            field.setDiv((double) readFloat32());
        }
        if ((flags & FLAG_HAS_ADD) != 0) {
            field.setAdd((double) readFloat32());
        }
        if ((flags & FLAG_HAS_LOOKUP) != 0) {
            Varint.DecodeResult lookupIdxResult = Varint.decode(data, pos);
            int lookupIdx = (int) lookupIdxResult.value;
            pos = lookupIdxResult.newPos;
            
            Map<Integer, String> lookup = new HashMap<>();
            for (Map.Entry<Integer, Object> entry : lookups.get(lookupIdx).entrySet()) {
                lookup.put(entry.getKey(), String.valueOf(entry.getValue()));
            }
            field.setLookup(lookup);
        }
        if ((flags & FLAG_HAS_VAR) != 0) {
            Varint.DecodeResult varIdxResult = Varint.decode(data, pos);
            int varIdx = (int) varIdxResult.value;
            pos = varIdxResult.newPos;
            field.setVar(strings.get(varIdx));
        }
        
        return field;
    }
    
    private Field parseBitfield() {
        int bitInfo = data[pos++] & 0xFF;
        int startBit = (bitInfo >> 4) & 0x0F;
        int bitWidth = bitInfo & 0x0F;
        
        int flags = data[pos++] & 0xFF;
        int nameIdx = (data[pos] & 0xFF) | ((data[pos + 1] & 0xFF) << 8);
        pos += 2;
        
        String name = nameIdx != 0xFFFF ? strings.get(nameIdx) : null;
        
        Field field = new Field();
        field.setType(FieldType.BITS);
        field.setBitOffset(startBit);
        field.setBits(bitWidth);
        if (name != null) field.setName(name);
        
        if ((flags & FLAG_HAS_LOOKUP) != 0) {
            Varint.DecodeResult lookupIdxResult = Varint.decode(data, pos);
            int lookupIdx = (int) lookupIdxResult.value;
            pos = lookupIdxResult.newPos;
            
            Map<Integer, String> lookup = new HashMap<>();
            for (Map.Entry<Integer, Object> entry : lookups.get(lookupIdx).entrySet()) {
                lookup.put(entry.getKey(), String.valueOf(entry.getValue()));
            }
            field.setLookup(lookup);
        }
        if ((flags & FLAG_HAS_VAR) != 0) {
            Varint.DecodeResult varIdxResult = Varint.decode(data, pos);
            int varIdx = (int) varIdxResult.value;
            pos = varIdxResult.newPos;
            field.setVar(strings.get(varIdx));
        }
        
        return field;
    }
    
    private Field parseObject() {
        int nameIdx = (data[pos] & 0xFF) | ((data[pos + 1] & 0xFF) << 8);
        pos += 2;
        
        String name = nameIdx != 0xFFFF ? strings.get(nameIdx) : null;
        
        Varint.DecodeResult fieldCountResult = Varint.decode(data, pos);
        int fieldCount = (int) fieldCountResult.value;
        pos = fieldCountResult.newPos;
        
        List<Field> fields = new ArrayList<>();
        for (int i = 0; i < fieldCount; i++) {
            fields.add(parseField());
        }
        
        Field field = new Field();
        field.setType(FieldType.OBJECT);
        field.setFields(fields);
        if (name != null) field.setName(name);
        
        return field;
    }
    
    private Field parseByteGroup() {
        Varint.DecodeResult groupSizeResult = Varint.decode(data, pos);
        pos = groupSizeResult.newPos;
        
        Varint.DecodeResult fieldCountResult = Varint.decode(data, pos);
        int fieldCount = (int) fieldCountResult.value;
        pos = fieldCountResult.newPos;
        
        List<Field> fields = new ArrayList<>();
        for (int i = 0; i < fieldCount; i++) {
            fields.add(parseField());
        }
        
        Field field = new Field();
        field.setType(FieldType.OBJECT);
        field.setFields(fields);
        
        return field;
    }
    
    private Field parseTLV() {
        int flags = data[pos++] & 0xFF;
        int tagSize = (flags & 0x03) + 1;
        int lengthSize = (flags >> 2) & 0x03;
        boolean merge = (flags & 0x10) != 0;
        String[] unknownModes = {"skip", "error", "raw"};
        String unknownMode = unknownModes[(flags >> 5) & 0x03];
        boolean hasTagFields = (flags & 0x80) != 0;
        
        List<Field> tagFields = null;
        List<String> tagKey = null;
        
        if (hasTagFields) {
            Varint.DecodeResult tagFieldCountResult = Varint.decode(data, pos);
            int tagFieldCount = (int) tagFieldCountResult.value;
            pos = tagFieldCountResult.newPos;
            
            tagFields = new ArrayList<>();
            for (int i = 0; i < tagFieldCount; i++) {
                tagFields.add(parseField());
            }
            
            Varint.DecodeResult tagKeyCountResult = Varint.decode(data, pos);
            int tagKeyCount = (int) tagKeyCountResult.value;
            pos = tagKeyCountResult.newPos;
            
            tagKey = new ArrayList<>();
            for (int i = 0; i < tagKeyCount; i++) {
                Varint.DecodeResult idxResult = Varint.decode(data, pos);
                int idx = (int) idxResult.value;
                pos = idxResult.newPos;
                tagKey.add(tagFields.get(idx).getName());
            }
        }
        
        // Parse cases
        Varint.DecodeResult caseCountResult = Varint.decode(data, pos);
        int caseCount = (int) caseCountResult.value;
        pos = caseCountResult.newPos;
        
        Map<String, List<Field>> cases = new HashMap<>();
        for (int i = 0; i < caseCount; i++) {
            // Read tag values
            Varint.DecodeResult tagValueCountResult = Varint.decode(data, pos);
            int tagValueCount = (int) tagValueCountResult.value;
            pos = tagValueCountResult.newPos;
            
            List<Integer> tagValues = new ArrayList<>();
            for (int j = 0; j < tagValueCount; j++) {
                Varint.DecodeResult valResult = Varint.decode(data, pos);
                tagValues.add((int) valResult.value);
                pos = valResult.newPos;
            }
            
            // Read fields for this case
            Varint.DecodeResult fieldCountResult = Varint.decode(data, pos);
            int fieldCount = (int) fieldCountResult.value;
            pos = fieldCountResult.newPos;
            
            List<Field> fields = new ArrayList<>();
            for (int j = 0; j < fieldCount; j++) {
                fields.add(parseField());
            }
            
            // Build case key
            String caseKey = tagValues.size() == 1 ? 
                String.valueOf(tagValues.get(0)) : tagValues.toString();
            cases.put(caseKey, fields);
        }
        
        Field field = new Field();
        field.setType(FieldType.TLV);
        field.setTagSize(tagSize);
        field.setLengthSize(lengthSize);
        field.setMerge(merge);
        field.setUnknown(unknownMode);
        field.setTlvCases(cases);
        
        if (tagFields != null) {
            field.setTagFields(tagFields);
            field.setTagKey(tagKey);
        }
        
        return field;
    }
    
    private Field parseMatch() {
        int flags = data[pos++] & 0xFF;
        
        int nameIdx = (data[pos] & 0xFF) | ((data[pos + 1] & 0xFF) << 8);
        pos += 2;
        String name = nameIdx != 0xFFFF ? strings.get(nameIdx) : null;
        
        // Discriminator
        int mode = data[pos++] & 0xFF;
        String on = null;
        int length = 1;
        
        if (mode == 0x01) {
            Varint.DecodeResult varIdxResult = Varint.decode(data, pos);
            int varIdx = (int) varIdxResult.value;
            pos = varIdxResult.newPos;
            on = "$" + strings.get(varIdx);
        } else {
            Varint.DecodeResult lenResult = Varint.decode(data, pos);
            length = (int) lenResult.value;
            pos = lenResult.newPos;
        }
        
        // Cases
        Varint.DecodeResult caseCountResult = Varint.decode(data, pos);
        int caseCount = (int) caseCountResult.value;
        pos = caseCountResult.newPos;
        
        List<Field.Case> cases = new ArrayList<>();
        for (int i = 0; i < caseCount; i++) {
            int caseType = data[pos++] & 0xFF;
            Field.Case caseDef = new Field.Case();
            
            if (caseType == 0xFF) {
                // Default
                int defaultMode = data[pos++] & 0xFF;
                caseDef.setDefault(true);
            } else if (caseType == 0xFE) {
                // Multiple values
                Varint.DecodeResult valCountResult = Varint.decode(data, pos);
                int valCount = (int) valCountResult.value;
                pos = valCountResult.newPos;
                
                List<Integer> values = new ArrayList<>();
                for (int j = 0; j < valCount; j++) {
                    Varint.DecodeResult valResult = Varint.decodeSigned(data, pos);
                    values.add((int) valResult.value);
                    pos = valResult.newPos;
                }
                caseDef.setCaseValue(values);
            } else {
                // Single value
                Varint.DecodeResult caseValResult = Varint.decodeSigned(data, pos);
                caseDef.setCaseValue((int) caseValResult.value);
                pos = caseValResult.newPos;
            }
            
            // Parse case fields
            Varint.DecodeResult fieldCountResult = Varint.decode(data, pos);
            int fieldCount = (int) fieldCountResult.value;
            pos = fieldCountResult.newPos;
            
            List<Field> caseFields = new ArrayList<>();
            for (int j = 0; j < fieldCount; j++) {
                caseFields.add(parseField());
            }
            caseDef.setFields(caseFields);
            
            cases.add(caseDef);
        }
        
        Field field = new Field();
        field.setType(FieldType.MATCH);
        field.setCases(cases);
        if (name != null) field.setName(name);
        if (on != null) field.setOn(on);
        field.setLength(length);
        
        return field;
    }
    
    private float readFloat32() {
        ByteBuffer buffer = ByteBuffer.wrap(data, pos, 4);
        buffer.order(ByteOrder.LITTLE_ENDIAN);
        pos += 4;
        return buffer.getFloat();
    }
    
    private FieldType getFieldType(int type, int size) {
        return switch (type) {
            case FIELD_TYPE_UNSIGNED -> switch (size) {
                case 1 -> FieldType.U8;
                case 2 -> FieldType.U16;
                case 4 -> FieldType.U32;
                case 8 -> FieldType.U64;
                default -> FieldType.U8;
            };
            case FIELD_TYPE_SIGNED -> switch (size) {
                case 1 -> FieldType.I8;
                case 2 -> FieldType.I16;
                case 4 -> FieldType.I32;
                case 8 -> FieldType.I64;
                default -> FieldType.I8;
            };
            case FIELD_TYPE_FLOAT -> switch (size) {
                case 2 -> FieldType.F16;
                case 4 -> FieldType.F32;
                case 8 -> FieldType.F64;
                default -> FieldType.F32;
            };
            case FIELD_TYPE_BYTES -> FieldType.BYTES;
            case FIELD_TYPE_BOOL -> FieldType.BOOL;
            case FIELD_TYPE_SKIP -> FieldType.SKIP;
            case FIELD_TYPE_OBJECT -> FieldType.OBJECT;
            case FIELD_TYPE_MATCH -> FieldType.MATCH;
            case FIELD_TYPE_TLV -> FieldType.TLV;
            default -> FieldType.U8;
        };
    }
    
    private int getDefaultLength(int type, int size) {
        return switch (type) {
            case FIELD_TYPE_UNSIGNED, FIELD_TYPE_SIGNED -> size > 0 ? size : 1;
            case FIELD_TYPE_FLOAT -> size > 0 ? size : 4;
            case FIELD_TYPE_BOOL -> 1;
            default -> 1;
        };
    }
}
