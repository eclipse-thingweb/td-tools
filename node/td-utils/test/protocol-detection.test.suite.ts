import httpAndMqtt from "./examples/httpAndMqtt.json";
import noProtocol from "./examples/noProtocol.json";
import onlyHttp from "./examples/onlyHttp.json";
import onlyMqtt from "./examples/onlyMqtt.json";
import secureProtocols from "./examples/secureProtocols.json";

export const testSuite = [
    {
        name: "httpAndMqtt",
        input: httpAndMqtt,
        expected: {
            http: [{ uri: "http://mylamp.example.com:1234" }],
            mqtt: [{ uri: "mqtt://mylamp.example.com:1234" }],
        },
    },
    {
        name: "noProtocol",
        input: noProtocol,
        expected: {},
    },
    {
        name: "onlyHttp",
        input: onlyHttp,
        expected: {
            http: [
                { uri: "http://mylamp.example.com:4212" },
                { uri: "http://mylamp.example.com:4214", subprotocol: "longpoll" },
            ],
        },
    },
    {
        name: "onlyMqtt",
        input: onlyMqtt,
        expected: {
            mqtt: [{ uri: "mqtt://mylamp.example.com" }, { uri: "mqtt://mylamp.example.com", subprotocol: "sparkplug" }],
        },
    },
    {
        name: "secureProtocols",
        input: secureProtocols,
        expected: {
            https: [{ uri: "https://mylamp.example.com", subprotocol: "longpoll" }],
            mqtts: [{ uri: "mqtts://mylamp.example.com" }],
        },
    },
];
