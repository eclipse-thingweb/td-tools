<h1>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/eclipse-thingweb/thingweb/main/brand/logos/td-tools_for_dark_bg.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/eclipse-thingweb/thingweb/master/brand/logos/td-tools.svg">
    <img title="Eclipse Thingweb TD Tools" alt="Eclipse Thingweb logo with TD Tools" src="https://github.com/eclipse-thingweb/thingweb/raw/main/brand/logos/td-tools.svg" width="300">
  </picture>
</h1>

[![AAS AID CI Pipeline](https://github.com/eclipse-thingweb/td-tools/actions/workflows/ci-aas-aid.yaml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/ci-aas-aid.yaml)
[![AsyncAPI Converter CI Pipeline](https://github.com/eclipse-thingweb/td-tools/actions/workflows/ci-async-api-converter.yaml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/ci-async-api-converter.yaml)
[![OpenAPI Converter CI Pipeline](https://github.com/eclipse-thingweb/td-tools/actions/workflows/ci-open-api-converter.yaml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/ci-open-api-converter.yaml)
[![JSON Spell Checker CI Pipeline](https://github.com/eclipse-thingweb/td-tools/actions/workflows/ci-json-spell-checker.yaml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/ci-json-spell-checker.yaml)
[![TD Utils CI Pipeline](https://github.com/eclipse-thingweb/td-tools/actions/workflows/ci-td-utils.yaml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/ci-td-utils.yaml)
[![Thing Model CI Pipeline](https://github.com/eclipse-thingweb/td-tools/actions/workflows/ci-thing-model.yaml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/ci-thing-model.yaml)

[![CodeQL](https://github.com/eclipse-thingweb/td-tools/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/codeql-analysis.yml)
[![ESLint](https://github.com/eclipse-thingweb/td-tools/actions/workflows/eslint.yml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/eslint.yml)
[![Prettier](https://github.com/eclipse-thingweb/td-tools/actions/workflows/prettier.yml/badge.svg)](https://github.com/eclipse-thingweb/td-tools/actions/workflows/prettier.yml)
[![codecov](https://codecov.io/gh/eclipse-thingweb/td-tools/branch/main/graph/badge.svg?token=ZP8VZROLXD)](https://codecov.io/gh/eclipse-thingweb/td-tools)

The goal of this repository is to contain different tools for Thing Descriptions and Thing Models.
Currently, they are scattered in different Thingweb repositories and packages and they will be moved here.

Tools in this repository:

-   [AAS AID Tooling](https://github.com/eclipse-thingweb/td-tools/tree/main/node/aas-aid): Converting TD to AAS AID and vice versa
-   [AsyncAPI Converter](https://github.com/eclipse-thingweb/td-tools/tree/main/node/async-api-converter): Converting TDs to AsyncAPI documents when the TD uses MQTT binding
-   [JSON Spell Checker](https://github.com/eclipse-thingweb/td-tools/tree/main/node/json-spell-checker): Checking errors in JSON documents (e.g. TDs) when there is a JSON Schema available (e.g. TD JSON Schema). This is not limited to TDs only.
-   [OpenAPI Converter](https://github.com/eclipse-thingweb/td-tools/tree/main/node/open-api-converter): Converting TDs to OpenAPI documents when the TD uses HTTP binding
-   [Thing Model Tooling](https://github.com/eclipse-thingweb/td-tools/tree/main/node/thing-model): Tooling to use Thing Models, such as resolving dependencies and imports.

Additionally, the [TD Utils](https://github.com/eclipse-thingweb/td-tools/tree/main/node/td-utils) package contains small tools that help with TD-based workflows. These are:

- Protocol Detection: Going through a TD and providing an object with all found protocols.


The list of existing tools in other Thingweb repositories, which will be moved here over time:

-   TD Validation: https://github.com/eclipse-thingweb/playground/tree/master/packages/core . Also in node-wot via simple AJV/Schema plus sanity checks on forms.
-   Default addition or removal for TDs: https://github.com/eclipse-thingweb/playground/tree/master/packages/defaults
-   Feature/Assertion detecter for TDs: https://github.com/eclipse-thingweb/playground/tree/master/packages/assertions (will be moved to W3C Thing Description Repository)
