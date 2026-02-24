/**
 * Google Gemini provider
 * Author: Husain Z Attarwala, PhD
 */
import { GoogleGenerativeAI, SchemaType } from '@google/generative-ai';
export class GoogleProvider {
    client;
    model;
    maxTokens;
    temperature;
    systemPrompt;
    constructor(options) {
        this.client = new GoogleGenerativeAI(options.apiKey);
        this.model = options.model;
        this.maxTokens = options.maxTokens || 8192;
        this.temperature = options.temperature || 1.0;
        this.systemPrompt = options.systemPrompt || '';
    }
    convertToolsToGemini(tools) {
        return tools.map(tool => ({
            name: tool.name,
            description: tool.description,
            parameters: {
                type: SchemaType.OBJECT,
                properties: tool.input_schema.properties,
                required: tool.input_schema.required || [],
            },
        }));
    }
    async chat(messages, tools) {
        const model = this.client.getGenerativeModel({
            model: this.model,
            systemInstruction: this.systemPrompt,
        });
        const geminiMessages = messages
            .filter(m => m.role !== 'system')
            .map(m => ({
            role: m.role === 'assistant' ? 'model' : 'user',
            parts: [{ text: m.content }],
        }));
        const generationConfig = {
            maxOutputTokens: this.maxTokens,
            temperature: this.temperature,
        };
        const chatOptions = {
            history: geminiMessages.slice(0, -1),
            generationConfig,
        };
        if (tools && tools.length > 0) {
            chatOptions.tools = [{ functionDeclarations: this.convertToolsToGemini(tools) }];
        }
        const chat = model.startChat(chatOptions);
        const lastMessage = geminiMessages[geminiMessages.length - 1];
        const result = await chat.sendMessage(lastMessage.parts[0].text);
        const response = result.response;
        let textContent = '';
        const toolCalls = [];
        for (const candidate of response.candidates || []) {
            for (const part of candidate.content.parts) {
                if (part.text) {
                    textContent += part.text;
                }
                else if (part.functionCall) {
                    toolCalls.push({
                        id: part.functionCall.name + '_' + Date.now(),
                        name: part.functionCall.name,
                        arguments: part.functionCall.args,
                    });
                }
            }
        }
        return {
            content: textContent,
            tool_calls: toolCalls.length > 0 ? toolCalls : undefined,
            stop_reason: response.candidates?.[0]?.finishReason || 'STOP',
            usage: {
                input_tokens: response.usageMetadata?.promptTokenCount || 0,
                output_tokens: response.usageMetadata?.candidatesTokenCount || 0,
            },
        };
    }
    async stream(messages, tools, onChunk) {
        const model = this.client.getGenerativeModel({
            model: this.model,
            systemInstruction: this.systemPrompt,
        });
        const geminiMessages = messages
            .filter(m => m.role !== 'system')
            .map(m => ({
            role: m.role === 'assistant' ? 'model' : 'user',
            parts: [{ text: m.content }],
        }));
        const generationConfig = {
            maxOutputTokens: this.maxTokens,
            temperature: this.temperature,
        };
        const chatOptions = {
            history: geminiMessages.slice(0, -1),
            generationConfig,
        };
        if (tools && tools.length > 0) {
            chatOptions.tools = [{ functionDeclarations: this.convertToolsToGemini(tools) }];
        }
        const chat = model.startChat(chatOptions);
        const lastMessage = geminiMessages[geminiMessages.length - 1];
        const result = await chat.sendMessageStream(lastMessage.parts[0].text);
        let textContent = '';
        const toolCalls = [];
        let stopReason = 'STOP';
        let usage = { input_tokens: 0, output_tokens: 0 };
        for await (const chunk of result.stream) {
            for (const candidate of chunk.candidates || []) {
                for (const part of candidate.content.parts) {
                    if (part.text) {
                        textContent += part.text;
                        if (onChunk) {
                            onChunk({
                                type: 'content',
                                content: part.text,
                            });
                        }
                    }
                    else if (part.functionCall) {
                        const toolCall = {
                            id: part.functionCall.name + '_' + Date.now(),
                            name: part.functionCall.name,
                            arguments: part.functionCall.args,
                        };
                        toolCalls.push(toolCall);
                        if (onChunk) {
                            onChunk({
                                type: 'tool_call',
                                tool_call: toolCall,
                            });
                        }
                    }
                }
            }
        }
        const finalResponse = await result.response;
        if (finalResponse.usageMetadata) {
            usage = {
                input_tokens: finalResponse.usageMetadata.promptTokenCount || 0,
                output_tokens: finalResponse.usageMetadata.candidatesTokenCount || 0,
            };
        }
        if (onChunk) {
            onChunk({ type: 'done', usage });
        }
        return {
            content: textContent,
            tool_calls: toolCalls.length > 0 ? toolCalls : undefined,
            stop_reason: stopReason,
            usage,
        };
    }
}
//# sourceMappingURL=google.js.map