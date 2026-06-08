import json
import os
from datetime import datetime
from typing import Optional

from PIL import Image

from utils.capture.screenshot import take_screenshot
from utils.core.log import get_recent_log_lines, log_info, log_warning


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _debug_dir() -> str:
    path = os.path.join(_project_root(), "debug")
    os.makedirs(path, exist_ok=True)
    return path


def save_debug_screenshot(prefix: str, screenshot: Optional[Image.Image] = None) -> Optional[str]:
    """Save a timestamped screenshot to the project debug directory."""
    try:
        if screenshot is None:
            screenshot = take_screenshot()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{prefix}_{timestamp}.png"
        path = os.path.join(_debug_dir(), filename)
        screenshot.save(path)
        log_info(f"Saved debug screenshot: {path}")
        return path
    except Exception as e:
        log_warning(f"Failed to save debug screenshot for {prefix}: {e}")
        return None


def save_debug_bundle(prefix: str, reason: str, screenshot: Optional[Image.Image] = None, log_limit: int = 100):
    """Save a screenshot and recent timestamped logs for a diagnostic event."""
    try:
        if screenshot is None:
            screenshot = take_screenshot()

        timestamp = datetime.now().astimezone()
        filename_timestamp = timestamp.strftime("%Y%m%d_%H%M%S_%f")
        base_path = os.path.join(_debug_dir(), f"{prefix}_{filename_timestamp}")
        image_path = f"{base_path}.png"
        json_path = f"{base_path}.json"

        screenshot.save(image_path)
        payload = {
            "timestamp": timestamp.isoformat(timespec="milliseconds"),
            "reason": reason,
            "image": os.path.basename(image_path),
            "logs": get_recent_log_lines(log_limit),
        }
        with open(json_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

        log_info(f"Saved debug bundle: {image_path}, {json_path}")
        return {"image_path": image_path, "json_path": json_path}
    except Exception as e:
        log_warning(f"Failed to save debug bundle for {prefix}: {e}")
        return None
