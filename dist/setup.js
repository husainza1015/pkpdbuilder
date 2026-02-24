/**
 * Zero-config setup wizard
 * Author: Husain Z Attarwala, PhD
 */
import inquirer from 'inquirer';
import chalk from 'chalk';
import ora from 'ora';
import { saveApiKey, saveConfig, PROVIDERS } from './config.js';
import { discoverEnvironment } from './discovery.js';
import { testR } from './r-bridge.js';
export async function runSetup() {
    console.log(chalk.bold.cyan('\n🔧 PKPDBuilder Setup\n'));
    const spinner = ora('Discovering environment...').start();
    const discovery = discoverEnvironment();
    spinner.stop();
    // R environment
    if (discovery.r.found) {
        console.log(chalk.green(`✓ R ${discovery.r.version} found at ${discovery.r.path}`));
        // Package checks
        const packages = ['nlmixr2', 'mrgsolve', 'PKNCA', 'xgxr', 'ggplot2'];
        for (const pkg of packages) {
            const installed = discovery.r.packages[pkg];
            if (installed) {
                console.log(chalk.green(`  ✓ ${pkg}`));
            }
            else {
                console.log(chalk.yellow(`  ✗ ${pkg} (optional)`));
            }
        }
        // Test R
        spinner.start('Testing R execution...');
        const rWorks = await testR();
        spinner.stop();
        if (rWorks) {
            console.log(chalk.green('✓ R is working correctly'));
        }
        else {
            console.log(chalk.red('✗ R execution test failed'));
        }
    }
    else {
        console.log(chalk.red('✗ R not found'));
        console.log(chalk.dim('  Install R from https://cran.r-project.org/'));
        console.log(chalk.dim('  Then install packages: install.packages(c("nlmixr2", "mrgsolve"))'));
    }
    console.log('');
    // API Keys
    const apiKeysFound = discovery.apiKeys.filter(k => k.found);
    if (apiKeysFound.length > 0) {
        console.log(chalk.green('✓ Found API keys:'));
        apiKeysFound.forEach(k => {
            console.log(chalk.green(`  - ${k.provider}`));
        });
        const { useExisting } = await inquirer.prompt([
            {
                type: 'confirm',
                name: 'useExisting',
                message: 'Use existing API key?',
                default: true,
            },
        ]);
        if (useExisting) {
            // Pick provider
            const providerChoices = apiKeysFound.map(k => ({
                name: PROVIDERS[k.provider].name,
                value: k.provider,
            }));
            const { provider } = await inquirer.prompt([
                {
                    type: 'list',
                    name: 'provider',
                    message: 'Select default provider:',
                    choices: providerChoices,
                },
            ]);
            saveConfig({ provider });
            console.log(chalk.green(`\n✓ Setup complete! Default provider: ${provider}`));
            console.log(chalk.dim('  Run `pkpdbuilder` to start the interactive mode'));
            return;
        }
    }
    // Prompt for new API key
    console.log(chalk.yellow('No API key found or you chose to add a new one.\n'));
    console.log('Get an API key from:');
    Object.entries(PROVIDERS).forEach(([key, info]) => {
        if (!info.local) {
            console.log(chalk.dim(`  ${info.name}: ${info.docs}`));
        }
    });
    console.log('');
    const { provider } = await inquirer.prompt([
        {
            type: 'list',
            name: 'provider',
            message: 'Select provider:',
            choices: [
                { name: 'Anthropic (Claude)', value: 'anthropic' },
                { name: 'OpenAI (GPT)', value: 'openai' },
                { name: 'Google (Gemini)', value: 'google' },
                { name: 'Ollama (Local)', value: 'ollama' },
            ],
        },
    ]);
    if (provider === 'ollama') {
        console.log(chalk.green('✓ Ollama selected (no API key needed)'));
        saveConfig({ provider });
    }
    else {
        const { apiKey } = await inquirer.prompt([
            {
                type: 'password',
                name: 'apiKey',
                message: `Enter your ${PROVIDERS[provider].name} API key:`,
                mask: '*',
            },
        ]);
        if (!apiKey) {
            console.log(chalk.red('No API key provided. Setup aborted.'));
            return;
        }
        saveApiKey(provider, apiKey);
        saveConfig({ provider });
        console.log(chalk.green(`\n✓ API key saved securely for ${provider}`));
    }
    console.log(chalk.green('\n✓ Setup complete!'));
    console.log(chalk.dim('  Run `pkpdbuilder` to start the interactive mode'));
}
//# sourceMappingURL=setup.js.map