/**
 * Environment auto-discovery: R installation, datasets
 * Author: Husain Z Attarwala, PhD
 */

import { execSync, spawnSync } from 'child_process';
import { existsSync, readdirSync, statSync } from 'fs';
import { join, extname } from 'path';
import { platform } from 'os';

export interface REnvironment {
  found: boolean;
  path: string;
  version: string;
  packages: {
    nlmixr2: boolean;
    mrgsolve: boolean;
    PKNCA: boolean;
    xgxr: boolean;
    ggplot2: boolean;
  };
}

export interface Dataset {
  name: string;
  path: string;
  size: number;
}

/**
 * Find Rscript executable on the system
 */
export function findRscript(): string | null {
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
      if (existsSync(path)) return path;
    }
  } catch (e) {
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
            if (existsSync(rscript)) return rscript;
          }
        } catch (e) {
          // Continue
        }
      }
    }
  } else if (isMac) {
    const macPaths = [
      '/usr/local/bin/Rscript',
      '/opt/homebrew/bin/Rscript',
      '/Library/Frameworks/R.framework/Versions/Current/Resources/bin/Rscript',
    ];
    for (const path of macPaths) {
      if (existsSync(path)) return path;
    }

    const frameworkDir = '/Library/Frameworks/R.framework/Versions';
    if (existsSync(frameworkDir)) {
      try {
        const versions = readdirSync(frameworkDir)
          .filter(d => d.match(/^\d+\.\d+$/))
          .sort()
          .reverse();
        for (const version of versions) {
          const rscript = join(frameworkDir, version, 'Resources', 'bin', 'Rscript');
          if (existsSync(rscript)) return rscript;
        }
      } catch (e) {
        // Continue
      }
    }
  } else {
    const linuxPaths = ['/usr/bin/Rscript', '/usr/local/bin/Rscript', '/opt/R/bin/Rscript'];
    for (const path of linuxPaths) {
      if (existsSync(path)) return path;
    }
  }

  return null;
}

/**
 * Get R version
 */
export function getRVersion(rscript: string): string {
  try {
    const result = execSync(`"${rscript}" --version`, {
      encoding: 'utf-8',
      stdio: 'pipe',
    });
    const match = result.match(/R scripting front-end version (\d+\.\d+\.\d+)/);
    return match ? match[1] : 'unknown';
  } catch (e) {
    return 'unknown';
  }
}

/**
 * Check which R packages are installed
 */
export function checkRPackages(rscript: string): REnvironment['packages'] {
  const packages = { nlmixr2: false, mrgsolve: false, PKNCA: false, xgxr: false, ggplot2: false };

  try {
    const code = `installed <- installed.packages()[,"Package"]; cat(paste(c("nlmixr2","mrgsolve","PKNCA","xgxr","ggplot2") %in% installed, collapse=","))`;
    const result = execSync(`"${rscript}" -e "${code}"`, {
      encoding: 'utf-8',
      stdio: 'pipe',
    });
    const values = result.trim().split(',').map(v => v.trim() === 'TRUE');
    packages.nlmixr2 = values[0] || false;
    packages.mrgsolve = values[1] || false;
    packages.PKNCA = values[2] || false;
    packages.xgxr = values[3] || false;
    packages.ggplot2 = values[4] || false;
  } catch (e) {
    // All false
  }

  return packages;
}

/**
 * Discover R environment
 */
export function discoverR(): REnvironment {
  const rscript = findRscript();
  if (!rscript) {
    return {
      found: false,
      path: '',
      version: '',
      packages: { nlmixr2: false, mrgsolve: false, PKNCA: false, xgxr: false, ggplot2: false },
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
export function scanForDatasets(dir: string = process.cwd(), maxDepth: number = 2): Dataset[] {
  const datasets: Dataset[] = [];
  const validExtensions = ['.csv', '.xpt', '.sas7bdat', '.nm', '.txt'];

  function scan(currentDir: string, depth: number) {
    if (depth > maxDepth) return;
    try {
      const entries = readdirSync(currentDir);
      for (const entry of entries) {
        const fullPath = join(currentDir, entry);
        try {
          const stat = statSync(fullPath);
          if (stat.isDirectory()) {
            if (!entry.startsWith('.') && entry !== 'node_modules') {
              scan(fullPath, depth + 1);
            }
          } else if (stat.isFile()) {
            const ext = extname(entry).toLowerCase();
            if (validExtensions.includes(ext)) {
              datasets.push({ name: entry, path: fullPath, size: stat.size });
            }
          }
        } catch (e) { /* skip */ }
      }
    } catch (e) { /* skip */ }
  }

  scan(dir, 0);
  return datasets;
}

/**
 * Check for project-specific files
 */
export function checkProjectFiles(dir: string = process.cwd()) {
  return {
    memory: existsSync(join(dir, 'MEMORY.md')) || existsSync(join(dir, '.pkpdbuilder', 'memory.json')),
    models: existsSync(join(dir, 'models')) || existsSync(join(dir, 'pkpdbuilder_output', 'models')),
    reports: existsSync(join(dir, 'reports')) || existsSync(join(dir, 'pkpdbuilder_output', 'reports')),
  };
}
