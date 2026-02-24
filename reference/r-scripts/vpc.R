#!/usr/bin/env Rscript
# Visual Predictive Check
suppressPackageStartupMessages({
  library(nlmixr2)
  library(vpc)
  library(ggplot2)
  library(jsonlite)
})

args_file <- Sys.getenv("PMX_ARGS_FILE")
result_file <- Sys.getenv("PMX_RESULT_FILE")
args <- fromJSON(args_file)

output_dir <- args$output_dir
model_name <- args$model_name
n_sim <- args$n_sim
pred_corr <- args$prediction_corrected

# Load fit object
fit_file <- file.path(output_dir, paste0(model_name, "_fit.rds"))
if (!file.exists(fit_file)) {
  write(toJSON(list(success = FALSE, error = "Fit object not found. Run fit_model first."), auto_unbox = TRUE), result_file)
  quit(status = 0)
}

tryCatch({
  fit <- readRDS(fit_file)
  
  # Generate VPC
  vpc_result <- vpcPlot(fit, n = n_sim, show = list(obs_dv = TRUE),
                         ylab = "Concentration", xlab = "Time")
  
  out_path <- file.path(output_dir, paste0("vpc_", model_name, ".png"))
  ggsave(out_path, vpc_result, width = 10, height = 6, dpi = 150)
  
  write(toJSON(list(
    success = TRUE,
    plot_path = out_path,
    n_simulations = n_sim,
    prediction_corrected = pred_corr,
    message = sprintf("VPC saved: %s (%d simulations)", out_path, n_sim)
  ), auto_unbox = TRUE), result_file)
  
}, error = function(e) {
  write(toJSON(list(
    success = FALSE,
    error = paste("VPC generation failed:", conditionMessage(e))
  ), auto_unbox = TRUE), result_file)
})
