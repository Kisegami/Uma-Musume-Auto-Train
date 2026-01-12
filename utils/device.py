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


