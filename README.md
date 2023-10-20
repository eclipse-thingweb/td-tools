<img title="ThingWeb" alt="Thingweb logo" src="https://raw.githubusercontent.com/eclipse-thingweb/website/master/misc/thingweb_logo.svg" width="300px">

# Thing Description Tools

The goal of this repository is to contain different tools for Thing Descriptions and Thing Models.
Currently, they are scattered in different Thingweb repositories and packages and they will be moved here. 

The list of all tools:
- TD Validation: https://github.com/eclipse-thingweb/playground/tree/master/packages/core . Also in node-wot via simple AJV/Schema plus sanity checks on forms. 
- Thing Model helpers to resolve sub TMs: https://github.com/eclipse-thingweb/node-wot/blob/master/packages/td-tools/src/thing-model-helpers.ts
- AAS AID <-> TD converter: https://github.com/eclipse-thingweb/node-wot/tree/master/packages/td-tools/src/util
- Default addition or removal for TDs: https://github.com/eclipse-thingweb/playground/tree/master/packages/defaults
- JSON Schema based "spell checker" to find mistakes in a TD: https://github.com/eclipse-thingweb/playground/tree/master/packages/json-spell-checker
- TD to OpenAPI converter: https://github.com/eclipse-thingweb/playground/tree/master/packages/td_to_openAPI
- TD to AsyncAPI converter: https://github.com/eclipse-thingweb/playground/tree/master/packages/td_to_asyncapi
- Feature/Assertion detecter for TDs: https://github.com/eclipse-thingweb/playground/tree/master/packages/assertions (will be moved to W3C Thing Description Repository)