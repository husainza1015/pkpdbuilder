#!/usr/bin/env Rscript
# ETA diagnostic plots
suppressPackageStartupMessages({
  library(ggplot2)
  library(jsonlite)
  library(gridExtra)
})

args_file <- Sys.getenv("PMX_ARGS_FILE")
result_file <- Sys.getenv("PMX_RESULT_FILE")
args <- fromJSON(args_file)

output_dir <- args$output_dir
model_name <- args$model_name

# Load fit data
fitdata_file <- file.path(output_dir, paste0(model_name, "_fitdata.csv"))
if (!file.exists(fitdata_file)) {
  write(toJSON(list(success = FALSE, error = "Fit data not found."), auto_unbox = TRUE), result_file)
  quit(status = 0)
}

df <- read.csv(fitdata_file)
names(df) <- toupper(names(df))

# Find ETA columns
eta_cols <- grep("^ETA", names(df), value = TRUE)

if (length(eta_cols) == 0) {
  write(toJSON(list(success = FALSE, error = "No ETA columns found in fit data."), auto_unbox = TRUE), result_file)
  quit(status = 0)
}

# Get one row per subject (ETAs are constant within subject)
subj_df <- df[!duplicated(df$ID), ]

theme_pmx <- theme_minimal(base_size = 11) +
  theme(plot.title = element_text(size = 10, face = "bold"))

plots <- list()

# ETA histograms
for (eta in eta_cols) {
  p <- ggplot(subj_df, aes_string(x = eta)) +
    geom_histogram(aes(y = after_stat(density)), bins = 15, fill = "#2563eb", alpha = 0.6) +
    stat_function(fun = dnorm, args = list(mean = 0, sd = sd(subj_df[[eta]], na.rm = TRUE)),
                  color = "red", linetype = "dashed") +
    labs(x = eta, y = "Density", title = paste(eta, "Distribution")) +
    theme_pmx
  plots <- c(plots, list(p))
}

# ETA vs covariates (WT if available)
cov_cols <- intersect(c("WT", "AGE", "CRCL", "SEX"), names(subj_df))
for (cov in cov_cols) {
  for (eta in eta_cols[1:min(2, length(eta_cols))]) {
    if (subj_df[[cov]] |> unique() |> length() <= 4) {
      # Categorical: boxplot
      p <- ggplot(subj_df, aes_string(x = paste0("factor(", cov, ")"), y = eta)) +
        geom_boxplot(fill = "#93c5fd", alpha = 0.6) +
        geom_hline(yintercept = 0, linetype = "dashed", color = "red") +
        labs(x = cov, y = eta, title = paste(eta, "vs", cov)) +
        theme_pmx
    } else {
      # Continuous: scatter
      p <- ggplot(subj_df, aes_string(x = cov, y = eta)) +
        geom_point(color = "#2563eb", alpha = 0.6) +
        geom_smooth(method = "loess", se = TRUE, color = "red", linetype = "dashed") +
        geom_hline(yintercept = 0, linetype = "dashed") +
        labs(x = cov, y = eta, title = paste(eta, "vs", cov)) +
        theme_pmx
    }
    plots <- c(plots, list(p))
  }
}

if (length(plots) > 0) {
  out_path <- file.path(output_dir, paste0("eta_", model_name, ".png"))
  ncol <- min(3, length(plots))
  nrow <- ceiling(length(plots) / ncol)
  height <- max(4, nrow * 3)
  
  png(out_path, width = ncol * 400, height = nrow * 300, res = 150)
  do.call(grid.arrange, c(plots, ncol = ncol))
  dev.off()
  
  write(toJSON(list(
    success = TRUE,
    plot_path = out_path,
    n_plots = length(plots),
    eta_columns = eta_cols,
    message = sprintf("ETA plots saved: %s", out_path)
  ), auto_unbox = TRUE), result_file)
} else {
  write(toJSON(list(success = FALSE, error = "No plots generated"), auto_unbox = TRUE), result_file)
}
