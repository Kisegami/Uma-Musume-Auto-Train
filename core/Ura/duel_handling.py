"""Special duel-event handling for Ura mode."""

import os
import re

import cv2
import numpy as np

from utils.capture.screenshot import take_screenshot
from utils.core.config_loader import load_main_config
from utils.core.log import log_debug, log_info, log_warning
from utils.ocr.ocr_utils import extract_text
from utils.vision.recognizer import best_match_template


HAPPY_MEEKS_CHALLENGE_EVENT = "Happy Meek's Challenge!"
DEFAULT_DUEL_CHOICES = ["speed", "stamina", "power", "guts", "wits", "energy"]
DUEL_CHOICE_NAME_TO_STAT = {
    "contest of speed": "speed",
    "contest of stamina": "stamina",
    "contest of power": "power",
    "contest of guts": "guts",
    "contest of wits": "wits",
    "contest of energy": "energy",
    "let's see who has more energy": "energy",
}
DUEL_PREDICTION_BEST = 1
DUEL_PREDICTION_WORST = 4
DUEL_PREDICTION_THRESHOLD = 0.80
DUEL_PREDICTION_REGION = (936, 874, 1023, 1405)
DUEL_PREDICTION_TEMPLATES = {
    1: "assets/ura/duel_1.png",
    2: "assets/ura/duel_2.png",
    3: "assets/ura/duel_3.png",
    4: "assets/ura/duel_4.png",
}
DUEL_TRAINING_ICON_TEMPLATE = "assets/ura/duel_icon.png"
DUEL_TRAINING_ICON_REGION = (816, 268, 126, 972)
DUEL_TRAINING_ICON_THRESHOLD = 0.80


def get_duel_choice_sort_key(choice_info, duel_priority):
    """Sort duel choices by prediction first, configured priority second.

    Prediction rank is primary, where 1 is the best prediction and 4 is the
    worst. The configured duel priority only breaks ties between whitelisted
    choices with the same prediction rank.
    """
    stat = choice_info.get("stat")
    prediction = choice_info.get("prediction", DUEL_PREDICTION_WORST)

    try:
        priority_index = duel_priority.index(stat)
    except ValueError:
        priority_index = len(duel_priority)

    return prediction, priority_index


def _get_project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def _normalize_duel_choices(duel_choices):
    if not isinstance(duel_choices, list):
        duel_choices = DEFAULT_DUEL_CHOICES

    normalized = []
    for choice in duel_choices:
        if choice in DEFAULT_DUEL_CHOICES and choice not in normalized:
            normalized.append(choice)
    return normalized or DEFAULT_DUEL_CHOICES[:]


def _load_duel_priority():
    config = load_main_config(os.path.join(_get_project_root(), "config.json"))
    training = config.get("training", {})
    return _normalize_duel_choices(training.get("duel_choices", DEFAULT_DUEL_CHOICES))


def find_happy_meeks_duel_training(screenshot, confidence=DUEL_TRAINING_ICON_THRESHOLD):
    """Find the Happy Meek's Duel icon on the current training hover screen."""
    match = best_match_template(
        screenshot,
        DUEL_TRAINING_ICON_TEMPLATE,
        confidence=confidence,
        region=DUEL_TRAINING_ICON_REGION,
    )
    if match:
        log_debug(
            "Happy Meek's Duel training icon found: "
            f"confidence={match['confidence']:.3f}, bbox={match['bbox']}"
        )
    else:
        log_debug("Happy Meek's Duel training icon not found")
    return match


def check_happy_meeks_duel_training(screenshot, confidence=DUEL_TRAINING_ICON_THRESHOLD):
    """Return True when the hovered training has a Happy Meek's Duel icon."""
    return find_happy_meeks_duel_training(screenshot, confidence=confidence) is not None


def _normalize_choice_name(choice_name):
    text = (choice_name or "").strip().lower()
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00b4": "'",
        "`": "'",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"[^a-z0-9']+", " ", text)
    return " ".join(text.split()).strip()


def _stat_from_choice_name(choice_name):
    normalized = _normalize_choice_name(choice_name)
    if not normalized:
        return None

    if normalized in DUEL_CHOICE_NAME_TO_STAT:
        return DUEL_CHOICE_NAME_TO_STAT[normalized]

    # OCR can occasionally damage punctuation or the final exclamation mark.
    for known_choice, stat in DUEL_CHOICE_NAME_TO_STAT.items():
        if known_choice in normalized or normalized in known_choice:
            return stat
    return None


def _ocr_choice_name(screenshot, row_bbox):
    _, top, _, bottom = row_bbox
    text_bbox = (120, top + 34, 560, min(bottom, top + 92))
    crop = screenshot.crop(text_bbox)
    try:
        text = extract_text(crop, config="--oem 3 --psm 7 -c preserve_interword_spaces=1")
    except Exception as e:
        log_warning(f"Duel choice OCR failed: {e}")
        return "", text_bbox
    return " ".join(text.strip().split()), text_bbox


def _screen_to_gray(screenshot):
    rgb = np.array(screenshot.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)


def _load_prediction_template(template_path):
    template = cv2.imread(os.path.join(_get_project_root(), template_path), cv2.IMREAD_GRAYSCALE)
    if template is None:
        log_warning(f"Duel prediction template not found: {template_path}")
    return template


def _match_prediction_for_row(screen_gray, row_bbox):
    pred_left, pred_top, pred_right, pred_bottom = DUEL_PREDICTION_REGION
    _, row_top, _, row_bottom = row_bbox
    search_top = max(pred_top, row_top)
    search_bottom = min(pred_bottom, row_bottom)
    if search_bottom <= search_top:
        search_top = max(pred_top, row_top - 20)
        search_bottom = min(pred_bottom, row_bottom + 20)

    roi = screen_gray[search_top:search_bottom, pred_left:pred_right]
    best_match = None
    for prediction, template_path in DUEL_PREDICTION_TEMPLATES.items():
        template = _load_prediction_template(template_path)
        if template is None:
            continue

        template_h, template_w = template.shape[:2]
        if roi.shape[0] < template_h or roi.shape[1] < template_w:
            continue

        result = cv2.matchTemplate(roi, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        x = pred_left + max_loc[0]
        y = search_top + max_loc[1]
        match = {
            "prediction": prediction,
            "confidence": float(max_val),
            "bbox": (x, y, x + template_w, y + template_h),
        }
        if best_match is None or match["confidence"] > best_match["confidence"]:
            best_match = match

    if best_match and best_match["confidence"] >= DUEL_PREDICTION_THRESHOLD:
        return best_match
    return best_match


def _row_from_choice_location(choice_location, screenshot_height):
    x, y, w, h = choice_location
    top = max(0, y - 42)
    bottom = min(screenshot_height, y + 106)
    return (36, top, 1044, bottom)


def _scan_duel_choices(choice_locations):
    screenshot = take_screenshot()
    screen_gray = _screen_to_gray(screenshot)
    ordered_locations = sorted(choice_locations, key=lambda loc: (loc[1], loc[0]))
    scanned_choices = []

    for index, choice_location in enumerate(ordered_locations, start=1):
        row_bbox = _row_from_choice_location(choice_location, screenshot.height)
        choice_name, text_bbox = _ocr_choice_name(screenshot, row_bbox)
        stat = _stat_from_choice_name(choice_name)
        prediction_match = _match_prediction_for_row(screen_gray, row_bbox)
        prediction = (
            prediction_match["prediction"]
            if prediction_match and prediction_match["confidence"] >= DUEL_PREDICTION_THRESHOLD
            else DUEL_PREDICTION_WORST
        )

        scanned_choices.append({
            "choice_number": index,
            "choice_name": choice_name,
            "stat": stat,
            "prediction": prediction,
            "prediction_match": prediction_match,
            "choice_location": choice_location,
            "row_bbox": row_bbox,
            "text_bbox": text_bbox,
        })

    return scanned_choices


def handle_happy_meeks_challenge(choice_locations=None):
    """Handle Happy Meek's Challenge! in Ura mode.

    This is the first routing point for the duel event. Detailed duel decision
    logic should choose the highest prediction rank first (1 is best), then use
    configured duel priority only as a tiebreaker.

    Returns:
        tuple: (choice_number, success, choice_locations)
    """
    if not choice_locations:
        log_warning("Happy Meek's Challenge! routed to duel handler, but no choices were visible")
        return 1, False, []

    log_info("Happy Meek's Challenge! routed to Ura duel handler")

    duel_priority = _load_duel_priority()
    scanned_choices = _scan_duel_choices(choice_locations)
    whitelisted_choices = [
        choice for choice in scanned_choices
        if choice.get("stat") in duel_priority
    ]

    for choice in scanned_choices:
        prediction_match = choice.get("prediction_match")
        confidence_text = ""
        if prediction_match:
            confidence_text = f" confidence={prediction_match['confidence']:.3f}"
        log_info(
            f"Duel choice {choice['choice_number']}: "
            f"name='{choice['choice_name']}', stat={choice['stat']}, "
            f"prediction={choice['prediction']}{confidence_text}"
        )

    if not whitelisted_choices:
        log_warning("No whitelisted duel choices were detected; defaulting to first visible choice")
        return 1, True, choice_locations

    selected = min(
        whitelisted_choices,
        key=lambda choice: get_duel_choice_sort_key(choice, duel_priority),
    )
    log_info(
        f"Duel selected choice {selected['choice_number']}: "
        f"{selected['choice_name']} "
        f"(prediction={selected['prediction']}, priority={duel_priority})"
    )
    return selected["choice_number"], True, choice_locations
