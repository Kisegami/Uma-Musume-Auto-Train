import time
from collections import Counter

from core.Trackblazer.items import load_item_catalog
from core.Trackblazer.ocr import extract_text
from utils.capture.debug import save_debug_bundle
from utils.capture.screenshot import take_screenshot
from utils.core.log import log_debug, log_info, log_warning
from utils.inputs.input import tap, perform_swipe, wait_and_tap
from utils.vision.recognizer import best_match_template, match_template
from utils.vision.template_matching import deduplicated_matches, wait_for_image


ITEMS_INVENTORY_TEMPLATE = "assets/trackblazer/items_inventory.png"
ITEM_USE_TEMPLATE = "assets/buttons/skill_up.png"
ITEM_CONFIRM_USE_TEMPLATE = "assets/trackblazer/item_confirm_use.png"
ITEM_USE_2_TEMPLATE = "assets/trackblazer/item_use_2.png"
CLOSE_TEMPLATE = "assets/buttons/close.png"

ITEM_USE_THRESHOLD = 0.80
ITEM_USE_DEDUP_DISTANCE = 30
BUTTON_THRESHOLD = 0.80
OPEN_INVENTORY_BUTTON_THRESHOLD = 0.70
ITEM_NAME_MIN_MATCH_SCORE = 0.85

ITEM_NAME_OCR_OFFSET = (-742, -86, 525, 54)

USE_SWIPE_CENTER_X = 528
USE_SWIPE_START_Y = 1504
USE_SWIPE_END_Y = 313
USE_SWIPE_DURATION_MS = 850
USE_WAIT_BEFORE_SWIPE = 0.2
USE_WAIT_AFTER_SWIPE = 1.2
USE_MAX_SWIPES = 10

# Keep non-swipe waits short so item automation does not stall the turn loop.
WAIT_AFTER_OPEN_INVENTORY = 0.3
WAIT_AFTER_ITEM_TAP = 0.2
WAIT_AFTER_BUTTON_TAP = 0.3
WAIT_AFTER_CONFIRM_USE = 0.3
WAIT_AFTER_USE_2 = 0.9
WAIT_AFTER_CLOSE = 0.3
OPEN_INVENTORY_TIMEOUT = 3.0
OPEN_INVENTORY_CHECK_INTERVAL = 0.1
CLEAR_INVENTORY_SETTLE_AFTER_OPEN = 0.5
CLOSE_BUTTON_TIMEOUT = 10.0


def _locate_template_fullscreen(template_path, threshold):
    screenshot = take_screenshot()
    return best_match_template(screenshot, template_path, confidence=threshold)


def _find_all_matches(screenshot, template_path, threshold, dedup_distance):
    raw_boxes = match_template(screenshot, template_path, confidence=threshold)
    filtered_boxes = deduplicated_matches(raw_boxes, threshold=dedup_distance)

    matches = []
    for x, y, w, h in filtered_boxes:
        matches.append(
            {
                "confidence": float(threshold),
                "bbox": (x, y, w, h),
                "center": (x + w // 2, y + h // 2),
            }
        )
    matches.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
    return matches


def _normalize_text(text):
    text = str(text or "").strip().lower()
    cleaned = []
    for ch in text:
        cleaned.append(ch if ch.isalnum() else " ")
    return " ".join("".join(cleaned).split())


def _crop_item_name_region(screenshot, center_x, center_y):
    left = center_x + ITEM_NAME_OCR_OFFSET[0]
    top = center_y + ITEM_NAME_OCR_OFFSET[1]
    width = ITEM_NAME_OCR_OFFSET[2]
    height = ITEM_NAME_OCR_OFFSET[3]
    left = max(0, left)
    top = max(0, top)
    right = min(screenshot.width, left + width)
    bottom = min(screenshot.height, top + height)
    bbox = (left, top, right, bottom)
    return bbox, screenshot.crop(bbox)


def _resolve_best_catalog_item(ocr_text):
    from difflib import SequenceMatcher

    normalized_ocr = _normalize_text(ocr_text)
    if not normalized_ocr:
        return None

    best_score = -1.0
    best_item = None
    for item in load_item_catalog():
        normalized_name = _normalize_text(item.get("name", ""))
        if not normalized_name:
            continue
        if normalized_ocr == normalized_name:
            score = 1.0
        elif normalized_name in normalized_ocr:
            score = 0.97
        elif normalized_ocr in normalized_name:
            score = 0.94
        else:
            score = SequenceMatcher(None, normalized_ocr, normalized_name).ratio()

        if score > best_score:
            best_score = score
            best_item = item

    if best_item is None or best_score < ITEM_NAME_MIN_MATCH_SCORE:
        return None
    return {"score": best_score, "item": best_item}


def _scan_visible_use_items():
    screenshot = take_screenshot()
    use_matches = _find_all_matches(
        screenshot,
        ITEM_USE_TEMPLATE,
        ITEM_USE_THRESHOLD,
        ITEM_USE_DEDUP_DISTANCE,
    )

    visible_items = []
    for match in use_matches:
        center_x, center_y = match["center"]
        _, ocr_crop = _crop_item_name_region(screenshot, center_x, center_y)
        ocr_text = extract_text(ocr_crop, config="--psm 7")
        resolved = _resolve_best_catalog_item(ocr_text)
        visible_items.append(
            {
                "use_match": match,
                "ocr_text": ocr_text,
                "catalog_match": resolved,
            }
        )
    return visible_items


def _tap_match(match, wait_after=0.2):
    center_x, center_y = match["center"]
    tap(center_x, center_y)
    time.sleep(wait_after)


def _tap_button_if_visible(template_path, label, threshold=BUTTON_THRESHOLD, attempts=10, wait_between=0.1):
    del label
    timeout = max(float(wait_between), int(attempts) * float(wait_between))
    post_tap_wait = WAIT_AFTER_BUTTON_TAP
    if template_path == CLOSE_TEMPLATE:
        timeout = max(timeout, CLOSE_BUTTON_TIMEOUT)
    tapped = wait_and_tap(
        template_path,
        timeout=timeout,
        check_interval=wait_between,
        confidence=threshold,
    )
    if tapped:
        time.sleep(post_tap_wait)
    return tapped


def _open_inventory_if_needed():
    if _locate_template_fullscreen(ITEM_USE_TEMPLATE, ITEM_USE_THRESHOLD):
        log_debug("[Items] Item inventory already open")
        return True

    if not _tap_button_if_visible(
        ITEMS_INVENTORY_TEMPLATE,
        "items inventory button",
        threshold=OPEN_INVENTORY_BUTTON_THRESHOLD,
    ):
        log_warning("[Items] Failed to open item inventory from lobby")
        save_debug_bundle("trackblazer_item_inventory_open_failed", "Item inventory button was not found in the lobby")
        return False

    if wait_for_image(
        ITEM_USE_TEMPLATE,
        timeout=OPEN_INVENTORY_TIMEOUT,
        confidence=ITEM_USE_THRESHOLD,
        check_interval=OPEN_INVENTORY_CHECK_INTERVAL,
    ):
        time.sleep(CLEAR_INVENTORY_SETTLE_AFTER_OPEN)
        return True

    log_warning("[Items] Item inventory did not open after tapping lobby button")
    save_debug_bundle("trackblazer_item_inventory_open_failed", "Item inventory did not open after tapping the lobby button")
    return False


def _swipe_inventory_once():
    time.sleep(USE_WAIT_BEFORE_SWIPE)
    result = perform_swipe(
        USE_SWIPE_CENTER_X,
        USE_SWIPE_START_Y,
        USE_SWIPE_CENTER_X,
        USE_SWIPE_END_Y,
        USE_SWIPE_DURATION_MS,
    )
    time.sleep(USE_WAIT_AFTER_SWIPE)
    return result


def execute_item_usage_plan(usage_actions):
    if not usage_actions:
        return []

    if not _open_inventory_if_needed():
        return []

    target_counts = Counter()
    action_lookup = {}
    for action in usage_actions:
        normalized_name = _normalize_text(action.get("item_name", ""))
        quantity = max(1, int(action.get("quantity", 1)))
        target_counts[normalized_name] += quantity
        action_lookup[normalized_name] = action

    selected_counts = Counter()
    executed_actions = []

    for swipe_index in range(USE_MAX_SWIPES + 1):
        visible_items = _scan_visible_use_items()
        per_scan_usage = Counter()

        for entry in visible_items:
            resolved = entry["catalog_match"]
            if not resolved:
                continue

            item = resolved["item"]
            normalized_name = _normalize_text(item["name"])
            if normalized_name not in target_counts:
                continue

            needed_total = target_counts[normalized_name]
            remaining_total = needed_total - selected_counts[normalized_name]
            remaining_this_row = remaining_total - per_scan_usage[normalized_name]
            if remaining_this_row <= 0:
                continue

            for _ in range(remaining_this_row):
                _tap_match(entry["use_match"], wait_after=WAIT_AFTER_ITEM_TAP)
                selected_counts[normalized_name] += 1
                per_scan_usage[normalized_name] += 1

        if all(selected_counts[name] >= count for name, count in target_counts.items()):
            break

        if swipe_index < USE_MAX_SWIPES:
            log_debug(f"[Items] Use scan swipe {swipe_index + 1}/{USE_MAX_SWIPES}")
            if not _swipe_inventory_once():
                log_warning("[Items] Failed to swipe item inventory during use scan")
                break

    if sum(selected_counts.values()) <= 0:
        log_info("[Items] No usable targets were found in inventory scan")
        _tap_button_if_visible(CLOSE_TEMPLATE, "close button", attempts=10)
        return []

    if not _tap_button_if_visible(ITEM_CONFIRM_USE_TEMPLATE, "item confirm use button", attempts=15):
        log_warning("[Items] Confirm-use button not found after selecting items")
        _tap_button_if_visible(CLOSE_TEMPLATE, "close button", attempts=10)
        return []

    time.sleep(WAIT_AFTER_CONFIRM_USE)
    if not _tap_button_if_visible(ITEM_USE_2_TEMPLATE, "item use 2 button", attempts=15):
        log_warning("[Items] item_use_2 button not found after confirm-use")
        _tap_button_if_visible(CLOSE_TEMPLATE, "close button", attempts=10)
        return []

    time.sleep(WAIT_AFTER_USE_2)
    if not _tap_button_if_visible(CLOSE_TEMPLATE, "close button", attempts=15):
        log_warning("[Items] Close button not found after item use")
        return []

    time.sleep(WAIT_AFTER_CLOSE)

    for normalized_name, quantity in selected_counts.items():
        action = action_lookup.get(normalized_name)
        if not action:
            continue
        executed = dict(action)
        executed["quantity"] = quantity
        executed_actions.append(executed)

    return executed_actions
