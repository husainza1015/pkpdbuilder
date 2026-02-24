"""Configuration management for pkpdbuilder CLI."""
import os
import json
from pathlib import Path

PROVIDERS = {
    "anthropic": {
        "name": "Anthropic (Claude)",
        "models": [
            # Claude 4.6 (latest, Feb 2026)
            "claude-opus-4-6-20260220",
            "claude-sonnet-4-6-20260220",
            # Claude 4.5
            "claude-opus-4-5-20250514",
            "claude-sonnet-4-5-20250514",
            "claude-haiku-4-5-20250514",
        ],
        "default": "claude-sonnet-4-6-20260220",
        "env_key": "ANTHROPIC_API_KEY",
        "auth_methods": ["api_key", "oauth"],
        "docs": "https://console.anthropic.com/settings/keys",
    },
    "openai": {
        "name": "OpenAI (GPT)",
        "models": [
            # GPT-5.x series (latest)
            "gpt-5.2",
            "gpt-5.1",
            "gpt-5",
            "gpt-5-mini",
            "gpt-5-nano",
            # GPT-4.1 series
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
            # GPT-4o
            "gpt-4o",
            "gpt-4o-mini",
            # Reasoning models
            "o4-mini",
            "o3",
            "o3-pro",
            "o3-mini",
        ],
        "default": "gpt-5.2",
        "env_key": "OPENAI_API_KEY",
        "auth_methods": ["api_key"],
        "docs": "https://platform.openai.com/api-keys",
    },
    "google": {
        "name": "Google (Gemini)",
        "models": [
            # Gemini 3.x (latest)
            "gemini-3.1-pro",
            "gemini-3-pro",
            "gemini-3-flash",
            # Gemini 2.5
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            # Gemini 2.0
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
        ],
        "default": "gemini-2.5-pro",
        "env_key": "GOOGLE_API_KEY",
        "auth_methods": ["api_key"],
        "docs": "https://aistudio.google.com/apikey",
    },
    "deepseek": {
        "name": "DeepSeek",
        "models": [
            "deepseek-v3.2",
            "deepseek-r1",
        ],
        "default": "deepseek-v3.2",
        "env_key": "DEEPSEEK_API_KEY",
        "auth_methods": ["api_key"],
        "docs": "https://platform.deepseek.com/api_keys",
        "base_url": "https://api.deepseek.com/v1",
    },
    "xai": {
        "name": "xAI (Grok)",
        "models": [
            "grok-4.1-fast",
            "grok-4",
            "grok-3",
            "grok-3-mini",
        ],
        "default": "grok-4.1-fast",
        "env_key": "XAI_API_KEY",
        "auth_methods": ["api_key"],
        "docs": "https://console.x.ai",
        "base_url": "https://api.x.ai/v1",
    },
}

DEFAULT_CONFIG = {
    "provider": "anthropic",
    "model": "claude-sonnet-4-5-20250514",
    "max_tokens": 8192,
    "r_path": "Rscript",
    "output_dir": "./pkpdbuilder_output",
    "pkpdbuilder_api": "https://www.pkpdbuilder.com/api/v1",
    "autonomy": "full",  # full | supervised | ask
    "onboarded": False,
}

CONFIG_DIR = Path.home() / ".pkpdbuilder"
CONFIG_FILE = CONFIG_DIR / "config.json"
KEYS_FILE = CONFIG_DIR / "keys.json"  # Separate for security


def get_api_key(provider: str = None) -> str:
    """Get API key for provider from env, keys file, or config."""
    config = load_config()
    provider = provider or config.get("provider", "anthropic")
    provider_info = PROVIDERS.get(provider, {})
    
    # 1. Environment variable
    env_key = provider_info.get("env_key", "")
    if env_key and os.environ.get(env_key):
        return os.environ[env_key]
    
    # 2. Keys file (preferred storage)
    if KEYS_FILE.exists():
        keys = json.loads(KEYS_FILE.read_text())
        if provider in keys:
            return keys[provider]
    
    # 3. Legacy: config file
    if CONFIG_FILE.exists():
        cfg = json.loads(CONFIG_FILE.read_text())
        if "api_key" in cfg:
            return cfg["api_key"]
    
    return ""


def save_api_key(provider: str, key: str):
    """Save API key to keys file (600 permissions)."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    keys = {}
    if KEYS_FILE.exists():
        keys = json.loads(KEYS_FILE.read_text())
    keys[provider] = key
    KEYS_FILE.write_text(json.dumps(keys, indent=2))
    KEYS_FILE.chmod(0o600)


def load_config() -> dict:
    """Load config, merging defaults with user overrides."""
    config = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        user_cfg = json.loads(CONFIG_FILE.read_text())
        config.update(user_cfg)
    # Env overrides
    if os.environ.get("PKPDBUILDER_PROVIDER"):
        config["provider"] = os.environ["PKPDBUILDER_PROVIDER"]
    if os.environ.get("PKPDBUILDER_MODEL"):
        config["model"] = os.environ["PKPDBUILDER_MODEL"]
    if os.environ.get("PKPDBUILDER_OUTPUT_DIR"):
        config["output_dir"] = os.environ["PKPDBUILDER_OUTPUT_DIR"]
    return config


def save_config(config: dict):
    """Save config to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # Don't save API keys in config
    clean = {k: v for k, v in config.items() if k != "api_key"}
    CONFIG_FILE.write_text(json.dumps(clean, indent=2))


def ensure_output_dir(config: dict) -> Path:
    """Create and return output directory."""
    out = Path(config["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    return out
