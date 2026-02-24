"""Model library tool — browse, search, and retrieve pre-built nlmixr2 models."""
from .registry import register_tool


@register_tool(
    name="list_model_library",
    description="""List all pre-built models in the PMX model library. 
Contains 50+ models translated from Monolix model library to nlmixr2-ready code.
Categories: pk, pd, pkpd, tmdd, advanced.
Each model includes ready-to-use nlmixr2 R code, Monolix equivalent name, and metadata.""",
    parameters={
        "properties": {
            "category": {
                "type": "string",
                "enum": ["all", "pk", "pd", "pkpd", "tmdd", "advanced"],
                "description": "Filter by category (default: all)",
                "default": "all"
            },
            "search": {
                "type": "string",
                "description": "Search keyword (e.g., 'transit', 'emax', 'tmdd', 'oral')"
            }
        },
        "required": []
    }
)
def list_model_library(category: str = "all", search: str = None) -> dict:
    from pkpdbuilder.models import list_models, search_models
    
    if search:
        models = search_models(search)
    elif category == "all":
        models = list_models()
    else:
        models = list_models(category=category)
    
    summary = []
    for m in models:
        summary.append({
            "name": m["name"],
            "category": m["category"],
            "description": m["description"],
            "route": m.get("route", ""),
            "elimination": m.get("elimination", ""),
            "compartments": m.get("compartments", 0),
            "monolix_equivalent": m.get("monolix_equivalent", ""),
        })
    
    # Category counts
    cats = {}
    all_models = list_models()
    for m in all_models:
        cats[m["category"]] = cats.get(m["category"], 0) + 1
    
    return {
        "success": True,
        "total": len(all_models),
        "shown": len(summary),
        "categories": cats,
        "models": summary,
        "message": f"Library: {len(all_models)} models total. Showing {len(summary)} " + 
                   (f"matching '{search}'" if search else f"in '{category}'")
    }


@register_tool(
    name="get_model_code",
    description="""Retrieve the full nlmixr2 R code for a model from the library.
Returns ready-to-use model function code that can be passed directly to fit_model
or written to an R script. All models use standard nlmixr2 syntax with log-transformed
parameters, IIV, and residual error specification.""",
    parameters={
        "properties": {
            "model_name": {
                "type": "string",
                "description": "Model name (e.g., 'pk_1cmt_oral', 'pd_idr1_imax', 'tmdd_qss_2cmt')"
            }
        },
        "required": ["model_name"]
    }
)
def get_model_code(model_name: str) -> dict:
    from pkpdbuilder.models import get_model
    
    try:
        model = get_model(model_name)
        return {
            "success": True,
            "name": model["name"],
            "category": model["category"],
            "description": model["description"],
            "monolix_equivalent": model.get("monolix_equivalent", ""),
            "code": model["code"],
            "message": f"Model '{model['name']}' — {model['description']}"
        }
    except KeyError as e:
        return {"success": False, "error": str(e)}
