#!/usr/bin/env Rscript
# Fit a model from the PMX model library — injects R code directly
suppressPackageStartupMessages({
  library(nlmixr2)
  library(jsonlite)
})

args_file <- Sys.getenv("PMX_ARGS_FILE")
result_file <- Sys.getenv("PMX_RESULT_FILE")
args <- fromJSON(args_file)

output_dir <- args$output_dir
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

dat <- read.csv(args$data_file)
names(dat) <- toupper(names(dat))
dat$DV <- as.numeric(dat$DV)
dat$TIME <- as.numeric(dat$TIME)
if ("AMT" %in% names(dat)) dat$AMT <- as.numeric(dat$AMT)
if ("WT" %in% names(dat)) dat$WT <- as.numeric(dat$WT)

model_name <- args$model_name
library_model <- args$library_model
estimation <- ifelse(args$estimation == "saem", "saem", "focei")

tryCatch({
  # Evaluate the model code from the library
  eval(parse(text = args$model_code))
  
  # The model code defines a function with the library_model name
  # Find it in the environment
  model_fn <- NULL
  for (obj_name in ls()) {
    obj <- get(obj_name)
    if (is.function(obj)) {
      # Try to check if it's an nlmixr2 model
      model_fn <- obj
      break
    }
  }
  
  if (is.null(model_fn)) {
    write(toJSON(list(success = FALSE, error = "Could not parse model code"), auto_unbox = TRUE), result_file)
    quit(status = 0)
  }
  
  # Fit
  fit <- nlmixr2(model_fn, dat, est = estimation, control = list(print = 0))
  
  # Extract results
  params <- list()
  fe <- fixef(fit)
  se_vec <- tryCatch(sqrt(diag(vcov(fit))), error = function(e) rep(NA, length(fe)))
  
  for (i in seq_along(fe)) {
    nm <- names(fe)[i]
    se_val <- if (length(se_vec) >= i) se_vec[i] else NA
    params[[nm]] <- list(
      estimate = round(fe[i], 6),
      se = if (!is.na(se_val)) round(se_val, 6) else NA
    )
    if (grepl("^l", nm) && !grepl("^logit", nm)) {
      params[[nm]]$transformed <- round(exp(fe[i]), 4)
    }
    if (!is.na(se_val) && abs(fe[i]) > 1e-10) {
      params[[nm]]$rse_pct <- round(abs(se_val / fe[i]) * 100, 1)
    }
  }
  
  # IIV
  omega <- fit$omega
  iiv_results <- list()
  if (!is.null(omega) && nrow(omega) > 0) {
    for (i in seq_len(nrow(omega))) {
      nm <- rownames(omega)[i]
      var_val <- omega[i, i]
      iiv_results[[nm]] <- list(
        variance = round(var_val, 4),
        cv_pct = round(sqrt(exp(var_val) - 1) * 100, 1)
      )
    }
  }
  
  # Shrinkage
  shrinkage <- tryCatch({
    s <- fit$shrinkage
    if (!is.null(s)) as.list(round(s, 1)) else list()
  }, error = function(e) list())
  
  # Save fit data and object
  fit_df <- as.data.frame(fit)
  write.csv(fit_df, file.path(output_dir, paste0(model_name, "_fitdata.csv")), row.names = FALSE)
  saveRDS(fit, file.path(output_dir, paste0(model_name, "_fit.rds")))
  
  result <- list(
    model_name = model_name,
    library_model = library_model,
    model_type = library_model,
    estimation = estimation,
    converged = TRUE,
    ofv = round(as.numeric(fit$objf), 2),
    aic = round(AIC(fit), 2),
    bic = round(BIC(fit), 2),
    n_params = length(fe),
    parameters = params,
    iiv = iiv_results,
    shrinkage = shrinkage,
    n_subjects = length(unique(dat$ID)),
    n_observations = nrow(dat[dat$EVID == 0 | is.na(dat$EVID), ]),
    message = sprintf("Model %s (%s) converged. OFV = %.2f", model_name, library_model, as.numeric(fit$objf))
  )
  
  write(toJSON(result, auto_unbox = TRUE, pretty = TRUE),
        file.path(output_dir, paste0(model_name, "_results.json")))
  write(toJSON(result, auto_unbox = TRUE, pretty = TRUE), result_file)
  
}, error = function(e) {
  result <- list(
    success = FALSE,
    model_name = model_name,
    library_model = library_model,
    converged = FALSE,
    error = conditionMessage(e)
  )
  write(toJSON(result, auto_unbox = TRUE, pretty = TRUE), result_file)
})
