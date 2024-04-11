# Eclipse Thingweb - AAS AID tooling for WoT Thing Descriptions

The package provides tooling for Asset Adminstration Shell (AAS) w.r.t. Asset Interfaces Description (AID).

The [IDTA Asset Interfaces Description (AID) working group](https://github.com/admin-shell-io/submodel-templates/tree/main/development/Asset%20Interface%20Description/1/0) defines a submodel template specification for the Asset Adminstration Shell that can be used to describe the asset's service interface or asset's related service interfaces. The current AID working assumptions reuse existing definitions from [WoT Thing Descriptions](https://www.w3.org/TR/wot-thing-description11/). Hence it is possible to consume AAS with AID definitions with [node-wot](https://github.com/eclipse-thingweb/node-wot) (e.g., read/subscribe live data of the asset and/or associated service).

## Sample Applications

### Prerequisites

-   `npm install @thingweb/aas-aid`
-   `npm install @node-wot/binding-http` (needed for consuming the generated TD with node-wot only)

### AAS/AID to WoT TD

The file `counterHTTP.json` describes the counter sample in AAS/AID format for http binding. The `AssetInterfacesDescription` utility class allows to transform the AID format to a valid WoT TD format which in the end can be properly consumed by node-wot.

The example `aid-to-td.js` transforms an AID submodel (from an AAS file) into a regular WoT TD.
Note: Besides converting the AID submodel it is also possible to convert a full AAS file.

```js
// aid-to-td.js
const fs = require("fs/promises"); // to read JSON file in AID format

Servient = require("@node-wot/core").Servient;
HttpClientFactory = require("@node-wot/binding-http").HttpClientFactory;

// AID Util
AssetInterfacesDescription = require("@thingweb/aas-aid").AssetInterfacesDescription;

// create Servient and add HTTP binding
let servient = new Servient();
servient.addClientFactory(new HttpClientFactory(null));

let assetInterfacesDescription = new AssetInterfacesDescription();

async function example() {
    try {
        const aas = await fs.readFile("counterHTTP.json", {
            encoding: "utf8",
        });
        // pick AID submodel
        const aid = JSON.stringify(JSON.parse(aas).submodels[0]);

        // transform AID to WoT TD
        const tdAID = assetInterfacesDescription.transformAID2TD(aid, `{"title": "counter"}`);
        // Note: transformSM2TD() may have up to 3 input parameters
        // * aid (required):           AID submodel in JSON format
        // * template (optional):      Initial TD template
        // * submodelRegex (optional): Submodel filter based on regular expression
        //                             e.g., filtering HTTP only by calling transformAAS2TD(aas, `{}`, "HTTP")

        // do work as usual
        const WoT = await servient.start();
        const thing = await WoT.consume(JSON.parse(tdAID));

        // read property count
        const read1 = await thing.readProperty("count");
        console.log("count value is: ", await read1.value());
    } catch (err) {
        console.log(err);
    }
}

// launch example
example();
```

#### Run AID to TD transformation sample

`node aid-to-td.js`
... will show the counter value retrieved from http://plugfest.thingweb.io:8083/counter/properties/count

Note: make sure that the file `counterHTTP.json` is in the same folder as the script.

### WoT TD to AAS/AID

The example `td-to-aid.js` loads the online [counter TD](http://plugfest.thingweb.io:8083/counter/) and converts it to an AID submodel in JSON format.

Note: by using the option `createAAS` a full AAS form is created (instead of the AID submodel only).

```js
// td-to-aid.js
AssetInterfacesDescription = require("@thingweb/aas-aid").AssetInterfacesDescription;

let assetInterfacesDescription = new AssetInterfacesDescription();

async function example() {
    try {
        const response = await fetch("http://plugfest.thingweb.io:8083/counter");
        const counterTD = await response.json();

        const sm = assetInterfacesDescription.transformTD2AID(JSON.stringify(counterTD), { createAAS: true }, [
            "http",
            "coap",
        ]);

        // print JSON format of AID submodel
        console.log(sm);
    } catch (err) {
        console.log(err);
    }
}

// launch example
example();
```

#### Run TD to AAS/AID transformation sample

`node td-to-aid.js`
... will show the online counter in AAS/AID JSON format (compliant with AAS V3.0 and can be imported by AASX Package Explorer).

## License

Licensed under the Eclipse or W3C license, see [License](https://github.com/eclipse-thingweb/td-tools/blob/main/LICENSE.md).
