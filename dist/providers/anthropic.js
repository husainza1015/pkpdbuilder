/**
 * Anthropic Claude provider
 * Author: Husain Z Attarwala, PhD
 */
import Anthropic from '@anthropic-ai/sdk';
export class AnthropicProvider {
    client;
    model;
    maxTokens;
    temperature;
    systemPrompt;
    constructor(options) {
        this.client = new Anthropic({
            apiKey: options.apiKey,
        });
        this.model = options.model;
        this.maxTokens = options.maxTokens || 8192;
        this.temperature = options.temperature || 1.0;
        this.systemPrompt = options.systemPrompt || '';
    }
    async chat(messages, tools) {
        const anthropicMessages = messages
            .filter(m => m.role !== 'system')
            .map(m => ({
            role: m.role,
            content: m.content,
        }));
        const params = {
            model: this.model,
            max_tokens: this.maxTokens,
            temperature: this.temperature,
            messages: anthropicMessages,
        };
        if (this.systemPrompt) {
            params.system = this.systemPrompt;
        }
        if (tools && tools.length > 0) {
            params.tools = tools;
        }
        const response = await this.client.messages.create(params);
        // Extract content and tool calls
        let textContent = '';
        const toolCalls = [];
        for (const block of response.content) {
            if (block.type === 'text') {
                textContent += block.text;
            }
            else if (block.type === 'tool_use') {
                toolCalls.push({
                    id: block.id,
                    name: block.name,
                    arguments: block.input,
                });
            }
        }
        return {
            content: textContent,
            tool_calls: toolCalls.length > 0 ? toolCalls : undefined,
            stop_reason: response.stop_reason || 'end_turn',
            usage: {
                input_tokens: response.usage.input_tokens,
                output_tokens: response.usage.output_tokens,
            },
        };
    }
    async stream(messages, tools, onChunk) {
        const anthropicMessages = messages
            .filter(m => m.role !== 'system')
            .map(m => ({
            role: m.role,
            content: m.content,
        }));
        const params = {
            model: this.model,
            max_tokens: this.maxTokens,
            temperature: this.temperature,
            messages: anthropicMessages,
        };
        if (this.systemPrompt) {
            params.system = this.systemPrompt;
        }
        if (tools && tools.length > 0) {
            params.tools = tools;
        }
        const stream = await this.client.messages.create({
            ...params,
            stream: true,
        });
        let textContent = '';
        const toolCalls = [];
        let currentToolCall = null;
        let stopReason = 'end_turn';
        let usage = { input_tokens: 0, output_tokens: 0 };
        for await (const event of stream) {
            if (event.type === 'content_block_start') {
                if (event.content_block.type === 'tool_use') {
                    currentToolCall = {
                        id: event.content_block.id,
                        name: event.content_block.name,
                        arguments: {},
                    };
                }
            }
            else if (event.type === 'content_block_delta') {
                if (event.delta.type === 'text_delta') {
                    textContent += event.delta.text;
                    if (onChunk) {
                        onChunk({
                            type: 'content',
                            content: event.delta.text,
                        });
                    }
                }
                else if (event.delta.type === 'input_json_delta') {
                    if (currentToolCall) {
                        // Accumulate JSON for tool arguments
                        const partial = event.delta.partial_json;
                        // Note: Anthropic sends partial JSON, need to accumulate
                    }
                }
            }
            else if (event.type === 'content_block_stop') {
                if (currentToolCall && currentToolCall.id) {
                    toolCalls.push(currentToolCall);
                    if (onChunk) {
                        onChunk({
                            type: 'tool_call',
                            tool_call: currentToolCall,
                        });
                    }
                    currentToolCall = null;
                }
            }
            else if (event.type === 'message_delta') {
                if (event.delta.stop_reason) {
                    stopReason = event.delta.stop_reason;
                }
                if (event.usage) {
                    usage = event.usage;
                }
            }
            else if (event.type === 'message_stop') {
                // Capture final usage if available
                if (event.message?.usage) {
                    usage = event.message.usage;
                }
            }
        }
        if (onChunk) {
            onChunk({
                type: 'done',
                usage,
            });
        }
        return {
            content: textContent,
            tool_calls: toolCalls.length > 0 ? toolCalls : undefined,
            stop_reason: stopReason,
            usage,
        };
    }
}
//# sourceMappingURL=anthropic.js.map