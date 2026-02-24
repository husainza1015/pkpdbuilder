/**
 * Model library index
 * Author: Husain Z Attarwala, PhD
 */
import { existsSync, readFileSync, readdirSync } from 'fs';
import { join, extname } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const modelCache = new Map();
/**
 * Load all model definitions from JSON files
 */
export function loadAllModels() {
    const models = [];
    const categories = ['pk', 'pd', 'pkpd', 'tmdd', 'advanced'];
    for (const category of categories) {
        const categoryPath = join(__dirname, category);
        if (!existsSync(categoryPath))
            continue;
        const files = readdirSync(categoryPath).filter(f => extname(f) === '.json');
        for (const file of files) {
            try {
                const filePath = join(categoryPath, file);
                const content = readFileSync(filePath, 'utf-8');
                const model = JSON.parse(content);
                models.push(model);
                modelCache.set(model.name, model);
            }
            catch (e) {
                console.error(`Failed to load model ${file}: ${e}`);
            }
        }
    }
    return models;
}
/**
 * Get a specific model by name
 */
export function getModel(name) {
    if (modelCache.size === 0) {
        loadAllModels();
    }
    return modelCache.get(name) || null;
}
/**
 * List models by category
 */
export function listModelsByCategory(category) {
    if (modelCache.size === 0) {
        loadAllModels();
    }
    const allModels = Array.from(modelCache.values());
    if (category) {
        return allModels.filter(m => m.category === category);
    }
    return allModels;
}
//# sourceMappingURL=index.js.map