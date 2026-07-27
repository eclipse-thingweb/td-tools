/*
 * schema_interpreter.hpp - C++ Runtime Payload Schema Interpreter
 *
 * Modern C++ wrapper around the C interpreter with:
 * - RAII resource management
 * - Type-safe field access
 * - std::variant for field values
 * - Range-based iteration
 *
 * Usage:
 *   Schema schema("env_sensor");
 *   schema.addField<int16_t>("temperature").mult(0.01);
 *   schema.addField<uint8_t>("humidity").mult(0.5);
 *   
 *   auto result = schema.decode(payload);
 *   double temp = result.get<double>("temperature");
 */

#ifndef SCHEMA_INTERPRETER_HPP
#define SCHEMA_INTERPRETER_HPP

#include <string>
#include <vector>
#include <variant>
#include <optional>
#include <stdexcept>
#include <cstring>
#include <cstdint>

namespace payload_schema {

// Field value variant type
using FieldValue = std::variant<
    int64_t,
    uint64_t,
    double,
    bool,
    std::string,
    std::vector<uint8_t>
>;

// Endianness
enum class Endian { Big, Little };

// Field types
enum class FieldType {
    U8, U16, U24, U32,
    S8, S16, S24, S32,
    F32, F64,
    Bool, Bits, Skip,
    Ascii, Hex, Bytes,
    Object, Match, Enum
};

// Decoded field result
struct DecodedField {
    std::string name;
    FieldValue value;
    FieldType type;
    
    template<typename T>
    T as() const {
        if constexpr (std::is_same_v<T, double>) {
            if (auto* d = std::get_if<double>(&value)) return *d;
            if (auto* i = std::get_if<int64_t>(&value)) return static_cast<double>(*i);
            if (auto* u = std::get_if<uint64_t>(&value)) return static_cast<double>(*u);
        } else if constexpr (std::is_integral_v<T>) {
            if (auto* i = std::get_if<int64_t>(&value)) return static_cast<T>(*i);
            if (auto* u = std::get_if<uint64_t>(&value)) return static_cast<T>(*u);
            if (auto* d = std::get_if<double>(&value)) return static_cast<T>(*d);
        } else if constexpr (std::is_same_v<T, std::string>) {
            if (auto* s = std::get_if<std::string>(&value)) return *s;
        } else if constexpr (std::is_same_v<T, bool>) {
            if (auto* b = std::get_if<bool>(&value)) return *b;
        }
        throw std::bad_variant_access();
    }
};

// Decode result
class DecodeResult {
public:
    std::vector<DecodedField> fields;
    int bytes_consumed = 0;
    std::string error;
    
    bool ok() const { return error.empty(); }
    
    template<typename T>
    std::optional<T> get(const std::string& name) const {
        for (const auto& f : fields) {
            if (f.name == name) {
                try {
                    return f.as<T>();
                } catch (...) {
                    return std::nullopt;
                }
            }
        }
        return std::nullopt;
    }
    
    template<typename T>
    T get(const std::string& name, T default_val) const {
        return get<T>(name).value_or(default_val);
    }
    
    // Range-based iteration
    auto begin() const { return fields.begin(); }
    auto end() const { return fields.end(); }
};

// Field definition builder
class FieldBuilder {
public:
    std::string name_;
    FieldType type_;
    uint8_t size_ = 0;
    uint8_t bit_start_ = 0;
    uint8_t bit_width_ = 0;
    bool consume_ = false;
    Endian endian_ = Endian::Big;
    double mult_ = 1.0;
    double div_ = 1.0;
    double add_ = 0.0;
    bool has_mult_ = false;
    bool has_div_ = false;
    bool has_add_ = false;
    std::string var_;
    std::vector<std::pair<int, std::string>> lookup_;
    
    FieldBuilder(const std::string& name, FieldType type) 
        : name_(name), type_(type) {}
    
    FieldBuilder& mult(double m) { mult_ = m; has_mult_ = true; return *this; }
    FieldBuilder& div(double d) { div_ = d; has_div_ = true; return *this; }
    FieldBuilder& add(double a) { add_ = a; has_add_ = true; return *this; }
    FieldBuilder& var(const std::string& v) { var_ = v; return *this; }
    FieldBuilder& endian(Endian e) { endian_ = e; return *this; }
    FieldBuilder& consume(bool c = true) { consume_ = c; return *this; }
    FieldBuilder& size(uint8_t s) { size_ = s; return *this; }
    
    FieldBuilder& lookup(int key, const std::string& value) {
        lookup_.emplace_back(key, value);
        return *this;
    }
};

// Schema class
class Schema {
public:
    explicit Schema(const std::string& name = "") : name_(name) {}
    
    Schema& setName(const std::string& name) { name_ = name; return *this; }
    Schema& setEndian(Endian e) { endian_ = e; return *this; }
    
    // Add field with type deduction
    template<typename T>
    FieldBuilder& addField(const std::string& name) {
        FieldType type;
        if constexpr (std::is_same_v<T, uint8_t>) type = FieldType::U8;
        else if constexpr (std::is_same_v<T, uint16_t>) type = FieldType::U16;
        else if constexpr (std::is_same_v<T, uint32_t>) type = FieldType::U32;
        else if constexpr (std::is_same_v<T, int8_t>) type = FieldType::S8;
        else if constexpr (std::is_same_v<T, int16_t>) type = FieldType::S16;
        else if constexpr (std::is_same_v<T, int32_t>) type = FieldType::S32;
        else if constexpr (std::is_same_v<T, float>) type = FieldType::F32;
        else if constexpr (std::is_same_v<T, double>) type = FieldType::F64;
        else if constexpr (std::is_same_v<T, bool>) type = FieldType::Bool;
        else static_assert(!sizeof(T), "Unsupported field type");
        
        fields_.emplace_back(name, type);
        return fields_.back();
    }
    
    // Add bitfield
    FieldBuilder& addBitfield(const std::string& name, uint8_t start, uint8_t width, bool consume = false) {
        fields_.emplace_back(name, FieldType::Bits);
        fields_.back().bit_start_ = start;
        fields_.back().bit_width_ = width;
        fields_.back().consume_ = consume;
        return fields_.back();
    }
    
    // Decode payload
    DecodeResult decode(const uint8_t* buf, size_t len) const {
        DecodeResult result;
        size_t pos = 0;
        
        std::vector<std::pair<std::string, int64_t>> vars;
        
        for (const auto& field : fields_) {
            if (pos >= len && field.type_ != FieldType::Skip) {
                result.error = "Buffer underrun at field: " + field.name_;
                return result;
            }
            
            DecodedField decoded;
            decoded.name = field.name_;
            decoded.type = field.type_;
            
            int64_t raw_value = 0;
            Endian endian = field.endian_;
            
            switch (field.type_) {
                case FieldType::U8:
                    raw_value = buf[pos++];
                    break;
                    
                case FieldType::U16:
                    if (pos + 2 > len) { result.error = "Buffer underrun"; return result; }
                    raw_value = endian == Endian::Big 
                        ? (buf[pos] << 8) | buf[pos+1]
                        : (buf[pos+1] << 8) | buf[pos];
                    pos += 2;
                    break;
                    
                case FieldType::U32:
                    if (pos + 4 > len) { result.error = "Buffer underrun"; return result; }
                    raw_value = endian == Endian::Big
                        ? ((uint32_t)buf[pos] << 24) | ((uint32_t)buf[pos+1] << 16) |
                          ((uint32_t)buf[pos+2] << 8) | buf[pos+3]
                        : ((uint32_t)buf[pos+3] << 24) | ((uint32_t)buf[pos+2] << 16) |
                          ((uint32_t)buf[pos+1] << 8) | buf[pos];
                    pos += 4;
                    break;
                    
                case FieldType::S8:
                    raw_value = static_cast<int8_t>(buf[pos++]);
                    break;
                    
                case FieldType::S16:
                    if (pos + 2 > len) { result.error = "Buffer underrun"; return result; }
                    raw_value = endian == Endian::Big
                        ? static_cast<int16_t>((buf[pos] << 8) | buf[pos+1])
                        : static_cast<int16_t>((buf[pos+1] << 8) | buf[pos]);
                    pos += 2;
                    break;
                    
                case FieldType::S32:
                    if (pos + 4 > len) { result.error = "Buffer underrun"; return result; }
                    raw_value = endian == Endian::Big
                        ? static_cast<int32_t>(((uint32_t)buf[pos] << 24) | ((uint32_t)buf[pos+1] << 16) |
                          ((uint32_t)buf[pos+2] << 8) | buf[pos+3])
                        : static_cast<int32_t>(((uint32_t)buf[pos+3] << 24) | ((uint32_t)buf[pos+2] << 16) |
                          ((uint32_t)buf[pos+1] << 8) | buf[pos]);
                    pos += 4;
                    break;
                    
                case FieldType::Bits: {
                    uint8_t byte_val = buf[pos];
                    raw_value = (byte_val >> field.bit_start_) & ((1 << field.bit_width_) - 1);
                    if (field.consume_) pos++;
                    break;
                }
                    
                case FieldType::Bool:
                    decoded.value = buf[pos++] != 0;
                    result.fields.push_back(decoded);
                    continue;
                    
                case FieldType::Skip:
                    pos += field.size_ ? field.size_ : 1;
                    continue;
                    
                default:
                    result.error = "Unsupported field type";
                    return result;
            }
            
            // Store variable
            if (!field.var_.empty()) {
                vars.emplace_back(field.var_, raw_value);
            }
            
            // Apply modifiers
            double final_value = static_cast<double>(raw_value);
            if (field.has_mult_) final_value *= field.mult_;
            if (field.has_div_ && field.div_ != 0) final_value /= field.div_;
            if (field.has_add_) final_value += field.add_;
            
            // Apply lookup
            if (!field.lookup_.empty()) {
                for (const auto& [k, v] : field.lookup_) {
                    if (k == static_cast<int>(raw_value)) {
                        decoded.value = v;
                        result.fields.push_back(decoded);
                        goto next_field;
                    }
                }
            }
            
            decoded.value = final_value;
            result.fields.push_back(decoded);
            next_field:;
        }
        
        result.bytes_consumed = static_cast<int>(pos);
        return result;
    }
    
    // Convenience overload
    DecodeResult decode(const std::vector<uint8_t>& buf) const {
        return decode(buf.data(), buf.size());
    }
    
    // Load schema from binary format
    static Schema loadBinary(const uint8_t* data, size_t len) {
        if (len < 5 || data[0] != 'P' || data[1] != 'S') {
            throw std::runtime_error("Invalid binary schema format");
        }
        
        Schema schema("binary");
        schema.endian_ = (data[3] & 0x01) ? Endian::Little : Endian::Big;
        
        uint8_t field_count = data[4];
        size_t offset = 5;
        
        for (int i = 0; i < field_count && offset < len; i++) {
            uint8_t type_byte = data[offset++];
            uint8_t type_code = (type_byte >> 4) & 0x07;
            uint8_t size = type_byte & 0x0F;
            
            // Multiplier
            if (offset >= len) break;
            uint8_t mult_exp = data[offset++];
            double mult = expToMult(mult_exp);
            
            // Field ID (2 bytes LE)
            if (offset + 1 >= len) break;
            uint16_t field_id = data[offset] | (data[offset + 1] << 8);
            offset += 2;
            
            // Generate name from IPSO or ID
            std::string name = ipsoToName(field_id);
            
            // Add field based on type
            FieldBuilder fb(name, typeCodeToFieldType(type_code, size));
            fb.size(size);
            if (mult != 1.0) {
                fb.mult(mult);
            }
            
            // Handle bitfield
            if (type_code == 0x6 && offset < len) {
                uint8_t bf_byte = data[offset++];
                fb.bit_start_ = (bf_byte >> 4) & 0x0F;
                fb.bit_width_ = bf_byte & 0x0F;
                fb.type_ = FieldType::Bits;
            }
            
            schema.fields_.push_back(fb);
        }
        
        return schema;
    }
    
    static Schema loadBinary(const std::vector<uint8_t>& data) {
        return loadBinary(data.data(), data.size());
    }

private:
    std::string name_;
    Endian endian_ = Endian::Big;
    std::vector<FieldBuilder> fields_;
    
    // Type code to FieldType mapping
    static FieldType typeCodeToFieldType(uint8_t code, uint8_t size) {
        switch (code) {
            case 0: // UINT
                switch (size) {
                    case 1: return FieldType::U8;
                    case 2: return FieldType::U16;
                    case 3: return FieldType::U24;
                    case 4: return FieldType::U32;
                }
                break;
            case 1: // SINT
                switch (size) {
                    case 1: return FieldType::S8;
                    case 2: return FieldType::S16;
                    case 3: return FieldType::S24;
                    case 4: return FieldType::S32;
                }
                break;
            case 2: return (size == 4) ? FieldType::F32 : FieldType::F64;
            case 4: return FieldType::Bool;
            case 6: return FieldType::Bits;
            case 8: return FieldType::Skip;
        }
        return FieldType::U8;
    }
    
    // Convert exponent byte to multiplier
    static double expToMult(uint8_t exp) {
        if (exp == 0) return 1.0;
        if (exp == 0x81) return 0.5;
        if (exp == 0x82) return 0.25;
        
        int8_t signed_exp = (exp > 127) ? static_cast<int8_t>(exp - 256) : static_cast<int8_t>(exp);
        double mult = 1.0;
        if (signed_exp > 0) {
            for (int i = 0; i < signed_exp; i++) mult *= 10.0;
        } else {
            for (int i = 0; i < -signed_exp; i++) mult /= 10.0;
        }
        return mult;
    }
    
    // IPSO ID to name
    static std::string ipsoToName(uint16_t id) {
        switch (id) {
            case 3303: return "temperature";
            case 3304: return "humidity";
            case 3315: return "pressure";
            case 3316: return "voltage";
            case 3317: return "current";
            case 3328: return "power";
            case 3330: return "distance";
            case 3301: return "illuminance";
            default: {
                char buf[32];
                snprintf(buf, sizeof(buf), "field_%04x", id);
                return std::string(buf);
            }
        }
    }
};

} // namespace payload_schema

#endif // SCHEMA_INTERPRETER_HPP
