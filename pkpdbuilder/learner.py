"""Adaptive learning engine — learns user preferences from usage patterns.

Tracks what the user does, detects patterns, and personalizes defaults over time.
All data stored in ~/.pkpdbuilder/profile/ and per-project memory/.
"""
import json
import os
from datetime import datetime, date
from pathlib import Path
from collections import Counter


PROFILE_DIR = Path.home() / ".pkpdbuilder" / "profile"
PROFILE_FILE = PROFILE_DIR / "user_profile.json"
USAGE_LOG = PROFILE_DIR / "usage_log.jsonl"
PROMPTS_FILE = PROFILE_DIR / "user_prompts.md"


def _ensure_dirs():
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def load_profile() -> dict:
    """Load user profile, creating defaults if needed."""
    _ensure_dirs()
    if PROFILE_FILE.exists():
        with open(PROFILE_FILE) as f:
            return json.load(f)
    return _default_profile()


def save_profile(profile: dict):
    """Save user profile."""
    _ensure_dirs()
    profile["updated"] = datetime.now().isoformat()
    with open(PROFILE_FILE, "w") as f:
        json.dump(profile, f, indent=2)


def _default_profile() -> dict:
    return {
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
        "version": 1,

        # Modeling preferences (learned over time)
        "modeling": {
            "preferred_estimation": None,      # e.g., "focei", "saem"
            "preferred_error_model": None,      # e.g., "proportional", "combined"
            "preferred_compartments": None,     # e.g., 2 if user always picks 2-CMT
            "always_try_models": [],            # e.g., ["1cmt", "2cmt"]
            "iiv_parameters": None,             # e.g., ["CL", "V", "Ka"]
            "preferred_algorithm": None,        # e.g., "nlminb", "bobyqa"
        },

        # Diagnostic preferences
        "diagnostics": {
            "auto_run_gof": True,
            "auto_run_vpc": True,
            "auto_run_eta": True,
            "auto_individual_fits": False,      # flips to True after user requests it
            "vpc_n_simulations": 200,           # updates if user always changes
            "preferred_vpc_type": None,         # "standard" or "pcvpc"
        },

        # Covariate analysis
        "covariates": {
            "auto_screen": True,
            "preferred_method": None,           # "scm", "wam", "manual"
            "significance_threshold": 0.05,
            "always_test": [],                  # covariates user always includes
            "never_test": [],                   # covariates user always skips
        },

        # Output preferences
        "output": {
            "preferred_report_format": "html",  # html, pdf, beamer
            "auto_generate_report": False,       # True if user always asks for report
            "auto_build_shiny": False,           # True if user always wants a Shiny app
            "auto_export_formats": [],           # e.g., ["nonmem", "pumas"]
            "preferred_plot_style": None,        # e.g., dark theme, specific colors
        },

        # Workflow patterns
        "workflow": {
            "typical_sequence": [],              # learned from usage order
            "skip_nca": False,                   # True if user always skips NCA
            "auto_compare_models": True,
            "blq_handling": None,                # e.g., "M3", "M1"
        },

        # Drug/therapeutic area expertise
        "expertise": {
            "drugs_analyzed": [],                # track drugs for context
            "therapeutic_areas": [],             # e.g., ["oncology", "rare disease"]
            "typical_routes": [],                # e.g., ["oral", "iv"]
            "typical_populations": [],           # e.g., ["pediatric", "renal impairment"]
        },

        # Usage stats
        "stats": {
            "total_sessions": 0,
            "total_models_fit": 0,
            "total_analyses": 0,
            "first_use": datetime.now().isoformat(),
            "last_use": datetime.now().isoformat(),
        }
    }


def log_prompt(prompt: str):
    """Append user prompt to user_prompts.md with timestamp."""
    _ensure_dirs()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header_needed = not PROMPTS_FILE.exists() or PROMPTS_FILE.stat().st_size == 0
    with open(PROMPTS_FILE, "a") as f:
        if header_needed:
            f.write("# User Prompts Log\n\n")
            f.write("All prompts sent to PKPDBuilder, logged for learning and reproducibility.\n\n")
            f.write("---\n\n")
        f.write(f"**[{ts}]**\n> {prompt}\n\n")


def log_event(event_type: str, data: dict):
    """Append a usage event to the log."""
    _ensure_dirs()
    entry = {
        "ts": datetime.now().isoformat(),
        "type": event_type,
        **data,
    }
    with open(USAGE_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def log_tool_call(tool_name: str, args: dict, result_summary: str = ""):
    """Log a tool invocation for pattern learning."""
    log_event("tool_call", {
        "tool": tool_name,
        "args": _sanitize_args(args),
        "result": result_summary[:200],
    })


def log_model_fit(model_name: str, compartments: int, route: str,
                  estimation: str, ofv: float = None, converged: bool = True):
    """Log a model fitting event."""
    log_event("model_fit", {
        "model": model_name,
        "compartments": compartments,
        "route": route,
        "estimation": estimation,
        "ofv": ofv,
        "converged": converged,
    })

    profile = load_profile()
    profile["stats"]["total_models_fit"] = profile["stats"].get("total_models_fit", 0) + 1
    profile["stats"]["last_use"] = datetime.now().isoformat()
    save_profile(profile)


def log_model_selected(model_name: str, reason: str):
    """Log which model the user/agent selected as final."""
    log_event("model_selected", {"model": model_name, "reason": reason})


def log_drug_analysis(drug_name: str, route: str = "", therapeutic_area: str = ""):
    """Log a new drug analysis for expertise tracking."""
    profile = load_profile()
    profile["stats"]["total_analyses"] = profile["stats"].get("total_analyses", 0) + 1
    
    drugs = profile["expertise"]["drugs_analyzed"]
    if drug_name.lower() not in [d.lower() for d in drugs]:
        drugs.append(drug_name)
    
    if route and route not in profile["expertise"]["typical_routes"]:
        profile["expertise"]["typical_routes"].append(route)
    
    if therapeutic_area and therapeutic_area not in profile["expertise"]["therapeutic_areas"]:
        profile["expertise"]["therapeutic_areas"].append(therapeutic_area)
    
    save_profile(profile)


def log_session_start():
    """Log session start."""
    profile = load_profile()
    profile["stats"]["total_sessions"] = profile["stats"].get("total_sessions", 0) + 1
    profile["stats"]["last_use"] = datetime.now().isoformat()
    save_profile(profile)


def learn_from_history():
    """Analyze usage log and update profile with learned patterns.
    
    Called periodically (e.g., at session start or after N tool calls).
    Detects repeated patterns and updates defaults.
    """
    if not USAGE_LOG.exists():
        return

    profile = load_profile()
    events = []
    with open(USAGE_LOG) as f:
        for line in f:
            try:
                events.append(json.loads(line))
            except:
                continue

    if len(events) < 5:
        return  # Need enough data to learn

    # ── Learn estimation method preference ──
    estimations = [e["estimation"] for e in events 
                   if e["type"] == "model_fit" and "estimation" in e]
    if len(estimations) >= 3:
        most_common = Counter(estimations).most_common(1)[0]
        if most_common[1] / len(estimations) >= 0.7:
            profile["modeling"]["preferred_estimation"] = most_common[0]

    # ── Learn compartment preference ──
    selected = [e for e in events if e["type"] == "model_selected"]
    if len(selected) >= 3:
        # Look at what compartment models get selected
        sel_models = [e["model"] for e in selected]
        cmt_counts = Counter()
        for e in events:
            if e["type"] == "model_fit" and e.get("model") in sel_models:
                cmt_counts[e.get("compartments", 1)] += 1
        if cmt_counts:
            preferred = cmt_counts.most_common(1)[0]
            if preferred[1] >= 2:
                profile["modeling"]["preferred_compartments"] = preferred[0]

    # ── Learn which tools user always requests ──
    tool_calls = [e["tool"] for e in events if e["type"] == "tool_call"]
    tool_counts = Counter(tool_calls)
    total_sessions = max(profile["stats"].get("total_sessions", 1), 1)

    # If user runs individual_fits in >60% of sessions, auto-enable
    if tool_counts.get("individual_fits", 0) / total_sessions > 0.6:
        profile["diagnostics"]["auto_individual_fits"] = True

    # If user always generates report
    if tool_counts.get("generate_report", 0) / total_sessions > 0.7:
        profile["output"]["auto_generate_report"] = True

    # If user always builds Shiny app
    if tool_counts.get("build_shiny_app", 0) / total_sessions > 0.5:
        profile["output"]["auto_build_shiny"] = True

    # ── Learn export format preferences ──
    exports = [e for e in events if e["type"] == "tool_call" and e["tool"] == "export_model"]
    if exports:
        formats = [e["args"].get("format", "") for e in exports]
        common_formats = [f for f, c in Counter(formats).items() if c >= 2 and f]
        if common_formats:
            profile["output"]["auto_export_formats"] = common_formats

    # ── Learn VPC preferences ──
    vpcs = [e for e in events if e["type"] == "tool_call" and e["tool"] == "vpc"]
    if len(vpcs) >= 2:
        vpc_sims = [e["args"].get("n_simulations", 200) for e in vpcs]
        if len(set(vpc_sims)) == 1 and vpc_sims[0] != 200:
            profile["diagnostics"]["vpc_n_simulations"] = vpc_sims[0]
        
        vpc_types = [e["args"].get("prediction_corrected", False) for e in vpcs]
        if all(vpc_types):
            profile["diagnostics"]["preferred_vpc_type"] = "pcvpc"

    # ── Learn BLQ handling ──
    blq_calls = [e for e in events if e["type"] == "tool_call" and e["tool"] == "handle_blq"]
    if len(blq_calls) >= 2:
        methods = [e["args"].get("method", "M1") for e in blq_calls]
        most_common = Counter(methods).most_common(1)[0]
        if most_common[1] >= 2:
            profile["workflow"]["blq_handling"] = most_common[0]

    # ── Learn covariate preferences ──
    cov_calls = [e for e in events if e["type"] == "tool_call" 
                 and e["tool"] in ("covariate_screening", "stepwise_covariate_model")]
    if cov_calls:
        tested_covs = []
        for e in cov_calls:
            covs = e["args"].get("covariates", [])
            if isinstance(covs, list):
                tested_covs.extend(covs)
        common_covs = [c for c, n in Counter(tested_covs).items() if n >= 2]
        if common_covs:
            profile["covariates"]["always_test"] = common_covs

    # ── Learn workflow sequence ──
    session_tools = []
    for e in events:
        if e["type"] == "tool_call":
            session_tools.append(e["tool"])
    if len(session_tools) >= 10:
        # Extract common subsequences
        profile["workflow"]["typical_sequence"] = _extract_sequence(session_tools)

    save_profile(profile)
    return profile


def _extract_sequence(tools: list) -> list:
    """Extract the most common tool ordering pattern."""
    # Look for the typical analysis workflow order
    workflow_tools = [
        "load_dataset", "summarize_dataset", "plot_data", "dataset_qc",
        "run_nca", "fit_model", "fit_from_library", "compare_models",
        "goodness_of_fit", "vpc", "eta_plots", "individual_fits",
        "covariate_screening", "stepwise_covariate_model", "forest_plot",
        "simulate_regimen", "population_simulation",
        "generate_report", "build_shiny_app", "export_model",
    ]
    # Return tools in the order they typically appear
    seen = []
    for t in tools:
        if t in workflow_tools and t not in seen:
            seen.append(t)
    return seen[:15]


def get_personalized_prompt_section() -> str:
    """Generate a system prompt section from learned preferences.
    
    Injected into the agent's system prompt to personalize behavior.
    """
    profile = load_profile()
    sections = []

    # Modeling defaults
    m = profile["modeling"]
    if m["preferred_estimation"]:
        sections.append(f"- User prefers {m['preferred_estimation']} estimation")
    if m["preferred_compartments"]:
        sections.append(f"- User typically selects {m['preferred_compartments']}-compartment models")
    if m["preferred_error_model"]:
        sections.append(f"- User prefers {m['preferred_error_model']} error model")

    # Diagnostics
    d = profile["diagnostics"]
    if d["auto_individual_fits"]:
        sections.append("- Always generate individual fit plots (user's preference)")
    if d["vpc_n_simulations"] != 200:
        sections.append(f"- User prefers VPC with {d['vpc_n_simulations']} simulations")
    if d["preferred_vpc_type"] == "pcvpc":
        sections.append("- User prefers prediction-corrected VPC")

    # Output
    o = profile["output"]
    if o["auto_generate_report"]:
        sections.append("- Automatically generate an analysis report at the end")
    if o["auto_build_shiny"]:
        sections.append("- Automatically build a Shiny simulator app")
    if o["auto_export_formats"]:
        fmts = ", ".join(o["auto_export_formats"])
        sections.append(f"- Auto-export model to: {fmts}")

    # Workflow
    w = profile["workflow"]
    if w["blq_handling"]:
        sections.append(f"- Default BLQ handling: {w['blq_handling']}")
    if w["skip_nca"]:
        sections.append("- User typically skips NCA (go straight to model fitting)")

    # Covariates
    c = profile["covariates"]
    if c["always_test"]:
        covs = ", ".join(c["always_test"])
        sections.append(f"- Always test these covariates: {covs}")

    # Expertise context
    e = profile["expertise"]
    if e["drugs_analyzed"]:
        recent = e["drugs_analyzed"][-5:]
        sections.append(f"- Previously analyzed: {', '.join(recent)}")
    if e["therapeutic_areas"]:
        sections.append(f"- Expertise areas: {', '.join(e['therapeutic_areas'])}")

    # Stats
    s = profile["stats"]
    if s["total_analyses"] > 0:
        sections.append(f"- User has completed {s['total_analyses']} analyses ({s['total_models_fit']} models fit)")

    if not sections:
        return ""

    header = "\n## Learned User Preferences\n"
    header += "(Automatically learned from usage patterns — adapt defaults accordingly)\n"
    return header + "\n".join(sections) + "\n"


def _sanitize_args(args: dict) -> dict:
    """Remove large/sensitive values from args for logging."""
    clean = {}
    for k, v in args.items():
        if isinstance(v, str) and len(v) > 200:
            clean[k] = v[:100] + "..."
        else:
            clean[k] = v
    return clean
