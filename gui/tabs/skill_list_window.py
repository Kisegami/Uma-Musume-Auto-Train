"""
Skill List Editor - Enhanced Implementation
- Cards stack vertically with smooth drag-drop reordering
- Rare skills can have a child skill (other_version) shown below with visual connection
- Intelligent auto-linking: automatically handles parent-child relationships
- Modern UI with better feedback and visual hierarchy
"""

import json
import os
import qtawesome as qta
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFrame, QMessageBox, QCompleter, QScrollArea, QWidget, QSizePolicy,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QMimeData, QTimer, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QDrag, QCursor, QColor

from ..styles import COLORS, MAIN_STYLESHEET


# ===== DATA LAYER =====
_skills_cache = None
_skills_by_name = {}
_rarity_map = {}
_child_to_parent = {}  # Maps child skill name -> parent (Rare) skill name


def load_skills():
    """Load skills and build lookup tables."""
    global _skills_cache, _skills_by_name, _rarity_map, _child_to_parent
    if _skills_cache is not None:
        return
    
    try:
        with open(os.path.join('assets', 'skills', 'skills.json'), 'r', encoding='utf-8') as f:
            _skills_cache = json.load(f)
    except:
        _skills_cache = {}
        return
    
    for rarity in ['Normal', 'Rare', 'Unique']:
        for skill in _skills_cache.get(rarity, []):
            name = skill.get('name', '')
            _skills_by_name[name] = skill
            _rarity_map[name] = rarity
            
            # Build child->parent mapping for Rare skills
            if rarity == 'Rare' and 'other_version' in skill:
                child = skill['other_version']
                _child_to_parent[child] = name


def get_rarity(name):
    """Get rarity of a skill (checks base name and variations)."""
    load_skills()
    
    # First try exact match
    if name in _rarity_map:
        return _rarity_map[name]
    
    # Try with variations if not found
    variations = get_skill_variations(name)
    for variant in variations:
        if variant in _rarity_map:
            return _rarity_map[variant]
    
    return 'Normal'


def get_child_skill(rare_name):
    """Get the child skill name for a Rare skill (returns base name)."""
    load_skills()
    
    # Check exact match first
    skill = _skills_by_name.get(rare_name, {})
    if 'other_version' in skill:
        return get_skill_base_name(skill['other_version'])
    
    # Try variations
    variations = get_skill_variations(rare_name)
    for variant in variations:
        skill = _skills_by_name.get(variant, {})
        if 'other_version' in skill:
            return get_skill_base_name(skill['other_version'])
    
    return None


def get_parent_skill(child_name):
    """Get the parent Rare skill name for a child skill (returns base name)."""
    load_skills()
    
    # Get base name of child
    child_base = get_skill_base_name(child_name)
    
    # Check if base name or any variation is a child
    child_variations = get_skill_variations(child_base)
    for child_var in child_variations:
        if child_var in _child_to_parent:
            return get_skill_base_name(_child_to_parent[child_var])
    
    return None


def get_all_skill_names():
    load_skills()
    return list(_skills_by_name.keys())


def get_skill_base_name(skill_name):
    """Get base name without variation suffix (◎,○,×)."""
    for suffix in [' ◎', ' ○', ' ×']:
        if skill_name.endswith(suffix):
            return skill_name[:-2]  # Remove last 2 characters (space + symbol)
    return skill_name


def get_skill_variations(base_name):
    """Get all variations of a skill (including base name)."""
    load_skills()
    variations = []
    
    # Check if base name exists
    if base_name in _skills_by_name:
        variations.append(base_name)
    
    # Check for variations with suffixes
    for suffix in [' ◎', ' ○', ' ×']:
        variant = base_name + suffix
        if variant in _skills_by_name:
            variations.append(variant)
    
    return variations


def skill_or_variation_in_list(skill_name, skill_list):
    """Check if a skill or any of its variations is in the list."""
    base_name = get_skill_base_name(skill_name)
    variations = get_skill_variations(base_name)
    
    for skill in skill_list:
        if skill in variations or get_skill_base_name(skill) == base_name:
            return True
    return False


def find_skill_in_list(skill_name, skill_list):
    """Find the actual skill name (or variation) that exists in the list."""
    base_name = get_skill_base_name(skill_name)
    variations = get_skill_variations(base_name)
    
    for skill in skill_list:
        if skill in variations or get_skill_base_name(skill) == base_name:
            return skill
    return None


def get_deduplicated_skill_names():
    """Get skill names with variations deduplicated (only base names shown)."""
    load_skills()
    seen_bases = set()
    deduplicated = []
    
    for skill_name in sorted(_skills_by_name.keys()):
        base_name = get_skill_base_name(skill_name)
        if base_name not in seen_bases:
            seen_bases.add(base_name)
            # Always show just the base name
            deduplicated.append(base_name)
    
    return deduplicated


# ===== CARD STYLES =====
STYLES = {
    'Unique': {
        'border': '#9333ea', 
        'bg': '#f3e8ff', 
        'bg_hover': '#e9d5ff',
        'text': '#581c87', 
        'icon': '◆',
        'shadow': '#9333ea40'
    },
    'Rare': {
        'border': '#eab308', 
        'bg': '#fef9c3', 
        'bg_hover': '#fef08a',
        'text': '#713f12', 
        'icon': '★',
        'shadow': '#eab30840'
    },
    'Normal': {
        'border': '#3b82f6', 
        'bg': '#dbeafe', 
        'bg_hover': '#bfdbfe',
        'text': '#1e3a8a', 
        'icon': '○',
        'shadow': '#3b82f640'
    },
    'Child': {
        'border': '#9ca3af', 
        'bg': '#f9fafb', 
        'bg_hover': '#f3f4f6',
        'text': '#374151', 
        'icon': '└─',
        'shadow': '#9ca3af30'
    },
}


# ===== DRAGGABLE CARD =====
class DragCard(QFrame):
    def __init__(self, index, parent_dialog, rarity):
        super().__init__()
        self.index = index
        self.parent_dialog = parent_dialog
        self.rarity = rarity
        self.is_dragging = False
        self.is_drag_over = False
        
        self.setAcceptDrops(True)
        self.setCursor(Qt.OpenHandCursor)
        
        # Add shadow effect for depth
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(STYLES[rarity]['shadow']))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
    
    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            self.is_dragging = True
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(str(self.index))
            drag.setMimeData(mime)
            self.setCursor(Qt.ClosedHandCursor)
            
            # Increase shadow during drag
            shadow = self.graphicsEffect()
            if shadow:
                shadow.setBlurRadius(15)
                shadow.setOffset(0, 4)
            
            drag.exec(Qt.MoveAction)
            
            # Reset shadow after drag
            if shadow:
                shadow.setBlurRadius(8)
                shadow.setOffset(0, 2)
            
            self.setCursor(Qt.OpenHandCursor)
            self.is_dragging = False
    
    def dragEnterEvent(self, e):
        if e.mimeData().hasText():
            self.is_drag_over = True
            self.setStyleSheet(self.styleSheet() + f" border: 3px dashed {STYLES[self.rarity]['border']}; ")
            e.acceptProposedAction()
    
    def dragLeaveEvent(self, e):
        self.is_drag_over = False
        # Parent will refresh the style
    
    def dropEvent(self, e):
        self.is_drag_over = False
        from_idx = int(e.mimeData().text())
        to_idx = self.index
        if from_idx != to_idx:
            self.parent_dialog._reorder(from_idx, to_idx)
        e.acceptProposedAction()
    
    def enterEvent(self, e):
        """Add hover effect."""
        if not self.is_dragging:
            s = STYLES[self.rarity]
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {s['bg_hover']}; 
                    border: 2px solid {s['border']}; 
                    border-radius: 12px;
                }}
            """)
        super().enterEvent(e)
    
    def leaveEvent(self, e):
        """Remove hover effect."""
        if not self.is_dragging:
            s = STYLES[self.rarity]
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {s['bg']}; 
                    border: 2px solid {s['border']}; 
                    border-radius: 12px;
                }}
            """)
        super().leaveEvent(e)


# ===== MAIN WINDOW =====
class SkillListWindow(QDialog):
    """Complete skill list editor."""
    
    def __init__(self, parent, skill_file_path):
        super().__init__(parent)
        self.skill_file = skill_file_path
        self.skills = []  # List of skill names (only parent/standalone skills)
        self.child_upgrades = {}  # rare_skill_name -> child_skill_name
        self.status_label = None  # Status message label
        self.status_timer = QTimer()  # Timer to clear status messages
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self._clear_status)
        
        load_skills()
        self._load()
        
        self.setWindowTitle("Edit Skill Priority List")
        self.setMinimumSize(700, 650)
        self.setStyleSheet(MAIN_STYLESHEET)
        self._build_ui()
    
    def _load(self):
        """Load from template file and convert to base names."""
        self.skills = []
        self.child_upgrades = {}
        
        if self.skill_file and os.path.exists(self.skill_file):
            try:
                with open(self.skill_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Convert skills to base names (strip variation symbols)
                raw_skills = data.get('skill_priority', [])
                self.skills = [get_skill_base_name(skill) for skill in raw_skills]
                
                # Convert child upgrades to base names
                raw_upgrades = data.get('gold_skill_upgrades', {})
                self.child_upgrades = {
                    get_skill_base_name(parent): get_skill_base_name(child)
                    for parent, child in raw_upgrades.items()
                }
            except:
                pass
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        
        # Header
        header = QHBoxLayout()
        
        # Title with icon
        title_container = QHBoxLayout()
        title_icon = QLabel()
        title_icon.setPixmap(qta.icon('fa5s.list-ol', color=COLORS['text_primary']).pixmap(QSize(24, 24)))
        title_container.addWidget(title_icon)
        
        title = QLabel("Skill Priority Manager")
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {COLORS['text_primary']};")
        title_container.addWidget(title)
        title_container.addStretch()
        
        header.addLayout(title_container, stretch=1)
        header.addStretch()
        
        # Legend badges
        for r in ['Unique', 'Rare', 'Normal']:
            s = STYLES[r]
            lbl = QLabel(f"{s['icon']} {r}")
            lbl.setStyleSheet(f"""
                background: {s['border']}; 
                color: white; 
                padding: 4px 10px; 
                border-radius: 10px; 
                font-weight: bold; 
                font-size: 11px;
                margin-left: 4px;
            """)
            header.addWidget(lbl)
        layout.addLayout(header)
        
        # Status message (hidden by default)
        self.status_label = QLabel()
        self.status_label.setStyleSheet(f"""
            background: #10b981; 
            color: white; 
            padding: 8px 12px; 
            border-radius: 8px; 
            font-weight: 500;
            font-size: 12px;
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.hide()
        layout.addWidget(self.status_label)
        
        # Add skill section
        add_frame = QFrame()
        add_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']}; 
                border-radius: 10px;
                border: 1px solid #e5e7eb;
            }}
        """)
        add_layout = QHBoxLayout(add_frame)
        add_layout.setContentsMargins(14, 12, 14, 12)
        add_layout.setSpacing(10)
        
        # Add icon using qtawesome
        add_icon_btn = QPushButton()
        add_icon_btn.setIcon(qta.icon('fa5s.plus-circle', color=COLORS['accent_blue']))
        add_icon_btn.setIconSize(QSize(20, 20))
        add_icon_btn.setFlat(True)
        add_icon_btn.setStyleSheet("border: none; background: transparent;")
        add_icon_btn.setEnabled(False)  # Just for display
        add_layout.addWidget(add_icon_btn)
        
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Type or search for a skill name...")
        self.entry.setStyleSheet(f"""
            QLineEdit {{
                border: 2px solid #e5e7eb;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                background: white;
                color: black;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['accent_blue']};
            }}
        """)
        # Use deduplicated names (base names only) for autocomplete
        completer = QCompleter(get_deduplicated_skill_names())
        
        # Style the popup of the completer so its text is readable too if needed
        popup = completer.popup()
        popup.setStyleSheet("background-color: white; color: black;")
        
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.entry.setCompleter(completer)
        self.entry.returnPressed.connect(self._add_skill)
        add_layout.addWidget(self.entry, stretch=1)
        
        add_btn = QPushButton("Add Skill")
        add_btn.setObjectName("primary")
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent_blue']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: #2563eb;
            }}
            QPushButton:pressed {{
                background: #1d4ed8;
            }}
        """)
        add_btn.clicked.connect(self._add_skill)
        add_layout.addWidget(add_btn)
        layout.addWidget(add_frame)
        
        # Info with icon
        info_layout = QHBoxLayout()
        info_icon = QLabel()
        info_icon.setPixmap(qta.icon('fa5s.info-circle', color=COLORS['text_secondary']).pixmap(QSize(14, 14)))
        info_layout.addWidget(info_icon)
        
        info = QLabel("Drag cards to reorder • Rare skills can have child upgrades • Auto-linking enabled")
        info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; padding: 4px;")
        info_layout.addWidget(info)
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # Cards scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet(f"background-color: {COLORS['bg_card']}; border-radius: 8px;")
        self.scroll.verticalScrollBar().setSingleStep(15)
        
        self.container = QWidget()
        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setContentsMargins(10, 10, 10, 10)
        self.cards_layout.setSpacing(6)
        self.cards_layout.addStretch()
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll, stretch=1)
        
        # Footer
        footer = QHBoxLayout()
        footer.setSpacing(10)
        
        self.count_lbl = QLabel()
        self.count_lbl.setStyleSheet(f"""
            color: {COLORS['text_secondary']}; 
            font-size: 12px;
            font-weight: 500;
        """)
        footer.addWidget(self.count_lbl)
        footer.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #6b7280;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #4b5563;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        footer.addWidget(cancel_btn)
        
        save_btn = QPushButton(" Save Changes")
        save_btn.setIcon(qta.icon('fa5s.save', color='white'))
        save_btn.setIconSize(QSize(16, 16))
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent_green']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: #16a34a;
            }}
            QPushButton:pressed {{
                background: #15803d;
            }}
        """)
        save_btn.clicked.connect(self._save)
        footer.addWidget(save_btn)
        layout.addLayout(footer)
        
        self._refresh()
    
    def _refresh(self):
        """Rebuild all cards with updated information."""
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for i, skill_name in enumerate(self.skills):
            group = self._make_card_group(i, skill_name)
            self.cards_layout.insertWidget(i, group)
        
        # Update count label
        total = len(self.skills)
        child_count = len(self.child_upgrades)
        
        if total == 0:
            self.count_lbl.setText("No skills added yet")
        elif child_count == 0:
            self.count_lbl.setText(f"{total} skill{'s' if total != 1 else ''}")
        else:
            self.count_lbl.setText(f"{total} skill{'s' if total != 1 else ''} • {child_count} child upgrade{'s' if child_count != 1 else ''}")
    
    def _make_card_group(self, index, skill_name):
        """Create card with optional child below."""
        rarity = get_rarity(skill_name)
        s = STYLES.get(rarity, STYLES['Normal'])
        child = self.child_upgrades.get(skill_name)
        available_child = get_child_skill(skill_name)  # Check if child is available
        
        group = QWidget()
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(5)
        
        # Main card
        card = DragCard(index, self, rarity)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {s['bg']}; 
                border: 2px solid {s['border']}; 
                border-radius: 12px;
            }}
        """)
        card.setFixedHeight(52)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)
        
        # Drag handle
        handle = QLabel("☰")
        handle.setStyleSheet(f"""
            color: {s['border']}; 
            font-size: 18px; 
            background: transparent;
            padding: 2px;
        """)
        handle.setToolTip("✋ Drag to reorder")
        layout.addWidget(handle)
        
        # Number
        num = QLabel(f"{index + 1}")
        num.setStyleSheet(f"""
            color: {s['text']}; 
            font-weight: bold; 
            background: transparent;
            font-size: 13px;
        """)
        num.setFixedWidth(28)
        num.setAlignment(Qt.AlignCenter)
        layout.addWidget(num)
        
        # Icon + Name
        icon_lbl = QLabel(s['icon'])
        icon_lbl.setStyleSheet(f"color: {s['border']}; font-size: 16px; background: transparent;")
        layout.addWidget(icon_lbl)
        
        name_lbl = QLabel(skill_name)
        name_lbl.setStyleSheet(f"""
            color: {s['text']}; 
            font-weight: bold; 
            font-size: 13px; 
            background: transparent;
        """)
        layout.addWidget(name_lbl, stretch=1)
        
        # Badge
        badge = QLabel(rarity)
        badge.setStyleSheet(f"""
            background: {s['border']}; 
            color: white; 
            padding: 3px 8px; 
            border-radius: 8px; 
            font-size: 10px; 
            font-weight: bold;
        """)
        layout.addWidget(badge)
        
        # Add child button (Rare only)
        if rarity == 'Rare' and available_child:
            child_btn = QPushButton()
            child_btn.setFixedSize(30, 30)
            
            # Get base name for display
            child_base = get_skill_base_name(available_child)
            
            if child:
                # Show remove child button
                child_btn.setIcon(qta.icon('fa5s.times', color='white'))
                child_btn.setIconSize(QSize(14, 14))
                child_btn.setToolTip(f"Remove child skill: {child}")
                child_btn.setStyleSheet("""
                    QPushButton {
                        background: #dc2626; 
                        color: white; 
                        border: none;
                        border-radius: 15px;
                    }
                    QPushButton:hover {
                        background: #b91c1c;
                    }
                """)
            else:
                # Show add child button
                child_btn.setIcon(qta.icon('fa5s.arrow-down', color='white'))
                child_btn.setIconSize(QSize(14, 14))
                child_btn.setToolTip(f"Add child skill: {child_base}")
                child_btn.setStyleSheet("""
                    QPushButton {
                        background: #f59e0b; 
                        color: white; 
                        border: none;
                        border-radius: 15px;
                    }
                    QPushButton:hover {
                        background: #d97706;
                    }
                """)
            
            child_btn.clicked.connect(lambda _, i=index: self._toggle_child(i))
            layout.addWidget(child_btn)
        
        # Delete button
        del_btn = QPushButton()
        del_btn.setIcon(qta.icon('fa5s.trash-alt', color='white'))
        del_btn.setIconSize(QSize(14, 14))
        del_btn.setFixedSize(30, 30)
        del_btn.setToolTip("Delete this skill")
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent_red']}; 
                color: white; 
                border: none;
                border-radius: 15px;
            }}
            QPushButton:hover {{
                background: #dc2626;
            }}
        """)
        del_btn.clicked.connect(lambda _, i=index: self._delete(i))
        layout.addWidget(del_btn)
        
        group_layout.addWidget(card)
        
        # Child card (below, indented with connection line)
        if child:
            cs = STYLES['Child']
            
            # Create a container for the connection line and child card
            child_container = QWidget()
            child_container_layout = QHBoxLayout(child_container)
            child_container_layout.setContentsMargins(0, 0, 0, 0)
            child_container_layout.setSpacing(0)
            
            # Connection indicator (vertical line + corner)
            connector = QLabel("│\n└─")
            connector.setStyleSheet(f"""
                color: {cs['border']}; 
                font-size: 10px; 
                background: transparent;
                padding-left: 20px;
                line-height: 0.8;
            """)
            connector.setFixedWidth(35)
            child_container_layout.addWidget(connector)
            
            # Child card
            child_card = QFrame()
            child_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {cs['bg']}; 
                    border: 2px solid {cs['border']}; 
                    border-radius: 10px;
                    border-left-width: 3px;
                }}
            """)
            child_card.setFixedHeight(40)
            
            cl = QHBoxLayout(child_card)
            cl.setContentsMargins(12, 6, 12, 6)
            cl.setSpacing(10)
            
            # Child icon
            child_icon = QLabel("↳")
            child_icon.setStyleSheet(f"color: {cs['border']}; font-size: 16px; background: transparent;")
            cl.addWidget(child_icon)
            
            # Child name (always base name without symbols)
            child_name = QLabel(child)
            child_name.setStyleSheet(f"""
                color: {cs['text']}; 
                font-weight: bold; 
                font-size: 12px; 
                background: transparent;
            """)
            cl.addWidget(child_name, stretch=1)
            
            # Child rarity badge
            child_rarity = get_rarity(child)
            child_rarity_badge = QLabel(f"Child ({child_rarity})")
            child_rarity_badge.setStyleSheet(f"""
                background: {cs['border']}; 
                color: white; 
                padding: 2px 7px; 
                border-radius: 7px; 
                font-size: 10px;
                font-weight: 500;
            """)
            cl.addWidget(child_rarity_badge)
            
            child_container_layout.addWidget(child_card, stretch=1)
            group_layout.addWidget(child_container)
        
        return group
    
    def _show_status(self, message, is_error=False):
        """Show a temporary status message."""
        if is_error:
            self.status_label.setStyleSheet(f"""
                background: #ef4444; 
                color: white; 
                padding: 8px 12px; 
                border-radius: 8px; 
                font-weight: 500;
                font-size: 12px;
            """)
        else:
            self.status_label.setStyleSheet(f"""
                background: #10b981; 
                color: white; 
                padding: 8px 12px; 
                border-radius: 8px; 
                font-weight: 500;
                font-size: 12px;
            """)
        
        self.status_label.setText(message)
        self.status_label.show()
        self.status_timer.start(3000)  # Hide after 3 seconds
    
    def _clear_status(self):
        """Clear the status message."""
        self.status_label.hide()
    
    def _add_skill(self):
        """Add skill with intelligent auto-linking logic (always uses base names)."""
        name = self.entry.text().strip()
        if not name:
            return
        
        # Always use base name (strip variation symbols)
        base_name = get_skill_base_name(name)
        variations = get_skill_variations(base_name)
        
        if not variations:
            # Not found at all
            self._show_status(f"⚠️ Skill '{base_name}' not found in database", is_error=True)
            return
        
        # Always use base name without symbols
        skill_to_add = base_name
        
        # Check if already in list (check base names)
        if skill_to_add in self.skills:
            self._show_status(f"ℹ️ '{skill_to_add}' is already in the list", is_error=True)
            return
        
        # Check if this skill is already a child of any rare skill in the list
        for rare_skill in self.skills:
            if get_rarity(rare_skill) == 'Rare':
                child_of_rare = get_child_skill(rare_skill)
                if child_of_rare == skill_to_add:
                    # This skill is a potential child of this rare skill
                    if rare_skill in self.child_upgrades:
                        # Already assigned as child
                        self._show_status(f"ℹ️ '{skill_to_add}' is already the child skill of '{rare_skill}'", is_error=True)
                        return
                    else:
                        # Auto-link as child (rare skill exists but doesn't have child yet)
                        self.child_upgrades[rare_skill] = skill_to_add
                        self.entry.clear()
                        self._refresh()
                        self._show_status(f"Auto-linked '{skill_to_add}' as child of '{rare_skill}'")
                        return
        
        # Check if this is a Rare skill and its child is already in list
        child_base_name = get_child_skill(skill_to_add)
        if child_base_name:
            child_base = get_skill_base_name(child_base_name)
            if child_base in self.skills:
                # Replace child with parent, link as child
                idx = self.skills.index(child_base)
                self.skills[idx] = skill_to_add
                self.child_upgrades[skill_to_add] = child_base
                self.entry.clear()
                self._refresh()
                self._show_status(f"Replaced '{child_base}' with '{skill_to_add}' and auto-linked as child")
                return
        
        # Normal add
        self.skills.append(skill_to_add)
        self.entry.clear()
        self._refresh()
        rarity = get_rarity(skill_to_add)
        self._show_status(f"Added {rarity} skill: {skill_to_add}")
    
    def _reorder(self, from_idx, to_idx):
        """Reorder skills."""
        skill = self.skills.pop(from_idx)
        self.skills.insert(to_idx, skill)
        self._refresh()
    
    def _toggle_child(self, index):
        """Toggle child skill for Rare skill (always uses base names)."""
        skill = self.skills[index]
        child_base_raw = get_child_skill(skill)
        if not child_base_raw:
            return
        
        # Always use base name without symbols
        child_base = get_skill_base_name(child_base_raw)
        
        if skill in self.child_upgrades:
            # Remove child
            removed_child = self.child_upgrades[skill]
            del self.child_upgrades[skill]
            self._refresh()
            self._show_status(f"Removed child skill '{removed_child}' from '{skill}'")
        else:
            # Add child using base name
            self.child_upgrades[skill] = child_base
            self._refresh()
            self._show_status(f"Added child skill '{child_base}' to '{skill}'")
    
    def _delete(self, index):
        """Delete skill with confirmation."""
        skill = self.skills[index]
        has_child = skill in self.child_upgrades
        
        # Confirmation dialog
        msg = f"Delete '{skill}'?"
        if has_child:
            msg += f"\n(Child skill '{self.child_upgrades[skill]}' will also be removed)"
        
        reply = QMessageBox.question(
            self, 
            "Confirm Delete", 
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.skills.pop(index)
            if has_child:
                child_name = self.child_upgrades[skill]
                del self.child_upgrades[skill]
                self._show_status(f"Deleted '{skill}' and child '{child_name}'")
            else:
                self._show_status(f"Deleted '{skill}'")
            self._refresh()
    
    def _save(self):
        """Save to file with validation."""
        if not self.skills:
            reply = QMessageBox.question(
                self,
                "Empty List",
                "You haven't added any skills. Save empty list?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        try:
            data = {
                'skill_priority': self.skills,
                'gold_skill_upgrades': self.child_upgrades
            }
            
            os.makedirs(os.path.dirname(self.skill_file), exist_ok=True)
            with open(self.skill_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            child_count = len(self.child_upgrades)
            msg = f"Successfully saved {len(self.skills)} skill(s)"
            if child_count > 0:
                msg += f" with {child_count} child upgrade(s)"
            
            QMessageBox.information(self, "Success", msg)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{str(e)}")
