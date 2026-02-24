#!/usr/bin/env Rscript
# Stepwise Covariate Modeling (SCM) via nlmixr2extra::covarSearchAuto
suppressPackageStartupMessages({
  library(nlmixr2)
  library(jsonlite)
})

args_file <- Sys.getenv("PMX_ARGS_FILE")
result_file <- Sys.getenv("PMX_RESULT_FILE")
args <- fromJSON(args_file)

output_dir <- args$output_dir
model_name <- args$model_name
covariates <- args$covariates
forward_p  <- args$forward_p
backward_p <- args$backward_p

fit_file <- file.path(output_dir, paste0(model_name, "_fit.rds"))
if (!file.exists(fit_file)) {
  write(toJSON(list(success = FALSE, error = "Fit object not found. Run fit_model first."), auto_unbox = TRUE), result_file)
  quit(status = 0)
}

fit <- readRDS(fit_file)

tryCatch({
  if (requireNamespace("nlmixr2extra", quietly = TRUE)) {
    library(nlmixr2extra)
    
    # Identify parameter names and covariate names from fit
    param_names <- names(fixef(fit))
    # Get structural params (exclude error terms)
    struct_params <- param_names[grepl("^(t|l)", param_names) & !grepl("(err|sd|prop|add)", param_names, ignore.case = TRUE)]
    
    # Run covarSearchAuto
    scm <- covarSearchAuto(
      fit = fit,
      varsVec = struct_params,
      covarsVec = covariates,
      pVal = list(fwd = forward_p, bck = backward_p),
      searchType = "scm"
    )
    
    output <- list(
      success = TRUE,
      method = "SCM (nlmixr2extra::covarSearchAuto)",
      forward_p = forward_p,
      backward_p = backward_p,
      summary = capture.output(print(scm)),
      message = "Stepwise covariate model selection complete."
    )
  } else {
    # Manual SCM fallback — test each covariate individually
    fit_data <- as.data.frame(fit)
    base_ofv <- as.numeric(fit$objf)
    
    results <- list()
    for (cov in covariates) {
      if (cov %in% names(fit_data)) {
        # Simple correlation test with ETAs
        eta_cols <- grep("^eta\\.", names(fit_data), value = TRUE)
        subj <- fit_data[!duplicated(fit_data$ID), ]
        for (eta in eta_cols) {
          if (cov %in% names(subj)) {
            ct <- cor.test(subj[[eta]], subj[[cov]], method = "spearman")
            results <- c(results, list(list(
              covariate = cov, parameter = eta,
              correlation = round(ct$estimate, 3),
              p_value = round(ct$p.value, 4),
              significant = ct$p.value < forward_p
            )))
          }
        }
      }
    }
    
    sig <- Filter(function(r) r$significant, results)
    
    output <- list(
      success = TRUE,
      method = "Manual correlation screening (nlmixr2extra not available)",
      forward_p = forward_p,
      results = results,
      n_significant = length(sig),
      recommended = lapply(sig, function(r) paste(r$covariate, "on", r$parameter)),
      message = sprintf("Screened %d covariate-parameter pairs. %d significant at p<%.2f",
                        length(results), length(sig), forward_p)
    )
  }
  
  write(toJSON(output, auto_unbox = TRUE, pretty = TRUE), result_file)
  
}, error = function(e) {
  write(toJSON(list(success = FALSE, error = conditionMessage(e)), auto_unbox = TRUE), result_file)
})
