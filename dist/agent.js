/**
 * AI Agent with tool-calling loop for pharmacometrics
 * Author: Husain Z Attarwala, PhD
 */
import { createProvider } from './providers/index.js';
import { loadConfig, getApiKey, PROVIDERS } from './config.js';
import { getAllTools, executeTool } from './tools/registry.js';
import chalk from 'chalk';
const SYSTEM_PROMPT = `You are PMX, a pharmacometrics co-pilot. You help scientists with population PK/PD analysis.

You have access to specialized tools for:
- Loading and exploring PK/PD datasets (NONMEM format)
- Fitting population PK models with nlmixr2 (1/2/3-compartment, oral/IV, with IIV)
- Running diagnostics (GOF plots, VPC, ETA distributions)
- Non-compartmental analysis (NCA) using PKNCA
- Covariate screening and stepwise covariate modeling (SCM)
- Forest plots for covariate effects
- Dose simulation with mrgsolve
- Population simulation with inter-individual variability
- Searching PubMed for published PopPK models
- Looking up drug PK parameters from PKPDBuilder
- Generating analysis reports (FDA-style HTML)
- Generating Beamer slide presentations (PDF)
- Building interactive Shiny simulator apps
- Multi-backend support: nlmixr2, NONMEM, Monolix, Phoenix NLME
- Project memory management (memory_read/write/search, init_project)

## Operating Mode: Autonomous

You run AUTONOMOUSLY by default. When given a task:
1. Do the full analysis without stopping to ask permission at each step
2. Make sensible default choices (start simple, compare models, pick the best)
3. Only pause to ask if there's genuine ambiguity that affects the outcome

## Standard Workflow

When asked to "analyze" or "run PopPK analysis":
1. load_dataset → summarize_dataset → plot_data
2. run_nca (initial parameter estimates)
3. fit_model (1-CMT) → fit_model (2-CMT)
4. compare_models → select best
5. goodness_of_fit → vpc → eta_plots
6. covariate_screening → stepwise_covariate_model (if significant)
7. parameter_table → generate_report
8. memory_write (log decisions and model history)

## Memory

At session start, call memory_read to restore project context.
After key decisions, call memory_write to log them.

## Communication Style

Be concise but thorough. Use pharmacometrics terminology correctly.
Present parameter tables in readable format.
Always state model recommendation with reasoning.
Flag concerns: high RSE (>50%), large shrinkage (>30%), convergence issues.
`;
export class PKPDBuilderAgent {
    provider;
    messages = [];
    tools = [];
    config;
    streaming;
    maxIterations;
    onStream;
    constructor(options = {}) {
        this.config = loadConfig();
        const providerName = options.provider || this.config.provider;
        const modelName = options.model || this.config.model;
        this.streaming = options.streaming ?? true;
        this.maxIterations = options.maxIterations || 10;
        this.onStream = options.onStream;
        const apiKey = getApiKey(providerName);
        if (!apiKey && !PROVIDERS[providerName]?.local) {
            throw new Error(`No API key for ${providerName}. Set ${PROVIDERS[providerName]?.env_key} or run setup.`);
        }
        this.provider = createProvider(providerName, {
            apiKey,
            model: modelName,
            maxTokens: this.config.max_tokens,
            temperature: 1.0,
            systemPrompt: SYSTEM_PROMPT,
        });
        this.tools = getAllTools();
    }
    /**
     * Add a user message to the conversation
     */
    addUserMessage(content) {
        this.messages.push({
            role: 'user',
            content,
        });
    }
    /**
     * Add an assistant message to the conversation
     */
    addAssistantMessage(content) {
        this.messages.push({
            role: 'assistant',
            content,
        });
    }
    /**
     * Run the agent loop: send message, execute tools, repeat until done
     */
    async run(userMessage) {
        this.addUserMessage(userMessage);
        let iterations = 0;
        let finalResponse = '';
        while (iterations < this.maxIterations) {
            iterations++;
            let response;
            if (this.streaming && this.provider.stream) {
                response = await this.provider.stream(this.messages, this.tools, chunk => {
                    if (chunk.type === 'content' && chunk.content && this.onStream) {
                        this.onStream(chunk.content);
                    }
                });
            }
            else {
                response = await this.provider.chat(this.messages, this.tools);
            }
            // Add assistant response to history
            if (response.content) {
                this.addAssistantMessage(response.content);
                finalResponse = response.content;
            }
            // If no tool calls, we're done
            if (!response.tool_calls || response.tool_calls.length === 0) {
                break;
            }
            // Execute tool calls
            for (const toolCall of response.tool_calls) {
                if (this.onStream) {
                    this.onStream(`\n${chalk.blue(`[Tool: ${toolCall.name}]`)}\n`);
                }
                const result = await executeTool(toolCall.name, toolCall.arguments);
                // Add tool result as a user message
                this.addUserMessage(`Tool "${toolCall.name}" returned:\n${JSON.stringify(result, null, 2)}`);
                if (this.onStream) {
                    this.onStream(`${chalk.dim(JSON.stringify(result, null, 2).slice(0, 200))}...\n`);
                }
            }
            // Continue loop to let the agent process tool results
        }
        if (iterations >= this.maxIterations) {
            const warning = '\n\n[Warning: Max iterations reached. Analysis may be incomplete.]';
            finalResponse += warning;
        }
        return finalResponse;
    }
    /**
     * Clear conversation history
     */
    clearHistory() {
        this.messages = [];
    }
    /**
     * Get conversation history
     */
    getHistory() {
        return [...this.messages];
    }
    /**
     * Get message count
     */
    getMessageCount() {
        return this.messages.length;
    }
}
//# sourceMappingURL=agent.js.map