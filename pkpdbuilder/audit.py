"""LLM API audit logging — tracks every API call for compliance and cost monitoring."""
import json
import time
from datetime import datetime
from pathlib import Path

AUDIT_DIR = Path.home() / ".pkpdbuilder" / "audit"
AUDIT_FILE = AUDIT_DIR / "api_calls.jsonl"

# Approximate cost per 1M tokens (USD) — updated Feb 2026
TOKEN_COSTS = {
    # Anthropic
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-opus-4-5": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.0},
    # OpenAI
    "gpt-5.2": {"input": 2.50, "output": 10.0},
    "gpt-5.1": {"input": 2.50, "output": 10.0},
    "gpt-5": {"input": 2.50, "output": 10.0},
    "gpt-4o": {"input": 2.50, "output": 10.0},
    "o3": {"input": 10.0, "output": 40.0},
    "o4-mini": {"input": 1.10, "output": 4.40},
    # Google
    "gemini-2.5-pro": {"input": 1.25, "output": 5.0},
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    # DeepSeek
    "deepseek-v3.2": {"input": 0.27, "output": 1.10},
    "deepseek-r1": {"input": 0.55, "output": 2.19},
    # Local
    "ollama": {"input": 0.0, "output": 0.0},
}


def _ensure_dir():
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def log_api_call(
    provider: str,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    tools_called: list = None,
    duration_ms: int = 0,
    dataset_in_context: bool = False,
    error: str = None,
):
    """Log a single LLM API call."""
    _ensure_dir()
    entry = {
        "ts": datetime.now().isoformat(),
        "provider": provider,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "tools_called": tools_called or [],
        "duration_ms": duration_ms,
        "dataset_in_context": dataset_in_context,
    }
    if error:
        entry["error"] = error

    # Estimate cost
    cost_info = _find_cost(model, provider)
    if cost_info:
        cost = (prompt_tokens * cost_info["input"] + completion_tokens * cost_info["output"]) / 1_000_000
        entry["estimated_cost_usd"] = round(cost, 6)

    with open(AUDIT_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _find_cost(model: str, provider: str) -> dict:
    """Find token cost for a model, fuzzy matching."""
    if provider == "ollama":
        return {"input": 0.0, "output": 0.0}
    # Exact match
    if model in TOKEN_COSTS:
        return TOKEN_COSTS[model]
    # Partial match (strip date suffixes)
    for key, cost in TOKEN_COSTS.items():
        if key in model or model.startswith(key):
            return cost
    return None


def get_recent_calls(n: int = 20) -> list:
    """Get the last N API calls."""
    if not AUDIT_FILE.exists():
        return []
    entries = []
    with open(AUDIT_FILE) as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except:
                continue
    return entries[-n:]


def audit_summary() -> dict:
    """Aggregate audit stats: total tokens, calls, cost, by provider."""
    if not AUDIT_FILE.exists():
        return {"total_calls": 0, "total_tokens": 0, "estimated_cost_usd": 0.0, "by_provider": {}}

    calls = []
    with open(AUDIT_FILE) as f:
        for line in f:
            try:
                calls.append(json.loads(line))
            except:
                continue

    total_tokens = sum(c.get("total_tokens", 0) for c in calls)
    total_cost = sum(c.get("estimated_cost_usd", 0.0) for c in calls)
    total_prompt = sum(c.get("prompt_tokens", 0) for c in calls)
    total_completion = sum(c.get("completion_tokens", 0) for c in calls)

    by_provider = {}
    for c in calls:
        p = c.get("provider", "unknown")
        if p not in by_provider:
            by_provider[p] = {"calls": 0, "tokens": 0, "cost": 0.0}
        by_provider[p]["calls"] += 1
        by_provider[p]["tokens"] += c.get("total_tokens", 0)
        by_provider[p]["cost"] += c.get("estimated_cost_usd", 0.0)

    dataset_calls = sum(1 for c in calls if c.get("dataset_in_context"))

    return {
        "total_calls": len(calls),
        "total_tokens": total_tokens,
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "estimated_cost_usd": round(total_cost, 4),
        "calls_with_dataset": dataset_calls,
        "by_provider": by_provider,
    }


class APICallTimer:
    """Context manager to time API calls and extract token usage."""

    def __init__(self, provider: str, model: str, dataset_in_context: bool = False):
        self.provider = provider
        self.model = model
        self.dataset_in_context = dataset_in_context
        self.start_time = None
        self.tools_called = []

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass  # Logging done explicitly via .log()

    def log(self, prompt_tokens: int = 0, completion_tokens: int = 0,
            tools_called: list = None, error: str = None):
        duration_ms = int((time.time() - self.start_time) * 1000) if self.start_time else 0
        log_api_call(
            provider=self.provider,
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            tools_called=tools_called or self.tools_called,
            duration_ms=duration_ms,
            dataset_in_context=self.dataset_in_context,
            error=error,
        )
