// Minimal flat ESLint config (eslint v9+)
module.exports = [
    {
        // Apply to JS/TS source files
        files: ["**/*.{js,ts,jsx,tsx}"],
        // Ignore top-level/build artifacts and package bundles. Keep linting focused on source files.
        ignores: [
            "dist",
            "dist/**",
            "node_modules",
            "node_modules/**",
            "bin",
            "bin/**",
            // ignore built distributions inside node/* packages
            "node/*/dist",
            "node/*/dist/**",
            "node/**/dist",
            "node/**/dist/**",
            // ignore generated web bundles and minified bundles
            "node/**/web-bundle*.js",
            "node/**/web-bundle*.min.js",
            "node/**/bundle*.js",
            "**/*.min.js",
        ],
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
    },
];
