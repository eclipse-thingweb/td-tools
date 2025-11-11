// Flat ESLint config compatible with ESLint v9
module.exports = [
    {
        ignores: ["dist", "node_modules", "bin"],
        languageOptions: {
            parserOptions: {
                ecmaVersion: 8,
            },
            globals: {
                // browser globals
                window: "readonly",
                document: "readonly",
                navigator: "readonly",
                // node globals
                global: "readonly",
                process: "readonly",
                module: "readonly",
                require: "readonly",
                __dirname: "readonly",
                __filename: "readonly",
                // jest globals
                describe: "readonly",
                it: "readonly",
                test: "readonly",
                expect: "readonly",
                beforeEach: "readonly",
                afterEach: "readonly",
                jest: "readonly",
            },
        },
        extends: ["eslint:recommended", "prettier"],
    },
];
