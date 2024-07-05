import httpAndMqtt from "./examples/httpAndMqtt.json";
import noProtocol from "./examples/noProtocol.json";
import onlyHttp from "./examples/onlyHttp.json";
import onlyMqtt from "./examples/onlyMqtt.json";
import secureProtocols from "./examples/secureProtocols.json";

export const testSuite = [
    {
        name: "httpAndMqtt",
        input: httpAndMqtt,
        expected: [
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
        input: noProtocol,
        expected: [],
    },
    {
        name: "onlyHttp",
        input: onlyHttp,
        expected: [
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
        input: onlyMqtt,
        expected: [
            {
                protocol: "mqtt",
                hostname: "mylamp.example.com",
            },
        ],
    },
    {
        name: "secureProtocols",
        input: secureProtocols,
        expected: [
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
