import time
import subprocess
import sys
import os

# Add script's directory to Python path (for embeddable Python compatibility)
# This ensures utils/ and other modules can be found regardless of how Python is invoked
if '__file__' in globals():
    script_dir = os.path.dirname(os.path.abspath(__file__))
else:
    # Fallback: use current working directory or sys.argv[0] if available
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv else os.getcwd()
if script_dir and script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils.core.log import log_info, log_warning, log_error, log_success

# Fix Windows console encoding for Unicode support
if os.name == 'nt':  # Windows
    try:
        # Set console to UTF-8 mode
        os.system('chcp 65001 > nul')
        # Also try to set stdout encoding
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

from utils.capture.screenshot import get_screen_size, load_config
from utils.core.config_loader import load_main_config

# Load full config to determine mode
def load_full_config():
    """Load full configuration from config.json"""
    try:
        return load_main_config()
    except Exception as e:
        log_error(f"Error loading config: {e}")
        return {}

config = load_full_config()
mode = config.get("mode", "ura").lower()

from utils.vision.ui_check import ui_check

# Import the appropriate execute module based on mode
if mode == "unity":
    mode_name = "Unity Cup"
else:
    mode_name = "URA"

from utils.platform.device import run_adb, _get_adb_path

# Logging is now handled by utils.core.log module

def check_adb_connection():
    """Check if ADB is connected to a device"""
    adb_config = load_config()  # This returns adb_config section
    adb_path = _get_adb_path()  # Use the function that finds bundled ADB
    device_address = adb_config.get('device_address', '')
    
    try:
        result = subprocess.run([adb_path, 'devices'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')[1:]  # Skip header line
        connected_devices = [line for line in lines if line.strip() and '\tdevice' in line]
        
        if not connected_devices:
            log_warning("No ADB devices connected!")
            # Try to auto-connect using device_address from config.json
            if device_address:
                log_info("Attempting to connect to: " + device_address)
                try:
                    connect_result = subprocess.run(
                        [adb_path, 'connect', device_address], capture_output=True, text=True, check=False
                    )
                    output = (connect_result.stdout or '').strip()
                    error_output = (connect_result.stderr or '').strip()
                    if output:
                        log_info(output)
                    if error_output and not output:
                        log_error(error_output)

                    # Re-check devices after attempting to connect
                    result = subprocess.run([adb_path, 'devices'], capture_output=True, text=True, check=True)
                    lines = result.stdout.strip().split('\n')[1:]
                    connected_devices = [line for line in lines if line.strip() and '\tdevice' in line]
                    if not connected_devices:
                        log_error("Failed to connect to device at: " + device_address)
                        log_info("Please ensure the emulator/device is running and USB debugging is enabled.")
                        return False
                except Exception as e:
                    log_error("Error during adb connect: " + str(e))
                    return False
            else:
                log_info("No device address configured in config.json (adb_config.device_address).")
                log_info("Please connect your Android device or emulator and enable USB debugging.")
                return False
        
        log_info("Connected devices: " + str(len(connected_devices)))
        for device in connected_devices:
            log_info("  " + device.split('\t')[0])
        return True
        
    except subprocess.CalledProcessError:
        log_info("ADB not found! Please install Android SDK and add ADB to your PATH.")
        return False
    except FileNotFoundError:
        log_info("ADB not found! Please install Android SDK and add ADB to your PATH.")
        return False

def get_device_info():
    """Get device information"""
    try:
        # Get screen size
        width, height = get_screen_size()
        log_info("Device screen size: " + str(width) + "x" + str(height))
        
        # Get device model
        model = run_adb(['shell', 'getprop', 'ro.product.model'])
        if model:
            log_info("Device model: " + model)
        
        # Get Android version
        version = run_adb(['shell', 'getprop', 'ro.build.version.release'])
        if version:
            log_info("Android version: " + version)
            
        return True
        
    except Exception as e:
        log_error("Error getting device info: " + str(e))
        return False

def main():
    log_info(f"Uma Auto - {mode_name} Version!")
    log_info("=" * 40)
    log_info(f"Mode: {mode.upper()}")
    
    # Check ADB connection
    if not check_adb_connection():
        return
    
    # Get device information
    if not get_device_info():
        return
    
    log_info("")
    log_success("Starting automation...")
    if mode == "unity":
        log_info("Make sure Umamusume Unity Cup is running on your device!")
    else:
        log_info("Make sure Umamusume is running on your device!")
    log_info("Press Ctrl+C to stop the automation.")
    log_info("=" * 40)
    
    try:
        ui_check(startup=True)  # First call — stop bot if UI is unrecognized
        while True:
            ui_check()
    except KeyboardInterrupt:
        log_info("")
        log_warning("Automation stopped by user.")
    except Exception as e:
        log_info("")
        log_error("Automation error: " + str(e))

if __name__ == "__main__":
    main()
