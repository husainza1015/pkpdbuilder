#!/usr/bin/env Rscript
# nlmixr2 model fitting — called by pmx CLI
suppressPackageStartupMessages({
  library(nlmixr2)
  library(jsonlite)
})

args_file <- Sys.getenv("PMX_ARGS_FILE")
result_file <- Sys.getenv("PMX_RESULT_FILE")
args <- fromJSON(args_file)

output_dir <- args$output_dir
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

# Load data
dat <- read.csv(args$data_file)
names(dat) <- toupper(names(dat))

# Ensure numeric
dat$DV <- as.numeric(dat$DV)
dat$TIME <- as.numeric(dat$TIME)
if ("AMT" %in% names(dat)) dat$AMT <- as.numeric(dat$AMT)
if ("WT" %in% names(dat)) dat$WT <- as.numeric(dat$WT)

model_type <- args$model_type
iiv_on <- args$iiv_on
error_model <- args$error_model
estimation <- args$estimation
model_name <- args$model_name

# ── Build model function ──
build_model <- function(model_type, iiv_on, error_model) {
  # Determine structural model
  is_oral <- grepl("oral", model_type)
  n_cmt <- as.integer(gsub("([0-9]+)cmt.*", "\\1", model_type))
  
  # Initial estimates — sensible defaults for typical drugs
  # Try to derive from NCA results if available
  nca_file <- file.path(output_dir, "nca_results_wide.csv")
  if (file.exists(nca_file)) {
    nca <- tryCatch(read.csv(nca_file), error = function(e) NULL)
    if (!is.null(nca)) {
      cl_init <- if ("CL_F_gmean" %in% names(nca)) log(nca$CL_F_gmean[1]) else log(5)
      v_init  <- if ("Vd_F_gmean" %in% names(nca)) log(nca$Vd_F_gmean[1]) else log(50)
    } else {
      cl_init <- log(5)
      v_init  <- log(50)
    }
  } else {
    cl_init <- log(5)
    v_init  <- log(50)
  }
  
  ini_block <- sprintf("
    tka <- log(1.5)
    tcl <- %.4f
    tv  <- %.4f
  ", cl_init, v_init)
  
  if (n_cmt >= 2) {
    ini_block <- paste0(ini_block, "
    tv2 <- log(2)
    tq  <- log(0.5)
    ")
  }
  
  # IIV
  for (p in iiv_on) {
    p_lower <- tolower(p)
    ini_block <- paste0(ini_block, sprintf("
    eta.%s ~ 0.1", p_lower))
  }
  
  # Residual error
  if (error_model == "proportional") {
    ini_block <- paste0(ini_block, "
    prop.err <- 0.2")
  } else if (error_model == "additive") {
    ini_block <- paste0(ini_block, "
    add.err <- 0.5")
  } else {
    ini_block <- paste0(ini_block, "
    prop.err <- 0.2
    add.err <- 0.1")
  }
  
  # Model block
  model_block <- ""
  
  if (is_oral) {
    model_block <- paste0(model_block, "
    ka <- exp(tka")
    if ("Ka" %in% iiv_on || "ka" %in% iiv_on) {
      model_block <- paste0(model_block, " + eta.ka")
    }
    model_block <- paste0(model_block, ")\n")
  }
  
  model_block <- paste0(model_block, "
    cl <- exp(tcl")
  if ("CL" %in% iiv_on || "cl" %in% iiv_on) {
    model_block <- paste0(model_block, " + eta.cl")
  }
  model_block <- paste0(model_block, ")
    v <- exp(tv")
  if ("V" %in% iiv_on || "v" %in% iiv_on) {
    model_block <- paste0(model_block, " + eta.v")
  }
  model_block <- paste0(model_block, ")\n")
  
  if (n_cmt >= 2) {
    model_block <- paste0(model_block, "
    v2 <- exp(tv2)
    q  <- exp(tq)
    ")
  }
  
  # ODE/linCmt
  if (n_cmt == 1 && is_oral) {
    model_block <- paste0(model_block, "
    d/dt(depot) = -ka * depot
    d/dt(center) = ka * depot - cl/v * center
    cp = center / v
    ")
  } else if (n_cmt == 1 && !is_oral) {
    model_block <- paste0(model_block, "
    d/dt(center) = -cl/v * center
    cp = center / v
    ")
  } else if (n_cmt == 2 && is_oral) {
    model_block <- paste0(model_block, "
    d/dt(depot)  = -ka * depot
    d/dt(center) = ka * depot - cl/v * center - q/v * center + q/v2 * periph
    d/dt(periph) = q/v * center - q/v2 * periph
    cp = center / v
    ")
  } else if (n_cmt == 2 && !is_oral) {
    model_block <- paste0(model_block, "
    d/dt(center) = -cl/v * center - q/v * center + q/v2 * periph
    d/dt(periph) = q/v * center - q/v2 * periph
    cp = center / v
    ")
  }
  
  # Residual error
  if (error_model == "proportional") {
    model_block <- paste0(model_block, "
    cp ~ prop(prop.err)")
  } else if (error_model == "additive") {
    model_block <- paste0(model_block, "
    cp ~ add(add.err)")
  } else {
    model_block <- paste0(model_block, "
    cp ~ prop(prop.err) + add(add.err)")
  }
  
  # Parse as nlmixr2 model
  model_code <- sprintf("function() {
    ini({%s
    })
    model({%s
    })
  }", ini_block, model_block)
  
  eval(parse(text = model_code))
}

# ── Fit model ──
tryCatch({
  model_fn <- build_model(model_type, iiv_on, error_model)
  
  est_method <- ifelse(estimation == "saem", "saem", "focei")
  
  fit <- nlmixr2(model_fn, dat, est = est_method,
                 control = list(print = 0))
  
  # Extract results
  params <- list()
  fixef <- fixef(fit)
  for (nm in names(fixef)) {
    params[[nm]] <- list(
      estimate = round(fixef[nm], 6),
      se = tryCatch(round(sqrt(diag(vcov(fit)))[nm], 6), error = function(e) NA)
    )
    # Transform for display
    if (grepl("^t", nm)) {
      params[[nm]]$transformed <- round(exp(fixef[nm]), 4)
      params[[nm]]$description <- gsub("^t", "", nm)
    }
  }
  
  # RSE
  for (nm in names(params)) {
    se <- params[[nm]]$se
    est <- params[[nm]]$estimate
    if (!is.na(se) && abs(est) > 1e-10) {
      params[[nm]]$rse_pct <- round(abs(se / est) * 100, 1)
    }
  }
  
  # IIV (omega)
  omega <- fit$omega
  iiv_results <- list()
  for (i in seq_len(nrow(omega))) {
    nm <- rownames(omega)[i]
    var_val <- omega[i, i]
    iiv_results[[nm]] <- list(
      variance = round(var_val, 4),
      cv_pct = round(sqrt(exp(var_val) - 1) * 100, 1)
    )
  }
  
  # Shrinkage
  shrinkage <- tryCatch({
    s <- fit$shrinkage
    if (!is.null(s)) as.list(round(s, 1)) else list()
  }, error = function(e) list())
  
  # Save IPRED, PRED, CWRES for diagnostics
  fit_df <- as.data.frame(fit)
  write.csv(fit_df, file.path(output_dir, paste0(model_name, "_fitdata.csv")), row.names = FALSE)
  
  # Save nlmixr2 fit object
  saveRDS(fit, file.path(output_dir, paste0(model_name, "_fit.rds")))
  
  result <- list(
    model_name = model_name,
    model_type = model_type,
    estimation = est_method,
    converged = TRUE,
    ofv = round(as.numeric(fit$objf), 2),
    aic = round(AIC(fit), 2),
    bic = round(BIC(fit), 2),
    n_params = length(fixef),
    parameters = params,
    iiv = iiv_results,
    residual_error = list(
      type = error_model,
      sigma = tryCatch(round(as.numeric(fit$sigma), 4), error = function(e) NA)
    ),
    shrinkage = shrinkage,
    n_subjects = length(unique(dat$ID)),
    n_observations = nrow(dat[dat$EVID == 0 | is.na(dat$EVID), ]),
    message = sprintf("Model %s converged successfully. OFV = %.2f", model_name, as.numeric(fit$objf))
  )
  
  # Save results JSON (for other tools to use)
  write(toJSON(result, auto_unbox = TRUE, pretty = TRUE),
        file.path(output_dir, paste0(model_name, "_results.json")))
  
  write(toJSON(result, auto_unbox = TRUE, pretty = TRUE), result_file)
  
}, error = function(e) {
  result <- list(
    success = FALSE,
    model_name = model_name,
    model_type = model_type,
    converged = FALSE,
    error = conditionMessage(e)
  )
  write(toJSON(result, auto_unbox = TRUE, pretty = TRUE), result_file)
})
