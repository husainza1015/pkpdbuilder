/**
 * Model library — 59 pre-built PK/PD models
 * Author: Husain Z Attarwala, PhD
 */

import { existsSync, readFileSync, readdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MODELS_DIR = join(__dirname, '..', 'models');

interface ModelDef {
  name: string;
  category: string;
  description: string;
  monolix_equivalent?: string;
  code: string;
}

let modelCache: Map<string, ModelDef> | null = null;

function loadModels(): Map<string, ModelDef> {
  if (modelCache) return modelCache;
  modelCache = new Map();

  const categories = ['pk', 'pd', 'pkpd', 'tmdd', 'advanced'];
  for (const cat of categories) {
    const catDir = join(MODELS_DIR, cat);
    if (!existsSync(catDir)) continue;

    const files = readdirSync(catDir).filter(f => f.endsWith('.json'));
    for (const file of files) {
      try {
        const model: ModelDef = JSON.parse(readFileSync(join(catDir, file), 'utf-8'));
        model.category = cat;
        modelCache.set(model.name, model);
      } catch {}
    }
  }

  return modelCache;
}

export function getModelLibrary(category: string = 'all'): any {
  const models = loadModels();
  const list: any[] = [];

  for (const [_, model] of models) {
    if (category !== 'all' && model.category !== category) continue;
    list.push({
      name: model.name,
      category: model.category,
      description: model.description,
      monolix_equivalent: model.monolix_equivalent,
    });
  }

  const counts: Record<string, number> = {};
  for (const m of list) {
    counts[m.category] = (counts[m.category] || 0) + 1;
  }

  return {
    success: true,
    total: list.length,
    categories: counts,
    models: list,
  };
}

export function getModelCode(modelName: string): any {
  const models = loadModels();
  const model = models.get(modelName);

  if (!model) {
    const available = [...models.keys()].filter(k => k.includes(modelName.replace('pk_', '').replace('pd_', '')));
    return {
      success: false,
      error: `Model '${modelName}' not found.${available.length > 0 ? ` Did you mean: ${available.join(', ')}` : ''}`,
    };
  }

  return {
    success: true,
    name: model.name,
    category: model.category,
    description: model.description,
    code: model.code,
  };
}
