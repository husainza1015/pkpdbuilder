/**
 * Interactive REPL for PKPDBuilder
 * Author: Husain Z Attarwala, PhD
 */
import inquirer from 'inquirer';
import chalk from 'chalk';
import { PKPDBuilderAgent } from './agent.js';
import { printBanner, miniPrompt } from './banner.js';
import { loadConfig, saveConfig } from './config.js';
import { discoverEnvironment } from './discovery.js';
const HELP_TEXT = `
${chalk.bold('PKPDBuilder REPL Commands')}

${chalk.cyan('Slash Commands:')}
  /help             Show this help
  /tools            List available tools
  /model <name>     Switch AI model
  /provider <name>  Switch provider (anthropic, openai, google, ollama)
  /clear            Clear conversation history
  /audit            Show recent API usage (stub)
  /profile          Show learning profile (stub)
  /exit, /quit      Exit the REPL

${chalk.cyan('Natural Language:')}
  Everything else is sent to the AI agent for analysis.
  Examples:
    - "load data.csv and summarize it"
    - "fit a 2-compartment model"
    - "run diagnostics and generate a report"
`;
export async function startRepl() {
    printBanner();
    // Discovery
    console.log(chalk.dim('  Checking environment...'));
    const discovery = discoverEnvironment();
    if (discovery.r.found) {
        console.log(chalk.green(`  ✓ R ${discovery.r.version} found at ${discovery.r.path}`));
        if (discovery.r.packages.nlmixr2)
            console.log(chalk.green('  ✓ nlmixr2 installed'));
        if (discovery.r.packages.mrgsolve)
            console.log(chalk.green('  ✓ mrgsolve installed'));
        if (!discovery.r.packages.PKNCA) {
            console.log(chalk.yellow('  ✗ PKNCA not found (optional — install with install.packages("PKNCA"))'));
        }
    }
    else {
        console.log(chalk.red('  ✗ R not found. Some features will be unavailable.'));
    }
    // API key check
    const apiKeyFound = discovery.apiKeys.find(k => k.found);
    if (apiKeyFound) {
        console.log(chalk.green(`  ✓ API key found: ${apiKeyFound.provider}`));
    }
    else {
        console.log(chalk.red('  ✗ No API key found. Run setup or set environment variable.'));
        return;
    }
    // Datasets
    if (discovery.datasets.length > 0) {
        console.log(chalk.dim(`  Found ${discovery.datasets.length} dataset(s) in current directory`));
    }
    console.log('');
    console.log(chalk.dim('  Ready! Type naturally or use /help for commands.'));
    console.log('');
    const config = loadConfig();
    const agent = new PKPDBuilderAgent({
        streaming: true,
        onStream: (chunk) => {
            process.stdout.write(chunk);
        },
    });
    // REPL loop
    while (true) {
        const { input } = await inquirer.prompt([
            {
                type: 'input',
                name: 'input',
                message: '',
                prefix: miniPrompt(),
            },
        ]);
        const trimmed = input.trim();
        if (!trimmed)
            continue;
        // Slash commands
        if (trimmed.startsWith('/')) {
            const cmd = trimmed.split(' ')[0].toLowerCase();
            const args = trimmed.substring(cmd.length).trim();
            if (cmd === '/help') {
                console.log(HELP_TEXT);
                continue;
            }
            if (cmd === '/exit' || cmd === '/quit') {
                console.log(chalk.dim('Goodbye!'));
                process.exit(0);
            }
            if (cmd === '/clear') {
                agent.clearHistory();
                console.log(chalk.green('✓ Conversation cleared'));
                continue;
            }
            if (cmd === '/tools') {
                console.log(chalk.bold('\nAvailable Tools:'));
                console.log('  load_dataset, summarize_dataset, plot_data, fit_model, vpc, goodness_of_fit, run_nca, simulate_regimen, generate_report, memory_read, memory_write, ...');
                console.log(chalk.dim('  (33 tools total)\n'));
                continue;
            }
            if (cmd === '/model') {
                if (!args) {
                    console.log(chalk.red('Usage: /model <model_name>'));
                }
                else {
                    saveConfig({ model: args });
                    console.log(chalk.green(`✓ Switched to model: ${args}`));
                }
                continue;
            }
            if (cmd === '/provider') {
                if (!args) {
                    console.log(chalk.red('Usage: /provider <provider_name>'));
                }
                else {
                    saveConfig({ provider: args });
                    console.log(chalk.green(`✓ Switched to provider: ${args}`));
                    console.log(chalk.yellow('  (Restart REPL to apply provider change)'));
                }
                continue;
            }
            if (cmd === '/audit') {
                console.log(chalk.dim('API audit log (stub)'));
                continue;
            }
            if (cmd === '/profile') {
                console.log(chalk.dim('Learning profile (stub)'));
                continue;
            }
            console.log(chalk.red(`Unknown command: ${cmd}`));
            console.log(chalk.dim('Type /help for available commands'));
            continue;
        }
        // Send to agent
        try {
            console.log(''); // Newline before response
            await agent.run(trimmed);
            console.log('\n'); // Newline after response
        }
        catch (error) {
            console.log(chalk.red(`\nError: ${error.message}\n`));
        }
    }
}
//# sourceMappingURL=repl.js.map