import { uniqWith, isEqual } from "lodash";
import {
    AnyUri,
    Form,
    ThingDescription,
    PropertyElement,
    ActionElement,
    EventElement,
} from "wot-thing-description-types";

export interface ProtocolScheme {
    protocol: string;
    hostname: string;
    port?: number;
}

type AffordanceElement = { [k: string]: PropertyElement | ActionElement | EventElement };

/**
 * Detect protocol schemes of a TD
 * @param {string} td TD string to detect protocols of
 * return List of available protocol schemes
 */
export const detectProtocolSchemes = (td: string): ProtocolScheme[] => {
    let tdJson: ThingDescription;

    try {
        tdJson = JSON.parse(td);
    } catch (err) {
        console.error("Could not parse the TD string.");
        return [];
    }

    const baseUriProtocol: ProtocolScheme | undefined = tdJson.base ? getHrefData(tdJson.base) : undefined;
    const thingProtocols: ProtocolScheme[] = tdJson.forms ? detectProtocolInForms(tdJson.forms) : [];
    const actionsProtocols: ProtocolScheme[] = tdJson.actions ? detectProtocolInAffordance(tdJson.actions) : [];
    const eventsProtocols: ProtocolScheme[] = tdJson.events ? detectProtocolInAffordance(tdJson.events) : [];
    const propertiesProtocols: ProtocolScheme[] = tdJson.properties
        ? detectProtocolInAffordance(tdJson.properties)
        : [];
    const protocolSchemes: ProtocolScheme[] = [
        ...thingProtocols,
        ...actionsProtocols,
        ...eventsProtocols,
        ...propertiesProtocols,
    ];

    if (baseUriProtocol) protocolSchemes.push(baseUriProtocol);

    return uniqWith(protocolSchemes, isEqual);
};

/**
 * Detect protocols in a TD affordance
 * @param {object} affordance That belongs to a TD
 * @returns List of protocol schemes
 */
const detectProtocolInAffordance = (affordance: AffordanceElement): ProtocolScheme[] => {
    if (!affordance) {
        return [];
    }

    let protocolSchemes: ProtocolScheme[] = [];

    for (const key in affordance) {
        if (key) {
            protocolSchemes = protocolSchemes.concat(detectProtocolInForms(affordance[key].forms));
        }
    }

    return protocolSchemes;
};

/**
 * Detect protocols in a TD forms or a TD affordance forms
 * @param {object} forms Forms field of a TD or a TD affordance
 * @returns List of protocol schemes
 */
const detectProtocolInForms = (forms: Form[]): ProtocolScheme[] => {
    if (!forms) {
        return [];
    }

    const protocolSchemes: ProtocolScheme[] = [];

    forms.forEach((form) => {
        const hrefData = getHrefData(form.href);

        if (hrefData) protocolSchemes.push(hrefData);
    });

    return protocolSchemes;
};

/**
 * Get href data
 * @param {string} href URI string
 * @returns an object with protocol, hostname and port
 */
const getHrefData = (href: AnyUri): ProtocolScheme | undefined => {
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
};
