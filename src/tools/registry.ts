/**
 * Tool registry for pharmacometrics operations
 * Author: Husain Z Attarwala, PhD
 */

import { Tool } from '../providers/base.js';
import * as dataTools from './data.js';
import * as modelingTools from './modeling.js';
import * as diagnosticsTools from './diagnostics.js';
import * as ncaTools from './nca.js';
import * as simulationTools from './simulation.js';
import * as literatureTools from './literature.js';
import * as covariateTools from './covariate.js';
import * as exportTools from './export.js';
import * as reportTools from './report.js';
import * as memoryTools from './memory.js';

const TOOL_DEFINITIONS: Tool[] = [];
const TOOL_HANDLERS: Map<string, (args: any) => Promise<any>> = new Map();

/**
 * Register a tool
 */
export function registerTool(tool: Tool, handler: (args: any) => Promise<any>): void {
  TOOL_DEFINITIONS.push(tool);
  TOOL_HANDLERS.set(tool.name, handler);
}

/**
 * Get all registered tools
 */
export function getAllTools(): Tool[] {
  return TOOL_DEFINITIONS;
}

/**
 * Execute a tool by name
 */
export async function executeTool(name: string, args: Record<string, any>): Promise<any> {
  const handler = TOOL_HANDLERS.get(name);
  
  if (!handler) {
    return {
      success: false,
      error: `Unknown tool: ${name}`,
    };
  }

  try {
    const result = await handler(args);
    return result;
  } catch (error: any) {
    return {
      success: false,
      error: error.message || String(error),
    };
  }
}

// Register all tools from modules
export function initializeTools(): void {
  // Data tools
  registerTool(dataTools.loadDatasetTool, dataTools.loadDataset);
  registerTool(dataTools.summarizeDatasetTool, dataTools.summarizeDataset);
  registerTool(dataTools.plotDataTool, dataTools.plotData);
  registerTool(dataTools.datasetQCTool, dataTools.datasetQC);
  registerTool(dataTools.handleBLQTool, dataTools.handleBLQ);

  // Modeling tools
  registerTool(modelingTools.fitModelTool, modelingTools.fitModel);
  registerTool(modelingTools.fitFromLibraryTool, modelingTools.fitFromLibrary);
  registerTool(modelingTools.compareModelsTool, modelingTools.compareModels);
  registerTool(modelingTools.listModelLibraryTool, modelingTools.listModelLibrary);
  registerTool(modelingTools.getModelCodeTool, modelingTools.getModelCode);

  // Diagnostics tools
  registerTool(diagnosticsTools.goodnessOfFitTool, diagnosticsTools.goodnessOfFit);
  registerTool(diagnosticsTools.vpcTool, diagnosticsTools.vpc);
  registerTool(diagnosticsTools.etaPlotsTool, diagnosticsTools.etaPlots);
  registerTool(diagnosticsTools.individualFitsTool, diagnosticsTools.individualFits);
  registerTool(diagnosticsTools.parameterTableTool, diagnosticsTools.parameterTable);

  // NCA tools
  registerTool(ncaTools.runNcaTool, ncaTools.runNca);

  // Simulation tools
  registerTool(simulationTools.simulateRegimenTool, simulationTools.simulateRegimen);
  registerTool(simulationTools.populationSimulationTool, simulationTools.populationSimulation);

  // Literature tools
  registerTool(literatureTools.searchPubmedTool, literatureTools.searchPubmed);
  registerTool(literatureTools.lookupDrugTool, literatureTools.lookupDrug);

  // Covariate tools
  registerTool(covariateTools.covariateScreeningTool, covariateTools.covariateScreening);
  registerTool(covariateTools.stepwiseCovariateModelTool, covariateTools.stepwiseCovariateModel);
  registerTool(covariateTools.forestPlotTool, covariateTools.forestPlot);

  // Export tools
  registerTool(exportTools.exportModelTool, exportTools.exportModel);
  registerTool(exportTools.importModelTool, exportTools.importModel);
  registerTool(exportTools.listBackendsTool, exportTools.listBackends);

  // Report tools
  registerTool(reportTools.generateReportTool, reportTools.generateReport);
  registerTool(reportTools.buildShinyAppTool, reportTools.buildShinyApp);
  registerTool(reportTools.generateBeamerSlidesTool, reportTools.generateBeamerSlides);

  // Memory tools
  registerTool(memoryTools.memoryReadTool, memoryTools.memoryRead);
  registerTool(memoryTools.memoryWriteTool, memoryTools.memoryWrite);
  registerTool(memoryTools.memorySearchTool, memoryTools.memorySearch);
  registerTool(memoryTools.initProjectTool, memoryTools.initProject);
}

// Initialize all tools on module load
initializeTools();
