# Eclipse Thingweb - TD Utils

[![TD Utils CI Pipeline](https://github.com/eclipse-thingweb/td-tools/actions/workflows/ci-td-utils.yaml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/ci-td-utils.yaml)
[![CodeQL](https://github.com/eclipse-thingweb/td-tools/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/codeql-analysis.yml)
[![ESLint](https://github.com/eclipse-thingweb/td-tools/actions/workflows/eslint.yml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/eslint.yml)
[![Prettier](https://github.com/eclipse-thingweb/td-tools/actions/workflows/prettier.yml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/prettier.yml)

The package provides utility tools for TDs, such as:

-   Detecting protocol schemes in a TD

## Usage

-   Install this package via NPM (`npm install @thingweb/td-utils`) (or clone the repo, change to `node/td-utils` and install the package with `npm install`)
-   Node.js or Browser import:

    -   Node.js: Require the package and use the functions

```javascript
const tdUtils = require("@thingweb/td-utils");
```

-   Browser: Import the `tdUtils` object as a global by adding a script tag to your HTML.

```html
<script src="./node_modules/@thingweb/td-utils/dist/web-bundle.min.js"></script>
```

## License

Licensed under the Eclipse or W3C license, see [License](https://github.com/eclipse-thingweb/td-tools/blob/main/LICENSE.md).
