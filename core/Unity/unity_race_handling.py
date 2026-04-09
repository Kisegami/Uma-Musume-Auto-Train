import time
from typing import List, Tuple, Optional

from utils.vision.recognizer import match_template, locate_on_screen, max_match_confidence
from utils.vision.template_matching import deduplicated_matches
from utils.capture.screenshot import take_screenshot
from utils.inputs.input import tap, wait_and_tap
from utils.core.log import log_info, log_debug, log_warning
from utils.constants.unity import get_template_region

# Regions (x1, y1, x2, y2)
TEAM_RANK_REGION = (0, 48, 270, 201)
OPPONENT_RANK_REGION = (3, 217, 387, 1465)

# Rank order (higher first)
RANK_ORDER = ["S", "A", "B", "C", "D", "E", "G"]
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
    "A": "assets/unity/opponent_a.png",
    "B": "assets/unity/opponent_b.png",
    "C": "assets/unity/opponent_c.png",
    "D": "assets/unity/opponent_d.png",
    "E": "assets/unity/opponent_e.png",
    "F": "assets/unity/opponent_f.png",
    "G": "assets/unity/opponent_g.png",
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


def _center_of_bbox(bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
    x, y, w, h = bbox
    return x + w // 2, y + h // 2


def _double_tap(x: int, y: int):
    """Tap twice with 100ms interval."""
    tap(x, y)
    time.sleep(0.1)
    tap(x, y)


def _wait_and_double_tap(template_path: str, timeout: float, check_interval: float = 0.2, confidence: float = 0.8) -> bool:
    """Wait for template and double tap with 100ms interval."""
    start = time.time()
    region = get_template_region(template_path)
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
    region = get_template_region(template_path)
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


def unity_race_workflow():
    """
    Unity Race handling workflow.
    Trigger: caller already detected Unity Cup in lobby and invoked this workflow.
    """
    log_info("[UnityRace] Starting Unity race workflow...")

    # Tap Unity Race button first
    if not _wait_and_double_tap("assets/unity/unity_race.png", timeout=8):
        log_warning("[UnityRace] unity_race.png not found/clicked; aborting workflow.")
        return False

    # Step 1: Opponent selection or Zenith Race (polling with screenshot interval)
    log_info("[UnityRace] Waiting for Select Opponent or Zenith Race button...")
    timeout = 20.0
    check_interval = 0.5
    start_time = time.time()
    select_opponent = None
    zenith_btn = None
    screenshot = None
    
    while time.time() - start_time < timeout:
        screenshot = take_screenshot()
        select_matches = match_template(screenshot, "assets/unity/select_opponent.png", confidence=0.8, region=get_template_region("assets/unity/select_opponent.png"))
        select_opponent = select_matches[0] if select_matches else None
        zenith_matches = match_template(screenshot, "assets/unity/zenith_race_btn.png", confidence=0.8, region=get_template_region("assets/unity/zenith_race_btn.png"))
        zenith_btn = zenith_matches[0] if zenith_matches else None
        
        if select_opponent or zenith_btn:
            break
        
        time.sleep(check_interval)
    
    if not select_opponent and not zenith_btn:
        log_warning("[UnityRace] Neither Select Opponent nor Zenith Race detected within timeout.")
        screenshot = take_screenshot()  # Take one final screenshot for error handling

    if select_opponent:
        log_info("[UnityRace] Select Opponent screen detected.")
        # Team rank
        team_ranks = _detect_ranks(TEAM_RANK_REGION, TEAM_TEMPLATES, screenshot)
        team_rank = team_ranks[0][0] if team_ranks else None
        log_info(f"[UnityRace] Team rank detected: {team_rank}")

        # Opponent ranks
        opponent_ranks = _detect_ranks(OPPONENT_RANK_REGION, OPPONENT_TEMPLATES, screenshot)
        log_info(f"[UnityRace] Opponent ranks detected: {[r for r, _ in opponent_ranks]}")

        chosen = None
        if team_rank and opponent_ranks:
            chosen = _pick_best_opponent(team_rank, opponent_ranks)

        if chosen:
            rank, bbox = chosen
            cx, cy = _center_of_bbox(bbox)
            log_info(f"[UnityRace] Choosing opponent rank {rank}")
            _double_tap(cx, cy)
        else:
            log_warning("[UnityRace] No suitable opponent found (<= team rank).")

        # Tap the select/confirm button (use bbox directly)
        sx, sy, sw, sh = select_opponent
        _double_tap(sx + sw // 2, sy + sh // 2)

    elif zenith_btn:
        log_info("[UnityRace] Zenith Race button detected, tapping.")
        x, y, w, h = zenith_btn
        _double_tap(x + w // 2, y + h // 2)

    else:
        log_warning("[UnityRace] Neither Select Opponent nor Zenith Race detected after tapping unity_race. Aborting.")
        return False

    # Step 2: Begin Showdown -> See All Race -> Skip -> Next -> Next Unity -> Next
    time.sleep(0.1)
    screenshot = take_screenshot()

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

    log_info("[UnityRace] Skipping race...")
    if not _wait_and_double_tap("assets/buttons/skip_btn.png", timeout=20):
        log_warning("[UnityRace] skip_btn.png not found; aborting workflow.")
        return False

    log_info("[UnityRace] Next...")
    if not _wait_and_double_tap("assets/buttons/next_btn.png", timeout=20):
        log_warning("[UnityRace] next_btn.png not found after skip; aborting workflow.")
        return False

    log_info("[UnityRace] Next Unity...")
    if not _wait_and_double_tap("assets/unity/next_unity.png", timeout=20):
        log_warning("[UnityRace] next_unity.png not found; aborting workflow.")
        return False

    log_info("[UnityRace] Final Next...")
    if not _wait_and_double_tap("assets/buttons/next_btn.png", timeout=20):
        log_warning("[UnityRace] final next_btn.png not found; aborting workflow.")
        return False

    log_info("[UnityRace] Workflow completed.")
    return True


