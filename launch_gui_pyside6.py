"""
PySide6 GUI Launcher for Uma Musume Auto-Train Bot
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Main entry point for PySide6 GUI"""
    print("Uma Musume Auto-Train Bot - PySide6 GUI")
    print("=" * 50)
    
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
    from gui_pyside6.main_window import MainWindow
    
    # Create application
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set application info
    app.setApplicationName("Uma Musume Auto-Train")
    app.setApplicationVersion("2.0")
    
    # Enable high DPI scaling
    try:
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except AttributeError:
        pass  # Already enabled in Qt6
    
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
