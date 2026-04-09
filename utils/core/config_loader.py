import json
import os
from typing import Any, Dict, Optional


def _read_raw_config(path: str = "config.json") -> Dict[str, Any]:
    """Load raw JSON data from config file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_main_config(path: str = "config.json") -> Dict[str, Any]:
    """
    Load configuration while supporting a nested parent container.

    Some tools write the config inside a parent key (e.g. {"config": {...}}).
    This helper always returns the inner config dict if present, otherwise the
    raw dictionary. Returns empty dict on failure.
    """
    data = _read_raw_config(path)
    if isinstance(data, dict):
        nested = data.get("config")
        if isinstance(nested, dict):
            return nested
    return data if isinstance(data, dict) else {}


def load_config_section(section: str, default: Optional[Any] = None, path: str = "config.json") -> Any:
    """
    Convenience accessor for a named section using load_main_config.

    Args:
        section: top-level section name, e.g. "training" or "adb_config".
        default: value to return when section is missing.
        path: optional path override.
    """
    cfg = load_main_config(path)
    return cfg.get(section, default)

