import os
from datetime import datetime
from typing import Optional

from PIL import Image

from utils.capture.screenshot import take_screenshot
from utils.core.log import log_info, log_warning


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
