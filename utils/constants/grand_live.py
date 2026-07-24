"""Grand Live template-search regions for a 1080x1920 screen.

Grand Live uses the URA regions as its baseline. Scenario-specific entries are
derived from ``debug/template_match_regions_grand_live.json`` with 10 pixels of
padding on every side. Existing URA regions are only expanded, never shrunk.
"""

from utils.constants.ura import URA_TEMPLATE_REGIONS


GRAND_LIVE_TEMPLATE_REGIONS = {
    **URA_TEMPLATE_REGIONS,

    # Existing URA regions expanded to include Grand Live matches.
    "assets/buttons/complete_career.png": (385, 1559, 572, 149),
    "assets/icons/event_choice_1.png": (0, 455, 186, 967),
    "assets/buttons/race_ura.png": (408, 1497, 408, 188),
    "assets/buttons/race_day_btn.png": (412, 1506, 382, 137),
    "assets/buttons/recreation_btn.png": (312, 1663, 375, 142),

    # Templates observed only in the Grand Live region dump.
    "assets/grandlive/concert_btn.png": (605, 1637, 341, 64),
    "assets/grandlive/grand_concert_btn.png": (645, 1640, 241, 83),
    "assets/grandlive/lessons_btn_2.png": (192, 1638, 237, 57),
    "assets/grandlive/learn_btn.png": (597, 1707, 385, 109),
    "assets/grandlive/concert_start.png": (574, 1281, 380, 153),
    "assets/grandlive/race_day.png": (19, 98, 206, 89),
    "assets/grandlive/lessons_btn.png": (437, 1646, 561, 118),
    "assets/grandlive/lessons_btn_complete.png": (9, 1456, 1071, 234),
    "assets/grandlive/skills_btn_complete.png": (9, 1456, 1071, 234),
    "assets/grandlive/on_stage.png": (421, 999, 213, 187),
    "assets/buttons/title_menu.png": (951, 1789, 104, 98),
    "assets/ui/home_theater.png": (184, 1601, 92, 69),
    "assets/buttons/ongoing_career.png": (834, 1500, 153, 123),
    "assets/buttons/resume_career.png": (673, 1319, 249, 97),
    "assets/buttons/skill_up.png": (936, 848, 76, 616),
    "assets/buttons/learn.png": (588, 1719, 375, 107),
    "assets/icons/dating.png": (469, 1588, 66, 72),
    "assets/buttons/cancel_recreation.png": (445, 1333, 189, 86),
    "assets/ui/trainee_date.png": (684, 842, 349, 97),
    "assets/ui/pal_date.png": (253, 664, 318, 97),
}


def get_template_region(template_path):
    return GRAND_LIVE_TEMPLATE_REGIONS.get(template_path.replace("\\", "/"))
