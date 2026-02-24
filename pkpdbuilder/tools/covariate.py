"""Covariate model building tools."""
import os
import json
import tempfile
from .registry import register_tool
from .data import get_current_dataset


@register_tool(
    name="covariate_screening",
    description="""Screen covariates for potential effects on PK parameters. Generates:
1. ETA vs covariate scatter/box plots with correlation statistics
2. Univariate covariate-parameter relationship summary
3. Categorical covariate effect sizes (geometric mean ratios)
4. Continuous covariate correlation coefficients (Spearman)
5. Recommended covariates for formal testing

Uses empirical Bayes estimates (ETAs) from a fitted model. This is the exploratory step before formal stepwise covariate modeling.""",
    parameters={
        "properties": {
            "model_name": {
                "type": "string",
                "description": "Name of the fitted base model",
                "default": "model"
            },
            "covariates": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of covariate column names to screen. If empty, auto-detects from dataset."
            }
        },
        "required": []
    }
)
def covariate_screening(model_name: str = "model", covariates: list = None) -> dict:
    from ..r_bridge import run_r_script
    from ..config import load_config
    config = load_config()
    
    # Get covariates from dataset if not specified
    if not covariates and get_current_dataset() is not None:
        df = get_current_dataset()
        skip = {"ID", "TIME", "DV", "AMT", "EVID", "MDV", "CMT", "RATE", "SS", "II", "ADDL"}
        covariates = [c for c in df.columns if c not in skip]
    
    args = {
        "model_name": model_name,
        "covariates": covariates or [],
        "output_dir": config["output_dir"],
    }
    
    return run_r_script("covariate_screen.R", args, config)


@register_tool(
    name="stepwise_covariate_model",
    description="""Run stepwise covariate model (SCM) building using forward addition and backward elimination.

Forward addition: Test each covariate-parameter relationship. Include if ΔOFV > 3.84 (p<0.05, 1 df).
Backward elimination: Remove covariates one by one. Keep if ΔOFV > 6.63 (p<0.01, 1 df).

Supports:
- Continuous covariates: linear, power, exponential effects
- Categorical covariates: proportional shift
- Allometric scaling (power model centered on reference)

Returns the final covariate model with parameter estimates.""",
    parameters={
        "properties": {
            "model_name": {
                "type": "string",
                "description": "Name of the base model to add covariates to"
            },
            "covariates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "covariate": {"type": "string", "description": "Covariate column name"},
                        "parameters": {"type": "array", "items": {"type": "string"}, "description": "PK parameters to test (e.g., ['CL', 'V'])"},
                        "effect_type": {"type": "string", "enum": ["linear", "power", "exponential", "proportional"], "description": "Type of covariate effect"}
                    }
                },
                "description": "Covariate-parameter relationships to test"
            },
            "forward_p": {
                "type": "number",
                "description": "p-value threshold for forward addition (default: 0.05)",
                "default": 0.05
            },
            "backward_p": {
                "type": "number",
                "description": "p-value threshold for backward elimination (default: 0.01)",
                "default": 0.01
            }
        },
        "required": ["model_name", "covariates"]
    }
)
def stepwise_covariate_model(model_name: str, covariates: list,
                              forward_p: float = 0.05, backward_p: float = 0.01) -> dict:
    from ..r_bridge import run_r_script
    from ..config import load_config
    config = load_config()
    
    # Save current dataset for R
    if get_current_dataset() is not None:
        tmp = tempfile.mktemp(suffix='.csv')
        get_current_dataset().to_csv(tmp, index=False)
    else:
        return {"success": False, "error": "No dataset loaded."}
    
    args = {
        "model_name": model_name,
        "data_file": tmp,
        "covariates": covariates,
        "forward_p": forward_p,
        "backward_p": backward_p,
        "output_dir": config["output_dir"],
    }
    
    result = run_r_script("covariate_scm.R", args, config, timeout=1800)
    
    try:
        os.unlink(tmp)
    except:
        pass
    
    return result


@register_tool(
    name="forest_plot",
    description="""Generate a forest plot showing covariate effects on PK parameters.
Shows the estimated effect of each covariate (point estimate + 90% CI) relative to the reference.
Standard pharmacometrics visualization used in regulatory submissions.

Reads covariate effects from a fitted model with covariates included.""",
    parameters={
        "properties": {
            "model_name": {
                "type": "string",
                "description": "Name of the covariate model"
            },
            "reference_subject": {
                "type": "object",
                "description": "Reference subject characteristics (e.g., {WT: 70, AGE: 40, SEX: 0})"
            }
        },
        "required": ["model_name"]
    }
)
def forest_plot(model_name: str, reference_subject: dict = None) -> dict:
    from ..r_bridge import run_r_script
    from ..config import load_config
    config = load_config()
    
    args = {
        "model_name": model_name,
        "reference_subject": reference_subject or {},
        "output_dir": config["output_dir"],
    }
    
    return run_r_script("forest_plot.R", args, config)
