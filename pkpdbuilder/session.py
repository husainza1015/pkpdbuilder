"""Session save/resume for pmx CLI."""
import json
import os
from datetime import datetime
from pathlib import Path

SESSION_DIR = Path.home() / ".pmx" / "sessions"


def save_session(agent, name: str = None) -> str:
    """Save current agent state to disk."""
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    
    if not name:
        name = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    session_data = {
        "name": name,
        "created": datetime.now().isoformat(),
        "messages": agent.messages,
        "config": agent.config,
    }
    
    path = SESSION_DIR / f"{name}.json"
    with open(path, 'w') as f:
        json.dump(session_data, f, indent=2, default=str)
    
    return str(path)


def load_session(name: str) -> dict:
    """Load a saved session."""
    path = SESSION_DIR / f"{name}.json"
    if not path.exists():
        return None
    
    with open(path) as f:
        return json.load(f)


def list_sessions() -> list:
    """List available sessions."""
    if not SESSION_DIR.exists():
        return []
    
    sessions = []
    for f in sorted(SESSION_DIR.glob("*.json"), reverse=True):
        try:
            with open(f) as fh:
                data = json.load(fh)
            sessions.append({
                "name": f.stem,
                "created": data.get("created"),
                "n_messages": len(data.get("messages", [])),
            })
        except:
            pass
    
    return sessions
