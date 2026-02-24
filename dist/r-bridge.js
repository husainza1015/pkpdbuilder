/**
 * R subprocess bridge for executing R scripts and code
 * Author: Husain Z Attarwala, PhD
 */
import { execFile } from 'child_process';
import { writeFileSync, readFileSync, unlinkSync, existsSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';
import { promisify } from 'util';
import { findRscript } from './discovery.js';
import { loadConfig } from './config.js';
const execFileAsync = promisify(execFile);
/**
 * Get Rscript path from config or discovery
 */
export function getRscriptPath() {
    const config = loadConfig();
    // If config has a valid path, use it
    if (config.r_path && config.r_path !== 'Rscript') {
        if (existsSync(config.r_path)) {
            return config.r_path;
        }
    }
    // Try to find it
    const found = findRscript();
    if (found)
        return found;
    // Default fallback
    return 'Rscript';
}
/**
 * Execute raw R code
 */
export async function runRCode(code, timeout = 300000) {
    const rscript = getRscriptPath();
    // Create temp file for R code
    const tempFile = join(tmpdir(), `pkpdbuilder_${Date.now()}_${Math.random().toString(36).slice(2)}.R`);
    try {
        writeFileSync(tempFile, code, 'utf-8');
        const { stdout, stderr } = await execFileAsync(rscript, [tempFile], {
            timeout,
            maxBuffer: 10 * 1024 * 1024, // 10MB
        });
        return {
            success: true,
            stdout: stdout || '',
            stderr: stderr || '',
        };
    }
    catch (error) {
        const err = error;
        return {
            success: false,
            stdout: err.stdout || '',
            stderr: err.stderr || '',
            error: err.message,
        };
    }
    finally {
        // Cleanup temp file
        try {
            if (existsSync(tempFile)) {
                unlinkSync(tempFile);
            }
        }
        catch (e) {
            // Ignore cleanup errors
        }
    }
}
/**
 * Execute an R script with JSON arguments
 *
 * The R script should:
 * 1. Read input.json from the temp directory
 * 2. Process the data
 * 3. Write output.json to the temp directory
 */
export async function runRScript(scriptPath, args = {}, timeout = 300000) {
    const rscript = getRscriptPath();
    if (!existsSync(scriptPath)) {
        return {
            success: false,
            stdout: '',
            stderr: `Script not found: ${scriptPath}`,
            error: `Script not found: ${scriptPath}`,
        };
    }
    // Create temp directory for I/O
    const tempId = `pkpdbuilder_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    const inputFile = join(tmpdir(), `${tempId}_input.json`);
    const outputFile = join(tmpdir(), `${tempId}_output.json`);
    try {
        // Write input args as JSON
        writeFileSync(inputFile, JSON.stringify(args, null, 2), 'utf-8');
        // Execute R script with input/output file paths as arguments
        const { stdout, stderr } = await execFileAsync(rscript, [scriptPath, inputFile, outputFile], {
            timeout,
            maxBuffer: 10 * 1024 * 1024, // 10MB
        });
        // Read result if output file was created
        let result = undefined;
        if (existsSync(outputFile)) {
            try {
                const resultJson = readFileSync(outputFile, 'utf-8');
                result = JSON.parse(resultJson);
            }
            catch (e) {
                // Output file exists but couldn't parse
                result = { error: 'Failed to parse R output JSON' };
            }
        }
        return {
            success: true,
            stdout: stdout || '',
            stderr: stderr || '',
            result,
        };
    }
    catch (error) {
        const err = error;
        return {
            success: false,
            stdout: err.stdout || '',
            stderr: err.stderr || '',
            error: err.message,
        };
    }
    finally {
        // Cleanup temp files
        try {
            if (existsSync(inputFile))
                unlinkSync(inputFile);
            if (existsSync(outputFile))
                unlinkSync(outputFile);
        }
        catch (e) {
            // Ignore cleanup errors
        }
    }
}
/**
 * Quick check if R is available and working
 */
export async function testR() {
    const result = await runRCode('cat("OK")');
    return result.success && result.stdout.includes('OK');
}
/**
 * Install an R package
 */
export async function installRPackage(packageName) {
    const code = `
    if (!require("${packageName}", quietly = TRUE)) {
      install.packages("${packageName}", repos = "https://cloud.r-project.org/")
      if (require("${packageName}", quietly = TRUE)) {
        cat("SUCCESS: ${packageName} installed\\n")
      } else {
        stop("FAILED: Could not install ${packageName}")
      }
    } else {
      cat("ALREADY_INSTALLED: ${packageName}\\n")
    }
  `;
    return await runRCode(code, 600000); // 10 minute timeout for package installation
}
/**
 * Check if a package is installed
 */
export async function isPackageInstalled(packageName) {
    const code = `cat(as.character(require("${packageName}", quietly = TRUE)))`;
    const result = await runRCode(code);
    return result.success && result.stdout.trim() === 'TRUE';
}
/**
 * Get installed R packages
 */
export async function getInstalledPackages() {
    const code = `cat(paste(installed.packages()[,"Package"], collapse=","))`;
    const result = await runRCode(code);
    if (!result.success)
        return [];
    return result.stdout
        .trim()
        .split(',')
        .map(p => p.trim())
        .filter(p => p.length > 0);
}
//# sourceMappingURL=r-bridge.js.map