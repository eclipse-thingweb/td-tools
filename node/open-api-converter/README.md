# Eclipse Thingweb - TD to OpenAPI Converter

The package supports OpenAPI instance generation (output as `json` or `yaml`), using a Thing Description (TD) as input.

## Usage

This package can integrate OpenAPI instance generation from a TD in your application.

-   Install this package via NPM (`npm install @thingweb/open-api-converter`) (or clone the repo, change to `node/open-api-converter`, and install the package with `npm install`)

-   Node.js or Browser import:

    -   Node.js: Require the package and use the functions

```javascript
const tdToOpenAPI = require("@thingweb/open-api-converter");
```

-   Browser: Import the `tdToOpenAPI` object as a global by adding a script tag to your HTML.

```html
<script src="./node_modules/@thingweb/open-api-converter/dist/web-bundle.min.js"></script>
```

-   Now, you can convert a TD to an OpenAPI instance.

```javascript
tdToOpenAPI(td).then((OpenAPI) => {
    console.log(JSON.stringify(OpenAPI.json, undefined, 2));
    console.log(OpenAPI.yaml);
});
```

You can find usage examples in the [tests folder](./tests/),

## License

Licensed under the Eclipse or W3C license, see [License](https://github.com/eclipse-thingweb/td-tools/blob/main/LICENSE.md).
