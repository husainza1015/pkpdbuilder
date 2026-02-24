#!/usr/bin/env Rscript
# Import models from other software into nlmixr2
suppressPackageStartupMessages({
  library(jsonlite)
})

args_file <- Sys.getenv("PMX_ARGS_FILE")
result_file <- Sys.getenv("PMX_RESULT_FILE")
args <- fromJSON(args_file)

output_dir <- args$output_dir
file_path <- args$file_path
source_format <- args$source_format
model_name <- args$model_name

if (!file.exists(file_path)) {
  write(toJSON(list(success = FALSE, error = paste("File not found:", file_path)), auto_unbox = TRUE), result_file)
  quit(status = 0)
}

tryCatch({
  if (source_format == "nonmem") {
    # Import NONMEM via nonmem2rx
    if (requireNamespace("nonmem2rx", quietly = TRUE)) {
      library(nonmem2rx)
      library(rxode2)
      
      mod <- nonmem2rx(file_path, lst = sub("\\.ctl$", ".lst", file_path))
      
      # Save as rxode2/nlmixr2 model
      saveRDS(mod, file.path(output_dir, paste0(model_name, "_imported.rds")))
      
      write(toJSON(list(
        success = TRUE,
        format = "nonmem",
        model_name = model_name,
        message = sprintf("NONMEM model imported as '%s'. Use with nlmixr2 for re-estimation or rxode2 for simulation.", model_name)
      ), auto_unbox = TRUE), result_file)
    } else {
      write(toJSON(list(
        success = FALSE,
        error = "nonmem2rx package not installed. Install with: install.packages('nonmem2rx')"
      ), auto_unbox = TRUE), result_file)
    }
    
  } else if (source_format == "monolix") {
    # Import Monolix via monolix2rx
    if (requireNamespace("monolix2rx", quietly = TRUE)) {
      library(monolix2rx)
      
      mod <- monolix2rx(file_path)
      saveRDS(mod, file.path(output_dir, paste0(model_name, "_imported.rds")))
      
      write(toJSON(list(
        success = TRUE,
        format = "monolix",
        model_name = model_name,
        message = sprintf("Monolix model imported as '%s'. Ready for nlmixr2 re-estimation or rxode2 simulation.", model_name)
      ), auto_unbox = TRUE), result_file)
    } else {
      write(toJSON(list(
        success = FALSE,
        error = "monolix2rx package not installed. Install with: install.packages('monolix2rx')"
      ), auto_unbox = TRUE), result_file)
    }
    
  } else if (source_format == "phoenix_pml") {
    # Read PML file and provide translation guidance
    pml_code <- readLines(file_path)
    
    write(toJSON(list(
      success = TRUE,
      format = "phoenix_pml",
      model_name = model_name,
      pml_code = paste(pml_code, collapse = "\n"),
      message = "Phoenix PML file read. Automatic translation not yet available — Claude will translate the PML code to nlmixr2 syntax.",
      note = "babelmixr2 may support Phoenix PML import in future versions. For now, pmx will use AI to translate the model code."
    ), auto_unbox = TRUE), result_file)
    
  } else if (source_format == "pumas") {
    # Read Julia/Pumas code
    julia_code <- readLines(file_path)
    
    write(toJSON(list(
      success = TRUE,
      format = "pumas",
      model_name = model_name,
      julia_code = paste(julia_code, collapse = "\n"),
      message = "Pumas (Julia) model file read. Claude will translate the @model code to nlmixr2 syntax.",
      note = "Pumas models use similar ODE structure to nlmixr2 — translation is straightforward for standard PK/PD models."
    ), auto_unbox = TRUE), result_file)
  }
  
}, error = function(e) {
  write(toJSON(list(success = FALSE, error = conditionMessage(e)), auto_unbox = TRUE), result_file)
})
