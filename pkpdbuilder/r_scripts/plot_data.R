#!/usr/bin/env Rscript
# Data exploration plots
suppressPackageStartupMessages({
  library(ggplot2)
  library(jsonlite)
})

args_file <- Sys.getenv("PMX_ARGS_FILE")
result_file <- Sys.getenv("PMX_RESULT_FILE")
args <- fromJSON(args_file)

output_dir <- args$output_dir
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

dat <- read.csv(args$data_file)
names(dat) <- toupper(names(dat))

plot_type <- args$plot_type
log_y <- args$log_y

obs <- dat[is.na(dat$EVID) | dat$EVID == 0, ]
obs <- obs[!is.na(obs$DV), ]

theme_pmx <- theme_minimal(base_size = 13) +
  theme(legend.position = "none")

plots_saved <- c()

# Spaghetti plot
if (plot_type %in% c("spaghetti", "all")) {
  p <- ggplot(obs, aes(x = TIME, y = DV, group = ID, color = factor(ID))) +
    geom_line(alpha = 0.6) +
    geom_point(size = 1, alpha = 0.6) +
    labs(x = "Time", y = "Concentration", title = "Concentration-Time Profiles (All Subjects)") +
    theme_pmx
  if (log_y) p <- p + scale_y_log10()
  
  out_path <- file.path(output_dir, "data_spaghetti.png")
  ggsave(out_path, p, width = 10, height = 6, dpi = 150)
  plots_saved <- c(plots_saved, out_path)
}

# Individual profiles (faceted, up to 16 subjects)
if (plot_type %in% c("individual", "all")) {
  subj_ids <- unique(obs$ID)
  if (length(subj_ids) > 16) subj_ids <- subj_ids[1:16]
  sub_obs <- obs[obs$ID %in% subj_ids, ]
  
  p <- ggplot(sub_obs, aes(x = TIME, y = DV)) +
    geom_line(color = "#2563eb") +
    geom_point(size = 1.5, color = "#2563eb") +
    facet_wrap(~ID, scales = "free_y") +
    labs(x = "Time", y = "Concentration", title = "Individual Profiles") +
    theme_pmx
  if (log_y) p <- p + scale_y_log10()
  
  n_panels <- length(subj_ids)
  height <- max(6, ceiling(n_panels / 4) * 3)
  out_path <- file.path(output_dir, "data_individual.png")
  ggsave(out_path, p, width = 12, height = height, dpi = 150)
  plots_saved <- c(plots_saved, out_path)
}

# Dose-normalized
if (plot_type %in% c("dose_normalized", "all") && "AMT" %in% names(dat)) {
  doses_df <- dat[!is.na(dat$AMT) & dat$AMT > 0, c("ID", "AMT")]
  dose_per_subj <- tapply(doses_df$AMT, doses_df$ID, function(x) x[1])
  
  obs$DOSE <- dose_per_subj[as.character(obs$ID)]
  obs$DV_NORM <- obs$DV / obs$DOSE
  obs_norm <- obs[!is.na(obs$DV_NORM), ]
  
  if (nrow(obs_norm) > 0) {
    p <- ggplot(obs_norm, aes(x = TIME, y = DV_NORM, group = ID, color = factor(ID))) +
      geom_line(alpha = 0.6) +
      geom_point(size = 1, alpha = 0.6) +
      labs(x = "Time", y = "Dose-Normalized Concentration", title = "Dose-Normalized Profiles") +
      theme_pmx
    if (log_y) p <- p + scale_y_log10()
    
    out_path <- file.path(output_dir, "data_dose_normalized.png")
    ggsave(out_path, p, width = 10, height = 6, dpi = 150)
    plots_saved <- c(plots_saved, out_path)
  }
}

write(toJSON(list(
  success = TRUE,
  plots = plots_saved,
  n_plots = length(plots_saved),
  message = sprintf("Generated %d data exploration plots", length(plots_saved))
), auto_unbox = TRUE), result_file)
