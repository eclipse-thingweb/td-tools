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

import {
    AnyUri,
    Form,
    ThingDescription,
    PropertyElement,
    ActionElement,
    EventElement,
} from "wot-thing-description-types";

const topLevelFormKey = "form";
const topLevelFormDefinitions = "formDefinitions";
const topLevelConnectionKey = "connection";
const topLevelConnectionDefinitions = "connectionDefinitions";
const topLevelSecurityKey = "security";
const topLevelSecurityDefinitions = "securityDefinitions";

export function expandTD(inputTD: ThingDescription): ThingDescription | undefined {
    let defaultForm: any = {};
    let defaultConnection: any = {};
    // finding default connection(s) based on the top level "connection" and "connectionDefinitions" keys
    if (topLevelConnectionKey in inputTD) {
        const topLevelConnection = (inputTD as any)[topLevelConnectionKey];

        if (Array.isArray(topLevelConnection)) {
            if (topLevelConnection.length > 1) {
                // TODO: multiple connection: choose how to handle; for now, keep first as default
            } else if (topLevelConnection.length === 1) {
                defaultConnection = (inputTD as any)[topLevelConnectionDefinitions]?.[topLevelConnection[0]];
                delete inputTD.connection;
            } else if (topLevelConnection.length === 0) {
                throw new Error("Empty connection array is not allowed");
            } else {
                // should not be possible. throw error
                throw new Error("Badly formatted connection array");
            }
        } else if (typeof topLevelConnection === "object" && topLevelConnection !== null) {
            // Check if object is empty
            if (Object.keys(topLevelConnection).length === 0) {
                throw new Error("Empty connection object is not allowed");
            }
            defaultConnection = topLevelConnection;
            delete inputTD.connection;
        } else {
            // only object or array is allowed. return error
            throw new Error("Only object or array is allowed for the connection key in the top level");
        }
    }
    // finding default form(s) based on the top level "form" and "formDefinitions" keys
    if (topLevelFormKey in inputTD) {
        const topLevelForm = (inputTD as any)[topLevelFormKey];
        if (Array.isArray(topLevelForm)) {
            if (topLevelForm.length > 1) {
                // TODO: multiple forms: choose how to handle; for now, keep first as default
            } else if (topLevelForm.length === 1) {
                defaultForm = (inputTD as any)[topLevelFormDefinitions]?.[topLevelForm[0]];
                delete inputTD.form;
            } else if (topLevelForm.length === 0) {
                throw new Error("Empty form array is not allowed");
            } else {
                // should not be possible. throw error
                throw new Error("Badly formatted form array");
            }
        } else if (typeof topLevelForm === "object" && topLevelForm !== null) {
            // Check if object is empty
            if (Object.keys(topLevelForm).length === 0) {
                throw new Error("Empty form object is not allowed");
            }
            defaultForm = topLevelForm;
            delete inputTD.form;
        } else {
            // only object or array is allowed. return error
            throw new Error("Only non-empty object or array is allowed for the form key in the top level");
        }
        // adding default connection to default form if there is only one of each
    } else {
        // no top level form to expand. There can be connection etc. in the top level. For now, we return input
        // TODO: handle this properly
        return inputTD;
    }

    // if defaultForm and defaultConnection are both present, merge them. defaultForm takes precedence
    if (Object.keys(defaultForm).length > 0 && Object.keys(defaultConnection).length > 0) {
        defaultForm = { ...defaultConnection, ...defaultForm };
    } else if (Object.keys(defaultConnection).length > 0) {
        defaultForm = defaultConnection;
    }

    // Helper function to expand forms for an interaction affordance
    function expandForms(element: PropertyElement | ActionElement | EventElement, defaultForm: any) {
        for (const formElement of element.forms) {
            // if base is present in defaultForm and the href in the formElement is relative, expand it
            if ("base" in defaultForm) {
                formElement.href = new URL(formElement.href as string, defaultForm.base as string).toString();
            }
            // go through each key in defaultForm and add to formElement if not present
            for (const key in defaultForm) {
                if (key !== "base" && !(key in formElement)) {
                    (formElement as any)[key] = (defaultForm as any)[key];
                }
            }
        }
    }

    // Expand forms for properties
    if ("properties" in inputTD) {
        const properties = inputTD.properties;
        for (const propertyKey in properties) {
            expandForms(properties[propertyKey] as PropertyElement, defaultForm);
        }
    }

    // Expand forms for actions
    if ("actions" in inputTD) {
        const actions = inputTD.actions;
        for (const actionKey in actions) {
            expandForms(actions[actionKey] as ActionElement, defaultForm);
        }
    }

    // Expand forms for events
    if ("events" in inputTD) {
        const events = inputTD.events;
        for (const eventKey in events) {
            expandForms(events[eventKey] as EventElement, defaultForm);
        }
    }
    return inputTD;
}
