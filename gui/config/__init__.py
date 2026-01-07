"""
Config tabs for Uma Musume Auto-Train Bot GUI

This package contains modular configuration tabs that can be imported
and used by the main ConfigPanel class.
"""

try:
    from .main_tab import MainTab
    from .performance_tab import PerformanceTab
    from .training_tab import TrainingTab
    from .racing_tab import RacingTab
    from .event_tab import EventTab
    from .skill_tab import SkillTab
    from .restart_tab import RestartTab
    from .others_tab import OthersTab
    from .update_tab import UpdateTab
    
    __all__ = [
        'MainTab',
        'PerformanceTab',
        'TrainingTab', 
        'RacingTab',
        'EventTab',
        'SkillTab',
        'RestartTab',
        'OthersTab',
        'UpdateTab'
    ]
    
except ImportError as e:
    # If import fails, the main config panel will fall back to inline methods
    print(f"Warning: Could not import config tabs: {e}")
    __all__ = []
