/**
 * Project memory management tools
 * Author: Husain Z Attarwala, PhD
 */
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs';
import { join } from 'path';
export const memoryReadTool = {
    name: 'memory_read',
    description: 'Read project memory to restore context from previous sessions.',
    input_schema: {
        type: 'object',
        properties: {},
        required: [],
    },
};
export async function memoryRead() {
    const memoryPath = join(process.cwd(), '.pkpdbuilder', 'memory.json');
    if (!existsSync(memoryPath)) {
        return { success: true, message: 'No project memory found', memory: {} };
    }
    try {
        const data = JSON.parse(readFileSync(memoryPath, 'utf-8'));
        return { success: true, memory: data };
    }
    catch (e) {
        return { success: false, error: e.message };
    }
}
export const memoryWriteTool = {
    name: 'memory_write',
    description: 'Write key information to project memory for future sessions.',
    input_schema: {
        type: 'object',
        properties: {
            key: { type: 'string', description: 'Memory key' },
            value: { type: 'string', description: 'Value to store' },
        },
        required: ['key', 'value'],
    },
};
export async function memoryWrite(args) {
    const memoryDir = join(process.cwd(), '.pkpdbuilder');
    const memoryPath = join(memoryDir, 'memory.json');
    if (!existsSync(memoryDir)) {
        mkdirSync(memoryDir, { recursive: true });
    }
    let memory = {};
    if (existsSync(memoryPath)) {
        try {
            memory = JSON.parse(readFileSync(memoryPath, 'utf-8'));
        }
        catch (e) {
            // Start fresh if corrupted
        }
    }
    memory[args.key] = args.value;
    writeFileSync(memoryPath, JSON.stringify(memory, null, 2));
    return { success: true, message: `Stored: ${args.key}` };
}
export const memorySearchTool = {
    name: 'memory_search',
    description: 'Search project memory for specific information.',
    input_schema: {
        type: 'object',
        properties: {
            query: { type: 'string', description: 'Search query' },
        },
        required: ['query'],
    },
};
export async function memorySearch(args) {
    const { memory } = (await memoryRead());
    const results = Object.entries(memory || {}).filter(([k, v]) => String(k).toLowerCase().includes(args.query.toLowerCase()) ||
        String(v).toLowerCase().includes(args.query.toLowerCase()));
    return { success: true, results: Object.fromEntries(results) };
}
export const initProjectTool = {
    name: 'init_project',
    description: 'Initialize a new PKPD project with memory and directory structure.',
    input_schema: {
        type: 'object',
        properties: {
            project_name: { type: 'string' },
            drug_name: { type: 'string' },
        },
        required: [],
    },
};
export async function initProject(args) {
    const projectDir = join(process.cwd(), '.pkpdbuilder');
    if (!existsSync(projectDir)) {
        mkdirSync(projectDir, { recursive: true });
    }
    await memoryWrite({
        key: 'project_name',
        value: args.project_name || 'Unnamed Project',
    });
    if (args.drug_name) {
        await memoryWrite({ key: 'drug_name', value: args.drug_name });
    }
    return { success: true, message: 'Project initialized', project_dir: projectDir };
}
//# sourceMappingURL=memory.js.map