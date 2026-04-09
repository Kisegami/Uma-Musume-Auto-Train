"""
UMAT API Client
================
HTTP client for the local uma_viewer API (http://localhost:8123).
Provides fast packet-backed game state data as an alternative to OCR/template matching.

All functions return None on failure (connection error, timeout, waiting state),
allowing callers to fall back to OCR-based detection seamlessly.
"""

import requests
from utils.core.log import log_debug, log_info, log_warning, log_error
from utils.core.config_loader import load_main_config

# ── Configuration ─────────────────────────────────────────────────────────────

_config = load_main_config()
_api_config = _config.get("api", {})

API_ENABLED = _api_config.get("enabled", False)
API_BASE_URL = _api_config.get("base_url", "http://localhost:8123").rstrip("/")
API_TIMEOUT = _api_config.get("timeout", 2)  # seconds


# ── Internal helpers ──────────────────────────────────────────────────────────

def _api_get(endpoint: str) -> dict | None:
    """
    Perform a GET request to the API.

    Returns the parsed JSON dict, or None if:
    - API is disabled in config
    - Connection fails / times out
    - Response contains {"status": "waiting"}
    """
    if not API_ENABLED:
        return None

    url = f"{API_BASE_URL}{endpoint}"
    try:
        resp = requests.get(url, timeout=API_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        # Check for waiting state
        if isinstance(data, dict) and data.get("status") == "waiting":
            log_debug(f"[API] {endpoint} → waiting (no packet data yet)")
            return None

        return data

    except requests.ConnectionError:
        log_debug(f"[API] Connection refused: {url}")
        return None
    except requests.Timeout:
        log_debug(f"[API] Timeout: {url}")
        return None
    except requests.RequestException as e:
        log_debug(f"[API] Request failed for {url}: {e}")
        return None
    except ValueError as e:
        log_debug(f"[API] Invalid JSON from {url}: {e}")
        return None


def reload_config():
    """Reload API config from disk (e.g. after config change at runtime)."""
    global API_ENABLED, API_BASE_URL, API_TIMEOUT, _config, _api_config
    _config = load_main_config()
    _api_config = _config.get("api", {})
    API_ENABLED = _api_config.get("enabled", False)
    API_BASE_URL = _api_config.get("base_url", "http://localhost:8123").rstrip("/")
    API_TIMEOUT = _api_config.get("timeout", 2)


# ── Public API ────────────────────────────────────────────────────────────────

def is_api_enabled() -> bool:
    """Check if API mode is enabled in config."""
    return API_ENABLED


def is_api_available() -> bool:
    """
    Quick health check: call /status and verify it returns real data.
    Returns True if API is enabled *and* responding with non-waiting data.
    """
    if not API_ENABLED:
        return False
    data = _api_get("/status")
    return data is not None


def get_status() -> dict | None:
    """
    Fetch full game status from /status endpoint.

    Returns dict with keys:
        year, scenario, character, stats{spd,sta,pwr,guts,wit},
        energy{current,max}, mood{name,value}, current_skill_points
    Or None if unavailable.
    """
    return _api_get("/status")


def get_training() -> dict | None:
    """
    Fetch training data from /training endpoint.

    Returns dict with key 'trainings' containing list of:
        {name, failure, hint_found, support_cards[{name,type,bond_level}],
         spirit{spirit_count, spirit_training_extra_count, spirit_burst_count}}
    Or None if unavailable.
    """
    return _api_get("/training")


def get_skills() -> dict | None:
    """
    Fetch available skills from /skills endpoint.

    Returns dict with keys:
        current_skill_points, skills[{name, price}]
    Or None if unavailable.
    """
    return _api_get("/skills")


def get_events() -> dict | None:
    """
    Fetch active events from /events endpoint.

    Returns dict with key 'events' containing list of:
        {name}
    Or None if unavailable.
    """
    return _api_get("/events")
