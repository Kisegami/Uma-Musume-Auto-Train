# Phone screen constants (1080x1920 portrait)
# These are estimated regions for phone screen - you'll need to adjust them manually
# All regions are in PIL format: (left, top, right, bottom)

# Support card icon region (right side of screen)
from utils.core.log import log_info, log_warning, log_error, log_debug, log_success
SUPPORT_CARD_ICON_REGION=(828, 240, 1080, 1194)

# Mood region (top area)
MOOD_REGION=(819, 211, 969, 274)

# Turn region (top left) - more focused to capture just the turn number
TURN_REGION=(21, 149, 210, 239)

# Failure region (bottom area)
FAILURE_REGION=(45, 1357, 1044, 1465)

# Year region (top area)
YEAR_REGION=(249, 63, 561, 99)

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

# Merged OK button region covering both the old box and the newly provided box
OK_BUTTON_REGION = (309, 1163, 705, 690)

UNITY_TEMPLATE_REGIONS = {
    "assets/buttons/back_btn.png": (3, 1651, 261, 261),
    "assets/buttons/cancel_lobby.png": (295, 1285, 481, 185),
    "assets/buttons/close.png": (59, 1153, 472, 186),
    "assets/buttons/complete_career.png": (573, 1559, 384, 149),
    "assets/buttons/confirm.png": (296, 1277, 731, 429),
    "assets/buttons/infirmary_btn2.png": (97, 1592, 441, 213),
    "assets/buttons/inspiration_btn.png": (374, 1470, 298, 256),
    "assets/buttons/next2_btn.png": (351, 1755, 592, 147),
    "assets/buttons/next_btn.png": (290, 1567, 493, 315),
    "assets/buttons/ok_btn.png": OK_BUTTON_REGION,
    "assets/buttons/race_btn.png": (289, 1282, 743, 437),
    "assets/buttons/race_day_btn.png": (599, 1506, 195, 137),
    "assets/buttons/race_ura.png": (595, 1497, 221, 188),
    "assets/buttons/races_btn.png": (704, 1671, 246, 137),
    "assets/buttons/recreation_btn.png": (395, 1663, 292, 142),
    "assets/buttons/rest_btn.png": (19, 1372, 313, 236),
    "assets/buttons/rest_summer_btn.png": (22, 1375, 308, 211),
    "assets/buttons/skills_btn.png": (190, 1602, 248, 138),
    "assets/buttons/skip_btn.png": (890, 1715, 180, 172),
    "assets/buttons/training_btn.png": (348, 1461, 378, 139),
    "assets/buttons/try_again.png": (507, 1259, 537, 222),
    "assets/buttons/view_results.png": (199, 1672, 353, 200),
    "assets/icons/clock.png": (225, 1035, 210, 211),
    "assets/icons/dating.png": (570, 1548, 146, 152),
    "assets/icons/end.png": (640, 950, 438, 140),
    "assets/icons/event_choice_1.png": (0, 867, 158, 555),
    "assets/icons/front.png": (832, 957, 245, 130),
    "assets/icons/late.png": (624, 955, 358, 136),
    "assets/icons/pace.png": (647, 957, 415, 133),
    "assets/races/fan.png": (380, 1117, 154, 380),
    "assets/ui/pal_date.png": (213, 624, 398, 177),
    "assets/ui/tazuna_hint.png": (903, 248, 155, 150),
    "assets/unity/begin_showdown.png": (548, 1270, 459, 212),
    "assets/unity/goal.png": (0, 50, 285, 185),
    "assets/unity/next_unity.png": (335, 1654, 634, 241),
    "assets/unity/see_all_race_btn.png": (578, 1649, 390, 275),
    "assets/unity/select_opponent.png": (314, 1520, 466, 236),
    "assets/unity/unity_cup.png": (422, 121, 230, 154),
    "assets/unity/unity_race.png": (422, 1499, 230, 150),
    "assets/unity/zenith_race_btn.png": (365, 1327, 342, 273),
}


def get_template_region(template_path):
    return UNITY_TEMPLATE_REGIONS.get(template_path.replace("\\", "/"))

MOOD_LIST = ["AWFUL", "BAD", "NORMAL", "GOOD", "GREAT", "UNKNOWN"]

# Note: All button clicking is done through template matching using button images
# The system finds UI elements dynamically by searching for button images
# No hardcoded positions are needed - this ensures compatibility across different screen sizes 

# Per-type failure rate regions (for direct number OCR)
FAILURE_REGION_SPD = (114, 1386, 204, 1425)
FAILURE_REGION_STA = (306, 1386, 393, 1425)
FAILURE_REGION_PWR = (495, 1386, 588, 1425)
FAILURE_REGION_GUTS = (687, 1386, 777, 1425)
FAILURE_REGION_WIT = (879, 1386, 966, 1425)

