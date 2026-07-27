package org.lora.schema;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.HashMap;
import java.util.Map;

public class DecodeContext {
    private final byte[] data;
    private int offset;
    private String endian;
    private final Map<String, Object> variables;

    public DecodeContext(byte[] data, String endian) {
        this.data = data;
        this.offset = 0;
        this.endian = endian != null ? endian : "big";
        this.variables = new HashMap<>();
    }

    public int remaining() {
        return data.length - offset;
    }

    public byte[] read(int n) {
        if (offset + n > data.length) {
            throw new SchemaException.DecodeException(
                String.format("Buffer underflow: need %d bytes at offset %d, but only %d remaining",
                    n, offset, remaining()));
        }
        byte[] result = new byte[n];
        System.arraycopy(data, offset, result, 0, n);
        offset += n;
        return result;
    }

    public byte[] peek(int n, int relativeOffset) {
        int pos = offset + relativeOffset;
        if (pos + n > data.length) {
            throw new SchemaException.DecodeException(
                String.format("Buffer underflow at peek offset %d", pos));
        }
        byte[] result = new byte[n];
        System.arraycopy(data, pos, result, 0, n);
        return result;
    }

    public int getOffset() { return offset; }
    public void setOffset(int offset) { this.offset = offset; }
    
    public String getEndian() { return endian; }
    public void setEndian(String endian) { this.endian = endian; }
    
    public Map<String, Object> getVariables() { return variables; }
    
    public void setVariable(String name, Object value) {
        variables.put(name, value);
    }
    
    public Object getVariable(String name) {
        return variables.get(name);
    }

    public long decodeUnsigned(byte[] bytes, String endian) {
        if (bytes.length == 0) return 0;
        
        long value = 0;
        if ("little".equals(endian)) {
            for (int i = bytes.length - 1; i >= 0; i--) {
                value = (value << 8) | (bytes[i] & 0xFF);
            }
        } else {
            for (byte b : bytes) {
                value = (value << 8) | (b & 0xFF);
            }
        }
        return value;
    }

    public long decodeSigned(byte[] bytes, String endian) {
        long uval = decodeUnsigned(bytes, endian);
        int bits = bytes.length * 8;
        long signBit = 1L << (bits - 1);
        if (uval >= signBit) {
            return uval - (1L << bits);
        }
        return uval;
    }

    public double decodeFloat(byte[] bytes, int size, String endian) {
        ByteBuffer buffer = ByteBuffer.wrap(bytes);
        buffer.order("little".equals(endian) ? ByteOrder.LITTLE_ENDIAN : ByteOrder.BIG_ENDIAN);
        
        return switch (size) {
            case 2 -> float16ToDouble(buffer.getShort());
            case 4 -> buffer.getFloat();
            case 8 -> buffer.getDouble();
            default -> throw new SchemaException.DecodeException("Unsupported float size: " + size);
        };
    }

    private double float16ToDouble(short bits) {
        int sign = (bits >> 15) & 0x1;
        int exp = (bits >> 10) & 0x1F;
        int mant = bits & 0x3FF;

        double value;
        if (exp == 0) {
            value = Math.pow(2, -14) * mant / 1024.0;
        } else if (exp == 31) {
            if (mant != 0) {
                return Double.NaN;
            }
            value = Double.POSITIVE_INFINITY;
        } else {
            value = Math.pow(2, exp - 15) * (1 + mant / 1024.0);
        }

        return sign == 1 ? -value : value;
    }

    public int decodeBits(int byteVal, int bitOffset, int numBits) {
        int mask = (1 << numBits) - 1;
        return (byteVal >> bitOffset) & mask;
    }
}
