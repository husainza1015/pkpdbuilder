"""Simulation tools using mrgsolve."""
import os
import tempfile
import json
from .registry import register_tool
from .data import get_current_dataset


@register_tool(
    name="simulate_regimen",
    description="""Simulate concentration-time profiles for a dosing regimen using mrgsolve.
Uses parameters from a fitted model or user-specified values.
Supports single and multiple dosing, different routes, and steady-state.
Returns simulated profiles and generates a plot.""",
    parameters={
        "properties": {
            "model_name": {
                "type": "string",
                "description": "Name of fitted model to use parameters from (or 'custom' for manual params)"
            },
            "dose": {"type": "number", "description": "Dose amount (mg)"},
            "interval": {"type": "number", "description": "Dosing interval (hours)"},
            "n_doses": {"type": "integer", "description": "Number of doses", "default": 1},
            "duration": {"type": "number", "description": "Infusion duration (hours, 0 for bolus/oral)", "default": 0},
            "sim_duration": {"type": "number", "description": "Total simulation time (hours)"},
            "n_subjects": {"type": "integer", "description": "Number of virtual subjects (1 = typical, >1 = population)", "default": 1},
            "custom_params": {
                "type": "object",
                "description": "Custom parameters if model_name='custom' (e.g., {CL: 5, V: 50, Ka: 1.5})"
            }
        },
        "required": ["dose", "sim_duration"]
    }
)
def simulate_regimen(dose: float, sim_duration: float, model_name: str = None,
                     interval: float = None, n_doses: int = 1, duration: float = 0,
                     n_subjects: int = 1, custom_params: dict = None) -> dict:
    from ..r_bridge import run_r_script
    from ..config import load_config
    config = load_config()
    
    args = {
        "dose": dose,
        "sim_duration": sim_duration,
        "interval": interval or sim_duration,
        "n_doses": n_doses,
        "duration": duration,
        "n_subjects": n_subjects,
        "output_dir": config["output_dir"],
    }
    
    # Load params from fitted model or use custom
    if model_name and model_name != "custom":
        result_file = os.path.join(config["output_dir"], f"{model_name}_results.json")
        if os.path.exists(result_file):
            with open(result_file) as f:
                model_results = json.load(f)
            args["model_params"] = model_results.get("parameters", {})
            args["iiv"] = model_results.get("iiv", {})
            args["model_type"] = model_results.get("model_type", "1cmt_oral")
        else:
            return {"success": False, "error": f"Model results not found: {model_name}"}
    elif custom_params:
        args["model_params"] = custom_params
        args["model_type"] = "custom"
    else:
        return {"success": False, "error": "Provide model_name or custom_params"}
    
    return run_r_script("simulate_mrgsolve.R", args, config, timeout=300)


@register_tool(
    name="population_simulation",
    description="""Simulate a virtual population using fitted model parameters with IIV.
Generates N virtual patients and simulates concentration-time profiles.
Returns summary statistics (median, 5th/95th percentiles) and individual profiles.
Useful for dose selection, therapeutic window analysis, and exposure predictions.""",
    parameters={
        "properties": {
            "model_name": {"type": "string", "description": "Name of fitted model"},
            "dose": {"type": "number", "description": "Dose amount (mg)"},
            "interval": {"type": "number", "description": "Dosing interval (hours)"},
            "n_doses": {"type": "integer", "description": "Number of doses", "default": 7},
            "n_subjects": {"type": "integer", "description": "Number of virtual subjects", "default": 500},
            "sim_duration": {"type": "number", "description": "Total simulation time (hours)"},
            "covariates": {
                "type": "object",
                "description": "Covariate distributions (e.g., {WT: {mean: 70, sd: 15}, SEX: {prob_female: 0.5}})"
            }
        },
        "required": ["model_name", "dose", "sim_duration"]
    }
)
def population_simulation(model_name: str, dose: float, sim_duration: float,
                          interval: float = None, n_doses: int = 7,
                          n_subjects: int = 500, covariates: dict = None) -> dict:
    from ..r_bridge import run_r_script
    from ..config import load_config
    config = load_config()
    
    args = {
        "model_name": model_name,
        "dose": dose,
        "interval": interval or 24,
        "n_doses": n_doses,
        "n_subjects": n_subjects,
        "sim_duration": sim_duration,
        "covariates": covariates or {},
        "output_dir": config["output_dir"],
    }
    
    # Load model params
    result_file = os.path.join(config["output_dir"], f"{model_name}_results.json")
    if os.path.exists(result_file):
        with open(result_file) as f:
            model_results = json.load(f)
        args["model_params"] = model_results.get("parameters", {})
        args["iiv"] = model_results.get("iiv", {})
        args["model_type"] = model_results.get("model_type", "1cmt_oral")
    else:
        return {"success": False, "error": f"Model results not found: {model_name}"}
    
    return run_r_script("population_sim.R", args, config, timeout=600)
