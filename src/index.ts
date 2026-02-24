#!/usr/bin/env node
/**
 * PKPDBuilder CLI — Claude Code wrapper for pharmacometrics
 * Author: Husain Z Attarwala, PhD
 */

import { Command } from 'commander';
import { printBanner } from './banner.js';
import { discoverR, scanForDatasets, checkProjectFiles } from './discovery.js';
import { existsSync, writeFileSync, mkdirSync, readFileSync } from 'fs';
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
function findClaude(): string | null {
  const isWindows = platform() === 'win32';
  const cmd = isWindows ? 'where' : 'which';

  try {
    const result = spawnSync(cmd, ['claude'], { encoding: 'utf-8', stdio: 'pipe' });
    if (result.status === 0 && result.stdout.trim()) {
      return result.stdout.trim().split('\n')[0];
    }
  } catch (e) {
    // Not found
  }

  // Check common npm global paths on Windows
  if (isWindows) {
    const npmGlobal = join(homedir(), 'AppData', 'Roaming', 'npm', 'claude.cmd');
    if (existsSync(npmGlobal)) return npmGlobal;
  }

  return null;
}

/**
 * Write CLAUDE.md with pharmacometrics system prompt into cwd
 */
function ensureClaudeMd(): void {
  const claudeMdPath = join(process.cwd(), 'CLAUDE.md');
  
  // Check if our bundled CLAUDE.md exists
  const bundledPath = join(PACKAGE_ROOT, 'CLAUDE.md');
  if (existsSync(bundledPath)) {
    // Only write if not already present or if ours is newer
    if (!existsSync(claudeMdPath)) {
      writeFileSync(claudeMdPath, readFileSync(bundledPath, 'utf-8'));
    }
    return;
  }

  // Inline fallback
  if (!existsSync(claudeMdPath)) {
    writeFileSync(claudeMdPath, CLAUDE_MD_CONTENT);
  }
}

/**
 * Generate MCP config pointing to our server
 */
function getMcpConfig(): object {
  const serverPath = join(PACKAGE_ROOT, 'dist', 'mcp-server.js');
  
  return {
    mcpServers: {
      pkpdbuilder: {
        command: 'node',
        args: [serverPath],
      },
    },
  };
}

/**
 * Write MCP config to temp file and return path
 */
function writeMcpConfig(): string {
  const configDir = join(homedir(), '.pkpdbuilder');
  if (!existsSync(configDir)) {
    mkdirSync(configDir, { recursive: true });
  }

  const configPath = join(configDir, 'mcp-config.json');
  writeFileSync(configPath, JSON.stringify(getMcpConfig(), null, 2));
  return configPath;
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
  } else {
    console.log(chalk.yellow('  ⚠ R not found (modeling tools won\'t work)'));
  }

  // Check datasets
  const datasets = scanForDatasets();
  if (datasets.length > 0) {
    console.log(chalk.green(`  ✓ ${datasets.length} dataset(s) found`));
  }

  // Check project memory
  const projFiles = checkProjectFiles();
  if (projFiles.memory) {
    console.log(chalk.green('  ✓ Project memory found'));
  }

  console.log('');

  // Ensure CLAUDE.md exists in cwd
  ensureClaudeMd();

  // Write MCP config
  const mcpConfigPath = writeMcpConfig();

  // Launch Claude Code with our MCP server
  console.log(chalk.dim('  Launching Claude Code with pharmacometrics tools...\n'));

  const result = spawnSync(claudePath, ['--mcp-config', mcpConfigPath], {
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
      } catch (e) {
        // Version check failed, that's ok
      }
    } else {
      console.log(chalk.red('  ✗ Claude Code not found'));
      console.log(chalk.dim('    npm install -g @anthropic-ai/claude-code'));
    }

    // R
    const r = discoverR();
    if (r.found) {
      console.log(chalk.green(`  ✓ R ${r.version} at ${r.path}`));
      console.log(chalk.bold('\n  R Packages:'));
      Object.entries(r.packages).forEach(([pkg, installed]) => {
        if (installed) {
          console.log(chalk.green(`    ✓ ${pkg}`));
        } else {
          console.log(chalk.yellow(`    ✗ ${pkg}`));
        }
      });
    } else {
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

    // MCP server
    const serverPath = join(PACKAGE_ROOT, 'dist', 'mcp-server.js');
    if (existsSync(serverPath)) {
      console.log(chalk.green('\n  ✓ MCP server built'));
    } else {
      console.log(chalk.red('\n  ✗ MCP server not found (run npm run build)'));
    }

    console.log('');
  });

// ── Tools: list available tools ─────────────────────────────

program
  .command('tools')
  .description('List all pharmacometrics tools exposed via MCP')
  .action(() => {
    console.log(chalk.bold.cyan('\n  PKPDBuilder Tools (MCP)\n'));

    const categories: Record<string, string[]> = {
      Data: ['load_dataset', 'summarize_dataset', 'plot_data', 'dataset_qc', 'handle_blq'],
      Modeling: ['fit_model', 'fit_from_library', 'compare_models', 'list_model_library', 'get_model_code'],
      Diagnostics: ['goodness_of_fit', 'vpc', 'eta_plots', 'individual_fits', 'parameter_table'],
      NCA: ['run_nca'],
      Simulation: ['simulate_regimen', 'population_simulation'],
      Literature: ['search_pubmed', 'lookup_drug'],
      Covariate: ['covariate_screening', 'stepwise_covariate_model', 'forest_plot'],
      'Export/Import': ['export_model', 'import_model', 'list_backends'],
      Reports: ['generate_report', 'build_shiny_app', 'generate_beamer_slides'],
      Memory: ['memory_read', 'memory_write', 'memory_search', 'init_project'],
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
    const config = getMcpConfig();
    console.log(JSON.stringify(config, null, 2));
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
- **Memory:** memory_read, memory_write, memory_search, init_project

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
8. memory_write (log decisions and model history)

## Key Conventions

- Use pharmacometrics terminology correctly
- Present parameter tables in readable format
- Always state model recommendation with reasoning
- Flag concerns: high RSE (>50%), large shrinkage (>30%), convergence issues
- At session start, call memory_read to restore project context
- After key decisions, call memory_write to log them
`;
