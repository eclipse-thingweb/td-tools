import {
    AnyUri,
    Form,
    ThingDescription,
    PropertyElement,
    ActionElement,
    EventElement,
} from "wot-thing-description-types";

export interface ProtocolSchemeMap {
    [k: string]: ProtocolScheme[];
}

export interface ProtocolScheme {
    uri: string;
    subprotocol?: string;
}

export interface HrefInfo {
    protocol: string;
    uri: string;
}

type AffordanceElement = { [k: string]: PropertyElement | ActionElement | EventElement };

/**
 * Detect protocol schemes of a TD
 * @param {string} td TD string to detect protocols of
 * return List of available protocol schemes
 */
export const detectProtocolSchemes = (td: string): ProtocolSchemeMap => {
    let tdJson: ThingDescription;

    const protocolSchemes: ProtocolSchemeMap = {};

    try {
        tdJson = JSON.parse(td);
    } catch (err) {
        console.error("Could not parse the TD string.");
        return protocolSchemes;
    }

    const baseHrefInfo = getHrefInfo(tdJson.base);

    addProtocolScheme(protocolSchemes, baseHrefInfo);
    detectProtocolInForms(protocolSchemes, tdJson.forms);
    detectProtocolInAffordance(protocolSchemes, tdJson.actions);
    detectProtocolInAffordance(protocolSchemes, tdJson.events);
    detectProtocolInAffordance(protocolSchemes, tdJson.properties);

    return protocolSchemes;
};

/**
 * Detect protocols in a TD affordance
 * @param protocolSchemes Protocol scheme map that the protocol scheme will be added
 * @param {object} affordance That belongs to a TD
 * @returns List of protocol schemes
 */
const detectProtocolInAffordance = (protocolSchemes: ProtocolSchemeMap, affordance?: AffordanceElement) => {
    if (!affordance) {
        return;
    }

    for (const key in affordance) {
        if (key) {
            detectProtocolInForms(protocolSchemes, affordance[key].forms);
        }
    }
};

/**
 * Detect protocols in a TD forms or a TD affordance forms
 * @param protocolSchemes Protocol scheme map that the protocol scheme will be added
 * @param {object} forms Forms field of a TD or a TD affordance
 * @returns List of protocol schemes
 */
const detectProtocolInForms = (protocolSchemes: ProtocolSchemeMap, forms?: Form[]) => {
    if (!forms) {
        return;
    }

    forms.forEach((form) => {
        const hrefInfo = getHrefInfo(form.href);

        addProtocolScheme(protocolSchemes, hrefInfo, form.subprotocol);
    });
};

/**
 * Get href data
 * @param {string} href URI string
 * @returns an object with protocol, hostname and port
 */
const getHrefInfo = (href?: AnyUri): HrefInfo | undefined => {
    if (!href) {
        return;
    }

    const splitHref = href.split(":");
    const uri = href.split("/")[2];
    const protocol = splitHref[0];

    return {
        protocol,
        uri: protocol + "://" + uri,
    };
};

/**
 *
 * @param protocolSchemes Protocol scheme map that the protocol scheme will be added
 * @param hrefInfo Protocol scheme's information that is extracted from the href
 * @param subprotocol Subprotocol of the protocol scheme
 */
const addProtocolScheme = (protocolSchemes: ProtocolSchemeMap, hrefInfo?: HrefInfo, subprotocol?: string) => {
    if (hrefInfo) {
        const protocolScheme = {
            uri: hrefInfo.uri,
            subprotocol: subprotocol,
        };

        if (protocolSchemes[hrefInfo.protocol]) {
            const schemeExists =
                protocolSchemes[hrefInfo.protocol].filter(
                    (s) => s.uri === protocolScheme.uri && s.subprotocol === protocolScheme.subprotocol
                ).length > 0;

            if (!schemeExists) protocolSchemes[hrefInfo.protocol].push(protocolScheme);
        } else {
            protocolSchemes[hrefInfo.protocol] = [protocolScheme];
        }
    }
};
