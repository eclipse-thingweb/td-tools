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

import cborcoap from "./expansionExamples/cborcoap.json";

export const testSuite = [
    {
        name: "cborcoap",
        input: cborcoap,
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
              "scheme": "nosec"
            }
          }
        ]
      },
      "prop2": {
        "type": "string",
        "forms": [
          {
            "href": "coap://[2001:db8::1]/mything/props/prop2",
            "contentType": "application/cbor",
            "security": {
              "scheme": "nosec"
            }
          }
        ]
      }
    }
  }
},
];
