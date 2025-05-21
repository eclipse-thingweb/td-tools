#!/usr/bin/env node
const { Command } = require("commander");
const chalk = require("chalk");
const { input, select, editor } = require('@inquirer/prompts');
const { createSpinner } = require('nanospinner');
const { addDefaults } = require('@thing-description-playground/defaults');
const tdValidator = require('@thing-description-playground/core').tdValidator;
const { generateCode } = require('../src/lib/code-generator.js');
const { getTDProtocols, getAvailableLanguages, getAvailableLibraries, getAffordanceType, generateFile, parseTD, getTDAffordances, getFormIndexes, getOperations } = require('../src/util/util.js');
const fs = require('fs');
const path = require("path");
const dotenv = require('dotenv');
dotenv.config();

/**
 * Provide a user friendly message when the user exits the program and throw an error if the reason for the exit is not an ExitPromptError
 */
process.on('uncaughtException', (error) => {
    if (error instanceof Error && error.name === 'ExitPromptError') {
        console.log(chalk.yellow('\nThe Code Generator has been exited!'));
        process.exit(1);
    } else {
        throw error;
    }
});


/**************************/
/* One-line CLI logic **/
/**************************/
const program = new Command();

program
    .name("generate-code")
    .description("Generate protocol specific code snippets for Thing Descriptions")
    .version('1.0.0')

program
    .option("-i, --interactive", "The interactive mode", false)
    .option("-t, --td <path>", "Path to the Thing Description file")
    .option("-a, --affordance <name>", "Affordance to use")
    .option("-f, --form-index <index>", "Form index to use")
    .option("-o, --operation <name>", "Operation to perform")
    .option("-l, --language <name>", "Programming language")
    .option("-L, --library <name>", "Library to use")
    .option("--ai", "Use AI generation", false)
    .option("--tool <name>", "AI tool to use (ChatGPT, Gemini, Llama)")
    .option("-O, --output <type>", "Output type (console or file)", "console")
    .action((options) => {
        if (options.interactive) {
            runInteractiveCLI();
        } else {

            const requiredOptions = ['td', 'affordance', 'operation', 'language', 'library'];
            const missingOptions = requiredOptions.filter((option) => !options[option]);

            if (missingOptions.length > 0) {
                console.error("Error: " + chalk.red(`Missing required options: ${missingOptions.join(', ')}`));
                program.help();
                program.exit(1);
            }

            runOneLineCLI(options);
        }
    });

program.parse(process.argv);

/**
 * Run the one-line CLI
 * @param { Object } options 
 */
async function runOneLineCLI(options) {
    const spinner = createSpinner("Generating code...").start();
    try {
        const fileType = path.extname(options.td);

        if (fileType !== '.json' && fileType !== '.jsonld' && fileType !== '.txt') {
            throw new Error("Invalid file format! Please select a JSON, JSONLD or TXT file.");
        }

        const fileContent = fs.readFileSync(options.td, 'utf8');
        const parsedTD = parseTD(fileContent);

        await validateTD(parsedTD);

        const generatorInputs = {
            td: parsedTD,
            affordance: options.affordance,
            formIndex: options.formIndex,
            operation: options.operation,
            programmingLanguage: options.language.toLowerCase(),
            library: options.library.toLowerCase()
        };

        //Get the AI tool if the generator type is AI
        if (options.ai) {

            //Get the AI configuration based on the selected AI tool
            if (options.tool == "chatgpt") {
                aiConfig = {
                    apiKey: process.env.OPENAI_API_KEY,
                    enpoint: process.env.OPENAI_ENDPOINT,
                    model: process.env.OPENAI_MODEL
                }
            }
            else if (options.tool == "gemini") {
                aiConfig = {
                    apiKey: process.env.GEMINI_API_KEY,
                    model: process.env.GEMINI_MODEL
                }
            }
            else {
                aiConfig = {
                    apiKey: process.env.GROQ_API_KEY,
                    model: process.env.GROQ_MODEL
                }
            }
        }

        const outputCode = await generateCode(generatorInputs, options.ai, options.tool ? options.tool : null);
        spinner.success(`Success: ${chalk.green('Code generated successfully!\n')}`);

        if (options.output === 'file') {
            generateFile(options.affordance, options.operation, options.language, outputCode);
        } else {
            console.log(outputCode);
        }
    } catch (error) {
        spinner.error("Error: " + chalk.red(error.message));
        process.exit(1);
    }
}



/**************************/
/* Interactive CLI Logic **/
/**************************/

/**
 * Get the type of input for the TD
 * @returns { String } tdInput
 */
async function tdInputType() {
    const tdInput = await select({
        message: 'How would you like to input your TD?',
        choices: [
            {
                name: 'File',
                value: 'file',
            },
            {
                name: 'Text',
                value: 'text',
            },
        ],
    });

    return tdInput;
}

/**
 * Add defaults and validate the TD
 * @param { Object } td 
 * @returns { Boolean }
 */
async function validateTD(td) {
    //add defaults to the td, to assure that all forms have an operation and contentType
    addDefaults(td);

    // Store log messages, to show only if the validation fails
    let logMessages = [];

    // Push log messages to the logMessages array
    function validationLog(msg) {
        logMessages.push(msg);
    }

    //run the tdValidator function
    const validation = await tdValidator(JSON.stringify(td), validationLog, { checkDefaults: true, checkJsonLd: true, checkTmConformance: false });

    //check al the report values to see if the validation passed
    const validTD = Object.values(validation.report).every(value => value !== 'failed');

    if (validTD) {
        return true;
    } else {
        throw new Error('The Thing Description is invalid! Please check the following errors:\n' + logMessages.join('\n'));
    }
}

/**
 * Get the TD from a file
 * @returns { Object } parsedTD
 */
async function getTDFile() {

    const fileSelectorModule = await import('inquirer-file-selector');
    const fileSelector = fileSelectorModule.default;
    const filePath = await fileSelector({
        message: 'Select the path to your TD file:',
        basePath: process.cwd(),
        type: 'file',
        allowCancel: true,
        cancelText: 'Exited file selection',
    });

    try {
        const fileType = path.extname(filePath);

        if (fileType !== '.json' && fileType !== '.jsonld' && fileType !== '.txt') {
            console.log(chalk.red("Invalid file format! Please select a JSON, JSONLD or TXT file."));
            process.exit(1);
        }

        const fileContent = fs.readFileSync(filePath, 'utf8');
        const parsedTD = parseTD(fileContent);
        await validateTD(parsedTD);
        return parsedTD;


    } catch (error) {
        console.log("Error: " + chalk.red(error.message));
        process.exit(1);
    }
}

/**
 * Get the TD from a text editor
 * @returns { Object } parsedTD
 */
async function getTDEditor() {

    const td = await editor({
        message: 'Enter your TD here:',
    });

    try {
        const parsedTD = parseTD(td);
        await validateTD(parsedTD);
        return parsedTD;
    }
    catch (error) {
        console.log("Error: " + chalk.red(error.message));
        process.exit(1);
    }
}

/**
 * Get all the affordance options from the TD and return the selected affordance
 * @param { Object } td 
 * @returns { String } affordance
 */
async function getAffordanceOptions(td) {
    try {
        const affordanceOptions = getTDAffordances(td);

        const affordance = await select({
            message: 'Select an affordance:',
            choices: affordanceOptions,
        });

        return affordance;

    } catch (error) {
        console.log("Error: " + chalk.red(error.message));
        process.exit(1);
    }
}

/**
 * Get all the forms available for the selected affordance and return the selected form index
 * @param { Object } td 
 * @param { String } affordanceType 
 * @param { String } affordance 
 * @returns { String } formIndex
 */
async function getFormIndex(td, affordanceType, affordance) {
    try {
        const availableForms = getFormIndexes(td, affordanceType, affordance) || [];
        const emptyForm = [{ name: 'None', value: null, description: "Do not want to specify any form!" }];

        const formIndexOptions = [
            ...emptyForm,
            ...availableForms.map((index) => { return { name: index, value: index } })
        ];

        const formIndex = await select({
            message: `Select a form index:`,
            choices: formIndexOptions,
        });

        return formIndex;

    } catch (error) {
        console.log("Error: " + chalk.red(error.message));
        process.exit(1);
    }
}

/**
 * Get the possbile operations for the selected affordance and return the selected operation
 * @param { String } affordanceType 
 * @returns { String } operation
 */
async function getOperation(td, affordanceType, affordance, formIndex) {

    try {
        const availableOperations = getOperations(td, affordanceType, affordance, formIndex);

        if (availableOperations.length === 1) {
            console.log(`${chalk.green.bold('✓')} ${chalk.bold('Select an operation:')} ${chalk.cyan(availableOperations[0])}`);
            return availableOperations[0];
        }
        else {
            const operation = await select({
                message: 'Select an operation:',
                choices: availableOperations,
            });

            return operation;
        }

    } catch (error) {
        console.log("Error: " + chalk.red(error.message));
        process.exit(1);
    }
}

/**
 * Get the generator type
 * @returns { Boolean } isAI
 */
async function getGeneratorType() {
    const isAI = await select({
        message: 'Select a generator type:',
        choices: [
            { name: 'Deterministic', value: false },
            { name: 'AI', value: true },
        ],
    });

    return isAI;
}

/**
 * Get the AI tool
 * @returns { String } aiTool
 */
async function getAITool() {
    const aiTool = await select({
        message: 'Select an AI tool:',
        choices: [
            { name: 'ChatGPT', value: "chatgpt" },
            { name: 'Gemini', value: "gemini" },
            { name: 'Llama', value: "llama" },
        ],
    });

    return aiTool;
}

/**
 * Get the available programming languages based on the selected TD protocols and return the selected programming language.
 * If the generator type is AI, get the programming language as a text input
 * @param { Boolean } isAI 
 * @param { Array } tdProtocols 
 * @returns { Array } [programmingLanguage, languageList]
 */
async function getProgrammingLanguage(isAI, tdProtocols) {

    if (isAI) {
        const programmingLanguage = await input({
            type: 'text',
            message: 'Enter a programming language:',
        });

        return [programmingLanguage, null];
    } else {
        const languagesList = getAvailableLanguages(tdProtocols);
        let availableLanguages = [];

        languagesList.forEach((language) => {
            availableLanguages.push(...Object.keys(language))
        })

        availableLanguages = [...new Set(availableLanguages)];

        if (availableLanguages && availableLanguages.length > 0) {
            const programmingLanguage = await select({
                message: 'Enter a programming language:',
                choices: availableLanguages,
            });

            return [programmingLanguage, languagesList];
        } else {
            console.log(chalk.red('No programming languages available!'));
            process.exit(1);
        }
    }
}

/**
 * Get the available libraries based on the selected programming language and return the selected library.
 * If the generator type is AI, get the library as a text input
 * @param { Boolean } isAI 
 * @param { String } programmingLanguage 
 * @param { Array } languageList 
 * @returns { String } library
 */
async function getLibrary(isAI, programmingLanguage, languageList) {

    if (isAI) {
        const library = await input({
            type: 'text',
            message: 'Enter a library:',
        });

        return library;
    }
    else {
        const availableLibraries = getAvailableLibraries(programmingLanguage, languageList);

        if (availableLibraries && availableLibraries.length > 0) {
            const library = await select({
                message: 'Select a library:',
                choices: availableLibraries,
            });

            return library;
        } else {
            console.log(chalk.red('No libraries available!'));
            process.exit(1);
        }
    }
}

/**
 * Get the desired output type
 * @returns { String } output
 */
async function getOutputType() {
    const output = await select({
        message: 'How would you like to output the code?',
        choices: [
            {
                name: 'Console',
                value: 'console',
            },
            {
                name: 'File',
                value: 'file',
            },
        ],
    });

    return output;
}

/**
 * Return the CLI options for the one-line CLI
 * @param { Object } generatorInputs 
 * @param { Boolean } isAI 
 * @param { String } aiTool 
 * @param { String } outputType 
 * @returns { String } cliOptionsString
 */
function returnCLIOptions(generatorInputs, isAI, aiTool, outputType) {
    const cliOptionsString = `generate-code ${chalk.gray('--td')} [path to TD] ${chalk.gray('--affordance')} ${generatorInputs.affordance} ${generatorInputs.formIndex !== null ? chalk.gray('--form-index ') + generatorInputs.formIndex : ''} ${chalk.gray('--operation')} ${generatorInputs.operation} ${chalk.gray('--language')} ${generatorInputs.programmingLanguage} ${chalk.gray('--library')} ${generatorInputs.library} ${isAI ? chalk.gray('--ai --tool ') + aiTool : ''} ${chalk.gray('--output')} ${outputType}`;

    return cliOptionsString;
}

/**
 * Main function to run the interactive CLI
 */
async function runInteractiveCLI() {

    //Declare all necessary variables
    let inputTD;
    let affordance;
    let formIndex;
    let operation;
    let aiConfig;
    let isAI = false;
    let aiTool;
    let tdProtocols;
    let programmingLanguage;
    let languageList;
    let library;
    let outputType = 'console';

    //Get the type of input for the TD
    const inputType = await tdInputType();

    //Get the TD based on the input type
    if (inputType === 'file') {
        inputTD = await getTDFile();
    } else {
        inputTD = await getTDEditor();
    }

    //Get the affordance
    affordance = await getAffordanceOptions(inputTD);

    //Get the affordance type
    const affordanceType = getAffordanceType(inputTD, affordance);

    //Get the form index
    formIndex = await getFormIndex(inputTD, affordanceType, affordance);

    //Get the operation
    operation = await getOperation(inputTD, affordanceType, affordance, formIndex);

    //Get the TD protocols
    tdProtocols = getTDProtocols(JSON.stringify(inputTD));

    //Do not ask for the generator type if the TD protocols are not available in the templates
    if (tdProtocols) {
        //Get the generator type
        isAI = await getGeneratorType();
    } else {
        isAI = true;
    }

    //Get the AI tool if the generator type is AI
    if (isAI) {
        aiTool = await getAITool();

        //Get the AI configuration based on the selected AI tool
        if (aiTool == "chatgpt") {
            aiConfig = {
                apiKey: process.env.OPENAI_API_KEY,
                enpoint: process.env.OPENAI_ENDPOINT,
                model: process.env.OPENAI_MODEL
            }
        }
        else if (aiTool == "gemini") {
            aiConfig = {
                apiKey: process.env.GEMINI_API_KEY,
                model: process.env.GEMINI_MODEL
            }
        }
        else {
            aiConfig = {
                apiKey: process.env.GROQ_API_KEY,
                model: process.env.GROQ_MODEL
            }
        }
    }

    //Get the programming language
    [programmingLanguage, languageList] = await getProgrammingLanguage(isAI, tdProtocols);

    //Get the library
    library = await getLibrary(isAI, programmingLanguage, languageList);

    //Get the output type
    outputType = await getOutputType();

    //Prepare the inputs for the code generator and generate the code
    const generatorInputs = {
        td: inputTD,
        affordance: affordance,
        formIndex: formIndex,
        operation: operation,
        programmingLanguage: programmingLanguage,
        library: library
    };

    //Start the loading spinner
    const spinner = createSpinner('Generating Code...').start();

    try {
        //Generate the code and stop the spinner if successful
        const outputCode = await generateCode(generatorInputs, isAI, aiTool ? aiTool : null, aiConfig);
        spinner.success(`Success: ${chalk.green('Code generated successfully!')}`)
        console.log(`${chalk.bold.yellow('CLI Options:')} ${returnCLIOptions(generatorInputs, isAI, aiTool, outputType)}`);
        if (outputType === 'file') {
            generateFile(affordance, operation, programmingLanguage, outputCode);
        } else {
            console.log(`\n${outputCode}`);
        }

    } catch (error) {
        //Stop the spinner and display the error message
        spinner.error(`Error: ${chalk.red(error.message)}`);
        process.exit(1);
    }

}