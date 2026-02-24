#!/usr/bin/env node
/**
 * PKPDBuilder MCP Server
 * Exposes pharmacometrics tools to Claude Code via Model Context Protocol
 * Author: Husain Z Attarwala, PhD
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

// Import tool handlers
import * as dataTools from './tools/data.js';
import * as modelingTools from './tools/modeling.js';
import * as diagnosticsTools from './tools/diagnostics.js';
import * as ncaTools from './tools/nca.js';
import * as simulationTools from './tools/simulation.js';
import * as literatureTools from './tools/literature.js';
import * as covariateTools from './tools/covariate.js';
import * as exportTools from './tools/export.js';
import * as reportTools from './tools/report.js';
import * as memoryTools from './tools/memory.js';

const server = new McpServer({
  name: 'pkpdbuilder',
  version: '0.3.0',
});

/**
 * Helper: wrap a tool handler for MCP (returns content array)
 */
function mcpWrap(handler: (args: any) => Promise<any>) {
  return async (args: any) => {
    try {
      const result = await handler(args);
      return {
        content: [
          {
            type: 'text' as const,
            text: typeof result === 'string' ? result : JSON.stringify(result, null, 2),
          },
        ],
      };
    } catch (error: any) {
      return {
        content: [
          {
            type: 'text' as const,
            text: JSON.stringify({ success: false, error: error.message }),
          },
        ],
        isError: true,
      };
    }
  };
}

// ── Data Tools ──────────────────────────────────────────────

server.tool(
  'load_dataset',
  'Load a PK/PD dataset (CSV, XPT, SAS7BDAT). Returns summary statistics and column info.',
  { path: z.string().describe('Path to the dataset file') },
  mcpWrap(dataTools.loadDataset)
);

server.tool(
  'summarize_dataset',
  'Get detailed summary of a loaded dataset: column types, missing values, distributions.',
  { path: z.string().describe('Path to the dataset file') },
  mcpWrap(dataTools.summarizeDataset)
);

server.tool(
  'plot_data',
  'Generate exploratory PK/PD plots (concentration-time, dose-response).',
  {
    path: z.string().describe('Path to the dataset file'),
    plot_type: z.string().optional().describe('Plot type: conc_time, dose_response, spaghetti'),
    output_dir: z.string().optional().describe('Output directory for plots'),
  },
  mcpWrap(dataTools.plotData)
);

server.tool(
  'dataset_qc',
  'Run quality checks on a NONMEM-format dataset: required columns, BLQ handling, dosing records.',
  { path: z.string().describe('Path to the dataset file') },
  mcpWrap(dataTools.datasetQC)
);

server.tool(
  'handle_blq',
  'Handle Below Limit of Quantification (BLQ) data using M1-M7 methods.',
  {
    path: z.string().describe('Path to the dataset file'),
    method: z.string().optional().describe('BLQ method: M1 (discard), M3 (likelihood), M5 (LOQ/2)'),
  },
  mcpWrap(dataTools.handleBLQ)
);

// ── Modeling Tools ──────────────────────────────────────────

server.tool(
  'fit_model',
  'Fit a population PK model using nlmixr2. Supports 1/2/3-CMT, oral/IV, with IIV on CL/V.',
  {
    dataset_path: z.string().describe('Path to the dataset'),
    model_type: z.string().describe('Model type: 1cmt_oral, 2cmt_iv, 2cmt_oral, etc.'),
    estimation: z.string().optional().describe('Estimation method: focei (default), saem, nlme'),
    output_dir: z.string().optional().describe('Output directory'),
  },
  mcpWrap(modelingTools.fitModel)
);

server.tool(
  'fit_from_library',
  'Fit a model from the built-in library of published PopPK models.',
  {
    model_id: z.string().describe('Model ID from the library'),
    dataset_path: z.string().describe('Path to the dataset'),
    output_dir: z.string().optional().describe('Output directory'),
  },
  mcpWrap(modelingTools.fitFromLibrary)
);

server.tool(
  'compare_models',
  'Compare fitted models using OFV, AIC, BIC, and diagnostic criteria.',
  {
    model_paths: z.array(z.string()).describe('Paths to model result files'),
    output_dir: z.string().optional().describe('Output directory'),
  },
  mcpWrap(modelingTools.compareModels)
);

server.tool(
  'list_model_library',
  'List available models in the built-in pharmacometrics model library.',
  {
    category: z.string().optional().describe('Filter by category: pk, pkpd, tmdd, pbpk'),
  },
  mcpWrap(modelingTools.listModelLibrary)
);

server.tool(
  'get_model_code',
  'Get nlmixr2/NONMEM/Monolix code for a model from the library.',
  {
    model_id: z.string().describe('Model ID'),
    backend: z.string().optional().describe('Backend: nlmixr2 (default), nonmem, monolix'),
  },
  mcpWrap(modelingTools.getModelCode)
);

// ── Diagnostics Tools ───────────────────────────────────────

server.tool(
  'goodness_of_fit',
  'Generate Goodness-of-Fit (GOF) diagnostic plots: DV vs PRED, DV vs IPRED, CWRES vs TIME.',
  {
    model_path: z.string().describe('Path to fitted model results'),
    output_dir: z.string().optional().describe('Output directory'),
  },
  mcpWrap(diagnosticsTools.goodnessOfFit)
);

server.tool(
  'vpc',
  'Generate Visual Predictive Check (VPC) plot.',
  {
    model_path: z.string().describe('Path to fitted model results'),
    n_sim: z.number().optional().describe('Number of simulations (default 200)'),
    output_dir: z.string().optional().describe('Output directory'),
  },
  mcpWrap(diagnosticsTools.vpc)
);

server.tool(
  'eta_plots',
  'Generate ETA distribution plots and ETA-covariate correlations.',
  {
    model_path: z.string().describe('Path to fitted model results'),
    output_dir: z.string().optional().describe('Output directory'),
  },
  mcpWrap(diagnosticsTools.etaPlots)
);

server.tool(
  'individual_fits',
  'Generate individual-level fit plots (observed vs predicted per subject).',
  {
    model_path: z.string().describe('Path to fitted model results'),
    subjects: z.array(z.number()).optional().describe('Subject IDs to plot (default: first 9)'),
    output_dir: z.string().optional().describe('Output directory'),
  },
  mcpWrap(diagnosticsTools.individualFits)
);

server.tool(
  'parameter_table',
  'Generate a formatted parameter table (estimates, RSE, IIV, shrinkage).',
  {
    model_path: z.string().describe('Path to fitted model results'),
    format: z.string().optional().describe('Output format: text (default), html, latex'),
  },
  mcpWrap(diagnosticsTools.parameterTable)
);

// ── NCA Tools ───────────────────────────────────────────────

server.tool(
  'run_nca',
  'Run Non-Compartmental Analysis (NCA) using PKNCA. Calculates AUC, Cmax, Tmax, t1/2, CL/F, Vd/F.',
  {
    dataset_path: z.string().describe('Path to the dataset'),
    dose_col: z.string().optional().describe('Dose column name'),
    output_dir: z.string().optional().describe('Output directory'),
  },
  mcpWrap(ncaTools.runNca)
);

// ── Simulation Tools ────────────────────────────────────────

server.tool(
  'simulate_regimen',
  'Simulate a dosing regimen using mrgsolve (concentration-time profiles).',
  {
    model_path: z.string().describe('Path to model or mrgsolve code'),
    dose: z.number().describe('Dose amount'),
    interval: z.number().describe('Dosing interval (hours)'),
    n_doses: z.number().optional().describe('Number of doses'),
    output_dir: z.string().optional().describe('Output directory'),
  },
  mcpWrap(simulationTools.simulateRegimen)
);

server.tool(
  'population_simulation',
  'Simulate a virtual population with inter-individual variability.',
  {
    model_path: z.string().describe('Path to model results'),
    n_subjects: z.number().optional().describe('Number of subjects (default 100)'),
    dose: z.number().describe('Dose amount'),
    interval: z.number().describe('Dosing interval (hours)'),
    output_dir: z.string().optional().describe('Output directory'),
  },
  mcpWrap(simulationTools.populationSimulation)
);

// ── Literature Tools ────────────────────────────────────────

server.tool(
  'search_pubmed',
  'Search PubMed for published PopPK/PKPD models and parameters.',
  {
    query: z.string().describe('Search query (e.g., "vancomycin population pharmacokinetics")'),
    max_results: z.number().optional().describe('Max results (default 10)'),
  },
  mcpWrap(literatureTools.searchPubmed)
);

server.tool(
  'lookup_drug',
  'Look up drug PK parameters from the PKPDBuilder database.',
  {
    drug_name: z.string().describe('Drug name (generic or brand)'),
  },
  mcpWrap(literatureTools.lookupDrug)
);

// ── Covariate Tools ─────────────────────────────────────────

server.tool(
  'covariate_screening',
  'Screen covariates for significance using univariate analysis (GAM/correlation).',
  {
    model_path: z.string().describe('Path to base model results'),
    covariates: z.array(z.string()).optional().describe('Covariate columns to screen'),
    output_dir: z.string().optional().describe('Output directory'),
  },
  mcpWrap(covariateTools.covariateScreening)
);

server.tool(
  'stepwise_covariate_model',
  'Run Stepwise Covariate Modeling (SCM) — forward inclusion + backward elimination.',
  {
    model_path: z.string().describe('Path to base model results'),
    covariates: z.array(z.string()).describe('Covariates to test'),
    output_dir: z.string().optional().describe('Output directory'),
  },
  mcpWrap(covariateTools.stepwiseCovariateModel)
);

server.tool(
  'forest_plot',
  'Generate a forest plot showing covariate effects on PK parameters.',
  {
    model_path: z.string().describe('Path to covariate model results'),
    output_dir: z.string().optional().describe('Output directory'),
  },
  mcpWrap(covariateTools.forestPlot)
);

// ── Export/Import Tools ─────────────────────────────────────

server.tool(
  'export_model',
  'Export a fitted model to NONMEM, Monolix, or Phoenix NLME format.',
  {
    model_path: z.string().describe('Path to nlmixr2 model results'),
    backend: z.string().describe('Target: nonmem, monolix, phoenix'),
    output_dir: z.string().optional().describe('Output directory'),
  },
  mcpWrap(exportTools.exportModel)
);

server.tool(
  'import_model',
  'Import a model from NONMEM, Monolix, or Phoenix NLME into nlmixr2.',
  {
    model_path: z.string().describe('Path to the model file'),
    backend: z.string().describe('Source: nonmem, monolix, phoenix'),
  },
  mcpWrap(exportTools.importModel)
);

server.tool(
  'list_backends',
  'List available modeling backends (nlmixr2, NONMEM, Monolix, Phoenix) and their status.',
  {},
  mcpWrap(exportTools.listBackends)
);

// ── Report Tools ────────────────────────────────────────────

server.tool(
  'generate_report',
  'Generate an FDA-style PopPK analysis report (HTML).',
  {
    model_path: z.string().describe('Path to final model results'),
    title: z.string().optional().describe('Report title'),
    output_dir: z.string().optional().describe('Output directory'),
  },
  mcpWrap(reportTools.generateReport)
);

server.tool(
  'build_shiny_app',
  'Generate an interactive R Shiny simulator app from a fitted model.',
  {
    model_path: z.string().describe('Path to model results'),
    app_name: z.string().optional().describe('App name'),
    output_dir: z.string().optional().describe('Output directory'),
  },
  mcpWrap(reportTools.buildShinyApp)
);

server.tool(
  'generate_beamer_slides',
  'Generate Beamer/LaTeX presentation slides summarizing the analysis.',
  {
    model_path: z.string().describe('Path to model results'),
    title: z.string().optional().describe('Presentation title'),
    output_dir: z.string().optional().describe('Output directory'),
  },
  mcpWrap(reportTools.generateBeamerSlides)
);

// ── Memory Tools ────────────────────────────────────────────

server.tool(
  'memory_read',
  'Read project memory (previous analyses, decisions, model history).',
  {
    project_dir: z.string().optional().describe('Project directory (default: cwd)'),
  },
  mcpWrap(memoryTools.memoryRead)
);

server.tool(
  'memory_write',
  'Write to project memory (log decisions, model selections, notes).',
  {
    key: z.string().describe('Memory key (e.g., "base_model", "final_model")'),
    value: z.string().describe('Value to store'),
    project_dir: z.string().optional().describe('Project directory (default: cwd)'),
  },
  mcpWrap(memoryTools.memoryWrite)
);

server.tool(
  'memory_search',
  'Search project memory for past decisions and analysis context.',
  {
    query: z.string().describe('Search query'),
    project_dir: z.string().optional().describe('Project directory (default: cwd)'),
  },
  mcpWrap(memoryTools.memorySearch)
);

server.tool(
  'init_project',
  'Initialize a new PKPDBuilder project directory with standard structure.',
  {
    project_name: z.string().describe('Project name'),
    project_dir: z.string().optional().describe('Parent directory (default: cwd)'),
  },
  mcpWrap(memoryTools.initProject)
);

// ── Start Server ────────────────────────────────────────────

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch(console.error);
