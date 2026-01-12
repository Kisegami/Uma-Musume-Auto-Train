"""
Icon Helper for PySide6 GUI
Centralized QtAwesome icon management for consistent icons across the application.
"""

import qtawesome as qta
from PySide6.QtGui import QIcon


def get_icon(name: str, color: str = "white") -> QIcon:
    """
    Get a QtAwesome icon by name.
    
    Args:
        name: Icon name (e.g., 'play', 'pause', 'check')
        color: Icon color (default: white)
    
    Returns:
        QIcon object
    """
    icon_map = {
        # Playback controls
        'play': 'fa5s.play',
        'pause': 'fa5s.pause',
        'stop': 'fa5s.stop',
        'play-circle': 'fa5s.play-circle',
        
        # Navigation/expansion
        'expand': 'fa5s.chevron-right',
        'collapse': 'fa5s.chevron-down',
        'chevron-right': 'fa5s.chevron-right',
        'chevron-down': 'fa5s.chevron-down',
        
        # Status indicators
        'check': 'fa5s.check',
        'check-circle': 'fa5s.check-circle',
        'times': 'fa5s.times',
        'close': 'fa5s.times-circle',
        'warning': 'fa5s.exclamation-triangle',
        'info': 'fa5s.info-circle',
        
        # Common actions
        'save': 'fa5s.save',
        'edit': 'fa5s.edit',
        'delete': 'fa5s.trash',
        'add': 'fa5s.plus',
        'remove': 'fa5s.minus',
    }
    
    icon_name = icon_map.get(name, name)
    return qta.icon(icon_name, color=color)


def get_icon_char(name: str) -> str:
    """
    Get a FontAwesome character for inline text use.
    
    Args:
        name: Icon name
    
    Returns:
        Unicode character string
    """
    char_map = {
        'play': '\uf04b',
        'pause': '\uf04c',
        'stop': '\uf04d',
        'expand': '\uf054',
        'collapse': '\uf078',
        'check': '\uf00c',
        'times': '\uf00d',
        'warning': '\uf071',
    }
    
    return char_map.get(name, '')
