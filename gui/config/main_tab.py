"""
Main Tab for Uma Musume Auto-Train Bot GUI Configuration

Contains ADB configuration and screenshot capture settings.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

try:
    from .base_tab import BaseTab
except ImportError:
    from base_tab import BaseTab

class MainTab(BaseTab):
    """Main configuration tab containing ADB and capture settings"""
    
    # Mode display labels mapping
    MODE_DISPLAY_LABELS = {
        "ura": "URA Finale",
        "unity": "Unity Cup"
    }
    MODE_VALUES = {
        "URA Finale": "ura",
        "Unity Cup": "unity"
    }
    
    def __init__(self, tabview, config_panel, colors):
        """Initialize the Main tab"""
        super().__init__(tabview, config_panel, colors, "Main")
    
    def create_tab(self):
        """Create the Main tab with ADB configuration"""
        # Add tab to tabview
        main_tab = self.tabview.add("Main")
        
        # Create scrollable content
        main_scroll = self.create_scrollable_content(main_tab)
        
        config = self.main_window.get_config()

        # Mode Configuration Section
        mode_frame, _ = self.create_section_frame(main_scroll, "Mode Configuration")
        
        # Mode selector with display labels
        mode_value = config.get('mode', 'ura')
        mode_display = self.MODE_DISPLAY_LABELS.get(mode_value, "URA Finale")
        self.config_panel.mode_var = tk.StringVar(value=mode_display)
        # Store actual mode value separately for saving
        self.config_panel._mode_actual_value = mode_value
        self.add_variable_with_autosave('mode', self.config_panel.mode_var)
        _, mode_combo = self.create_setting_row(mode_frame, "Mode:", 'optionmenu', 
                                               values=['URA Finale', 'Unity Cup'], 
                                               variable=self.config_panel.mode_var,
                                               command=lambda _: self.on_mode_change())

        # ADB Configuration Section
        adb_frame, _ = self.create_section_frame(main_scroll, "ADB Configuration")

        # Device/Emulator Type (detected at launch)
        emulator_types = getattr(self.config_panel.main_window, 'detected_emulator_types', []) or []
        if not emulator_types:
            # Fallback: try detecting now
            try:
                from utils.emulator_detect import list_emulator_types
                emulator_types = list_emulator_types()
                self.config_panel.main_window.detected_emulator_types = emulator_types
            except Exception:
                emulator_types = []
        # Add "Phone" option to the list
        if 'Phone' not in emulator_types:
            emulator_types = emulator_types + ['Phone']
        self.config_panel.emulator_type_var = tk.StringVar(value=config.get('emulator_type', ''))
        self.add_variable_with_autosave('emulator_type', self.config_panel.emulator_type_var)
        values = emulator_types if emulator_types else ['']
        _, emu_type_combo = self.create_setting_row(
            adb_frame,
            "Device/Emulator Type:",
            'optionmenu',
            values=values,
            variable=self.config_panel.emulator_type_var,
            command=lambda _: self.on_device_type_change()
        )
        
        # Device Address
        self.config_panel.device_address_var = tk.StringVar(value=config.get('adb_config', {}).get('device_address', '127.0.0.1:7555'))
        self.add_variable_with_autosave('device_address', self.config_panel.device_address_var)
        _, device_entry = self.create_setting_row(adb_frame, "Device Address:", 'entry', textvariable=self.config_panel.device_address_var, width=200)
        
        # ADB Path
        self.config_panel.adb_path_var = tk.StringVar(value=config.get('adb_config', {}).get('adb_path', 'adb'))
        self.add_variable_with_autosave('adb_path', self.config_panel.adb_path_var)
        _, adb_path_entry = self.create_setting_row(adb_frame, "ADB Path:", 'entry', textvariable=self.config_panel.adb_path_var, width=200)
        
        # Advanced ADB settings (hidden from GUI, kept in config with defaults)
        # Screenshot Timeout
        self.config_panel.screenshot_timeout_var = tk.IntVar(value=config.get('adb_config', {}).get('screenshot_timeout', 5))
        # Input Delay
        self.config_panel.input_delay_var = tk.DoubleVar(value=config.get('adb_config', {}).get('input_delay', 0.0))
        # Connection Timeout
        self.config_panel.connection_timeout_var = tk.IntVar(value=config.get('adb_config', {}).get('connection_timeout', 10))

        # Auto-save info label
        self.create_autosave_info_label(main_scroll)
    
    def update_config(self, config):
        """Update the config dictionary with current values"""
        # Update ADB config
        config['adb_config'] = {
            'device_address': self.config_panel.device_address_var.get(),
            'adb_path': self.config_panel.adb_path_var.get(),
            'screenshot_timeout': self.config_panel.screenshot_timeout_var.get(),
            'input_delay': self.config_panel.input_delay_var.get(),
            'connection_timeout': self.config_panel.connection_timeout_var.get()
        }

        # Emulator type
        config['emulator_type'] = self.config_panel.emulator_type_var.get()
        
        # Update mode (convert display label to actual value)
        mode_display = self.config_panel.mode_var.get()
        mode_value = self.MODE_VALUES.get(mode_display, 'ura')
        config['mode'] = mode_value
        # Update stored actual value
        self.config_panel._mode_actual_value = mode_value
    
    def on_mode_change(self):
        """Handle mode change - update training tab visibility"""
        # Skip during initialization
        if getattr(self, '_initializing', False):
            return
        
        # Convert display label to actual value
        mode_display = self.config_panel.mode_var.get()
        mode_value = self.MODE_VALUES.get(mode_display, 'ura')
        self.config_panel._mode_actual_value = mode_value
        
        # Update config first
        try:
            config = self.main_window.get_config()
            self.update_config(config)
            self.main_window.set_config(config)
        except Exception as e:
            print(f"Error updating mode: {e}")
        
        # Notify training tab to update visibility
        training_tab = self.config_panel.get_tab('training')
        if training_tab and hasattr(training_tab, 'update_unity_fields_visibility'):
            training_tab.update_unity_fields_visibility()
    
    def on_device_type_change(self):
        """Handle device/emulator type change - show warning for Phone option"""
        device_type = self.config_panel.emulator_type_var.get()
        
        if device_type == 'Phone':
            messagebox.showinfo(
                "Phone Device Notice",
                "When using a Phone device:\n\n"
                "• Auto address detection won't work.\n"
                "• You need to manually enter the ADB address.\n"
                "• The device must have a resolution of 1080x1920 (Portrait).\n\n"
                "Please ensure your phone is in portrait mode and "
                "USB debugging is enabled."
            )
