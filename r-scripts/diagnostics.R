#!/usr/bin/env Rscript
# Diagnostic plots — GOF panel
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
  write(toJSON(list(success = FALSE, error = "Fit data not found. Run fit_model first."), auto_unbox = TRUE), result_file)
  quit(status = 0)
}

df <- read.csv(fitdata_file)

# Normalize column names (nlmixr2 output varies)
names(df) <- toupper(names(df))
# Map common column name variants
col_map <- list(
  DV = c("DV", "Y"),
  PRED = c("PRED"),
  IPRED = c("IPRED"),
  CWRES = c("CWRES", "CRES"),
  IWRES = c("IWRES"),
  TIME = c("TIME")
)

find_col <- function(df, candidates) {
  for (c in candidates) {
    if (c %in% names(df)) return(c)
  }
  return(NULL)
}

dv_col <- find_col(df, col_map$DV)
pred_col <- find_col(df, col_map$PRED)
ipred_col <- find_col(df, col_map$IPRED)
cwres_col <- find_col(df, col_map$CWRES)
time_col <- find_col(df, col_map$TIME)

plots <- list()

theme_pmx <- theme_minimal(base_size = 12) +
  theme(plot.title = element_text(size = 11, face = "bold"))

# 1. DV vs PRED
if (!is.null(dv_col) && !is.null(pred_col)) {
  obs <- df[!is.na(df[[dv_col]]) & df[[dv_col]] > 0, ]
  plots[[1]] <- ggplot(obs, aes_string(x = pred_col, y = dv_col)) +
    geom_point(alpha = 0.5, size = 1.5, color = "#2563eb") +
    geom_abline(slope = 1, intercept = 0, linetype = "dashed", color = "red") +
    labs(x = "Population Predicted (PRED)", y = "Observed (DV)", title = "DV vs PRED") +
    theme_pmx
}

# 2. DV vs IPRED
if (!is.null(dv_col) && !is.null(ipred_col)) {
  obs <- df[!is.na(df[[dv_col]]) & df[[dv_col]] > 0, ]
  plots[[2]] <- ggplot(obs, aes_string(x = ipred_col, y = dv_col)) +
    geom_point(alpha = 0.5, size = 1.5, color = "#16a34a") +
    geom_abline(slope = 1, intercept = 0, linetype = "dashed", color = "red") +
    labs(x = "Individual Predicted (IPRED)", y = "Observed (DV)", title = "DV vs IPRED") +
    theme_pmx
}

# 3. CWRES vs TIME
if (!is.null(cwres_col) && !is.null(time_col)) {
  obs <- df[!is.na(df[[cwres_col]]), ]
  plots[[3]] <- ggplot(obs, aes_string(x = time_col, y = cwres_col)) +
    geom_point(alpha = 0.5, size = 1.5, color = "#9333ea") +
    geom_hline(yintercept = 0, linetype = "dashed") +
    geom_hline(yintercept = c(-2, 2), linetype = "dotted", color = "red") +
    labs(x = "Time", y = "CWRES", title = "CWRES vs Time") +
    theme_pmx
}

# 4. CWRES vs PRED
if (!is.null(cwres_col) && !is.null(pred_col)) {
  obs <- df[!is.na(df[[cwres_col]]), ]
  plots[[4]] <- ggplot(obs, aes_string(x = pred_col, y = cwres_col)) +
    geom_point(alpha = 0.5, size = 1.5, color = "#ea580c") +
    geom_hline(yintercept = 0, linetype = "dashed") +
    geom_hline(yintercept = c(-2, 2), linetype = "dotted", color = "red") +
    labs(x = "PRED", y = "CWRES", title = "CWRES vs PRED") +
    theme_pmx
}

# 5. QQ plot of CWRES
if (!is.null(cwres_col)) {
  obs <- df[!is.na(df[[cwres_col]]), ]
  plots[[5]] <- ggplot(obs, aes_string(sample = cwres_col)) +
    stat_qq(alpha = 0.5, color = "#0891b2") +
    stat_qq_line(color = "red", linetype = "dashed") +
    labs(title = "QQ Plot of CWRES") +
    theme_pmx
}

# Save combined panel
if (length(plots) > 0) {
  out_path <- file.path(output_dir, paste0("gof_", model_name, ".png"))
  png(out_path, width = 1200, height = 800, res = 150)
  n <- length(plots)
  ncol <- min(3, n)
  nrow <- ceiling(n / ncol)
  do.call(grid.arrange, c(plots, ncol = ncol, nrow = nrow))
  dev.off()
  
  write(toJSON(list(
    success = TRUE,
    plot_path = out_path,
    n_plots = n,
    message = sprintf("GOF plots saved: %s", out_path)
  ), auto_unbox = TRUE), result_file)
} else {
  write(toJSON(list(success = FALSE, error = "No plottable columns found in fit data"), auto_unbox = TRUE), result_file)
}
