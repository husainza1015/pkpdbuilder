#!/usr/bin/env node
/**
 * PKPDBuilder CLI — wraps Claude Code with pharmacometric MCP tools
 * Author: Husain Z Attarwala, PhD
 */

import { Command } from 'commander';
import { existsSync, writeFileSync, mkdirSync, readFileSync } from 'fs';
import { join, dirname } from 'path';
import { execSync, spawn } from 'child_process';
import { homedir } from 'os';
import chalk from 'chalk';
import { fileURLToPath } from 'url';
import { findRscript } from './r-bridge.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PACKAGE_ROOT = join(__dirname, '..');
const VERSION = '0.3.0';

const program = new Command();

program
  .name('pkpdbuilder')
  .description('The Pharmacometrician\'s Co-Pilot — Claude Code + pharmacometric MCP tools')
  .version(VERSION);

// ── Main command: launch Claude Code with MCP ──────────

program
  .command('start', { isDefault: true })
  .description('Launch Claude Code with pharmacometric tools')
  .action(async () => {
    printBanner();

    // Check Claude Code is installed
    if (!hasClaude()) {
      console.log(chalk.red('\n  Claude Code not found.'));
      console.log(chalk.dim('  Install: npm install -g @anthropic-ai/claude-code'));
      console.log(chalk.dim('  Then:    claude login\n'));
      process.exit(1);
    }

    // Check R environment
    checkR();

    // Ensure MCP config exists
    ensureMcpConfig();

    // Ensure CLAUDE.md exists in cwd
    ensureClaudeMd();

    console.log(chalk.green('\n  ✓ Launching Claude Code with pharmacometric tools...\n'));

    // Launch Claude Code
    const claude = spawn('claude', [], {
      stdio: 'inherit',
      cwd: process.cwd(),
    });

    claude.on('exit', (code) => process.exit(code || 0));
  });

// ── Init command: scaffold project ─────────────────────

program
  .command('init')
  .description('Initialize a pharmacometrics project in the current directory')
  .argument('[drug]', 'Drug name for the project')
  .action((drug?: string) => {
    printBanner();
    ensureClaudeMd(drug);
    ensureMcpConfig();

    // Create output directory
    const outDir = join(process.cwd(), 'pkpdbuilder_output');
    if (!existsSync(outDir)) {
      mkdirSync(outDir, { recursive: true });
      console.log(chalk.green('  ✓ Created pkpdbuilder_output/'));
    }

    // Create MEMORY.md
    const memFile = join(process.cwd(), 'MEMORY.md');
    if (!existsSync(memFile)) {
      writeFileSync(memFile, `# Project Memory\n\n## Drug: ${drug || 'TBD'}\n\n## Key Decisions\n\n## Model History\n`);
      console.log(chalk.green('  ✓ Created MEMORY.md'));
    }

    console.log(chalk.green('\n  Project initialized! Run `pkpdbuilder` to start.\n'));
  });

// ── Doctor command: check environment ──────────────────

program
  .command('doctor')
  .description('Check environment: Claude Code, R, packages')
  .action(() => {
    printBanner();
    console.log(chalk.bold('  Environment Check'));
    console.log(chalk.dim('  ─────────────────\n'));

    // Claude Code
    if (hasClaude()) {
      try {
        const ver = execSync('claude --version', { encoding: 'utf-8' }).trim();
        console.log(chalk.green(`  ✓ Claude Code ${ver}`));
      } catch {
        console.log(chalk.green('  ✓ Claude Code installed'));
      }
    } else {
      console.log(chalk.red('  ✗ Claude Code not found'));
      console.log(chalk.dim('    npm install -g @anthropic-ai/claude-code'));
    }

    // R
    checkR();

    // MCP config
    const mcpPath = getMcpConfigPath();
    if (existsSync(mcpPath)) {
      console.log(chalk.green(`  ✓ MCP config at ${mcpPath}`));
    } else {
      console.log(chalk.yellow('  ○ MCP not configured (run pkpdbuilder to auto-configure)'));
    }

    // CLAUDE.md
    if (existsSync(join(process.cwd(), 'CLAUDE.md'))) {
      console.log(chalk.green('  ✓ CLAUDE.md found in project'));
    } else {
      console.log(chalk.yellow('  ○ No CLAUDE.md (run pkpdbuilder init)'));
    }

    console.log('');
  });

// ── Helpers ────────────────────────────────────────────

function hasClaude(): boolean {
  try {
    execSync('claude --version', { stdio: 'pipe' });
    return true;
  } catch {
    return false;
  }
}

function checkR(): void {
  try {
    const rPath = findRscript();
    console.log(chalk.green(`  ✓ R found at ${rPath}`));

    // Check packages
    const result = execSync(
      `"${rPath}" -e "pkgs <- c('nlmixr2','mrgsolve','PKNCA','ggplot2'); installed <- sapply(pkgs, requireNamespace, quietly=TRUE); cat(paste(pkgs, installed, sep='=', collapse=';'))"`,
      { encoding: 'utf-8', timeout: 15000 }
    ).trim();

    const pairs = result.split(';');
    for (const pair of pairs) {
      const [pkg, status] = pair.split('=');
      if (status === 'TRUE') {
        console.log(chalk.green(`    ✓ ${pkg}`));
      } else {
        console.log(chalk.yellow(`    ✗ ${pkg} (install.packages("${pkg}"))`));
      }
    }
  } catch (err: any) {
    console.log(chalk.yellow('  ✗ R not found — R tools will be unavailable'));
    console.log(chalk.dim('    Install from https://cran.r-project.org'));
  }
}

function getMcpConfigPath(): string {
  // Claude Code MCP config location
  const home = homedir();
  if (process.platform === 'win32') {
    return join(home, '.claude', 'claude_desktop_config.json');
  }
  return join(home, '.claude', 'claude_desktop_config.json');
}

function ensureMcpConfig(): void {
  const configPath = getMcpConfigPath();
  const configDir = dirname(configPath);

  if (!existsSync(configDir)) {
    mkdirSync(configDir, { recursive: true });
  }

  let config: any = {};
  if (existsSync(configPath)) {
    try {
      config = JSON.parse(readFileSync(configPath, 'utf-8'));
    } catch {}
  }

  if (!config.mcpServers) config.mcpServers = {};

  // Add/update pkpdbuilder MCP server
  const serverPath = join(PACKAGE_ROOT, 'dist', 'server.js');
  config.mcpServers['pkpdbuilder'] = {
    command: 'node',
    args: [serverPath],
  };

  writeFileSync(configPath, JSON.stringify(config, null, 2));
  console.log(chalk.green('  ✓ MCP server configured'));
}

function ensureClaudeMd(drug?: string): void {
  const claudeMd = join(process.cwd(), 'CLAUDE.md');
  if (existsSync(claudeMd)) {
    console.log(chalk.dim('  ○ CLAUDE.md already exists'));
    return;
  }

  const content = `# PKPDBuilder — Pharmacometrics Co-Pilot

You are a pharmacometrics expert assistant. You have access to specialized MCP tools for population PK/PD analysis via the \`pkpdbuilder\` MCP server.

## Available Tools

### Data
- \`load_dataset\` — Load CSV/NONMEM datasets, validates ID/TIME/DV columns
- \`summarize_dataset\` — Subject counts, covariate distributions, dosing summary
- \`plot_data\` — Spaghetti plots, individual profiles, dose-normalized
- \`dataset_qc\` — Quality checks (missing values, duplicates, BLQ)
- \`handle_blq\` — Handle BLQ data (M1-M7 methods)

### Modeling
- \`fit_model\` — Fit PopPK models via nlmixr2 (1/2/3-CMT, oral/IV, SAEM/FOCEI)
- \`fit_from_library\` — Fit pre-built models from the 59-model library
- \`compare_models\` — Compare fits by OFV/AIC/BIC
- \`list_model_library\` — Browse all available models
- \`get_model_code\` — View nlmixr2 R code for any library model

### Diagnostics
- \`goodness_of_fit\` — DV vs PRED/IPRED, CWRES plots
- \`vpc\` — Visual Predictive Check
- \`eta_plots\` — ETA distributions, ETA vs covariates
- \`individual_fits\` — Per-subject observed vs predicted
- \`parameter_table\` — Formatted parameter estimates with RSE/shrinkage

### Analysis
- \`run_nca\` — Non-compartmental analysis (PKNCA)
- \`simulate_regimen\` — Dosing simulations via mrgsolve
- \`population_simulation\` — Virtual population with IIV
- \`covariate_screening\` — Univariate covariate analysis
- \`stepwise_covariate_model\` — Forward addition/backward elimination
- \`forest_plot\` — Covariate effect forest plots

### Literature
- \`search_pubmed\` — Search PubMed for PK/PD publications
- \`lookup_drug\` — Look up published PK parameters

### Export & Reports
- \`export_model\` — Export to NONMEM/Monolix/Pumas format
- \`import_model\` — Import from NONMEM/Monolix
- \`generate_report\` — HTML PopPK analysis report
- \`build_shiny_app\` — Interactive R Shiny simulator

## Workflow
Standard pharmacometric workflow:
1. Load and QC the dataset
2. Explore data visually
3. Run NCA for initial parameter estimates
4. Fit base structural model (start simple: 1-CMT → 2-CMT)
5. Compare models, select best by BIC
6. Covariate screening → stepwise covariate model
7. Generate diagnostics (GOF, VPC, ETAs)
8. Export final model + generate report

## Guidelines
- Always check data quality before fitting
- Start with simpler models before complex ones
- Report parameter estimates with RSE and shrinkage
- Use VPC as the primary model evaluation tool
- Check all NONMEM conventions (EVID, CMT, MDV) when loading data
${drug ? `\n## Drug: ${drug}\n` : ''}
`;

  writeFileSync(claudeMd, content);
  console.log(chalk.green('  ✓ Created CLAUDE.md'));
}

function printBanner(): void {
  const violet = chalk.rgb(168, 85, 247);
  const indigo = chalk.rgb(99, 102, 241);
  const cyan = chalk.rgb(6, 182, 212);

  console.log('');
  console.log(violet('  ██████╗ ██╗  ██╗██████╗ ██████╗ '));
  console.log(violet('  ██╔══██╗██║ ██╔╝██╔══██╗██╔══██╗'));
  console.log(indigo('  ██████╔╝█████╔╝ ██████╔╝██║  ██║'));
  console.log(indigo('  ██╔═══╝ ██╔═██╗ ██╔═══╝ ██║  ██║'));
  console.log(cyan('  ██║     ██║  ██╗██║     ██████╔╝'));
  console.log(cyan('  ╚═╝     ╚═╝  ╚═╝╚═╝     ╚═════╝ '));
  console.log(violet('  ██████╗ ██╗   ██╗██╗██╗     ██████╗ ███████╗██████╗ '));
  console.log(violet('  ██╔══██╗██║   ██║██║██║     ██╔══██╗██╔════╝██╔══██╗'));
  console.log(indigo('  ██████╔╝██║   ██║██║██║     ██║  ██║█████╗  ██████╔╝'));
  console.log(indigo('  ██╔══██╗██║   ██║██║██║     ██║  ██║██╔══╝  ██╔══██╗'));
  console.log(cyan('  ██████╔╝╚██████╔╝██║███████╗██████╔╝███████╗██║  ██║'));
  console.log(cyan('  ╚═════╝  ╚═════╝ ╚═╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝'));
  console.log('');
  console.log(chalk.dim(`  The Pharmacometrician's Co-Pilot • v${VERSION}`));
  console.log(chalk.dim('  Developer: Husain Z Attarwala, PhD'));
  console.log('');
}

program.parse();
