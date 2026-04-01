import json
import os
import threading
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple


_LOCK = threading.Lock()


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _safe_mode(mode: str) -> str:
    return (mode or "unknown").lower()


def _dump_dir() -> str:
    path = os.path.join(_project_root(), "debug")
    os.makedirs(path, exist_ok=True)
    return path


def _session_path() -> str:
    return os.path.join(_dump_dir(), "template_match_regions.json")


def _load_or_init(path: str, mode: str) -> Dict:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass

    return {
        "mode": _safe_mode(mode),
        "created_at": _timestamp(),
        "updated_at": _timestamp(),
        "file_path": path,
        "templates": {},
    }


def _bbox_key(match: Tuple[int, int, int, int]) -> str:
    x, y, w, h = match
    return f"{int(x)},{int(y)},{int(w)},{int(h)}"


def _normalize_region(region: Optional[Tuple[int, int, int, int]]):
    if region is None:
        return None
    return [int(region[0]), int(region[1]), int(region[2]), int(region[3])]


def _append_unique_region(entry: Dict, match: Tuple[int, int, int, int], seen_at: str) -> None:
    x, y, w, h = [int(v) for v in match]
    key = _bbox_key((x, y, w, h))

    for item in entry["unique_regions"]:
        if item["bbox_key"] == key:
            item["hits"] += 1
            item["last_seen"] = seen_at
            return

    entry["unique_regions"].append({
        "bbox_key": key,
        "bbox": [x, y, w, h],
        "center": [x + w // 2, y + h // 2],
        "hits": 1,
        "first_seen": seen_at,
        "last_seen": seen_at,
    })


def record_template_matches(
    mode: str,
    context: str,
    template_specs: Iterable[Tuple[str, float, Optional[Tuple[int, int, int, int]]]],
    batch_results: Dict[str, List[Tuple[int, int, int, int]]],
) -> Optional[str]:
    """
    Persist found template-match regions for later inspection.

    Writes incrementally so data survives unexpected bot termination.
    Returns the JSON path when data is recorded, otherwise None.
    """
    found_any = False
    for template_path, _, _ in template_specs:
        if batch_results.get(template_path):
            found_any = True
            break
    if not found_any:
        return None

    path = _session_path()
    seen_at = _timestamp()

    with _LOCK:
        data = _load_or_init(path, mode)
        templates = data.setdefault("templates", {})

        for template_path, confidence, region in template_specs:
            matches = batch_results.get(template_path, [])
            if not matches:
                continue

            entry = templates.setdefault(template_path, {
                "template_path": template_path,
                "contexts": [],
                "confidence_thresholds": [],
                "search_regions": [],
                "total_hits": 0,
                "unique_regions": [],
            })

            if context not in entry["contexts"]:
                entry["contexts"].append(context)

            if confidence not in entry["confidence_thresholds"]:
                entry["confidence_thresholds"].append(confidence)

            normalized_region = _normalize_region(region)
            if normalized_region not in entry["search_regions"]:
                entry["search_regions"].append(normalized_region)

            entry["total_hits"] += len(matches)
            for match in matches:
                _append_unique_region(entry, match, seen_at)

        data["updated_at"] = seen_at

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    return path
