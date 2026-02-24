/**
 * Configuration management for pkpdbuilder CLI
 * Author: Husain Z Attarwala, PhD
 */
import Conf from 'conf';
import { existsSync, mkdirSync } from 'fs';
import { homedir } from 'os';
import { join } from 'path';
const DEFAULT_CONFIG = {
    r_path: 'Rscript',
    output_dir: './pkpdbuilder_output',
    pkpdbuilder_api: 'https://www.pkpdbuilder.com/api/v1',
};
const CONFIG_DIR = join(homedir(), '.pkpdbuilder');
const configStore = new Conf({
    projectName: 'pkpdbuilder',
    cwd: CONFIG_DIR,
    defaults: DEFAULT_CONFIG,
});
/**
 * Load config with environment overrides
 */
export function loadConfig() {
    const config = { ...DEFAULT_CONFIG };
    const store = configStore;
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
export function saveConfig(config) {
    const store = configStore;
    for (const [key, value] of Object.entries(config)) {
        store.set(key, value);
    }
}
/**
 * Ensure output directory exists
 */
export function ensureOutputDir(config) {
    const dir = config.output_dir;
    if (!existsSync(dir)) {
        mkdirSync(dir, { recursive: true });
    }
    return dir;
}
/**
 * Get config directory path
 */
export function getConfigDir() {
    return CONFIG_DIR;
}
//# sourceMappingURL=config.js.map