"""Presentation and report generation tools — Beamer slides and Word/PPT."""
import os
import json
from datetime import datetime
from .registry import register_tool


@register_tool(
    name="generate_beamer_slides",
    description="""Generate a LaTeX Beamer slide deck for a pharmacometrics team meeting or regulatory presentation.

Includes slides for:
- Title and objectives
- Dataset summary
- Model development history
- Parameter estimates table
- GOF diagnostic panel
- VPC
- ETA distributions and covariate effects
- Forest plot (if covariate model)
- Simulation results
- Conclusions

Output: .Rmd file that renders to PDF via rmarkdown::render(). Requires LaTeX/TinyTeX.""",
    parameters={
        "properties": {
            "model_name": {"type": "string", "description": "Final model name", "default": "model"},
            "drug_name": {"type": "string", "description": "Drug name"},
            "title": {"type": "string", "description": "Presentation title"},
            "author": {"type": "string", "description": "Author name", "default": "PMX CLI"},
            "theme": {"type": "string", "description": "Beamer theme", "default": "Madrid"},
            "include_vpc": {"type": "boolean", "default": True},
            "include_forest": {"type": "boolean", "default": False},
        },
        "required": ["drug_name"]
    }
)
def generate_beamer_slides(drug_name: str, model_name: str = "model",
                           title: str = None, author: str = "PMX CLI",
                           theme: str = "Madrid", include_vpc: bool = True,
                           include_forest: bool = False) -> dict:
    from ..config import load_config
    config = load_config()
    out_dir = config["output_dir"]
    
    pres_title = title or f"Population Pharmacokinetic Analysis of {drug_name}"
    
    # Load model results
    model_results = None
    result_file = os.path.join(out_dir, f"{model_name}_results.json")
    if os.path.exists(result_file):
        with open(result_file) as f:
            model_results = json.load(f)
    
    # Collect available plots
    plots = {}
    plot_patterns = {
        "gof": [f"gof_{model_name}.png", "gof.png"],
        "vpc": [f"vpc_{model_name}.png", "vpc.png"],
        "eta": [f"eta_{model_name}.png", "eta.png"],
        "spaghetti": ["data_spaghetti.png"],
        "individual": ["data_individual.png"],
        "forest": [f"forest_{model_name}.png", "forest.png"],
        "population_sim": ["population_sim.png"],
    }
    for name, patterns in plot_patterns.items():
        for pattern in patterns:
            path = os.path.join(out_dir, pattern)
            if os.path.exists(path):
                plots[name] = os.path.abspath(path)
                break
    
    rmd_content = _build_beamer_rmd(pres_title, author, drug_name, model_name, 
                                      model_results, plots, theme, include_vpc, include_forest)
    
    rmd_path = os.path.join(out_dir, f"{drug_name.lower().replace(' ', '_')}_slides.Rmd")
    with open(rmd_path, 'w') as f:
        f.write(rmd_content)
    
    # Try to render PDF
    pdf_path = rmd_path.replace('.Rmd', '.pdf')
    render_cmd = None
    
    return {
        "success": True,
        "rmd_path": rmd_path,
        "render_command": f'Rscript -e "rmarkdown::render(\'{rmd_path}\')"',
        "message": f"Beamer slides saved: {rmd_path}. Render with: Rscript -e \"rmarkdown::render('{rmd_path}')\"",
        "slides": list(plots.keys()) + ["title", "dataset", "parameters", "conclusions"],
    }


def _build_beamer_rmd(title, author, drug_name, model_name, results, plots, theme, inc_vpc, inc_forest):
    """Build the Beamer R Markdown content."""
    
    # Parameter table
    param_table_code = ""
    if results and results.get("parameters"):
        params = results["parameters"]
        iiv = results.get("iiv", {})
        rows = []
        for pname, pval in params.items():
            if isinstance(pval, dict):
                est = pval.get("transformed", pval.get("estimate", ""))
                desc = pval.get("description", pname)
                rse = pval.get("rse_pct", "-")
                # Find matching IIV
                eta_key = f"eta.{desc}" if desc != pname else f"eta.{pname}"
                iiv_cv = iiv.get(eta_key, {}).get("cv_pct", "-") if iiv else "-"
            else:
                est = pval
                desc = pname
                rse = "-"
                iiv_cv = "-"
            rows.append(f'  c("{desc}", "{est}", "{rse}", "{iiv_cv}")')
        
        param_table_code = f"""
param_df <- data.frame(
  Parameter = c({', '.join([f'"{r.split(",")[0].strip().replace("c(", "").replace('"', "")}"' for r in rows])}),
  rbind({', '.join(rows)})
)
names(param_df) <- c("Parameter", "Estimate", "RSE%", "IIV %CV")
knitr::kable(param_df, format = "latex", booktabs = TRUE) |>
  kableExtra::kable_styling(font_size = 9, latex_options = "striped")
"""
    
    rmd = f"""---
title: "{title}"
author: "{author}"
date: "{datetime.now().strftime('%B %d, %Y')}"
output:
  beamer_presentation:
    theme: "{theme}"
    colortheme: "seahorse"
    fonttheme: "structurebold"
    slide_level: 2
    keep_tex: false
header-includes:
  - \\usepackage{{booktabs}}
  - \\usepackage{{graphicx}}
---

```{{r setup, include=FALSE}}
knitr::opts_chunk$set(echo = FALSE, warning = FALSE, message = FALSE, 
                       fig.align = "center", out.width = "90%")
library(knitr)
library(kableExtra)
```

# Analysis Overview

## Objectives

- Develop a population pharmacokinetic model for **{drug_name}**
- Characterize inter-individual variability in PK parameters
- Evaluate covariate effects on PK
- Support dose selection through simulation

"""
    
    # Dataset slide
    if results:
        rmd += f"""## Dataset Summary

- **Subjects:** {results.get('n_subjects', 'N/A')}
- **Observations:** {results.get('n_observations', 'N/A')}
- **Model type:** {results.get('model_type', 'N/A')}
- **Estimation:** {results.get('estimation', 'FOCE-I')}

"""
    
    # Data overview
    if "spaghetti" in plots:
        rmd += f"""## Concentration-Time Data

```{{r data-overview}}
knitr::include_graphics("{plots['spaghetti']}")
```

"""
    
    # Model development
    rmd += "# Model Development\n\n"
    
    # Parameter table
    if param_table_code:
        rmd += f"""## Final Model Parameters

```{{r param-table, results='asis'}}
{param_table_code}
```

"""
    
    if results:
        rmd += f"""## Model Fit Summary

| Metric | Value |
|--------|-------|
| OFV | {results.get('ofv', 'N/A')} |
| AIC | {results.get('aic', 'N/A')} |
| BIC | {results.get('bic', 'N/A')} |
| Converged | {'Yes' if results.get('converged') else 'No'} |

"""
    
    # Diagnostics
    rmd += "# Diagnostics\n\n"
    
    if "gof" in plots:
        rmd += f"""## Goodness of Fit

```{{r gof}}
knitr::include_graphics("{plots['gof']}")
```

"""
    
    if inc_vpc and "vpc" in plots:
        rmd += f"""## Visual Predictive Check

```{{r vpc}}
knitr::include_graphics("{plots['vpc']}")
```

"""
    
    if "eta" in plots:
        rmd += f"""## ETA Distributions

```{{r eta}}
knitr::include_graphics("{plots['eta']}")
```

"""
    
    if inc_forest and "forest" in plots:
        rmd += f"""## Covariate Effects

```{{r forest}}
knitr::include_graphics("{plots['forest']}")
```

"""
    
    # Simulations
    if "population_sim" in plots:
        rmd += f"""# Simulations

## Population Simulation

```{{r pop-sim}}
knitr::include_graphics("{plots['population_sim']}")
```

"""
    
    # Conclusions
    rmd += f"""# Summary

## Conclusions

- Population PK model for **{drug_name}** successfully developed
- Model adequately describes observed data (GOF, VPC)
- Key findings:
  - [Add key covariate effects]
  - [Add dosing implications]

## References

- Generated by **pmx** — The Pharmacometrician's Co-Pilot
- nlmixr2, mrgsolve, PKNCA
"""
    
    return rmd
