package org.lora.schema;

public class Varint {
    
    public static class DecodeResult {
        public final long value;
        public final int newPos;
        
        public DecodeResult(long value, int newPos) {
            this.value = value;
            this.newPos = newPos;
        }
    }
    
    public static DecodeResult decode(byte[] data, int pos) {
        long result = 0;
        int shift = 0;
        while (pos < data.length) {
            int b = data[pos++] & 0xFF;
            result |= (long)(b & 0x7F) << shift;
            if ((b & 0x80) == 0) break;
            shift += 7;
        }
        return new DecodeResult(result, pos);
    }
    
    public static DecodeResult decodeSigned(byte[] data, int pos) {
        DecodeResult r = decode(data, pos);
        long zigzag = r.value;
        long value = (zigzag >>> 1) ^ -(zigzag & 1);
        return new DecodeResult(value, r.newPos);
    }
    
    public static byte[] encode(long value) {
        if (value == 0) return new byte[]{0};
        
        byte[] temp = new byte[10];
        int len = 0;
        while (value != 0) {
            int b = (int)(value & 0x7F);
            value >>>= 7;
            if (value != 0) {
                b |= 0x80;
            }
            temp[len++] = (byte)b;
        }
        
        byte[] result = new byte[len];
        System.arraycopy(temp, 0, result, 0, len);
        return result;
    }
    
    public static byte[] encodeSigned(long value) {
        long zigzag = (value << 1) ^ (value >> 63);
        return encode(zigzag);
    }
}
