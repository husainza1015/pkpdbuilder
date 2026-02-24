"""R subprocess bridge — execute R scripts and return results."""
import subprocess
import json
import tempfile
import os
from pathlib import Path

R_SCRIPTS_DIR = Path(__file__).parent / "r_scripts"


def run_r_script(script_name: str, args: dict, config: dict, timeout: int = 600) -> dict:
    """
    Run an R script with JSON args, return JSON result.
    
    Convention: Each R script reads args from a temp JSON file,
    writes results to another temp JSON file.
    """
    script_path = R_SCRIPTS_DIR / script_name
    if not script_path.exists():
        return {"success": False, "error": f"R script not found: {script_name}"}
    
    # Write args to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(args, f)
        args_file = f.name
    
    result_file = tempfile.mktemp(suffix='.json')
    
    try:
        env = os.environ.copy()
        env["PMX_ARGS_FILE"] = args_file
        env["PMX_RESULT_FILE"] = result_file
        env["PMX_OUTPUT_DIR"] = config.get("output_dir", "./pmx_output")
        
        proc = subprocess.run(
            [config.get("r_path", "Rscript"), str(script_path)],
            capture_output=True, text=True, timeout=timeout, env=env
        )
        
        if proc.returncode != 0:
            return {
                "success": False,
                "error": f"R script failed:\n{proc.stderr[-2000:] if proc.stderr else 'No error output'}",
                "stdout": proc.stdout[-1000:] if proc.stdout else ""
            }
        
        if os.path.exists(result_file):
            with open(result_file) as f:
                result = json.load(f)
            result["success"] = True
            return result
        else:
            return {
                "success": True,
                "stdout": proc.stdout,
                "message": "Script completed but no structured result file produced."
            }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"R script timed out after {timeout}s"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        for f in [args_file, result_file]:
            try:
                os.unlink(f)
            except FileNotFoundError:
                pass


def run_r_code(code: str, config: dict, timeout: int = 300) -> dict:
    """Run arbitrary R code and capture output."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.R', delete=False) as f:
        f.write(code)
        script_file = f.name
    
    try:
        proc = subprocess.run(
            [config.get("r_path", "Rscript"), script_file],
            capture_output=True, text=True, timeout=timeout
        )
        return {
            "success": proc.returncode == 0,
            "stdout": proc.stdout[-3000:] if proc.stdout else "",
            "stderr": proc.stderr[-2000:] if proc.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"R code timed out after {timeout}s"}
    finally:
        try:
            os.unlink(script_file)
        except FileNotFoundError:
            pass


def check_r_environment(config: dict) -> dict:
    """Check that R and required packages are available."""
    code = """
    pkgs <- c("nlmixr2", "mrgsolve", "xpose", "vpc", "ggplot2", "dplyr", "jsonlite", "PKNCA")
    installed <- sapply(pkgs, requireNamespace, quietly=TRUE)
    cat(jsonlite::toJSON(list(
        r_version = paste(R.version$major, R.version$minor, sep="."),
        packages = as.list(installed)
    ), auto_unbox=TRUE))
    """
    result = run_r_code(code, config, timeout=30)
    if result["success"] and result["stdout"]:
        try:
            info = json.loads(result["stdout"].strip())
            info["success"] = True
            return info
        except json.JSONDecodeError:
            pass
    return {"success": False, "error": result.get("stderr", "Unknown error")}
