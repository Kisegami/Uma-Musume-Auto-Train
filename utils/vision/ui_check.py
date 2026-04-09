import time
import importlib
from utils.capture.screenshot import take_screenshot
from utils.vision.recognizer import locate_on_screen
from utils.core.log import log_info, log_warning, log_error, log_debug
from utils.inputs.input import tap
from utils.vision.template_matching import wait_for_image
from utils.platform.device import reopen_and_resume_career

# --- Dynamically load career_lobby based on mode ---
from utils.core.config_loader import load_main_config

def get_career_lobby():
    config = load_main_config()
    mode = config.get("mode", "ura").lower()
    
    try:
        module_name = f"core.{mode.capitalize()}.execute"
        module = importlib.import_module(module_name)
        return module.career_lobby
    except ImportError as e:
        log_error(f"Failed to load career_lobby for mode '{mode}': {e}. Falling back to Ura.")
        from core.Ura.execute import career_lobby
        return career_lobby

def Home_run():
    log_info("Bot started from Home screen")
    screenshot = take_screenshot()
    
    # 1. Check for ongoing career
    log_info("Checking for ongoing career...")
    ongoing = locate_on_screen("assets/buttons/ongoing_career.png", confidence=0.8)
    if ongoing:
        log_info("Ongoing career found. Attempting to resume...")
        tap(ongoing[0], ongoing[1])
        time.sleep(1.5)
        
        log_info("Waiting for 'Resume Career' button...")
        resume = wait_for_image("assets/buttons/resume_career.png", timeout=10, confidence=0.8)
        if resume:
            tap(resume[0], resume[1])
            log_info("Tapped 'Resume Career'. Waiting 5 seconds before checking UI...")
            time.sleep(5)
            
            for attempt in range(3):
                log_info(f"Running career_ui_check - Attempt {attempt + 1}/3...")
                if career_ui_check():
                    return True
                time.sleep(1)
                
            log_warning("Failed to resume automation after 3 UI checks.")
        else:
            log_warning("'Resume Career' button not found.")
            
    # 2. Check for Career Home button to start new career
    log_info("Checking for Career Home to start new career...")
    career_home = locate_on_screen("assets/buttons/Career_Home.png", confidence=0.8)
    if career_home:
        log_info("Career Home button found.")
        
        # Dynamically load restart_career modules
        config = load_main_config()
        mode = config.get("mode", "ura").lower()
        
        try:
            module_name = f"core.{mode.capitalize()}.restart_career"
            module = importlib.import_module(module_name)
            load_restart_config = module.load_restart_config
            start_career = module.start_career
                
            restart_config = load_restart_config()
            restart_enabled = restart_config.get('restart_enabled', False)
            
            if restart_enabled:
                log_info("Restart is enabled. Starting new career...")
                return start_career()
            else:
                log_warning("You need to enable restart career to start from home, or start the bot from Career Lobby")
                return False
                
        except Exception as e:
            log_error(f"Failed to execute start_career from Home: {e}")
            return False
            
    log_warning("Neither ongoing career nor Career Home button could be acted upon.")
    return False

def return_home():
    log_info("Not in Home, return to Home")
    
    # Check if home button is visible and tap it
    home_btn = locate_on_screen("assets/ui/home.png", confidence=0.8)
    if home_btn:
        log_info("Tapping home button...")
        tap(home_btn[0], home_btn[1])
        
        # Wait for home theater screen to confirm we arrived
        log_info("Waiting for home screen...")
        if wait_for_image("assets/ui/home_theater.png", timeout=15, confidence=0.8):
            log_info("Home screen confirmed. Start from Home Screen.")
            return Home_run()
        else:
            log_warning("Did not reach home screen after tapping home.")
            return False
            
    log_warning("Home button not found.")
    return False

def reconnect():
    log_info("Connection error found, try reconnect")
    
    # Check if retry button is visible and tap it
    retry_btn = locate_on_screen("assets/buttons/retry_connection.png", confidence=0.8)
    if retry_btn:
        log_info("Tapping retry connection button...")
        tap(retry_btn[0], retry_btn[1])
        
        # Wait 3 seconds to let game attempt reconnect
        time.sleep(3)
        
        log_info("Re-evaluating screen state...")
        return ui_check()
        
    log_warning("Retry connection button not found.")
    return False

def continue_race():
    log_info("Race screen found, continue the race")
    
    # Dynamically load the modules
    config = load_main_config()
    mode = config.get("mode", "ura").lower()
    
    try:
        module_name = f"core.{mode.capitalize()}.races_handling"
        module = importlib.import_module(module_name)
        race_prep = module.race_prep
        after_race = module.after_race
        handle_race_retry_if_failed = module.handle_race_retry_if_failed
    except Exception as e:
        log_error(f"Failed to load race handlers for continue_race: {e}")
        return False

    log_info("Starting race preparation...")
    race_prep()
    
    # Loop to check for either next button or clock icon with polling
    log_info("Checking for next button or clock icon with polling...")
    retry_count = 0
    max_retries_per_race = 250  # 50 seconds timeout (250 * 200ms)
    
    while retry_count < max_retries_per_race:
        retry_count += 1
        
        # 1. Check for clock (failed race)
        clock = locate_on_screen("assets/icons/clock.png", confidence=0.8)
        if clock:
            log_info(f"Race FAILED (clock icon detected, attempt {retry_count}), handling retry...")
            handle_race_retry_if_failed()
            continue
            
        # 2. Check for next (success)
        next_btn = locate_on_screen("assets/buttons/next_btn.png", confidence=0.8)
        if next_btn:
            log_info(f"Race complete (next button found after {retry_count} attempts). Handling after_race...")
            after_race()
            return True
            
        # 3. Spam tap middle to advance UI and wait
        tap(540, 960)
        time.sleep(0.2)
        
    log_warning(f"Safety limit reached ({max_retries_per_race} attempts), proceeding with after_race")
    after_race()
    return True

def enable_skip():
    """
    Enable skip by tapping skip_off twice, then skip_x1 once,
    and confirming skip_x2 is visible.
    """
    log_info("Enabling skip...")
    
    # Tap skip_off 2 times
    for i in range(2):
        skip_off = locate_on_screen("assets/buttons/skip_off.png", confidence=0.8)
        if skip_off:
            log_info(f"Tapping skip_off ({i + 1}/2)...")
            tap(skip_off[0], skip_off[1])
            time.sleep(0.5)
    
    # Tap skip_x1 1 time
    skip_x1 = locate_on_screen("assets/buttons/skip_x1.png", confidence=0.8)
    if skip_x1:
        log_info("Tapping skip_x1...")
        tap(skip_x1[0], skip_x1[1])
        time.sleep(0.5)
    
    # Confirm skip_x2 is visible
    skip_x2 = locate_on_screen("assets/buttons/skip_x2.png", confidence=0.8)
    if skip_x2:
        log_info("Skip enabled successfully (skip_x2 confirmed).")
    else:
        log_warning("skip_x2 not found â€” skip may not be fully enabled.")

def career_ui_check():
    """
    Specific UI check for career mode.
    """
    log_info("Starting career UI check...")
    
    # 0. Check if skip is disabled and enable it
    skip_off = locate_on_screen("assets/buttons/skip_off.png", confidence=0.8)
    if skip_off:
        log_info("Skip is disabled, enabling...")
        enable_skip()
    
    # 1. Check next, next2, ok buttons
    for btn_path in [
        "assets/buttons/next_btn.png", 
        "assets/buttons/next2_btn.png", 
        "assets/buttons/ok_btn.png"
    ]:
        btn = locate_on_screen(btn_path, confidence=0.8)
        if btn:
            log_info(f"Found {btn_path}, tapping and spamming middle...")
            tap(btn[0], btn[1])
            spam_start = time.time()
            while time.time() - spam_start < 5:
                tap(540, 960)
                time.sleep(0.3)
            return career_ui_check()
            
    # 2. Check back button
    back_btn = locate_on_screen("assets/buttons/back_btn.png", confidence=0.8)
    if back_btn:
        log_info("Found back button, tapping...")
        tap(back_btn[0], back_btn[1])
        time.sleep(1)
        return career_ui_check()
        
    # 3. Check tazuna_hint, event_choice_1, unity_cup, or complete_career (Career Lobby / end of run)
    if locate_on_screen("assets/ui/tazuna_hint.png", confidence=0.95) or \
       locate_on_screen("assets/icons/event_choice_1.png", confidence=0.8) or \
       locate_on_screen("assets/unity/unity_cup.png", confidence=0.8) or \
       locate_on_screen("assets/buttons/complete_career.png", confidence=0.8):
        log_info("Found Lobby, continue automation...")
        career_lobby_func = get_career_lobby()
        result = career_lobby_func()
        if result is False:
            raise RuntimeError("Bot stopped by career_lobby â€” do not restart.")
        return True
        
    # 4. Check connection error
    if locate_on_screen("assets/ui/connection_error.png", confidence=0.8):
        return reconnect()
        
    # 5. Check view results
    if locate_on_screen("assets/buttons/view_results.png", confidence=0.8):
        continue_race()
        log_info("Race finished. Waiting 5 seconds before career UI check...")
        time.sleep(5)
        for attempt in range(3):
            log_info(f"Post-race career_ui_check - Attempt {attempt + 1}/3...")
            if career_ui_check():
                return True
            time.sleep(1)
        log_warning("Failed to find career UI after race (3 attempts).")
        return False

    log_warning("No recognized UI elements found in career_ui_check.")
    return False

def ui_check(startup=False):
    """
    Run the UI check sequence.
    Detects the current screen state and routes to the appropriate handler.
    career_ui_check() handles all career-related screens and enters
    career_lobby() WITHOUT timeout for the permanent automation loop.
    
    Args:
        startup: If True (initial launch), stops the bot on unrecognized UI.
                 If False (called from watchdog/reopen), restarts the game instead.
    """
    log_info("Starting UI check...")
    
    # 1. Try career UI check â€” detects lobby, race, events, back button, etc.
    #    When it finds the lobby, it enters career_lobby() WITHOUT timeout
    log_info("Checking for career UI elements...")
    if career_ui_check():
        return True

    # 2. Check home_theater.png
    if locate_on_screen("assets/ui/home_theater.png", confidence=0.8):
        Home_run()
        return True
        
    # 3. Check home.png
    if locate_on_screen("assets/ui/home.png", confidence=0.8):
        return_home()
        return True
        
    # 4. Check connection_error.png
    if locate_on_screen("assets/ui/connection_error.png", confidence=0.8):
        reconnect()
        return True
        
    # 5. Nothing recognized
    if startup:
        # First launch â€” stop the bot so user can check what's on screen
        log_error("No recognized UI elements found at startup! Saving debug screenshot...")
        try:
            screenshot = take_screenshot()
            screenshot.save("debug_unknown_ui.png")
            log_error("Unknown UI screenshot saved to debug_unknown_ui.png")
        except Exception as e:
            log_error(f"Failed to save debug screenshot: {e}")
        raise RuntimeError("Unknown UI state at startup â€” stopping bot. Check debug_unknown_ui.png")
    else:
        # Called from watchdog/reopen â€” restart the game
        log_warning("No recognized UI elements found after checks. Restarting the game...")
        reopen_and_resume_career()
        return True

if __name__ == "__main__":
    ui_check()
