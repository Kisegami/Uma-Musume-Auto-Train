"""
Font Manager for Uma Musume Auto-Train Bot GUI

This module provides centralized font management for all GUI components.
Fonts are loaded from font_config.json and can be easily customized.
"""

import json
import os
import customtkinter as ctk
from typing import Dict, Tuple, Optional

class FontManager:
    """Manages fonts for the entire GUI application"""
    
    def __init__(self, config_file: str = "font_config.json"):
        """Initialize the font manager
        
        Args:
            config_file: Path to the font configuration JSON file
        """
        self.config_file = config_file
        self.fonts = {}
        self.fallback_fonts = {}
        self._font_cache = {}  # Cache for CTkFont objects to avoid recreation
        self._scale_factor = 1.0  # Will be calculated based on screen DPI
        self.load_font_config()
    
    def calculate_scale_factor(self, root_window=None):
        """Calculate font scale factor based on screen DPI
        
        Args:
            root_window: Optional tkinter root window for DPI detection
            
        The scale factor is calculated relative to 96 DPI (standard for 1080p).
        """
        try:
            import tkinter as tk
            if root_window is None:
                # Create temporary window for DPI detection
                temp_root = tk.Tk()
                temp_root.withdraw()
                dpi = temp_root.winfo_fpixels('1i')
                screen_width = temp_root.winfo_screenwidth()
                screen_height = temp_root.winfo_screenheight()
                temp_root.destroy()
            else:
                dpi = root_window.winfo_fpixels('1i')
                screen_width = root_window.winfo_screenwidth()
                screen_height = root_window.winfo_screenheight()
            
            # Base reference: 96 DPI at 1920x1080
            # Scale based on both DPI and resolution
            base_dpi = 96.0
            base_width = 1920
            
            # Calculate scale factor
            # Primary scaling is DPI-based
            dpi_scale = dpi / base_dpi
            
            # Secondary scaling considers screen width for very high resolutions
            # This helps with 4K displays where DPI might not fully reflect size needs
            resolution_scale = min(screen_width / base_width, 1.5)  # Cap at 1.5x
            
            # Combine scales with DPI being dominant
            self._scale_factor = (dpi_scale * 0.7 + resolution_scale * 0.3)
            
            # Clamp scale factor to reasonable bounds
            self._scale_factor = max(0.75, min(self._scale_factor, 2.0))
            
            print(f"✓ Screen: {screen_width}x{screen_height}, DPI: {dpi:.1f}, Font scale: {self._scale_factor:.2f}")
            
        except Exception as e:
            print(f"⚠ Could not calculate DPI scale: {e}, using 1.0")
            self._scale_factor = 1.0
        
        # Clear font cache to regenerate with new scale
        self._font_cache.clear()
        
    def load_font_config(self):
        """Load font configuration from JSON file"""
        config_path = os.path.join(os.path.dirname(__file__), self.config_file)
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            self.fonts = config.get('fonts', {})
            self.fallback_fonts = config.get('fallback_fonts', {})
            
            print(f"✓ Loaded font configuration from {config_path}")
            print(f"✓ Loaded {len(self.fonts)} font definitions")
            
        except FileNotFoundError:
            print(f"⚠ Font config file not found: {config_path}")
            print("⚠ Using default fonts")
            self._load_default_fonts()
        except json.JSONDecodeError as e:
            print(f"⚠ Error parsing font config: {e}")
            print("⚠ Using default fonts")
            self._load_default_fonts()
        except Exception as e:
            print(f"⚠ Error loading font config: {e}")
            print("⚠ Using default fonts")
            self._load_default_fonts()
    
    def _load_default_fonts(self):
        """Load default font configuration as fallback"""
        self.fonts = {
            'title_large': {'family': 'Comic Sans MS', 'size': 18, 'weight': 'bold'},
            'title_medium': {'family': 'Comic Sans MS', 'size': 16, 'weight': 'bold'},
            'title_small': {'family': 'Comic Sans MS', 'size': 14, 'weight': 'bold'},
            'body_large': {'family': 'Comic Sans MS', 'size': 12, 'weight': 'normal'},
            'body_medium': {'family': 'Comic Sans MS', 'size': 11, 'weight': 'normal'},
            'body_small': {'family': 'Comic Sans MS', 'size': 10, 'weight': 'normal'},
            'monospace_large': {'family': 'Consolas', 'size': 18, 'weight': 'normal'},
            'monospace_medium': {'family': 'Consolas', 'size': 14, 'weight': 'normal'},
            'monospace_small': {'family': 'Consolas', 'size': 12, 'weight': 'normal'},
            'button': {'family': 'Comic Sans MS', 'size': 11, 'weight': 'bold'},
            'label': {'family': 'Comic Sans MS', 'size': 14, 'weight': 'normal'},
            'input': {'family': 'Comic Sans MS', 'size': 11, 'weight': 'normal'},
            'section_title': {'family': 'Comic Sans MS', 'size': 14, 'weight': 'bold'},
            'tab_title': {'family': 'Comic Sans MS', 'size': 16, 'weight': 'bold'},
            'status_title': {'family': 'Comic Sans MS', 'size': 16, 'weight': 'bold'},
            'status_value': {'family': 'Comic Sans MS', 'size': 14, 'weight': 'bold'},
            'status_label': {'family': 'Comic Sans MS', 'size': 10, 'weight': 'normal'},
            'log_text': {'family': 'Consolas', 'size': 18, 'weight': 'normal'},
            'dropdown': {'family': 'Comic Sans MS', 'size': 11, 'weight': 'normal'},
            'checkbox': {'family': 'Comic Sans MS', 'size': 10, 'weight': 'normal'},
            'radiobutton': {'family': 'Comic Sans MS', 'size': 10, 'weight': 'normal'},
            'tooltip': {'family': 'Comic Sans MS', 'size': 9, 'weight': 'normal'}
        }
        
        self.fallback_fonts = {
            'sans_serif': ['Comic Sans MS', 'Segoe UI', 'Arial', 'Helvetica', 'sans-serif'],
            'monospace': ['Consolas', 'Courier New', 'Monaco', 'monospace']
        }
    
    def get_font(self, font_name: str) -> ctk.CTkFont:
        """Get a CTkFont object for the specified font name
        
        Args:
            font_name: Name of the font (e.g., 'title_large', 'button', etc.)
            
        Returns:
            CTkFont object configured with the specified font
        """
        if font_name not in self.fonts:
            print(f"⚠ Font '{font_name}' not found, using 'body_medium' as fallback")
            font_name = 'body_medium'
        
        # Return cached font if available
        if font_name in self._font_cache:
            return self._font_cache[font_name]
            
        font_config = self.fonts[font_name]
        
        # Apply scale factor to size
        base_size = font_config.get('size', 11)
        scaled_size = int(round(base_size * self._scale_factor))
        
        # Ensure minimum readable size
        scaled_size = max(scaled_size, 8)
        
        # Create and cache new font
        font = ctk.CTkFont(
            family=font_config.get('family', 'Comic Sans MS'),
            size=scaled_size,
            weight=font_config.get('weight', 'normal')
        )
        self._font_cache[font_name] = font
        return font
    
    def get_font_tuple(self, font_name: str) -> Tuple[str, int, str]:
        """Get font as tuple (family, size, weight) for tkinter widgets
        
        Args:
            font_name: Name of the font
            
        Returns:
            Tuple of (family, size, weight)
        """
        if font_name not in self.fonts:
            print(f"⚠ Font '{font_name}' not found, using 'body_medium' as fallback")
            font_name = 'body_medium'
            
        font_config = self.fonts[font_name]
        
        # Apply scale factor to size
        base_size = font_config.get('size', 11)
        scaled_size = int(round(base_size * self._scale_factor))
        scaled_size = max(scaled_size, 8)
        
        return (
            font_config.get('family', 'Comic Sans MS'),
            scaled_size,
            font_config.get('weight', 'normal')
        )
    
    def get_font_dict(self, font_name: str) -> Dict[str, any]:
        """Get font configuration as dictionary
        
        Args:
            font_name: Name of the font
            
        Returns:
            Dictionary with font configuration
        """
        if font_name not in self.fonts:
            print(f"⚠ Font '{font_name}' not found, using 'body_medium' as fallback")
            font_name = 'body_medium'
            
        return self.fonts[font_name].copy()
    
    def list_available_fonts(self) -> list:
        """Get list of all available font names"""
        return list(self.fonts.keys())
    
    def reload_config(self):
        """Reload font configuration from file"""
        self._font_cache.clear()  # Clear cache on reload
        self.load_font_config()
        print("✓ Font configuration reloaded")
    
    def save_config(self, new_config: dict):
        """Save new font configuration to file
        
        Args:
            new_config: New font configuration dictionary
        """
        config_path = os.path.join(os.path.dirname(__file__), self.config_file)
        
        try:
            config = {
                "_description": "Font configuration for Uma Musume Auto-Train Bot GUI",
                "_instructions": "Change font families, sizes, and weights here. All GUI elements will use these settings.",
                "fonts": new_config.get('fonts', self.fonts),
                "fallback_fonts": new_config.get('fallback_fonts', self.fallback_fonts)
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                
            print(f"✓ Font configuration saved to {config_path}")
            self.reload_config()
            
        except Exception as e:
            print(f"⚠ Error saving font config: {e}")


# Global font manager instance
_font_manager = None

def get_font_manager() -> FontManager:
    """Get the global font manager instance"""
    global _font_manager
    if _font_manager is None:
        _font_manager = FontManager()
    return _font_manager

def get_font(font_name: str) -> ctk.CTkFont:
    """Convenience function to get a font"""
    return get_font_manager().get_font(font_name)

def get_font_tuple(font_name: str) -> Tuple[str, int, str]:
    """Convenience function to get font as tuple"""
    return get_font_manager().get_font_tuple(font_name)

def reload_fonts():
    """Convenience function to reload font configuration"""
    get_font_manager().reload_config()

def init_font_scaling(root_window=None):
    """Initialize font scaling based on screen DPI
    
    Call this early during GUI initialization, after creating the root window.
    
    Args:
        root_window: Optional tkinter root window for DPI detection
    """
    get_font_manager().calculate_scale_factor(root_window)
