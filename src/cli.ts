#!/usr/bin/env node
/**
 * PKPDBuilder CLI — The Pharmacometrician's Co-Pilot
 * Wraps Claude Code with pharmacometric MCP tools + domain knowledge
 * 
 * User sees: pkpdbuilder
 * Under the hood: Claude Code + MCP server + R backend
 * 
 * Author: Husain Z Attarwala, PhD
 */

import { Command } from 'commander';
import { existsSync, writeFileSync, mkdirSync, readFileSync } from 'fs';
import { join, dirname } from 'path';
import { execSync, spawn, spawnSync } from 'child_process';
import { homedir } from 'os';
import chalk from 'chalk';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PACKAGE_ROOT = join(__dirname, '..');
const VERSION = '0.3.0';

const program = new Command();

program
  .name('pkpdbuilder')
  .description('The Pharmacometrician\'s Co-Pilot')
  .version(VERSION);

// ── Main command: launch ───────────────────────────────

program
  .command('start', { isDefault: true })
  .description('Launch PKPDBuilder')
  .action(async () => {
    printBanner();

    // Step 1: Ensure Claude Code is installed
    if (!hasClaude()) {
      console.log(chalk.yellow('  Setting up for first use...\n'));
      installClaude();
    }

    // Step 2: Ensure Claude Code is authenticated
    if (!isClaudeAuthenticated()) {
      console.log(chalk.yellow('  Authentication required.\n'));
      console.log(chalk.dim('  PKPDBuilder uses Claude (Anthropic) as its AI engine.'));
      console.log(chalk.dim('  You need an Anthropic API key or Claude Max subscription.\n'));
      
      // Run claude login interactively
      const login = spawnSync('claude', ['login'], { stdio: 'inherit' });
      if (login.status !== 0) {
        console.log(chalk.red('\n  Authentication failed. Run `pkpdbuilder` again after logging in.'));
        process.exit(1);
      }
      console.log(chalk.green('\n  ✓ Authenticated\n'));
    }

    // Step 3: Check R (non-blocking)
    const rStatus = checkR();

    // Step 4: Configure MCP server (silent)
    ensureMcpConfig();

    // Step 5: Ensure CLAUDE.md in cwd
    ensureClaudeMd();

    // Step 6: Launch
    console.log(chalk.green('  ✓ Ready\n'));
    if (!rStatus) {
      console.log(chalk.dim('  Note: R not found — modeling tools will be unavailable.'));
      console.log(chalk.dim('  Install R from https://cran.r-project.org for full functionality.\n'));
    }

    const claude = spawn('claude', [], {
      stdio: 'inherit',
      cwd: process.cwd(),
      env: { ...process.env },
    });

    claude.on('exit', (code) => process.exit(code || 0));
  });

// ── Init: scaffold a project ───────────────────────────

program
  .command('init')
  .description('Initialize a pharmacometrics project')
  .argument('[drug]', 'Drug name')
  .action((drug?: string) => {
    printBanner();
    ensureClaudeMd(drug);

    const outDir = join(process.cwd(), 'pkpdbuilder_output');
    if (!existsSync(outDir)) {
      mkdirSync(outDir, { recursive: true });
      console.log(chalk.green('  ✓ Created pkpdbuilder_output/'));
    }

    const memFile = join(process.cwd(), 'MEMORY.md');
    if (!existsSync(memFile)) {
      writeFileSync(memFile, `# Project Memory\n\n## Drug: ${drug || 'TBD'}\n\n## Key Decisions\n\n## Model History\n`);
      console.log(chalk.green('  ✓ Created MEMORY.md'));
    }

    console.log(chalk.green('\n  Project ready! Run `pkpdbuilder` to start.\n'));
  });

// ── Doctor: check everything ───────────────────────────

program
  .command('doctor')
  .description('Check environment')
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

      if (isClaudeAuthenticated()) {
        console.log(chalk.green('  ✓ Authenticated'));
      } else {
        console.log(chalk.yellow('  ○ Not authenticated (run pkpdbuilder to login)'));
      }
    } else {
      console.log(chalk.yellow('  ○ Claude Code not installed (run pkpdbuilder to auto-install)'));
    }

    // R
    checkR(true);

    // MCP
    const mcpPath = getMcpConfigPath();
    if (existsSync(mcpPath)) {
      try {
        const config = JSON.parse(readFileSync(mcpPath, 'utf-8'));
        if (config.mcpServers?.pkpdbuilder) {
          console.log(chalk.green('  ✓ MCP tools configured'));
        } else {
          console.log(chalk.yellow('  ○ MCP not configured (run pkpdbuilder)'));
        }
      } catch {
        console.log(chalk.yellow('  ○ MCP config unreadable'));
      }
    } else {
      console.log(chalk.yellow('  ○ MCP not configured (run pkpdbuilder)'));
    }

    // CLAUDE.md
    if (existsSync(join(process.cwd(), 'CLAUDE.md'))) {
      console.log(chalk.green('  ✓ CLAUDE.md found'));
    } else {
      console.log(chalk.yellow('  ○ No CLAUDE.md (run pkpdbuilder init)'));
    }

    console.log('');
  });

// ═══════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════

function hasClaude(): boolean {
  try {
    execSync('claude --version', { stdio: 'pipe' });
    return true;
  } catch {
    return false;
  }
}

function installClaude(): void {
  console.log(chalk.cyan('  Installing Claude Code...'));
  try {
    execSync('npm install -g @anthropic-ai/claude-code', {
      stdio: 'inherit',
      timeout: 120000,
    });
    console.log(chalk.green('  ✓ Claude Code installed\n'));
  } catch {
    console.log(chalk.red('\n  Failed to install Claude Code.'));
    console.log(chalk.dim('  Try manually: npm install -g @anthropic-ai/claude-code'));
    process.exit(1);
  }
}

function isClaudeAuthenticated(): boolean {
  // Check if Claude Code has stored credentials
  const home = homedir();
  const credPaths = [
    join(home, '.claude', 'config.json'),
    join(home, '.claude', 'credentials.json'),
    join(home, '.claude.json'),
  ];

  for (const p of credPaths) {
    if (existsSync(p)) {
      try {
        const data = readFileSync(p, 'utf-8');
        if (data.includes('api_key') || data.includes('oauth') || data.includes('token') || data.includes('sk-ant-')) {
          return true;
        }
      } catch {}
    }
  }

  // Also check env var
  if (process.env.ANTHROPIC_API_KEY) return true;

  return false;
}

function findRscript(): string | null {
  // Check PATH
  try {
    execSync('Rscript --version', { stdio: 'pipe' });
    return 'Rscript';
  } catch {}

  // Windows
  if (process.platform === 'win32') {
    const programFiles = process.env['ProgramFiles'] || 'C:\\Program Files';
    const rBase = join(programFiles, 'R');
    if (existsSync(rBase)) {
      try {
        const { readdirSync } = require('fs');
        const versions = (readdirSync(rBase) as string[])
          .filter((d: string) => d.startsWith('R-'))
          .sort()
          .reverse();
        for (const v of versions) {
          const p = join(rBase, v, 'bin', 'Rscript.exe');
          if (existsSync(p)) return p;
        }
      } catch {}
    }
  }

  // macOS
  if (process.platform === 'darwin') {
    for (const p of [
      '/usr/local/bin/Rscript',
      '/opt/homebrew/bin/Rscript',
      '/Library/Frameworks/R.framework/Resources/bin/Rscript',
    ]) {
      if (existsSync(p)) return p;
    }
  }

  // Linux
  for (const p of ['/usr/bin/Rscript', '/usr/local/bin/Rscript']) {
    if (existsSync(p)) return p;
  }

  return null;
}

function checkR(verbose = false): boolean {
  const rPath = findRscript();
  if (!rPath) {
    if (verbose) {
      console.log(chalk.yellow('  ✗ R not found'));
      console.log(chalk.dim('    Install from https://cran.r-project.org'));
    }
    return false;
  }

  console.log(chalk.green(`  ✓ R found at ${rPath}`));

  if (verbose) {
    try {
      const result = execSync(
        `"${rPath}" -e "pkgs <- c('nlmixr2','mrgsolve','PKNCA','ggplot2'); installed <- sapply(pkgs, requireNamespace, quietly=TRUE); cat(paste(pkgs, installed, sep='=', collapse=';'))"`,
        { encoding: 'utf-8', timeout: 15000 }
      ).trim();

      for (const pair of result.split(';')) {
        const [pkg, status] = pair.split('=');
        if (status === 'TRUE') {
          console.log(chalk.green(`    ✓ ${pkg}`));
        } else {
          console.log(chalk.yellow(`    ✗ ${pkg}`));
        }
      }
    } catch {}
  }

  return true;
}

function getMcpConfigPath(): string {
  return join(homedir(), '.claude', 'claude_desktop_config.json');
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

  const serverPath = join(PACKAGE_ROOT, 'dist', 'server.js');
  config.mcpServers['pkpdbuilder'] = {
    command: 'node',
    args: [serverPath],
  };

  writeFileSync(configPath, JSON.stringify(config, null, 2));
}

function ensureClaudeMd(drug?: string): void {
  const claudeMd = join(process.cwd(), 'CLAUDE.md');
  if (existsSync(claudeMd)) return;

  const content = `# PKPDBuilder — Pharmacometrics Co-Pilot

You are a pharmacometrics expert. You have specialized MCP tools for population PK/PD analysis.

## Tools

### Data
- \`load_dataset\` — Load CSV/NONMEM datasets (validates ID/TIME/DV)
- \`summarize_dataset\` — Subject counts, covariates, dosing summary
- \`plot_data\` — Spaghetti, individual, dose-normalized plots
- \`dataset_qc\` — Quality checks
- \`handle_blq\` — BLQ handling (M1-M7)

### Modeling
- \`fit_model\` — Fit PopPK via nlmixr2 (1/2/3-CMT, SAEM/FOCEI)
- \`fit_from_library\` — Fit from 59-model library
- \`compare_models\` — OFV/AIC/BIC comparison
- \`list_model_library\` — Browse models
- \`get_model_code\` — View nlmixr2 code

### Diagnostics
- \`goodness_of_fit\` — DV vs PRED/IPRED, CWRES
- \`vpc\` — Visual Predictive Check
- \`eta_plots\` — ETA distributions + covariates
- \`individual_fits\` — Per-subject fits
- \`parameter_table\` — Estimates with RSE/shrinkage

### Analysis
- \`run_nca\` — NCA via PKNCA
- \`simulate_regimen\` — Dosing simulation (mrgsolve)
- \`population_simulation\` — Virtual population with IIV
- \`covariate_screening\` — Univariate screening
- \`stepwise_covariate_model\` — SCM (forward/backward)
- \`forest_plot\` — Covariate effects

### Literature
- \`search_pubmed\` — PubMed search
- \`lookup_drug\` — Published PK parameters

### Export
- \`export_model\` — NONMEM/Monolix/Pumas
- \`import_model\` — Import from NONMEM/Monolix
- \`generate_report\` — HTML analysis report
- \`build_shiny_app\` — Interactive Shiny simulator

## Workflow
1. Load + QC dataset
2. Explore data visually
3. NCA for initial estimates
4. Fit base model (simple → complex)
5. Compare models by BIC
6. Covariate screening → SCM
7. Diagnostics (GOF, VPC, ETAs)
8. Final report + export
${drug ? `\n## Drug: ${drug}\n` : ''}
`;

  writeFileSync(claudeMd, content);
  console.log(chalk.green('  ✓ Created CLAUDE.md'));
}

function printBanner(): void {
  const v = chalk.rgb(168, 85, 247);
  const i = chalk.rgb(99, 102, 241);
  const c = chalk.rgb(6, 182, 212);

  console.log('');
  console.log(v('  ██████╗ ██╗  ██╗██████╗ ██████╗ '));
  console.log(v('  ██╔══██╗██║ ██╔╝██╔══██╗██╔══██╗'));
  console.log(i('  ██████╔╝█████╔╝ ██████╔╝██║  ██║'));
  console.log(i('  ██╔═══╝ ██╔═██╗ ██╔═══╝ ██║  ██║'));
  console.log(c('  ██║     ██║  ██╗██║     ██████╔╝'));
  console.log(c('  ╚═╝     ╚═╝  ╚═╝╚═╝     ╚═════╝ '));
  console.log(v('  ██████╗ ██╗   ██╗██╗██╗     ██████╗ ███████╗██████╗ '));
  console.log(v('  ██╔══██╗██║   ██║██║██║     ██╔══██╗██╔════╝██╔══██╗'));
  console.log(i('  ██████╔╝██║   ██║██║██║     ██║  ██║█████╗  ██████╔╝'));
  console.log(i('  ██╔══██╗██║   ██║██║██║     ██║  ██║██╔══╝  ██╔══██╗'));
  console.log(c('  ██████╔╝╚██████╔╝██║███████╗██████╔╝███████╗██║  ██║'));
  console.log(c('  ╚═════╝  ╚═════╝ ╚═╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝'));
  console.log('');
  console.log(chalk.dim(`  The Pharmacometrician's Co-Pilot • v${VERSION}`));
  console.log(chalk.dim('  Developer: Husain Z Attarwala, PhD\n'));
}

program.parse();
