import time
from utils.input import perform_swipe

# Support card list swipe coordinates
SUPPORT_LIST_X = 540
SUPPORT_LIST_START_Y = 1450
SUPPORT_LIST_END_Y = 550
SUPPORT_LIST_SWIPE_DURATION_MS = 800

def swipe_support_list_down(wait_before=0.5, wait_after=1.5):
    """
    Swipe down in the support card list.
    Swipes UP on the screen to scroll DOWN in the list.

    Args:
        wait_before: Seconds to wait before performing swipe (default: 0.5)
        wait_after: Seconds to wait after swipe for UI to settle (default: 1.5)

    Returns:
        bool: True if swipe was successful, False otherwise
    """
    time.sleep(wait_before)
    result = perform_swipe(
        SUPPORT_LIST_X, SUPPORT_LIST_START_Y,
        SUPPORT_LIST_X, SUPPORT_LIST_END_Y,
        SUPPORT_LIST_SWIPE_DURATION_MS
    )
    time.sleep(wait_after)
    return result
