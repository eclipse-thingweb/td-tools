const { uniqWith, isEqual } = require('lodash');

/**
 * Detect protocol schemes of a TD
 * @param {string} td TD string to detect protocols of
 * return List of available protocol schemes
 */
function detectProtocolSchemes(td) {
    let tdJson;

    try {
        tdJson = JSON.parse(td);
    } catch (err) {
        return [];
    }

    const baseUriProtocol = getHrefData(tdJson.base);
    const thingProtocols = detectProtocolInForms(tdJson.forms);
    const actionsProtocols = detectProtocolInAffordance(tdJson.actions);
    const eventsProtocols = detectProtocolInAffordance(tdJson.events);
    const propertiesProtocols = detectProtocolInAffordance(tdJson.properties);
    const protocolSchemes = [
        ...new Set([
            baseUriProtocol,
            ...thingProtocols,
            ...actionsProtocols,
            ...eventsProtocols,
            ...propertiesProtocols,
        ]),
    ].filter((p) => p !== undefined);


    return uniqWith(protocolSchemes, isEqual);
}

/**
 * Detect protocols in a TD affordance
 * @param {object} affordance That belongs to a TD
 * @returns List of protocol schemes
 */
function detectProtocolInAffordance(affordance) {
    if (!affordance) {
        return [];
    }

    let protocolSchemes = [];

    for (const key in affordance) {
        if (key) {
            protocolSchemes = protocolSchemes.concat(detectProtocolInForms(affordance[key].forms));
        }
    }

    return protocolSchemes;
}

/**
 * Detect protocols in a TD forms or a TD affordance forms
 * @param {object} forms Forms field of a TD or a TD affordance
 * @returns List of protocol schemes
 */
function detectProtocolInForms(forms) {
    if (!forms) {
        return [];
    }

    const protocolSchemes = [];

    forms.forEach((form) => {
        protocolSchemes.push(getHrefData(form.href));
    });

    return protocolSchemes;
}

/**
 * Get href data
 * @param {string} href URI string
 * @returns an object with protocol, hostname and port 
 */
function getHrefData(href) {
    if (!href) {
        return;
    }

    const splitHref = href.split(":");
    const hostAndPort = href.split("/")[2];
    const splitHostAndPort = hostAndPort.split(":");
    const protocol = splitHref[0];
    const hostname = splitHostAndPort[0];
    const port = splitHostAndPort[1] ? Number(splitHostAndPort[1]) : undefined;

    return {
        protocol,
        hostname,
        port,
    };
}

module.exports = {
    detectProtocolSchemes,
};
