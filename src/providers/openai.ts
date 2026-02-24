/**
 * OpenAI GPT provider
 * Author: Husain Z Attarwala, PhD
 */

import OpenAI from 'openai';
import type {
  Provider,
  ProviderOptions,
  Message,
  Tool,
  ChatResponse,
  ToolCall,
  StreamChunk,
} from './base.js';

export class OpenAIProvider implements Provider {
  private client: OpenAI;
  private model: string;
  private maxTokens: number;
  private temperature: number;

  constructor(options: ProviderOptions) {
    this.client = new OpenAI({
      apiKey: options.apiKey,
    });
    this.model = options.model;
    this.maxTokens = options.maxTokens || 8192;
    this.temperature = options.temperature || 1.0;
  }

  private convertToolsToOpenAI(tools: Tool[]): OpenAI.Chat.ChatCompletionTool[] {
    return tools.map(tool => ({
      type: 'function' as const,
      function: {
        name: tool.name,
        description: tool.description,
        parameters: tool.input_schema,
      },
    }));
  }

  async chat(messages: Message[], tools?: Tool[]): Promise<ChatResponse> {
    const openaiMessages: OpenAI.Chat.ChatCompletionMessageParam[] = messages.map(m => ({
      role: m.role,
      content: m.content,
    }));

    const params: OpenAI.Chat.ChatCompletionCreateParams = {
      model: this.model,
      messages: openaiMessages,
      max_tokens: this.maxTokens,
      temperature: this.temperature,
    };

    if (tools && tools.length > 0) {
      params.tools = this.convertToolsToOpenAI(tools);
    }

    const response = await this.client.chat.completions.create(params);

    const choice = response.choices[0];
    const message = choice.message;

    const toolCalls: ToolCall[] = [];
    if (message.tool_calls) {
      for (const tc of message.tool_calls) {
        toolCalls.push({
          id: tc.id,
          name: tc.function.name,
          arguments: JSON.parse(tc.function.arguments),
        });
      }
    }

    return {
      content: message.content || '',
      tool_calls: toolCalls.length > 0 ? toolCalls : undefined,
      stop_reason: choice.finish_reason,
      usage: response.usage
        ? {
            input_tokens: response.usage.prompt_tokens,
            output_tokens: response.usage.completion_tokens,
          }
        : undefined,
    };
  }

  async stream(
    messages: Message[],
    tools?: Tool[],
    onChunk?: (chunk: StreamChunk) => void
  ): Promise<ChatResponse> {
    const openaiMessages: OpenAI.Chat.ChatCompletionMessageParam[] = messages.map(m => ({
      role: m.role,
      content: m.content,
    }));

    const params: OpenAI.Chat.ChatCompletionCreateParams = {
      model: this.model,
      messages: openaiMessages,
      max_tokens: this.maxTokens,
      temperature: this.temperature,
      stream: true,
    };

    if (tools && tools.length > 0) {
      params.tools = this.convertToolsToOpenAI(tools);
    }

    const stream = await this.client.chat.completions.create(params);

    let textContent = '';
    const toolCalls: Map<number, ToolCall> = new Map();
    let stopReason = 'stop';

    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta;
      if (!delta) continue;

      if (delta.content) {
        textContent += delta.content;
        if (onChunk) {
          onChunk({
            type: 'content',
            content: delta.content,
          });
        }
      }

      if (delta.tool_calls) {
        for (const tc of delta.tool_calls) {
          if (!toolCalls.has(tc.index)) {
            toolCalls.set(tc.index, {
              id: tc.id || '',
              name: tc.function?.name || '',
              arguments: {},
            });
          }
          const existing = toolCalls.get(tc.index)!;
          if (tc.function?.arguments) {
            // Accumulate arguments
            const argsStr = (existing.arguments as any)._partial || '';
            (existing.arguments as any)._partial = argsStr + tc.function.arguments;
          }
        }
      }

      if (chunk.choices[0]?.finish_reason) {
        stopReason = chunk.choices[0].finish_reason;
      }
    }

    // Parse accumulated tool arguments
    const finalToolCalls: ToolCall[] = [];
    for (const tc of toolCalls.values()) {
      try {
        const argsStr = (tc.arguments as any)._partial || '{}';
        tc.arguments = JSON.parse(argsStr);
        finalToolCalls.push(tc);
        if (onChunk) {
          onChunk({
            type: 'tool_call',
            tool_call: tc,
          });
        }
      } catch (e) {
        // Failed to parse, skip
      }
    }

    if (onChunk) {
      onChunk({ type: 'done' });
    }

    return {
      content: textContent,
      tool_calls: finalToolCalls.length > 0 ? finalToolCalls : undefined,
      stop_reason: stopReason,
    };
  }
}
