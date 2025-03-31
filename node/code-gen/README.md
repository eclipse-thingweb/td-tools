# WoT Code Generator

This package provides a client code generator for Thing Descriptions (TDs), capable of producing either deterministic or AI-generated code.

It can be used as a standalone package or via a command-line interface (CLI).

## Usage

Install this package via NPM:

```bash
npm install @thingweb/code-gen
```

Alternatively, clone the repository, navigate to node/code-gen, and install dependencies:

```bash
git clone https://github.com/eclipse-thingweb/td-tools
cd node/code-generator
npm install
```

## Code Generator CLI

A command-line interface tool for generating protocol-specific code snippets from Web of Things (WoT) Thing Descriptions (TDs).

### Features

- Interactive and one-line command modes
- Deterministic Support for multiple programming languages and libraries
- AI-powered code generation for not yet available cases (ChatGPT, Gemini, Llama)
- Flexible TD input (file or text editor)
- Multiple output options (console of file)

### Installation Steps

1. Clone the repository using Git:

    ```bash
    git clone https://github.com/SergioCasCeb/code-generator.git
    ```

2. Navigate to the project directory:

    ```bash
    cd code-generator
    ```

3. Install all project dependencies:

    ```bash
    npm install
    ```

4. Link the project globally to make the `generate-code` command available on your system:

    ```bash
    npm link
    ```

    This allows you to run the `generate-code` command anywhere in your terminal.

### Usage

The CLI can be used in two modes: interactive and one-line command

#### Interactive Mode

Run the CLI in interactive mode:

```bash
generate-code -i
```

The interactive mode guides you through the following steps:

1. Choose TD input method (file or text editor)
2. Select an affordance
3. Choose a form index (optional)
4. Select and operation
5. Choose between deterministic or AI-powered generation (If a protocol is not supported AI is selected by default)
6. Select programming language
7. Select library
8. Choose output type (console or file)

*Finally, after generating the code, the interactive mode also returns the equivalent options to run the CLI in the one-line mode.*

#### One-line Command Mode

For automated workflows, use the one-line command mode:

#### Options

- `-i, --interactive`: Run CLI in interactive mode
- `-t, --td <path>`: Path to the Thing Description file
- `-a, --affordance <name>`: Affordance to use
- `-f, --form-index <index>`: Form index to use
- `-o, --operation <name>`: Operation to perform
- `-l, --language <name>`: Programming language
- `-L, --library <name>`: Library to use
- `--ai`: Use AI generation
- `--tool <name>`: AI tool to use (ChatGPT, Gemini, Llama)
- `-O, --output <type>`: Output type (console or file)
- `-h, --help`: Display help information
- `-V, --version`: Display version number

#### Examples

Generate code utilizing the deterministic generator

```bash
generate-code --td ./calculator.td.jsonld -a result -f 0 -o readproperty -l javascript -L node-wot -O console
```

Generate code utilizing the AI generator

```bash
generate-code --td ./calculator.td.jsonld -a result -f 0 -o readproperty -l javascript -L axios --ai --tool chatgpt -O console
```

### Supported formats

#### Input files

- JSON (.json)
- JSON-LD (.jsonld)
- Text (.txt)

#### Programming Languages and Libraries

Deterministic:

- JavaScript
    - Fetch
    - node-wot
    - modbus-serial

- Python
    - Requests

No restrictions when using AI generation.

### Output

#### Console Output

The generated code is printed directly to the console in simple text format. AI generation adds markdown syntax to the code.

#### File Output

A new folder called `generator-ouput` is created within the project and the generated code is saved to a file with the following naming convention `<affordance>_<operation>_<language>.<extension>`

## Contributing

The deterministic code generation uses `handlebars` templates and protocol-specific helpers for correct compilation.

To contribute new templates:

1. Submit a PR containing only the template in the respective folder.
2. Test it within the code generator.
3. If protocol-specific logic is required, add the necessary helper functions in the respective folder along with documentation.
4. Finally, submit a final PR including any updates or additions to the code-generator, the `handlebars` helpers, etc.

We welcome contributions that expand the supported protocols and improve the overall code generation!
