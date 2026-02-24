#!/usr/bin/env Rscript
# Covariate screening — ETA vs covariates
suppressPackageStartupMessages({
  library(ggplot2)
  library(jsonlite)
  library(gridExtra)
  library(dplyr)
})

args_file <- Sys.getenv("PMX_ARGS_FILE")
result_file <- Sys.getenv("PMX_RESULT_FILE")
args <- fromJSON(args_file)

output_dir <- args$output_dir
model_name <- args$model_name
covariates <- args$covariates

# Load fit data
fitdata_file <- file.path(output_dir, paste0(model_name, "_fitdata.csv"))
if (!file.exists(fitdata_file)) {
  write(toJSON(list(success = FALSE, error = "Fit data not found."), auto_unbox = TRUE), result_file)
  quit(status = 0)
}

df <- read.csv(fitdata_file)
names(df) <- toupper(names(df))

# Try to merge covariates from original dataset
orig_file <- file.path(output_dir, paste0(model_name, "_origdata.csv"))
if (!file.exists(orig_file)) {
  # Check if there's a dataset file we stored
  data_files <- list.files(output_dir, pattern = ".*\\.csv$", full.names = TRUE)
  # Also try the current working directory for common data files
}

# Get one row per subject (ETAs are subject-level)
subj_df <- df[!duplicated(df$ID), ]

# If covariates not in fit data, try to get from original
# Look for covariate data file
cov_file <- file.path(output_dir, "covariate_data.csv")
if (file.exists(cov_file)) {
  cov_df <- read.csv(cov_file)
  names(cov_df) <- toupper(names(cov_df))
  cov_subj <- cov_df[!duplicated(cov_df$ID), ]
  # Merge covariate columns that aren't already in subj_df
  new_cols <- setdiff(names(cov_subj), names(subj_df))
  if (length(new_cols) > 0) {
    subj_df <- merge(subj_df, cov_subj[, c("ID", new_cols)], by = "ID", all.x = TRUE)
  }
}

# Find ETA columns
eta_cols <- grep("^ETA", names(subj_df), value = TRUE)

if (length(eta_cols) == 0) {
  write(toJSON(list(success = FALSE, error = "No ETA columns found."), auto_unbox = TRUE), result_file)
  quit(status = 0)
}

# If no covariates specified, auto-detect
if (length(covariates) == 0) {
  skip <- c("ID", "TIME", "DV", "AMT", "EVID", "MDV", "CMT", "RATE", "SS", "II", "ADDL",
             "PRED", "IPRED", "CWRES", "IWRES", "WRES", grep("^ETA", names(subj_df), value = TRUE))
  covariates <- setdiff(names(subj_df), skip)
}
covariates <- intersect(covariates, names(subj_df))

if (length(covariates) == 0) {
  write(toJSON(list(success = FALSE, error = "No covariates found in dataset."), auto_unbox = TRUE), result_file)
  quit(status = 0)
}

# Screen each covariate against each ETA
screening_results <- list()
plots <- list()
theme_pmx <- theme_minimal(base_size = 10) + theme(plot.title = element_text(size = 9))

for (cov in covariates) {
  cov_data <- subj_df[[cov]]
  if (all(is.na(cov_data))) next
  
  is_categorical <- length(unique(cov_data[!is.na(cov_data)])) <= 5
  
  for (eta in eta_cols) {
    eta_data <- subj_df[[eta]]
    valid <- !is.na(cov_data) & !is.na(eta_data)
    
    if (sum(valid) < 5) next
    
    if (is_categorical) {
      # Categorical: ANOVA / Kruskal-Wallis
      test <- tryCatch({
        kruskal.test(eta_data[valid] ~ factor(cov_data[valid]))
      }, error = function(e) NULL)
      
      p_val <- if (!is.null(test)) test$p.value else NA
      effect_size <- NA
      test_type <- "kruskal-wallis"
      
      # Box plot
      p <- ggplot(subj_df[valid, ], aes_string(x = paste0("factor(", cov, ")"), y = eta)) +
        geom_boxplot(fill = "#93c5fd", alpha = 0.5, outlier.shape = NA) +
        geom_jitter(width = 0.1, alpha = 0.5, size = 1.5) +
        geom_hline(yintercept = 0, linetype = "dashed", color = "red") +
        labs(title = sprintf("%s vs %s (p=%.3f)", eta, cov, ifelse(is.na(p_val), 1, p_val)),
             x = cov, y = eta) +
        theme_pmx
      
    } else {
      # Continuous: Spearman correlation
      cor_test <- tryCatch({
        cor.test(cov_data[valid], eta_data[valid], method = "spearman")
      }, error = function(e) NULL)
      
      p_val <- if (!is.null(cor_test)) cor_test$p.value else NA
      effect_size <- if (!is.null(cor_test)) cor_test$estimate else NA
      test_type <- "spearman"
      
      # Scatter plot
      p <- ggplot(subj_df[valid, ], aes_string(x = cov, y = eta)) +
        geom_point(alpha = 0.6, color = "#2563eb") +
        geom_smooth(method = "loess", se = TRUE, color = "red", linetype = "dashed", linewidth = 0.8) +
        geom_hline(yintercept = 0, linetype = "dashed") +
        labs(title = sprintf("%s vs %s (rho=%.2f, p=%.3f)", eta, cov,
                             ifelse(is.na(effect_size), 0, effect_size),
                             ifelse(is.na(p_val), 1, p_val)),
             x = cov, y = eta) +
        theme_pmx
    }
    
    plots <- c(plots, list(p))
    
    screening_results <- c(screening_results, list(list(
      covariate = cov,
      parameter_eta = eta,
      type = ifelse(is_categorical, "categorical", "continuous"),
      test = test_type,
      p_value = round(ifelse(is.na(p_val), 1, p_val), 4),
      effect_size = round(ifelse(is.na(effect_size), 0, effect_size), 3),
      significant = ifelse(is.na(p_val), FALSE, p_val < 0.05),
      recommended = ifelse(is.na(p_val), FALSE, p_val < 0.01)
    )))
  }
}

# Save screening plot
if (length(plots) > 0) {
  out_path <- file.path(output_dir, paste0("covariate_screen_", model_name, ".png"))
  ncol <- min(4, length(plots))
  nrow <- ceiling(length(plots) / ncol)
  height <- max(4, nrow * 3)
  width <- max(8, ncol * 3)
  
  png(out_path, width = width * 100, height = height * 100, res = 100)
  do.call(grid.arrange, c(plots, ncol = ncol))
  dev.off()
} else {
  out_path <- NULL
}

# Summarize recommendations
significant <- Filter(function(r) r$significant, screening_results)
recommended <- Filter(function(r) r$recommended, screening_results)

output <- list(
  screening = screening_results,
  n_tested = length(screening_results),
  n_significant = length(significant),
  n_recommended = length(recommended),
  recommended_covariates = lapply(recommended, function(r) {
    list(covariate = r$covariate, on = r$parameter_eta, p = r$p_value)
  }),
  plot_path = out_path,
  message = sprintf("Screened %d covariate-parameter pairs. %d significant (p<0.05), %d recommended (p<0.01).",
                     length(screening_results), length(significant), length(recommended))
)

write(toJSON(output, auto_unbox = TRUE, pretty = TRUE), result_file)
