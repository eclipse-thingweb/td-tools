/**
 * All Modbus protocol specific helper functions are defined in this file.
 */
const URLToolkit = require('url-toolkit');

/**
 * get the IP from the URL
 * @param { String } URL 
 * @returns { String } - IP address
 */
function getIP(URL) {
    const urlComponents = URLToolkit.parseURL(URL);
    const ipMatch = urlComponents["netLoc"].match(/\/\/([\d.]+):/);

    if(ipMatch) {
        return ipMatch[1];
    }else {
        throw new Error("IP was not found in the URL");
    }
}

/**
 * Get the Port from the URL
 * @param { String } URL 
 * @returns { String } - Port number
 */
function getPort(URL) {
    const urlComponents = URLToolkit.parseURL(URL);
    const portMatch = urlComponents["netLoc"].match(/:(\d+)$/);
    
    if(portMatch) {
        return portMatch[1];
    }else {
        throw new Error("Port was not found in the URL");
    }
}

/**
 * Get the UnitID from the URL
 * @param { String } URL 
 * @returns { String } unitID - the unitID specified in the URL
 */
function getUnitID(URL) {
    const urlComponents = URLToolkit.parseURL(URL);
    const unitID = urlComponents["path"].replace("/", "");

    if(unitID) {
        return unitID;
    }
    else {
        throw new Error("UnitID was not found in the URL");
    }  
}

/**
 * Get the Address from the URL parameters
 * @param { String } URL 
 * @returns { String } address - the address specified in the parameters
 */
function getAddress(URL) {
    const urlComponents = URLToolkit.parseURL(URL);
    const params = new URLSearchParams(urlComponents["query"]);

    const address = params.get('address');

    if(address) {
        return address;
    }
    else {
        throw new Error("Address was not specified in the URL");
    }
}

/**
 * Get the quantity/length from the URL parameters
 * @param { String } URL 
 * @returns { String } quantity - the quantity specified in the parameters
 */
function getQuantity(URL) {
    const urlComponents = URLToolkit.parseURL(URL);
    const params = new URLSearchParams(urlComponents["query"]);

    const quantity = params.get('quantity');

    if(quantity) {
        return quantity;
    }
    else {
        throw new Error("Quantity was not specified in the URL");
    }
}

/**
 * Get the modbus polling time specified in the form
 * @param { Object } form 
 * @returns { String } pollingTime - the polling time specified in the form
 */
function getPollingTime(form) {
    const pollingTime = form["modv:pollingTime"];

    return pollingTime ? pollingTime : '500';
}

/**
 * Get the modbus function specified in the form, if not specified 
 * set a default one depending on the operation
 * @param { Object } form 
 * @param { String } operation 
 * @returns { String } modbusFunction - the modbus function to be used
 */
function getModbusFunction(form, operation) {

    let modbusFunction;

    const modbusSerialFunctions = {
        readCoil: 'readCoils',
        readDiscreteInput: 'readDiscreteInputs',
        readHoldingRegisters: 'readHoldingRegisters',
        readInputRegisters: 'readInputRegisters',
        writeSingleCoil: 'writeCoil',
        writeSingleHoldingRegister: 'writeRegister',
        writeMultipleCoils: 'writeCoils',
        writeMultipleHoldingRegisters: 'writeRegisters'
    }

    if(form["modv:function"]) {
        modbusFunction = modbusSerialFunctions[form["modv:function"]];
    }
    else {
        if(operation === 'readproperty') {
            modbusFunction = 'readDiscreteInputs';
        }
        else if(operation === 'writeproperty' || operation === 'invokeaction') {
            modbusFunction = 'writeCoil';
        }
        else if(operation === 'observeproperty' || operation === 'unobserveproperty') {
            modbusFunction = 'readCoils';
        }
        else {
            return null;
        }
    }
    
    if(modbusFunction) {
        return modbusFunction;
    }else {
        throw new Error("Not found or wrong Modbus function specified in the TD");
    }
}

//Export all the modbus helper functions
module.exports = {
    getIP,
    getPort,
    getUnitID,
    getAddress,
    getQuantity,
    getPollingTime,
    getModbusFunction
}