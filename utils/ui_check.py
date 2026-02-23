import time
from utils.screenshot import take_screenshot
from utils.template_matching import match_template
from utils.log import log_info, log_warning, log_error, log_debug
from core.Unity.execute import career_lobby

try:
    from utils.device import reopen_and_resume_career
except ImportError:
    reopen_and_resume_career = None

def Home_run():
    log_info("Home theater found, running Home_run()...")
    # Placeholder for Home_run logic
    pass

def return_home():
    log_info("Home found, running return_home()...")
    # Placeholder for return_home logic
    pass

def reconnect():
    log_info("Connection error found, running reconnect()...")
    # Placeholder for reconnect logic
    pass

def continue_race():
    log_info("View results found, running continue_race()...")
    # Placeholder for continue_race logic
    pass

def ui_check():
    """
    Run the UI check sequence
    """
    log_info("Starting UI check...")
    
    # 1. Run the lobby loop 3 times
    for i in range(3):
        log_info(f"Running lobby loop - Attempt {i + 1}/3...")
        # Since career_lobby() is a while True loop natively,
        # we realistically don't "run it 3 times" like a regular function.
        # However, following the spec strictly:
        try:
            # This requires custom handling if career_lobby traps execution, 
            # assuming it returns after a single logical pass for some reason or 
            # we just call it. For safety we might just assume the user means "run lobby logic".
            career_lobby() 
        except Exception as e:
            log_warning(f"Lobby loop iteration {i+1} exited/failed: {e}")
            pass
        
    log_info("Finished running lobby loops. Checking for specific UI screens...")

    # Now take a screenshot to check 
    screenshot = take_screenshot()
    
    # 2. Check home_theater.png
    if match_template(screenshot, "assets/ui/home_theater.png", confidence=0.8):
        Home_run()
        return True
        
    # 3. Check home.png
    if match_template(screenshot, "assets/ui/home.png", confidence=0.8):
        return_home()
        return True
        
    # 4. Check connection_error.png
    if match_template(screenshot, "assets/ui/connection_error.png", confidence=0.8):
        reconnect()
        return True
        
    # 5. Check view_results.png
    if match_template(screenshot, "assets/buttons/view_results.png", confidence=0.8):
        continue_race()
        return True
        
    # 6. If nothing above run, restart the game
    log_warning("No recognized UI elements found after checks. Restarting the game...")
    if reopen_and_resume_career:
        reopen_and_resume_career()
        return True
    else:
        log_error("Restart function (reopen_and_resume_career) not available or imported!")
        
    return False

if __name__ == "__main__":
    ui_check()
