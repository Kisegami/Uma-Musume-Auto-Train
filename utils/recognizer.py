import cv2
import numpy as np
from PIL import Image
import os
from utils.screenshot import take_screenshot
from utils.log import log_debug, log_info, log_warning, log_error
from utils.template_match_dump import record_single_template_match, record_template_matches_for_mode
from utils.config_loader import load_main_config
from utils.constants_unity import get_template_region as get_unity_template_region
from utils.constants_ura import get_template_region as get_ura_template_region

def _get_project_root():
    """Get the project root directory"""
    current = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current)
    
    if os.path.exists(os.path.join(project_root, 'main.py')) or os.path.exists(os.path.join(project_root, 'assets')):
        return project_root
    
    cwd = os.getcwd()
    if os.path.exists(os.path.join(cwd, 'main.py')) or os.path.exists(os.path.join(cwd, 'assets')):
        return cwd
    
    return project_root

def _resolve_asset_path(template_path):
    """Resolve asset path relative to project root"""
    if os.path.isabs(template_path):
        return template_path
    
    if os.path.exists(template_path):
        return os.path.abspath(template_path)
    
    project_root = _get_project_root()
    resolved_path = os.path.join(project_root, template_path)
    resolved_path = os.path.normpath(resolved_path)
    return resolved_path

# ── Template image cache & conversion helpers ─────────────────────────
_template_cache = {}

def _load_template(template_path):
    """Load and cache a template image from disk.

    Templates are loaded once and stored in memory for reuse,
    eliminating repeated cv2.imread disk I/O.

    Returns:
        cv2 BGR image or None if the template could not be loaded.
    """
    resolved = _resolve_asset_path(template_path)
    if resolved in _template_cache:
        return _template_cache[resolved]

    if not os.path.exists(resolved):
        log_error(f"Template not found: {template_path} (resolved to: {resolved})")
        _template_cache[resolved] = None
        return None

    img = cv2.imread(resolved, cv2.IMREAD_COLOR)
    if img is None:
        log_error(f"Failed to load template: {resolved}")
    _template_cache[resolved] = img
    return img

def _screenshot_to_cv(screenshot):
    """Convert a PIL screenshot to OpenCV BGR numpy array (single conversion)."""
    return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)


def _resolve_search_region(template_path, region):
    if region is not None:
        return region
    try:
        mode = load_main_config().get("mode")
        if mode == "unity":
            return get_unity_template_region(template_path)
        if mode == "ura":
            return get_ura_template_region(template_path)
    except Exception:
        pass
    return None
# ──────────────────────────────────────────────────────────────────────

def match_template(screenshot, template_path, confidence=0.8, region=None):
    """
    Match template image on screenshot using OpenCV
    
    Args:
        screenshot: PIL Image of the screen
        template_path: Path to template image
        confidence: Minimum confidence threshold
        region: Region to search in (x, y, width, height)
    
    Returns:
        List of (x, y, width, height) matches or empty list if not found
    """
    try:
        template = _load_template(template_path)
        if template is None:
            return []
        
        screenshot_cv = _screenshot_to_cv(screenshot)
        region = _resolve_search_region(template_path, region)
        
        if region:
            x, y, w, h = region
            screenshot_cv = screenshot_cv[y:y+h, x:x+w]
        
        h, w = template.shape[:2]
        result = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= confidence)
        matches = []
        
        for pt in zip(*locations[::-1]):
            if region:
                pt = (pt[0] + region[0], pt[1] + region[1])
            matches.append((pt[0], pt[1], w, h))

        if matches:
            record_single_template_match(template_path, matches, confidence, region)
            return matches
        return []
        
    except Exception as e:
        log_error(f"Error in template matching: {e}")
        return []

def max_match_confidence(screenshot, template_path, region=None):
    """
    Compute the maximum template match score for a template against a screenshot.

    Args:
        screenshot: PIL Image of the screen
        template_path: Path to template image
        region: Optional region to search (x, y, w, h)

    Returns:
        float: max normalized correlation score in [0,1], or 0.0 on error
    """
    try:
        template = _load_template(template_path)
        if template is None:
            return 0.0

        screenshot_cv = _screenshot_to_cv(screenshot)
        region = _resolve_search_region(template_path, region)

        if region:
            x, y, w, h = region
            screenshot_cv = screenshot_cv[y:y+h, x:x+w]

        result = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        return float(max_val)
    except Exception as e:
        log_error(f"Error computing max template confidence: {e}")
        return 0.0

def match_templates_batch(screenshot, template_specs):
    """Match multiple templates against a single screenshot efficiently.

    Converts the screenshot to OpenCV format ONCE and uses cached templates,
    eliminating redundant PIL-to-numpy-to-BGR conversions and disk I/O.

    Args:
        screenshot: PIL Image
        template_specs: list of tuples (template_path, confidence, region)
            - template_path: str - path to template image
            - confidence: float - minimum confidence threshold
            - region: tuple (x, y, w, h) or None - optional search region

    Returns:
        dict: {template_path: [(x, y, w, h), ...]} - matches per template.
              Empty list [] means no match for that template.
    """
    screenshot_cv = _screenshot_to_cv(screenshot)
    results = {}

    for template_path, confidence, region in template_specs:
        region = _resolve_search_region(template_path, region)
        template = _load_template(template_path)
        if template is None:
            results[template_path] = []
            continue

        search_img = screenshot_cv
        if region:
            rx, ry, rw, rh = region
            search_img = screenshot_cv[ry:ry+rh, rx:rx+rw]

        try:
            th, tw = template.shape[:2]
            result = cv2.matchTemplate(search_img, template, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= confidence)
            matches = []
            for pt in zip(*locations[::-1]):
                px, py = pt[0], pt[1]
                if region:
                    px += region[0]
                    py += region[1]
                matches.append((px, py, tw, th))
            results[template_path] = matches
        except Exception as e:
            log_error(f"Error in batch template matching for {template_path}: {e}")
            results[template_path] = []

    record_template_matches_for_mode(template_specs, results)
    return results

def locate_on_screen(template_path, confidence=0.8, region=None):
    """
    Locate template on screen and return center coordinates
    
    Args:
        template_path: Path to template image
        confidence: Minimum confidence threshold
        region: Region to search in (x, y, width, height)
    
    Returns:
        (x, y) center coordinates or None if not found
    """
    screenshot = take_screenshot()
    matches = match_template(screenshot, template_path, confidence, region)
    
    if matches:
        x, y, w, h = matches[0]
        return (x + w//2, y + h//2)
    
    return None

def locate_all_on_screen(template_path, confidence=0.8, region=None):
    """
    Locate all instances of template on screen
    
    Args:
        template_path: Path to template image
        confidence: Minimum confidence threshold
        region: Region to search in (x, y, width, height)
    
    Returns:
        List of (x, y, width, height) matches or empty list if not found
    """
    screenshot = take_screenshot()
    matches = match_template(screenshot, template_path, confidence, region)
    
    return matches if matches else []

def is_image_on_screen(template_path, confidence=0.8, region=None):
    """
    Check if template image is present on screen
    
    Args:
        template_path: Path to template image
        confidence: Minimum confidence threshold
        region: Region to search in (x, y, width, height)
    
    Returns:
        True if found, False otherwise
    """
    return locate_on_screen(template_path, confidence, region) is not None
