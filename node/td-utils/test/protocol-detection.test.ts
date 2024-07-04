/*
 *  Copyright (c) 2022 Contributors to the Eclipse Foundation
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
import { detectProtocolSchemes, ProtocolScheme } from "../src/detectProtocolSchemes";
import { ThingDescription } from "wot-thing-description-types";
import httpAndMqtt from "./examples/httpAndMqtt.json";
import noProtocol from "./examples/noProtocol.json";
import onlyHttp from "./examples/onlyHttp.json";
import onlyMqtt from "./examples/onlyMqtt.json";
import secureProtocols from "./examples/secureProtocols.json";

export type ThingDescriptionTest = ThingDescription & { protocolSchemes: ProtocolScheme[] };

describe("test examples", () => {
    it("should test httpAndMqtt", () => {
        testTD(httpAndMqtt);
    });

    it("should test noProtocol", () => {
        testTD(noProtocol);
    });

    it("should test onlyHttp", () => {
        testTD(onlyHttp);
    });

    it("should test onlyMqtt", () => {
        testTD(onlyMqtt);
    });

    it("should test secureProtocols", () => {
        testTD(secureProtocols);
    });
});

const testTD = (td: any) => {
    const detectedProtocolSchemes = detectProtocolSchemes(JSON.stringify(td));

    expect(detectedProtocolSchemes.length).toBe(td.protocolSchemes.length);
    td.protocolSchemes.forEach((s: ProtocolScheme) => {
        expect(detectedProtocolSchemes).toContainEqual(s);
    });
};
