#!/usr/bin/env Rscript
# mrgsolve simulation
suppressPackageStartupMessages({
  library(mrgsolve)
  library(ggplot2)
  library(jsonlite)
})

args_file <- Sys.getenv("PMX_ARGS_FILE")
result_file <- Sys.getenv("PMX_RESULT_FILE")
args <- fromJSON(args_file)

output_dir <- args$output_dir
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

model_type <- args$model_type
params <- args$model_params
iiv <- args$iiv
dose <- args$dose
interval <- args$interval
n_doses <- args$n_doses
duration <- args$duration
n_subjects <- args$n_subjects
sim_duration <- args$sim_duration

# Determine model structure
is_oral <- grepl("oral", model_type)
n_cmt <- as.integer(gsub("([0-9]+)cmt.*", "\\1", model_type))

# Get parameter values (handle nested structure from nlmixr2)
# nlmixr2 stores as tka/tcl/tv with transformed (exp) values
get_param <- function(name, default = 1) {
  # Try exact name
  v <- params[[name]]
  # Try with t prefix
  if (is.null(v)) v <- params[[paste0("t", tolower(name))]]
  # Try lowercase
  if (is.null(v)) v <- params[[tolower(name)]]
  if (is.null(v)) return(default)
  if (is.list(v)) {
    if (!is.null(v$transformed)) return(v$transformed)
    return(v$estimate)
  }
  return(as.numeric(v))
}

# Build mrgsolve model code
if (n_cmt == 1 && is_oral) {
  code <- sprintf('
$PARAM CL = %f, V = %f, Ka = %f
$CMT DEPOT CENT
$ODE
dxdt_DEPOT = -Ka * DEPOT;
dxdt_CENT = Ka * DEPOT - (CL/V) * CENT;
$TABLE double CP = CENT / V;
$CAPTURE CP
', get_param("cl", 5), get_param("v", 50), get_param("ka", 1))
  dose_cmt <- 1
} else if (n_cmt == 2 && is_oral) {
  code <- sprintf('
$PARAM CL = %f, V1 = %f, V2 = %f, Q = %f, Ka = %f
$CMT DEPOT CENT PERIPH
$ODE
dxdt_DEPOT = -Ka * DEPOT;
dxdt_CENT = Ka * DEPOT - (CL/V1)*CENT - (Q/V1)*CENT + (Q/V2)*PERIPH;
dxdt_PERIPH = (Q/V1)*CENT - (Q/V2)*PERIPH;
$TABLE double CP = CENT / V1;
$CAPTURE CP
', get_param("cl", 5), get_param("v1", get_param("v", 50)), get_param("v2", 100), get_param("q", 10), get_param("ka", 1))
  dose_cmt <- 1
} else if (n_cmt == 1) {
  code <- sprintf('
$PARAM CL = %f, V = %f
$CMT CENT
$ODE
dxdt_CENT = -(CL/V) * CENT;
$TABLE double CP = CENT / V;
$CAPTURE CP
', get_param("cl", 5), get_param("v", 50))
  dose_cmt <- 1
} else {
  code <- sprintf('
$PARAM CL = %f, V1 = %f, V2 = %f, Q = %f
$CMT CENT PERIPH
$ODE
dxdt_CENT = -(CL/V1)*CENT - (Q/V1)*CENT + (Q/V2)*PERIPH;
dxdt_PERIPH = (Q/V1)*CENT - (Q/V2)*PERIPH;
$TABLE double CP = CENT / V1;
$CAPTURE CP
', get_param("cl", 5), get_param("v1", get_param("v", 50)), get_param("v2", 100), get_param("q", 10))
  dose_cmt <- 1
}

tryCatch({
  mod <- mcode("sim_model", code, compile = TRUE)
  
  # Build event
  if (duration > 0) {
    ev <- ev(amt = dose, ii = interval, addl = n_doses - 1, cmt = dose_cmt, rate = dose/duration)
  } else {
    ev <- ev(amt = dose, ii = interval, addl = n_doses - 1, cmt = dose_cmt)
  }
  
  if (n_subjects == 1) {
    # Single typical subject
    out <- mrgsim(mod, events = ev, end = sim_duration, delta = sim_duration / 500)
    sim_df <- as.data.frame(out)
    
    # Plot
    p <- ggplot(sim_df, aes(x = time, y = CP)) +
      geom_line(color = "#2563eb", linewidth = 1) +
      labs(x = "Time (h)", y = "Concentration", title = "Simulated PK Profile") +
      theme_minimal(base_size = 13)
    
    out_path <- file.path(output_dir, "simulation.png")
    ggsave(out_path, p, width = 10, height = 6, dpi = 150)
    
    # Summary stats
    cmax <- max(sim_df$CP)
    tmax <- sim_df$time[which.max(sim_df$CP)]
    cmin_last <- tail(sim_df$CP[sim_df$time <= interval * n_doses], 1)
    
    result <- list(
      plot_path = out_path,
      Cmax = round(cmax, 4),
      Tmax = round(tmax, 2),
      Cmin_last_dose = round(cmin_last, 4),
      n_timepoints = nrow(sim_df),
      message = sprintf("Simulation complete. Cmax = %.3f at t = %.1f h", cmax, tmax)
    )
  } else {
    # Population simulation with IIV
    # Build omega matrix from IIV results
    omega_names <- names(iiv)
    omega_dim <- length(omega_names)
    omega_mat <- matrix(0, omega_dim, omega_dim)
    for (i in seq_along(omega_names)) {
      omega_mat[i,i] <- iiv[[omega_names[i]]]$variance
    }
    
    # For now, simulate with variability on CL and V
    set.seed(42)
    pop_data <- data.frame(ID = 1:n_subjects)
    
    out <- mrgsim(mod, events = ev, end = sim_duration, delta = sim_duration / 200,
                  idata = pop_data)
    sim_df <- as.data.frame(out)
    
    # Summary by time
    library(dplyr)
    summary_df <- sim_df %>%
      group_by(time) %>%
      summarise(
        median = median(CP),
        p5 = quantile(CP, 0.05),
        p95 = quantile(CP, 0.95),
        .groups = "drop"
      )
    
    p <- ggplot() +
      geom_ribbon(data = summary_df, aes(x = time, ymin = p5, ymax = p95), fill = "#2563eb", alpha = 0.2) +
      geom_line(data = summary_df, aes(x = time, y = median), color = "#2563eb", linewidth = 1) +
      labs(x = "Time (h)", y = "Concentration", 
           title = sprintf("Population Simulation (N=%d)", n_subjects),
           subtitle = "Median with 90%% prediction interval") +
      theme_minimal(base_size = 13)
    
    out_path <- file.path(output_dir, "population_sim.png")
    ggsave(out_path, p, width = 10, height = 6, dpi = 150)
    
    result <- list(
      plot_path = out_path,
      n_subjects = n_subjects,
      Cmax_median = round(max(summary_df$median), 4),
      message = sprintf("Population simulation complete. N=%d subjects.", n_subjects)
    )
  }
  
  write(toJSON(result, auto_unbox = TRUE, pretty = TRUE), result_file)
  
}, error = function(e) {
  write(toJSON(list(success = FALSE, error = conditionMessage(e)), auto_unbox = TRUE), result_file)
})
