# Phone screen constants (1080x1920 portrait)
# These are estimated regions for phone screen - you'll need to adjust them manually
# All regions are in PIL format: (left, top, right, bottom)

# Support card icon region (right side of screen)
from utils.core.log import log_info, log_warning, log_error, log_debug, log_success
SUPPORT_CARD_ICON_REGION=(876, 253, 1080, 1171)

# Mood region (top area)
MOOD_REGION=(819, 211, 969, 274)

# Turn region (top left) - more focused to capture just the turn number
TURN_REGION=(21, 149, 210, 239)

# Failure region (bottom area)
FAILURE_REGION=(45, 1357, 1044, 1465)

# Year region (top area)
YEAR_REGION=(21, 66, 333, 96)

# Criteria region (top area)
CRITERIA_REGION=(363, 153, 867, 201)

# Skill points region (bottom right)
SKILL_PTS_REGION=(903, 1383, 1035, 1443) 

# Stat regions for character stats (bottom area)
SPD_REGION=(108, 1284, 204, 1326)
STA_REGION=(282, 1283, 378, 1322)
PWR_REGION=(444, 1284, 543, 1326)
GUTS_REGION=(621, 1281, 711, 1323)
WIT_REGION=(780, 1284, 876, 1323)

# Event detection region (middle area)
EVENT_REGION=(168, 347, 825, 434)

# Race selection regions
RACE_CARD_REGION=(0, 0, 610, 220)  # Dynamic region calculated as (x, y, 350, 110)

# Default screen region (phone resolution)
DEFAULT_SCREEN_REGION=(0, 0, 1080, 1920)
RESTART_COMPLETE_SPAM_TARGET = (543, 1787)

# Unified OK button region derived from template-match dump
OK_BUTTON_REGION = (632, 1150, 283, 189)

TRACKBLAZER_TEMPLATE_REGIONS = {
    "assets/buttons/back_btn.png": (0, 1650, 300, 270),
    "assets/buttons/cancel_lobby.png": (55, 1151, 484, 715),
    "assets/buttons/claw.png": (219, 1259, 642, 582),
    "assets/buttons/close.png": (57, 1152, 712, 710),
    "assets/buttons/complete_career.png": (573, 1559, 384, 149),
    "assets/buttons/confirm.png": (296, 1277, 731, 429),
    "assets/buttons/infirmary_btn2.png": (53, 1632, 301, 133),
    "assets/buttons/inspiration_btn.png": (375, 1471, 297, 255),
    "assets/buttons/learn.png": (548, 1679, 455, 187),
    "assets/buttons/next2_btn.png": (351, 1755, 592, 165),
    "assets/buttons/next_btn.png": (296, 1567, 722, 318),
    "assets/buttons/ok_btn.png": OK_BUTTON_REGION,
    "assets/buttons/race_btn.png": (329, 1322, 663, 357),
    "assets/buttons/race_day_btn.png": (412, 1546, 115, 57),
    "assets/buttons/race_ura.png": (595, 1497, 221, 188),
    "assets/buttons/races_btn.png": (789, 1671, 246, 137),
    "assets/buttons/recreation_btn.png": (312, 1703, 212, 62),
    "assets/buttons/rest_btn.png": (59, 1412, 233, 156),
    "assets/buttons/rest_summer_btn.png": (22, 1375, 308, 211),
    "assets/buttons/skill_up.png": (895, 201, 158, 1390),
    "assets/buttons/skills_btn.png": (54, 1465, 987, 243),
    "assets/buttons/skip_btn.png": (890, 1715, 180, 172),
    "assets/buttons/strategy_change.png": (702, 1038, 299, 147),
    "assets/buttons/training_btn.png": (388, 1501, 298, 59),
    "assets/buttons/try_again.png": (507, 1259, 537, 222),
    "assets/buttons/view_results.png": (199, 1672, 353, 207),
    "assets/icons/clock.png": (225, 1035, 210, 211),
    "assets/icons/end.png": (640, 950, 440, 140),
    "assets/icons/event_choice_1.png": (0, 738, 182, 686),
    "assets/icons/front.png": (832, 957, 246, 130),
    "assets/icons/late.png": (624, 955, 358, 136),
    "assets/icons/maiden_lobby.png": (29, 1112, 231, 133),
    "assets/icons/pace.png": (647, 957, 416, 133),
    "assets/races/2_star_race.png": (804, 1089, 145, 206),
    "assets/races/fan.png": (350, 1147, 150, 399),
    "assets/trackblazer/item_confirm_use.png": (580, 1691, 382, 176),
    "assets/trackblazer/item_pick.png": (824, 715, 193, 732),
    "assets/trackblazer/item_use_2.png": (533, 1695, 498, 159),
    "assets/trackblazer/items_inventory.png": (741, 1092, 175, 250),
    "assets/trackblazer/items_shop.png": (421, 1586, 587, 226),
    "assets/trackblazer/race_ts_climax.png": (362, 1504, 241, 162),
    "assets/ui/tazuna_hint.png": (902, 231, 156, 170),
}


def get_template_region(template_path):
    return TRACKBLAZER_TEMPLATE_REGIONS.get(template_path.replace("\\", "/"))

MOOD_LIST = ["AWFUL", "BAD", "NORMAL", "GOOD", "GREAT", "UNKNOWN"]

# Note: All button clicking is done through template matching using button images
# The system finds UI elements dynamically by searching for button images
# No hardcoded positions are needed - this ensures compatibility across different screen sizes 

# Per-type failure rate regions (for direct number OCR)
FAILURE_REGION_SPD = (109, 1404, 205, 1442)
FAILURE_REGION_STA = (308, 1404, 389, 1442)
FAILURE_REGION_PWR = (501, 1404, 579, 1442)
FAILURE_REGION_GUTS = (691, 1404, 769, 1442)
FAILURE_REGION_WIT = (881, 1404, 962, 1442)


