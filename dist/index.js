#!/usr/bin/env node
/**
 * PKPDBuilder CLI — Claude Code wrapper for pharmacometrics
 * Author: Husain Z Attarwala, PhD
 */
import { Command } from 'commander';
import { printBanner } from './banner.js';
import { discoverR, scanForDatasets, checkProjectFiles } from './discovery.js';
import { existsSync, writeFileSync, readFileSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { spawnSync, execSync } from 'child_process';
import { platform, homedir } from 'os';
import chalk from 'chalk';
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const PACKAGE_ROOT = join(__dirname, '..');
const program = new Command();
program
    .name('pkpdbuilder')
    .description("The Pharmacometrician's Co-Pilot — powered by Claude Code")
    .version('0.3.0');
/**
 * Find claude CLI on the system
 */
function findClaude() {
    const isWindows = platform() === 'win32';
    const cmd = isWindows ? 'where' : 'which';
    try {
        const result = spawnSync(cmd, ['claude'], { encoding: 'utf-8', stdio: 'pipe' });
        if (result.status === 0 && result.stdout.trim()) {
            return result.stdout.trim().split('\n')[0].trim();
        }
    }
    catch (e) {
        // Not found via PATH
    }
    // Check common npm global paths on Windows
    if (isWindows) {
        const npmGlobal = join(homedir(), 'AppData', 'Roaming', 'npm', 'claude.cmd');
        if (existsSync(npmGlobal))
            return npmGlobal;
    }
    return null;
}
/**
 * Get the path to our MCP server entry point
 */
function getMcpServerPath() {
    return join(PACKAGE_ROOT, 'dist', 'mcp-server.js');
}
/**
 * Ensure .mcp.json exists in the project directory with our server
 * This is the most reliable way to configure MCP for Claude Code
 */
function ensureMcpJson() {
    const mcpJsonPath = join(process.cwd(), '.mcp.json');
    const serverPath = getMcpServerPath();
    const ourConfig = {
        command: 'node',
        args: [serverPath],
    };
    let config = { mcpServers: {} };
    // Read existing .mcp.json if present
    if (existsSync(mcpJsonPath)) {
        try {
            config = JSON.parse(readFileSync(mcpJsonPath, 'utf-8'));
            if (!config.mcpServers)
                config.mcpServers = {};
        }
        catch (e) {
            // Corrupted — overwrite
            config = { mcpServers: {} };
        }
    }
    // Add/update our server entry
    config.mcpServers.pkpdbuilder = ourConfig;
    writeFileSync(mcpJsonPath, JSON.stringify(config, null, 2) + '\n');
}
/**
 * Write CLAUDE.md with pharmacometrics instructions if not present
 */
function ensureClaudeMd() {
    const claudeMdPath = join(process.cwd(), 'CLAUDE.md');
    // Don't overwrite user's existing CLAUDE.md
    if (existsSync(claudeMdPath))
        return;
    // Use bundled CLAUDE.md if available
    const bundledPath = join(PACKAGE_ROOT, 'CLAUDE.md');
    if (existsSync(bundledPath)) {
        writeFileSync(claudeMdPath, readFileSync(bundledPath, 'utf-8'));
        return;
    }
    // Inline fallback
    writeFileSync(claudeMdPath, CLAUDE_MD_CONTENT);
}
/**
 * Ensure Claude Code has our MCP server whitelisted
 * Writes to ~/.claude/settings.json if needed
 */
function ensureMcpApproved() {
    const settingsDir = join(homedir(), '.claude');
    const settingsPath = join(settingsDir, 'settings.json');
    if (!existsSync(settingsDir)) {
        mkdirSync(settingsDir, { recursive: true });
    }
    let settings = {};
    if (existsSync(settingsPath)) {
        try {
            settings = JSON.parse(readFileSync(settingsPath, 'utf-8'));
        }
        catch (e) {
            settings = {};
        }
    }
    // Enable our MCP server from .mcp.json
    if (!settings.enabledMcpjsonServers) {
        settings.enabledMcpjsonServers = [];
    }
    if (!settings.enabledMcpjsonServers.includes('pkpdbuilder')) {
        settings.enabledMcpjsonServers.push('pkpdbuilder');
        writeFileSync(settingsPath, JSON.stringify(settings, null, 2) + '\n');
    }
}
// ── Default: launch Claude Code with PMx tools ──────────────
program.action(async () => {
    printBanner();
    // Check for Claude Code
    const claudePath = findClaude();
    if (!claudePath) {
        console.log(chalk.red('  ✗ Claude Code CLI not found\n'));
        console.log(chalk.white('  Install it first:'));
        console.log(chalk.cyan('    npm install -g @anthropic-ai/claude-code\n'));
        console.log(chalk.dim('  Then run `pkpdbuilder` again.'));
        console.log('');
        process.exit(1);
    }
    console.log(chalk.green('  ✓ Claude Code found'));
    // Check MCP server is built
    const serverPath = getMcpServerPath();
    if (!existsSync(serverPath)) {
        console.log(chalk.red('  ✗ MCP server not found'));
        console.log(chalk.dim('    Run: cd <pkpdbuilder-dir> && npm run build'));
        process.exit(1);
    }
    console.log(chalk.green('  ✓ MCP server ready'));
    // Check R
    const r = discoverR();
    if (r.found) {
        console.log(chalk.green(`  ✓ R ${r.version}`));
        const pkgs = Object.entries(r.packages)
            .filter(([, v]) => v)
            .map(([k]) => k);
        if (pkgs.length > 0) {
            console.log(chalk.dim(`    Packages: ${pkgs.join(', ')}`));
        }
        const missing = Object.entries(r.packages)
            .filter(([, v]) => !v)
            .map(([k]) => k);
        if (missing.length > 0) {
            console.log(chalk.yellow(`    Missing: ${missing.join(', ')}`));
        }
    }
    else {
        console.log(chalk.yellow("  ⚠ R not found (modeling tools won't work)"));
        console.log(chalk.dim('    Install from https://cran.r-project.org/'));
    }
    // Check datasets
    const datasets = scanForDatasets();
    if (datasets.length > 0) {
        console.log(chalk.green(`  ✓ ${datasets.length} dataset(s) in current directory`));
    }
    // Check project memory
    const projFiles = checkProjectFiles();
    if (projFiles.memory) {
        console.log(chalk.green('  ✓ Project memory found'));
    }
    console.log('');
    // Setup MCP: write .mcp.json and approve in settings
    ensureMcpJson();
    ensureMcpApproved();
    // Ensure CLAUDE.md exists
    ensureClaudeMd();
    console.log(chalk.dim('  Starting Claude Code with pharmacometrics tools...\n'));
    // Launch Claude Code
    const result = spawnSync(claudePath, [], {
        stdio: 'inherit',
        cwd: process.cwd(),
        env: { ...process.env },
    });
    process.exit(result.status ?? 0);
});
// ── Doctor: environment check ───────────────────────────────
program
    .command('doctor')
    .description('Check environment and dependencies')
    .action(async () => {
    printBanner('Environment Check');
    // Claude Code
    const claudePath = findClaude();
    if (claudePath) {
        console.log(chalk.green(`  ✓ Claude Code at ${claudePath}`));
        try {
            const ver = execSync(`"${claudePath}" --version 2>&1`, { encoding: 'utf-8' }).trim();
            console.log(chalk.dim(`    Version: ${ver}`));
        }
        catch (e) {
            // Version check failed
        }
    }
    else {
        console.log(chalk.red('  ✗ Claude Code not found'));
        console.log(chalk.dim('    npm install -g @anthropic-ai/claude-code'));
    }
    // MCP server
    const serverPath = getMcpServerPath();
    if (existsSync(serverPath)) {
        console.log(chalk.green('  ✓ MCP server built'));
    }
    else {
        console.log(chalk.red('  ✗ MCP server not found'));
    }
    // R
    const r = discoverR();
    if (r.found) {
        console.log(chalk.green(`  ✓ R ${r.version} at ${r.path}`));
        console.log(chalk.bold('\n  R Packages:'));
        Object.entries(r.packages).forEach(([pkg, installed]) => {
            if (installed) {
                console.log(chalk.green(`    ✓ ${pkg}`));
            }
            else {
                console.log(chalk.yellow(`    ✗ ${pkg}`));
            }
        });
    }
    else {
        console.log(chalk.red('  ✗ R not found'));
        console.log(chalk.dim('    https://cran.r-project.org/'));
    }
    // Datasets
    const datasets = scanForDatasets();
    if (datasets.length > 0) {
        console.log(chalk.bold('\n  Datasets:'));
        datasets.slice(0, 10).forEach((d) => {
            console.log(chalk.cyan(`    ${d.name} (${(d.size / 1024).toFixed(1)} KB)`));
        });
        if (datasets.length > 10) {
            console.log(chalk.dim(`    ... and ${datasets.length - 10} more`));
        }
    }
    // .mcp.json
    const mcpJsonPath = join(process.cwd(), '.mcp.json');
    if (existsSync(mcpJsonPath)) {
        try {
            const cfg = JSON.parse(readFileSync(mcpJsonPath, 'utf-8'));
            if (cfg.mcpServers?.pkpdbuilder) {
                console.log(chalk.green('\n  ✓ .mcp.json configured'));
            }
            else {
                console.log(chalk.yellow('\n  ⚠ .mcp.json exists but pkpdbuilder not configured'));
            }
        }
        catch (e) {
            console.log(chalk.red('\n  ✗ .mcp.json is invalid'));
        }
    }
    else {
        console.log(chalk.dim('\n  - No .mcp.json (will be created on first run)'));
    }
    console.log('');
});
// ── Tools: list available tools ─────────────────────────────
program
    .command('tools')
    .description('List all pharmacometrics tools exposed via MCP')
    .action(() => {
    console.log(chalk.bold.cyan('\n  PKPDBuilder Tools (MCP)\n'));
    const categories = {
        Data: ['load_dataset', 'summarize_dataset', 'plot_data', 'dataset_qc', 'handle_blq'],
        Modeling: ['fit_model', 'fit_from_library', 'compare_models', 'list_model_library', 'get_model_code'],
        Diagnostics: ['goodness_of_fit', 'vpc', 'eta_plots', 'individual_fits', 'parameter_table'],
        NCA: ['run_nca'],
        Simulation: ['simulate_regimen', 'population_simulation'],
        Literature: ['search_pubmed', 'lookup_drug'],
        Covariate: ['covariate_screening', 'stepwise_covariate_model', 'forest_plot'],
        'Export/Import': ['export_model', 'import_model', 'list_backends'],
        Reports: ['generate_report', 'build_shiny_app', 'generate_beamer_slides'],
        Memory: ['pkpd_memory_read', 'pkpd_memory_write', 'pkpd_memory_search', 'init_pkpd_project'],
    };
    let total = 0;
    Object.entries(categories).forEach(([category, tools]) => {
        console.log(chalk.bold(`  ${category}:`));
        tools.forEach((tool) => {
            console.log(chalk.cyan(`    • ${tool}`));
            total++;
        });
        console.log('');
    });
    console.log(chalk.dim(`  ${total} tools available via MCP\n`));
});
// ── MCP config: print config for manual use ─────────────────
program
    .command('mcp-config')
    .description('Print MCP server configuration (for manual Claude Code setup)')
    .action(() => {
    const config = {
        mcpServers: {
            pkpdbuilder: {
                command: 'node',
                args: [getMcpServerPath()],
            },
        },
    };
    console.log(JSON.stringify(config, null, 2));
});
// ── Setup: register MCP server with Claude Code ─────────────
program
    .command('setup')
    .description('Register PKPDBuilder MCP server with Claude Code')
    .action(async () => {
    printBanner('Setup');
    const claudePath = findClaude();
    if (!claudePath) {
        console.log(chalk.red('  ✗ Claude Code not installed'));
        console.log(chalk.dim('    npm install -g @anthropic-ai/claude-code'));
        process.exit(1);
    }
    const serverPath = getMcpServerPath();
    if (!existsSync(serverPath)) {
        console.log(chalk.red('  ✗ MCP server not built'));
        process.exit(1);
    }
    // Method 1: Register via claude mcp add (user scope)
    console.log(chalk.dim('  Registering MCP server with Claude Code...'));
    try {
        const result = spawnSync(claudePath, [
            'mcp', 'add', 'pkpdbuilder',
            '--transport', 'stdio',
            '--scope', 'user',
            '--',
            'node', serverPath,
        ], {
            encoding: 'utf-8',
            stdio: 'pipe',
        });
        if (result.status === 0) {
            console.log(chalk.green('  ✓ MCP server registered (user scope)'));
        }
        else {
            console.log(chalk.yellow('  ⚠ claude mcp add failed, using .mcp.json fallback'));
        }
    }
    catch (e) {
        console.log(chalk.yellow('  ⚠ claude mcp add failed, using .mcp.json fallback'));
    }
    // Method 2: Also ensure .mcp.json and settings approval
    ensureMcpJson();
    ensureMcpApproved();
    console.log(chalk.green('  ✓ .mcp.json configured'));
    console.log(chalk.green('  ✓ MCP server approved in settings'));
    console.log(chalk.green('\n  Setup complete! Run `pkpdbuilder` to start.\n'));
});
program.parse();
// ── Inline CLAUDE.md content ────────────────────────────────
const CLAUDE_MD_CONTENT = `# CLAUDE.md — PKPDBuilder

You are a pharmacometrics co-pilot. You have access to specialized PKPDBuilder MCP tools for population PK/PD analysis.

## Available Tools (via MCP)

- **Data:** load_dataset, summarize_dataset, plot_data, dataset_qc, handle_blq
- **Modeling:** fit_model, fit_from_library, compare_models, list_model_library, get_model_code
- **Diagnostics:** goodness_of_fit, vpc, eta_plots, individual_fits, parameter_table
- **NCA:** run_nca
- **Simulation:** simulate_regimen, population_simulation
- **Literature:** search_pubmed, lookup_drug
- **Covariate:** covariate_screening, stepwise_covariate_model, forest_plot
- **Export:** export_model, import_model, list_backends
- **Reports:** generate_report, build_shiny_app, generate_beamer_slides
- **Memory:** pkpd_memory_read, pkpd_memory_write, pkpd_memory_search, init_pkpd_project

## Operating Mode: Autonomous

Run autonomously. When given a task:
1. Do the full analysis without stopping to ask permission at each step
2. Make sensible default choices (start simple, compare models, pick the best)
3. Only pause to ask if there is genuine ambiguity

## Standard PopPK Workflow

When asked to "analyze" or "run PopPK analysis":
1. load_dataset → summarize_dataset → plot_data
2. run_nca (initial parameter estimates)
3. fit_model (1-CMT) → fit_model (2-CMT)
4. compare_models → select best
5. goodness_of_fit → vpc → eta_plots
6. covariate_screening → stepwise_covariate_model (if significant)
7. parameter_table → generate_report
8. pkpd_memory_write (log decisions and model history)

## Key Conventions

- Use pharmacometrics terminology correctly
- Present parameter tables in readable format
- Always state model recommendation with reasoning
- Flag concerns: high RSE (>50%), large shrinkage (>30%), convergence issues
- At session start, call pkpd_memory_read to restore project context
- After key decisions, call pkpd_memory_write to log them
`;
//# sourceMappingURL=index.js.map