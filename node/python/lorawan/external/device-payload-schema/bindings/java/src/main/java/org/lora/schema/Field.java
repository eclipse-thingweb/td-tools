package org.lora.schema;

import java.util.*;

public class Field {
    private String name;
    private FieldType type = FieldType.U8;
    private int length;
    private int byteOffset;
    private int bitOffset;
    private int bits;
    private String endian;
    private Double add;
    private Double mult;
    private Double div;
    private List<String> modOrder;
    private List<Transform> transform;
    private Map<Integer, String> lookup;
    private String var;
    private Object value;
    private List<Field> fields;
    private String on;
    private List<Case> cases;
    
    // Repeat fields
    private Object count;
    private Object byteLength;
    private String until;
    private int max;
    private int min;
    
    // Bytes format
    private String format;
    private String separator;
    
    // TLV fields
    private int tagSize;
    private int lengthSize;
    private List<Field> tagFields;
    private Object tagKey;
    private Boolean merge;
    private String unknown;
    private Map<String, List<Field>> tlvCases;
    
    // Bitfield string
    private List<List<Object>> parts;
    private String delimiter;
    private String prefix;
    
    // Formula
    private String formula;
    
    // Flagged construct
    private FlaggedDef flagged;
    
    // TLV inline
    private Field tlvInline;

    public Field() {
        this.modOrder = new ArrayList<>();
    }

    // Getters and setters
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    
    public FieldType getType() { return type; }
    public void setType(FieldType type) { this.type = type; }
    
    public int getLength() { return length; }
    public void setLength(int length) { this.length = length; }
    
    public int getByteOffset() { return byteOffset; }
    public void setByteOffset(int byteOffset) { this.byteOffset = byteOffset; }
    
    public int getBitOffset() { return bitOffset; }
    public void setBitOffset(int bitOffset) { this.bitOffset = bitOffset; }
    
    public int getBits() { return bits; }
    public void setBits(int bits) { this.bits = bits; }
    
    public String getEndian() { return endian; }
    public void setEndian(String endian) { this.endian = endian; }
    
    public Double getAdd() { return add; }
    public void setAdd(Double add) { this.add = add; }
    
    public Double getMult() { return mult; }
    public void setMult(Double mult) { this.mult = mult; }
    
    public Double getDiv() { return div; }
    public void setDiv(Double div) { this.div = div; }
    
    public List<String> getModOrder() { return modOrder; }
    public void setModOrder(List<String> modOrder) { this.modOrder = modOrder; }
    
    public List<Transform> getTransform() { return transform; }
    public void setTransform(List<Transform> transform) { this.transform = transform; }
    
    public Map<Integer, String> getLookup() { return lookup; }
    public void setLookup(Map<Integer, String> lookup) { this.lookup = lookup; }
    
    public String getVar() { return var; }
    public void setVar(String var) { this.var = var; }
    
    public Object getValue() { return value; }
    public void setValue(Object value) { this.value = value; }
    
    public List<Field> getFields() { return fields; }
    public void setFields(List<Field> fields) { this.fields = fields; }
    
    public String getOn() { return on; }
    public void setOn(String on) { this.on = on; }
    
    public List<Case> getCases() { return cases; }
    public void setCases(List<Case> cases) { this.cases = cases; }
    
    public Object getCount() { return count; }
    public void setCount(Object count) { this.count = count; }
    
    public Object getByteLength() { return byteLength; }
    public void setByteLength(Object byteLength) { this.byteLength = byteLength; }
    
    public String getUntil() { return until; }
    public void setUntil(String until) { this.until = until; }
    
    public int getMax() { return max; }
    public void setMax(int max) { this.max = max; }
    
    public int getMin() { return min; }
    public void setMin(int min) { this.min = min; }
    
    public String getFormat() { return format; }
    public void setFormat(String format) { this.format = format; }
    
    public String getSeparator() { return separator; }
    public void setSeparator(String separator) { this.separator = separator; }
    
    public int getTagSize() { return tagSize; }
    public void setTagSize(int tagSize) { this.tagSize = tagSize; }
    
    public int getLengthSize() { return lengthSize; }
    public void setLengthSize(int lengthSize) { this.lengthSize = lengthSize; }
    
    public List<Field> getTagFields() { return tagFields; }
    public void setTagFields(List<Field> tagFields) { this.tagFields = tagFields; }
    
    public Object getTagKey() { return tagKey; }
    public void setTagKey(Object tagKey) { this.tagKey = tagKey; }
    
    public Boolean getMerge() { return merge; }
    public void setMerge(Boolean merge) { this.merge = merge; }
    
    public String getUnknown() { return unknown; }
    public void setUnknown(String unknown) { this.unknown = unknown; }
    
    public Map<String, List<Field>> getTlvCases() { return tlvCases; }
    public void setTlvCases(Map<String, List<Field>> tlvCases) { this.tlvCases = tlvCases; }
    
    public List<List<Object>> getParts() { return parts; }
    public void setParts(List<List<Object>> parts) { this.parts = parts; }
    
    public String getDelimiter() { return delimiter; }
    public void setDelimiter(String delimiter) { this.delimiter = delimiter; }
    
    public String getPrefix() { return prefix; }
    public void setPrefix(String prefix) { this.prefix = prefix; }
    
    public String getFormula() { return formula; }
    public void setFormula(String formula) { this.formula = formula; }
    
    public FlaggedDef getFlagged() { return flagged; }
    public void setFlagged(FlaggedDef flagged) { this.flagged = flagged; }
    
    public Field getTlvInline() { return tlvInline; }
    public void setTlvInline(Field tlvInline) { this.tlvInline = tlvInline; }

    public int getEffectiveLength() {
        if (length > 0) {
            return length;
        }
        return type.defaultLength();
    }

    public String getEffectiveEndian(String defaultEndian) {
        return endian != null ? endian : defaultEndian;
    }

    public static class Transform {
        private Double add;
        private Double mult;
        private Double div;

        public Double getAdd() { return add; }
        public void setAdd(Double add) { this.add = add; }
        
        public Double getMult() { return mult; }
        public void setMult(Double mult) { this.mult = mult; }
        
        public Double getDiv() { return div; }
        public void setDiv(Double div) { this.div = div; }
    }

    public static class Case {
        private Object caseValue;
        private boolean isDefault;
        private List<Field> fields;

        public Object getCaseValue() { return caseValue; }
        public void setCaseValue(Object caseValue) { this.caseValue = caseValue; }
        
        public boolean isDefault() { return isDefault; }
        public void setDefault(boolean isDefault) { this.isDefault = isDefault; }
        
        public List<Field> getFields() { return fields; }
        public void setFields(List<Field> fields) { this.fields = fields; }
    }

    public static class FlaggedDef {
        private String field;
        private List<FlaggedGroup> groups;

        public String getField() { return field; }
        public void setField(String field) { this.field = field; }
        
        public List<FlaggedGroup> getGroups() { return groups; }
        public void setGroups(List<FlaggedGroup> groups) { this.groups = groups; }
    }

    public static class FlaggedGroup {
        private int bit;
        private List<Field> fields;

        public int getBit() { return bit; }
        public void setBit(int bit) { this.bit = bit; }
        
        public List<Field> getFields() { return fields; }
        public void setFields(List<Field> fields) { this.fields = fields; }
    }
}
