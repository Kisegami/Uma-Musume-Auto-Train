# Phone screen constants (1080x1920 portrait)
# These are estimated regions for phone screen - you'll need to adjust them manually
# All regions are in PIL format: (left, top, right, bottom)

# Support card icon region (right side of screen)
from utils.log import log_info, log_warning, log_error, log_debug, log_success
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

URA_TEMPLATE_REGIONS = {
    "assets/buttons/back_btn.png": (9, 1743, 237, 196),
    "assets/buttons/cancel_lobby.png": (58, 1285, 481, 185),
    "assets/buttons/claw.png": (219, 1259, 642, 582),
    "assets/buttons/close.png": (59, 1153, 472, 186),
    "assets/buttons/complete_career.png": (573, 1559, 384, 149),
    "assets/buttons/confirm.png": (533, 1277, 494, 183),
    "assets/buttons/infirmary_btn2.png": (97, 1592, 441, 213),
    "assets/buttons/inspiration_btn.png": (375, 1471, 297, 255),
    "assets/buttons/next2_btn.png": (351, 1755, 592, 147),
    "assets/buttons/next_btn.png": (290, 1567, 493, 312),
    "assets/buttons/ok_btn.png": (632, 1150, 283, 189),
    "assets/buttons/race_btn.png": (289, 1282, 743, 437),
    "assets/buttons/race_day_btn.png": (599, 1506, 195, 137),
    "assets/buttons/race_ura.png": (595, 1497, 221, 188),
    "assets/buttons/races_btn.png": (704, 1671, 246, 137),
    "assets/buttons/recreation_btn.png": (395, 1663, 292, 142),
    "assets/buttons/rest_btn.png": (19, 1372, 313, 236),
    "assets/buttons/rest_summer_btn.png": (22, 1375, 308, 211),
    "assets/buttons/skills_btn.png": (190, 1602, 248, 138),
    "assets/buttons/skip_btn.png": (890, 1715, 180, 172),
    "assets/buttons/strategy_change.png": (702, 1038, 299, 147),
    "assets/buttons/training_btn.png": (348, 1461, 378, 139),
    "assets/buttons/try_again.png": (507, 1259, 537, 222),
    "assets/buttons/view_results.png": (199, 1672, 353, 205),
    "assets/icons/clock.png": (225, 1035, 210, 211),
    "assets/icons/end.png": (640, 950, 446, 140),
    "assets/icons/event_choice_1.png": (0, 867, 186, 555),
    "assets/icons/front.png": (660, 957, 417, 130),
    "assets/icons/late.png": (624, 955, 358, 136),
    "assets/icons/maiden_lobby.png": (29, 1112, 231, 133),
    "assets/icons/pace.png": (647, 957, 415, 133),
    "assets/races/2_star_race.png": (804, 1089, 145, 206),
    "assets/races/fan.png": (380, 1117, 154, 408),
    "assets/ui/tazuna_hint.png": (903, 248, 155, 150),
}


def get_template_region(template_path):
    return URA_TEMPLATE_REGIONS.get(template_path.replace("\\", "/"))

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

