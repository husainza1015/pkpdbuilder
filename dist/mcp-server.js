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
function mcpWrap(handler) {
    return async (args) => {
        try {
            const result = await handler(args);
            return {
                content: [
                    {
                        type: 'text',
                        text: typeof result === 'string' ? result : JSON.stringify(result, null, 2),
                    },
                ],
            };
        }
        catch (error) {
            return {
                content: [
                    {
                        type: 'text',
                        text: JSON.stringify({ success: false, error: error.message }),
                    },
                ],
                isError: true,
            };
        }
    };
}
// ── Data Tools ──────────────────────────────────────────────
// Parameter names must match what handler functions access from args
server.tool('load_dataset', 'Load a PK/PD dataset (CSV, NONMEM format). Validates required columns (ID, TIME, DV). Returns summary: rows, subjects, observations, doses.', {
    file_path: z.string().describe('Path to the dataset file (CSV)'),
    delimiter: z.string().optional().describe('Column delimiter (default: auto-detect)'),
}, mcpWrap(dataTools.loadDataset));
server.tool('summarize_dataset', 'Get detailed summary of the currently loaded dataset: column types, distributions, subject counts.', {}, mcpWrap(dataTools.summarizeDataset));
server.tool('plot_data', 'Generate exploratory PK/PD plots: spaghetti (individual profiles), scatter, histogram. Saves to output directory.', {
    plot_type: z.string().optional().describe('Plot type: spaghetti, scatter, histogram'),
    log_y: z.boolean().optional().describe('Use log scale for Y-axis'),
}, mcpWrap(dataTools.plotData));
server.tool('dataset_qc', 'Quality checks: missing values, duplicates, outliers, LLOQ violations.', {
    lloq: z.number().optional().describe('Lower limit of quantification'),
}, mcpWrap(dataTools.datasetQC));
server.tool('handle_blq', 'Handle Below Limit of Quantification data using M1/M3/M5 methods.', {
    method: z.string().describe('BLQ method: drop, half_lloq, impute'),
    lloq: z.number().describe('LLOQ value'),
}, mcpWrap(dataTools.handleBLQ));
// ── Modeling Tools ──────────────────────────────────────────
server.tool('fit_model', 'Fit a population PK model using nlmixr2. Provide nlmixr2 model code, or describe the model and let the tool generate the code. Supports FOCEI, SAEM estimation.', {
    model_code: z.string().describe('nlmixr2 model code (ini + model blocks)'),
    model_name: z.string().optional().describe('Name for this model fit'),
    estimation_method: z.string().optional().describe('Estimation method: focei (default), saem, foce'),
}, mcpWrap(modelingTools.fitModel));
server.tool('fit_from_library', 'Fit a pre-defined model from the built-in library (e.g., pk_1cmt_oral_1abs, pk_2cmt_iv_bolus).', {
    library_model_name: z.string().describe('Model name from library'),
    model_name: z.string().optional().describe('Custom name for this fit'),
}, mcpWrap(modelingTools.fitFromLibrary));
server.tool('compare_models', 'Compare fitted models by OFV, AIC, BIC. Returns comparison table and recommendation.', {
    model_names: z.array(z.string()).describe('Names of fitted models to compare'),
}, mcpWrap(modelingTools.compareModels));
server.tool('list_model_library', 'List all available models in the pharmacometrics model library.', {
    category: z.string().optional().describe('Filter: pk, pd, pkpd, tmdd, advanced'),
}, mcpWrap(modelingTools.listModelLibrary));
server.tool('get_model_code', 'Get nlmixr2/NONMEM code for a model from the library.', {
    model_name: z.string().describe('Model name from library'),
}, mcpWrap(modelingTools.getModelCode));
// ── Diagnostics Tools ───────────────────────────────────────
server.tool('goodness_of_fit', 'Generate GOF plots: DV vs PRED, DV vs IPRED, CWRES vs TIME, CWRES vs PRED.', {
    model_name: z.string().optional().describe('Model name'),
}, mcpWrap(diagnosticsTools.goodnessOfFit));
server.tool('vpc', 'Visual Predictive Check: simulate from model and compare to observed data.', {
    model_name: z.string().optional().describe('Model name'),
    n_sim: z.number().optional().describe('Number of simulations (default 200)'),
    prediction_corrected: z.boolean().optional().describe('Use prediction correction'),
}, mcpWrap(diagnosticsTools.vpc));
server.tool('eta_plots', 'ETA distribution plots and shrinkage assessment.', {
    model_name: z.string().optional().describe('Model name'),
}, mcpWrap(diagnosticsTools.etaPlots));
server.tool('individual_fits', 'Individual subject fit plots (observed vs predicted per subject).', {
    model_name: z.string().optional().describe('Model name'),
    subject_ids: z.array(z.string()).optional().describe('Subject IDs to plot (default: first 9)'),
}, mcpWrap(diagnosticsTools.individualFits));
server.tool('parameter_table', 'Formatted parameter table with estimates, RSE, IIV, shrinkage.', {
    model_name: z.string().optional().describe('Model name'),
}, mcpWrap(diagnosticsTools.parameterTable));
// ── NCA Tools ───────────────────────────────────────────────
server.tool('run_nca', 'Non-Compartmental Analysis using PKNCA: AUC, Cmax, Tmax, t½, CL/F, Vd/F.', {
    dataset_path: z.string().optional().describe('Path to dataset (uses loaded dataset if omitted)'),
    dose_col: z.string().optional().describe('Dose column name'),
}, mcpWrap(ncaTools.runNca));
// ── Simulation Tools ────────────────────────────────────────
server.tool('simulate_regimen', 'Simulate a dosing regimen using mrgsolve (concentration-time profiles).', {
    model_name: z.string().optional().describe('Model name'),
    dose: z.number().describe('Dose amount'),
    interval: z.number().describe('Dosing interval (hours)'),
    n_doses: z.number().optional().describe('Number of doses'),
}, mcpWrap(simulationTools.simulateRegimen));
server.tool('population_simulation', 'Simulate a virtual population with inter-individual variability.', {
    model_name: z.string().optional().describe('Model name'),
    n_subjects: z.number().describe('Number of subjects'),
    dose: z.number().describe('Dose amount'),
}, mcpWrap(simulationTools.populationSimulation));
// ── Literature Tools ────────────────────────────────────────
server.tool('search_pubmed', 'Search PubMed for published PopPK/PD models and pharmacometric literature.', {
    query: z.string().describe('Search query (e.g., "vancomycin population pharmacokinetics")'),
    max_results: z.number().optional().describe('Max results (default 10)'),
}, mcpWrap(literatureTools.searchPubmed));
server.tool('lookup_drug', 'Look up published PK parameters for a drug from the PKPDBuilder database.', {
    drug_name: z.string().describe('Drug name (generic or brand)'),
}, mcpWrap(literatureTools.lookupDrug));
// ── Covariate Tools ─────────────────────────────────────────
server.tool('covariate_screening', 'Screen covariates for significance using univariate analysis (GAM/correlation).', {
    model_name: z.string().optional().describe('Base model name'),
    covariates: z.array(z.string()).optional().describe('Covariate columns to screen'),
}, mcpWrap(covariateTools.covariateScreening));
server.tool('stepwise_covariate_model', 'Stepwise Covariate Modeling (SCM): forward inclusion + backward elimination.', {
    model_name: z.string().optional().describe('Base model name'),
    covariates: z.array(z.string()).describe('Covariates to test'),
}, mcpWrap(covariateTools.stepwiseCovariateModel));
server.tool('forest_plot', 'Forest plot showing covariate effects on PK parameters.', {
    model_name: z.string().optional().describe('Covariate model name'),
}, mcpWrap(covariateTools.forestPlot));
// ── Export/Import Tools ─────────────────────────────────────
server.tool('export_model', 'Export a fitted nlmixr2 model to NONMEM, Monolix, or Phoenix NLME format.', {
    model_name: z.string().describe('Model name'),
    target: z.string().describe('Target backend: nonmem, monolix, phoenix'),
}, mcpWrap(exportTools.exportModel));
server.tool('import_model', 'Import a model from NONMEM/Monolix/Phoenix into nlmixr2.', {
    file_path: z.string().describe('Path to the model control stream'),
    source_format: z.string().describe('Source format: nonmem, monolix, phoenix'),
}, mcpWrap(exportTools.importModel));
server.tool('list_backends', 'List available modeling backends and their installation status.', {}, mcpWrap(exportTools.listBackends));
// ── Report Tools ────────────────────────────────────────────
server.tool('generate_report', 'Generate an FDA-style PopPK analysis report (HTML).', {
    model_name: z.string().optional().describe('Final model name'),
    title: z.string().optional().describe('Report title'),
}, mcpWrap(reportTools.generateReport));
server.tool('build_shiny_app', 'Generate an interactive R Shiny simulator app from a fitted model.', {
    model_name: z.string().optional().describe('Model name'),
    app_name: z.string().optional().describe('App name'),
}, mcpWrap(reportTools.buildShinyApp));
server.tool('generate_beamer_slides', 'Generate Beamer/LaTeX presentation slides summarizing the analysis.', {
    model_name: z.string().optional().describe('Model name'),
    title: z.string().optional().describe('Presentation title'),
}, mcpWrap(reportTools.generateBeamerSlides));
// ── Memory Tools ────────────────────────────────────────────
server.tool('pkpd_memory_read', 'Read PKPDBuilder project memory (previous analyses, model decisions, parameter history). Separate from CLAUDE.md — this stores structured pharmacometrics context.', {}, mcpWrap(memoryTools.memoryRead));
server.tool('pkpd_memory_write', 'Write to PKPDBuilder project memory. Use for logging model selections, parameter estimates, analysis decisions.', {
    key: z.string().describe('Memory key (e.g., "base_model", "final_model", "covariates_tested")'),
    value: z.string().describe('Value to store'),
}, mcpWrap(memoryTools.memoryWrite));
server.tool('pkpd_memory_search', 'Search PKPDBuilder project memory for past analysis decisions and context.', {
    query: z.string().describe('Search query'),
}, mcpWrap(memoryTools.memorySearch));
server.tool('init_pkpd_project', 'Initialize a new PKPDBuilder project: creates .pkpdbuilder/ directory with memory and output structure.', {
    project_name: z.string().describe('Project name'),
    drug_name: z.string().optional().describe('Drug name'),
}, mcpWrap(memoryTools.initProject));
// ── Start Server ────────────────────────────────────────────
async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
}
main().catch(console.error);
//# sourceMappingURL=mcp-server.js.map