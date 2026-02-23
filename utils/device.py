import subprocess
import time
import os
import sys
from pathlib import Path
from utils.log import log_debug, log_info, log_warning, log_error
from utils.config_loader import load_config_section

def _find_bundled_adb():
    """
    Find bundled ADB with priority:
    1. toolkit/ADB/ directory (extracted ADB binary)
    2. adbutils package binaries
    Returns path to adb executable or None if not found.
    """
    # First, check toolkit/ADB/ directory (for lightweight releases)
    script_dir = Path(__file__).parent.parent.parent  # Go up from utils/device.py to project root
    toolkit_adb_paths = [
        script_dir / 'toolkit' / 'ADB' / 'adb.exe',  # Windows
        script_dir / 'toolkit' / 'ADB' / 'adb',      # Linux/Mac
    ]
    for adb_path in toolkit_adb_paths:
        if adb_path.exists():
            if sys.platform != 'win32' and not os.access(adb_path, os.X_OK):
                continue
            # log_debug(f"Using bundled ADB from toolkit: {adb_path}")
            return str(adb_path)
    
    # Try to find adbutils binaries (fallback for when dependencies are installed)
    try:
        import site
        site_packages = site.getsitepackages()
        
        # Check common locations
        for site_pkg in site_packages:
            adb_path = Path(site_pkg) / 'adbutils' / 'binaries' / 'adb.exe'
            if adb_path.exists():
                return str(adb_path)
            
            # Linux/Mac
            adb_path = Path(site_pkg) / 'adbutils' / 'binaries' / 'adb'
            if adb_path.exists() and os.access(adb_path, os.X_OK):
                return str(adb_path)
        
        # Check relative to current Python executable (for venv)
        python_dir = Path(sys.executable).parent
        adb_path = python_dir / 'Lib' / 'site-packages' / 'adbutils' / 'binaries' / 'adb.exe'
        if adb_path.exists():
            return str(adb_path)
        
        # Linux/Mac venv
        adb_path = python_dir / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages' / 'adbutils' / 'binaries' / 'adb'
        if adb_path.exists() and os.access(adb_path, os.X_OK):
            return str(adb_path)
            
    except Exception as e:
        # log_debug(f"Could not find bundled ADB: {e}")
        pass
    
    return None

def _load_adb_config():
    return load_config_section('adb_config', {})

def _get_adb_path():
    """
    Get ADB path with priority:
    1. From config.json (adb_config.adb_path)
    2. Bundled ADB from adbutils
    3. System ADB (in PATH)
    """
    adb_cfg = _load_adb_config()
    config_path = adb_cfg.get('adb_path')
    
    # If explicitly set in config, use it
    if config_path and config_path != 'adb':
        if os.path.exists(config_path):
            return config_path
        # log_warning(f"ADB path from config not found: {config_path}, trying bundled ADB...")
    
    # Try bundled ADB from adbutils
    bundled_adb = _find_bundled_adb()
    if bundled_adb:
        # log_debug(f"Using bundled ADB: {bundled_adb}")
        return bundled_adb
    
    # Fallback to system ADB
    log_info("Bundled ADB not found, using system ADB (must be in PATH)")
    return 'adb'

def run_adb(command, binary=False, add_input_delay=False):
    """
    Execute an ADB command using settings from config.json (adb_config).
    Automatically uses bundled ADB from adbutils if available.

    Args:
        command: list[str] like ['shell','input','tap','x','y']
        binary: when True, return raw bytes stdout
        add_input_delay: if True, sleep input_delay when invoking 'input' commands
                         Set to False to skip delay (faster but may cause input conflicts on some emulators)

    Returns:
        str|bytes|None: stdout text (default) or bytes (when binary=True) on success; None on error
    
    Note:
        input_delay exists to prevent input conflicts when sending rapid commands to emulators.
        Some emulators may drop or ignore inputs if sent too quickly. However, modern emulators
        (LDPlayer, Nemu, etc.) often work fine without delay. You can:
        - Set input_delay to 0.0 in config.json to disable globally
        - Use add_input_delay=False for specific calls that need speed
        - Reduce input_delay to 0.05-0.1s for a balance between speed and reliability
    """
    try:
        adb_cfg = _load_adb_config()
        adb_path = _get_adb_path()
        device_address = adb_cfg.get('device_address', '')
        input_delay = float(adb_cfg.get('input_delay', 0.5))

        full_cmd = [adb_path]
        if device_address:
            full_cmd.extend(['-s', device_address])
        full_cmd.extend(command)

        # Only apply delay if requested and delay > 0
        if add_input_delay and 'input' in command and input_delay > 0:
            time.sleep(input_delay)

        result = subprocess.run(full_cmd, capture_output=True, check=True)
        return result.stdout if binary else result.stdout.decode(errors='ignore').strip()
    except subprocess.CalledProcessError as e:
        log_error(f"ADB command failed: {e}")
        return None
    except Exception as e:
        log_error(f"Error running ADB command: {e}")
        return None

# ---------------------------------------------------------------------------
# Game restart helpers
# ---------------------------------------------------------------------------

GAME_PACKAGE = "com.cygames.umamusume"

def restart_game(package_name: str = GAME_PACKAGE) -> None:
    """Force-stop and cold-launch the game via ADB."""
    log_warning(f"[Watchdog] Force-stopping {package_name}...")
    run_adb(['shell', 'am', 'force-stop', package_name])
    time.sleep(2)
    log_info(f"[Watchdog] Relaunching {package_name}...")
    run_adb([
        'shell', 'monkey',
        '-p', package_name,
        '-c', 'android.intent.category.LAUNCHER',
        '1'
    ])


def reopen_and_resume_career() -> bool:
    """
    Full re-entry sequence after a game restart:

    1. Launch the game (caller must have called restart_game() first, or call
       this which will do it internally).
    2. Wait for title_menu.png  → spam-tap centre to advance.
    3. Dismiss any close.png / skip_btn.png popups as they appear.
    4. Tap ongoing_career.png  → wait & tap resume_career.png.
    5. Wait for tazuna_hint.png (lobby confirmed).

    Returns True when the lobby is confirmed, False on failure.
    """
    # Inline imports so this module stays light on top-level deps
    from utils.screenshot import take_screenshot
    from utils.recognizer import locate_on_screen, match_template
    from utils.input import tap, tap_on_image
    from utils.template_matching import wait_for_image
    from utils.log import log_info, log_warning, log_debug

    log_info("[Watchdog] Restarting game and resuming career...")
    restart_game()

    # ── Step 1: wait up to 90 s for title_menu to appear ──────────────────
    log_info("[Watchdog] Waiting for title screen...")
    title = wait_for_image("assets/buttons/title_menu.png", timeout=90, confidence=0.8)
    if not title:
        log_warning("[Watchdog] Title screen not found after 90 s — giving up.")
        return False

    log_info("[Watchdog] Title screen found. Tapping centre to advance...")

    # ── Step 2 + 3: spam-tap centre while dismissing popups until ongoing_career ──
    SPAM_TIMEOUT = 120          # seconds to find ongoing_career
    SPAM_INTERVAL = 0.4         # seconds between taps
    spam_start = time.time()

    while time.time() - spam_start < SPAM_TIMEOUT:
        screenshot = take_screenshot()

        # Done when ongoing_career appears
        ongoing = match_template(screenshot, "assets/buttons/ongoing_career.png", confidence=0.8)
        if ongoing:
            log_info("[Watchdog] 'Ongoing Career' button found.")
            break

        # Dismiss close / skip popups
        close = match_template(screenshot, "assets/buttons/close.png", confidence=0.8)
        if close:
            x, y, w, h = close[0]
            log_debug("[Watchdog] Dismissing close button.")
            tap(x + w // 2, y + h // 2)
            time.sleep(0.3)
            continue

        skip = match_template(screenshot, "assets/buttons/skip_btn.png", confidence=0.8)
        if skip:
            x, y, w, h = skip[0]
            log_debug("[Watchdog] Dismissing skip button.")
            tap(x + w // 2, y + h // 2)
            time.sleep(0.3)
            continue

        # Generic centre tap to advance
        tap(540, 960)
        time.sleep(SPAM_INTERVAL)
    else:
        log_warning("[Watchdog] 'Ongoing Career' button not found — giving up.")
        return False

    # ── Step 4a: tap ongoing_career ────────────────────────────────────────
    time.sleep(5)  # wait for screen to stabilise before tapping Ongoing Career
    screenshot = take_screenshot()
    ongoing = match_template(screenshot, "assets/buttons/ongoing_career.png", confidence=0.8)
    if ongoing:
        x, y, w, h = ongoing[0]
        tap(x + w // 2, y + h // 2)
        log_info("[Watchdog] Tapped 'Ongoing Career'.")
    time.sleep(1.5)

    # ── Step 4b: wait for resume_career ───────────────────────────────────
    log_info("[Watchdog] Waiting for 'Resume Career' button...")
    resume = wait_for_image("assets/buttons/resume_career.png", timeout=30, confidence=0.8)
    if not resume:
        log_warning("[Watchdog] 'Resume Career' button not found.")
        return False

    tap(resume[0], resume[1])
    log_info("[Watchdog] Tapped 'Resume Career'.")
    time.sleep(2)

    # ── Step 5: wait for lobby (tazuna_hint) ──────────────────────────────
    log_info("[Watchdog] Waiting for lobby (tazuna_hint)...")
    lobby = wait_for_image("assets/ui/tazuna_hint.png", timeout=60, confidence=0.95)
    if not lobby:
        log_warning("[Watchdog] Lobby not confirmed after resume.")
        return False

    log_info("[Watchdog] Lobby confirmed — resuming automation.")
    return True

