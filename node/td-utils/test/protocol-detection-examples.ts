import { ThingDescription } from "wot-thing-description-types";
import { ProtocolScheme } from "../src/detectProtocolSchemes";

type TestVariables = {
    name: string;
    protocolSchemes: ProtocolScheme[];
};

export type ThingDescriptionTest = ThingDescription & TestVariables;

export const examples: ThingDescriptionTest[] = [
    {
        name: "httpAndMqtt",
        id: "urn:simple",
        "@context": "https://www.w3.org/2022/wot/td/v1.1",
        title: "MyLampThing",
        description: "Valid TD copied from the spec's first example",
        securityDefinitions: {
            basic_sc: { scheme: "basic", in: "header" },
        },
        security: ["basic_sc"],
        properties: {
            status: {
                type: "string",
                forms: [{ href: "http://mylamp.example.com:1234/status" }],
            },
        },
        actions: {
            toggle: {
                forms: [{ href: "mqtt://mylamp.example.com:1234/toggle" }],
            },
        },
        protocolSchemes: [
            {
                protocol: "http",
                hostname: "mylamp.example.com",
                port: 1234,
            },
            {
                protocol: "mqtt",
                hostname: "mylamp.example.com",
                port: 1234,
            },
        ],
    },
    {
        name: "noProtocol",
        id: "urn:simple",
        "@context": "https://www.w3.org/2022/wot/td/v1.1",
        title: "MyLampThing",
        description: "Valid TD copied from the spec's first example",
        securityDefinitions: {
            basic_sc: { scheme: "basic", in: "header" },
        },
        security: ["basic_sc"],
        properties: {},
        actions: {},
        events: {},
        protocolSchemes: [],
    },
    {
        name: "onlyHttp",
        id: "urn:simple",
        "@context": "https://www.w3.org/2022/wot/td/v1.1",
        title: "MyLampThing",
        description: "Valid TD copied from the spec's first example",
        securityDefinitions: {
            basic_sc: { scheme: "basic", in: "header" },
        },
        security: ["basic_sc"],
        properties: {
            status: {
                type: "string",
                forms: [{ href: "http://mylamp.example.com:4212/status" }],
            },
        },
        actions: {
            toggle: {
                forms: [{ href: "http://mylamp.example.com:4212/toggle" }],
            },
        },
        events: {
            overheating: {
                data: { type: "string" },
                forms: [
                    {
                        href: "http://mylamp.example.com:4214/oh",
                        subprotocol: "longpoll",
                    },
                ],
            },
        },
        protocolSchemes: [
            {
                protocol: "http",
                hostname: "mylamp.example.com",
                port: 4212,
            },
            {
                protocol: "http",
                hostname: "mylamp.example.com",
                port: 4214,
            },
        ],
    },
    {
        name: "onlyMqtt",
        id: "urn:simple",
        "@context": "https://www.w3.org/2022/wot/td/v1.1",
        title: "MyLampThing",
        description: "Valid TD copied from the spec's first example",
        securityDefinitions: {
            basic_sc: { scheme: "basic", in: "header" },
        },
        security: ["basic_sc"],
        properties: {
            status: {
                type: "string",
                forms: [{ href: "mqtt://mylamp.example.com/status" }],
            },
        },
        actions: {
            toggle: {
                forms: [{ href: "mqtt://mylamp.example.com/toggle" }],
            },
        },
        events: {
            overheating: {
                data: { type: "string" },
                forms: [
                    {
                        href: "mqtt://mylamp.example.com/oh",
                        subprotocol: "longpoll",
                    },
                ],
            },
        },
        protocolSchemes: [
            {
                protocol: "mqtt",
                hostname: "mylamp.example.com",
            },
        ],
    },
    {
        name: "secureProtocols",
        id: "urn:simple",
        "@context": "https://www.w3.org/2022/wot/td/v1.1",
        title: "MyLampThing",
        description: "Valid TD copied from the spec's first example",
        securityDefinitions: {
            basic_sc: { scheme: "basic", in: "header" },
        },
        security: ["basic_sc"],
        base: "mqtts://mylamp.example.com/status",
        events: {
            overheating: {
                data: { type: "string" },
                forms: [
                    {
                        href: "https://mylamp.example.com/oh",
                        subprotocol: "longpoll",
                    },
                ],
            },
        },
        protocolSchemes: [
            {
                protocol: "https",
                hostname: "mylamp.example.com",
            },
            {
                protocol: "mqtts",
                hostname: "mylamp.example.com",
            },
        ],
    },
];
