import time
from typing import List, Tuple, Optional

from PIL import ImageStat

from utils.vision.recognizer import match_template, max_match_confidence
from utils.vision.template_matching import deduplicated_matches
from utils.capture.screenshot import take_screenshot
from utils.inputs.input import tap
from utils.core.config_loader import load_main_config
from utils.core.log import log_info, log_debug, log_warning


# Regions (x1, y1, x2, y2)
TEAM_RANK_REGION = (0, 48, 270, 201)
OPPONENT_RANK_REGION = (3, 217, 387, 1465)

# Rank order (higher first)
RANK_ORDER = ["S", "A", "B", "C", "D", "E", "F", "G"]
RANK_INDEX = {r: i for i, r in enumerate(RANK_ORDER)}

TEAM_TEMPLATES = {
    "S": "assets/unity/team_s.png",   # placeholder if added later
    "A": "assets/unity/team_a.png",   # placeholder if added later
    "B": "assets/unity/team_b.png",
    "C": "assets/unity/team_c.png",
    "D": "assets/unity/team_d.png",
    "E": "assets/unity/team_e.png",
    # "G": "assets/unity/team_f.png",  # placeholder if ever added
    "G": None,
}

OPPONENT_TEMPLATES = {
    "S": "assets/unity/opponent_s.png",
    "A": "assets/unity/opponent_a.png",
    "B": "assets/unity/opponent_b.png",
    "C": "assets/unity/opponent_c.png",
    "D": "assets/unity/opponent_d.png",
    "E": "assets/unity/opponent_e.png",
    "F": "assets/unity/opponent_f.png",
    "G": "assets/unity/opponent_g.png",
}

UNITY_RETRY_TEMPLATE = "assets/unity/unity_retry.png"
UNITY_RACE_TRY_AGAIN_TEMPLATE = "assets/unity/unity_race_try_again.png"
UNITY_RESULT_NEXT_TEMPLATE = "assets/unity/unity_race_next.png"
UNITY_RETRY_BRIGHTNESS_THRESHOLD = 180
UNITY_RESULT_BUTTON_DELAY = 2.0
UNITY_OPPONENT_EQUAL_RANK = "equal_rank"
UNITY_OPPONENT_HIGHEST_RANK = "highest_rank"
UNITY_OPPONENT_RESCAN_DELAY = 3.0
ZENITH_RACE_TEMPLATES = (
    "assets/unity/zenith_race_btn.png",
    "assets/unity/zenith_race_btn_2.png",
)


def _get_unity_race_settings():
    racing_config = load_main_config().get("racing", {})
    return {
        "use_clock_retry": racing_config.get("unity_use_clock_retry", False),
        "opponent_select_method": racing_config.get(
            "unity_opponent_select_method",
            UNITY_OPPONENT_EQUAL_RANK,
        ),
    }


def _detect_ranks(region: Tuple[int, int, int, int], templates: dict, screenshot) -> List[Tuple[str, Tuple[int, int, int, int]]]:
    """Return list of (rank, bbox) within a region using template matching."""
    x1, y1, x2, y2 = region
    region_cv = (x1, y1, x2 - x1, y2 - y1)
    results = []
    for rank, path in templates.items():
        if not path:
            continue
        matches = match_template(screenshot, path, confidence=0.8, region=region_cv)
        filtered = deduplicated_matches(matches, threshold=30) if matches else []
        for (x, y, w, h) in filtered:
            results.append((rank, (x, y, w, h)))
    return results


def _duplicated_rank_names(ranks: List[Tuple[str, Tuple[int, int, int, int]]]) -> List[str]:
    seen = set()
    duplicates = []
    for rank, _ in ranks:
        if rank in seen and rank not in duplicates:
            duplicates.append(rank)
        seen.add(rank)
    return duplicates


def _pick_best_opponent(team_rank: str, opponents: List[Tuple[str, Tuple[int, int, int, int]]]) -> Optional[Tuple[str, Tuple[int, int, int, int]]]:
    """Pick an opponent with rank <= team_rank, preferring the strongest (closest to team)."""
    if team_rank not in RANK_INDEX:
        return None
    team_idx = RANK_INDEX[team_rank]
    candidates = []
    for rank, bbox in opponents:
        if rank in RANK_INDEX and RANK_INDEX[rank] >= team_idx:
            # higher index == lower rank (because list is high->low)
            candidates.append((RANK_INDEX[rank], rank, bbox))
    if not candidates:
        return None
    candidates.sort()  # smallest index first (closest to team rank but not higher)
    best = candidates[0]
    return best[1], best[2]


def _pick_top_opponent(opponents: List[Tuple[str, Tuple[int, int, int, int]]]) -> Optional[Tuple[str, Tuple[int, int, int, int]]]:
    """Pick the visually topmost opponent, regardless of rank."""
    if not opponents:
        return None
    return min(opponents, key=lambda item: item[1][1])


def _center_of_bbox(bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
    x, y, w, h = bbox
    return x + w // 2, y + h // 2


def _find_first_template_match(screenshot, template_paths, confidence: float = 0.8):
    for template_path in template_paths:
        matches = match_template(screenshot, template_path, confidence=confidence)
        if matches:
            return matches[0]
    return None


def _double_tap(x: int, y: int):
    """Tap twice with 100ms interval."""
    tap(x, y)
    time.sleep(0.1)
    tap(x, y)


def _wait_between_unity_result_buttons():
    time.sleep(UNITY_RESULT_BUTTON_DELAY)


def _wait_and_double_tap(template_path: str, timeout: float, check_interval: float = 0.2, confidence: float = 0.8) -> bool:
    """Wait for template and double tap with 100ms interval."""
    start = time.time()
    region = None  # auto-resolved by recognizer
    best_score = 0.0
    while time.time() - start < timeout:
        screenshot = take_screenshot()
        score = max_match_confidence(screenshot, template_path, region=region)
        if score > best_score:
            best_score = score

        matches = match_template(screenshot, template_path, confidence=confidence, region=region)
        res = None
        if matches:
            x, y, w, h = matches[0]
            res = (x + w // 2, y + h // 2)

        if res:
            cx, cy = res
            _double_tap(cx, cy)
            return True
        time.sleep(check_interval)
    log_warning(
        f"_wait_and_double_tap: {template_path} not found within timeout. "
        f"best_confidence={best_score:.3f}, threshold={confidence:.3f}, region={region}"
    )
    return False


def _wait_and_tap(template_path: str, timeout: float, check_interval: float = 0.2, confidence: float = 0.8) -> bool:
    """Wait for template and tap its center once."""
    start = time.time()
    region = None  # auto-resolved by recognizer
    best_score = 0.0

    while time.time() - start < timeout:
        screenshot = take_screenshot()
        score = max_match_confidence(screenshot, template_path, region=region)
        if score > best_score:
            best_score = score

        matches = match_template(screenshot, template_path, confidence=confidence, region=region)
        if matches:
            x, y, w, h = matches[0]
            tap(x + w // 2, y + h // 2)
            return True

        time.sleep(check_interval)

    log_warning(
        f"_wait_and_tap: {template_path} not found within timeout. "
        f"best_confidence={best_score:.3f}, threshold={confidence:.3f}, region={region}"
    )
    return False


def _wait_for_stable_template(
    template_path: str,
    timeout: float,
    check_interval: float = 0.2,
    confidence: float = 0.8,
    stable_hits: int = 2,
) -> bool:
    """Wait until a template is detected in consecutive frames.

    This is used for buttons that appear during transition animations and may
    briefly match before they are safe to tap.
    """
    start = time.time()
    region = None  # auto-resolved by recognizer
    consecutive_hits = 0
    best_score = 0.0

    while time.time() - start < timeout:
        screenshot = take_screenshot()
        score = max_match_confidence(screenshot, template_path, region=region)
        if score > best_score:
            best_score = score

        if score >= confidence:
            consecutive_hits += 1
            if consecutive_hits >= stable_hits:
                return True
        else:
            consecutive_hits = 0

        time.sleep(check_interval)

    log_warning(
        f"_wait_for_stable_template: {template_path} not stable within timeout. "
        f"best_confidence={best_score:.3f}, threshold={confidence:.3f}, "
        f"stable_hits={stable_hits}, region={region}"
    )
    return False


def _is_unity_retry_enabled(screenshot, bbox, threshold: int = UNITY_RETRY_BRIGHTNESS_THRESHOLD) -> bool:
    x, y, w, h = bbox
    roi = screenshot.crop((x, y, x + w, y + h)).convert("L")
    brightness = float(ImageStat.Stat(roi).mean[0])
    enabled = brightness >= threshold
    log_info(
        f"[UnityRace] Clock retry brightness: {brightness:.1f} "
        f"({'enabled' if enabled else 'disabled'}, threshold={threshold})"
    )
    return enabled


def _tap_unity_result_next(screenshot, retry_bbox=None) -> None:
    """Tap the green Unity result Next button on the retry decision screen."""
    next_matches = match_template(screenshot, UNITY_RESULT_NEXT_TEMPLATE, confidence=0.8)
    if next_matches:
        x, y, w, h = next_matches[0]
        _double_tap(x + w // 2, y + h // 2)
        return

    if retry_bbox:
        x, y, w, h = retry_bbox
        next_x = x + w + (screenshot.width - (x + w)) // 2
        next_y = y + h // 2
    else:
        next_x = int(screenshot.width * 0.71)
        next_y = int(screenshot.height * 0.93)
    tap(int(next_x), int(next_y))


def _wait_retry_or_next(use_clock_retry: bool, timeout: float = 20, confidence: float = 0.8) -> str:
    """Wait for the retry decision screen.

    Returns:
        "retry" when a lit retry button was tapped,
        "next" when the normal next button was tapped,
        "missing" on timeout.
    """
    start = time.time()
    logged_retry_not_used = False
    while time.time() - start < timeout:
        screenshot = take_screenshot()

        retry_matches = match_template(screenshot, UNITY_RETRY_TEMPLATE, confidence=confidence)
        if retry_matches:
            retry_bbox = retry_matches[0]
            retry_enabled = _is_unity_retry_enabled(screenshot, retry_bbox)
            if use_clock_retry and retry_enabled:
                x, y, w, h = retry_bbox
                log_info("[UnityRace] Clock retry is enabled by config and available; retrying Unity race.")
                _double_tap(x + w // 2, y + h // 2)
                log_info("[UnityRace] Waiting for Unity Race Try Again confirmation...")
                if not _wait_and_tap(UNITY_RACE_TRY_AGAIN_TEMPLATE, timeout=10, confidence=0.8):
                    log_warning("[UnityRace] Unity Race Try Again button not found after clock retry tap.")
                    return "missing"
                return "retry"
            if not logged_retry_not_used:
                log_info("[UnityRace] Clock retry not used; tapping Unity result Next.")
                logged_retry_not_used = True
            _tap_unity_result_next(screenshot, retry_bbox)
            return "next"

        next_matches = match_template(screenshot, "assets/buttons/next_btn.png", confidence=confidence)
        if next_matches:
            x, y, w, h = next_matches[0]
            _double_tap(x + w // 2, y + h // 2)
            return "next"

        time.sleep(0.2)

    log_warning("[UnityRace] Neither Unity retry nor next button appeared within timeout.")
    return "missing"


def _select_unity_opponent_or_zenith(opponent_select_method: str) -> bool:
    log_info("[UnityRace] Waiting for Select Opponent or Zenith Race button...")
    timeout = 20.0
    check_interval = 0.5
    start_time = time.time()
    select_opponent = None
    zenith_btn = None
    screenshot = None

    while time.time() - start_time < timeout:
        screenshot = take_screenshot()
        select_matches = match_template(screenshot, "assets/unity/select_opponent.png", confidence=0.8)
        select_opponent = select_matches[0] if select_matches else None
        zenith_btn = _find_first_template_match(screenshot, ZENITH_RACE_TEMPLATES, confidence=0.8)

        if select_opponent or zenith_btn:
            break

        time.sleep(check_interval)

    if not select_opponent and not zenith_btn:
        log_warning("[UnityRace] Neither Select Opponent nor Zenith Race detected within timeout.")
        return False

    if select_opponent:
        log_info("[UnityRace] Select Opponent screen detected.")
        opponent_ranks = _detect_ranks(OPPONENT_RANK_REGION, OPPONENT_TEMPLATES, screenshot)
        log_info(f"[UnityRace] Opponent ranks detected: {[r for r, _ in opponent_ranks]}")
        duplicated_ranks = _duplicated_rank_names(opponent_ranks)
        if duplicated_ranks:
            log_info(
                "[UnityRace] Duplicate opponent rank badges detected "
                f"({duplicated_ranks}); waiting {UNITY_OPPONENT_RESCAN_DELAY:.0f}s for animation, then rescanning."
            )
            time.sleep(UNITY_OPPONENT_RESCAN_DELAY)
            screenshot = take_screenshot()
            opponent_ranks = _detect_ranks(OPPONENT_RANK_REGION, OPPONENT_TEMPLATES, screenshot)
            log_info(f"[UnityRace] Opponent ranks after rescan: {[r for r, _ in opponent_ranks]}")

        if opponent_select_method == UNITY_OPPONENT_HIGHEST_RANK:
            chosen = _pick_top_opponent(opponent_ranks)
            log_info("[UnityRace] Opponent select method: Pick highest rank Opponent")
        else:
            team_ranks = _detect_ranks(TEAM_RANK_REGION, TEAM_TEMPLATES, screenshot)
            team_rank = team_ranks[0][0] if team_ranks else None
            log_info(f"[UnityRace] Team rank detected: {team_rank}")
            chosen = _pick_best_opponent(team_rank, opponent_ranks) if team_rank and opponent_ranks else None
            log_info("[UnityRace] Opponent select method: Pick equal rank Opponent")

        if chosen:
            rank, bbox = chosen
            cx, cy = _center_of_bbox(bbox)
            log_info(f"[UnityRace] Choosing opponent rank {rank}")
            _double_tap(cx, cy)
        else:
            log_warning("[UnityRace] No suitable opponent found.")

        sx, sy, sw, sh = select_opponent
        _double_tap(sx + sw // 2, sy + sh // 2)
        return True

    log_info("[UnityRace] Zenith Race button detected, tapping.")
    x, y, w, h = zenith_btn
    _double_tap(x + w // 2, y + h // 2)
    return True


def unity_race_workflow():
    """
    Unity Race handling workflow.
    Trigger: caller already detected Unity Cup in lobby and invoked this workflow.
    """
    log_info("[UnityRace] Starting Unity race workflow...")
    settings = _get_unity_race_settings()

    # Tap Unity Race button first
    if not _wait_and_double_tap("assets/unity/unity_race.png", timeout=8):
        log_warning("[UnityRace] unity_race.png not found/clicked; aborting workflow.")
        return False

    retry_count = 0
    max_unity_retries = 10
    while retry_count <= max_unity_retries:
        if not _select_unity_opponent_or_zenith(settings["opponent_select_method"]):
            return False

        time.sleep(0.1)
        log_info("[UnityRace] Trying to begin showdown...")
        time.sleep(0.6)  # Allow the post-selection transition animation to settle.
        if not _wait_for_stable_template(
            "assets/unity/begin_showdown.png",
            timeout=20,
            check_interval=0.25,
            confidence=0.8,
            stable_hits=2,
        ):
            log_warning("[UnityRace] begin_showdown.png did not stabilize; aborting workflow before results sequence.")
            return False
        if not _wait_and_double_tap("assets/unity/begin_showdown.png", timeout=20):
            log_warning("[UnityRace] begin_showdown.png not found; aborting workflow before results sequence.")
            return False

        log_info("[UnityRace] Waiting for 'See All Race Results'...")
        if not _wait_and_double_tap("assets/unity/see_all_race_btn.png", timeout=12, confidence=0.8):
            log_warning("[UnityRace] Primary match for see_all_race_btn failed; retrying with lower confidence.")
            if not _wait_and_double_tap("assets/unity/see_all_race_btn.png", timeout=10, confidence=0.72):
                log_warning("[UnityRace] see_all_race_btn.png not found; aborting workflow.")
                return False

        _wait_between_unity_result_buttons()
        log_info("[UnityRace] Skipping race...")
        if not _wait_and_double_tap("assets/buttons/skip_btn.png", timeout=20):
            log_warning("[UnityRace] skip_btn.png not found; aborting workflow.")
            return False

        _wait_between_unity_result_buttons()
        log_info("[UnityRace] Next...")
        if not _wait_and_double_tap("assets/buttons/next_btn.png", timeout=20):
            log_warning("[UnityRace] next_btn.png not found after skip; aborting workflow.")
            return False

        _wait_between_unity_result_buttons()
        log_info("[UnityRace] Retry decision / Next...")
        retry_decision = _wait_retry_or_next(settings["use_clock_retry"], timeout=20)
        if retry_decision == "retry":
            retry_count += 1
            log_info(f"[UnityRace] Restarting Unity race from opponent selection ({retry_count}/{max_unity_retries}).")
            continue
        if retry_decision == "missing":
            return False

        _wait_between_unity_result_buttons()
        log_info("[UnityRace] Final Next...")
        if not _wait_and_double_tap("assets/buttons/next_btn.png", timeout=20):
            log_warning("[UnityRace] final next_btn.png not found; aborting workflow.")
            return False

        log_info("[UnityRace] Workflow completed.")
        return True

    log_warning("[UnityRace] Maximum Unity race clock retries reached; aborting workflow.")
    return False


