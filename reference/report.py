"""Report generation tools."""
import os
import json
from datetime import datetime
from .registry import register_tool


@register_tool(
    name="generate_report",
    description="""Generate a PopPK analysis report in HTML format. Includes:
- Dataset summary
- Model development history (base → final)
- Parameter estimates table
- Diagnostic plots
- VPC
- Simulation results
Follows FDA Population PK Guidance structure.""",
    parameters={
        "properties": {
            "model_name": {"type": "string", "description": "Final model name", "default": "model"},
            "drug_name": {"type": "string", "description": "Drug name for the report title"},
            "author": {"type": "string", "description": "Report author", "default": "PMX CLI"},
            "title": {"type": "string", "description": "Custom report title"},
        },
        "required": ["drug_name"]
    }
)
def generate_report(drug_name: str, model_name: str = "model", 
                    author: str = "PMX CLI", title: str = None) -> dict:
    from ..config import load_config
    config = load_config()
    out_dir = config["output_dir"]
    
    report_title = title or f"Population Pharmacokinetic Analysis of {drug_name}"
    
    # Collect available results
    model_results = None
    result_file = os.path.join(out_dir, f"{model_name}_results.json")
    if os.path.exists(result_file):
        with open(result_file) as f:
            model_results = json.load(f)
    
    # Collect plot files
    plots = {}
    for plot_name in ["gof", "vpc", "eta", "spaghetti", "data_plots", "population_sim"]:
        for ext in [".png", f"_{model_name}.png"]:
            path = os.path.join(out_dir, f"{plot_name}{ext}")
            if os.path.exists(path):
                plots[plot_name] = path
                break
    
    # Build HTML report
    html = _build_report_html(report_title, author, drug_name, model_name, model_results, plots, out_dir)
    
    report_path = os.path.join(out_dir, f"{drug_name.lower().replace(' ', '_')}_popPK_report.html")
    with open(report_path, 'w') as f:
        f.write(html)
    
    return {
        "success": True,
        "report_path": report_path,
        "message": f"Report generated: {report_path}",
        "sections": list(plots.keys()) + (["parameters", "model_summary"] if model_results else []),
    }


def _build_report_html(title, author, drug_name, model_name, results, plots, out_dir):
    """Build the HTML report content."""
    import base64
    
    def embed_image(path):
        if os.path.exists(path):
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            return f'<img src="data:image/png;base64,{b64}" style="max-width:100%;margin:10px 0;">'
        return "<p><em>Plot not available</em></p>"
    
    # Parameter table
    param_html = ""
    if results and results.get("parameters"):
        param_html = "<table><thead><tr><th>Parameter</th><th>Estimate</th><th>RSE%</th><th>IIV (%CV)</th></tr></thead><tbody>"
        params = results["parameters"]
        iiv = results.get("iiv", {})
        for pname, pval in params.items():
            if isinstance(pval, dict):
                est = pval.get("estimate", "")
                rse = pval.get("rse_pct", "")
                iiv_val = iiv.get(pname, {}).get("cv_pct", "-")
            else:
                est = pval
                rse = "-"
                iiv_val = iiv.get(pname, "-")
            param_html += f"<tr><td>{pname}</td><td>{est}</td><td>{rse}</td><td>{iiv_val}</td></tr>"
        param_html += "</tbody></table>"
    
    # Model summary
    summary_html = ""
    if results:
        summary_html = f"""
        <h2>Model Summary</h2>
        <ul>
            <li><strong>Model Type:</strong> {results.get('model_type', 'N/A')}</li>
            <li><strong>Estimation:</strong> {results.get('estimation', 'FOCE-I')}</li>
            <li><strong>OFV:</strong> {results.get('ofv', 'N/A')}</li>
            <li><strong>AIC:</strong> {results.get('aic', 'N/A')}</li>
            <li><strong>BIC:</strong> {results.get('bic', 'N/A')}</li>
            <li><strong>Converged:</strong> {'Yes' if results.get('converged') else 'No'}</li>
        </ul>
        """
    
    html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #1a1a1a; line-height: 1.6; }}
h1 {{ border-bottom: 2px solid #2563eb; padding-bottom: 10px; }}
h2 {{ color: #2563eb; margin-top: 40px; }}
table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
th {{ background: #f5f7ff; font-weight: 600; }}
tr:nth-child(even) {{ background: #fafbff; }}
.meta {{ color: #666; font-size: 0.9em; margin-bottom: 30px; }}
.section {{ margin: 30px 0; }}
</style>
</head><body>
<h1>{title}</h1>
<div class="meta">
    <p>Author: {author} | Drug: {drug_name} | Date: {datetime.now().strftime('%Y-%m-%d')}</p>
    <p>Generated by <strong>pmx</strong> — The Pharmacometrician's Co-Pilot</p>
</div>

{summary_html}

<div class="section">
<h2>Parameter Estimates</h2>
{param_html or "<p><em>No model results available. Run fit_model first.</em></p>"}
</div>

<div class="section">
<h2>Goodness of Fit</h2>
{embed_image(plots.get('gof', ''))}
</div>

<div class="section">
<h2>Visual Predictive Check</h2>
{embed_image(plots.get('vpc', ''))}
</div>

<div class="section">
<h2>ETA Diagnostics</h2>
{embed_image(plots.get('eta', ''))}
</div>

<div class="section">
<h2>Data Overview</h2>
{embed_image(plots.get('spaghetti', plots.get('data_plots', '')))}
</div>

</body></html>"""
    
    return html
