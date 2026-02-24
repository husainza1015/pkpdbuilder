/**
 * Configuration management for pkpdbuilder CLI
 * Author: Husain Z Attarwala, PhD
 */

import Conf from 'conf';
import { existsSync, mkdirSync } from 'fs';
import { homedir } from 'os';
import { join } from 'path';

export interface PKPDConfig {
  r_path: string;
  output_dir: string;
  pkpdbuilder_api: string;
}

const DEFAULT_CONFIG: PKPDConfig = {
  r_path: 'Rscript',
  output_dir: './pkpdbuilder_output',
  pkpdbuilder_api: 'https://www.pkpdbuilder.com/api/v1',
};

const CONFIG_DIR = join(homedir(), '.pkpdbuilder');

const configStore = new Conf({
  projectName: 'pkpdbuilder',
  cwd: CONFIG_DIR,
  defaults: DEFAULT_CONFIG as any,
}) as any;

/**
 * Load config with environment overrides
 */
export function loadConfig(): PKPDConfig {
  const config: any = { ...DEFAULT_CONFIG };
  const store: any = configStore;

  for (const key of Object.keys(DEFAULT_CONFIG)) {
    const val = store.get(key);
    if (val !== undefined) {
      config[key] = val;
    }
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
    store.set(key, value);
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
