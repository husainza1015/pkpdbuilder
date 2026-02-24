"""PMX Model Library — Monolix-equivalent models translated to nlmixr2.

All models are ready-to-use nlmixr2 model functions. Each returns an R code string
that can be passed directly to nlmixr2::nlmixr2() for fitting.

Usage:
    from pkpdbuilder.models import get_model, list_models, search_models
    
    # Get a specific model
    code = get_model("pk_1cmt_oral")
    
    # List all models
    models = list_models()
    
    # Search by keyword
    matches = search_models("transit")
"""
import importlib
import pkgutil
from pathlib import Path

_REGISTRY = {}


def register_model(name: str, category: str, description: str, 
                   route: str = "", elimination: str = "linear",
                   compartments: int = 1, pd_type: str = "",
                   monolix_equivalent: str = "", code: str = ""):
    """Register a model in the library."""
    _REGISTRY[name] = {
        "name": name,
        "category": category,
        "description": description,
        "route": route,
        "elimination": elimination,
        "compartments": compartments,
        "pd_type": pd_type,
        "monolix_equivalent": monolix_equivalent,
        "code": code,
    }


def get_model(name: str) -> dict:
    """Get a model by name. Returns dict with 'code' (R) and metadata."""
    _ensure_loaded()
    if name not in _REGISTRY:
        # Try fuzzy match
        matches = [k for k in _REGISTRY if name.lower() in k.lower()]
        if len(matches) == 1:
            return _REGISTRY[matches[0]]
        elif matches:
            raise KeyError(f"Model '{name}' not found. Did you mean: {', '.join(matches[:5])}")
        raise KeyError(f"Model '{name}' not found. Use list_models() to see available models.")
    return _REGISTRY[name]


def list_models(category: str = None) -> list:
    """List all models, optionally filtered by category."""
    _ensure_loaded()
    models = list(_REGISTRY.values())
    if category:
        models = [m for m in models if m["category"] == category]
    return models


def search_models(query: str) -> list:
    """Search models by keyword in name or description."""
    _ensure_loaded()
    q = query.lower()
    return [m for m in _REGISTRY.values() 
            if q in m["name"].lower() or q in m["description"].lower() 
            or q in m.get("monolix_equivalent", "").lower()]


def _ensure_loaded():
    """Load all model modules if not already loaded."""
    if _REGISTRY:
        return
    pkg_dir = Path(__file__).parent
    for subdir in ["pk", "pd", "pkpd", "tmdd", "advanced"]:
        sub_path = pkg_dir / subdir
        if sub_path.exists():
            for module_info in pkgutil.iter_modules([str(sub_path)]):
                importlib.import_module(f".{subdir}.{module_info.name}", package="pkpdbuilder.models")
