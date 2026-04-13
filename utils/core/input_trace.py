import os
import threading
from datetime import datetime

from utils.core.config_loader import load_main_config


_LOCK = threading.Lock()
_CACHED_ENABLED = None
_CACHED_MTIME = None


def _project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _config_path():
    return os.path.join(_project_root(), "config.json")


def _debug_dir():
    path = os.path.join(_project_root(), "debug")
    os.makedirs(path, exist_ok=True)
    return path


def get_input_trace_path():
    return os.path.join(_debug_dir(), "input_actions_live.log")


def _load_enabled_flag():
    global _CACHED_ENABLED, _CACHED_MTIME

    config_path = _config_path()
    try:
        current_mtime = os.path.getmtime(config_path)
    except OSError:
        current_mtime = None

    if _CACHED_ENABLED is not None and _CACHED_MTIME == current_mtime:
        return _CACHED_ENABLED

    try:
        config = load_main_config(config_path)
        _CACHED_ENABLED = bool(config.get("input_action_debug_log", False))
    except Exception:
        _CACHED_ENABLED = False

    _CACHED_MTIME = current_mtime
    return _CACHED_ENABLED


def is_input_trace_enabled():
    return _load_enabled_flag()


def reset_input_trace_log():
    path = get_input_trace_path()
    with _LOCK:
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
    return path


def write_input_trace(action, **fields):
    if not is_input_trace_enabled():
        return None

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    parts = [f"[{timestamp}]", action]
    for key, value in fields.items():
        parts.append(f"{key}={value}")
    line = " ".join(parts)

    path = get_input_trace_path()
    with _LOCK:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    return path
