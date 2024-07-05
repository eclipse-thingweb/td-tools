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
import { testSuite } from "./protocol-detection.test.suite";

export type ThingDescriptionTest = ThingDescription & { protocolSchemes: ProtocolScheme[] };

describe("test examples", () => {
    testSuite.forEach((t) => {
        it(`should test ${t.name}`, () => {
            testTD(t.input, t.expected);
        });
    });
});

const testTD = (td: any, expected: ProtocolScheme[]) => {
    const detectedProtocolSchemes = detectProtocolSchemes(JSON.stringify(td));

    expect(detectedProtocolSchemes.length).toBe(expected.length);
    expected.forEach((s: ProtocolScheme) => {
        expect(detectedProtocolSchemes).toContainEqual(s);
    });
};
