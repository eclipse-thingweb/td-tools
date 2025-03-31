/**
 * All general and reusable utility helper functions are defined in this file.
 */
const JSONSchemaFaker = require("json-schema-faker");

/**
 * Check if two arguments are equal
 * @param { any } arg1 
 * @param { any } arg2 
 * @returns { boolean } - true if equal, false otherwise
 */
function equalTo(arg1, arg2) {
    return arg1 === arg2;
}

/**
 * Check if any of the (2 or 3) arguments are true
 * @param { boolean } arg1 
 * @param { boolean } arg2 
 * @param { boolean } arg3 
 * @returns { boolean } - true if any of the arguments are true, false otherwise
 */
function or(arg1, arg2, arg3) {
    arg1 = arg1 != (true || false) ?  false : arg1;
    arg2 = arg2 != (true || false) ?  false : arg2;
    arg3 = arg3 != (true || false) ?  false : arg3;
    
    return arg1 || arg2 || arg3;
}

/**
 * Join two strings with a space in between
 * @param { String } arg1 
 * @param { String } arg2 
 * @returns { String } - joined string
 */
function joinStr(arg1, arg2) {
    return arg1 + " " + arg2;
}

/**
 * transform a string to follow the camelCase convention
 * @param { String } str 
 * @returns { String } - string in camelCase
 */
function toCamelCase(str) {
    return str
        .toLowerCase()
        .split(" ")
        .map((word, index) => {
            return index > 0 ? word.charAt(0).toUpperCase() + word.slice(1) : word;
        })
        .join(""); 
}

/**
* transform a string to follow the snake_case convention
 * @param { String } str 
 * @returns { String } - string in snake_case
 */
function toSnakeCase(str) {
    str = str.toLowerCase();
    return str.split(" ").join("_");  
}

function toLowerCase(str) {
    return str.toLowerCase();
}

/**
 * Generate a mock input based on the JSON schema in the affordance object
 * @param { Object } affordanceObject 
 * @returns testInput - the generated test input
 */
function generateTestInput(affordanceObject) {
    let testInput;

    if(affordanceObject["input"]) {
        testInput = JSONSchemaFaker.generate(affordanceObject["input"]);
    }else {
        testInput = JSONSchemaFaker.generate(affordanceObject);
    }

    if(typeof testInput === "number" && !Number.isInteger(testInput)) {
        testInput = parseFloat(testInput.toFixed(2));
    }
    
    return testInput;
}

// Export all utility functions
module.exports = {
    equalTo,
    or,
    joinStr,
    toCamelCase,
    toSnakeCase,
    toLowerCase,
    generateTestInput
};