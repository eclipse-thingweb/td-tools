/**
 * All HTTP protocol specific helper functions are defined in this file
 */


/**
 * Get the subprotocol from the form, if it is not present, return sse as the default subprotocol
 * @param { Object } form 
 * @param { String } operation 
 * @returns { String } - the subprotocol to be used
 */
function getSubprotocol(form, operation) {
    if(form["subprotocol"]) {
        return form["subprotocol"];
    }else {
        if(operation == "observeproperty" || operation == "unobserveproperty" || operation == "subscribeevent" || operation == "unsubscribeevent") {
            return 'sse';
        }else{
            return null;
        }
    }
}

/**
 * Get the htv:methodName from the form to return the required method, or
 * return the default method for the specified operation
 * @param { Object } form 
 * @param { String } operation 
 * @returns { String } - the method to be used
 */
function getMethod(form, operation) {

    if(form["htv:methodName"]){
        return form["htv:methodName"];
    }else{
        if(operation == "observerproperty" || operation == "unobserveproperty" || operation == "subscribeevent" 
            || operation == "unsubscribeevent" || operation == "readproperty") {
            return "GET";
        }
        else if(operation == "invokeaction") {
            return "POST";
        }
        else if(operation == "writeproperty") {
            return "PUT";
        }
        else {
            return null;
        }
    }
}

/**
 * Get the content type from the form, if it is not present, return application/json as the default content type
 * @param { Object } form 
 * @returns { String } - the content type to be used
 */
function getContentType(form) {
    if(form["contentType"]){
        return form["contentType"];
    }else{
        return "application/json";
    }
}

// Export all http helper functions
module.exports = {
    getSubprotocol,
    getMethod,
    getContentType
}