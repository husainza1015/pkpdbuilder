#!/usr/bin/env Rscript
# Non-Compartmental Analysis using PKNCA
suppressPackageStartupMessages({
  library(PKNCA)
  library(jsonlite)
  library(dplyr)
})

args_file <- Sys.getenv("PMX_ARGS_FILE")
result_file <- Sys.getenv("PMX_RESULT_FILE")
args <- fromJSON(args_file)

output_dir <- args$output_dir
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

dat <- read.csv(args$data_file)
names(dat) <- toupper(names(dat))

route <- args$route
dose_col <- toupper(args$dose_col)

tryCatch({
  # Prepare concentration data
  obs <- dat[is.na(dat$EVID) | dat$EVID == 0, ]
  obs <- obs[!is.na(obs$DV), ]
  
  # Prepare dose data
  dose_dat <- dat[!is.na(dat[[dose_col]]) & dat[[dose_col]] > 0, ]
  
  # PKNCA objects
  conc_obj <- PKNCAconc(obs, DV ~ TIME | ID)
  
  dose_obj <- PKNCAdose(dose_dat, as.formula(paste(dose_col, "~ TIME | ID")))
  
  # Define intervals — use full time range per subject
  # PKNCA auto-computes standard NCA parameters
  data_obj <- PKNCAdata(conc_obj, dose_obj)
  
  # Run NCA
  nca_result <- pk.nca(data_obj)
  
  # Extract results
  results_df <- as.data.frame(nca_result)
  
  # Pivot to wide format per subject
  wide_results <- list()
  subjects <- unique(results_df$ID)
  
  # Key parameters to extract
  key_params <- c("cmax", "tmax", "auclast", "aucinf.obs", "half.life", 
                   "cl.obs", "vd.obs", "vz.obs", "vss.obs",
                   "lambda.z", "r.squared", "aucinf.pred",
                   "aucpext.obs", "mrt.obs")
  
  for (sid in subjects) {
    subj_data <- results_df[results_df$ID == sid, ]
    params <- list(ID = sid)
    for (p in key_params) {
      row <- subj_data[subj_data$PPTESTCD == p, ]
      if (nrow(row) > 0) {
        val <- row$PPORRES[[1]]
        if (!is.null(val) && !is.na(val)) {
          params[[p]] <- round(as.numeric(val), 4)
        }
      }
    }
    wide_results[[as.character(sid)]] <- params
  }
  
  # Summary statistics (geometric mean for PK params)
  geo_mean <- function(x) {
    x <- x[!is.na(x) & x > 0]
    if (length(x) == 0) return(NA)
    exp(mean(log(x)))
  }
  
  geo_cv <- function(x) {
    x <- x[!is.na(x) & x > 0]
    if (length(x) < 2) return(NA)
    round(sqrt(exp(var(log(x))) - 1) * 100, 1)
  }
  
  get_vals <- function(param) {
    vals <- sapply(wide_results, function(r) {
      v <- r[[param]]
      if (is.null(v)) return(NA_real_)
      return(as.numeric(v))
    })
    as.numeric(vals)
  }
  
  summary_stats <- list(
    n_subjects = length(subjects),
    Cmax_gmean = round(geo_mean(get_vals("cmax")), 4),
    Cmax_geo_cv_pct = geo_cv(get_vals("cmax")),
    Tmax_median = round(median(get_vals("tmax"), na.rm = TRUE), 2),
    AUClast_gmean = round(geo_mean(get_vals("auclast")), 4),
    AUClast_geo_cv_pct = geo_cv(get_vals("auclast")),
    AUCinf_gmean = round(geo_mean(get_vals("aucinf.obs")), 4),
    AUCinf_geo_cv_pct = geo_cv(get_vals("aucinf.obs")),
    thalf_gmean = round(geo_mean(get_vals("half.life")), 2),
    thalf_geo_cv_pct = geo_cv(get_vals("half.life"))
  )
  
  # Add CL/F and Vd/F for extravascular
  if (route == "oral") {
    summary_stats$CL_F_gmean <- round(geo_mean(get_vals("cl.obs")), 4)
    summary_stats$Vz_F_gmean <- round(geo_mean(get_vals("vz.obs")), 2)
  } else {
    summary_stats$CL_gmean <- round(geo_mean(get_vals("cl.obs")), 4)
    summary_stats$Vss_gmean <- round(geo_mean(get_vals("vss.obs")), 2)
  }
  
  # Save full PKNCA output as CSV
  csv_path <- file.path(output_dir, "nca_results.csv")
  write.csv(results_df, csv_path, row.names = FALSE)
  
  # Also save wide format
  wide_df <- do.call(rbind, lapply(wide_results, as.data.frame))
  wide_csv <- file.path(output_dir, "nca_results_wide.csv")
  write.csv(wide_df, wide_csv, row.names = FALSE)
  
  # Available parameters in output
  available_params <- unique(results_df$PPTESTCD)
  
  output <- list(
    individual = wide_results,
    summary = summary_stats,
    csv_path = csv_path,
    wide_csv_path = wide_csv,
    available_parameters = as.list(available_params),
    pknca_version = as.character(packageVersion("PKNCA")),
    message = sprintf("NCA complete (PKNCA v%s). %d subjects. Geometric mean t½ = %.1f h, AUCinf = %.1f",
                       packageVersion("PKNCA"), length(subjects),
                       summary_stats$thalf_gmean, summary_stats$AUCinf_gmean)
  )
  
  write(toJSON(output, auto_unbox = TRUE, pretty = TRUE), result_file)
  
}, error = function(e) {
  write(toJSON(list(
    success = FALSE,
    error = paste("PKNCA failed:", conditionMessage(e))
  ), auto_unbox = TRUE), result_file)
})
