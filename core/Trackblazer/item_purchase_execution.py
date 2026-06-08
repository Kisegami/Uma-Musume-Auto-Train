import time
from collections import Counter, defaultdict, deque

from core.Trackblazer.items import load_item_settings, load_item_catalog
from core.Trackblazer.ocr import extract_text
from utils.capture.debug import save_debug_bundle
from utils.capture.screenshot import take_screenshot
from utils.core.log import log_debug, log_info, log_warning
from utils.inputs.input import tap, perform_swipe, wait_and_tap
from utils.vision.recognizer import best_match_template, match_template
from utils.vision.template_matching import deduplicated_matches, wait_for_image


ITEMS_SHOP_TEMPLATE = "assets/trackblazer/items_shop.png"
ITEM_PICK_TEMPLATE = "assets/trackblazer/item_pick.png"
CONFIRM_TEMPLATE = "assets/buttons/confirm.png"
CLOSE_TEMPLATE = "assets/buttons/close.png"
BACK_TEMPLATE = "assets/buttons/back_btn.png"

BUTTON_THRESHOLD = 0.80
ITEM_PICK_THRESHOLD = 0.80
ITEM_PICK_DEDUP_DISTANCE = 30
ITEM_NAME_OCR_OFFSET = (-680, -84, 579, 60)
ITEM_NAME_MIN_MATCH_SCORE = 0.85

SHOP_SWIPE_CENTER_X = 567
SHOP_SWIPE_START_Y = 1332
SHOP_SWIPE_END_Y = 887
SHOP_SWIPE_DURATION_MS = 870
SHOP_WAIT_BEFORE_SWIPE = 0.5
SHOP_WAIT_AFTER_SWIPE = 1.8

# Keep non-swipe waits short so item automation does not stall the turn loop.
WAIT_AFTER_OPEN_SHOP = 0.3
WAIT_AFTER_ITEM_TAP = 0.2
WAIT_AFTER_BUTTON_TAP = 0.3
WAIT_AFTER_CONFIRM = 0.3
WAIT_BEFORE_CLOSE_AFTER_CONFIRM = 0.5
WAIT_AFTER_CLOSE = 0.3
WAIT_AFTER_BACK = 0.3
OPEN_SHOP_TIMEOUT = 3.0
OPEN_SHOP_CHECK_INTERVAL = 0.1
SHOP_SETTLE_AFTER_OPEN = 0.5


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


def _scan_visible_shop_items():
    screenshot = take_screenshot()
    pick_matches = _find_all_matches(
        screenshot,
        ITEM_PICK_TEMPLATE,
        ITEM_PICK_THRESHOLD,
        ITEM_PICK_DEDUP_DISTANCE,
    )

    visible_items = []
    for match in pick_matches:
        center_x, center_y = match["center"]
        _, ocr_crop = _crop_item_name_region(screenshot, center_x, center_y)
        ocr_text = extract_text(ocr_crop, config="--psm 7")
        resolved = _resolve_best_catalog_item(ocr_text)
        visible_items.append(
            {
                "pick_match": match,
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
    tapped = wait_and_tap(
        template_path,
        timeout=timeout,
        check_interval=wait_between,
        confidence=threshold,
    )
    if tapped:
        time.sleep(WAIT_AFTER_BUTTON_TAP)
    return tapped


def _open_shop_if_needed():
    if _locate_template_fullscreen(ITEM_PICK_TEMPLATE, ITEM_PICK_THRESHOLD):
        log_debug("[Items] Shop already open")
        return True

    if not _tap_button_if_visible(ITEMS_SHOP_TEMPLATE, "items shop button"):
        log_warning("[Items] Failed to open item shop from lobby")
        save_debug_bundle("trackblazer_item_shop_open_failed", "Item shop button was not found in the lobby")
        return False

    if wait_for_image(
        ITEM_PICK_TEMPLATE,
        timeout=OPEN_SHOP_TIMEOUT,
        confidence=ITEM_PICK_THRESHOLD,
        check_interval=OPEN_SHOP_CHECK_INTERVAL,
    ):
        time.sleep(SHOP_SETTLE_AFTER_OPEN)
        return True

    log_warning("[Items] Item shop did not open after tapping lobby button")
    save_debug_bundle("trackblazer_item_shop_open_failed", "Item shop did not open after tapping the lobby button")
    return False


def _swipe_shop_once(settings):
    swipe_offset = int(settings.get("shop_swipe_time_offset", 0))
    duration_ms = max(100, SHOP_SWIPE_DURATION_MS + swipe_offset)
    time.sleep(SHOP_WAIT_BEFORE_SWIPE)
    result = perform_swipe(
        SHOP_SWIPE_CENTER_X,
        SHOP_SWIPE_START_Y,
        SHOP_SWIPE_CENTER_X,
        SHOP_SWIPE_END_Y,
        duration_ms,
    )
    time.sleep(SHOP_WAIT_AFTER_SWIPE)
    return result


def _close_shop_after_purchase(confirm_used):
    if confirm_used:
        time.sleep(WAIT_BEFORE_CLOSE_AFTER_CONFIRM)
        if _tap_button_if_visible(CLOSE_TEMPLATE, "close button", attempts=15):
            time.sleep(WAIT_AFTER_CLOSE)
        else:
            log_warning("[Items] Close button not found after confirm")

    if _tap_button_if_visible(BACK_TEMPLATE, "back button", attempts=10):
        time.sleep(WAIT_AFTER_BACK)
        return

    log_warning("[Items] Back button not found while exiting shop")


def execute_item_purchase_plan(purchase_actions, config):
    if not purchase_actions:
        return []

    settings = load_item_settings(config)
    max_swipes = int(settings.get("purchase_max_swipes", 10))

    if not _open_shop_if_needed():
        return []

    actions_by_name = defaultdict(deque)
    target_counts = Counter()
    for action in purchase_actions:
        normalized_name = _normalize_text(action.get("item_name", ""))
        if not normalized_name:
            continue
        actions_by_name[normalized_name].append(dict(action))
        target_counts[normalized_name] += 1

    executed_actions = []
    selected_counts = Counter()
    selected_rows = set()

    for swipe_index in range(max_swipes + 1):
        visible_items = _scan_visible_shop_items()
        for entry in visible_items:
            resolved = entry["catalog_match"]
            if not resolved:
                continue

            item_name = resolved["item"]["name"]
            normalized_name = _normalize_text(item_name)
            if normalized_name not in target_counts:
                continue
            if selected_counts[normalized_name] >= target_counts[normalized_name]:
                continue

            row_key = tuple(entry["pick_match"]["center"])
            if row_key in selected_rows:
                continue

            _tap_match(entry["pick_match"], wait_after=WAIT_AFTER_ITEM_TAP)
            selected_rows.add(row_key)
            selected_counts[normalized_name] += 1

            if actions_by_name[normalized_name]:
                executed_actions.append(actions_by_name[normalized_name].popleft())

        if all(selected_counts[name] >= count for name, count in target_counts.items()):
            break

        if swipe_index < max_swipes:
            log_debug(f"[Items] Purchase scan swipe {swipe_index + 1}/{max_swipes}")
            if not _swipe_shop_once(settings):
                log_warning("[Items] Failed to swipe item shop during purchase scan")
                break

    confirm_used = False
    if executed_actions:
        confirm_used = _tap_button_if_visible(CONFIRM_TEMPLATE, "confirm button", attempts=15)
        if confirm_used:
            time.sleep(WAIT_AFTER_CONFIRM)
        else:
            log_warning("[Items] Confirm button not found after selecting purchases")
    else:
        log_info("[Items] No purchasable targets were found in shop scan")

    _close_shop_after_purchase(confirm_used)
    return executed_actions if confirm_used else []
