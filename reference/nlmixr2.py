"""nlmixr2 model fitting tools."""
import os
import json
import tempfile
from .registry import register_tool
from .data import get_current_dataset, get_current_dataset_path


@register_tool(
    name="fit_from_library",
    description="""Fit a model from the PMX model library to the loaded dataset.
This connects the 59-model library (PK, PD, PK/PD, TMDD, advanced) to nlmixr2.
Use list_model_library to browse available models, then fit_from_library to run them.
The model's R code is injected directly into nlmixr2 — supports all model types including
transit absorption, Michaelis-Menten, IDR Types I-IV, TMDD, effect compartment, etc.

Examples:
  fit_from_library(library_model="pk_1cmt_oral_mm", model_name="M_mm")
  fit_from_library(library_model="pkpd_1cmt_oral_idr1", model_name="M_idr1")
  fit_from_library(library_model="tmdd_qss_2cmt", model_name="M_tmdd")""",
    parameters={
        "properties": {
            "library_model": {
                "type": "string",
                "description": "Model name from the library (e.g., 'pk_2cmt_oral_mm', 'pd_idr1_imax', 'tmdd_qss_1cmt')"
            },
            "model_name": {
                "type": "string",
                "description": "Label for this fit (e.g., 'M3', 'base_mm')",
                "default": "model"
            },
            "estimation": {
                "type": "string",
                "enum": ["focei", "saem"],
                "description": "Estimation method (default: focei)",
                "default": "focei"
            },
            "error_model": {
                "type": "string",
                "enum": ["proportional", "additive", "combined"],
                "description": "Override residual error model (default: use model's built-in)",
            }
        },
        "required": ["library_model"]
    }
)
def fit_from_library(library_model: str, model_name: str = "model",
                     estimation: str = "focei", error_model: str = None) -> dict:
    if get_current_dataset() is None:
        return {"success": False, "error": "No dataset loaded. Use load_dataset first."}
    
    from ..r_bridge import run_r_script
    from ..config import load_config
    from ..models import get_model
    
    try:
        model_info = get_model(library_model)
    except KeyError as e:
        return {"success": False, "error": str(e)}
    
    config = load_config()
    
    tmp = tempfile.mktemp(suffix='.csv')
    get_current_dataset().to_csv(tmp, index=False)
    
    args = {
        "data_file": tmp,
        "model_code": model_info["code"],
        "model_name": model_name,
        "library_model": library_model,
        "estimation": estimation,
        "error_model": error_model or "",
        "output_dir": config["output_dir"],
    }
    
    result = run_r_script("fit_library_model.R", args, config, timeout=900)
    
    try:
        os.unlink(tmp)
    except:
        pass
    
    return result


@register_tool(
    name="fit_model",
    description="""Fit a population pharmacokinetic model using nlmixr2. Supports:
- Structural models: 1-compartment, 2-compartment, 3-compartment
- Absorption: first-order (oral), zero-order (IV infusion), IV bolus, transit compartment
- IIV: on CL, V (V1/V2), Ka, Q, V3 — specify which parameters get random effects
- Residual error: proportional, additive, combined
- Covariates: allometric scaling on WT, linear/proportional effects
- Estimation: FOCE-I (default), SAEM

Returns parameter estimates, standard errors, OFV, AIC/BIC, and convergence status.""",
    parameters={
        "properties": {
            "model_type": {
                "type": "string",
                "enum": ["1cmt_oral", "1cmt_iv", "2cmt_oral", "2cmt_iv", "3cmt_iv"],
                "description": "Structural model type"
            },
            "iiv_on": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Parameters with inter-individual variability (e.g., ['CL', 'V', 'Ka'])",
                "default": ["CL", "V"]
            },
            "error_model": {
                "type": "string",
                "enum": ["proportional", "additive", "combined"],
                "description": "Residual error model",
                "default": "proportional"
            },
            "covariates": {
                "type": "array",
                "items": {"type": "object", "properties": {
                    "covariate": {"type": "string"},
                    "parameter": {"type": "string"},
                    "effect": {"type": "string", "enum": ["allometric", "linear", "proportional"]}
                }},
                "description": "Covariate effects to include",
                "default": []
            },
            "estimation": {
                "type": "string",
                "enum": ["focei", "saem"],
                "description": "Estimation method",
                "default": "focei"
            },
            "model_name": {
                "type": "string",
                "description": "Name/label for this model (e.g., 'M1', 'base_model')",
                "default": "model"
            }
        },
        "required": ["model_type"]
    }
)
def fit_model(model_type: str, iiv_on: list = None, error_model: str = "proportional",
              covariates: list = None, estimation: str = "focei", model_name: str = "model") -> dict:
    if get_current_dataset() is None:
        return {"success": False, "error": "No dataset loaded. Use load_dataset first."}
    
    from ..r_bridge import run_r_script
    from ..config import load_config
    
    config = load_config()
    
    # Save current dataset for R
    tmp = tempfile.mktemp(suffix='.csv')
    get_current_dataset().to_csv(tmp, index=False)
    
    args = {
        "data_file": tmp,
        "model_type": model_type,
        "iiv_on": iiv_on or ["CL", "V"],
        "error_model": error_model,
        "covariates": covariates or [],
        "estimation": estimation,
        "model_name": model_name,
        "output_dir": config["output_dir"],
    }
    
    result = run_r_script("fit_nlmixr2.R", args, config, timeout=900)
    
    try:
        os.unlink(tmp)
    except:
        pass
    
    return result


@register_tool(
    name="compare_models",
    description="Compare fitted models by OFV, AIC, BIC, and parameter counts. Reads model results from previous fit_model runs in the output directory. Returns a comparison table with recommendations.",
    parameters={
        "properties": {
            "model_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of model names to compare (must have been previously fit)"
            }
        },
        "required": ["model_names"]
    }
)
def compare_models(model_names: list) -> dict:
    from ..config import load_config
    config = load_config()
    out_dir = config["output_dir"]
    
    models = []
    for name in model_names:
        result_file = os.path.join(out_dir, f"{name}_results.json")
        if os.path.exists(result_file):
            with open(result_file) as f:
                models.append(json.load(f))
        else:
            models.append({"model_name": name, "error": "Results not found"})
    
    # Build comparison
    comparison = []
    for m in models:
        if "error" in m and "Results not found" in str(m.get("error", "")):
            comparison.append({"model": m["model_name"], "status": "not found"})
            continue
        comparison.append({
            "model": m.get("model_name", "?"),
            "model_type": m.get("model_type", "?"),
            "ofv": m.get("ofv"),
            "aic": m.get("aic"),
            "bic": m.get("bic"),
            "n_params": m.get("n_params"),
            "converged": m.get("converged", False),
        })
    
    # Sort by BIC
    valid = [c for c in comparison if c.get("bic") is not None]
    if valid:
        valid.sort(key=lambda x: x["bic"])
        best = valid[0]["model"]
    else:
        best = None
    
    return {
        "success": True,
        "comparison": comparison,
        "recommendation": f"Best model by BIC: {best}" if best else "No valid models to compare",
    }
