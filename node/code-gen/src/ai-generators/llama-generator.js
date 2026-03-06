const { Groq } = require("groq-sdk");

/**
 * Generate code using the Llama API
 * @param { Object } generatorInputs 
 * @returns { Promise<String> } The generated code
 */
async function generateLlamaCode(generatorInputs, aiConfig) {
    const groq = new Groq({ apiKey: aiConfig.apiKey, dangerouslyAllowBrowser: true});

    const systemInstructions = "You are an expert senior IoT and WoT developer. Based on the provided JSON object, generate protocol-specific code that follows best practices using the specified programming language and library. Do not include any extra explanations, or descriptions only the code. The input includes a Thing Description (TD) with properties, actions, and events, from which you must use the specified affordance. Implement the operation as described, using the specified form or the default if no form index is provided. If the operation is observeproperty or subscribeevent assume the user also wants a way to unobserve and/or unsubscribe. The programming language and library should be adhered to in the generated code. Focus solely on producing the required code to perform the operation based on these inputs.";

    const chatCompletion = await groq.chat.completions.create({
        messages: [
            {
                role: "user",
                content: systemInstructions,
            },
            {
                role: "user",
                content: generatorInputs,
            },
        ],
        model: aiConfig.model ? aiConfig.model : "llama3-8b-8192",
    });

    // Print the completion returned by the LLM.
    return chatCompletion.choices[0]?.message?.content || "";
}

//Export the function to be used in the main script
module.exports = generateLlamaCode;