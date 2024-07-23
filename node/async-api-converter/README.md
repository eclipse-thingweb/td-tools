# Eclipse Thingweb - TD to AsyncAPI Converter

[![AsyncAPI Converter CI Pipeline](https://github.com/eclipse-thingweb/td-tools/actions/workflows/ci-async-api-converter.yaml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/ci-async-api-converter.yaml)
[![CodeQL](https://github.com/eclipse-thingweb/td-tools/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/codeql-analysis.yml)
[![ESLint](https://github.com/eclipse-thingweb/td-tools/actions/workflows/eslint.yml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/eslint.yml)
[![Prettier](https://github.com/eclipse-thingweb/td-tools/actions/workflows/prettier.yml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/prettier.yml)

The package provides support for AsyncAPI instance generation (output as `json` or `yaml`), using a Thing Description (TD) as input.

## Usage

You can use this package to integrate AsyncAPI instance generation from a TD in your application.

-   Install this package via NPM (`npm install @thingweb/async-api-converter`) (or clone the repo, change to `node/async-api-converter` and install the package with `npm install`)
-   Node.js or Browser import:

    -   Node.js: Require the package and use the functions

```javascript
const tdToAsyncAPI = require("@thingweb/async-api-converter");
```

-   Browser: Import the `tdToAsyncAPI` object as a global by adding a script tag to your HTML.

```html
<script src="./node_modules/@thingweb/async-api-converter/dist/web-bundle.min.js"></script>
```

-   Now you can convert a TD to an AsyncAPI instance.

```javascript
tdToAsyncAPI(td).then((AsyncAPI) => {
    console.log(JSON.stringify(AsyncAPI.json, undefined, 2));
    console.log(AsyncAPI.yaml);
});
```

You can find usage examples in the [tests folder](./tests/), or the [web] and [cli] packages.

## License

Licensed under the Eclipse or W3C license, see [License](https://github.com/eclipse-thingweb/td-tools/blob/main/LICENSE.md).

## Limitations

This conversion package should be seen as a first draft.
It is currently limited to the **MQTT** protocol and converting observable properties or subscribable events of a Thing Description instance to channels of an AsyncAPI instance.
Furthermore, it converts some general information about the documents, e.g., an `id` if available.
Due to the structure of both specifications, there occur other limitations, e.g., an AsyncAPI document does not allow specifying servers only for some channels or security restrictions for specific channels/operations/messages.

## Possible Extensions

Resulting of the current Limitations there are possible extensions for the future:

-   Supporting HTTP:  
    Both the TD and the AsyncAPI specification support describing http-based operations but they are doing so in a quite different way, which is the tricky part if one wants to convert from one to another.
    The Thing Description supports HTTP for asynchronous and synchronous messages.
    In AsyncAPI, the HTTP protocol is always mentioned to support "HTTP streaming APIs".
    The specification does not mention certain subprotocols but allows defining HTTP messages (as request/response and with the method) so one way of converting could be to specify necessary messages for every subprotocol.
    Still, this does probably not represent the real implementations properly.

-   Supporting WebSockets:  
    AsyncAPI treats WebSocket connections as independent protocols with given restrictions, e.g., only one WebSocket connection is possible per AsyncAPI instance (because routing channels to certain servers is not possible and WebSocket does not support channels/topics/...).
    This should be taken into account for the conversion, one promising approach for converting protocols other than MQTT-like, could be to generate one AsyncAPI instance per available server to deal with the in this case more expressive TDs.
-   Adding security support:  
    The focus of AsyncAPI is hardly on security (since event-based solutions are often used in closed systems) but still it supports quite some mechanisms.
    The more complicated part in converting this from TD to AsyncAPI is that TDs support different security mechanisms for every operation, while AsyncAPI allows only defining them per Server (and there is no server-to-channel/operation/message mapping).

-   Add further use cases:
    Currently, only two types of TD interactions are mapped to their AsyncAPI equivalents:

    -   Properties with the op `observeproperty` indicating that the property can be watched asynchronously
    -   Events to which a client can subscribe (`subscribeevent`)

        But there could be other use cases that should be taken into account, e.g., reading (possible with retain option) variables via MQTT that might not be an asynchronous operation itself but useful to support since MQTT operations cannot be represented with OpenAPI instances.

-   Think about how to treat interactions with the same path (-> same AsyncAPI channel), e.g., a property and an event that both interact with `thing.example.com/status`

## Comments

A TD doesn't necessarily to be valid to be converted to an AsyncAPI instance.
This converter will only throw an Error if the invalid part has a strong effect on the conversion result, but tries to ignore the most cases.
This is by purpose, since there is the possibility to validate a TD using, e.g., the playground core package and the conversion of experimental TDs for example to create new TD features, should be supported.
