"""Non-compartmental analysis (NCA) tools."""
import os
import tempfile
from .registry import register_tool
from .data import get_current_dataset


@register_tool(
    name="run_nca",
    description="""Run non-compartmental analysis (NCA) using PKNCA (the gold-standard R NCA package). Calculates per-subject:
- Cmax, Tmax
- AUClast (linear-up/log-down trapezoidal)
- AUCinf (observed and predicted extrapolation)
- Terminal half-life (t½) with lambda_z and r²
- CL/F (oral) or CL (IV), Vz/F or Vss
- MRT, %AUC extrapolated
- And all other standard NCA parameters

Returns individual results, geometric mean summary with geometric CV%, and full PKNCA output CSV.
Compliant with regulatory NCA standards (FDA/EMA bioequivalence guidance).""",
    parameters={
        "properties": {
            "route": {
                "type": "string",
                "enum": ["oral", "iv_bolus", "iv_infusion"],
                "description": "Route of administration",
                "default": "oral"
            },
            "dose_col": {
                "type": "string",
                "description": "Column name for dose amount",
                "default": "AMT"
            },
            "n_terminal_points": {
                "type": "integer",
                "description": "Min points for terminal slope estimation",
                "default": 3
            }
        },
        "required": []
    }
)
def run_nca(route: str = "oral", dose_col: str = "AMT", n_terminal_points: int = 3) -> dict:
    if get_current_dataset() is None:
        return {"success": False, "error": "No dataset loaded."}
    
    from ..r_bridge import run_r_script
    from ..config import load_config
    config = load_config()
    
    tmp = tempfile.mktemp(suffix='.csv')
    get_current_dataset().to_csv(tmp, index=False)
    
    args = {
        "data_file": tmp,
        "route": route,
        "dose_col": dose_col,
        "n_terminal_points": n_terminal_points,
        "output_dir": config["output_dir"],
    }
    
    result = run_r_script("run_nca.R", args, config)
    
    try:
        os.unlink(tmp)
    except:
        pass
    
    return result
