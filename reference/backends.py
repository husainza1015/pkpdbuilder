"""Multi-engine backend support — nlmixr2, NONMEM, Monolix, Phoenix NLME, Pumas."""
import os
import json
import shutil
from .registry import register_tool


@register_tool(
    name="list_backends",
    description="""List available pharmacometric estimation backends and their status.
Checks for: nlmixr2 (R), NONMEM (Fortran), Monolix (Lixoft), Phoenix NLME (Certara), Pumas (Julia).
Reports which are installed and ready to use.""",
    parameters={"properties": {}, "required": []}
)
def list_backends() -> dict:
    from ..r_bridge import run_r_code
    from ..config import load_config
    config = load_config()
    
    backends = {}
    
    # nlmixr2 (always primary)
    r_check = run_r_code('cat(requireNamespace("nlmixr2", quietly=TRUE))', config, timeout=10)
    backends["nlmixr2"] = {
        "status": "available" if r_check.get("stdout", "").strip() == "TRUE" else "not installed",
        "language": "R",
        "license": "open source (GPL-2)",
        "estimation": ["FOCE-I", "SAEM", "nlme"],
        "description": "Open-source NLME estimation engine in R"
    }
    
    # NONMEM
    nonmem_path = os.environ.get("NONMEM_HOME", "/opt/NONMEM")
    nmfe_exists = any(
        os.path.exists(os.path.join(nonmem_path, f"run/nmfe{v}"))
        for v in ["75", "74", "73"]
    )
    backends["nonmem"] = {
        "status": "available" if nmfe_exists else "not found",
        "language": "Fortran",
        "license": "commercial (ICON/Certara)",
        "estimation": ["FOCE-I", "SAEM", "IMP", "BAYES"],
        "description": "Industry gold-standard NLME software",
        "path": nonmem_path if nmfe_exists else None
    }
    
    # Monolix
    monolix_path = os.environ.get("MONOLIX_HOME", "")
    if not monolix_path:
        # Check common locations
        for p in ["/opt/Lixoft/MonolixSuite", os.path.expanduser("~/Lixoft/MonolixSuite"),
                  "/Applications/MonolixSuite.app"]:
            if os.path.exists(p):
                monolix_path = p
                break
    
    # Also check R lixoftConnectors
    mlx_r = run_r_code('cat(requireNamespace("lixoftConnectors", quietly=TRUE))', config, timeout=10)
    mlx_available = os.path.exists(monolix_path) if monolix_path else False
    mlx_r_available = mlx_r.get("stdout", "").strip() == "TRUE"
    
    backends["monolix"] = {
        "status": "available" if (mlx_available or mlx_r_available) else "not found",
        "language": "R (lixoftConnectors) / standalone",
        "license": "commercial (Lixoft/Simulations Plus)",
        "estimation": ["SAEM"],
        "description": "SAEM-based NLME estimation with model libraries",
        "r_interface": mlx_r_available,
        "path": monolix_path if mlx_available else None
    }
    
    # Phoenix NLME (PML)
    phoenix_path = os.environ.get("PHOENIX_HOME", "")
    if not phoenix_path:
        for p in ["/opt/Certara/Phoenix", os.path.expanduser("~/Certara/Phoenix"),
                  "C:\\Program Files\\Certara\\Phoenix"]:
            if os.path.exists(p):
                phoenix_path = p
                break
    
    # Check R Certara.NLME8
    phnx_r = run_r_code('cat(requireNamespace("Certara.NLME8", quietly=TRUE))', config, timeout=10)
    phnx_available = os.path.exists(phoenix_path) if phoenix_path else False
    phnx_r_available = phnx_r.get("stdout", "").strip() == "TRUE"
    
    backends["phoenix_nlme"] = {
        "status": "available" if (phnx_available or phnx_r_available) else "not found",
        "language": "PML / R (Certara.NLME8)",
        "license": "commercial (Certara)",
        "estimation": ["FOCE-I", "QRPEM", "Laplacian", "Naive pooled"],
        "description": "Certara's NLME engine with PML model language",
        "r_interface": phnx_r_available,
        "path": phoenix_path if phnx_available else None
    }
    
    # Pumas (Julia)
    julia_path = shutil.which("julia")
    pumas_available = False
    if julia_path:
        import subprocess
        try:
            result = subprocess.run(
                [julia_path, "-e", 'using Pumas; println("OK")'],
                capture_output=True, text=True, timeout=30
            )
            pumas_available = "OK" in result.stdout
        except:
            pass
    
    backends["pumas"] = {
        "status": "available" if pumas_available else ("julia found, Pumas not installed" if julia_path else "not found"),
        "language": "Julia",
        "license": "commercial (PumasAI)",
        "estimation": ["FOCE-I", "SAEM", "Bayesian", "DeepPumas (ML-augmented)"],
        "description": "Julia-based NLME with ML-augmented modeling (DeepPumas)",
        "julia_path": julia_path,
        "features": ["DeepPumas neural-ODE", "Bayesian estimation", "GPU acceleration"]
    }
    
    available = [k for k, v in backends.items() if v["status"] == "available"]
    
    return {
        "success": True,
        "backends": backends,
        "available": available,
        "n_available": len(available),
        "message": f"{len(available)} backends available: {', '.join(available)}"
    }


@register_tool(
    name="export_model",
    description="""Export a fitted nlmixr2 model to another software format:
- NONMEM control stream (.ctl) — via babelmixr2
- Monolix project (.mlxtran) — via babelmixr2
- Phoenix NLME (PML) — via babelmixr2 or manual translation
- Pumas (Julia) — via manual translation
- mrgsolve (.cpp) — for simulation

Useful for teams that need to validate results across platforms or submit in a specific format.""",
    parameters={
        "properties": {
            "model_name": {
                "type": "string",
                "description": "Name of the fitted nlmixr2 model to export"
            },
            "target": {
                "type": "string",
                "enum": ["nonmem", "monolix", "phoenix_pml", "pumas", "mrgsolve"],
                "description": "Target software format"
            },
            "output_file": {
                "type": "string",
                "description": "Output file path (auto-generated if not specified)"
            }
        },
        "required": ["model_name", "target"]
    }
)
def export_model(model_name: str, target: str, output_file: str = None) -> dict:
    from ..r_bridge import run_r_script
    from ..config import load_config
    config = load_config()
    
    args = {
        "model_name": model_name,
        "target": target,
        "output_file": output_file or "",
        "output_dir": config["output_dir"],
    }
    
    return run_r_script("export_model.R", args, config, timeout=120)


@register_tool(
    name="import_model",
    description="""Import a model from another pharmacometric software into nlmixr2:
- NONMEM control stream + output (.ctl/.lst) — via nonmem2rx
- Monolix project (.mlxtran) — via monolix2rx
- Phoenix PML — manual translation
- Pumas Julia code — manual translation

The imported model can then be used with all pmx tools (diagnostics, simulation, etc.).""",
    parameters={
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the model file to import"
            },
            "source_format": {
                "type": "string",
                "enum": ["nonmem", "monolix", "phoenix_pml", "pumas"],
                "description": "Source software format"
            },
            "model_name": {
                "type": "string",
                "description": "Name for the imported model",
                "default": "imported_model"
            }
        },
        "required": ["file_path", "source_format"]
    }
)
def import_model(file_path: str, source_format: str, model_name: str = "imported_model") -> dict:
    from ..r_bridge import run_r_script
    from ..config import load_config
    config = load_config()
    
    args = {
        "file_path": file_path,
        "source_format": source_format,
        "model_name": model_name,
        "output_dir": config["output_dir"],
    }
    
    return run_r_script("import_model.R", args, config, timeout=120)
