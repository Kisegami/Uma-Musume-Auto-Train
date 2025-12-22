"""
Standalone skill scanner that:
1) Ensures ADB device is connected
2) Scans and scrolls through skills using the skill_up template
3) Prints a deduplicated list of skills (name + price)

This script intentionally avoids importing from core/Unity modules.
It relies only on utils helpers and bundled assets.

Run: python standalone_skill_scan.py
Optional config: set adb_config.device_address in config.json to pick a device.
"""

import os
import re
import subprocess
import time
from typing import List, Tuple, Dict, Any

import cv2
import numpy as np
from PIL import Image

from utils.device import _get_adb_path, _load_adb_config, run_adb
from utils.input import perform_swipe, tap
from utils.log import log_debug, log_error, log_info, log_warning
from utils.screenshot import take_screenshot

try:
    import pytesseract

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    log_warning("pytesseract not installed; OCR will be skipped.")


# -------------------------
# ADB helpers
# -------------------------
def _list_devices(adb_path: str) -> List[str]:
    """Return list of connected device serials."""
    try:
        result = subprocess.run(
            [adb_path, "devices"],
            capture_output=True,
            text=True,
            check=True,
        )
        lines = result.stdout.splitlines()
        return [
            line.split()[0]
            for line in lines
            if "\tdevice" in line and not line.startswith("List of devices")
        ]
    except Exception as exc:  # pragma: no cover - diagnostic only
        log_error(f"Failed to list devices: {exc}")
        return []


def ensure_device_connected() -> bool:
    """
    Ensure an ADB device is available.
    - Uses config.json -> adb_config.device_address if provided.
    - Falls back to any already connected device.
    """
    cfg = _load_adb_config()
    target = cfg.get("device_address", "")
    adb_path = _get_adb_path()

    connected = _list_devices(adb_path)
    if connected:
        log_info(f"Using connected device: {connected[0]}")
        return True

    if target:
        log_info(f"No device connected, attempting adb connect {target} ...")
        try:
            subprocess.run(
                [adb_path, "connect", target],
                capture_output=True,
                text=True,
                check=False,
            )
            time.sleep(1)
        except Exception as exc:  # pragma: no cover - diagnostic only
            log_error(f"adb connect failed: {exc}")

        connected = _list_devices(adb_path)
        if connected:
            log_info(f"Connected to {connected[0]}")
            return True
        log_warning("adb connect did not find a device.")
    else:
        log_warning("No device connected and adb_config.device_address not set.")

    return False


# -------------------------
# OCR helpers
# -------------------------
def clean_skill_name(text: str) -> str:
    if not text:
        return "Unknown Skill"

    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[^\w\s\-\(\)'\"&]", "", text)
    text = re.sub(r"^[0-9]+", "", text).strip()

    # Known misreads
    lower = text.lower()
    if lower.startswith("1can see right through you") or (
        lower.startswith("1") and "can see" in lower
    ):
        return "I Can See Right Through You"
    if "can see right through you" in lower and lower != "i can see right through you":
        return "I Can See Right Through You"
    if lower in {"umastan", "uma stan", "umestan"}:
        return "Uma Stan"

    return text if text else "Unknown Skill"


def clean_skill_price(text: str) -> str:
    if not text:
        return "0"
    text = re.sub(r"\s+", " ", text).strip()
    numbers = re.findall(r"\d+", text)
    if numbers:
        return numbers[0]
    return text if text else "0"


# -------------------------
# Template matching helpers
# -------------------------
def remove_overlapping_rectangles(
    rectangles: List[Tuple[int, int, int, int]], overlap_threshold: float = 0.5
) -> List[Tuple[int, int, int, int]]:
    if not rectangles:
        return []

    boxes = [[x, y, x + w, y + h] for x, y, w, h in rectangles]
    boxes = sorted(
        boxes,
        key=lambda box: (box[2] - box[0]) * (box[3] - box[1]),
        reverse=True,
    )

    keep = []
    for box in boxes:
        should_keep = True
        for kept_box in keep:
            x1 = max(box[0], kept_box[0])
            y1 = max(box[1], kept_box[1])
            x2 = min(box[2], kept_box[2])
            y2 = min(box[3], kept_box[3])
            if x1 < x2 and y1 < y2:
                intersection_area = (x2 - x1) * (y2 - y1)
                box_area = (box[2] - box[0]) * (box[3] - box[1])
                if intersection_area / box_area >= overlap_threshold:
                    should_keep = False
                    break
        if should_keep:
            keep.append(box)
    return [(x1, y1, x2 - x1, y2 - y1) for x1, y1, x2, y2 in keep]


def _load_skill_template():
    template_path = os.path.join("assets", "buttons", "skill_up.png")
    if not os.path.exists(template_path):
        return None, f"Template not found: {template_path}"
    template = cv2.imread(template_path, cv2.IMREAD_COLOR)
    if template is None:
        return None, f"Failed to load template: {template_path}"
    return template, None


def _perform_template_matching(screenshot: Image.Image, template, confidence: float):
    screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    template_height, template_width = template.shape[:2]
    result = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
    locations = np.where(result >= confidence)
    matches = [(pt[0], pt[1], template_width, template_height) for pt in zip(*locations[::-1])]
    return matches


def is_button_available(
    screenshot: Image.Image,
    x: int,
    y: int,
    width: int,
    height: int,
    brightness_threshold: int = 150,
) -> Tuple[bool, float]:
    button_region = screenshot.crop((x, y, x + width, y + height)).convert("L")
    brightness_array = np.array(button_region)
    avg_brightness = float(np.mean(brightness_array))
    return avg_brightness >= brightness_threshold, avg_brightness


def _filter_available_buttons(
    screenshot: Image.Image,
    unique_matches: List[Tuple[int, int, int, int]],
    filter_dark_buttons: bool,
    brightness_threshold: int,
):
    if not filter_dark_buttons:
        return unique_matches, []

    available = []
    info = []
    for rect in unique_matches:
        x, y, w, h = rect
        is_available, avg = is_button_available(screenshot, x, y, w, h, brightness_threshold)
        info.append({"location": rect, "brightness": avg, "available": is_available})
        if is_available:
            available.append(rect)
    return available, info


# -------------------------
# OCR extraction
# -------------------------
def extract_skill_info(screenshot: Image.Image, button_x: int, button_y: int):
    if not OCR_AVAILABLE:
        return {"name": "OCR not available", "price": "OCR not available"}

    offset_x = button_x - 946
    offset_y = button_y - 809

    name_region = (204 + offset_x, 719 + offset_y, 732 + offset_x, 788 + offset_y)
    price_region = (834 + offset_x, 803 + offset_y, 927 + offset_x, 854 + offset_y)

    name = "Name Error"
    price = "Price Error"
    try:
        name_crop = screenshot.crop(name_region)
        name_raw = pytesseract.image_to_string(name_crop, lang="eng").strip()
        name = clean_skill_name(name_raw)
    except Exception as exc:
        log_debug(f"Name OCR error: {exc}")

    try:
        price_crop = screenshot.crop(price_region)
        price_raw = pytesseract.image_to_string(price_crop, lang="eng").strip()
        if not price_raw:
            price_raw = pytesseract.image_to_string(
                price_crop,
                config="--psm 8 -c tessedit_char_whitelist=0123456789",
            ).strip()
        if not price_raw:
            price_raw = pytesseract.image_to_string(price_crop, config="--psm 7").strip()
        price = clean_skill_price(price_raw)
    except Exception as exc:
        log_debug(f"Price OCR error: {exc}")

    return {"name": name, "price": price}


def _extract_skills_info(
    screenshot: Image.Image,
    available_matches: List[Tuple[int, int, int, int]],
    extract_skills: bool,
):
    if not extract_skills or not available_matches:
        return []
    skills = []
    for x, y, w, h in available_matches:
        info = extract_skill_info(screenshot, x, y)
        skills.append(
            {
                "name": info["name"],
                "price": info["price"],
                "location": (x, y, w, h),
            }
        )
    return skills


# -------------------------
# String similarity / dedup
# -------------------------
def calculate_string_similarity(str1: str, str2: str) -> float:
    if not str1 or not str2:
        return 0.0
    if str1 == str2:
        return 1.0

    def levenshtein_distance(s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    distance = levenshtein_distance(str1, str2)
    max_length = max(len(str1), len(str2))
    return 1.0 - (distance / max_length)


def deduplicate_skills(skills_list: List[Dict[str, Any]], similarity_threshold: float = 0.8):
    if not skills_list:
        return []
    if len(skills_list) == 1:
        return skills_list

    sorted_skills = sorted(
        skills_list,
        key=lambda x: int(x.get("price", "0")) if str(x.get("price", "0")).isdigit() else 0,
    )

    deduped = []
    seen = set()
    for skill in sorted_skills:
        name = skill.get("name", "").lower().strip()
        if not name:
            continue
        duplicate = any(
            calculate_string_similarity(name, seen_name) >= similarity_threshold for seen_name in seen
        )
        if not duplicate:
            deduped.append(skill)
            seen.add(name)
    return deduped


# -------------------------
# Core scanning logic
# -------------------------
def recognize_skill_up_locations(
    confidence: float = 0.9,
    overlap_threshold: float = 0.5,
    filter_dark_buttons: bool = True,
    brightness_threshold: int = 150,
    extract_skills: bool = True,
):
    screenshot = take_screenshot()
    template, err = _load_skill_template()
    if template is None:
        return {"error": err, "count": 0, "skills": []}

    matches = _perform_template_matching(screenshot, template, confidence)
    unique_matches = remove_overlapping_rectangles(matches, overlap_threshold)
    available_matches, brightness_info = _filter_available_buttons(
        screenshot, unique_matches, filter_dark_buttons, brightness_threshold
    )
    skills_info = _extract_skills_info(screenshot, available_matches, extract_skills)

    return {
        "count": len(available_matches),
        "skills": skills_info,
        "available_matches": available_matches,
        "brightness_info": brightness_info,
        "raw_matches": len(matches),
        "deduplicated_matches": len(unique_matches),
    }


def scan_all_skills_with_scroll(
    swipe_start_x: int = 504,
    swipe_start_y: int = 1500,
    swipe_end_x: int = 504,
    swipe_end_y: int = 887,
    confidence: float = 0.9,
    brightness_threshold: int = 150,
    max_scrolls: int = 20,
):
    all_skills = []
    seen_names = set()
    scrolls = 0
    duplicate_found = None

    while scrolls < max_scrolls:
        log_info(f"Scanning page {scrolls + 1}/{max_scrolls} ...")
        result = recognize_skill_up_locations(
            confidence=confidence,
            overlap_threshold=0.5,
            filter_dark_buttons=True,
            brightness_threshold=brightness_threshold,
            extract_skills=True,
        )
        if "error" in result:
            return {**result, "all_skills": all_skills, "scrolls_performed": scrolls}

        current_skills = result.get("skills", [])
        if not current_skills:
            log_debug("No skills detected on this screen.")

        for skill in current_skills:
            name = skill.get("name", "")
            if name in seen_names:
                duplicate_found = name
                log_info(f"Duplicate detected ('{name}'), stopping scroll.")
                break
            seen_names.add(name)
            all_skills.append(skill)

        if duplicate_found:
            break

        scrolls += 1
        if scrolls < max_scrolls:
            log_debug("Scrolling down...")
            # time.sleep(0.1)
            if not perform_swipe(swipe_start_x, swipe_start_y, swipe_end_x, swipe_end_y):
                log_warning("Swipe failed; stopping.")
                break
            tap(504, 800)
            # time.sleep(0.2)

    return {
        "all_skills": all_skills,
        "total_unique_skills": len(all_skills),
        "scrolls_performed": scrolls,
        "duplicate_found": duplicate_found,
    }


# -------------------------
# Entry point
# -------------------------
def main():
    log_info("=== Standalone Skill Scanner ===")
    if not ensure_device_connected():
        log_error("No device available. Please connect an emulator/device first.")
        return

    scan_result = scan_all_skills_with_scroll()
    if scan_result.get("error"):
        log_error(f"Scan failed: {scan_result['error']}")
        return

    deduped = deduplicate_skills(scan_result.get("all_skills", []))
    log_info("=== Deduplicated Skill List ===")
    for idx, skill in enumerate(deduped, start=1):
        log_info(f"{idx:02d}. {skill.get('name')} - {skill.get('price')}")

    log_info(
        f"Total unique skills: {len(deduped)} | Scrolls: {scan_result.get('scrolls_performed', 0)}"
    )


if __name__ == "__main__":
    main()





