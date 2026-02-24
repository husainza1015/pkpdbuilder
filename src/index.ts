#!/usr/bin/env node
/**
 * PKPDBuilder CLI - Entry Point
 * Author: Husain Z Attarwala, PhD
 */

import { Command } from 'commander';
import { startRepl } from './repl.js';
import { runSetup } from './setup.js';
import { printBanner } from './banner.js';
import { discoverEnvironment } from './discovery.js';
import { PKPDBuilderAgent } from './agent.js';
import chalk from 'chalk';

const program = new Command();

program
  .name('pkpdbuilder')
  .description('The Pharmacometrician\'s Co-Pilot')
  .version('0.2.0');

// Default action: start REPL
program
  .action(async () => {
    await startRepl();
  });

// Setup command
program
  .command('setup')
  .description('Run first-time setup wizard')
  .action(async () => {
    await runSetup();
  });

// Doctor command - environment check
program
  .command('doctor')
  .description('Check environment and dependencies')
  .action(async () => {
    printBanner('Environment Check');
    
    const discovery = discoverEnvironment();
    
    console.log(chalk.bold('R Environment:'));
    if (discovery.r.found) {
      console.log(chalk.green(`  ✓ R ${discovery.r.version} at ${discovery.r.path}`));
      console.log(chalk.bold('\n  Packages:'));
      Object.entries(discovery.r.packages).forEach(([pkg, installed]) => {
        if (installed) {
          console.log(chalk.green(`    ✓ ${pkg}`));
        } else {
          console.log(chalk.yellow(`    ✗ ${pkg} (not installed)`));
        }
      });
    } else {
      console.log(chalk.red('  ✗ R not found'));
    }

    console.log(chalk.bold('\nAPI Keys:'));
    discovery.apiKeys.forEach(k => {
      if (k.found) {
        console.log(chalk.green(`  ✓ ${k.provider}`));
      } else {
        console.log(chalk.dim(`  - ${k.provider} (not configured)`));
      }
    });

    console.log(chalk.bold('\nDatasets in current directory:'));
    if (discovery.datasets.length > 0) {
      discovery.datasets.slice(0, 10).forEach(d => {
        console.log(chalk.cyan(`  - ${d.name} (${d.size} bytes)`));
      });
      if (discovery.datasets.length > 10) {
        console.log(chalk.dim(`  ... and ${discovery.datasets.length - 10} more`));
      }
    } else {
      console.log(chalk.dim('  (none found)'));
    }

    console.log(chalk.bold('\nProject Files:'));
    console.log(
      discovery.projectFiles.memory
        ? chalk.green('  ✓ Project memory found')
        : chalk.dim('  - No project memory')
    );
    console.log('');
  });

// Ask command - one-shot query
program
  .command('ask <query>')
  .description('Ask a one-time question (non-interactive)')
  .option('-m, --model <model>', 'Model to use')
  .option('-p, --provider <provider>', 'Provider to use')
  .action(async (query: string, options: any) => {
    try {
      const agent = new PKPDBuilderAgent({
        model: options.model,
        provider: options.provider,
        streaming: true,
        onStream: (chunk) => {
          process.stdout.write(chunk);
        },
      });

      console.log('');
      await agent.run(query);
      console.log('\n');
    } catch (error: any) {
      console.error(chalk.red(`Error: ${error.message}`));
      process.exit(1);
    }
  });

// Tools command - list all tools
program
  .command('tools')
  .description('List all available tools')
  .action(() => {
    console.log(chalk.bold.cyan('\nPKPDBuilder Tools\n'));
    
    const categories = {
      'Data': ['load_dataset', 'summarize_dataset', 'plot_data', 'dataset_qc', 'handle_blq'],
      'Modeling': ['fit_model', 'fit_from_library', 'compare_models', 'list_model_library', 'get_model_code'],
      'Diagnostics': ['goodness_of_fit', 'vpc', 'eta_plots', 'individual_fits', 'parameter_table'],
      'NCA': ['run_nca'],
      'Simulation': ['simulate_regimen', 'population_simulation'],
      'Literature': ['search_pubmed', 'lookup_drug'],
      'Covariate': ['covariate_screening', 'stepwise_covariate_model', 'forest_plot'],
      'Export/Import': ['export_model', 'import_model', 'list_backends'],
      'Reports': ['generate_report', 'build_shiny_app', 'generate_beamer_slides'],
      'Memory': ['memory_read', 'memory_write', 'memory_search', 'init_project'],
      'Filesystem': ['read_file', 'write_file', 'list_directory', 'search_files', 'move_file', 'get_file_info'],
    };

    Object.entries(categories).forEach(([category, tools]) => {
      console.log(chalk.bold(category + ':'));
      tools.forEach(tool => {
        console.log(chalk.cyan(`  - ${tool}`));
      });
      console.log('');
    });
  });

program.parse();
