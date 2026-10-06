"""
KI.AI Design System and QSS Theme Stylesheet.
Emerald Dark Theme with glassmorphic cards, modern typography,
responsive layouts, custom scrollbars, and vibrant status colors.
"""

from config import settings

MAIN_STYLESHEET = f"""
/* Global Reset & Typography */
QWidget {{
    background-color: {settings.THEME['background']};
    color: {settings.THEME['text_primary']};
    font-family: {settings.THEME['font_family']};
    font-size: 13px;
    selection-background-color: {settings.THEME['primary']};
    selection-color: #FFFFFF;
}}

/* Main Window */
QMainWindow {{
    background-color: {settings.THEME['background']};
}}

/* Sidebar Frame */
QFrame#sidebar {{
    background-color: {settings.THEME['surface']};
    border-right: 1px solid {settings.THEME['border_card']};
}}

/* Top Header Frame */
QFrame#top_header {{
    background-color: {settings.THEME['surface']};
    border-bottom: 1px solid {settings.THEME['border_card']};
}}

/* Sidebar Navigation Buttons */
QPushButton.nav_btn {{
    background-color: transparent;
    color: {settings.THEME['text_secondary']};
    border: none;
    border-left: 3px solid transparent;
    border-radius: 6px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton.nav_btn:hover {{
    background-color: {settings.THEME['surface_card']};
    color: #FFFFFF;
}}

QPushButton.nav_btn[active="true"], QPushButton.nav_btn:checked {{
    background-color: {settings.THEME['primary_light']};
    border-left: 3px solid {settings.THEME['primary']};
    color: {settings.THEME['primary']};
    font-weight: bold;
}}

/* Cards & Surface Containers */
QFrame.card {{
    background-color: {settings.THEME['surface_card']};
    border: 1px solid {settings.THEME['border_card']};
    border-radius: 12px;
    padding: 16px;
}}

QFrame.card:hover {{
    border: 1px solid {settings.THEME['primary']};
}}

QFrame.highlight_card {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #064E3B, stop:1 #0F172A);
    border: 1px solid {settings.THEME['primary']};
    border-radius: 12px;
    padding: 20px;
}}

/* Typography Headings */
QLabel.heading1 {{
    font-size: 22px;
    font-weight: bold;
    color: {settings.THEME['text_primary']};
}}

QLabel.heading2 {{
    font-size: 17px;
    font-weight: 600;
    color: {settings.THEME['text_primary']};
}}

QLabel.heading3 {{
    font-size: 14px;
    font-weight: 600;
    color: {settings.THEME['text_primary']};
}}

QLabel.text_muted {{
    color: {settings.THEME['text_muted']};
    font-size: 12px;
}}

/* Buttons */
QPushButton.btn_primary {{
    background-color: {settings.THEME['primary']};
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 9px 18px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton.btn_primary:hover {{
    background-color: {settings.THEME['primary_hover']};
}}

QPushButton.btn_primary:pressed {{
    background-color: {settings.THEME['primary_deep']};
}}

QPushButton.btn_primary:disabled {{
    background-color: #334155;
    color: #64748B;
}}

QPushButton.btn_secondary {{
    background-color: {settings.THEME['surface_light']};
    color: {settings.THEME['text_primary']};
    border: 1px solid {settings.THEME['border_card']};
    border-radius: 8px;
    padding: 9px 16px;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton.btn_secondary:hover {{
    background-color: #475569;
    border-color: {settings.THEME['text_secondary']};
}}

QPushButton.btn_outline {{
    background-color: transparent;
    color: {settings.THEME['primary']};
    border: 1px solid {settings.THEME['primary']};
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
}}

QPushButton.btn_outline:hover {{
    background-color: {settings.THEME['primary_light']};
}}

QPushButton.btn_danger {{
    background-color: {settings.THEME['danger']};
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: 600;
}}

QPushButton.btn_danger:hover {{
    background-color: #DC2626;
}}

QPushButton.btn_success {{
    background-color: {settings.THEME['success']};
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: 600;
}}

QPushButton.btn_success:hover {{
    background-color: {settings.THEME['primary_hover']};
}}

/* Form Inputs & Combos */
QLineEdit {{
    background-color: {settings.THEME['surface']};
    color: {settings.THEME['text_primary']};
    border: 1px solid {settings.THEME['border_card']};
    border-radius: 8px;
    padding: 9px 12px;
    font-size: 13px;
}}

QLineEdit:focus {{
    border: 1px solid {settings.THEME['primary']};
    background-color: #1E293B;
}}

QTextEdit, QPlainTextEdit {{
    background-color: {settings.THEME['surface']};
    color: {settings.THEME['text_primary']};
    border: 1px solid {settings.THEME['border_card']};
    border-radius: 8px;
    padding: 8px 12px;
}}

QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {settings.THEME['primary']};
}}

QComboBox {{
    background-color: {settings.THEME['surface_card']};
    color: {settings.THEME['text_primary']};
    border: 1px solid {settings.THEME['border_card']};
    border-radius: 8px;
    padding: 8px 12px;
    min-width: 120px;
}}

QComboBox:hover {{
    border-color: {settings.THEME['primary']};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {settings.THEME['surface_card']};
    color: {settings.THEME['text_primary']};
    selection-background-color: {settings.THEME['primary']};
    selection-color: #FFFFFF;
    border: 1px solid {settings.THEME['border_card']};
    border-radius: 8px;
    outline: none;
    padding: 4px;
}}

/* Scrollbars */
QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background-color: #334155;
    border-radius: 4px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {settings.THEME['primary']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: transparent;
    height: 8px;
}}

QScrollBar::handle:horizontal {{
    background-color: #334155;
    border-radius: 4px;
    min-width: 24px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Progress Bar */
QProgressBar {{
    background-color: {settings.THEME['surface_light']};
    border-radius: 4px;
    text-align: center;
    color: #FFFFFF;
    font-size: 11px;
    font-weight: bold;
}}

QProgressBar::chunk {{
    background-color: {settings.THEME['primary']};
    border-radius: 4px;
}}

/* Tables */
QTableWidget, QTableView {{
    background-color: {settings.THEME['surface_card']};
    border: 1px solid {settings.THEME['border_card']};
    border-radius: 8px;
    gridline-color: #334155;
    selection-background-color: {settings.THEME['primary_light']};
    selection-color: {settings.THEME['text_primary']};
    outline: none;
}}

QHeaderView::section {{
    background-color: {settings.THEME['surface']};
    color: {settings.THEME['text_secondary']};
    font-weight: 600;
    font-size: 12px;
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid {settings.THEME['border_card']};
}}

/* Dialogs */
QDialog {{
    background-color: {settings.THEME['background']};
}}

/* Checkboxes & Radios */
QCheckBox {{
    color: {settings.THEME['text_primary']};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {settings.THEME['border_card']};
    border-radius: 4px;
    background-color: {settings.THEME['surface']};
}}

QCheckBox::indicator:checked {{
    background-color: {settings.THEME['primary']};
    border-color: {settings.THEME['primary']};
    image: none;
}}

/* Tab Widgets */
QTabWidget::pane {{
    border: 1px solid {settings.THEME['border_card']};
    border-radius: 8px;
    background-color: {settings.THEME['surface_card']};
}}

QTabBar::tab {{
    background-color: {settings.THEME['surface']};
    color: {settings.THEME['text_secondary']};
    padding: 8px 18px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}

QTabBar::tab:selected {{
    background-color: {settings.THEME['surface_card']};
    color: {settings.THEME['primary']};
    font-weight: bold;
    border-bottom: 2px solid {settings.THEME['primary']};
}}
"""
