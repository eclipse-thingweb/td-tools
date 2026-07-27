/*
 * schema_native.cc - Node.js N-API bindings for C schema interpreter
 *
 * Build: npm install && npm run build
 * Or: node-gyp rebuild
 */

#include <napi.h>
#include <string>
#include <cstring>

// Include the C schema interpreter
extern "C" {
#include "schema_interpreter.h"
}

// Schema wrapper class
class SchemaWrapper : public Napi::ObjectWrap<SchemaWrapper> {
public:
    static Napi::Object Init(Napi::Env env, Napi::Object exports);
    SchemaWrapper(const Napi::CallbackInfo& info);
    ~SchemaWrapper();

private:
    static Napi::FunctionReference constructor;
    
    Napi::Value Decode(const Napi::CallbackInfo& info);
    Napi::Value DecodeJSON(const Napi::CallbackInfo& info);
    Napi::Value GetName(const Napi::CallbackInfo& info);
    Napi::Value GetFieldCount(const Napi::CallbackInfo& info);
    
    schema_t schema_;
    bool valid_;
};

Napi::FunctionReference SchemaWrapper::constructor;

Napi::Object SchemaWrapper::Init(Napi::Env env, Napi::Object exports) {
    Napi::Function func = DefineClass(env, "NativeSchema", {
        InstanceMethod("decode", &SchemaWrapper::Decode),
        InstanceMethod("decodeJSON", &SchemaWrapper::DecodeJSON),
        InstanceAccessor("name", &SchemaWrapper::GetName, nullptr),
        InstanceAccessor("fieldCount", &SchemaWrapper::GetFieldCount, nullptr),
    });

    constructor = Napi::Persistent(func);
    constructor.SuppressDestruct();

    exports.Set("NativeSchema", func);
    return exports;
}

SchemaWrapper::SchemaWrapper(const Napi::CallbackInfo& info) 
    : Napi::ObjectWrap<SchemaWrapper>(info), valid_(false) {
    Napi::Env env = info.Env();

    if (info.Length() < 1 || !info[0].IsBuffer()) {
        Napi::TypeError::New(env, "Buffer expected for binary schema data")
            .ThrowAsJavaScriptException();
        return;
    }

    Napi::Buffer<uint8_t> buffer = info[0].As<Napi::Buffer<uint8_t>>();
    const uint8_t* data = buffer.Data();
    size_t len = buffer.Length();

    schema_init(&schema_);
    int ret = schema_load_binary(&schema_, data, len);
    
    if (ret != 0) {
        Napi::Error::New(env, "Failed to parse binary schema")
            .ThrowAsJavaScriptException();
        return;
    }

    valid_ = true;
}

SchemaWrapper::~SchemaWrapper() {
    // schema_t uses static allocation, no cleanup needed
}

Napi::Value SchemaWrapper::GetName(const Napi::CallbackInfo& info) {
    Napi::Env env = info.Env();
    if (!valid_) {
        return Napi::String::New(env, "");
    }
    return Napi::String::New(env, schema_.name);
}

Napi::Value SchemaWrapper::GetFieldCount(const Napi::CallbackInfo& info) {
    Napi::Env env = info.Env();
    if (!valid_) {
        return Napi::Number::New(env, 0);
    }
    return Napi::Number::New(env, schema_.field_count);
}

Napi::Value SchemaWrapper::Decode(const Napi::CallbackInfo& info) {
    Napi::Env env = info.Env();

    if (!valid_) {
        Napi::Error::New(env, "Schema not initialized")
            .ThrowAsJavaScriptException();
        return env.Null();
    }

    if (info.Length() < 1 || !info[0].IsBuffer()) {
        Napi::TypeError::New(env, "Buffer expected for payload")
            .ThrowAsJavaScriptException();
        return env.Null();
    }

    Napi::Buffer<uint8_t> buffer = info[0].As<Napi::Buffer<uint8_t>>();
    const uint8_t* payload = buffer.Data();
    size_t payload_len = buffer.Length();

    decode_result_t result;
    int ret = schema_decode_payload(&schema_, payload, payload_len, &result);

    if (ret != 0) {
        std::string msg = "Decode error: ";
        msg += result.error_msg;
        Napi::Error::New(env, msg).ThrowAsJavaScriptException();
        return env.Null();
    }

    // Build result object
    Napi::Object obj = Napi::Object::New(env);

    for (int i = 0; i < result.field_count; i++) {
        decoded_field_t* f = &result.fields[i];
        if (!f->valid || f->name[0] == '\0') continue;

        std::string name(f->name);
        
        switch (f->type) {
            case FIELD_TYPE_U8:
            case FIELD_TYPE_U16:
            case FIELD_TYPE_U24:
            case FIELD_TYPE_U32:
            case FIELD_TYPE_S8:
            case FIELD_TYPE_S16:
            case FIELD_TYPE_S24:
            case FIELD_TYPE_S32:
                obj.Set(name, Napi::Number::New(env, static_cast<double>(f->value.i64)));
                break;

            case FIELD_TYPE_U64:
            case FIELD_TYPE_S64:
                // For large integers, use BigInt
                obj.Set(name, Napi::BigInt::New(env, f->value.i64));
                break;

            case FIELD_TYPE_F16:
            case FIELD_TYPE_F32:
            case FIELD_TYPE_F64:
                obj.Set(name, Napi::Number::New(env, f->value.f64));
                break;

            case FIELD_TYPE_BOOL:
                obj.Set(name, Napi::Boolean::New(env, f->value.b));
                break;

            case FIELD_TYPE_ASCII:
            case FIELD_TYPE_HEX:
                obj.Set(name, Napi::String::New(env, f->value.str));
                break;

            default:
                obj.Set(name, Napi::Number::New(env, static_cast<double>(f->value.i64)));
                break;
        }
    }

    return obj;
}

Napi::Value SchemaWrapper::DecodeJSON(const Napi::CallbackInfo& info) {
    Napi::Env env = info.Env();

    if (!valid_) {
        Napi::Error::New(env, "Schema not initialized")
            .ThrowAsJavaScriptException();
        return env.Null();
    }

    if (info.Length() < 1 || !info[0].IsBuffer()) {
        Napi::TypeError::New(env, "Buffer expected for payload")
            .ThrowAsJavaScriptException();
        return env.Null();
    }

    Napi::Buffer<uint8_t> buffer = info[0].As<Napi::Buffer<uint8_t>>();
    const uint8_t* payload = buffer.Data();
    size_t payload_len = buffer.Length();

    decode_result_t result;
    int ret = schema_decode_payload(&schema_, payload, payload_len, &result);

    if (ret != 0) {
        std::string msg = "Decode error: ";
        msg += result.error_msg;
        Napi::Error::New(env, msg).ThrowAsJavaScriptException();
        return env.Null();
    }

    // Build JSON string directly
    std::string json = "{";
    bool first = true;

    for (int i = 0; i < result.field_count; i++) {
        decoded_field_t* f = &result.fields[i];
        if (!f->valid || f->name[0] == '\0') continue;

        if (!first) json += ",";
        first = false;

        json += "\"";
        json += f->name;
        json += "\":";

        char buf[64];
        switch (f->type) {
            case FIELD_TYPE_F16:
            case FIELD_TYPE_F32:
            case FIELD_TYPE_F64:
                snprintf(buf, sizeof(buf), "%g", f->value.f64);
                json += buf;
                break;

            case FIELD_TYPE_BOOL:
                json += f->value.b ? "true" : "false";
                break;

            case FIELD_TYPE_ASCII:
            case FIELD_TYPE_HEX:
                json += "\"";
                json += f->value.str;
                json += "\"";
                break;

            default:
                snprintf(buf, sizeof(buf), "%lld", (long long)f->value.i64);
                json += buf;
                break;
        }
    }

    json += "}";
    return Napi::String::New(env, json);
}

// Module helper functions
Napi::Value GetVersion(const Napi::CallbackInfo& info) {
    return Napi::String::New(info.Env(), "1.0.0");
}

Napi::Object Init(Napi::Env env, Napi::Object exports) {
    SchemaWrapper::Init(env, exports);
    exports.Set("version", Napi::Function::New(env, GetVersion));
    return exports;
}

NODE_API_MODULE(schema_native, Init)
