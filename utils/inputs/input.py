"""
Unified input module supporting multiple input methods.

Supports:
- ADB: Standard adb shell input commands (default, universal compatibility)
- MaaTouch: High-performance socket-based touch injection

The input method is configured via config.json "input_method" setting.
"""

import time
from utils.platform.device import run_adb
from utils.vision.recognizer import locate_on_screen
from utils.core.config_loader import load_config_section, load_main_config
from utils.core.log import log_info, log_warning, log_error, log_debug


# ============================================================================
# Input Method Configuration
# ============================================================================

_cached_input_method = None


def get_input_method() -> str:
    """Get the configured input method from config.json"""
    global _cached_input_method
    if _cached_input_method is None:
        try:
            config = load_main_config()
            _cached_input_method = config.get('input_method', 'adb')
        except:
            _cached_input_method = 'adb'
    return _cached_input_method


def set_input_method(method: str):
    """Set the input method (for runtime switching without restart)"""
    global _cached_input_method
    _cached_input_method = method


def reload_input_method():
    """Reload input method from config (call after config change)"""
    global _cached_input_method
    _cached_input_method = None
    return get_input_method()


# ============================================================================
# ADB Input Methods (Original Implementation)
# ============================================================================

def _adb_tap(x, y):
    """Tap using ADB shell input"""
    return run_adb(['shell', 'input', 'tap', str(x), str(y)], add_input_delay=False)


def _adb_swipe(start_x, start_y, end_x, end_y, duration_ms=20):
    """Swipe using ADB shell input"""
    return run_adb(['shell', 'input', 'swipe', str(start_x), str(start_y), 
                    str(end_x), str(end_y), str(duration_ms)], add_input_delay=False)


def _adb_long_press(x, y, duration_ms=1000):
    """Long press using ADB (implemented as swipe to same point)"""
    return _adb_swipe(x, y, x, y, duration_ms)


# ============================================================================
# MaaTouch Input Methods
# ============================================================================

_maatouch_connection = None


def _get_maatouch():
    """Get or create MaaTouch connection"""
    global _maatouch_connection
    if _maatouch_connection is None:
        from utils.inputs.maatouch import MaaTouchConnection
        _maatouch_connection = MaaTouchConnection()
    return _maatouch_connection


def _maatouch_tap(x, y):
    """Tap using MaaTouch"""
    return _get_maatouch().tap(x, y)


def _maatouch_swipe(start_x, start_y, end_x, end_y, duration_ms=20):
    """Swipe using MaaTouch"""
    return _get_maatouch().swipe(start_x, start_y, end_x, end_y, duration_ms)


def _maatouch_long_press(x, y, duration_ms=1000):
    """Long press using MaaTouch"""
    return _get_maatouch().long_press(x, y, duration_ms)


# ============================================================================
# Public API - Dispatches to configured input method
# ============================================================================

def tap(x, y):
    """
    Tap at coordinates (x, y).
    Uses the configured input method (ADB or MaaTouch).
    """
    method = get_input_method()
    if method == 'maatouch':
        return _maatouch_tap(x, y)
    return _adb_tap(x, y)


def swipe(start_x, start_y, end_x, end_y, duration_ms=20):
    """
    Swipe from (start_x, start_y) to (end_x, end_y).
    Uses the configured input method (ADB or MaaTouch).
    """
    method = get_input_method()
    if method == 'maatouch':
        return _maatouch_swipe(start_x, start_y, end_x, end_y, duration_ms)
    return _adb_swipe(start_x, start_y, end_x, end_y, duration_ms)


def long_press(x, y, duration_ms=1000):
    """
    Long press at coordinates (x, y) for duration_ms milliseconds.
    Uses the configured input method (ADB or MaaTouch).
    """
    method = get_input_method()
    if method == 'maatouch':
        return _maatouch_long_press(x, y, duration_ms)
    return _adb_long_press(x, y, duration_ms)


def perform_swipe(start_x, start_y, end_x, end_y, duration_ms=1050):
    """Perform smooth swipe gesture with optional longer duration."""
    result = swipe(start_x, start_y, end_x, end_y, duration_ms)
    if result:
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
    Perform swipe and tap as a single operation.
    
    For ADB: Sends both commands in one shell call.
    For MaaTouch: Sends commands sequentially via socket.
    """
    method = get_input_method()
    
    if method == 'maatouch':
        # MaaTouch: perform sequentially (still fast due to socket connection)
        swipe(swipe_start_x, swipe_start_y, swipe_end_x, swipe_end_y, swipe_duration_ms)
        tap(tap_x, tap_y)
        # Small delay to ensure UI settles before potential screen capture
        time.sleep(0.1)
        log_debug(f"Swipe+tap: ({swipe_start_x},{swipe_start_y})->({swipe_end_x},{swipe_end_y}), tap({tap_x},{tap_y})")
        return True
    
    # ADB: combine into single shell command
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


# ============================================================================
# Cleanup
# ============================================================================

def cleanup_input():
    """Cleanup input method resources (call on shutdown)"""
    global _maatouch_connection
    if _maatouch_connection:
        _maatouch_connection.disconnect()
        _maatouch_connection = None