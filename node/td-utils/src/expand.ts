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
    // in case of single form or connectin
    let defaultForm: any = {};
    let defaultConnection: any = {};

    // in case of multiple form or connections
    let defaultFormArray: any = [];
    let defaultConnectionArray: any = [];

    // finding default connection(s) based on the top level "connection" and "connectionDefinitions" keys
    if (topLevelConnectionKey in inputTD) {
        const topLevelConnection = (inputTD as any)[topLevelConnectionKey];

        if (Array.isArray(topLevelConnection)) {
            if (topLevelConnection.length > 1) {
                defaultConnectionArray = topLevelConnection.map((connKey: string) => {
                    return (inputTD as any)[topLevelConnectionDefinitions]?.[connKey];
                });

                delete inputTD.connection;
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
    } else {
        // no top level connection to expand. There can be form etc. in the top level.
    }

    // finding default form(s) based on the top level "form" and "formDefinitions" keys
    if (topLevelFormKey in inputTD) {
        const topLevelForm = (inputTD as any)[topLevelFormKey];
        if (Array.isArray(topLevelForm)) {
            if (topLevelForm.length > 1) {
                defaultFormArray = topLevelForm.map((formKey: string) => {
                    return (inputTD as any)[topLevelFormDefinitions]?.[formKey];
                });

                delete inputTD.form;
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
    } else {
        // no top level form to expand. There can be connection etc. in the top level.
    }

    // if defaultForm and defaultConnection are filled with items, merge them. defaultForm takes precedence
    if (Object.keys(defaultForm).length > 0 && Object.keys(defaultConnection).length > 0) {
        defaultForm = { ...defaultConnection, ...defaultForm };
    } else if (Object.keys(defaultConnection).length > 0) {
        defaultForm = defaultConnection;
    }
    defaultFormArray[0] = defaultForm;

    // // like above but for the array case. However, each array needs to be merged like a matrix multiplication. form array of length 2 and connection array of length 3 results in 6 forms
    if (defaultFormArray.length > 0 && defaultConnectionArray.length > 0) {
        const mergedFormArray: any[] = [];
        for (const formItem of defaultFormArray) {
            for (const connItem of defaultConnectionArray) {
                mergedFormArray.push({ ...connItem, ...formItem });
            }
        }
        defaultFormArray = mergedFormArray;
        delete inputTD[topLevelConnectionDefinitions];
        delete inputTD[topLevelFormDefinitions];
    }

    // Helper function to expand forms for an interaction affordance
    function expandForms(element: PropertyElement | ActionElement | EventElement, defaultFormArray: any) {
        // if single default form and multiple affordance forms, it is fine
        // if multiple default forms and single affordance form, it is fine. Need to expand that form array with each default form as potentials
        // if multiple default forms and multiple affordance forms, throw error

        // helper to merge a form with a default object (handles base/href expansion and missing keys)
        const mergeFormWithDefaults = (original: Form, def: any): Form => {
            const newForm: Form = { ...original };
            if ("base" in def && newForm.href) {
                try {
                    newForm.href = new URL(newForm.href as string, def.base as string).toString();
                } catch {
                    // ignore URL errors and leave href as-is
                }
            }
            for (const key in def) {
                if (key === "base") continue;
                if (!(key in newForm)) {
                    (newForm as any)[key] = def[key];
                }
            }
            return newForm;
        };

        if (defaultFormArray.length > 1 && element.forms.length > 1) {
            throw new Error("Multiple default forms and multiple affordance forms are not allowed together");
        } else if (defaultFormArray.length > 1 && element.forms.length === 1) {
            // expand the single form with each default form
            const originalForm = element.forms[0];
            element.forms = defaultFormArray.map((defForm: any) => mergeFormWithDefaults(originalForm, defForm));
            return;
        } else if (defaultFormArray.length === 1 && element.forms.length >= 1) {
            // case for single default form
            const def = defaultFormArray[0];
            element.forms = element.forms.map((formElement: Form) => mergeFormWithDefaults(formElement, def)) as [
                Form,
                ...Form[],
            ];
            return;
        }
    }

    if (defaultFormArray.length > 0) {
        // case for single default form
        if ("properties" in inputTD) {
            const properties = inputTD.properties;
            for (const propertyKey in properties) {
                expandForms(properties[propertyKey] as PropertyElement, defaultFormArray);
            }
        }

        if ("actions" in inputTD) {
            const actions = inputTD.actions;
            for (const actionKey in actions) {
                expandForms(actions[actionKey] as ActionElement, defaultFormArray);
            }
        }

        if ("events" in inputTD) {
            const events = inputTD.events;
            for (const eventKey in events) {
                expandForms(events[eventKey] as EventElement, defaultFormArray);
            }
        }
        return inputTD;
        // case for multiple default forms, i.e. multi ip address, multi protocol, multi content type
        // [
        // { base: 'http://192.168.1.10:8080/mything' },
        // { base: 'coap://[2001:DB8::1]/mything' }
        // ]
    } else {
        // no defaults at the top level. Investigate individual forms
    }
}
