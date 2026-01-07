import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import json
import os
from datetime import datetime

try:
    from .config_panel import ConfigPanel
    from .status_panel import StatusPanel
    from .log_panel import LogPanel
    from .bot_controller import BotController
except ImportError:
    from config_panel import ConfigPanel
    from status_panel import StatusPanel
    from log_panel import LogPanel
    from bot_controller import BotController

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Uma Musume Auto Train")
        
        # Calculate responsive geometry based on screen size
        self._set_responsive_geometry()
        
        self.set_app_icon()

        # Set customtkinter appearance mode and color theme
        ctk.set_appearance_mode("dark")  # "dark" or "light"
        ctk.set_default_color_theme("dark-blue")  # "blue", "green", "dark-blue"


        # Modern color scheme
        self.colors = {
            'bg_dark': '#212121',
            'bg_medium': '#2b2b2b',
            'bg_light': '#3c3c3c',
            'text_light': '#ffffff',
            'text_gray': '#b0b0b0',
            'accent_blue': '#1f538d',
            'accent_green': '#2d5a27',
            'accent_red': '#8b2635',
            'accent_yellow': '#8b6914',
            'border': '#3c3c3c'
        }

        # Configure root window
        self.root.configure(bg=self.colors['bg_dark'])
        
        # Bot control variables
        self.bot_running = False
        self.config_file = "config.json"
        
        # Auto-save configuration
        self.auto_save_enabled = True
        self.auto_save_delay = 1000  # 1 second delay after last change
        self.auto_save_timer = None
        
        # Load configuration
        self.load_config()
        # Detect emulator types available on this machine (prefer injected from launcher)
        env_detect = os.environ.get("UMA_DETECTED_EMULATOR_TYPES")
        if env_detect:
            try:
                self.detected_emulator_types = json.loads(env_detect)
            except Exception:
                self.detected_emulator_types = []
        else:
            try:
                from utils.emulator_detect import list_emulator_types
                self.detected_emulator_types = list_emulator_types()
                try:
                    self.add_log(f"Detected emulator types: {self.detected_emulator_types}", "info")
                except Exception:
                    pass
            except Exception:
                self.detected_emulator_types = []

        # Create GUI components
        self.create_widgets()
        
        # Initialize bot controller
        self.bot_controller = BotController(self)

    def create_widgets(self):
        """Create the main layout with three main panels using modern customtkinter"""
        # Main container with dark background
        main_frame = ctk.CTkFrame(self.root, fg_color=self.colors['bg_dark'], corner_radius=0)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Configure grid layout
        main_frame.grid_columnconfigure(0, weight=5, minsize=800)  # Left column - give much more space to config + status
        main_frame.grid_columnconfigure(1, weight=2, minsize=200, pad=0)  # Right column - significantly reduce log panel size
        main_frame.grid_rowconfigure(0, weight=1)
        
        # Left side container - Config and Status
        left_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left_frame.grid_columnconfigure(0, weight=1, minsize=800)  # Force minimum width
        left_frame.grid_rowconfigure(0, weight=2)  # Config takes more space
        left_frame.grid_rowconfigure(1, weight=1)  # Status takes less space
        
        # Top left - Config Panel (Beautiful rounded rectangle)
        self.config_panel = ConfigPanel(left_frame, self, self.colors)
        self.config_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 15))
        
        # Bottom left - Status Panel (Beautiful rounded rectangle)
        self.status_panel = StatusPanel(left_frame, self, self.colors)
        self.status_panel.grid(row=1, column=0, sticky="nsew")
        
        # Right side - Log Panel (Beautiful rounded rectangle)
        self.log_panel = LogPanel(main_frame, self, self.colors)
        self.log_panel.grid(row=0, column=1, sticky="nsew")
        
        # Add initial log message
        self.add_log("Modern GUI initialized successfully")
        self.add_log(f"Configuration loaded from: {self.config_file}")
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                # Load example config if main config doesn't exist
                if os.path.exists('config.example.json'):
                    with open('config.example.json', 'r', encoding='utf-8') as f:
                        self.config = json.load(f)
                    # Save as main config
                    self.save_config()
                else:
                    self.config = self.get_default_config()
                    self.save_config()
        except Exception as e:
            self.add_log(f"Error loading config: {e}")
            self.config = self.get_default_config()
    
    def get_default_config(self):
        """Get default configuration"""
        return {
            "capture_method": "auto",
            "emulator_type": "",
            "adb_config": {
                "device_address": "127.0.0.1:7555",
                "adb_path": "adb",
                "screenshot_timeout": 5,
                "input_delay": 0.5,
                "connection_timeout": 10
            },
            "nemu_ipc_config": {
                "nemu_folder": "J:\\MuMuPlayerGlobal",
                "instance_id": 2,
                "display_id": 0,
                "timeout": 1.0
            },
            "ldopengl_config": {
                "ld_folder": "J:\\LDPlayer\\LDPlayer9",
                "instance_id": 0,
                "orientation": 0
            },
            "training": {
                "priority_stat": ["spd", "sta", "wit", "pwr", "guts"],
                "minimum_mood": "GREAT",
                "maximum_failure": 15,
                "min_energy": 30,
                "min_score": {
                    "spd": 1.0,
                    "sta": 1.0,
                    "pwr": 1.0,
                    "guts": 1.0,
                    "wit": 1.0
                },
                "do_race_when_bad_training": False,
                "stat_caps": {
                    "spd": 1100,
                    "sta": 1100,
                    "pwr": 600,
                    "guts": 600,
                    "wit": 600
                }
            },
            "racing": {
                "strategy": "FRONT",
                "retry_race": True,
                "allowed_grades": ["G1", "G2"],
                "allowed_tracks": ["Turf"],
                "allowed_distances": ["Medium", "Long"],
                "do_custom_race": True,
                "custom_race_file": "template/races/custom_races.json"
            },
            "skills": {
                "skill_point_cap": 400,
                "skill_purchase": "auto",
                "skill_file": "template/skills/skills.json",
                "enable_skill_point_check": True
            },
            "restart_career": {
                "restart_enabled": True,
                "restart_times": 2,
                "total_fans_requirement": 0
            },
            "auto_start_career": {
                "include_guests_legacy": False,
                "support_speciality": "STA",
                "support_rarity": "SSR",
                "auto_charge_tp": True
            },
            "debug_mode": False,
            "stop_on_event_detection_failure": False
        }
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            self.add_log(f"Configuration saved to {self.config_file}")
        except Exception as e:
            self.add_log(f"Error saving config: {e}")
    
    def schedule_auto_save(self):
        """Schedule an auto-save after a delay"""
        if not self.auto_save_enabled:
            return
            
        # Cancel any existing timer
        if self.auto_save_timer:
            self.root.after_cancel(self.auto_save_timer)
        
        # Schedule new auto-save
        self.auto_save_timer = self.root.after(self.auto_save_delay, self.auto_save)
    
    def auto_save(self):
        """Perform automatic save without showing success message"""
        # If bot is running and auto-detect just set values, avoid overwriting until it syncs.
        try:
            if getattr(self, "bot_running", False):
                return
        except Exception:
            pass
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            self.add_log("Configuration auto-saved", "info")
        except Exception as e:
            self.add_log(f"Error auto-saving config: {e}", "error")
        finally:
            self.auto_save_timer = None
    

    

    

    
    def update_status(self, year, energy, turn, mood, goal_met, stats):
        """Update the status panel with real-time data"""
        self.status_panel.update_status(year, energy, turn, mood, goal_met, stats)
    
    def start_bot(self):
        """Start the bot automation"""
        if hasattr(self, 'bot_controller'):
            self.bot_controller.start_bot()
            self.bot_running = True
            # Update log panel button
            if hasattr(self, 'log_panel'):
                self.log_panel.update_start_stop_button(True)
    
    def stop_bot(self):
        """Stop the bot automation"""
        if hasattr(self, 'bot_controller'):
            self.bot_controller.stop_bot()
            self.bot_running = False
            # Update log panel button
            if hasattr(self, 'log_panel'):
                self.log_panel.update_start_stop_button(False)
    
    def add_log(self, message, level="info"):
        """Add a log message to the queue"""
        if hasattr(self, 'log_panel'):
            self.log_panel.add_log_entry(message, level)
    
    def get_config(self):
        """Get current configuration"""
        return self.config
    
    def set_config(self, new_config):
        """Update configuration"""
        self.config = new_config
        self.schedule_auto_save()
        self.config_panel.refresh_config()
    
    def update_config_value(self, key, value):
        """Update a single configuration value and trigger auto-save"""
        self.config[key] = value
        self.schedule_auto_save()
    
    def update_nested_config_value(self, parent_key, child_key, value):
        """Update a nested configuration value and trigger auto-save"""
        if parent_key not in self.config:
            self.config[parent_key] = {}
        self.config[parent_key][child_key] = value
        self.schedule_auto_save()

    def _set_responsive_geometry(self):
        """Calculate and set responsive window size based on screen dimensions"""
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate window size: 60% width, 70% height
        width = int(screen_width * 0.6)
        height = int(screen_height * 0.7)
        
        # Apply minimum bounds to ensure usability
        min_width = 900
        min_height = 600
        width = max(width, min_width)
        height = max(height, min_height)
        
        # Apply maximum bounds to prevent oversized windows
        max_width = 1800
        max_height = 1200
        width = min(width, max_width)
        height = min(height, max_height)
        
        # Set geometry and minimum size
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(min_width, min_height)

    def set_app_icon(self):
        """Attempt to set a custom window icon if provided"""
        # Look for user-provided icon files under assets/icons
        gui_dir = os.path.normpath(os.path.dirname(__file__))
        base_dir = os.path.normpath(os.path.join(gui_dir, ".."))
        icon_candidates = [
            os.path.join(gui_dir, "app.ico"),  # allow drop-in next to main_window
            os.path.join(gui_dir, "app.png"),
        ]

        for icon_path in icon_candidates:
            if not os.path.exists(icon_path):
                continue
            try:
                if icon_path.lower().endswith(".ico"):
                    self.root.iconbitmap(icon_path)
                else:
                    # Keep a reference so the image is not garbage-collected
                    self._icon_image_ref = tk.PhotoImage(file=icon_path)
                    self.root.iconphoto(False, self._icon_image_ref)
                break
            except Exception as e:
                print(f"Warning: Could not set app icon: {e}")

def main():
    """Main function to run the modern GUI"""
    root = ctk.CTk()
    root.title("Uma Musume Auto Train")
    app = MainWindow(root)
    
    # Handle window close
    def on_closing():
        if app.bot_running:
            if messagebox.askokcancel("Quit", "Bot is running. Do you want to stop it and quit?"):
                app.stop_bot()
                root.destroy()
            else:
                return
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Center window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    root.mainloop()

if __name__ == "__main__":
    main()
