"""Dating selection for Grand Live."""

import os
import time

from utils.capture.screenshot import take_screenshot
from utils.core.config_loader import load_main_config
from utils.core.log import log_debug, log_error, log_info, log_warning
from utils.inputs.input import tap
from utils.vision.recognizer import locate_on_screen, match_template
from utils.vision.template_matching import wait_for_image


def check_dating_available(screenshot=None, confidence=0.8):
    """Return whether the lobby currently shows an available dating action."""
    try:
        screenshot = screenshot or take_screenshot()
        matches = match_template(
            screenshot, os.path.join("assets", "icons", "dating.png"), confidence
        )
        found = bool(matches)
        log_debug(f"Dating icon found: {found}")
        return found
    except Exception as exc:
        log_debug(f"check_dating_available failed: {exc}")
        return False


def should_use_dating_for_rest(screenshot=None):
    """Return whether configured and currently available dating should replace rest."""
    dating_config = load_main_config().get("dating", {})
    if not dating_config.get("use_dating_instead_of_rest", False):
        log_debug("Dating replacement for rest is disabled in config")
        return False

    if check_dating_available(screenshot):
        log_debug("Dating is available and configured to replace rest")
        return True

    log_debug("Dating is not available - using normal rest")
    return False


def do_dating():
    """Open recreation and select the available pal date."""
    log_info("Starting dating workflow...")
    try:
        if not wait_for_image("assets/ui/tazuna_hint.png", timeout=10, confidence=0.9):
            log_warning("Cannot start dating because the career lobby was not found")
            return False

        recreation_btn = locate_on_screen(
            "assets/buttons/recreation_btn.png", confidence=0.8
        )
        if not recreation_btn:
            log_warning("No recreation button found - cannot access dating")
            return False

        log_info("Clicking recreation button to access dating...")
        tap(recreation_btn[0], recreation_btn[1])

        pal_date_btn = wait_for_image(
            "assets/ui/pal_date.png", timeout=5, confidence=0.8
        )
        if pal_date_btn:
            tap(pal_date_btn[0], pal_date_btn[1])
            log_info("Selected pal date")
            return True

        log_info("No pal date is available; skipping dating")
        cancel_btn = locate_on_screen(
            "assets/buttons/cancel_recreation.png", confidence=0.8
        )
        if cancel_btn:
            tap(cancel_btn[0], cancel_btn[1])
            time.sleep(0.5)
        return False
    except Exception as exc:
        log_error(f"Dating workflow failed: {exc}")
        return False
