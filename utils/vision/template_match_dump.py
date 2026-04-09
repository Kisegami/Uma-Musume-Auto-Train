import json
import os
import threading
from typing import Dict, Iterable, List, Optional, Tuple

from utils.core.config_loader import load_main_config


_LOCK = threading.Lock()


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _safe_mode(mode: str) -> str:
    return (mode or "unknown").lower()


def _dump_dir() -> str:
    path = os.path.join(_project_root(), "debug")
    os.makedirs(path, exist_ok=True)
    return path


def _session_path(mode: str) -> str:
    return os.path.join(_dump_dir(), f"template_match_regions_{_safe_mode(mode)}.json")


def _load_or_init(path: str) -> Dict[str, List[List[int]]]:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    normalized = {}
                    for key, value in data.items():
                        if isinstance(key, str) and isinstance(value, list):
                            normalized[key] = value
                    return normalized
        except Exception:
            pass
    return {}


def _write_one_asset_per_line(path: str, data: Dict[str, List[List[int]]]) -> None:
    items = []
    for key, value in data.items():
        key_json = json.dumps(key, ensure_ascii=False)
        value_json = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        items.append(f"  {key_json}:{value_json}")

    content = "{\n" + ",\n".join(items) + "\n}"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def record_template_matches(
    mode: str,
    context: str,
    template_specs: Iterable[Tuple[str, float, Optional[Tuple[int, int, int, int]]]],
    batch_results: Dict[str, List[Tuple[int, int, int, int]]],
) -> Optional[str]:
    """
    Persist unique template-match bounding boxes.

    Output format:
    {
      "assets/buttons/ok_btn.png": [[x, y, w, h], ...],
      ...
    }
    """
    del context

    found_any = False
    for template_path, _, _ in template_specs:
        if batch_results.get(template_path):
            found_any = True
            break
    if not found_any:
        return None

    path = _session_path(mode)

    with _LOCK:
        data = _load_or_init(path)

        for template_path, _, _ in template_specs:
            matches = batch_results.get(template_path, [])
            if not matches:
                continue

            entry = data.setdefault(template_path, [])
            existing = {tuple(int(v) for v in bbox) for bbox in entry if isinstance(bbox, list) and len(bbox) == 4}

            for match in matches:
                bbox = [int(match[0]), int(match[1]), int(match[2]), int(match[3])]
                key = tuple(bbox)
                if key not in existing:
                    entry.append(bbox)
                    existing.add(key)

        _write_one_asset_per_line(path, data)

    return path


def is_template_dump_enabled() -> bool:
    config = load_main_config()
    return bool(config.get("dump_lobby_template_regions", False))


def current_dump_mode() -> str:
    config = load_main_config()
    return config.get("mode", "unknown")


def record_template_matches_for_mode(
    template_specs: Iterable[Tuple[str, float, Optional[Tuple[int, int, int, int]]]],
    batch_results: Dict[str, List[Tuple[int, int, int, int]]],
) -> Optional[str]:
    if not is_template_dump_enabled():
        return None
    return record_template_matches(current_dump_mode(), "global_template_match", template_specs, batch_results)


def record_single_template_match(
    template_path: str,
    matches: List[Tuple[int, int, int, int]],
    confidence: float = 0.8,
    region: Optional[Tuple[int, int, int, int]] = None,
) -> Optional[str]:
    if not is_template_dump_enabled() or not matches:
        return None
    return record_template_matches_for_mode([(template_path, confidence, region)], {template_path: matches})
