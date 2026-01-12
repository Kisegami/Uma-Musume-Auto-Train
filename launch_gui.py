"""
GUI Launcher for Uma Musume Auto-Train Bot (PySide6)

This script launches the PySide6 GUI application from the root directory.
Simply run this file to start the new dark-themed GUI.

Usage:
    python launch_gui.py
    or
    python3 launch_gui.py
"""

import sys
import os
import json
import shutil
from pathlib import Path
from copy import deepcopy

# Add script's directory to Python path (for embeddable Python compatibility)
# This ensures utils/ and other modules can be found regardless of how Python is invoked
# Handle case where __file__ might not be defined (e.g., when executed via exec)
if '__file__' in globals():
    script_dir = os.path.dirname(os.path.abspath(__file__))
else:
    # Fallback: use current working directory or sys.argv[0] if available
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv else os.getcwd()
if script_dir and script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils.log import log_info, log_warning, log_error, log_debug, log_success
from utils.emulator_detect import list_emulator_types


def check_config_file(config_file: str, example_file: str) -> dict:
    """Check and create a config file if needed, merge missing keys from example"""
    config_path = Path(config_file)
    example_path = Path(example_file)
    
    result = {"file": config_file, "created": False, "updated": False, "error": None}
    
    if config_path.exists():
        # File exists, check if we need to merge missing keys
        if example_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    existing_config = json.load(f)
                with open(example_path, 'r', encoding='utf-8') as f:
                    example_config = json.load(f)
                
                # Deep merge function
                def deep_merge(existing_dict, example_dict):
                    merged = deepcopy(existing_dict)
                    for key, example_value in example_dict.items():
                        if key not in merged:
                            merged[key] = deepcopy(example_value)
                        elif isinstance(merged[key], dict) and isinstance(example_value, dict):
                            merged[key] = deep_merge(merged[key], example_value)
                    return merged
                
                merged_config = deep_merge(existing_config, example_config)
                
                if merged_config != existing_config:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(merged_config, f, indent=2, ensure_ascii=False)
                    result["updated"] = True
                    print(f"✓ Updated {config_file} with missing keys from {example_file}")
            except Exception as e:
                result["error"] = str(e)
                print(f"⚠ Error merging {config_file}: {e}")
    else:
        # Config doesn't exist, create from example
        if example_path.exists():
            try:
                shutil.copy2(example_path, config_path)
                result["created"] = True
                print(f"✓ Created {config_file} from {example_file}")
            except Exception as e:
                result["error"] = str(e)
                print(f"⚠ Failed to create {config_file}: {e}")
        else:
            result["error"] = f"Example file {example_file} not found"
            print(f"⚠ {result['error']}")
    
    return result


def check_all_configs():
    """Check all required configuration files"""
    config_files = {
        "config.json": "config.example.json",
        "training_score.json": "training_score.example.json",
        "training_score_unity.json": "training_score_unity.example.json",
        "event_priority.json": "event_priority.example.json",
    }
    
    results = {"created": 0, "updated": 0, "errors": 0, "ok": 0}
    
    for config_file, example_file in config_files.items():
        result = check_config_file(config_file, example_file)
        if result["created"]:
            results["created"] += 1
        elif result["updated"]:
            results["updated"] += 1
        elif result["error"]:
            results["errors"] += 1
        else:
            results["ok"] += 1
    
    return results


def main():
    """Main entry point for PySide6 GUI"""
    print("Uma Musume Auto-Train Bot - PySide6 GUI")
    print("=" * 50)
    
    # Check main configuration files
    try:
        print("Checking configuration files...")
        config_results = check_all_configs()
        if config_results["created"]:
            print(f"✓ Created {config_results['created']} new configuration file(s)")
        if config_results["updated"]:
            print(f"✓ Updated {config_results['updated']} configuration file(s) with missing keys")
        if config_results["errors"]:
            print(f"⚠ {config_results['errors']} error(s) during config check")
        if config_results["ok"] == 4:
            print("✓ All configuration files OK")
    except Exception as e:
        log_warning(f"Could not check configuration files: {e}")
        print("GUI will continue without automatic config file creation.")
    
    # Detect emulator types up front and pass via environment
    try:
        detected_types = list_emulator_types()
        os.environ["UMA_DETECTED_EMULATOR_TYPES"] = json.dumps(detected_types)
        print(f"Detected emulator types: {detected_types}")
    except Exception as e:
        print(f"Warning: Emulator detection failed: {e}")
        os.environ.pop("UMA_DETECTED_EMULATOR_TYPES", None)
    
    # Check for PySide6
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        print("[OK] PySide6 found")
    except ImportError:
        print("[!] PySide6 not found. Installing...")
        os.system(f"{sys.executable} -m pip install PySide6")
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
    
    # Import main window
    from gui.main_window import MainWindow
    
    # Create application
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set application info
    app.setApplicationName("Uma Musume Auto-Train")
    app.setApplicationVersion("2.0")
    
    # Note: High DPI scaling is enabled by default in Qt6/PySide6
    
    print("[OK] Application initialized")
    print("=" * 50)
    print()
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
