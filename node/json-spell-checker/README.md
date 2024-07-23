# Eclipse Thingweb - JSON Spell Checker

[![JSON Spell Checker CI Pipeline](https://github.com/eclipse-thingweb/td-tools/actions/workflows/ci-json-spell-checker.yaml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/ci-json-spell-checker.yaml)
[![CodeQL](https://github.com/eclipse-thingweb/td-tools/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/codeql-analysis.yml)
[![ESLint](https://github.com/eclipse-thingweb/td-tools/actions/workflows/eslint.yml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/eslint.yml)
[![Prettier](https://github.com/eclipse-thingweb/td-tools/actions/workflows/prettier.yml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/prettier.yml)

This package provides spell-checking support for JSON files when a JSON Schema is given.

Limitations:

-   There is limited nested spell-checking. Some of the $ref definitions can be nested infinitely. Therefore, spell-checking stops when recursive nesting is first detected.
-   This tool is mainly developed for Thing Descriptions. Even though it can be used for all JSON Schemas, it may not cover all schema rules. For example 'if, else, then' rule of Open API schema is not supported yet, but this functionality could be added in the future.

## License

Licensed under the MIT license, see [License](../../LICENSE.md).

## Script-based Spell Checking

JSON spell checker is a Node.js based tool.

You can use the functionality of this package by:

-   Install the package with npm `npm install @thing-description-playground/json-spell-checker` (or clone the repo and install the package with `npm install`)
-   Node.js or Browser

    -   Node.js: Require the package and use the validation function

    ```javascript
    const jsonSpellChecker = require("@thing-description-playground/json-spell-checker");
    ```

    -   Browser: Import the `JsonSpellChecker` as a global by adding a script tag to your HTML.

    ```html
    <script src="./node_modules/@thing-description-playground/json-spell-checker/dist/web-bundle.min.js"></script>
    ```

-   First, configure your spell checker using (similarityThreshold should be between 0 and 1 and try to set maxLengthDifference low if you need quick typo evaluation):

```javascript
jsonSpellChecker.configure(yourSchema, similarityThreshold, maxLengthDifference);
```

-   Or just set schema and use default values for similarityThreshold (0.85) and maxLengthDifference (2)

```javascript
jsonSpellChecker.configure(yourSchema);
```

-   Then call checkTypos function with your stringified JSON file to find typos

```javascript
jsonSpellChecker.checkTypos(stringifiedJsonFile);
```

### Structure

The [index.js](./src/index.js) file contains the main validation functionality and exports the module's functionalities.

## Examples

-   There are also examples provided in the [examples-scripts folder](./examples/scripts/) to demonstrate the usage of this package.

## Test Usage

Test Examples are located under the examples directory.
When preparing TD examples, you must fill in the 'typoCount' field corresponding to the number of typos in the TD.
