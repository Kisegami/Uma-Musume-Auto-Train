"""
Dark Theme Styles for PySide6 GUI
Inspired by Alas/MAA bot interfaces - Clean, modern dark theme.
"""

# Color Palette - Darker, more cohesive theme
COLORS = {
    # Backgrounds
    'bg_darkest': '#1a1a1a',       # Main background
    'bg_dark': '#242424',           # Sidebar/panels
    'bg_card': '#2d2d2d',           # Card backgrounds
    'bg_input': '#383838',          # Input fields
    'bg_hover': '#404040',          # Hover states
    
    # Borders
    'border': '#3a3a3a',
    'border_light': '#4a4a4a',
    
    # Text
    'text_primary': '#ffffff',
    'text_secondary': '#b0b0b0',
    'text_muted': '#707070',
    
    # Accents
    'accent_primary': '#7c5cff',    # Purple accent (like MAA)
    'accent_blue': '#4a9eff',
    'accent_green': '#4caf50',
    'accent_red': '#ef5350',
    'accent_orange': '#ff9800',
    'accent_pink': '#e91e63',
    
    # Sidebar
    'sidebar_bg': '#1e1e1e',
    'sidebar_active': '#7c5cff',
    'sidebar_hover': '#333333',
}


MAIN_STYLESHEET = f"""
/* ==================== Main Window ==================== */
QMainWindow {{
    background-color: {COLORS['bg_darkest']};
}}

QWidget {{
    background-color: transparent;
    color: {COLORS['text_primary']};
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 13px;
}}

/* ==================== Sidebar ==================== */
QFrame#sidebar {{
    background-color: {COLORS['sidebar_bg']};
    border: none;
    border-right: 1px solid {COLORS['border']};
}}

QPushButton#sidebarBtn {{
    background-color: transparent;
    color: {COLORS['text_secondary']};
    border: none;
    border-radius: 8px;
    padding: 12px 16px;
    text-align: left;
    font-size: 14px;
    font-weight: 600;
}}

QPushButton#sidebarBtn:hover {{
    background-color: {COLORS['sidebar_hover']};
    color: {COLORS['text_primary']};
}}

QPushButton#sidebarBtn:checked {{
    background-color: {COLORS['accent_primary']};
    color: {COLORS['text_primary']};
    font-weight: 700;
}}

/* ==================== Cards/Panels ==================== */
QFrame#card {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
}}

QFrame#cardNoBorder {{
    background-color: {COLORS['bg_card']};
    border: none;
    border-radius: 12px;
}}

/* ==================== Labels ==================== */
QLabel {{
    background-color: transparent;
    border: none;
}}

QLabel#title {{
    font-size: 20px;
    font-weight: bold;
    color: {COLORS['text_primary']};
}}

QLabel#sectionTitle {{
    font-size: 16px;
    font-weight: 600;
    color: {COLORS['text_primary']};
    padding: 8px 0;
}}

QLabel#subtitle {{
    font-size: 13px;
    color: {COLORS['text_secondary']};
}}

QLabel#muted {{
    color: {COLORS['text_muted']};
    font-size: 12px;
}}

/* ==================== Buttons ==================== */
QPushButton {{
    background-color: {COLORS['bg_input']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 500;
    min-height: 20px;
}}

QPushButton:hover {{
    background-color: {COLORS['bg_hover']};
    border-color: {COLORS['border_light']};
}}

QPushButton:pressed {{
    background-color: {COLORS['bg_card']};
}}

QPushButton#primary {{
    background-color: {COLORS['accent_green']};
    border: none;
    color: white;
}}

QPushButton#primary:hover {{
    background-color: #5cb85c;
}}

QPushButton#danger {{
    background-color: {COLORS['accent_red']};
    border: none;
    color: white;
}}

QPushButton#danger:hover {{
    background-color: #ff6659;
}}

QPushButton#accent {{
    background-color: {COLORS['accent_primary']};
    border: none;
    color: white;
}}

QPushButton#accent:hover {{
    background-color: #8b6fff;
}}

QPushButton#flat {{
    background-color: transparent;
    border: none;
    color: {COLORS['text_secondary']};
}}

QPushButton#flat:hover {{
    color: {COLORS['text_primary']};
    background-color: {COLORS['bg_hover']};
}}

/* ==================== Inputs ==================== */
QLineEdit {{
    background-color: {COLORS['bg_input']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    min-height: 18px;
}}

QLineEdit:focus {{
    border-color: {COLORS['accent_primary']};
}}

/* ==================== SpinBox ==================== */
QSpinBox, QDoubleSpinBox {{
    background-color: {COLORS['bg_input']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    min-height: 18px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {COLORS['accent_primary']};
}}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    width: 0;
    border: none;
}}

/* ==================== ComboBox ==================== */
QComboBox {{
    background-color: {COLORS['bg_input']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    padding-right: 24px;
    min-height: 18px;
}}

QComboBox:hover {{
    border-color: {COLORS['border_light']};
}}

QComboBox:focus {{
    border-color: {COLORS['accent_primary']};
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    selection-background-color: {COLORS['accent_primary']};
    outline: none;
    padding: 4px;
}}

QComboBox QAbstractItemView::item {{
    padding: 8px 12px;
    border-radius: 4px;
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: {COLORS['bg_hover']};
}}

/* ==================== CheckBox ==================== */
QCheckBox {{
    spacing: 10px;
    color: {COLORS['text_primary']};
}}

QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid {COLORS['border_light']};
    background-color: {COLORS['bg_input']};
}}

QCheckBox::indicator:hover {{
    border-color: {COLORS['accent_primary']};
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS['accent_primary']};
    border-color: {COLORS['accent_primary']};
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNiIgaGVpZ2h0PSIxNiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjMiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiPjwvcG9seWxpbmU+PC9zdmc+);
}}

/* ==================== RadioButton ==================== */
QRadioButton {{
    spacing: 10px;
    color: {COLORS['text_primary']};
}}

QRadioButton::indicator {{
    width: 20px;
    height: 20px;
    border-radius: 10px;
    border: 2px solid {COLORS['border_light']};
    background-color: {COLORS['bg_input']};
}}

QRadioButton::indicator:hover {{
    border-color: {COLORS['accent_primary']};
}}

QRadioButton::indicator:checked {{
    background-color: {COLORS['accent_primary']};
    border-color: {COLORS['accent_primary']};
}}

/* ==================== GroupBox ==================== */
QGroupBox {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
    margin-top: 20px;
    padding-top: 12px;
    font-weight: 400;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    padding: 0 8px;
    color: {COLORS['text_primary']};
    background-color: {COLORS['bg_card']};
    font-weight: 700;
    font-size: 14px;
}}

/* ==================== ScrollArea ==================== */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    margin: 4px 2px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['border_light']};
    min-height: 30px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['text_muted']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

/* ==================== TabWidget ==================== */
QTabWidget::pane {{
    border: none;
    background-color: transparent;
}}

QTabBar {{
    background-color: transparent;
}}

QTabBar::tab {{
    background-color: transparent;
    color: {COLORS['text_secondary']};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 12px 24px;
    font-weight: 500;
}}

QTabBar::tab:selected {{
    color: {COLORS['accent_primary']};
    border-bottom-color: {COLORS['accent_primary']};
}}

QTabBar::tab:hover:!selected {{
    color: {COLORS['text_primary']};
}}

/* ==================== Progress Bar ==================== */
QProgressBar {{
    background-color: {COLORS['bg_input']};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {COLORS['accent_primary']};
    border-radius: 4px;
}}

/* ==================== List Widget ==================== */
QListWidget {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    outline: none;
    padding: 4px;
}}

QListWidget::item {{
    padding: 10px 12px;
    border-radius: 6px;
    margin: 2px 0;
}}

QListWidget::item:selected {{
    background-color: {COLORS['accent_primary']};
}}

QListWidget::item:hover:!selected {{
    background-color: {COLORS['bg_hover']};
}}

/* ==================== TextEdit ==================== */
QTextEdit, QPlainTextEdit {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
}}

/* ==================== Splitter ==================== */
QSplitter::handle {{
    background-color: transparent;
}}

QSplitter::handle:horizontal {{
    width: 6px;
}}

/* ==================== Menu ==================== */
QMenuBar {{
    background-color: {COLORS['sidebar_bg']};
    color: {COLORS['text_primary']};
    border-bottom: 1px solid {COLORS['border']};
    padding: 4px 8px;
}}

QMenuBar::item {{
    padding: 6px 12px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {COLORS['bg_hover']};
}}

QMenu {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 6px;
}}

QMenu::item {{
    padding: 8px 24px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {COLORS['accent_primary']};
}}

QMenu::separator {{
    height: 1px;
    background-color: {COLORS['border']};
    margin: 6px 12px;
}}

/* ==================== ToolTip ==================== */
QToolTip {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
}}
"""


def get_color(name: str) -> str:
    """Get a color by name from the palette"""
    return COLORS.get(name, COLORS['text_primary'])
