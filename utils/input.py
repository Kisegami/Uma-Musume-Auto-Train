import subprocess
import time
from utils.device import run_adb
from utils.recognizer import locate_on_screen
from utils.config_loader import load_config_section
from utils.log import log_info, log_warning, log_error, log_debug, log_success


def load_config():
    """Load ADB configuration from config.json"""
    try:
        return load_config_section('adb_config', {})
    except Exception as e:
        log_error(f"Error loading config: {e}")
        return {}

def tap(x, y):
    """Tap at coordinates (x, y) - optimized: no input delay"""
    return run_adb(['shell', 'input', 'tap', str(x), str(y)], add_input_delay=False)

def swipe(start_x, start_y, end_x, end_y, duration_ms=20):
    """Swipe from (start_x, start_y) to (end_x, end_y) with duration in milliseconds - optimized: no input delay, faster default duration"""
    return run_adb(['shell', 'input', 'swipe', str(start_x), str(start_y), str(end_x), str(end_y), str(duration_ms)], add_input_delay=False)

def perform_swipe(start_x, start_y, end_x, end_y, duration_ms=1050):
    """Perform smooth swipe gesture with optional longer duration."""
    swipe_command = ['shell', 'input', 'swipe', str(start_x), str(start_y), str(end_x), str(end_y), str(duration_ms)]
    result = run_adb(swipe_command)
    if result is not None:
        log_debug(f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y})")
        return True
    log_debug("Failed to perform swipe")
    return False

def swipe_and_tap(
    swipe_start_x, swipe_start_y, 
    swipe_end_x, swipe_end_y, 
    swipe_duration_ms,
    tap_x, tap_y
):
    """
    Perform swipe and tap as a single ADB shell command to eliminate delay.
    Both commands are sent in one shell call, executed sequentially on device.
    
    This is the preferred method for scrolling operations where a stabilizing
    tap is needed immediately after the swipe.
    
    Args:
        swipe_start_x, swipe_start_y: Starting coordinates for swipe
        swipe_end_x, swipe_end_y: Ending coordinates for swipe
        swipe_duration_ms: Swipe duration in milliseconds
        tap_x, tap_y: Coordinates for stabilizing tap after swipe
    
    Returns:
        bool: True if command executed successfully, False otherwise
    """
    combined_command = (
        f"input swipe {swipe_start_x} {swipe_start_y} {swipe_end_x} {swipe_end_y} {swipe_duration_ms}; "
        f"input tap {tap_x} {tap_y}"
    )
    result = run_adb(['shell', combined_command])
    if result is not None:
        log_debug(f"Swipe+tap: ({swipe_start_x},{swipe_start_y})->({swipe_end_x},{swipe_end_y}), tap({tap_x},{tap_y})")
        return True
    log_debug("Failed to perform swipe+tap")
    return False

def long_press(x, y, duration_ms=1000):
    """Long press at coordinates (x, y) for duration_ms milliseconds - optimized: no input delay"""
    return swipe(x, y, x, y, duration_ms)

def triple_click(x, y, interval=0.1):
    """Perform triple click at coordinates (x, y)"""
    for i in range(3):
        tap(x, y)
        if i < 2:  # Don't wait after the last click
            time.sleep(interval)

def tap_on_image(img, confidence=0.8, min_search=1, text="", region=None):
    """Find image on screen and tap on it with retry logic"""
    for attempt in range(int(min_search)):
        btn = locate_on_screen(img, confidence=confidence, region=region)
        if btn:
            if text:
                log_info(text)
            tap(btn[0], btn[1])
            return True
        if attempt < int(min_search) - 1:  # Don't sleep on last attempt
            time.sleep(0.05)
    return False

def wait_and_tap(image_path: str, timeout: float = 10.0, check_interval: float = 0.2, confidence: float = 0.8) -> bool:
    """
    Poll locate_on_screen until image appears (up to timeout), then tap center.
    
    Args:
        image_path: Path to template image to wait for
        timeout: Maximum time to wait in seconds
        check_interval: Time between checks in seconds
        confidence: Minimum confidence threshold for template matching
    
    Returns:
        True if image was found and tapped, False otherwise
    """
    start = time.time()
    while time.time() - start < timeout:
        res = locate_on_screen(image_path, confidence=confidence)
        if res:
            cx, cy = res
            tap(cx, cy)
            return True
        time.sleep(check_interval)
    log_warning(f"wait_and_tap: {image_path} not found within timeout.")
    return False 