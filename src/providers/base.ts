/**
 * Base provider interface for LLM providers
 * Author: Husain Z Attarwala, PhD
 */

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface Tool {
  name: string;
  description: string;
  input_schema: {
    type: 'object';
    properties: Record<string, any>;
    required?: string[];
  };
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
}

export interface ToolResult {
  tool_call_id: string;
  content: string;
}

export interface ChatResponse {
  content: string;
  tool_calls?: ToolCall[];
  stop_reason: string;
  usage?: {
    input_tokens: number;
    output_tokens: number;
  };
}

export interface StreamChunk {
  type: 'content' | 'tool_call' | 'done';
  content?: string;
  tool_call?: ToolCall;
  usage?: {
    input_tokens: number;
    output_tokens: number;
  };
}

export interface ProviderOptions {
  apiKey: string;
  model: string;
  maxTokens?: number;
  temperature?: number;
  systemPrompt?: string;
}

export interface Provider {
  chat(messages: Message[], tools?: Tool[]): Promise<ChatResponse>;
  stream?(
    messages: Message[],
    tools?: Tool[],
    onChunk?: (chunk: StreamChunk) => void
  ): Promise<ChatResponse>;
}
