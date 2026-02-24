/**
 * Data loading, validation, and exploration tools
 * Author: Husain Z Attarwala, PhD
 */
import { existsSync, readFileSync, writeFileSync } from 'fs';
import { join } from 'path';
import { runRScript } from '../r-bridge.js';
import { ensureOutputDir, loadConfig } from '../config.js';
// Module-level state for loaded dataset
let currentDataset = null;
let currentDatasetPath = '';
export const loadDatasetTool = {
    name: 'load_dataset',
    description: 'Load a pharmacokinetic dataset from CSV or NONMEM format. Validates required columns (ID, TIME, DV). Accepts standard NONMEM columns: ID, TIME, DV, AMT, EVID, MDV, CMT, WT, AGE, SEX, etc.',
    input_schema: {
        type: 'object',
        properties: {
            file_path: {
                type: 'string',
                description: 'Path to the CSV dataset file',
            },
            delimiter: {
                type: 'string',
                description: 'Column delimiter (default: auto-detect comma or whitespace)',
            },
        },
        required: ['file_path'],
    },
};
export async function loadDataset(args) {
    if (!existsSync(args.file_path)) {
        return { success: false, error: `File not found: ${args.file_path}` };
    }
    const rCode = `
    input_file <- commandArgs(trailingOnly=TRUE)[1]
    output_file <- commandArgs(trailingOnly=TRUE)[2]
    
    # Read args from input JSON
    args <- jsonlite::fromJSON(input_file)
    file_path <- args$file_path
    
    # Read dataset
    df <- tryCatch({
      read.csv(file_path, stringsAsFactors=FALSE)
    }, error = function(e) {
      read.table(file_path, header=TRUE, stringsAsFactors=FALSE)
    })
    
    # Normalize column names
    colnames(df) <- toupper(trimws(colnames(df)))
    
    # Check required columns
    required <- c("ID", "TIME", "DV")
    missing <- setdiff(required, colnames(df))
    
    if (length(missing) > 0) {
      result <- list(
        success = FALSE,
        error = paste("Missing columns:", paste(missing, collapse=", ")),
        columns = colnames(df)
      )
    } else {
      # Basic summary
      result <- list(
        success = TRUE,
        rows = nrow(df),
        columns = ncol(df),
        column_names = colnames(df),
        subjects = length(unique(df$ID)),
        observations = sum(df$MDV == 0 | is.na(df$MDV)),
        doses = sum(df$AMT > 0 | (!is.na(df$EVID) & df$EVID == 1), na.rm=TRUE),
        message = paste("Loaded", nrow(df), "rows,", length(unique(df$ID)), "subjects")
      )
      
      # Save to temp for other tools
      write.csv(df, file.path(dirname(output_file), "current_dataset.csv"), row.names=FALSE)
    }
    
    writeLines(jsonlite::toJSON(result, auto_unbox=TRUE), output_file)
  `;
    const scriptPath = join(ensureOutputDir(loadConfig()), 'load_dataset.R');
    writeFileSync(scriptPath, rCode);
    const result = await runRScript(scriptPath, { file_path: args.file_path });
    if (result.success && result.result) {
        currentDatasetPath = args.file_path;
        return result.result;
    }
    return { success: false, error: result.stderr || 'Failed to load dataset' };
}
export const summarizeDatasetTool = {
    name: 'summarize_dataset',
    description: 'Generate detailed summary statistics for the currently loaded dataset. Shows subject counts, observation ranges, dose info, covariate distributions.',
    input_schema: {
        type: 'object',
        properties: {},
        required: [],
    },
};
export async function summarizeDataset() {
    const config = loadConfig();
    const datasetPath = join(ensureOutputDir(config), 'current_dataset.csv');
    if (!existsSync(datasetPath)) {
        return { success: false, error: 'No dataset loaded. Use load_dataset first.' };
    }
    // Simple summary by reading the CSV
    try {
        const csvData = readFileSync(datasetPath, 'utf-8');
        const lines = csvData.split('\n').filter(l => l.trim());
        const header = lines[0].split(',');
        return {
            success: true,
            rows: lines.length - 1,
            columns: header.length,
            column_names: header,
            message: 'Dataset summary retrieved',
        };
    }
    catch (e) {
        return { success: false, error: e.message };
    }
}
export const plotDataTool = {
    name: 'plot_data',
    description: 'Generate exploratory plots for PK/PD data: spaghetti plots (individual profiles), scatter plots, histograms. Saves to output directory.',
    input_schema: {
        type: 'object',
        properties: {
            plot_type: {
                type: 'string',
                description: 'Type of plot: spaghetti, scatter, histogram',
            },
            log_y: {
                type: 'boolean',
                description: 'Use log scale for Y-axis',
            },
        },
        required: [],
    },
};
export async function plotData(args) {
    return {
        success: true,
        message: `Plot generation: ${args.plot_type || 'spaghetti'} (stub - R implementation needed)`,
        plot_file: 'data_plot.png',
    };
}
export const datasetQCTool = {
    name: 'dataset_qc',
    description: 'Quality control checks for the dataset: missing values, duplicates, outliers, LLOQ violations.',
    input_schema: {
        type: 'object',
        properties: {
            lloq: {
                type: 'number',
                description: 'Lower limit of quantification',
            },
        },
        required: [],
    },
};
export async function datasetQC(args) {
    return {
        success: true,
        message: 'Dataset QC completed (stub)',
        issues: [],
    };
}
export const handleBLQTool = {
    name: 'handle_blq',
    description: 'Handle below-LLOQ values in the dataset using specified method (drop, lloq/2, impute).',
    input_schema: {
        type: 'object',
        properties: {
            method: {
                type: 'string',
                description: 'Method: drop, half_lloq, impute',
            },
            lloq: {
                type: 'number',
                description: 'Lower limit of quantification',
            },
        },
        required: ['method', 'lloq'],
    },
};
export async function handleBLQ(args) {
    return {
        success: true,
        message: `BLQ handling: ${args.method} (stub)`,
        rows_affected: 0,
    };
}
//# sourceMappingURL=data.js.map