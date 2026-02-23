"""
Shared skill list swipe functions for both Unity and Ura modules.

Centralizes swipe coordinates, duration, and timing so they can be
configured in one place instead of being duplicated across files.

Coordinates and duration tuned via tests/test_swipe_realtime.py
"""
import time
from utils.input import perform_swipe
from utils.log import log_debug

# Skill list swipe coordinates (stable values)
SKILL_LIST_CENTER_X = 504
SKILL_LIST_START_Y = 1490
SKILL_LIST_END_Y = 960
SKILL_LIST_SWIPE_DURATION_MS = 850


def swipe_skill_list_down_slow(wait_before=0.5, wait_after=1.8):
    """
    Swipe down in skill list - used for careful navigation.
    Swipes UP on screen to scroll DOWN in the list.

    Args:
        wait_before: Seconds to wait before performing swipe (default: 0.5)
        wait_after: Seconds to wait after swipe for UI to settle (default: 1.5)

    Returns:
        bool: True if swipe was successful, False otherwise
    """
    time.sleep(wait_before)
    result = perform_swipe(
        SKILL_LIST_CENTER_X, SKILL_LIST_START_Y,
        SKILL_LIST_CENTER_X, SKILL_LIST_END_Y,
        SKILL_LIST_SWIPE_DURATION_MS
    )
    time.sleep(wait_after)  # Wait for scroll animation to complete
    return result
