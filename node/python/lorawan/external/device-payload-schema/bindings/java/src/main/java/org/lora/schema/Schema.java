package org.lora.schema;

import org.yaml.snakeyaml.Yaml;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;

public class Schema {
    private String name;
    private int version;
    private String description;
    private String endian = "big";
    private List<Field> header;
    private List<Field> fields;
    private Map<String, PortDef> ports;

    public Schema() {
        this.header = new ArrayList<>();
        this.fields = new ArrayList<>();
    }

    // Getters and setters
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    
    public int getVersion() { return version; }
    public void setVersion(int version) { this.version = version; }
    
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    
    public String getEndian() { return endian; }
    public void setEndian(String endian) { this.endian = endian; }
    
    public List<Field> getHeader() { return header; }
    public void setHeader(List<Field> header) { this.header = header; }
    
    public List<Field> getFields() { return fields; }
    public void setFields(List<Field> fields) { this.fields = fields; }
    
    public Map<String, PortDef> getPorts() { return ports; }
    public void setPorts(Map<String, PortDef> ports) { this.ports = ports; }

    public static Schema fromYaml(String yamlContent) {
        Yaml yaml = new Yaml();
        Map<String, Object> raw = yaml.load(yamlContent);
        return parseRaw(raw);
    }

    public static Schema fromYamlFile(Path path) throws IOException {
        String content = Files.readString(path);
        return fromYaml(content);
    }

    public static Schema fromYamlFile(String path) throws IOException {
        return fromYamlFile(Path.of(path));
    }

    @SuppressWarnings("unchecked")
    private static Schema parseRaw(Map<String, Object> raw) {
        Schema schema = new Schema();
        
        schema.name = (String) raw.getOrDefault("name", "unnamed");
        schema.version = toInt(raw.get("version"), 1);
        schema.description = (String) raw.get("description");
        schema.endian = (String) raw.getOrDefault("endian", "big");
        
        // Parse fields
        Object fieldsRaw = raw.get("fields");
        if (fieldsRaw instanceof List) {
            schema.fields = parseFields((List<Map<String, Object>>) fieldsRaw);
        }
        
        // Parse header
        Object headerRaw = raw.get("header");
        if (headerRaw instanceof List) {
            schema.header = parseFields((List<Map<String, Object>>) headerRaw);
        }
        
        // Parse ports
        Object portsRaw = raw.get("ports");
        if (portsRaw instanceof Map) {
            schema.ports = new HashMap<>();
            Map<?, ?> portsMap = (Map<?, ?>) portsRaw;
            for (Map.Entry<?, ?> entry : portsMap.entrySet()) {
                String portKey = String.valueOf(entry.getKey());
                if (entry.getValue() instanceof Map) {
                    PortDef pd = parsePortDef((Map<String, Object>) entry.getValue());
                    schema.ports.put(portKey, pd);
                }
            }
        }
        
        return schema;
    }

    @SuppressWarnings("unchecked")
    private static PortDef parsePortDef(Map<String, Object> raw) {
        PortDef pd = new PortDef();
        pd.setDirection((String) raw.get("direction"));
        pd.setDescription((String) raw.get("description"));
        
        Object fieldsRaw = raw.get("fields");
        if (fieldsRaw instanceof List) {
            pd.setFields(parseFields((List<Map<String, Object>>) fieldsRaw));
        }
        
        return pd;
    }

    @SuppressWarnings("unchecked")
    private static List<Field> parseFields(List<Map<String, Object>> fieldsRaw) {
        List<Field> fields = new ArrayList<>();
        if (fieldsRaw == null) return fields;
        
        for (Map<String, Object> fm : fieldsRaw) {
            fields.add(parseField(fm));
        }
        return fields;
    }

    @SuppressWarnings("unchecked")
    private static Field parseField(Map<String, Object> fm) {
        Field f = new Field();
        
        f.setName((String) fm.get("name"));
        f.setType(FieldType.fromString((String) fm.get("type")));
        f.setLength(toInt(fm.get("length"), 0));
        f.setByteOffset(toInt(fm.get("byte_offset"), 0));
        f.setBitOffset(toInt(fm.get("bit_offset"), 0));
        f.setBits(toInt(fm.get("bits"), 0));
        f.setEndian((String) fm.get("endian"));
        
        // Modifiers
        if (fm.containsKey("mult")) {
            f.setMult(toDouble(fm.get("mult")));
        }
        if (fm.containsKey("div")) {
            f.setDiv(toDouble(fm.get("div")));
        }
        if (fm.containsKey("add")) {
            f.setAdd(toDouble(fm.get("add")));
        }
        
        // Track modifier order from map key order
        List<String> modOrder = new ArrayList<>();
        for (String key : fm.keySet()) {
            if (key.equals("add") || key.equals("mult") || key.equals("div")) {
                modOrder.add(key);
            }
        }
        f.setModOrder(modOrder);
        
        f.setVar((String) fm.get("var"));
        f.setOn((String) fm.get("on"));
        f.setValue(fm.get("value"));
        f.setFormula((String) fm.get("formula"));
        
        // Transform array
        Object transformRaw = fm.get("transform");
        if (transformRaw instanceof List) {
            List<Field.Transform> transforms = new ArrayList<>();
            for (Object tr : (List<?>) transformRaw) {
                if (tr instanceof Map) {
                    Map<String, Object> tm = (Map<String, Object>) tr;
                    Field.Transform t = new Field.Transform();
                    if (tm.containsKey("add")) t.setAdd(toDouble(tm.get("add")));
                    if (tm.containsKey("mult")) t.setMult(toDouble(tm.get("mult")));
                    if (tm.containsKey("div")) t.setDiv(toDouble(tm.get("div")));
                    transforms.add(t);
                }
            }
            f.setTransform(transforms);
        }
        
        // Lookup table
        Object lookupRaw = fm.get("lookup");
        if (lookupRaw instanceof Map) {
            Map<Integer, String> lookup = new HashMap<>();
            for (Map.Entry<?, ?> entry : ((Map<?, ?>) lookupRaw).entrySet()) {
                int key = toInt(entry.getKey(), 0);
                lookup.put(key, String.valueOf(entry.getValue()));
            }
            f.setLookup(lookup);
        }
        
        // Nested fields
        Object fieldsRaw = fm.get("fields");
        if (fieldsRaw instanceof List) {
            f.setFields(parseFields((List<Map<String, Object>>) fieldsRaw));
        }
        
        // Cases (for match/switch)
        Object casesRaw = fm.get("cases");
        if (casesRaw instanceof List) {
            List<Field.Case> cases = new ArrayList<>();
            for (Object cr : (List<?>) casesRaw) {
                if (cr instanceof Map) {
                    Map<String, Object> cm = (Map<String, Object>) cr;
                    Field.Case c = new Field.Case();
                    c.setCaseValue(cm.get("case") != null ? cm.get("case") : cm.get("match"));
                    c.setDefault(Boolean.TRUE.equals(cm.get("default")));
                    Object caseFieldsRaw = cm.get("fields");
                    if (caseFieldsRaw instanceof List) {
                        c.setFields(parseFields((List<Map<String, Object>>) caseFieldsRaw));
                    }
                    cases.add(c);
                }
            }
            f.setCases(cases);
        }
        
        // TLV cases (map format)
        if (f.getType() == FieldType.TLV && casesRaw instanceof Map) {
            Map<String, List<Field>> tlvCases = new HashMap<>();
            for (Map.Entry<?, ?> entry : ((Map<?, ?>) casesRaw).entrySet()) {
                String key = String.valueOf(entry.getKey());
                if (entry.getValue() instanceof List) {
                    tlvCases.put(key, parseFields((List<Map<String, Object>>) entry.getValue()));
                }
            }
            f.setTlvCases(tlvCases);
        }
        
        // Repeat fields
        f.setCount(fm.get("count"));
        f.setByteLength(fm.get("byte_length"));
        f.setUntil((String) fm.get("until"));
        f.setMax(toInt(fm.get("max"), 0));
        f.setMin(toInt(fm.get("min"), 0));
        
        // Bytes format
        f.setFormat((String) fm.get("format"));
        f.setSeparator((String) fm.get("separator"));
        
        // TLV fields
        f.setTagSize(toInt(fm.get("tag_size"), 0));
        f.setLengthSize(toInt(fm.get("length_size"), 0));
        Object tagFieldsRaw = fm.get("tag_fields");
        if (tagFieldsRaw instanceof List) {
            f.setTagFields(parseFields((List<Map<String, Object>>) tagFieldsRaw));
        }
        f.setTagKey(fm.get("tag_key"));
        if (fm.containsKey("merge")) {
            f.setMerge((Boolean) fm.get("merge"));
        }
        f.setUnknown((String) fm.get("unknown"));
        
        // Bitfield string
        f.setDelimiter((String) fm.get("delimiter"));
        f.setPrefix((String) fm.get("prefix"));
        Object partsRaw = fm.get("parts");
        if (partsRaw instanceof List) {
            List<List<Object>> parts = new ArrayList<>();
            for (Object p : (List<?>) partsRaw) {
                if (p instanceof List) {
                    parts.add(new ArrayList<>((List<?>) p));
                }
            }
            f.setParts(parts);
        }
        
        // Flagged construct
        Object flaggedRaw = fm.get("flagged");
        if (flaggedRaw instanceof Map) {
            Map<String, Object> flaggedMap = (Map<String, Object>) flaggedRaw;
            Field.FlaggedDef fd = new Field.FlaggedDef();
            fd.setField((String) flaggedMap.get("field"));
            
            Object groupsRaw = flaggedMap.get("groups");
            if (groupsRaw instanceof List) {
                List<Field.FlaggedGroup> groups = new ArrayList<>();
                for (Object gr : (List<?>) groupsRaw) {
                    if (gr instanceof Map) {
                        Map<String, Object> gm = (Map<String, Object>) gr;
                        Field.FlaggedGroup g = new Field.FlaggedGroup();
                        g.setBit(toInt(gm.get("bit"), 0));
                        Object gFieldsRaw = gm.get("fields");
                        if (gFieldsRaw instanceof List) {
                            g.setFields(parseFields((List<Map<String, Object>>) gFieldsRaw));
                        }
                        groups.add(g);
                    }
                }
                fd.setGroups(groups);
            }
            f.setFlagged(fd);
        }
        
        // TLV inline
        Object tlvRaw = fm.get("tlv");
        if (tlvRaw instanceof Map) {
            Field tlvField = parseField((Map<String, Object>) tlvRaw);
            tlvField.setType(FieldType.TLV);
            f.setTlvInline(tlvField);
        }
        
        return f;
    }

    // Decode methods
    public Map<String, Object> decode(byte[] data) {
        DecodeContext ctx = new DecodeContext(data, endian);
        Map<String, Object> result = new LinkedHashMap<>();
        
        // Decode header
        if (header != null && !header.isEmpty()) {
            Map<String, Object> headerResult = decodeFields(header, ctx);
            result.putAll(headerResult);
        }
        
        // Decode main fields
        Map<String, Object> fieldsResult = decodeFields(fields, ctx);
        result.putAll(fieldsResult);
        
        return result;
    }

    public Map<String, Object> decodeWithPort(byte[] data, int fPort) {
        List<Field> resolvedFields = resolveFields(fPort);
        
        DecodeContext ctx = new DecodeContext(data, endian);
        Map<String, Object> result = new LinkedHashMap<>();
        
        // Decode header
        if (header != null && !header.isEmpty()) {
            Map<String, Object> headerResult = decodeFields(header, ctx);
            result.putAll(headerResult);
        }
        
        // Decode resolved fields
        Map<String, Object> fieldsResult = decodeFields(resolvedFields, ctx);
        result.putAll(fieldsResult);
        
        return result;
    }

    private List<Field> resolveFields(int fPort) {
        if (ports == null) {
            return fields;
        }
        
        String portKey = String.valueOf(fPort);
        if (ports.containsKey(portKey)) {
            return ports.get(portKey).getFields();
        }
        if (ports.containsKey("default")) {
            return ports.get("default").getFields();
        }
        
        throw new SchemaException.DecodeException(
            String.format("No port definition for fPort %d and no default in schema '%s'", fPort, name));
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> decodeFields(List<Field> fieldList, DecodeContext ctx) {
        Map<String, Object> result = new LinkedHashMap<>();
        
        for (Field field : fieldList) {
            // Handle TLV
            if (field.getType() == FieldType.TLV) {
                Map<String, Object> tlvResult = decodeTLV(field, ctx);
                result.putAll(tlvResult);
                continue;
            }
            
            // Handle TLV inline
            if (field.getTlvInline() != null) {
                Map<String, Object> tlvResult = decodeTLV(field.getTlvInline(), ctx);
                result.putAll(tlvResult);
                continue;
            }
            
            // Handle flagged construct
            if (field.getFlagged() != null) {
                Map<String, Object> flaggedResult = decodeFlagged(field.getFlagged(), ctx);
                result.putAll(flaggedResult);
                for (Map.Entry<String, Object> entry : flaggedResult.entrySet()) {
                    ctx.setVariable(entry.getKey(), entry.getValue());
                }
                continue;
            }
            
            Object value = decodeField(field, ctx);
            
            if (value != null && field.getName() != null && !field.getName().isEmpty()) {
                result.put(field.getName(), value);
                ctx.setVariable(field.getName(), value);
            }
        }
        
        return result;
    }

    private Map<String, Object> decodeFlagged(Field.FlaggedDef fd, DecodeContext ctx) {
        Object flagsVal = ctx.getVariable(fd.getField());
        if (flagsVal == null) {
            throw new SchemaException.DecodeException("Flagged field reference not found: " + fd.getField());
        }
        int flags = toInt(flagsVal, 0);
        
        Map<String, Object> result = new LinkedHashMap<>();
        
        for (Field.FlaggedGroup group : fd.getGroups()) {
            int isPresent = (flags >> group.getBit()) & 1;
            if (isPresent != 0) {
                Map<String, Object> groupResult = decodeFields(group.getFields(), ctx);
                result.putAll(groupResult);
            }
        }
        
        return result;
    }

    private Object decodeField(Field field, DecodeContext ctx) {
        int length = field.getEffectiveLength();
        String fieldEndian = field.getEffectiveEndian(ctx.getEndian());
        
        Object value = null;
        
        switch (field.getType()) {
            case U8, U16, U32, U64, BYTE, UINT -> {
                byte[] data = ctx.read(length);
                value = ctx.decodeUnsigned(data, fieldEndian);
            }
            
            case I8, I16, I32, I64, S8, S16, S32, S64, SINT -> {
                byte[] data = ctx.read(length);
                value = ctx.decodeSigned(data, fieldEndian);
            }
            
            case BINT -> {
                byte[] data = ctx.read(length);
                value = ctx.decodeUnsigned(data, "big");
            }
            
            case F16, F32, F64, FLOAT16, FLOAT32, FLOAT64 -> {
                int size = switch (field.getType()) {
                    case F16, FLOAT16 -> 2;
                    case F32, FLOAT32 -> 4;
                    case F64, FLOAT64 -> 8;
                    default -> 4;
                };
                byte[] data = ctx.read(size);
                value = ctx.decodeFloat(data, size, fieldEndian);
            }
            
            case BOOL -> {
                byte[] data = ctx.peek(1, field.getByteOffset());
                value = ctx.decodeBits(data[0] & 0xFF, field.getBitOffset(), 1) != 0;
            }
            
            case BITS -> {
                byte[] data = ctx.peek(1, field.getByteOffset());
                int numBits = field.getBits() > 0 ? field.getBits() : 1;
                value = (long) ctx.decodeBits(data[0] & 0xFF, field.getBitOffset(), numBits);
            }
            
            case ASCII -> {
                byte[] data = ctx.read(length);
                String str = new String(data, StandardCharsets.US_ASCII);
                value = str.replace("\0", "").trim();
            }
            
            case HEX -> {
                byte[] data = ctx.read(length);
                value = bytesToHex(data);
            }
            
            case SKIP -> {
                ctx.read(length);
                return null;
            }
            
            case BYTES -> {
                byte[] data = ctx.read(length);
                value = formatBytes(data, field.getFormat(), field.getSeparator());
            }
            
            case REPEAT -> {
                value = decodeRepeat(field, ctx);
            }
            
            case BITFIELD_STRING -> {
                byte[] data = ctx.read(length);
                long intVal = ctx.decodeUnsigned(data, fieldEndian);
                value = decodeBitfieldString(intVal, field);
            }
            
            case STRING -> {
                value = field.getValue();
            }
            
            case NUMBER -> {
                if (field.getFormula() != null && !field.getFormula().isEmpty()) {
                    value = FormulaEvaluator.evaluate(field.getFormula(), 0, ctx);
                } else {
                    value = field.getValue();
                }
            }
            
            case OBJECT -> {
                value = decodeFields(field.getFields(), ctx);
            }
            
            case MATCH, SWITCH -> {
                value = decodeMatch(field, ctx);
            }
            
            case TLV -> {
                return decodeTLV(field, ctx);
            }
            
            default -> throw new SchemaException.DecodeException("Unknown field type: " + field.getType());
        }
        
        // Apply formula if present (takes precedence)
        if (field.getFormula() != null && !field.getFormula().isEmpty() && field.getType() != FieldType.NUMBER) {
            if (value instanceof Number) {
                value = FormulaEvaluator.evaluate(field.getFormula(), ((Number) value).doubleValue(), ctx);
            }
        } else if (value instanceof Number) {
            // Apply transformations
            double numVal = ((Number) value).doubleValue();
            
            if (field.getTransform() != null && !field.getTransform().isEmpty()) {
                for (Field.Transform t : field.getTransform()) {
                    if (t.getAdd() != null) numVal += t.getAdd();
                    if (t.getMult() != null) numVal *= t.getMult();
                    if (t.getDiv() != null && t.getDiv() != 0) numVal /= t.getDiv();
                }
            } else if (!field.getModOrder().isEmpty()) {
                for (String mod : field.getModOrder()) {
                    switch (mod) {
                        case "add" -> { if (field.getAdd() != null) numVal += field.getAdd(); }
                        case "mult" -> { if (field.getMult() != null) numVal *= field.getMult(); }
                        case "div" -> { if (field.getDiv() != null && field.getDiv() != 0) numVal /= field.getDiv(); }
                    }
                }
            } else {
                if (field.getAdd() != null) numVal += field.getAdd();
                if (field.getMult() != null) numVal *= field.getMult();
                if (field.getDiv() != null && field.getDiv() != 0) numVal /= field.getDiv();
            }
            
            value = numVal;
        }
        
        // Apply lookup
        if (field.getLookup() != null && value instanceof Number) {
            int intVal = ((Number) value).intValue();
            if (field.getLookup().containsKey(intVal)) {
                value = field.getLookup().get(intVal);
            }
        }
        
        // Store variable
        if (field.getVar() != null && !field.getVar().isEmpty()) {
            ctx.setVariable(field.getVar(), value);
        }
        
        return value;
    }

    private Object decodeMatch(Field field, DecodeContext ctx) {
        int matchValue;
        
        if (field.getOn() != null && !field.getOn().isEmpty()) {
            String varName = field.getOn().startsWith("$") ? field.getOn().substring(1) : field.getOn();
            Object val = ctx.getVariable(varName);
            if (val == null) {
                throw new SchemaException.DecodeException("Variable not found: $" + varName);
            }
            matchValue = toInt(val, 0);
        } else {
            int length = field.getLength() > 0 ? field.getLength() : 1;
            byte[] data = ctx.read(length);
            matchValue = (int) ctx.decodeUnsigned(data, ctx.getEndian());
        }
        
        for (Field.Case c : field.getCases()) {
            if (c.isDefault()) {
                return decodeFields(c.getFields(), ctx);
            }
            
            Object caseVal = c.getCaseValue();
            if (caseVal == null) continue;
            
            boolean matched = false;
            
            if (caseVal instanceof Number) {
                matched = matchValue == ((Number) caseVal).intValue();
            } else if (caseVal instanceof List<?> list) {
                for (Object item : list) {
                    if (item instanceof Number && matchValue == ((Number) item).intValue()) {
                        matched = true;
                        break;
                    }
                }
            } else if (caseVal instanceof Map<?, ?> rangeMap) {
                int minVal = toInt(rangeMap.get("min"), Integer.MIN_VALUE);
                int maxVal = toInt(rangeMap.get("max"), Integer.MAX_VALUE);
                matched = matchValue >= minVal && matchValue <= maxVal;
            }
            
            if (matched) {
                return decodeFields(c.getFields(), ctx);
            }
        }
        
        return null;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> decodeTLV(Field field, DecodeContext ctx) {
        int tagSize = field.getTagSize() > 0 ? field.getTagSize() : 1;
        int lengthSize = field.getLengthSize();
        boolean merge = field.getMerge() == null || field.getMerge();
        String unknownMode = field.getUnknown() != null ? field.getUnknown() : "skip";
        
        Map<String, Object> result = new LinkedHashMap<>();
        List<Map<String, Object>> channels = new ArrayList<>();
        
        while (ctx.remaining() > 0) {
            List<Integer> tag = new ArrayList<>();
            Map<String, Integer> tagValues = new HashMap<>();
            
            if (field.getTagFields() != null && !field.getTagFields().isEmpty()) {
                for (Field tf : field.getTagFields()) {
                    int tfLength = tf.getLength() > 0 ? tf.getLength() : 1;
                    byte[] data = ctx.read(tfLength);
                    int val = (int) ctx.decodeUnsigned(data, ctx.getEndian());
                    if (tf.getName() != null) {
                        tagValues.put(tf.getName(), val);
                    }
                }
                
                Object tagKey = field.getTagKey();
                if (tagKey instanceof List<?> keyList) {
                    for (Object k : keyList) {
                        if (k instanceof String && tagValues.containsKey(k)) {
                            tag.add(tagValues.get(k));
                        }
                    }
                } else if (tagKey instanceof String) {
                    tag.add(tagValues.getOrDefault((String) tagKey, 0));
                } else if (!field.getTagFields().isEmpty() && field.getTagFields().get(0).getName() != null) {
                    tag.add(tagValues.getOrDefault(field.getTagFields().get(0).getName(), 0));
                }
            } else {
                byte[] data = ctx.read(tagSize);
                tag.add((int) ctx.decodeUnsigned(data, ctx.getEndian()));
            }
            
            int dataLength = -1;
            if (lengthSize > 0) {
                byte[] data = ctx.read(lengthSize);
                dataLength = (int) ctx.decodeUnsigned(data, ctx.getEndian());
            }
            
            String caseKey = findTLVCaseKey(field.getTlvCases(), tag);
            
            if (caseKey != null) {
                List<Field> caseFields = field.getTlvCases().get(caseKey);
                Map<String, Object> caseResult = decodeFields(caseFields, ctx);
                
                if (merge) {
                    for (Map.Entry<String, Object> entry : caseResult.entrySet()) {
                        String k = entry.getKey();
                        Object v = entry.getValue();
                        if (result.containsKey(k)) {
                            Object existing = result.get(k);
                            if (existing instanceof List) {
                                ((List<Object>) existing).add(v);
                            } else {
                                List<Object> arr = new ArrayList<>();
                                arr.add(existing);
                                arr.add(v);
                                result.put(k, arr);
                            }
                        } else {
                            result.put(k, v);
                        }
                    }
                } else {
                    Map<String, Object> entry = new LinkedHashMap<>();
                    entry.put("tag", tag);
                    entry.putAll(caseResult);
                    channels.add(entry);
                }
            } else {
                if ("error".equals(unknownMode)) {
                    throw new SchemaException.DecodeException("Unknown TLV tag: " + tag);
                } else if (dataLength >= 0) {
                    ctx.read(dataLength);
                } else {
                    break;
                }
            }
        }
        
        if (!merge) {
            result.put("channels", channels);
        }
        
        return result;
    }

    private String findTLVCaseKey(Map<String, List<Field>> cases, List<Integer> tag) {
        if (cases == null) return null;
        
        if (tag.size() == 1) {
            String key = String.valueOf(tag.get(0));
            if (cases.containsKey(key)) {
                return key;
            }
        }
        
        String tagJson = tag.toString();
        if (cases.containsKey(tagJson)) {
            return tagJson;
        }
        
        return null;
    }

    private List<Map<String, Object>> decodeRepeat(Field field, DecodeContext ctx) {
        int maxIterations = field.getMax() > 0 ? field.getMax() : 1000;
        int minIterations = field.getMin();
        
        List<Map<String, Object>> result = new ArrayList<>();
        
        if (field.getCount() != null) {
            int count;
            if (field.getCount() instanceof Number) {
                count = ((Number) field.getCount()).intValue();
            } else if (field.getCount() instanceof String) {
                String varName = ((String) field.getCount()).replace("$", "");
                Object val = ctx.getVariable(varName);
                if (val == null) {
                    throw new SchemaException.DecodeException("Repeat count variable not found: " + varName);
                }
                count = toInt(val, 0);
            } else {
                throw new SchemaException.DecodeException("Invalid count type: " + field.getCount().getClass());
            }
            
            count = Math.min(count, maxIterations);
            
            for (int i = 0; i < count; i++) {
                result.add(decodeFields(field.getFields(), ctx));
            }
        } else if (field.getByteLength() != null) {
            int byteLen;
            if (field.getByteLength() instanceof Number) {
                byteLen = ((Number) field.getByteLength()).intValue();
            } else if (field.getByteLength() instanceof String) {
                String varName = ((String) field.getByteLength()).replace("$", "");
                Object val = ctx.getVariable(varName);
                if (val == null) {
                    throw new SchemaException.DecodeException("Repeat byte_length variable not found: " + varName);
                }
                byteLen = toInt(val, 0);
            } else {
                throw new SchemaException.DecodeException("Invalid byte_length type");
            }
            
            int endOffset = ctx.getOffset() + byteLen;
            int iterations = 0;
            
            while (ctx.getOffset() < endOffset && iterations < maxIterations) {
                result.add(decodeFields(field.getFields(), ctx));
                iterations++;
            }
            
            if (ctx.getOffset() != endOffset) {
                throw new SchemaException.DecodeException(
                    String.format("Repeat byte_length mismatch: expected end at %d, got %d", endOffset, ctx.getOffset()));
            }
        } else if ("end".equals(field.getUntil())) {
            int iterations = 0;
            while (ctx.remaining() > 0 && iterations < maxIterations) {
                result.add(decodeFields(field.getFields(), ctx));
                iterations++;
            }
        } else {
            throw new SchemaException.DecodeException("Repeat field must specify one of: count, byte_length, or until");
        }
        
        if (result.size() < minIterations) {
            throw new SchemaException.DecodeException(
                String.format("Repeat produced %d elements, but minimum is %d", result.size(), minIterations));
        }
        
        return result;
    }

    private String decodeBitfieldString(long intVal, Field field) {
        String delimiter = field.getDelimiter() != null ? field.getDelimiter() : ".";
        String prefix = field.getPrefix() != null ? field.getPrefix() : "";
        
        List<String> partStrs = new ArrayList<>();
        if (field.getParts() != null) {
            for (List<Object> part : field.getParts()) {
                if (part.size() < 2) continue;
                
                int bitOff = toInt(part.get(0), 0);
                int bitLen = toInt(part.get(1), 0);
                String format = part.size() >= 3 ? String.valueOf(part.get(2)) : "decimal";
                
                long mask = (1L << bitLen) - 1;
                long raw = (intVal >> bitOff) & mask;
                
                if ("hex".equals(format)) {
                    partStrs.add(Long.toHexString(raw).toUpperCase());
                } else {
                    partStrs.add(String.valueOf(raw));
                }
            }
        }
        
        return prefix + String.join(delimiter, partStrs);
    }

    private Object formatBytes(byte[] data, String format, String separator) {
        if (format == null) format = "hex";
        
        return switch (format) {
            case "hex", "hex:lower" -> {
                if (separator != null && !separator.isEmpty()) {
                    StringBuilder sb = new StringBuilder();
                    for (int i = 0; i < data.length; i++) {
                        if (i > 0) sb.append(separator);
                        sb.append(String.format("%02x", data[i]));
                    }
                    yield sb.toString();
                }
                yield bytesToHex(data);
            }
            case "hex:upper" -> {
                if (separator != null && !separator.isEmpty()) {
                    StringBuilder sb = new StringBuilder();
                    for (int i = 0; i < data.length; i++) {
                        if (i > 0) sb.append(separator);
                        sb.append(String.format("%02X", data[i]));
                    }
                    yield sb.toString();
                }
                yield bytesToHex(data).toUpperCase();
            }
            case "base64" -> Base64.getEncoder().encodeToString(data);
            case "array" -> {
                List<Integer> arr = new ArrayList<>();
                for (byte b : data) {
                    arr.add(b & 0xFF);
                }
                yield arr;
            }
            default -> bytesToHex(data);
        };
    }

    // Utility methods
    private static String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }

    private static int toInt(Object obj, int defaultValue) {
        if (obj == null) return defaultValue;
        if (obj instanceof Number) return ((Number) obj).intValue();
        if (obj instanceof String) {
            try {
                return Integer.parseInt((String) obj);
            } catch (NumberFormatException e) {
                return defaultValue;
            }
        }
        return defaultValue;
    }

    private static Double toDouble(Object obj) {
        if (obj == null) return null;
        if (obj instanceof Number) return ((Number) obj).doubleValue();
        if (obj instanceof String) {
            try {
                return Double.parseDouble((String) obj);
            } catch (NumberFormatException e) {
                return null;
            }
        }
        return null;
    }

    public static class PortDef {
        private String direction;
        private String description;
        private List<Field> fields;

        public String getDirection() { return direction; }
        public void setDirection(String direction) { this.direction = direction; }
        
        public String getDescription() { return description; }
        public void setDescription(String description) { this.description = description; }
        
        public List<Field> getFields() { return fields; }
        public void setFields(List<Field> fields) { this.fields = fields; }
    }
}
