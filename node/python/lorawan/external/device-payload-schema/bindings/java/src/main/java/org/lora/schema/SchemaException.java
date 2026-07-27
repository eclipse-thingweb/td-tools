package org.lora.schema;

public class SchemaException extends RuntimeException {
    
    public SchemaException(String message) {
        super(message);
    }
    
    public SchemaException(String message, Throwable cause) {
        super(message, cause);
    }
    
    public static class DecodeException extends SchemaException {
        public DecodeException(String message) {
            super(message);
        }
        
        public DecodeException(String message, Throwable cause) {
            super(message, cause);
        }
    }
    
    public static class EncodeException extends SchemaException {
        public EncodeException(String message) {
            super(message);
        }
        
        public EncodeException(String message, Throwable cause) {
            super(message, cause);
        }
    }
    
    public static class ParseException extends SchemaException {
        public ParseException(String message) {
            super(message);
        }
        
        public ParseException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
