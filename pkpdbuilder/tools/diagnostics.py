"""Diagnostic plot tools — GOF, VPC, ETA distributions, individual fits."""
import os
import json
import tempfile
from .registry import register_tool
from .data import get_current_dataset


@register_tool(
    name="goodness_of_fit",
    description="""Generate standard goodness-of-fit diagnostic plots for a fitted model:
1. DV vs PRED (population predictions)
2. DV vs IPRED (individual predictions)
3. CWRES vs TIME
4. CWRES vs PRED
5. |IWRES| vs IPRED
6. QQ plot of CWRES
Saves a combined panel PNG to the output directory.""",
    parameters={
        "properties": {
            "model_name": {
                "type": "string",
                "description": "Name of the fitted model (must match a previous fit_model run)",
                "default": "model"
            }
        },
        "required": []
    }
)
def goodness_of_fit(model_name: str = "model") -> dict:
    from ..r_bridge import run_r_script
    from ..config import load_config
    config = load_config()
    
    args = {
        "model_name": model_name,
        "output_dir": config["output_dir"],
    }
    
    return run_r_script("diagnostics.R", args, config)


@register_tool(
    name="vpc",
    description="""Run a Visual Predictive Check (VPC) for a fitted model. Simulates N replicates from the model and compares observed vs predicted percentiles (5th, 50th, 95th). Supports prediction-corrected VPC (pcVPC). Saves plot to output directory.""",
    parameters={
        "properties": {
            "model_name": {
                "type": "string",
                "description": "Name of the fitted model",
                "default": "model"
            },
            "n_sim": {
                "type": "integer",
                "description": "Number of simulation replicates",
                "default": 200
            },
            "prediction_corrected": {
                "type": "boolean",
                "description": "Use prediction-corrected VPC",
                "default": True
            }
        },
        "required": []
    }
)
def vpc(model_name: str = "model", n_sim: int = 200, prediction_corrected: bool = True) -> dict:
    from ..r_bridge import run_r_script
    from ..config import load_config
    config = load_config()
    
    args = {
        "model_name": model_name,
        "n_sim": n_sim,
        "prediction_corrected": prediction_corrected,
        "output_dir": config["output_dir"],
    }
    
    return run_r_script("vpc.R", args, config, timeout=600)


@register_tool(
    name="eta_plots",
    description="""Generate ETA (random effect) diagnostic plots:
1. ETA histograms with normality overlay
2. ETA vs ETA correlation matrix
3. ETA vs covariates (box plots for categorical, scatter for continuous)
Helps identify potential covariate effects and model misspecification.""",
    parameters={
        "properties": {
            "model_name": {
                "type": "string",
                "description": "Name of the fitted model",
                "default": "model"
            }
        },
        "required": []
    }
)
def eta_plots(model_name: str = "model") -> dict:
    from ..r_bridge import run_r_script
    from ..config import load_config
    config = load_config()
    
    args = {
        "model_name": model_name,
        "output_dir": config["output_dir"],
    }
    
    return run_r_script("eta_plots.R", args, config)


@register_tool(
    name="parameter_table",
    description="Generate a formatted parameter table for a fitted model including: fixed effects (theta), IIV (omega as %CV), residual error (sigma), RSE%, shrinkage, and condition number.",
    parameters={
        "properties": {
            "model_name": {
                "type": "string",
                "description": "Name of the fitted model",
                "default": "model"
            }
        },
        "required": []
    }
)
def parameter_table(model_name: str = "model") -> dict:
    from ..config import load_config
    import json
    
    config = load_config()
    result_file = os.path.join(config["output_dir"], f"{model_name}_results.json")
    
    if not os.path.exists(result_file):
        return {"success": False, "error": f"Model results not found: {model_name}"}
    
    with open(result_file) as f:
        results = json.load(f)
    
    return {
        "success": True,
        "model_name": model_name,
        "parameters": results.get("parameters", {}),
        "iiv": results.get("iiv", {}),
        "residual_error": results.get("residual_error", {}),
        "ofv": results.get("ofv"),
        "aic": results.get("aic"),
        "bic": results.get("bic"),
        "condition_number": results.get("condition_number"),
        "shrinkage": results.get("shrinkage", {}),
    }


@register_tool(
    name="individual_fits",
    description="""Generate individual observed vs predicted plots for each subject.
Shows observed data points overlaid with individual predictions (IPRED) and 
population predictions (PRED). Essential for regulatory submissions and assessing
model adequacy at the individual level. Subjects are arranged in paginated grid plots.""",
    parameters={
        "properties": {
            "model_name": {
                "type": "string",
                "description": "Name of the fitted model"
            },
            "n_per_page": {
                "type": "integer",
                "description": "Subjects per page (default 12)",
                "default": 12
            }
        },
        "required": ["model_name"]
    }
)
def individual_fits(model_name: str, n_per_page: int = 12) -> dict:
    from ..r_bridge import run_r_script
    from ..config import load_config
    config = load_config()
    
    args = {
        "model_name": model_name,
        "n_per_page": n_per_page,
        "output_dir": config["output_dir"],
    }
    
    return run_r_script("individual_fits.R", args, config)
