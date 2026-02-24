#!/usr/bin/env node
/**
 * PKPDBuilder MCP Server
 * Exposes pharmacometric tools to Claude Code via Model Context Protocol
 * 
 * Author: Husain Z Attarwala, PhD
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { runRScript, runRCode, findRscript } from './r-bridge.js';
import { getModelLibrary, getModelCode } from './models.js';
import { searchPubmed, lookupDrug } from './literature.js';

const server = new McpServer({
  name: 'pkpdbuilder',
  version: '0.3.0',
});

// ── Data Tools ──────────────────────────────────────────

server.tool(
  'load_dataset',
  'Load a PK/PD dataset from CSV or NONMEM format. Validates required columns (ID, TIME, DV).',
  {
    file_path: z.string().describe('Path to the CSV file'),
  },
  async ({ file_path }) => {
    const result = await runRScript('load_dataset.R', { file_path });
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

server.tool(
  'summarize_dataset',
  'Generate summary statistics of the loaded dataset: per-subject counts, covariate distributions, dosing info.',
  {
    file_path: z.string().describe('Path to the loaded dataset CSV'),
  },
  async ({ file_path }) => {
    const code = `
    library(jsonlite)
    d <- read.csv("${file_path}")
    n_subj <- length(unique(d$ID))
    n_obs <- nrow(d[d$EVID==0 | is.na(d$EVID),])
    n_dose <- nrow(d[d$EVID==1,])
    covs <- setdiff(names(d), c("ID","TIME","DV","AMT","EVID","MDV","CMT","RATE","SS","II","ADDL"))
    summary_list <- list(
      n_subjects = n_subj, n_observations = n_obs, n_doses = n_dose,
      columns = names(d), covariates = covs,
      time_range = range(d$TIME, na.rm=TRUE),
      dv_range = range(d$DV[d$DV > 0], na.rm=TRUE)
    )
    cat(toJSON(summary_list, auto_unbox=TRUE))
    `;
    const result = await runRCode(code);
    return { content: [{ type: 'text', text: result.success ? result.stdout : `Error: ${result.error}` }] };
  }
);

server.tool(
  'plot_data',
  'Generate exploratory PK plots: spaghetti, individual profiles, or dose-normalized. Saves PNG to output directory.',
  {
    file_path: z.string().describe('Path to dataset CSV'),
    plot_type: z.enum(['spaghetti', 'individual', 'dose_normalized']).default('spaghetti').describe('Type of plot'),
    output_dir: z.string().default('./pkpdbuilder_output').describe('Output directory for PNG'),
  },
  async ({ file_path, plot_type, output_dir }) => {
    const result = await runRScript('plot_data.R', { file_path, plot_type, output_dir });
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

server.tool(
  'dataset_qc',
  'Run quality checks: missing values, duplicate records, negative concentrations, time sequence errors.',
  {
    file_path: z.string().describe('Path to dataset CSV'),
  },
  async ({ file_path }) => {
    const result = await runRScript('dataset_qc.R', { file_path });
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

server.tool(
  'handle_blq',
  'Handle below-limit-of-quantification data using standard methods (M1-M7).',
  {
    file_path: z.string().describe('Path to dataset CSV'),
    method: z.enum(['M1', 'M3', 'M5', 'M6', 'M7']).default('M1').describe('BLQ handling method'),
    lloq: z.number().describe('Lower limit of quantification'),
  },
  async ({ file_path, method, lloq }) => {
    const result = await runRScript('handle_blq.R', { file_path, method, lloq });
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

// ── Modeling Tools ──────────────────────────────────────

server.tool(
  'fit_model',
  'Fit a population PK model using nlmixr2. Supports 1/2/3-CMT, oral/IV, linear/MM elimination, covariates.',
  {
    file_path: z.string().describe('Path to dataset CSV'),
    model_type: z.string().describe('Model type (e.g., "1cmt_oral", "2cmt_iv_bolus")'),
    error_model: z.enum(['proportional', 'additive', 'combined']).default('proportional'),
    estimation: z.enum(['saem', 'focei', 'nlme']).default('saem'),
    covariates: z.string().optional().describe('Covariate model string (e.g., "CL~WT, V~WT")'),
    output_dir: z.string().default('./pkpdbuilder_output'),
  },
  async ({ file_path, model_type, error_model, estimation, covariates, output_dir }) => {
    const result = await runRScript('fit_nlmixr2.R', { 
      file_path, model_type, error_model, estimation, covariates, output_dir 
    });
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

server.tool(
  'fit_from_library',
  'Fit a pre-built model from the PKPDBuilder model library to your dataset.',
  {
    file_path: z.string().describe('Path to dataset CSV'),
    model_name: z.string().describe('Model name from library (use list_model_library to see options)'),
    output_dir: z.string().default('./pkpdbuilder_output'),
  },
  async ({ file_path, model_name, output_dir }) => {
    const result = await runRScript('fit_library_model.R', { file_path, model_name, output_dir });
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

server.tool(
  'compare_models',
  'Compare fitted models by OFV, AIC, BIC. Returns comparison table with recommendation.',
  {
    output_dir: z.string().default('./pkpdbuilder_output').describe('Directory containing model fit results'),
  },
  async ({ output_dir }) => {
    const code = `
    library(jsonlite)
    files <- list.files("${output_dir}", pattern="*_results.json", full.names=TRUE)
    if (length(files) == 0) { cat(toJSON(list(success=FALSE, error="No model results found"), auto_unbox=TRUE)); quit() }
    results <- lapply(files, function(f) fromJSON(readLines(f, warn=FALSE)))
    comparison <- do.call(rbind, lapply(results, function(r) {
      data.frame(model=r$model_name, OFV=r$ofv, AIC=r$aic, BIC=r$bic, npar=r$n_params, stringsAsFactors=FALSE)
    }))
    comparison <- comparison[order(comparison$BIC),]
    cat(toJSON(list(success=TRUE, comparison=comparison, recommended=comparison$model[1]), auto_unbox=TRUE))
    `;
    const result = await runRCode(code);
    return { content: [{ type: 'text', text: result.success ? result.stdout : `Error: ${result.error}` }] };
  }
);

server.tool(
  'list_model_library',
  'List all 59 pre-built PK/PD models available in the library.',
  {
    category: z.enum(['all', 'pk', 'pd', 'pkpd', 'tmdd', 'advanced']).default('all').describe('Filter by category'),
  },
  async ({ category }) => {
    const models = getModelLibrary(category);
    return { content: [{ type: 'text', text: JSON.stringify(models, null, 2) }] };
  }
);

server.tool(
  'get_model_code',
  'Get the full nlmixr2 R code for a model from the library.',
  {
    model_name: z.string().describe('Model name (e.g., "pk_2cmt_iv_bolus")'),
  },
  async ({ model_name }) => {
    const code = getModelCode(model_name);
    return { content: [{ type: 'text', text: JSON.stringify(code, null, 2) }] };
  }
);

// ── Diagnostics Tools ───────────────────────────────────

server.tool(
  'goodness_of_fit',
  'Generate standard GOF diagnostic plots: DV vs PRED, DV vs IPRED, CWRES vs TIME, CWRES vs PRED.',
  {
    model_name: z.string().describe('Model name (matches fit output filename)'),
    output_dir: z.string().default('./pkpdbuilder_output'),
  },
  async ({ model_name, output_dir }) => {
    const result = await runRScript('diagnostics.R', { model_name, output_dir, plot_type: 'gof' });
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

server.tool(
  'vpc',
  'Run Visual Predictive Check. Simulates N replicates and compares observed vs predicted percentiles.',
  {
    model_name: z.string().describe('Model name'),
    n_sim: z.number().default(200).describe('Number of simulations'),
    output_dir: z.string().default('./pkpdbuilder_output'),
  },
  async ({ model_name, n_sim, output_dir }) => {
    const result = await runRScript('vpc.R', { model_name, n_sim, output_dir });
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

server.tool(
  'eta_plots',
  'Generate ETA diagnostic plots: distributions, ETA vs covariates, ETA correlations.',
  {
    model_name: z.string().describe('Model name'),
    output_dir: z.string().default('./pkpdbuilder_output'),
  },
  async ({ model_name, output_dir }) => {
    const result = await runRScript('eta_plots.R', { model_name, output_dir });
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

server.tool(
  'individual_fits',
  'Generate individual observed vs predicted plots for each subject.',
  {
    model_name: z.string().describe('Model name'),
    output_dir: z.string().default('./pkpdbuilder_output'),
  },
  async ({ model_name, output_dir }) => {
    const result = await runRScript('individual_fits.R', { model_name, output_dir });
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

server.tool(
  'parameter_table',
  'Generate formatted parameter table: fixed effects, IIV (%CV), residual error, RSE%, shrinkage.',
  {
    model_name: z.string().describe('Model name'),
    output_dir: z.string().default('./pkpdbuilder_output'),
  },
  async ({ model_name, output_dir }) => {
    const code = `
    library(jsonlite)
    fit <- readRDS("${output_dir}/${model_name}_fit.rds")
    params <- as.data.frame(fixef(fit))
    cat(toJSON(list(success=TRUE, parameters=params), auto_unbox=TRUE))
    `;
    const result = await runRCode(code);
    return { content: [{ type: 'text', text: result.success ? result.stdout : `Error: ${result.error}` }] };
  }
);

// ── NCA Tool ────────────────────────────────────────────

server.tool(
  'run_nca',
  'Run non-compartmental analysis using PKNCA. Calculates AUC, Cmax, Tmax, t1/2, CL/F, Vd/F per subject.',
  {
    file_path: z.string().describe('Path to dataset CSV'),
    dose_col: z.string().default('AMT').describe('Dose column name'),
    output_dir: z.string().default('./pkpdbuilder_output'),
  },
  async ({ file_path, dose_col, output_dir }) => {
    const result = await runRScript('run_nca.R', { file_path, dose_col, output_dir });
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

// ── Simulation Tools ────────────────────────────────────

server.tool(
  'simulate_regimen',
  'Simulate concentration-time profiles for a dosing regimen using mrgsolve.',
  {
    model_name: z.string().describe('Model name or library model'),
    dose: z.number().describe('Dose amount (mg)'),
    interval: z.number().describe('Dosing interval (hours)'),
    n_doses: z.number().default(10).describe('Number of doses'),
    output_dir: z.string().default('./pkpdbuilder_output'),
  },
  async ({ model_name, dose, interval, n_doses, output_dir }) => {
    const result = await runRScript('simulate_mrgsolve.R', { model_name, dose, interval, n_doses, output_dir });
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

server.tool(
  'population_simulation',
  'Simulate a virtual population using fitted model parameters with IIV.',
  {
    model_name: z.string().describe('Model name'),
    n_subjects: z.number().default(100).describe('Number of virtual subjects'),
    dose: z.number().describe('Dose amount (mg)'),
    output_dir: z.string().default('./pkpdbuilder_output'),
  },
  async ({ model_name, n_subjects, dose, output_dir }) => {
    const result = await runRScript('population_sim.R', { model_name, n_subjects, dose, output_dir });
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

// ── Literature Tools ────────────────────────────────────

server.tool(
  'search_pubmed',
  'Search PubMed for pharmacokinetic/pharmacometric publications. Returns titles, PMIDs, abstracts.',
  {
    query: z.string().describe('Search query'),
    max_results: z.number().default(5).describe('Maximum results to return'),
  },
  async ({ query, max_results }) => {
    const result = await searchPubmed(query, max_results);
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

server.tool(
  'lookup_drug',
  'Look up published PK parameters for a drug from the PKPDBuilder database.',
  {
    drug_name: z.string().describe('Drug name'),
  },
  async ({ drug_name }) => {
    const result = await lookupDrug(drug_name);
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

// ── Covariate Tools ─────────────────────────────────────

server.tool(
  'covariate_screening',
  'Screen covariates for potential effects on PK parameters. Generates univariate plots and statistics.',
  {
    model_name: z.string().describe('Model name'),
    output_dir: z.string().default('./pkpdbuilder_output'),
  },
  async ({ model_name, output_dir }) => {
    const result = await runRScript('covariate_screen.R', { model_name, output_dir });
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

server.tool(
  'stepwise_covariate_model',
  'Run stepwise covariate model building: forward addition + backward elimination.',
  {
    model_name: z.string().describe('Base model name'),
    covariates: z.string().describe('Covariates to test (comma-separated)'),
    output_dir: z.string().default('./pkpdbuilder_output'),
  },
  async ({ model_name, covariates, output_dir }) => {
    const result = await runRScript('covariate_scm.R', { model_name, covariates, output_dir });
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

server.tool(
  'forest_plot',
  'Generate forest plot showing covariate effects on PK parameters.',
  {
    model_name: z.string().describe('Model name'),
    output_dir: z.string().default('./pkpdbuilder_output'),
  },
  async ({ model_name, output_dir }) => {
    const result = await runRScript('forest_plot.R', { model_name, output_dir });
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

// ── Export Tools ─────────────────────────────────────────

server.tool(
  'export_model',
  'Export a fitted nlmixr2 model to NONMEM, Monolix, or Julia/Pumas format.',
  {
    model_name: z.string().describe('Model name'),
    format: z.enum(['nonmem', 'monolix', 'pumas']).describe('Target format'),
    output_dir: z.string().default('./pkpdbuilder_output'),
  },
  async ({ model_name, format, output_dir }) => {
    const result = await runRScript('export_model.R', { model_name, format, output_dir });
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

server.tool(
  'import_model',
  'Import a model from NONMEM or Monolix into nlmixr2 format.',
  {
    file_path: z.string().describe('Path to model file (.ctl or .mlxtran)'),
    format: z.enum(['nonmem', 'monolix']).describe('Source format'),
  },
  async ({ file_path, format }) => {
    const result = await runRScript('import_model.R', { file_path, format });
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

// ── Report Tools ────────────────────────────────────────

server.tool(
  'generate_report',
  'Generate a PopPK analysis report in HTML format with all diagnostics and parameter tables.',
  {
    model_name: z.string().describe('Model name'),
    drug_name: z.string().optional().describe('Drug name for report title'),
    output_dir: z.string().default('./pkpdbuilder_output'),
  },
  async ({ model_name, drug_name, output_dir }) => {
    const result = await runRScript('generate_report.R', { model_name, drug_name, output_dir });
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

server.tool(
  'build_shiny_app',
  'Generate an interactive R Shiny app from a fitted PK model.',
  {
    model_name: z.string().describe('Model name'),
    output_dir: z.string().default('./pkpdbuilder_output'),
  },
  async ({ model_name, output_dir }) => {
    const result = await runRScript('build_shiny.R', { model_name, output_dir });
    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
  }
);

// ── Start Server ────────────────────────────────────────

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch(console.error);
