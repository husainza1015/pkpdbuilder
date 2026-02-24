#!/usr/bin/env Rscript
# Population simulation with IIV using mrgsolve
suppressPackageStartupMessages({
  library(mrgsolve)
  library(jsonlite)
  library(dplyr)
  library(ggplot2)
})

args_file <- Sys.getenv("PMX_ARGS_FILE")
result_file <- Sys.getenv("PMX_RESULT_FILE")
args <- fromJSON(args_file)

output_dir <- args$output_dir
model_params <- args$model_params
iiv <- args$iiv
model_type <- args$model_type
dose <- args$dose
interval <- args$interval
n_doses <- args$n_doses
n_subjects <- args$n_subjects
sim_duration <- args$sim_duration

tryCatch({
  # Extract PK params (handle nlmixr2 naming: tka→Ka, tcl→CL, tv→V)
  get_param <- function(names_list, params) {
    for (nm in names_list) {
      if (nm %in% names(params)) {
        p <- params[[nm]]
        if (is.list(p) && !is.null(p$transformed)) return(p$transformed)
        if (is.list(p) && !is.null(p$estimate)) return(exp(p$estimate))
        return(as.numeric(p))
      }
    }
    return(NA)
  }
  
  Ka <- get_param(c("ka", "tka", "Ka", "KA"), model_params)
  CL <- get_param(c("cl", "tcl", "CL", "Cl"), model_params)
  V  <- get_param(c("v", "tv", "V", "Vc"), model_params)
  V2 <- get_param(c("v2", "tv2", "V2", "Vp"), model_params)
  Q  <- get_param(c("q", "tq", "Q"), model_params)
  
  is_oral <- !is.na(Ka)
  n_cmt <- if (!is.na(V2)) 2 else 1
  
  # Build mrgsolve model
  if (n_cmt == 1 && is_oral) {
    code <- sprintf('
      $PARAM CL = %.4f, V = %.4f, KA = %.4f
      $OMEGA @annotated
      ECL : %.4f : IIV-CL
      EV  : %.4f : IIV-V
      EKA : %.4f : IIV-Ka
      $CMT DEPOT CENT
      $ODE
      dxdt_DEPOT = -KA * DEPOT;
      dxdt_CENT  =  KA * DEPOT - (CL/V) * CENT;
      $TABLE double CP = CENT/V;
      $CAPTURE CP
    ', CL, V, Ka,
      ifelse(!is.null(iiv$eta.cl), iiv$eta.cl$variance, 0.1),
      ifelse(!is.null(iiv$eta.v),  iiv$eta.v$variance,  0.05),
      ifelse(!is.null(iiv$eta.ka), iiv$eta.ka$variance, 0.2))
  } else if (n_cmt == 2 && is_oral) {
    code <- sprintf('
      $PARAM CL = %.4f, V = %.4f, V2 = %.4f, Q = %.4f, KA = %.4f
      $OMEGA @annotated
      ECL : %.4f : IIV-CL
      EV  : %.4f : IIV-V
      EKA : %.4f : IIV-Ka
      $CMT DEPOT CENT PERIPH
      $ODE
      dxdt_DEPOT  = -KA * DEPOT;
      dxdt_CENT   =  KA * DEPOT - (CL/V + Q/V) * CENT + Q/V2 * PERIPH;
      dxdt_PERIPH =  Q/V * CENT - Q/V2 * PERIPH;
      $TABLE double CP = CENT/V;
      $CAPTURE CP
    ', CL, V, V2, Q, Ka,
      ifelse(!is.null(iiv$eta.cl), iiv$eta.cl$variance, 0.1),
      ifelse(!is.null(iiv$eta.v),  iiv$eta.v$variance,  0.05),
      ifelse(!is.null(iiv$eta.ka), iiv$eta.ka$variance, 0.2))
  } else {
    # IV 1-cmt
    code <- sprintf('
      $PARAM CL = %.4f, V = %.4f
      $OMEGA @annotated
      ECL : %.4f : IIV-CL
      EV  : %.4f : IIV-V
      $CMT CENT
      $ODE
      dxdt_CENT = -(CL/V) * CENT;
      $TABLE double CP = CENT/V;
      $CAPTURE CP
    ', CL, V,
      ifelse(!is.null(iiv$eta.cl), iiv$eta.cl$variance, 0.1),
      ifelse(!is.null(iiv$eta.v),  iiv$eta.v$variance,  0.05))
  }
  
  mod <- mcode("pop_sim", code, quiet = TRUE)
  
  # Build dosing events
  dose_cmt <- if (is_oral) 1 else ifelse(n_cmt == 2, 2, 1)
  ev_list <- list()
  for (i in seq_len(n_doses)) {
    ev_list <- c(ev_list, list(ev(amt = dose, cmt = dose_cmt, time = (i-1) * interval)))
  }
  events <- do.call(c, ev_list)
  
  # Simulate population
  idata <- data.frame(ID = 1:n_subjects)
  
  out <- mod %>%
    idata_set(idata) %>%
    ev(events) %>%
    mrgsim(end = sim_duration, delta = sim_duration/500) %>%
    as_tibble()
  
  # Summary stats
  summary_stats <- out %>%
    filter(CP > 0) %>%
    group_by(time) %>%
    summarize(
      median = median(CP),
      p5  = quantile(CP, 0.05),
      p25 = quantile(CP, 0.25),
      p75 = quantile(CP, 0.75),
      p95 = quantile(CP, 0.95),
      .groups = "drop"
    )
  
  # Exposure metrics per subject
  exposure <- out %>%
    filter(CP > 0) %>%
    group_by(ID) %>%
    summarize(
      Cmax = max(CP),
      Cmin = min(CP[time > interval/2]),
      AUC  = sum(diff(time) * (head(CP, -1) + tail(CP, -1)) / 2),
      .groups = "drop"
    )
  
  # Plot
  p <- ggplot() +
    geom_ribbon(data = summary_stats, aes(x = time, ymin = p5, ymax = p95), 
                fill = "#bbdefb", alpha = 0.5) +
    geom_ribbon(data = summary_stats, aes(x = time, ymin = p25, ymax = p75), 
                fill = "#64b5f6", alpha = 0.5) +
    geom_line(data = summary_stats, aes(x = time, y = median), color = "#1565c0", linewidth = 1) +
    labs(x = "Time (h)", y = "Concentration",
         title = sprintf("Population Simulation (N=%d)", n_subjects),
         subtitle = sprintf("Dose: %.0f mg q%.0fh × %d | Median + 50%%/90%% PI", dose, interval, n_doses)) +
    theme_minimal(base_size = 12) +
    theme(plot.title = element_text(face = "bold"))
  
  out_path <- file.path(output_dir, "population_simulation.png")
  ggsave(out_path, p, width = 10, height = 6, dpi = 150)
  
  output <- list(
    n_subjects = n_subjects,
    exposure_summary = list(
      Cmax = list(median = round(median(exposure$Cmax), 3),
                  p5 = round(quantile(exposure$Cmax, 0.05), 3),
                  p95 = round(quantile(exposure$Cmax, 0.95), 3)),
      AUC  = list(median = round(median(exposure$AUC), 1),
                  p5 = round(quantile(exposure$AUC, 0.05), 1),
                  p95 = round(quantile(exposure$AUC, 0.95), 1))
    ),
    plot_path = out_path,
    message = sprintf("Population simulation complete. N=%d, Median Cmax=%.2f, Median AUC=%.1f",
                      n_subjects, median(exposure$Cmax), median(exposure$AUC))
  )
  
  write(toJSON(output, auto_unbox = TRUE, pretty = TRUE), result_file)
  
}, error = function(e) {
  write(toJSON(list(success = FALSE, error = conditionMessage(e)), auto_unbox = TRUE), result_file)
})
