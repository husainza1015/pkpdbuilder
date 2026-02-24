#!/usr/bin/env Rscript
# Individual observed vs predicted plots per subject
suppressPackageStartupMessages({
  library(ggplot2)
  library(jsonlite)
  library(dplyr)
})

args_file <- Sys.getenv("PMX_ARGS_FILE")
result_file <- Sys.getenv("PMX_RESULT_FILE")
args <- fromJSON(args_file)

output_dir <- args$output_dir
model_name <- args$model_name
n_per_page <- ifelse(is.null(args$n_per_page), 12, args$n_per_page)

fitdata_file <- file.path(output_dir, paste0(model_name, "_fitdata.csv"))
if (!file.exists(fitdata_file)) {
  write(toJSON(list(success = FALSE, error = "Fit data not found."), auto_unbox = TRUE), result_file)
  quit(status = 0)
}

df <- read.csv(fitdata_file)
names(df) <- toupper(names(df))

tryCatch({
  subjects <- unique(df$ID)
  n_subj <- length(subjects)
  n_pages <- ceiling(n_subj / n_per_page)
  
  plots_saved <- c()
  
  for (page in seq_len(n_pages)) {
    start_idx <- (page - 1) * n_per_page + 1
    end_idx <- min(page * n_per_page, n_subj)
    page_subj <- subjects[start_idx:end_idx]
    
    page_data <- df[df$ID %in% page_subj, ]
    
    # Observations
    obs <- page_data[!is.na(page_data$DV) & page_data$DV > 0, ]
    
    p <- ggplot(obs, aes(x = TIME)) +
      geom_point(aes(y = DV), color = "black", size = 1.5, alpha = 0.8) +
      geom_line(aes(y = IPRED), color = "#e53935", linewidth = 0.7) +
      geom_line(aes(y = PRED), color = "#1565c0", linewidth = 0.5, linetype = "dashed") +
      facet_wrap(~ ID, scales = "free_y", ncol = 4) +
      labs(x = "Time", y = "Concentration",
           title = sprintf("Individual Fits — %s (page %d/%d)", model_name, page, n_pages),
           subtitle = "Black dots: observed | Red: individual pred | Blue dashed: population pred") +
      theme_minimal(base_size = 9) +
      theme(
        strip.text = element_text(face = "bold"),
        plot.title = element_text(face = "bold", size = 11)
      )
    
    out_path <- file.path(output_dir, sprintf("individual_fits_%s_%02d.png", model_name, page))
    n_rows <- ceiling(length(page_subj) / 4)
    ggsave(out_path, p, width = 12, height = max(3, n_rows * 2.5), dpi = 150)
    plots_saved <- c(plots_saved, out_path)
  }
  
  write(toJSON(list(
    success = TRUE,
    n_subjects = n_subj,
    n_pages = n_pages,
    plot_paths = plots_saved,
    message = sprintf("Individual fit plots saved: %d pages, %d subjects", n_pages, n_subj)
  ), auto_unbox = TRUE, pretty = TRUE), result_file)
  
}, error = function(e) {
  write(toJSON(list(success = FALSE, error = conditionMessage(e)), auto_unbox = TRUE), result_file)
})
