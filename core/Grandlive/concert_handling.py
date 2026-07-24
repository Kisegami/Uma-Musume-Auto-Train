"""Grand Live concert workflows."""

import time

from utils.core.log import log_info, log_warning
from utils.inputs.input import tap, tap_on_image
from utils.integrations.umat_api import get_status
from utils.vision.recognizer import locate_on_screen


CONCERT_BUTTON = "assets/grandlive/concert_btn.png"
GRAND_CONCERT_BUTTON = "assets/grandlive/grand_concert_btn.png"
CONCERT_START_BUTTON = "assets/grandlive/concert_start.png"
ON_STAGE_BUTTON = "assets/grandlive/on_stage.png"
SKIP_BUTTON = "assets/buttons/skip_btn.png"
NEXT_BUTTON = "assets/buttons/next_btn.png"


def _double_tap(x, y):
    tap(x, y)
    time.sleep(0.1)
    tap(x, y)


def _wait_and_double_tap(template_path, timeout=30.0, confidence=0.8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        location = locate_on_screen(template_path, confidence=confidence)
        if location:
            _double_tap(*location)
            return True
        time.sleep(0.1)
    log_warning(f"Concert UI timed out waiting for {template_path}")
    return False


def _wait_and_tap(
    template_path,
    timeout=30.0,
    confidence=0.8,
    pre_tap_delay=0.0,
):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        location = locate_on_screen(template_path, confidence=confidence)
        if location:
            if pre_tap_delay:
                time.sleep(pre_tap_delay)
            tap(*location)
            return True
        time.sleep(0.1)
    log_warning(f"Concert UI timed out waiting for {template_path}")
    return False


def _start_concert_until_skip(timeout=45.0):
    """Spam the concert Start button until the Skip button becomes visible."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        skip = locate_on_screen(SKIP_BUTTON, confidence=0.8)
        if skip:
            return skip

        start = locate_on_screen(CONCERT_START_BUTTON, confidence=0.8)
        if start:
            tap(*start)
        time.sleep(0.1)

    log_warning("Concert UI timed out waiting for the Skip button")
    return None


def _run_standard_concert_ui():
    if not tap_on_image(CONCERT_BUTTON, confidence=0.8, min_search=3):
        log_warning("Standard Concert button disappeared before it could be tapped")
        return False

    log_info("Starting standard Grand Live concert")
    skip = _start_concert_until_skip()
    if skip is None:
        return False

    log_info("Skipping standard Grand Live concert")
    _double_tap(*skip)
    if not _wait_and_double_tap(NEXT_BUTTON):
        return False

    log_info("Standard Grand Live concert UI completed")
    return True


def _run_grand_concert_ui():
    if not tap_on_image(GRAND_CONCERT_BUTTON, confidence=0.8, min_search=3):
        log_warning("Grand Concert button disappeared before it could be tapped")
        return False

    log_info("Starting Grand Concert")
    time.sleep(0.5)
    if not _wait_and_tap(CONCERT_START_BUTTON, pre_tap_delay=0.1):
        return False
    if not _wait_and_double_tap(ON_STAGE_BUTTON):
        return False
    if not _wait_and_double_tap(NEXT_BUTTON):
        return False

    log_info("Grand Concert UI completed")
    return True


def standard_concert_index(year):
    """Map an API year string on a standard concert day to concerts 1-4."""
    normalized = str(year or "").lower()
    if "junior" in normalized and "dec" in normalized:
        return 1
    if "classic" in normalized and "jun" in normalized:
        return 2
    if "classic" in normalized and "dec" in normalized:
        return 3
    if "senior" in normalized and "jun" in normalized:
        return 4
    return None


def _try_concert_day_lessons(concert_index):
    from core.Grandlive.lesson_handling import handle_concert_day_lessons

    return handle_concert_day_lessons(concert_index)


def do_concert():
    """Handle lessons and then execute a standard concert."""
    status = get_status() or {}
    year = status.get("year")
    concert_index = standard_concert_index(year)
    if concert_index is None:
        log_warning(
            f"Concert detected but API year could not identify it: "
            f"{year or 'Unknown'}; using Unknown concert "
            "with the default minimum of 3"
        )
        if _try_concert_day_lessons(None):
            return True
    elif _try_concert_day_lessons(concert_index):
        return True

    return _run_standard_concert_ui()


def do_grand_concert():
    """Handle lessons and then execute the Grand Concert."""
    if _try_concert_day_lessons(5):
        return True

    return _run_grand_concert_ui()
