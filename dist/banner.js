/**
 * Gradient ASCII banner for PKPDBuilder CLI
 * Author: Husain Z Attarwala, PhD
 */
import chalk from 'chalk';
const PKPD_LINES = [
    '██████╗ ██╗  ██╗██████╗ ██████╗ ',
    '██╔══██╗██║ ██╔╝██╔══██╗██╔══██╗',
    '██████╔╝█████╔╝ ██████╔╝██║  ██║',
    '██╔═══╝ ██╔═██╗ ██╔═══╝ ██║  ██║',
    '██║     ██║  ██╗██║     ██████╔╝',
    '╚═╝     ╚═╝  ╚═╝╚═╝     ╚═════╝ ',
];
const BUILDER_LINES = [
    '██████╗ ██╗   ██╗██╗██╗     ██████╗ ███████╗██████╗ ',
    '██╔══██╗██║   ██║██║██║     ██╔══██╗██╔════╝██╔══██╗',
    '██████╔╝██║   ██║██║██║     ██║  ██║█████╗  ██████╔╝',
    '██╔══██╗██║   ██║██║██║     ██║  ██║██╔══╝  ██╔══██╗',
    '██████╔╝╚██████╔╝██║███████╗██████╔╝███████╗██║  ██║',
    '╚═════╝  ╚═════╝ ╚═╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝',
];
/**
 * Generate RGB gradient from violet to cyan
 */
function violetToCyanGradient(steps) {
    const colors = [];
    // Violet: rgb(148, 0, 211) -> Cyan: rgb(0, 255, 255)
    for (let i = 0; i < steps; i++) {
        const t = i / (steps - 1);
        const r = Math.round(148 * (1 - t) + 0 * t);
        const g = Math.round(0 * (1 - t) + 255 * t);
        const b = Math.round(211 * (1 - t) + 255 * t);
        colors.push([r, g, b]);
    }
    return colors;
}
/**
 * Apply gradient colors to text lines
 */
function applyGradient(lines) {
    const totalLines = PKPD_LINES.length + BUILDER_LINES.length;
    const gradient = violetToCyanGradient(totalLines);
    const allLines = [...PKPD_LINES, ...BUILDER_LINES];
    return allLines.map((line, idx) => {
        const [r, g, b] = gradient[idx];
        return chalk.rgb(r, g, b)(line);
    });
}
/**
 * Print the gradient banner
 */
export function printBanner(subtitle = "The Pharmacometrician's Co-Pilot") {
    const coloredLines = applyGradient([...PKPD_LINES, ...BUILDER_LINES]);
    console.log('');
    // Print PKPD
    for (let i = 0; i < PKPD_LINES.length; i++) {
        console.log('  ' + coloredLines[i]);
    }
    // Print BUILDER
    for (let i = PKPD_LINES.length; i < coloredLines.length; i++) {
        console.log('  ' + coloredLines[i]);
    }
    console.log('');
    console.log(chalk.dim('  ' + subtitle));
    console.log(chalk.dim('  ' + '─'.repeat(subtitle.length)));
    console.log('');
}
/**
 * Print a simple version banner (no gradient, for compatibility)
 */
export function printSimpleBanner(subtitle = "The Pharmacometrician's Co-Pilot") {
    console.log('');
    console.log(chalk.magenta('  ╔═══════════════════════════════════════════════════╗'));
    console.log(chalk.magenta('  ║           ') + chalk.cyan.bold('PKPDBuilder') + chalk.magenta('                      ║'));
    console.log(chalk.magenta('  ╚═══════════════════════════════════════════════════╝'));
    console.log('');
    console.log(chalk.dim('  ' + subtitle));
    console.log(chalk.dim('  ' + '─'.repeat(subtitle.length)));
    console.log('');
}
/**
 * Mini banner for REPL prompt
 */
export function miniPrompt() {
    return chalk.rgb(148, 0, 211)('pkpdbuilder') + chalk.rgb(0, 255, 255)('>') + ' ';
}
//# sourceMappingURL=banner.js.map