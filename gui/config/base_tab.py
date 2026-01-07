"""
Base Tab for Uma Musume Auto-Train Bot GUI Configuration

Provides common functionality for all configuration tabs to reduce code duplication.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

try:
    from ..font_manager import get_font
except ImportError:
    from font_manager import get_font

# Make get_font available globally for all tabs
import builtins
builtins.get_font = get_font


class BaseTab:
    """Base class for all configuration tabs with common functionality"""
    
    def __init__(self, tabview, config_panel, colors, tab_name):
        """Initialize the base tab
        
        Args:
            tabview: The parent CTkTabview widget
            config_panel: Reference to the main ConfigPanel instance
            colors: Color scheme dictionary
            tab_name: Name of the tab for display
        """
        self.tabview = tabview
        self.config_panel = config_panel
        self.colors = colors
        self.main_window = config_panel.main_window
        self.tab_name = tab_name
        
        # Initialize variables dictionary for auto-save tracking
        self.variables = {}
        
        # Flag to prevent auto-save during initialization
        self._initializing = True
        
        # Create the tab
        self.create_tab()
        
        # Enable auto-save after initialization is complete
        self._initializing = False
    
    def create_tab(self):
        """Create the tab - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement create_tab()")
    
    def add_variable_with_autosave(self, name, variable, callback_name=None):
        """Add a variable with auto-save callback (debounced to prevent excessive saves)
        
        Args:
            name: Name/key for the variable
            variable: The tkinter variable
            callback_name: Optional specific callback method name (defaults to on_setting_change)
        """
        self.variables[name] = variable
        callback = callback_name or 'on_setting_change'
        if hasattr(self, callback):
            # Create debounced callback to prevent excessive updates while typing
            debounce_attr = f'_debounce_timer_{name}'
            
            def debounced_callback(*args):
                # Cancel any pending callback
                if hasattr(self, debounce_attr):
                    try:
                        self.config_panel.after_cancel(getattr(self, debounce_attr))
                    except:
                        pass
                # Schedule new callback after 300ms delay
                timer = self.config_panel.after(300, lambda: getattr(self, callback)(*args))
                setattr(self, debounce_attr, timer)
            
            variable.trace('w', debounced_callback)
    
    def create_section_frame(self, parent, title, pack_kwargs=None):
        """Create a standardized section frame with title
        
        Args:
            parent: Parent widget
            title: Section title
            pack_kwargs: Optional pack configuration
            
        Returns:
            Tuple of (frame, title_label)
        """
        if pack_kwargs is None:
            pack_kwargs = {'fill': tk.X, 'pady': 10, 'padx': 10}
            
        frame = ctk.CTkFrame(parent, fg_color=self.colors['bg_light'], corner_radius=10)
        frame.pack(**pack_kwargs)
        
        title_label = ctk.CTkLabel(frame, text=title, font=get_font('section_title'), 
                                  text_color=self.colors['text_light'])
        title_label.pack(pady=(15, 10))
        
        return frame, title_label
    
    def create_setting_row(self, parent, label_text, widget_type='entry', **widget_kwargs):
        """Create a standardized setting row with label and input widget
        
        Args:
            parent: Parent widget
            label_text: Text for the label
            widget_type: Type of widget ('entry', 'checkbox', 'optionmenu')
            **widget_kwargs: Additional arguments for the widget
            
        Returns:
            Tuple of (row_frame, widget)
        """
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.pack(fill=tk.X, padx=15, pady=5)
        
        label = ctk.CTkLabel(row_frame, text=label_text, text_color=self.colors['text_light'], 
                           font=get_font('label'))
        label.pack(side=tk.LEFT)
        
        if widget_type == 'entry':
            widget = ctk.CTkEntry(row_frame, corner_radius=8, **widget_kwargs)
            widget.pack(side=tk.RIGHT)
        elif widget_type == 'checkbox':
            widget = ctk.CTkCheckBox(row_frame, text="", text_color=self.colors['text_light'],
                                   font=get_font('checkbox'), **widget_kwargs)
            widget.pack(side=tk.RIGHT)
        elif widget_type == 'optionmenu':
            widget = ctk.CTkOptionMenu(row_frame, fg_color=self.colors['accent_blue'], 
                                     corner_radius=8, button_color=self.colors['accent_blue'],
                                     button_hover_color=self.colors['accent_green'],
                                     font=get_font('dropdown'), **widget_kwargs)
            widget.pack(side=tk.RIGHT)
        else:
            raise ValueError(f"Unsupported widget_type: {widget_type}")
            
        return row_frame, widget
    
    def create_autosave_info_label(self, parent, pack_kwargs=None):
        """Create the standard auto-save info label
        
        Args:
            parent: Parent widget
            pack_kwargs: Optional pack configuration
            
        Returns:
            The info label widget
        """
        if pack_kwargs is None:
            pack_kwargs = {'pady': 20}
            
        info_label = ctk.CTkLabel(parent, text="✓ All changes are automatically saved", 
                                 text_color=self.colors['accent_green'], font=get_font('body_medium'))
        info_label.pack(**pack_kwargs)
        return info_label
    
    def on_setting_change(self, *args):
        """Default auto-save callback - to be overridden by subclasses"""
        # Skip auto-save during initialization
        if getattr(self, '_initializing', False):
            return
        # Skip when bot is running to avoid clobbering auto-detected values
        if getattr(self.main_window, "bot_running", False):
            return
            
        try:
            config = self.main_window.get_config()
            self.update_config(config)
            self.main_window.set_config(config)
        except Exception as e:
            print(f"Error auto-saving {self.tab_name} settings: {e}")
    
    def update_config(self, config):
        """Update the config dictionary with current values - to be implemented by subclasses
        
        Args:
            config: The configuration dictionary to update
        """
        raise NotImplementedError("Subclasses must implement update_config()")
    
    def create_scrollable_content(self, tab_widget):
        """Create a standard scrollable frame for tab content
        
        Args:
            tab_widget: The tab widget to add scrollable content to
            
        Returns:
            The scrollable frame
        """
        scroll_frame = ctk.CTkScrollableFrame(tab_widget, fg_color="transparent", corner_radius=0)
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        return scroll_frame
    
    def show_error(self, title, message):
        """Show a standardized error message
        
        Args:
            title: Error dialog title
            message: Error message
        """
        messagebox.showerror(title, message)
    
    def show_success(self, message):
        """Show a standardized success message
        
        Args:
            message: Success message
        """
        messagebox.showinfo("Success", message)
