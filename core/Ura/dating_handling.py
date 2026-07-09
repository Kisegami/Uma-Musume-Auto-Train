"""
Dating handling module for URA.

Handles dating functionality when dating opportunities are available.
Dating can replace recreation/rest actions when available.
"""

import time

from utils.vision.recognizer import locate_on_screen, match_template
from utils.inputs.input import tap
from utils.capture.screenshot import take_screenshot
from utils.core.log import log_debug, log_info, log_warning, log_error
from utils.vision.template_matching import wait_for_image
from core.Ura.state import check_dating_available
from utils.core.config_loader import load_main_config


def do_dating():
    """
    Perform dating action.

    Flow:
    1. Wait for tazuna_hint to confirm we're in lobby.
    2. Tap recreation button.
    3. Check whether the normal recreation screen opened.
    4. Select trainee date or pal date depending on the screen.

    Returns:
        bool: True if dating was successfully initiated, False otherwise.
    """
    log_debug("Starting dating workflow...")
    log_info("Starting dating workflow...")

    try:
        log_debug("Waiting for tazuna_hint to confirm we're in lobby...")
        tazuna_hint = wait_for_image("assets/ui/tazuna_hint.png", timeout=10, confidence=0.9)
        if not tazuna_hint:
            log_warning("tazuna_hint not found after waiting - may not be in lobby")
            screenshot = take_screenshot()
            debug_filename = "debug_no_tazuna_hint_found.png"
            screenshot.save(debug_filename)
            log_error(f"Saved debug screenshot to: {debug_filename}")
            log_error("Stopping bot execution - tazuna_hint not found")
            raise RuntimeError(f"tazuna_hint not found. Debug image saved to {debug_filename}")

        log_debug("tazuna_hint found, confirmed in lobby")
        log_debug("Looking for recreation button...")
        recreation_btn = locate_on_screen("assets/buttons/recreation_btn.png", confidence=0.8)

        if recreation_btn:
            log_debug(f"Found recreation button at {recreation_btn}")
            log_info("Clicking recreation button to access dating...")
            tap(recreation_btn[0], recreation_btn[1])
            log_debug("Clicked recreation button")
        else:
            log_warning("No recreation button found - cannot access dating")
            screenshot = take_screenshot()
            debug_filename = "debug_no_recreation_button_found.png"
            screenshot.save(debug_filename)
            log_error(f"Saved debug screenshot to: {debug_filename}")
            log_error("Stopping bot execution - recreation button not found")
            raise RuntimeError(f"Recreation button not found. Debug image saved to {debug_filename}")

        log_debug("Waiting for recreation screen to load (checking for cancel button)...")
        cancel_matches = None
        max_wait_time = 5.0
        check_interval = 0.5
        elapsed_time = 0.0

        while elapsed_time < max_wait_time:
            screenshot = take_screenshot()
            cancel_matches = match_template(screenshot, "assets/buttons/cancel_recreation.png", confidence=0.8)
            if cancel_matches:
                log_debug(f"Cancel button found after {elapsed_time:.1f}s")
                break
            time.sleep(check_interval)
            elapsed_time += check_interval

        if cancel_matches:
            log_debug("Normal recreation screen detected, selecting trainee date...")
            log_info("Normal recreation screen detected, selecting trainee date...")

            trainee_date_btn = locate_on_screen("assets/ui/trainee_date.png", confidence=0.8)
            if trainee_date_btn:
                log_debug(f"Found trainee date button at {trainee_date_btn}")
                tap(trainee_date_btn[0], trainee_date_btn[1])
                log_info("Selected trainee date")
                return True

            log_warning("Trainee date button not found after detecting cancel button")
            return False

        log_debug("No recreation cancel button found, waiting for dating screen...")
        time.sleep(0.5)

        pal_date_btn = locate_on_screen("assets/ui/pal_date.png", confidence=0.8)
        if pal_date_btn:
            log_debug(f"Found pal date button at {pal_date_btn}")
            log_info("Selecting pal date...")
            tap(pal_date_btn[0], pal_date_btn[1])
            log_info("Selected pal date")
            return True

        log_warning("Pal date button not found - dating screen may not have loaded")
        return False

    except RuntimeError:
        raise
    except Exception as e:
        log_error(f"Dating workflow failed: {e}")
        return False


def should_use_dating_for_mood(screenshot=None):
    """
    Check if dating should be used instead of recreation for mood improvement.

    Dating is always preferred over normal recreation when available.
    """
    try:
        if check_dating_available(screenshot):
            log_debug("Dating is available - will use dating for mood (dating > recreation)")
            return True

        log_debug("Dating is not available - will use normal recreation")
        return False
    except Exception as e:
        log_debug(f"Error checking dating availability: {e}")
        return False


def should_use_dating_for_rest(screenshot=None):
    """
    Check if dating should be used instead of rest.

    This checks whether dating is enabled in config and currently available.
    """
    try:
        config = load_main_config()
        replace_rest = config.get("dating", {}).get("use_dating_instead_of_rest", False)
        if not replace_rest:
            log_debug("Dating replacement for rest is disabled in config")
            return False

        if check_dating_available(screenshot):
            log_debug("Dating is available and replace_rest is enabled - will use dating instead of rest")
            return True

        log_debug("Dating is not available - will use normal rest")
        return False
    except Exception as e:
        log_debug(f"Error checking dating for rest: {e}")
        return False
