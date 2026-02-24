/**
 * Configuration management for pkpdbuilder CLI
 * Author: Husain Z Attarwala, PhD
 */

import Conf from 'conf';
import { existsSync, mkdirSync, readFileSync, writeFileSync, chmodSync, unlinkSync } from 'fs';
import { homedir } from 'os';
import { join } from 'path';

export interface ProviderInfo {
  name: string;
  models: string[];
  default: string;
  env_key: string;
  auth_methods: string[];
  docs: string;
  local?: boolean;
}

export const PROVIDERS: Record<string, ProviderInfo> = {
  anthropic: {
    name: 'Anthropic (Claude)',
    models: [
      'claude-opus-4-6-20260220',
      'claude-sonnet-4-6-20260220',
      'claude-opus-4-5-20250514',
      'claude-sonnet-4-5-20250514',
      'claude-haiku-4-5-20250514',
    ],
    default: 'claude-sonnet-4-6-20260220',
    env_key: 'ANTHROPIC_API_KEY',
    auth_methods: ['api_key', 'oauth'],
    docs: 'https://console.anthropic.com/settings/keys',
  },
  openai: {
    name: 'OpenAI (GPT)',
    models: [
      'gpt-5.2',
      'gpt-5.1',
      'gpt-5',
      'gpt-5-mini',
      'gpt-5-nano',
      'gpt-4.1',
      'gpt-4.1-mini',
      'gpt-4.1-nano',
      'gpt-4o',
      'gpt-4o-mini',
      'o4-mini',
      'o3',
      'o3-pro',
      'o3-mini',
    ],
    default: 'gpt-5.2',
    env_key: 'OPENAI_API_KEY',
    auth_methods: ['api_key'],
    docs: 'https://platform.openai.com/api-keys',
  },
  google: {
    name: 'Google (Gemini)',
    models: [
      'gemini-3.1-pro-preview',
      'gemini-3-pro-preview',
      'gemini-3-flash-preview',
      'gemini-2.5-pro',
      'gemini-2.5-flash',
      'gemini-2.5-flash-lite',
      'gemini-2.0-flash',
      'gemini-2.0-flash-lite',
    ],
    default: 'gemini-2.5-flash',
    env_key: 'GOOGLE_API_KEY',
    auth_methods: ['api_key'],
    docs: 'https://aistudio.google.com/apikey',
  },
  ollama: {
    name: 'Ollama (Local)',
    models: ['llama3.3:70b', 'llama3.2:3b', 'qwen2.5:32b', 'mistral:7b'],
    default: 'llama3.3:70b',
    env_key: '',
    auth_methods: [],
    docs: 'https://ollama.ai',
    local: true,
  },
};

export interface PKPDConfig {
  provider: string;
  model: string;
  max_tokens: number;
  r_path: string;
  output_dir: string;
  pkpdbuilder_api: string;
  autonomy: 'full' | 'supervised' | 'ask';
  onboarded: boolean;
}

const DEFAULT_CONFIG: PKPDConfig = {
  provider: 'anthropic',
  model: 'claude-sonnet-4-5-20250514',
  max_tokens: 8192,
  r_path: 'Rscript',
  output_dir: './pkpdbuilder_output',
  pkpdbuilder_api: 'https://www.pkpdbuilder.com/api/v1',
  autonomy: 'full',
  onboarded: false,
};

const CONFIG_DIR = join(homedir(), '.pkpdbuilder');
const KEYS_FILE = join(CONFIG_DIR, 'keys.json');

// Use conf for main config
const configStore = new Conf({
  projectName: 'pkpdbuilder',
  cwd: CONFIG_DIR,
  defaults: DEFAULT_CONFIG as any,
}) as any;

/**
 * Get API key for provider. Lookup order:
 * 1. Environment variable
 * 2. keys.json file
 * 3. Legacy config
 */
export function getApiKey(provider?: string): string {
  const config = loadConfig();
  provider = provider || config.provider;
  const providerInfo = PROVIDERS[provider];

  if (!providerInfo) return '';

  // Ollama needs no key
  if (providerInfo.local) return 'ollama';

  // 1. Environment variable
  const envKey = providerInfo.env_key;
  if (envKey && process.env[envKey]) {
    return process.env[envKey]!;
  }

  // 2. Keys file
  if (existsSync(KEYS_FILE)) {
    try {
      const keys = JSON.parse(readFileSync(KEYS_FILE, 'utf-8'));
      if (keys[provider]) return keys[provider];
    } catch (e) {
      // Ignore parse errors
    }
  }

  // 3. Legacy: check if stored in main config
  const legacyKey = configStore.get('api_key' as any);
  if (legacyKey) return legacyKey as string;

  return '';
}

/**
 * Save API key to keys.json with restricted permissions
 */
export function saveApiKey(provider: string, key: string): void {
  if (!existsSync(CONFIG_DIR)) {
    mkdirSync(CONFIG_DIR, { recursive: true });
  }

  let keys: Record<string, string> = {};
  if (existsSync(KEYS_FILE)) {
    try {
      keys = JSON.parse(readFileSync(KEYS_FILE, 'utf-8'));
    } catch (e) {
      // Ignore parse errors, start fresh
    }
  }

  keys[provider] = key;
  writeFileSync(KEYS_FILE, JSON.stringify(keys, null, 2));

  // Restrict permissions (Unix only)
  try {
    chmodSync(KEYS_FILE, 0o600);
  } catch (e) {
    // Windows doesn't support chmod
  }
}

/**
 * Load config with environment overrides
 */
export function loadConfig(): PKPDConfig {
  const config: any = { ...DEFAULT_CONFIG };
  const store: any = configStore;

  // Load from conf store
  for (const key of Object.keys(DEFAULT_CONFIG)) {
    const val = store.get(key);
    if (val !== undefined) {
      config[key] = val;
    }
  }

  // Environment overrides
  if (process.env.PKPDBUILDER_PROVIDER) {
    config.provider = process.env.PKPDBUILDER_PROVIDER;
  }
  if (process.env.PKPDBUILDER_MODEL) {
    config.model = process.env.PKPDBUILDER_MODEL;
  }
  if (process.env.PKPDBUILDER_OUTPUT_DIR) {
    config.output_dir = process.env.PKPDBUILDER_OUTPUT_DIR;
  }

  return config;
}

/**
 * Save config to disk
 */
export function saveConfig(config: Partial<PKPDConfig>): void {
  const store: any = configStore;
  for (const [key, value] of Object.entries(config)) {
    if (key !== 'api_key') {
      // Don't save API keys in main config
      store.set(key, value);
    }
  }
}

/**
 * Ensure output directory exists
 */
export function ensureOutputDir(config: PKPDConfig): string {
  const dir = config.output_dir;
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
  return dir;
}

/**
 * Get config directory path
 */
export function getConfigDir(): string {
  return CONFIG_DIR;
}
