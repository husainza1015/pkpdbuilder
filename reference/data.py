"""Data loading, validation, and exploration tools."""
import json
import os
import pandas as pd
from pathlib import Path
from .registry import register_tool

# Module-level state for loaded dataset
_current_dataset = None
_current_dataset_path = None


def get_current_dataset():
    """Return the currently loaded dataset."""
    return _current_dataset


def get_current_dataset_path():
    return _current_dataset_path


@register_tool(
    name="load_dataset",
    description="Load a pharmacokinetic dataset from CSV or NONMEM format. Validates required columns (ID, TIME, DV). Accepts standard NONMEM columns: ID, TIME, DV, AMT, EVID, MDV, CMT, WT, AGE, SEX, etc. The file path can be absolute or relative to current directory.",
    parameters={
        "properties": {
            "file_path": {"type": "string", "description": "Path to the CSV dataset file"},
            "delimiter": {"type": "string", "description": "Column delimiter (default: auto-detect comma or whitespace)", "default": ","},
        },
        "required": ["file_path"]
    }
)
def load_dataset(file_path: str, delimiter: str = None) -> dict:
    global _current_dataset, _current_dataset_path
    
    path = Path(file_path).expanduser()
    if not path.exists():
        return {"success": False, "error": f"File not found: {file_path}"}
    
    try:
        # Auto-detect delimiter
        if delimiter:
            df = pd.read_csv(path, delimiter=delimiter)
        else:
            try:
                df = pd.read_csv(path)
            except Exception:
                df = pd.read_csv(path, delim_whitespace=True)
        
        # Normalize column names
        df.columns = [c.strip().upper() for c in df.columns]
        
        # Check required columns
        required = ["ID", "TIME", "DV"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            # Try common aliases
            aliases = {"CONC": "DV", "CONCENTRATION": "DV", "SUBJ": "ID", "SUBJECT": "ID", "TAD": "TIME"}
            for alias, target in aliases.items():
                if alias in df.columns and target in missing:
                    df.rename(columns={alias: target}, inplace=True)
                    missing.remove(target)
        
        if missing:
            return {
                "success": False,
                "error": f"Missing required columns: {missing}. Found: {list(df.columns)}",
                "columns": list(df.columns)
            }
        
        _current_dataset = df
        _current_dataset_path = str(path)
        
        # Save covariate data for later use (covariate screening needs it)
        from ..config import load_config, ensure_output_dir
        config = load_config()
        out = ensure_output_dir(config)
        df.to_csv(str(out / "covariate_data.csv"), index=False)
        
        # Compute summary
        n_subjects = df["ID"].nunique()
        n_obs = len(df[df.get("EVID", pd.Series([0]*len(df))) == 0])
        if "EVID" in df.columns:
            n_doses = len(df[df["EVID"] == 1])
        elif "AMT" in df.columns:
            n_doses = len(df[df["AMT"] > 0])
        else:
            n_doses = 0
        
        covariates = [c for c in df.columns if c not in ["ID", "TIME", "DV", "AMT", "EVID", "MDV", "CMT", "RATE", "SS", "II", "ADDL", "PRED", "IPRED", "CWRES", "WRES"]]
        
        obs_df = df[(df.get("EVID", 0) == 0) & (df["DV"].notna())]
        
        summary = {
            "success": True,
            "file": str(path.name),
            "n_subjects": int(n_subjects),
            "n_observations": int(n_obs),
            "n_doses": int(n_doses),
            "n_rows": len(df),
            "columns": list(df.columns),
            "covariates": covariates,
            "time_range": [float(df["TIME"].min()), float(df["TIME"].max())],
            "dv_range": [float(obs_df["DV"].min()), float(obs_df["DV"].max())] if len(obs_df) > 0 else [0, 0],
            "dose_amounts": sorted(df[df.get("AMT", pd.Series([0]*len(df))) > 0]["AMT"].unique().tolist()) if "AMT" in df.columns else [],
        }
        
        # Route of administration guess
        if "CMT" in df.columns:
            dose_cmts = df[df.get("EVID", 0) == 1]["CMT"].unique() if "EVID" in df.columns else []
            summary["dose_compartments"] = [int(c) for c in dose_cmts]
        
        return summary
        
    except Exception as e:
        return {"success": False, "error": f"Failed to load dataset: {e}"}


@register_tool(
    name="summarize_dataset",
    description="Generate a detailed summary of the currently loaded dataset including per-subject observation counts, covariate distributions, and dosing information.",
    parameters={"properties": {}, "required": []}
)
def summarize_dataset() -> dict:
    if _current_dataset is None:
        return {"success": False, "error": "No dataset loaded. Use load_dataset first."}
    
    df = _current_dataset
    obs = df[(df.get("EVID", 0) == 0) & (df["DV"].notna())]
    
    summary = {
        "success": True,
        "n_subjects": int(df["ID"].nunique()),
        "n_observations": len(obs),
        "obs_per_subject": {
            "mean": float(obs.groupby("ID").size().mean()),
            "min": int(obs.groupby("ID").size().min()),
            "max": int(obs.groupby("ID").size().max()),
        },
    }
    
    # Covariate summaries
    covariates = {}
    skip = {"ID", "TIME", "DV", "AMT", "EVID", "MDV", "CMT", "RATE", "SS", "II", "ADDL"}
    for col in df.columns:
        if col in skip:
            continue
        vals = df.groupby("ID")[col].first()
        if vals.nunique() <= 5:
            covariates[col] = {"type": "categorical", "values": vals.value_counts().to_dict()}
        else:
            covariates[col] = {
                "type": "continuous",
                "mean": round(float(vals.mean()), 2),
                "sd": round(float(vals.std()), 2),
                "min": round(float(vals.min()), 2),
                "max": round(float(vals.max()), 2),
                "median": round(float(vals.median()), 2),
            }
    summary["covariates"] = covariates
    
    # Dosing summary
    if "AMT" in df.columns:
        doses = df[df["AMT"] > 0] if "AMT" in df.columns else pd.DataFrame()
        if len(doses) > 0:
            summary["dosing"] = {
                "amounts": sorted(doses["AMT"].unique().tolist()),
                "n_doses_per_subject": {
                    "mean": float(doses.groupby("ID").size().mean()),
                    "min": int(doses.groupby("ID").size().min()),
                    "max": int(doses.groupby("ID").size().max()),
                }
            }
    
    return summary


@register_tool(
    name="plot_data",
    description="Generate exploratory plots of the loaded PK dataset: spaghetti plot (all subjects), individual profiles, or dose-normalized concentrations. Saves PNG files to the output directory.",
    parameters={
        "properties": {
            "plot_type": {
                "type": "string",
                "enum": ["spaghetti", "individual", "dose_normalized", "all"],
                "description": "Type of plot to generate",
                "default": "spaghetti"
            },
            "log_y": {"type": "boolean", "description": "Use log scale for y-axis", "default": False},
        },
        "required": []
    }
)
def plot_data(plot_type: str = "spaghetti", log_y: bool = False) -> dict:
    if _current_dataset is None:
        return {"success": False, "error": "No dataset loaded."}
    
    from ..r_bridge import run_r_script
    from ..config import load_config
    
    config = load_config()
    
    # Save dataset to temp file for R
    import tempfile
    tmp = tempfile.mktemp(suffix='.csv')
    _current_dataset.to_csv(tmp, index=False)
    
    args = {
        "data_file": tmp,
        "plot_type": plot_type,
        "log_y": log_y,
        "output_dir": config["output_dir"],
    }
    
    result = run_r_script("plot_data.R", args, config)
    
    try:
        os.unlink(tmp)
    except:
        pass
    
    return result
