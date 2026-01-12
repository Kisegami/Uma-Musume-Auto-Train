"""
Tabs Package for PySide6 GUI - Matching original 9 tabs
"""

from .main_tab import MainTab
from .performance_tab import PerformanceTab
from .training_tab import TrainingTab
from .racing_tab import RacingTab
from .skill_tab import SkillTab
from .event_tab import EventTab
from .restart_tab import RestartTab
from .others_tab import OthersTab
from .update_tab import UpdateTab

__all__ = [
    'MainTab',
    'PerformanceTab', 
    'TrainingTab',
    'RacingTab',
    'SkillTab',
    'EventTab',
    'RestartTab',
    'OthersTab',
    'UpdateTab'
]
