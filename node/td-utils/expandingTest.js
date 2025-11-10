const mod = require("./build/src/expand.js");
const expandTD = mod.expandTD || mod.default || mod;

const exampleTD =   {
    "@context": "https://www.w3.org/ns/wot-next/td",
    "title": "recommended-test-cbor-default",
    "form": {
      "contentType": "application/cbor",
      "base": "coap://[2001:db8::1]/mything/",
      "security": {
        "scheme": "nosec"
      }
    },
    "properties": {
      "prop1": {
        "type": "string",
        "forms": [
          {
            "href": "props/prop1"
          }
        ]
      },
      "prop2": {
        "type": "string",
        "forms": [
          {
            "href": "props/prop2"
          }
        ]
      }
    }
  };

/*
const exampleTDExpanded =   {
    "@context": "https://www.w3.org/ns/wot-next/td",
    "title": "recommended-test-cbor-default",
    "properties": {
      "prop1": {
        "type": "string",
        "forms": [
          {
            "href": "coap://[2001:DB8::1]/mything/props/prop1",
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
            "href": "coap://[2001:DB8::1]/mything/props/prop2",
            "contentType": "application/cbor",
            "security": {
              "scheme": "nosec"
            }
          }
        ]
      }
    }
  };

  */

const outputTD = expandTD(exampleTD);
console.log(JSON.stringify(outputTD, null, 2));