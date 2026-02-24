/**
 * R subprocess bridge — find and execute R scripts
 * Author: Husain Z Attarwala, PhD
 */

import { execFile, execFileSync } from 'child_process';
import { existsSync, mkdirSync, writeFileSync, readFileSync, unlinkSync } from 'fs';
import { join, dirname } from 'path';
import { tmpdir } from 'os';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const R_SCRIPTS_DIR = join(__dirname, '..', 'r-scripts');

let cachedRscriptPath: string | null = null;

export function findRscript(): string {
  if (cachedRscriptPath) return cachedRscriptPath;

  // Check PATH
  try {
    execFileSync('Rscript', ['--version'], { stdio: 'pipe' });
    cachedRscriptPath = 'Rscript';
    return cachedRscriptPath;
  } catch {}

  // Windows common locations
  if (process.platform === 'win32') {
    const programFiles = process.env['ProgramFiles'] || 'C:\\Program Files';
    const rBase = join(programFiles, 'R');
    if (existsSync(rBase)) {
      const { readdirSync } = require('fs');
      const versions = (readdirSync(rBase) as string[])
        .filter((d: string) => d.startsWith('R-'))
        .sort()
        .reverse();
      for (const v of versions) {
        const p = join(rBase, v, 'bin', 'Rscript.exe');
        if (existsSync(p)) {
          cachedRscriptPath = p;
          return p;
        }
      }
    }
  }

  // macOS
  if (process.platform === 'darwin') {
    for (const p of [
      '/usr/local/bin/Rscript',
      '/opt/homebrew/bin/Rscript',
      '/Library/Frameworks/R.framework/Resources/bin/Rscript',
    ]) {
      if (existsSync(p)) {
        cachedRscriptPath = p;
        return p;
      }
    }
  }

  // Linux
  for (const p of ['/usr/bin/Rscript', '/usr/local/bin/Rscript']) {
    if (existsSync(p)) {
      cachedRscriptPath = p;
      return p;
    }
  }

  throw new Error('Rscript not found. Install R from https://cran.r-project.org');
}

export async function runRScript(
  scriptName: string,
  args: Record<string, any>,
  timeout = 600
): Promise<any> {
  const scriptPath = join(R_SCRIPTS_DIR, scriptName);
  if (!existsSync(scriptPath)) {
    return { success: false, error: `R script not found: ${scriptName}` };
  }

  const rscript = findRscript();
  const argsFile = join(tmpdir(), `pkpd_args_${Date.now()}.json`);
  const resultFile = join(tmpdir(), `pkpd_result_${Date.now()}.json`);

  writeFileSync(argsFile, JSON.stringify(args));

  return new Promise((resolve) => {
    const env = {
      ...process.env,
      PMX_ARGS_FILE: argsFile,
      PMX_RESULT_FILE: resultFile,
      PMX_OUTPUT_DIR: args.output_dir || './pkpdbuilder_output',
    };

    const proc = execFile(rscript, [scriptPath], { env, timeout: timeout * 1000 }, (error, stdout, stderr) => {
      // Clean up temp files
      try { unlinkSync(argsFile); } catch {}

      if (error) {
        try { unlinkSync(resultFile); } catch {}
        resolve({ success: false, error: stderr || error.message });
        return;
      }

      if (existsSync(resultFile)) {
        try {
          const result = JSON.parse(readFileSync(resultFile, 'utf-8'));
          unlinkSync(resultFile);
          resolve({ success: true, ...result });
        } catch {
          resolve({ success: true, stdout, message: 'Script completed.' });
        }
      } else {
        resolve({ success: true, stdout, message: 'Script completed (no structured output).' });
      }
    });
  });
}

export async function runRCode(code: string, timeout = 300): Promise<any> {
  const rscript = findRscript();
  const scriptFile = join(tmpdir(), `pkpd_code_${Date.now()}.R`);
  writeFileSync(scriptFile, code);

  return new Promise((resolve) => {
    execFile(rscript, [scriptFile], { timeout: timeout * 1000 }, (error, stdout, stderr) => {
      try { unlinkSync(scriptFile); } catch {}

      if (error) {
        resolve({ success: false, error: stderr || error.message, stdout });
      } else {
        resolve({ success: true, stdout, stderr });
      }
    });
  });
}
