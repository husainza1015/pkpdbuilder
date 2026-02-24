/**
 * Environment auto-discovery: R installation, datasets, API keys
 * Author: Husain Z Attarwala, PhD
 */
import { execSync, spawnSync } from 'child_process';
import { existsSync, readdirSync, statSync } from 'fs';
import { join, extname } from 'path';
import { platform } from 'os';
import { getApiKey, PROVIDERS } from './config.js';
/**
 * Find Rscript executable on the system
 */
export function findRscript() {
    const isWindows = platform() === 'win32';
    const isMac = platform() === 'darwin';
    // 1. Check PATH first
    try {
        const result = spawnSync(isWindows ? 'where' : 'which', ['Rscript'], {
            encoding: 'utf-8',
            stdio: 'pipe',
        });
        if (result.status === 0 && result.stdout) {
            const path = result.stdout.trim().split('\n')[0];
            if (existsSync(path))
                return path;
        }
    }
    catch (e) {
        // Continue to manual search
    }
    // 2. Check common installation directories
    if (isWindows) {
        const programFiles = [
            process.env.ProgramFiles || 'C:\\Program Files',
            process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)',
        ];
        for (const pf of programFiles) {
            const rDir = join(pf, 'R');
            if (existsSync(rDir)) {
                try {
                    const versions = readdirSync(rDir)
                        .filter(d => d.startsWith('R-'))
                        .sort()
                        .reverse();
                    for (const version of versions) {
                        const rscript = join(rDir, version, 'bin', 'Rscript.exe');
                        if (existsSync(rscript))
                            return rscript;
                    }
                }
                catch (e) {
                    // Continue
                }
            }
        }
    }
    else if (isMac) {
        // macOS common paths
        const macPaths = [
            '/usr/local/bin/Rscript',
            '/opt/homebrew/bin/Rscript',
            '/Library/Frameworks/R.framework/Versions/Current/Resources/bin/Rscript',
        ];
        for (const path of macPaths) {
            if (existsSync(path))
                return path;
        }
        // Check Framework versions
        const frameworkDir = '/Library/Frameworks/R.framework/Versions';
        if (existsSync(frameworkDir)) {
            try {
                const versions = readdirSync(frameworkDir)
                    .filter(d => d.match(/^\d+\.\d+$/))
                    .sort()
                    .reverse();
                for (const version of versions) {
                    const rscript = join(frameworkDir, version, 'Resources', 'bin', 'Rscript');
                    if (existsSync(rscript))
                        return rscript;
                }
            }
            catch (e) {
                // Continue
            }
        }
    }
    else {
        // Linux common paths
        const linuxPaths = [
            '/usr/bin/Rscript',
            '/usr/local/bin/Rscript',
            '/opt/R/bin/Rscript',
        ];
        for (const path of linuxPaths) {
            if (existsSync(path))
                return path;
        }
    }
    return null;
}
/**
 * Get R version
 */
export function getRVersion(rscript) {
    try {
        const result = execSync(`"${rscript}" --version`, {
            encoding: 'utf-8',
            stdio: 'pipe',
        });
        const match = result.match(/R scripting front-end version (\d+\.\d+\.\d+)/);
        return match ? match[1] : 'unknown';
    }
    catch (e) {
        return 'unknown';
    }
}
/**
 * Check which R packages are installed
 */
export function checkRPackages(rscript) {
    const packages = {
        nlmixr2: false,
        mrgsolve: false,
        PKNCA: false,
        xgxr: false,
        ggplot2: false,
    };
    try {
        const code = `
      installed <- installed.packages()[,"Package"]
      cat(paste(c("nlmixr2", "mrgsolve", "PKNCA", "xgxr", "ggplot2") %in% installed, collapse=","))
    `;
        const result = execSync(`"${rscript}" -e "${code.replace(/\n/g, ' ')}"`, {
            encoding: 'utf-8',
            stdio: 'pipe',
        });
        const values = result.trim().split(',').map(v => v.trim() === 'TRUE');
        packages.nlmixr2 = values[0] || false;
        packages.mrgsolve = values[1] || false;
        packages.PKNCA = values[2] || false;
        packages.xgxr = values[3] || false;
        packages.ggplot2 = values[4] || false;
    }
    catch (e) {
        // All false if check fails
    }
    return packages;
}
/**
 * Discover R environment
 */
export function discoverR() {
    const rscript = findRscript();
    if (!rscript) {
        return {
            found: false,
            path: '',
            version: '',
            packages: {
                nlmixr2: false,
                mrgsolve: false,
                PKNCA: false,
                xgxr: false,
                ggplot2: false,
            },
        };
    }
    return {
        found: true,
        path: rscript,
        version: getRVersion(rscript),
        packages: checkRPackages(rscript),
    };
}
/**
 * Scan directory for dataset files
 */
export function scanForDatasets(dir = process.cwd(), maxDepth = 2) {
    const datasets = [];
    const validExtensions = ['.csv', '.xpt', '.sas7bdat', '.nm', '.txt'];
    function scan(currentDir, depth) {
        if (depth > maxDepth)
            return;
        try {
            const entries = readdirSync(currentDir);
            for (const entry of entries) {
                const fullPath = join(currentDir, entry);
                try {
                    const stat = statSync(fullPath);
                    if (stat.isDirectory()) {
                        // Skip node_modules, .git, etc.
                        if (!entry.startsWith('.') && entry !== 'node_modules') {
                            scan(fullPath, depth + 1);
                        }
                    }
                    else if (stat.isFile()) {
                        const ext = extname(entry).toLowerCase();
                        if (validExtensions.includes(ext)) {
                            datasets.push({
                                name: entry,
                                path: fullPath,
                                size: stat.size,
                            });
                        }
                    }
                }
                catch (e) {
                    // Skip files we can't stat
                }
            }
        }
        catch (e) {
            // Skip directories we can't read
        }
    }
    scan(dir, 0);
    return datasets;
}
/**
 * Check which API keys are available
 */
export function checkApiKeys() {
    const results = [];
    for (const [provider, info] of Object.entries(PROVIDERS)) {
        if (info.local) {
            // Check if Ollama is running
            try {
                const response = execSync('curl -s http://localhost:11434/api/tags', {
                    encoding: 'utf-8',
                    stdio: 'pipe',
                    timeout: 2000,
                });
                results.push({ provider, found: !!response });
            }
            catch (e) {
                results.push({ provider, found: false });
            }
        }
        else {
            const key = getApiKey(provider);
            results.push({ provider, found: !!key });
        }
    }
    return results;
}
/**
 * Check for project-specific files
 */
export function checkProjectFiles(dir = process.cwd()) {
    return {
        memory: existsSync(join(dir, 'MEMORY.md')) || existsSync(join(dir, '.pkpdbuilder', 'memory.json')),
        models: existsSync(join(dir, 'models')) || existsSync(join(dir, 'pkpdbuilder_output', 'models')),
        reports: existsSync(join(dir, 'reports')) || existsSync(join(dir, 'pkpdbuilder_output', 'reports')),
    };
}
/**
 * Run full environment discovery
 */
export function discoverEnvironment(dir) {
    const targetDir = dir || process.cwd();
    return {
        r: discoverR(),
        datasets: scanForDatasets(targetDir),
        apiKeys: checkApiKeys(),
        projectFiles: checkProjectFiles(targetDir),
    };
}
//# sourceMappingURL=discovery.js.map