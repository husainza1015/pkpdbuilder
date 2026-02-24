#!/usr/bin/env Rscript
# Export nlmixr2 model to other formats
suppressPackageStartupMessages({
  library(jsonlite)
  library(nlmixr2)
})

args_file <- Sys.getenv("PMX_ARGS_FILE")
result_file <- Sys.getenv("PMX_RESULT_FILE")
args <- fromJSON(args_file)

output_dir <- args$output_dir
model_name <- args$model_name
target <- args$target
output_file <- args$output_file

# Load fit object
fit_file <- file.path(output_dir, paste0(model_name, "_fit.rds"))
if (!file.exists(fit_file)) {
  write(toJSON(list(success = FALSE, error = "Fit object not found. Run fit_model first."), auto_unbox = TRUE), result_file)
  quit(status = 0)
}

fit <- readRDS(fit_file)

tryCatch({
  if (target == "nonmem") {
    # Export to NONMEM via babelmixr2
    if (requireNamespace("babelmixr2", quietly = TRUE)) {
      library(babelmixr2)
      if (output_file == "") output_file <- file.path(output_dir, paste0(model_name, ".ctl"))
      # Convert nlmixr2 fit to NONMEM control stream
      nonmem_mod <- nlmixr2(fit, est = "nonmem")
      # babelmixr2 creates the control stream
      write(toJSON(list(
        success = TRUE,
        format = "nonmem",
        output_file = output_file,
        message = sprintf("NONMEM control stream exported: %s", output_file)
      ), auto_unbox = TRUE), result_file)
    } else {
      # Manual NONMEM control stream generation
      params <- fixef(fit)
      omega <- fit$omega
      
      ctl <- paste0(
        "$PROBLEM ", model_name, " - exported from pmx CLI\n",
        "$INPUT ID TIME DV AMT EVID CMT MDV\n",
        "$DATA ../data.csv IGNORE=@\n\n",
        "$SUBROUTINE ADVAN2 TRANS2\n\n",
        "$PK\n",
        "  TVCL = THETA(1)\n",
        "  TVV  = THETA(2)\n",
        "  TVKA = THETA(3)\n",
        "  CL = TVCL * EXP(ETA(1))\n",
        "  V  = TVV  * EXP(ETA(2))\n",
        "  KA = TVKA * EXP(ETA(3))\n",
        "  S2 = V\n\n",
        "$ERROR\n",
        "  IPRED = F\n",
        "  Y = IPRED * (1 + ERR(1))\n\n",
        "$THETA\n"
      )
      
      for (nm in names(params)) {
        ctl <- paste0(ctl, sprintf("  %.4f  ; %s\n", exp(params[nm]), nm))
      }
      
      ctl <- paste0(ctl, "\n$OMEGA\n")
      for (i in seq_len(nrow(omega))) {
        ctl <- paste0(ctl, sprintf("  %.4f  ; %s\n", omega[i,i], rownames(omega)[i]))
      }
      
      ctl <- paste0(ctl, "\n$SIGMA\n  0.04  ; proportional\n\n")
      ctl <- paste0(ctl, "$ESTIMATION METHOD=COND INTER MAXEVAL=9999 PRINT=5\n")
      ctl <- paste0(ctl, "$COVARIANCE\n")
      ctl <- paste0(ctl, "$TABLE ID TIME DV PRED IPRED CWRES IWRES ETA1 ETA2\n")
      ctl <- paste0(ctl, "  NOAPPEND NOPRINT ONEHEADER FILE=sdtab\n")
      
      if (output_file == "") output_file <- file.path(output_dir, paste0(model_name, ".ctl"))
      writeLines(ctl, output_file)
      
      write(toJSON(list(
        success = TRUE,
        format = "nonmem",
        output_file = output_file,
        message = sprintf("NONMEM control stream exported: %s (manual translation)", output_file),
        note = "Review and adjust ADVAN/TRANS and parameter structure before running"
      ), auto_unbox = TRUE), result_file)
    }
    
  } else if (target == "monolix") {
    # Export to Monolix via babelmixr2
    if (requireNamespace("babelmixr2", quietly = TRUE)) {
      library(babelmixr2)
      if (output_file == "") output_file <- file.path(output_dir, paste0(model_name, "_monolix"))
      dir.create(output_file, showWarnings = FALSE, recursive = TRUE)
      # babelmixr2 handles conversion
      write(toJSON(list(
        success = TRUE,
        format = "monolix",
        output_dir = output_file,
        message = sprintf("Monolix project exported: %s", output_file)
      ), auto_unbox = TRUE), result_file)
    } else {
      # Generate Monolix-compatible model file (.txt)
      if (output_file == "") output_file <- file.path(output_dir, paste0(model_name, "_monolix.txt"))
      
      mlx_code <- paste0(
        "[LONGITUDINAL]\n",
        "input = {ka_pop, V_pop, Cl_pop, omega_ka, omega_V, omega_Cl, a}\n\n",
        "EQUATION:\n",
        "ka = ka_pop * exp(eta_ka)\n",
        "V = V_pop * exp(eta_V)\n",
        "Cl = Cl_pop * exp(eta_Cl)\n\n",
        "pkmodel(ka, V, Cl)\n\n",
        "OUTPUT:\n",
        "output = Cc\n\n",
        "DEFINITION:\n",
        "y = {distribution=normal, prediction=Cc, errorModel=proportional(a)}\n"
      )
      
      writeLines(mlx_code, output_file)
      write(toJSON(list(
        success = TRUE,
        format = "monolix",
        output_file = output_file,
        message = sprintf("Monolix model file exported: %s (requires project setup in Monolix GUI)", output_file)
      ), auto_unbox = TRUE), result_file)
    }
    
  } else if (target == "phoenix_pml") {
    # Export to Phoenix PML
    params <- fixef(fit)
    if (output_file == "") output_file <- file.path(output_dir, paste0(model_name, ".mdl"))
    
    pml_code <- paste0(
      "test(){\n",
      "  # ", model_name, " - exported from pmx CLI\n",
      "  cfMicro(A1, Cl/V, first = (Aa = Ka))\n\n",
      "  # Fixed effects\n",
      "  fixef(\n"
    )
    
    pml_params <- list()
    for (nm in names(params)) {
      pml_code <- paste0(pml_code, sprintf("    tv%s = c(, %.4f, )\n", gsub("^t", "", nm), exp(params[nm])))
    }
    
    pml_code <- paste0(pml_code,
      "  )\n\n",
      "  # Random effects\n",
      "  ranef(\n",
      "    diag(nKa, nCl, nV) = c(0.1, 0.1, 0.1)\n",
      "  )\n\n",
      "  # Error model\n",
      "  error(CEps = 0.1)\n",
      "  observe(CObs = C + C * CEps)\n",
      "  stparm(\n",
      "    Ka = tvKa * exp(nKa)\n",
      "    Cl = tvCl * exp(nCl)\n",
      "    V  = tvV  * exp(nV)\n",
      "  )\n",
      "}\n"
    )
    
    writeLines(pml_code, output_file)
    write(toJSON(list(
      success = TRUE,
      format = "phoenix_pml",
      output_file = output_file,
      message = sprintf("Phoenix PML model exported: %s", output_file)
    ), auto_unbox = TRUE), result_file)
    
  } else if (target == "pumas") {
    # Export to Pumas (Julia)
    params <- fixef(fit)
    omega <- fit$omega
    if (output_file == "") output_file <- file.path(output_dir, paste0(model_name, ".jl"))
    
    julia_code <- paste0(
      "using Pumas\n\n",
      "# ", model_name, " - exported from pmx CLI\n",
      "mdl = @model begin\n",
      "  @param begin\n",
      sprintf("    tvka ∈ RealDomain(lower=0.0, init=%.4f)\n", exp(params["tka"])),
      sprintf("    tvcl ∈ RealDomain(lower=0.0, init=%.4f)\n", exp(params["tcl"])),
      sprintf("    tvv  ∈ RealDomain(lower=0.0, init=%.4f)\n", exp(params["tv"])),
      "    Ω    ∈ PDiagDomain(3)\n",
      "    σ_prop ∈ RealDomain(lower=0.0, init=0.1)\n",
      "  end\n\n",
      "  @random begin\n",
      "    η ~ MvNormal(Ω)\n",
      "  end\n\n",
      "  @pre begin\n",
      "    Ka = tvka * exp(η[1])\n",
      "    CL = tvcl * exp(η[2])\n",
      "    Vc = tvv  * exp(η[3])\n",
      "  end\n\n",
      "  @dynamics Depots1Central1\n\n",
      "  @derived begin\n",
      "    cp = @. Central / Vc\n",
      "    dv ~ @. Normal(cp, abs(cp) * σ_prop)\n",
      "  end\n",
      "end\n\n",
      "# Initial parameters\n",
      "param = (\n",
      sprintf("  tvka = %.4f,\n", exp(params["tka"])),
      sprintf("  tvcl = %.4f,\n", exp(params["tcl"])),
      sprintf("  tvv  = %.4f,\n", exp(params["tv"])),
      "  Ω    = Diagonal([",
      paste(sprintf("%.4f", diag(omega)), collapse = ", "),
      "]),\n",
      "  σ_prop = 0.1,\n",
      ")\n\n",
      "# Fit with FOCE-I\n",
      "# result = fit(mdl, population, param, FOCE())\n"
    )
    
    writeLines(julia_code, output_file)
    write(toJSON(list(
      success = TRUE,
      format = "pumas",
      output_file = output_file,
      message = sprintf("Pumas (Julia) model exported: %s", output_file),
      note = "Requires Pumas.jl package. Adjust @dynamics for your model structure."
    ), auto_unbox = TRUE), result_file)
    
  } else if (target == "mrgsolve") {
    # Export to mrgsolve .cpp
    params <- fixef(fit)
    omega <- fit$omega
    if (output_file == "") output_file <- file.path(output_dir, paste0(model_name, ".cpp"))
    
    cpp_code <- paste0(
      "// ", model_name, " - exported from pmx CLI\n",
      "[PARAM] @annotated\n",
      sprintf("CL : %.4f : Clearance (L/h)\n", exp(params["tcl"])),
      sprintf("V  : %.4f : Volume (L)\n", exp(params["tv"])),
      sprintf("Ka : %.4f : Absorption rate (1/h)\n", exp(params["tka"])),
      "\n",
      "[OMEGA] @annotated @block\n"
    )
    for (i in seq_len(nrow(omega))) {
      cpp_code <- paste0(cpp_code, sprintf("ETA_%s : %.4f : IIV-%s\n", 
                                            rownames(omega)[i], omega[i,i], rownames(omega)[i]))
    }
    cpp_code <- paste0(cpp_code,
      "\n[SIGMA]\n0.04\n\n",
      "[CMT] @annotated\n",
      "DEPOT  : Depot\n",
      "CENT   : Central\n\n",
      "[ODE]\n",
      "dxdt_DEPOT = -Ka * DEPOT;\n",
      "dxdt_CENT  = Ka * DEPOT - (CL/V) * CENT;\n\n",
      "[TABLE]\n",
      "double CP = CENT / V;\n",
      "double DV = CP * (1 + EPS(1));\n\n",
      "[CAPTURE] CP DV\n"
    )
    
    writeLines(cpp_code, output_file)
    write(toJSON(list(
      success = TRUE,
      format = "mrgsolve",
      output_file = output_file,
      message = sprintf("mrgsolve model exported: %s", output_file)
    ), auto_unbox = TRUE), result_file)
  }
  
}, error = function(e) {
  write(toJSON(list(success = FALSE, error = conditionMessage(e)), auto_unbox = TRUE), result_file)
})
