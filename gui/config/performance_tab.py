"""
Performance Tab for Uma Musume Auto-Train Bot GUI Configuration

Contains screenshot capture method settings and performance-related options.
"""

import customtkinter as ctk
import tkinter as tk

try:
    from .base_tab import BaseTab
    from ..font_manager import get_font
except ImportError:
    from base_tab import BaseTab
    from font_manager import get_font

class PerformanceTab(BaseTab):
    """Performance configuration tab containing screenshot capture settings"""
    
    def __init__(self, tabview, config_panel, colors):
        """Initialize the Performance tab"""
        super().__init__(tabview, config_panel, colors, "Performance")
    
    def create_tab(self):
        """Create the Performance tab with screenshot capture settings"""
        # Add tab to tabview
        perf_tab = self.tabview.add("Performance")
        
        # Create scrollable content
        perf_scroll = self.create_scrollable_content(perf_tab)
        
        config = self.main_window.get_config()

        # Capture Method Section
        capture_frame, _ = self.create_section_frame(perf_scroll, "Screenshot Capture")

        # Method selector
        self.config_panel.capture_method_var = tk.StringVar(value=config.get('capture_method', 'auto'))
        self.add_variable_with_autosave('capture_method', self.config_panel.capture_method_var)
        _, method_combo = self.create_setting_row(capture_frame, "Method:", 'optionmenu', 
                                                 values=['auto', 'adb', 'nemu_ipc', 'ldopengl'], 
                                                 variable=self.config_panel.capture_method_var,
                                                 command=lambda _: self.config_panel.toggle_capture_settings())

        # Nemu IPC settings (hidden unless selected)
        self.config_panel.nemu_settings_frame = ctk.CTkFrame(capture_frame, fg_color=self.colors['bg_light'], corner_radius=10)
        nemu_cfg = config.get('nemu_ipc_config', {})
        # Fields
        nemu_folder_row = ctk.CTkFrame(self.config_panel.nemu_settings_frame, fg_color="transparent")
        nemu_folder_row.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(nemu_folder_row, text="MuMu/Nemu Folder:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.config_panel.nemu_folder_var = tk.StringVar(value=nemu_cfg.get('nemu_folder', 'J:\\MuMuPlayerGlobal'))
        self.add_variable_with_autosave('nemu_folder', self.config_panel.nemu_folder_var)
        ctk.CTkEntry(nemu_folder_row, textvariable=self.config_panel.nemu_folder_var, width=320, corner_radius=8, font=get_font('input')).pack(side=tk.RIGHT)

        instance_row = ctk.CTkFrame(self.config_panel.nemu_settings_frame, fg_color="transparent")
        instance_row.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(instance_row, text="Instance ID:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.config_panel.nemu_instance_var = tk.IntVar(value=nemu_cfg.get('instance_id', 2))
        self.add_variable_with_autosave('nemu_instance', self.config_panel.nemu_instance_var)
        ctk.CTkEntry(instance_row, textvariable=self.config_panel.nemu_instance_var, width=100, corner_radius=8, font=get_font('input')).pack(side=tk.RIGHT)

        display_row = ctk.CTkFrame(self.config_panel.nemu_settings_frame, fg_color="transparent")
        display_row.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(display_row, text="Display ID:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.config_panel.nemu_display_var = tk.IntVar(value=nemu_cfg.get('display_id', 0))
        self.add_variable_with_autosave('nemu_display', self.config_panel.nemu_display_var)
        ctk.CTkEntry(display_row, textvariable=self.config_panel.nemu_display_var, width=100, corner_radius=8, font=get_font('input')).pack(side=tk.RIGHT)

        timeout_row = ctk.CTkFrame(self.config_panel.nemu_settings_frame, fg_color="transparent")
        timeout_row.pack(fill=tk.X, padx=15, pady=(5, 15))
        ctk.CTkLabel(timeout_row, text="Timeout (s):", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.config_panel.nemu_timeout_var = tk.DoubleVar(value=nemu_cfg.get('timeout', 1.0))
        self.add_variable_with_autosave('nemu_timeout', self.config_panel.nemu_timeout_var)
        ctk.CTkEntry(timeout_row, textvariable=self.config_panel.nemu_timeout_var, width=100, corner_radius=8, font=get_font('input')).pack(side=tk.RIGHT)

        # LDOpenGL settings (hidden unless selected)
        self.config_panel.ldopengl_settings_frame = ctk.CTkFrame(capture_frame, fg_color=self.colors['bg_light'], corner_radius=10)
        ldopengl_cfg = config.get('ldopengl_config', {})
        # Fields
        ld_folder_row = ctk.CTkFrame(self.config_panel.ldopengl_settings_frame, fg_color="transparent")
        ld_folder_row.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(ld_folder_row, text="LDPlayer Folder:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.config_panel.ldopengl_folder_var = tk.StringVar(value=ldopengl_cfg.get('ld_folder', 'J:\\LDPlayer\\LDPlayer9'))
        self.add_variable_with_autosave('ldopengl_folder', self.config_panel.ldopengl_folder_var)
        ctk.CTkEntry(ld_folder_row, textvariable=self.config_panel.ldopengl_folder_var, width=320, corner_radius=8, font=get_font('input')).pack(side=tk.RIGHT)

        ld_instance_row = ctk.CTkFrame(self.config_panel.ldopengl_settings_frame, fg_color="transparent")
        ld_instance_row.pack(fill=tk.X, padx=15, pady=5)
        ctk.CTkLabel(ld_instance_row, text="Instance ID:", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.config_panel.ldopengl_instance_var = tk.IntVar(value=ldopengl_cfg.get('instance_id', 0))
        self.add_variable_with_autosave('ldopengl_instance', self.config_panel.ldopengl_instance_var)
        ctk.CTkEntry(ld_instance_row, textvariable=self.config_panel.ldopengl_instance_var, width=100, corner_radius=8, font=get_font('input')).pack(side=tk.RIGHT)

        ld_orientation_row = ctk.CTkFrame(self.config_panel.ldopengl_settings_frame, fg_color="transparent")
        ld_orientation_row.pack(fill=tk.X, padx=15, pady=(5, 15))
        ctk.CTkLabel(ld_orientation_row, text="Orientation (0=normal, 2=upside down):", text_color=self.colors['text_light'], font=get_font('label')).pack(side=tk.LEFT)
        self.config_panel.ldopengl_orientation_var = tk.IntVar(value=ldopengl_cfg.get('orientation', 0))
        self.add_variable_with_autosave('ldopengl_orientation', self.config_panel.ldopengl_orientation_var)
        ctk.CTkEntry(ld_orientation_row, textvariable=self.config_panel.ldopengl_orientation_var, width=100, corner_radius=8, font=get_font('input')).pack(side=tk.RIGHT)

        # Initial visibility
        self.config_panel.toggle_capture_settings()
        
        # Auto-save info label
        self.create_autosave_info_label(perf_scroll)
    
    def update_config(self, config):
        """Update the config dictionary with current values"""
        # Update capture method
        config['capture_method'] = self.config_panel.capture_method_var.get()
        
        # Update Nemu IPC config
        config['nemu_ipc_config'] = {
            'nemu_folder': self.config_panel.nemu_folder_var.get(),
            'instance_id': self.config_panel.nemu_instance_var.get(),
            'display_id': self.config_panel.nemu_display_var.get(),
            'timeout': self.config_panel.nemu_timeout_var.get()
        }
        
        # Update LDOpenGL config
        config['ldopengl_config'] = {
            'ld_folder': self.config_panel.ldopengl_folder_var.get(),
            'instance_id': self.config_panel.ldopengl_instance_var.get(),
            'orientation': self.config_panel.ldopengl_orientation_var.get()
        }
    
    def on_performance_setting_change(self, *args):
        """Called when any performance setting variable changes - auto-save"""
        self.on_setting_change(*args)
