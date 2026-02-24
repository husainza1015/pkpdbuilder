#!/usr/bin/env Rscript
# Forest plot for covariate effects on PK parameters
suppressPackageStartupMessages({
  library(ggplot2)
  library(jsonlite)
  library(nlmixr2)
})

args_file <- Sys.getenv("PMX_ARGS_FILE")
result_file <- Sys.getenv("PMX_RESULT_FILE")
args <- fromJSON(args_file)

output_dir <- args$output_dir
model_name <- args$model_name
ref_area <- args$ref_area  # e.g., c(0.8, 1.25)

fit_file <- file.path(output_dir, paste0(model_name, "_fit.rds"))
if (!file.exists(fit_file)) {
  write(toJSON(list(success = FALSE, error = "Fit object not found."), auto_unbox = TRUE), result_file)
  quit(status = 0)
}

fit <- readRDS(fit_file)

tryCatch({
  # Extract covariate effects from model
  fe <- fixef(fit)
  se_vec <- tryCatch(sqrt(diag(vcov(fit))), error = function(e) rep(NA, length(fe)))
  
  # Find covariate parameters (named like dWTcl, dAGEcl, dSEXcl)
  cov_params <- grep("^d[A-Z]", names(fe), value = TRUE)
  
  if (length(cov_params) == 0) {
    # Try to find power/linear covariate params
    cov_params <- names(fe)[!grepl("^(t|l|eta|prop|add)", names(fe), ignore.case = TRUE)]
  }
  
  if (length(cov_params) == 0) {
    write(toJSON(list(
      success = TRUE,
      message = "No covariate parameters found in model. Run stepwise_covariate_model first.",
      plot_path = NULL
    ), auto_unbox = TRUE), result_file)
    quit(status = 0)
  }
  
  # Build forest plot data
  forest_data <- data.frame(
    parameter = character(),
    mid = numeric(),
    lower = numeric(),
    upper = numeric(),
    stringsAsFactors = FALSE
  )
  
  for (p in cov_params) {
    idx <- which(names(fe) == p)
    est <- fe[idx]
    se <- if (length(se_vec) >= idx) se_vec[idx] else NA
    
    if (!is.na(se)) {
      # For power/exponential covariates, effect is exp(est)
      mid <- exp(est)
      lower <- exp(est - 1.96 * se)
      upper <- exp(est + 1.96 * se)
      forest_data <- rbind(forest_data, data.frame(
        parameter = p, mid = mid, lower = lower, upper = upper
      ))
    }
  }
  
  if (nrow(forest_data) == 0) {
    write(toJSON(list(success = TRUE, message = "No estimable covariate effects.", plot_path = NULL), 
                 auto_unbox = TRUE), result_file)
    quit(status = 0)
  }
  
  # Reference area
  ref_lo <- if (!is.null(ref_area)) ref_area[1] else 0.8
  ref_hi <- if (!is.null(ref_area)) ref_area[2] else 1.25
  
  p <- ggplot(forest_data, aes(x = mid, y = reorder(parameter, mid))) +
    geom_rect(aes(xmin = ref_lo, xmax = ref_hi, ymin = -Inf, ymax = Inf),
              fill = "#e8f5e9", alpha = 0.5) +
    geom_vline(xintercept = 1, linetype = "dashed", color = "grey50") +
    geom_errorbarh(aes(xmin = lower, xmax = upper), height = 0.2, linewidth = 0.8) +
    geom_point(size = 3, color = "#1565c0") +
    labs(x = "Ratio to Reference", y = "", 
         title = paste("Covariate Effects —", model_name),
         subtitle = paste0("Shaded: ", ref_lo, "–", ref_hi, " equivalence bounds")) +
    theme_minimal(base_size = 12) +
    theme(plot.title = element_text(face = "bold"))
  
  out_path <- file.path(output_dir, paste0("forest_", model_name, ".png"))
  ggsave(out_path, p, width = 8, height = max(3, nrow(forest_data) * 0.6 + 1), dpi = 150)
  
  write(toJSON(list(
    success = TRUE,
    plot_path = out_path,
    effects = forest_data,
    message = sprintf("Forest plot saved: %s (%d covariate effects)", out_path, nrow(forest_data))
  ), auto_unbox = TRUE, pretty = TRUE), result_file)
  
}, error = function(e) {
  write(toJSON(list(success = FALSE, error = conditionMessage(e)), auto_unbox = TRUE), result_file)
})
