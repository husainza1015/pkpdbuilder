/**
 * Ollama (local) provider
 * Author: Husain Z Attarwala, PhD
 */
export class OllamaProvider {
    baseUrl;
    model;
    maxTokens;
    temperature;
    constructor(options) {
        this.baseUrl = process.env.OLLAMA_HOST || 'http://localhost:11434';
        this.model = options.model;
        this.maxTokens = options.maxTokens || 8192;
        this.temperature = options.temperature || 1.0;
    }
    convertToolsToOllama(tools) {
        return tools.map(tool => ({
            type: 'function',
            function: {
                name: tool.name,
                description: tool.description,
                parameters: tool.input_schema,
            },
        }));
    }
    async chat(messages, tools) {
        const ollamaMessages = messages.map(m => ({
            role: m.role,
            content: m.content,
        }));
        const body = {
            model: this.model,
            messages: ollamaMessages,
            stream: false,
            options: {
                num_predict: this.maxTokens,
                temperature: this.temperature,
            },
        };
        if (tools && tools.length > 0) {
            body.tools = this.convertToolsToOllama(tools);
        }
        const response = await fetch(`${this.baseUrl}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!response.ok) {
            throw new Error(`Ollama error: ${response.statusText}`);
        }
        const data = await response.json();
        const toolCalls = [];
        if (data.message?.tool_calls) {
            for (const tc of data.message.tool_calls) {
                toolCalls.push({
                    id: tc.function.name + '_' + Date.now(),
                    name: tc.function.name,
                    arguments: tc.function.arguments,
                });
            }
        }
        return {
            content: data.message?.content || '',
            tool_calls: toolCalls.length > 0 ? toolCalls : undefined,
            stop_reason: data.done ? 'stop' : 'length',
        };
    }
    async stream(messages, tools, onChunk) {
        const ollamaMessages = messages.map(m => ({
            role: m.role,
            content: m.content,
        }));
        const body = {
            model: this.model,
            messages: ollamaMessages,
            stream: true,
            options: {
                num_predict: this.maxTokens,
                temperature: this.temperature,
            },
        };
        if (tools && tools.length > 0) {
            body.tools = this.convertToolsToOllama(tools);
        }
        const response = await fetch(`${this.baseUrl}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!response.ok) {
            throw new Error(`Ollama error: ${response.statusText}`);
        }
        let textContent = '';
        const toolCalls = [];
        let stopReason = 'stop';
        const reader = response.body?.getReader();
        if (!reader)
            throw new Error('No response body');
        const decoder = new TextDecoder();
        let buffer = '';
        while (true) {
            const { done, value } = await reader.read();
            if (done)
                break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            for (const line of lines) {
                if (!line.trim())
                    continue;
                try {
                    const data = JSON.parse(line);
                    if (data.message?.content) {
                        textContent += data.message.content;
                        if (onChunk) {
                            onChunk({
                                type: 'content',
                                content: data.message.content,
                            });
                        }
                    }
                    if (data.message?.tool_calls) {
                        for (const tc of data.message.tool_calls) {
                            const toolCall = {
                                id: tc.function.name + '_' + Date.now(),
                                name: tc.function.name,
                                arguments: tc.function.arguments,
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
                    if (data.done) {
                        stopReason = 'stop';
                    }
                }
                catch (e) {
                    // Skip invalid JSON lines
                }
            }
        }
        if (onChunk) {
            onChunk({ type: 'done' });
        }
        return {
            content: textContent,
            tool_calls: toolCalls.length > 0 ? toolCalls : undefined,
            stop_reason: stopReason,
        };
    }
}
//# sourceMappingURL=ollama.js.map