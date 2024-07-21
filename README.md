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

The goal of this repository is to contain different tools for Thing Descriptions and Thing Models.
Currently, they are scattered in different Thingweb repositories and packages and they will be moved here.

Tools in this repository:

-   Async API Converter: https://github.com/eclipse-thingweb/td-tools/tree/main/node/async-api-converter
-   AAS AID Tooling: https://github.com/eclipse-thingweb/td-tools/tree/main/node/aas-aid

The list of all existing tools:

-   TD Validation: https://github.com/eclipse-thingweb/playground/tree/master/packages/core . Also in node-wot via simple AJV/Schema plus sanity checks on forms.
-   Thing Model helpers to resolve sub TMs: https://github.com/eclipse-thingweb/node-wot/blob/master/packages/td-tools/src/thing-model-helpers.ts
-   Default addition or removal for TDs: https://github.com/eclipse-thingweb/playground/tree/master/packages/defaults
-   JSON Schema based "spell checker" to find mistakes in a TD: https://github.com/eclipse-thingweb/playground/tree/master/packages/json-spell-checker
-   TD to OpenAPI converter: https://github.com/eclipse-thingweb/playground/tree/master/packages/td_to_openAPI
-   Feature/Assertion detecter for TDs: https://github.com/eclipse-thingweb/playground/tree/master/packages/assertions (will be moved to W3C Thing Description Repository)

> **Warning**
> When transferring we should avoid circular dependencies.
