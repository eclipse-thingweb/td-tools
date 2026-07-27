package org.lora.schema;

import java.util.regex.*;

public class FormulaEvaluator {
    
    public static double evaluate(String formula, double x, DecodeContext ctx) {
        String expr = formula;
        
        // Substitute $field_name references
        Pattern varPattern = Pattern.compile("\\$([a-zA-Z_][a-zA-Z0-9_]*)");
        Matcher matcher = varPattern.matcher(expr);
        StringBuffer sb = new StringBuffer();
        while (matcher.find()) {
            String name = matcher.group(1);
            Object val = ctx.getVariable(name);
            double numVal = 0;
            if (val instanceof Number) {
                numVal = ((Number) val).doubleValue();
            }
            matcher.appendReplacement(sb, String.valueOf(numVal));
        }
        matcher.appendTail(sb);
        expr = sb.toString();
        
        // Replace standalone 'x' with raw value
        expr = expr.replaceAll("\\bx\\b", String.valueOf(x));
        
        // Replace 'and'/'or' with logical operators
        expr = expr.replaceAll("\\band\\b", "&&");
        expr = expr.replaceAll("\\bor\\b", "||");
        
        return evalExpr(expr);
    }
    
    private static double evalExpr(String expr) {
        ExprParser parser = new ExprParser(expr.trim());
        return parser.parseTernary();
    }
    
    private static class ExprParser {
        private final String input;
        private int pos;
        
        ExprParser(String input) {
            this.input = input;
            this.pos = 0;
        }
        
        private void skipSpaces() {
            while (pos < input.length() && input.charAt(pos) == ' ') {
                pos++;
            }
        }
        
        private char peek() {
            skipSpaces();
            if (pos >= input.length()) return 0;
            return input.charAt(pos);
        }
        
        private String peekStr(int n) {
            skipSpaces();
            int end = Math.min(pos + n, input.length());
            return input.substring(pos, end);
        }
        
        double parseTernary() {
            double val = parseOr();
            skipSpaces();
            if (pos < input.length() && input.charAt(pos) == '?') {
                pos++;
                double trueVal = parseTernary();
                skipSpaces();
                if (pos < input.length() && input.charAt(pos) == ':') {
                    pos++;
                    double falseVal = parseTernary();
                    return val != 0 ? trueVal : falseVal;
                }
                throw new SchemaException("Expected ':' in ternary");
            }
            return val;
        }
        
        private double parseOr() {
            double val = parseAnd();
            while (true) {
                if (peekStr(2).equals("||")) {
                    pos += 2;
                    double right = parseAnd();
                    val = (val != 0 || right != 0) ? 1 : 0;
                } else {
                    break;
                }
            }
            return val;
        }
        
        private double parseAnd() {
            double val = parseComparison();
            while (true) {
                if (peekStr(2).equals("&&")) {
                    pos += 2;
                    double right = parseComparison();
                    val = (val != 0 && right != 0) ? 1 : 0;
                } else {
                    break;
                }
            }
            return val;
        }
        
        private double parseComparison() {
            double val = parseAddSub();
            while (true) {
                skipSpaces();
                if (peekStr(2).equals(">=")) {
                    pos += 2;
                    double right = parseAddSub();
                    val = val >= right ? 1 : 0;
                } else if (peekStr(2).equals("<=")) {
                    pos += 2;
                    double right = parseAddSub();
                    val = val <= right ? 1 : 0;
                } else if (peekStr(2).equals("==")) {
                    pos += 2;
                    double right = parseAddSub();
                    val = val == right ? 1 : 0;
                } else if (peekStr(2).equals("!=")) {
                    pos += 2;
                    double right = parseAddSub();
                    val = val != right ? 1 : 0;
                } else if (peek() == '>') {
                    pos++;
                    double right = parseAddSub();
                    val = val > right ? 1 : 0;
                } else if (peek() == '<') {
                    pos++;
                    double right = parseAddSub();
                    val = val < right ? 1 : 0;
                } else {
                    break;
                }
            }
            return val;
        }
        
        private double parseAddSub() {
            double val = parseMulDiv();
            while (true) {
                skipSpaces();
                if (peek() == '+') {
                    pos++;
                    val += parseMulDiv();
                } else if (peek() == '-') {
                    pos++;
                    val -= parseMulDiv();
                } else {
                    break;
                }
            }
            return val;
        }
        
        private double parseMulDiv() {
            double val = parseUnary();
            while (true) {
                skipSpaces();
                if (peek() == '*') {
                    pos++;
                    val *= parseUnary();
                } else if (peek() == '/') {
                    pos++;
                    double right = parseUnary();
                    val = right == 0 ? 0 : val / right;
                } else {
                    break;
                }
            }
            return val;
        }
        
        private double parseUnary() {
            skipSpaces();
            if (peek() == '-') {
                pos++;
                return -parsePrimary();
            }
            return parsePrimary();
        }
        
        private double parsePrimary() {
            skipSpaces();
            
            // Parenthesized expression
            if (peek() == '(') {
                pos++;
                double val = parseTernary();
                skipSpaces();
                if (peek() == ')') pos++;
                return val;
            }
            
            // Function calls
            for (String fname : new String[]{"pow", "abs", "sqrt", "min", "max"}) {
                if (pos + fname.length() + 1 <= input.length() && 
                    input.substring(pos).startsWith(fname + "(")) {
                    pos += fname.length() + 1;
                    double arg1 = parseTernary();
                    skipSpaces();
                    
                    switch (fname) {
                        case "abs" -> {
                            if (peek() == ')') pos++;
                            return Math.abs(arg1);
                        }
                        case "sqrt" -> {
                            if (peek() == ')') pos++;
                            return Math.sqrt(arg1);
                        }
                    }
                    
                    // Two-argument functions
                    if (peek() == ',') pos++;
                    double arg2 = parseTernary();
                    skipSpaces();
                    if (peek() == ')') pos++;
                    
                    return switch (fname) {
                        case "pow" -> Math.pow(arg1, arg2);
                        case "min" -> Math.min(arg1, arg2);
                        case "max" -> Math.max(arg1, arg2);
                        default -> 0;
                    };
                }
            }
            
            // Number literal
            int start = pos;
            if (pos < input.length() && (input.charAt(pos) == '-' || input.charAt(pos) == '+')) {
                pos++;
            }
            while (pos < input.length() && 
                   (Character.isDigit(input.charAt(pos)) || 
                    input.charAt(pos) == '.' || 
                    input.charAt(pos) == 'e' || 
                    input.charAt(pos) == 'E')) {
                pos++;
            }
            if (pos > start) {
                String numStr = input.substring(start, pos);
                try {
                    return Double.parseDouble(numStr);
                } catch (NumberFormatException e) {
                    throw new SchemaException("Invalid number: " + numStr);
                }
            }
            
            throw new SchemaException("Unexpected token at position " + pos + ": " + 
                (pos < input.length() ? input.substring(pos) : "end of input"));
        }
    }
}
