"""Special duel-event handling for Ura mode."""

from utils.core.log import log_info, log_warning


HAPPY_MEEKS_CHALLENGE_EVENT = "Happy Meek's Challenge!"


def handle_happy_meeks_challenge(choice_locations=None):
    """Handle Happy Meek's Challenge! in Ura mode.

    This is the first routing point for the duel event. The detailed duel
    decision logic can live here without touching the shared event handler.

    Returns:
        tuple: (choice_number, success, choice_locations)
    """
    if not choice_locations:
        log_warning("Happy Meek's Challenge! routed to duel handler, but no choices were visible")
        return 1, False, []

    log_info("Happy Meek's Challenge! routed to Ura duel handler")
    return 1, True, choice_locations

