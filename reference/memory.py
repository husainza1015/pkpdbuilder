"""Memory management for long-lived drug program projects."""
import os
import json
from datetime import datetime, date
from pathlib import Path
from .registry import register_tool


def _project_root():
    """Find project root (directory containing CLAUDE.md or pmx.yaml)."""
    cwd = Path.cwd()
    for p in [cwd] + list(cwd.parents):
        if (p / "CLAUDE.md").exists() or (p / "pmx.yaml").exists():
            return p
    return cwd


def _memory_dir():
    root = _project_root()
    d = root / "memory"
    d.mkdir(exist_ok=True)
    return d


def _today_file():
    return _memory_dir() / f"{date.today().isoformat()}.md"


@register_tool(
    name="memory_read",
    description="""Read project memory. Loads MEMORY.md (long-term) and recent daily files.
Call at the start of every session to restore context about the drug program,
past modeling decisions, and ongoing work.""",
    parameters={
        "properties": {
            "days": {
                "type": "integer",
                "description": "Number of recent daily files to read (default 2)",
                "default": 2
            }
        },
        "required": []
    }
)
def memory_read(days: int = 2) -> dict:
    root = _project_root()
    result = {"success": True, "long_term": None, "daily": [], "decisions_count": 0, "models_count": 0}
    
    # Read MEMORY.md
    mem_file = root / "MEMORY.md"
    if mem_file.exists():
        result["long_term"] = mem_file.read_text()
    else:
        result["long_term"] = "(No MEMORY.md yet — create one with memory_write)"
    
    # Read recent daily files
    mem_dir = _memory_dir()
    daily_files = sorted(mem_dir.glob("????-??-??.md"), reverse=True)[:days]
    for f in daily_files:
        result["daily"].append({
            "date": f.stem,
            "content": f.read_text()
        })
    
    # Count decisions and model history
    decisions_file = mem_dir / "decisions.jsonl"
    if decisions_file.exists():
        result["decisions_count"] = sum(1 for _ in open(decisions_file))
    
    models_file = mem_dir / "model_history.jsonl"
    if models_file.exists():
        result["models_count"] = sum(1 for _ in open(models_file))
    
    return result


@register_tool(
    name="memory_write",
    description="""Write to project memory. Use for:
- 'daily': Append to today's session notes
- 'long_term': Update MEMORY.md with curated insights
- 'decision': Log a modeling decision with rationale
- 'model': Log a model fitting result to history

Always log decisions and model results — regulators need the audit trail.""",
    parameters={
        "properties": {
            "target": {
                "type": "string",
                "enum": ["daily", "long_term", "decision", "model"],
                "description": "Where to write"
            },
            "content": {
                "type": "string",
                "description": "Text content (for daily/long_term)"
            },
            "entry": {
                "type": "object",
                "description": "JSON entry (for decision/model)"
            },
            "mode": {
                "type": "string",
                "enum": ["append", "replace"],
                "description": "For long_term: append or replace entire file",
                "default": "append"
            }
        },
        "required": ["target"]
    }
)
def memory_write(target: str, content: str = None, entry: dict = None, mode: str = "append") -> dict:
    root = _project_root()
    mem_dir = _memory_dir()
    
    if target == "daily":
        f = _today_file()
        if not f.exists():
            f.write_text(f"# {date.today().isoformat()} — Session Notes\n\n")
        with open(f, "a") as fh:
            fh.write(f"\n{content}\n")
        return {"success": True, "file": str(f), "message": f"Appended to {f.name}"}
    
    elif target == "long_term":
        f = root / "MEMORY.md"
        if mode == "replace":
            f.write_text(content or "")
        else:
            existing = f.read_text() if f.exists() else "# Project Memory\n"
            f.write_text(existing + f"\n{content}\n")
        return {"success": True, "file": str(f), "message": "MEMORY.md updated"}
    
    elif target == "decision":
        f = mem_dir / "decisions.jsonl"
        entry = entry or {}
        entry.setdefault("ts", datetime.now().isoformat())
        with open(f, "a") as fh:
            fh.write(json.dumps(entry) + "\n")
        return {"success": True, "file": str(f), "message": f"Decision logged: {entry.get('decision', '?')}"}
    
    elif target == "model":
        f = mem_dir / "model_history.jsonl"
        entry = entry or {}
        entry.setdefault("ts", date.today().isoformat())
        with open(f, "a") as fh:
            fh.write(json.dumps(entry) + "\n")
        return {"success": True, "file": str(f), "message": f"Model logged: {entry.get('model', '?')} — {entry.get('action', '?')}"}
    
    return {"success": False, "error": f"Unknown target: {target}"}


@register_tool(
    name="memory_search",
    description="""Search project memory for past decisions, model history, or session notes.
Useful for: 'Why did we choose 2-CMT?', 'What was the OFV for M3?', 
'When did we add weight as a covariate?'""",
    parameters={
        "properties": {
            "query": {
                "type": "string",
                "description": "Search term or question"
            },
            "scope": {
                "type": "string",
                "enum": ["all", "decisions", "models", "daily", "long_term"],
                "description": "Where to search (default: all)",
                "default": "all"
            }
        },
        "required": ["query"]
    }
)
def memory_search(query: str, scope: str = "all") -> dict:
    root = _project_root()
    mem_dir = _memory_dir()
    query_lower = query.lower()
    results = []
    
    if scope in ("all", "long_term"):
        f = root / "MEMORY.md"
        if f.exists():
            text = f.read_text()
            lines = text.split("\n")
            for i, line in enumerate(lines):
                if query_lower in line.lower():
                    context = "\n".join(lines[max(0, i-1):i+2])
                    results.append({"source": "MEMORY.md", "line": i+1, "match": context})
    
    if scope in ("all", "decisions"):
        f = mem_dir / "decisions.jsonl"
        if f.exists():
            for line in open(f):
                if query_lower in line.lower():
                    entry = json.loads(line)
                    results.append({"source": "decisions.jsonl", "entry": entry})
    
    if scope in ("all", "models"):
        f = mem_dir / "model_history.jsonl"
        if f.exists():
            for line in open(f):
                if query_lower in line.lower():
                    entry = json.loads(line)
                    results.append({"source": "model_history.jsonl", "entry": entry})
    
    if scope in ("all", "daily"):
        for f in sorted(mem_dir.glob("????-??-??.md"), reverse=True)[:30]:
            text = f.read_text()
            if query_lower in text.lower():
                lines = text.split("\n")
                for i, line in enumerate(lines):
                    if query_lower in line.lower():
                        context = "\n".join(lines[max(0, i-1):i+2])
                        results.append({"source": f.name, "line": i+1, "match": context})
    
    return {
        "success": True,
        "query": query,
        "n_results": len(results),
        "results": results[:20],  # Cap at 20 to save context
        "message": f"Found {len(results)} matches for '{query}'"
    }


@register_tool(
    name="init_project",
    description="""Initialize a new drug program analysis project. Creates the standard directory 
structure, CLAUDE.md, MEMORY.md, and memory files. Use at the start of a new drug program.""",
    parameters={
        "properties": {
            "drug_name": {
                "type": "string",
                "description": "Drug name (e.g., 'tirzepatide', 'AX-4127')"
            },
            "indication": {
                "type": "string",
                "description": "Therapeutic indication"
            },
            "analysis_type": {
                "type": "string",
                "enum": ["popPK", "popPKPD", "PKPD", "exposureResponse"],
                "description": "Type of analysis",
                "default": "popPK"
            },
            "project_dir": {
                "type": "string",
                "description": "Directory to create project in (default: current dir)"
            }
        },
        "required": ["drug_name"]
    }
)
def init_project(drug_name: str, indication: str = "", analysis_type: str = "popPK", project_dir: str = None) -> dict:
    root = Path(project_dir) if project_dir else Path.cwd()
    root.mkdir(parents=True, exist_ok=True)
    
    # Create directory structure
    dirs = [
        "data/raw", "data/derived", "data/specs",
        "models/base", "models/covariate", "models/final",
        "output/diagnostics", "output/simulations", "output/tables", "output/exports",
        "reports/slides", "reports/analysis_report", "reports/regulatory",
        "apps/shiny",
        "memory"
    ]
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)
    
    # Create MEMORY.md
    mem_content = f"""# {drug_name} — Project Memory

## Project Info
- **Drug:** {drug_name}
- **Indication:** {indication or 'TBD'}
- **Analysis Type:** {analysis_type}
- **Started:** {date.today().isoformat()}

## Key Decisions
(Updated as analysis progresses)

## Model Development Summary
(Updated after model selection)

## Regulatory Notes
(Feedback, questions, commitments)
"""
    (root / "MEMORY.md").write_text(mem_content)
    
    # Create today's daily file
    daily = root / "memory" / f"{date.today().isoformat()}.md"
    daily.write_text(f"# {date.today().isoformat()} — Project Initialized\n\n- Drug: {drug_name}\n- Indication: {indication or 'TBD'}\n- Analysis: {analysis_type}\n")
    
    # Create pmx.yaml config
    config = f"""# PMX CLI Configuration
drug_name: "{drug_name}"
indication: "{indication or ''}"
analysis_type: "{analysis_type}"
output_dir: "./output"
r_path: "Rscript"
"""
    (root / "pmx.yaml").write_text(config)
    
    # Copy CLAUDE.md if not exists
    claude_src = Path(__file__).parent.parent.parent / "CLAUDE.md"
    claude_dst = root / "CLAUDE.md"
    if claude_src.exists() and not claude_dst.exists():
        import shutil
        shutil.copy2(claude_src, claude_dst)
    
    n_dirs = sum(1 for d in dirs if (root / d).exists())
    
    return {
        "success": True,
        "project_dir": str(root),
        "drug_name": drug_name,
        "directories_created": n_dirs,
        "files_created": ["MEMORY.md", "pmx.yaml", f"memory/{date.today().isoformat()}.md", "CLAUDE.md"],
        "message": f"Project initialized for {drug_name}. {n_dirs} directories + 4 files created."
    }
