/**
 * Provider registry and factory
 * Author: Husain Z Attarwala, PhD
 */

import { Provider, ProviderOptions } from './base.js';
import { AnthropicProvider } from './anthropic.js';
import { OpenAIProvider } from './openai.js';
import { GoogleProvider } from './google.js';
import { OllamaProvider } from './ollama.js';

export * from './base.js';
export { AnthropicProvider } from './anthropic.js';
export { OpenAIProvider } from './openai.js';
export { GoogleProvider } from './google.js';
export { OllamaProvider } from './ollama.js';

export function createProvider(providerName: string, options: ProviderOptions): Provider {
  switch (providerName) {
    case 'anthropic':
      return new AnthropicProvider(options);
    case 'openai':
      return new OpenAIProvider(options);
    case 'google':
      return new GoogleProvider(options);
    case 'ollama':
      return new OllamaProvider(options);
    default:
      throw new Error(`Unknown provider: ${providerName}`);
  }
}
