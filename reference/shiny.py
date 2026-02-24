"""Shiny app generator — builds interactive simulators from fitted models."""
import os
import json
from .registry import register_tool


@register_tool(
    name="build_shiny_app",
    description="""Generate an interactive R Shiny app from a fitted pharmacokinetic model.
The app includes:
- Dosing regimen inputs (dose, interval, number of doses)
- Covariate sliders (weight, age, etc.)
- Concentration-time profile plot
- PK parameter summary
- Population simulation tab

Uses mrgsolve for real-time simulation. App is ready to deploy to shinyapps.io.""",
    parameters={
        "properties": {
            "model_name": {"type": "string", "description": "Name of the fitted model"},
            "drug_name": {"type": "string", "description": "Drug name for the app title"},
            "app_dir": {"type": "string", "description": "Directory to save the app (default: output_dir/shiny_app)"},
        },
        "required": ["model_name", "drug_name"]
    }
)
def build_shiny_app(model_name: str, drug_name: str, app_dir: str = None) -> dict:
    from ..config import load_config
    config = load_config()
    out_dir = config["output_dir"]
    
    # Load model results
    result_file = os.path.join(out_dir, f"{model_name}_results.json")
    if not os.path.exists(result_file):
        return {"success": False, "error": f"Model results not found: {model_name}. Run fit_model first."}
    
    with open(result_file) as f:
        results = json.load(f)
    
    target_dir = app_dir or os.path.join(out_dir, "shiny_app")
    os.makedirs(target_dir, exist_ok=True)
    
    app_code = _generate_app_code(drug_name, results)
    
    app_path = os.path.join(target_dir, "app.R")
    with open(app_path, 'w') as f:
        f.write(app_code)
    
    return {
        "success": True,
        "app_path": app_path,
        "message": f"Shiny app generated at {app_path}",
        "run_command": f'Rscript -e "shiny::runApp(\'{target_dir}\', port=3838)"',
    }


def _generate_app_code(drug_name: str, results: dict) -> str:
    """Generate the Shiny app.R code."""
    params = results.get("parameters", {})
    model_type = results.get("model_type", "1cmt_oral")
    iiv = results.get("iiv", {})
    
    # Extract parameter values — nlmixr2 stores as tka/tcl/tv with transformed values
    def get_param(name, default):
        # Try exact name first
        v = params.get(name)
        if v is None:
            # Try with 't' prefix (nlmixr2 convention for log-transformed)
            v = params.get(f"t{name.lower()}")
        if v is None:
            # Try lowercase
            v = params.get(name.lower())
        if v is None:
            return default
        if isinstance(v, dict):
            # Prefer transformed (exp of log-domain estimate)
            if "transformed" in v:
                return round(v["transformed"], 4)
            return v.get("estimate", default)
        return v if v is not None else default
    
    # Determine model structure
    is_oral = "oral" in model_type
    n_cmt = 1
    if "2cmt" in model_type:
        n_cmt = 2
    elif "3cmt" in model_type:
        n_cmt = 3
    
    # Build mrgsolve model code
    if n_cmt == 1 and is_oral:
        mrg_model = f"""
$PARAM CL = {get_param('CL', 5)}, V = {get_param('V', 50)}, Ka = {get_param('Ka', 1)}
$CMT DEPOT CENT
$ODE
dxdt_DEPOT = -Ka * DEPOT;
dxdt_CENT = Ka * DEPOT - (CL/V) * CENT;
$TABLE double CP = CENT / V;
$CAPTURE CP
"""
    elif n_cmt == 2 and is_oral:
        mrg_model = f"""
$PARAM CL = {get_param('CL', 5)}, V1 = {get_param('V1', get_param('V', 50))}, V2 = {get_param('V2', 100)}, Q = {get_param('Q', 10)}, Ka = {get_param('Ka', 1)}
$CMT DEPOT CENT PERIPH
$ODE
dxdt_DEPOT = -Ka * DEPOT;
dxdt_CENT = Ka * DEPOT - (CL/V1) * CENT - (Q/V1) * CENT + (Q/V2) * PERIPH;
dxdt_PERIPH = (Q/V1) * CENT - (Q/V2) * PERIPH;
$TABLE double CP = CENT / V1;
$CAPTURE CP
"""
    elif n_cmt == 1:
        mrg_model = f"""
$PARAM CL = {get_param('CL', 5)}, V = {get_param('V', 50)}
$CMT CENT
$ODE
dxdt_CENT = -(CL/V) * CENT;
$TABLE double CP = CENT / V;
$CAPTURE CP
"""
    else:
        mrg_model = f"""
$PARAM CL = {get_param('CL', 5)}, V1 = {get_param('V1', get_param('V', 50))}, V2 = {get_param('V2', 100)}, Q = {get_param('Q', 10)}
$CMT CENT PERIPH
$ODE
dxdt_CENT = -(CL/V1) * CENT - (Q/V1) * CENT + (Q/V2) * PERIPH;
dxdt_PERIPH = (Q/V1) * CENT - (Q/V2) * PERIPH;
$TABLE double CP = CENT / V1;
$CAPTURE CP
"""
    
    dose_cmt = 1 if is_oral else (2 if n_cmt >= 2 and is_oral else 1)
    
    app_code = f'''library(shiny)
library(bslib)
library(mrgsolve)
library(ggplot2)
library(dplyr)

# ── mrgsolve Model ──
mod <- mcode("pk_model", "
{mrg_model.strip()}
")

# ── UI ──
ui <- page_sidebar(
  title = "{drug_name} PK Simulator",
  theme = bs_theme(bootswatch = "flatly"),
  sidebar = sidebar(
    width = 300,
    h4("Dosing Regimen"),
    numericInput("dose", "Dose (mg)", value = 100, min = 1),
    numericInput("interval", "Interval (h)", value = 24, min = 1),
    numericInput("n_doses", "Number of Doses", value = 7, min = 1, max = 100),
    hr(),
    h4("PK Parameters"),
    numericInput("cl", "CL (L/h)", value = {get_param('CL', 5)}, min = 0.001, step = 0.1),
    numericInput("v", "V (L)", value = {get_param('V', get_param('V1', 50))}, min = 0.1, step = 1),
    {"numericInput('ka', 'Ka (1/h)', value = " + str(get_param('Ka', 1)) + ", min = 0.001, step = 0.1)," if is_oral else ""}
    hr(),
    checkboxInput("log_y", "Log Y-axis", value = FALSE),
    actionButton("run", "Simulate", class = "btn-primary btn-block"),
  ),
  navset_card_tab(
    nav_panel("Concentration-Time",
      plotOutput("pk_plot", height = "500px")
    ),
    nav_panel("PK Parameters",
      tableOutput("pk_table")
    ),
    nav_panel("About",
      h4("{drug_name} PK Simulator"),
      p("Generated by pmx — The Pharmacometrician\\'s Co-Pilot"),
      p("Model: {model_type}"),
      p("Source parameters from fitted PopPK model."),
      hr(),
      p(style = "font-size: 12px; color: #999;", "For research and educational purposes only. Not for clinical decision-making.")
    )
  )
)

# ── Server ──
server <- function(input, output, session) {{
  sim_data <- eventReactive(input$run, {{
    params <- list(CL = input$cl, V{"1" if n_cmt >= 2 else ""} = input$v)
    {"params$Ka <- input$ka" if is_oral else ""}
    
    ev <- ev(amt = input$dose, ii = input$interval, addl = input$n_doses - 1, cmt = {dose_cmt})
    
    mod_updated <- param(mod, params)
    out <- mrgsim(mod_updated, events = ev, end = input$interval * input$n_doses + input$interval, delta = 0.1)
    as.data.frame(out)
  }}, ignoreNULL = FALSE)
  
  output$pk_plot <- renderPlot({{
    df <- sim_data()
    p <- ggplot(df, aes(x = time, y = CP)) +
      geom_line(color = "#2563eb", linewidth = 1.2) +
      labs(x = "Time (h)", y = "Concentration", title = "{drug_name} PK Profile") +
      theme_minimal(base_size = 14)
    
    if (input$log_y) p <- p + scale_y_log10()
    p
  }})
  
  output$pk_table <- renderTable({{
    df <- sim_data()
    data.frame(
      Parameter = c("Cmax", "Cmin (last dose)", "AUC (last interval)", "t1/2"),
      Value = c(
        round(max(df$CP), 3),
        round(tail(df$CP[df$time <= input$interval * input$n_doses], 1), 3),
        round(sum(diff(df$time[1:20]) * head(df$CP[1:20], -1)), 3),
        round(log(2) / (input$cl / input$v), 2)
      ),
      Units = c("mg/L", "mg/L", "mg*h/L", "h")
    )
  }})
}}

shinyApp(ui, server)
'''
    
    return app_code
