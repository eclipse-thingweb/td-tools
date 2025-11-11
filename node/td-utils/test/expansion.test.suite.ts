/*
 *  Copyright (c) 2025 Contributors to the Eclipse Foundation
 *
 *  See the NOTICE file(s) distributed with this work for additional
 *  information regarding copyright ownership.
 *
 *  This program and the accompanying materials are made available under the
 *  terms of the Eclipse Public License v. 2.0 which is available at
 *  http://www.eclipse.org/legal/epl-2.0, or the W3C Software Notice and
 *  Document License (2015-05-13) which is available at
 *  https://www.w3.org/Consortium/Legal/2015/copyright-software-and-document.
 *
 *  SPDX-License-Identifier: EPL-2.0 OR W3C-20150513
 */

export const positiveTestSuite = [
    {
        name: "cborcoap",
        input: {
            "@context": "https://www.w3.org/ns/wot-next/td",
            "title": "recommended-test-cbor-default",
            "form": {
                "contentType": "application/cbor",
                "base": "coap://[2001:DB8::1]/mything/",
                "security": {
                    "scheme": "nosec",
                },
            },
            "properties": {
                "prop1": {
                    "type": "string",
                    "forms": [
                        {
                            "href": "props/prop1",
                        },
                    ],
                },
                "prop2": {
                    "type": "string",
                    "forms": [
                        {
                            "href": "props/prop2",
                        },
                    ],
                },
            },
            "actions": {
                "act1": {
                    "input": { "type": "string" },
                    "forms": [
                        {
                            "href": "actions/act1",
                        },
                    ],
                },
            },
            "events": {
                "evt1": {
                    "data": { "type": "string" },
                    "forms": [
                        {
                            "href": "events/evt1",
                        },
                    ],
                },
            },
        },
        expected: {
            "@context": "https://www.w3.org/ns/wot-next/td",
            "title": "recommended-test-cbor-default",
            "properties": {
                "prop1": {
                    "type": "string",
                    "forms": [
                        {
                            "href": "coap://[2001:db8::1]/mything/props/prop1",
                            "contentType": "application/cbor",
                            "security": {
                                "scheme": "nosec",
                            },
                        },
                    ],
                },
                "prop2": {
                    "type": "string",
                    "forms": [
                        {
                            "href": "coap://[2001:db8::1]/mything/props/prop2",
                            "contentType": "application/cbor",
                            "security": {
                                "scheme": "nosec",
                            },
                        },
                    ],
                },
            },
            "actions": {
                "act1": {
                    "input": { "type": "string" },
                    "forms": [
                        {
                            "href": "coap://[2001:db8::1]/mything/actions/act1",
                            "contentType": "application/cbor",
                            "security": {
                                "scheme": "nosec",
                            },
                        },
                    ],
                },
            },
            "events": {
                "evt1": {
                    "data": { "type": "string" },
                    "forms": [
                        {
                            "href": "coap://[2001:db8::1]/mything/events/evt1",
                            "contentType": "application/cbor",
                            "security": {
                                "scheme": "nosec",
                            },
                        },
                    ],
                },
            },
        },
    },
    {
        name: "cborcoap-alternate-input",
        input: {
            "@context": "https://www.w3.org/ns/wot-next/td",
            "title": "recommended-test-cbor-default",
            "formDefinitions": {
                "f1": {
                    "contentType": "application/cbor",
                    "base": "coap://[2001:DB8::1]/mything/",
                    "security": {
                        "scheme": "nosec",
                    },
                },
            },
            "form": ["f1"],
            "properties": {
                "prop1": {
                    "type": "string",
                    "forms": [
                        {
                            "href": "props/prop1",
                        },
                    ],
                },
            },
        },
        expected: {
            "@context": "https://www.w3.org/ns/wot-next/td",
            "title": "recommended-test-cbor-default",
            "properties": {
                "prop1": {
                    "type": "string",
                    "forms": [
                        {
                            "href": "coap://[2001:db8::1]/mything/props/prop1",
                            "contentType": "application/cbor",
                            "security": {
                                "scheme": "nosec",
                            },
                        },
                    ],
                },
            },
        },
    },
    {
        name: "modbus-separate-form-connection",
        input: {
            "@context": "https://www.w3.org/ns/wot-next/td",
            "title": "recommended-test-modbus-params",
            "connection": {
                "base": "modbus+tcp://192.168.178.32:502/1/",
                "modv:timeout": 1000,
                "security": {
                    "scheme": "nosec",
                },
            },
            "form": {
                "modv:pollingInterval": 5000,
                "modv:zeroBasedAddressing": true,
                "modv:mostSignificantByte": true,
                "modv:mostSignificantWord": true,
                "contentType": "application/octet-stream",
            },
            "properties": {
                "prop1": {
                    "type": "boolean",
                    "forms": [
                        {
                            "href": "1",
                            "modv:entity": "Coil",
                        },
                    ],
                },
                "prop2": {
                    "type": "string",
                    "forms": [
                        {
                            "href": "2?quantity=8",
                            "modv:entity": "HoldingRegister",
                        },
                    ],
                },
            },
        },
        expected: {
            "@context": "https://www.w3.org/ns/wot-next/td",
            "title": "recommended-test-modbus-params",
            "properties": {
                "prop1": {
                    "type": "boolean",
                    "forms": [
                        {
                            "href": "modbus+tcp://192.168.178.32:502/1/1",
                            "modv:entity": "Coil",
                            "modv:timeout": 1000,
                            "security": {
                                "scheme": "nosec",
                            },
                            "modv:pollingInterval": 5000,
                            "modv:zeroBasedAddressing": true,
                            "modv:mostSignificantByte": true,
                            "modv:mostSignificantWord": true,
                            "contentType": "application/octet-stream",
                        },
                    ],
                },
                "prop2": {
                    "type": "string",
                    "forms": [
                        {
                            "href": "modbus+tcp://192.168.178.32:502/1/2?quantity=8",
                            "modv:entity": "HoldingRegister",
                            "modv:timeout": 1000,
                            "security": {
                                "scheme": "nosec",
                            },
                            "modv:pollingInterval": 5000,
                            "modv:zeroBasedAddressing": true,
                            "modv:mostSignificantByte": true,
                            "modv:mostSignificantWord": true,
                            "contentType": "application/octet-stream",
                        },
                    ],
                },
            },
        },
    },
];

export const negativeTestSuite = [
    {
        name: "empty-connection-object",
        input: {
            "@context": "https://www.w3.org/ns/wot-next/td",
            "title": "recommended-test-modbus-params",
            "connection": {},
            "properties": {
                "prop1": {
                    "type": "boolean",
                    "forms": [
                        {
                            "href": "1",
                            "modv:entity": "Coil",
                        },
                    ],
                },
            },
        },
        expected: "Only non-empty object or array is allowed for the form key in the top level",
    },
    {
        name: "empty-connection-object",
        input: {
            "@context": "https://www.w3.org/ns/wot-next/td",
            "title": "recommended-test-modbus-params",
            "form": {},
            "properties": {
                "prop1": {
                    "type": "boolean",
                    "forms": [
                        {
                            "href": "1",
                            "modv:entity": "Coil",
                        },
                    ],
                },
            },
        },
        expected: "Only non-empty object or array is allowed for the form key in the top level",
    },
];
