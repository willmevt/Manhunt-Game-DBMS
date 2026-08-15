PALETTE = {
    "background": "#F4F1E9",
    "panel": "#FBF9F2",
    "primary": "#8FA888",
    "primary_hover": "#7C9573",
    "primary_pressed": "#6B8262",
    "border": "#D8D2C0",
    "text": "#3E4A3A",
    "text_muted": "#6B715F",
    "selection": "#C7D6BC",
    "white": "#FFFFFF",
}

FONT_FAMILY = '"Montserrat", "Segoe UI", Arial, sans-serif'

STYLESHEET = f"""
QWidget {{
    background-color: {PALETTE["background"]};
    color: {PALETTE["text"]};
    font-family: {FONT_FAMILY};
    font-size: 10pt;
}}

QMainWindow, QDialog {{
    background-color: {PALETTE["background"]};
}}

QLabel {{
    background: transparent;
}}

QPushButton {{
    background-color: {PALETTE["primary"]};
    color: {PALETTE["white"]};
    border: 1px solid {PALETTE["primary_pressed"]};
    border-radius: 6px;
    padding: 6px 14px;
}}

QPushButton:hover {{
    background-color: {PALETTE["primary_hover"]};
}}

QPushButton:pressed {{
    background-color: {PALETTE["primary_pressed"]};
}}

QPushButton:disabled {{
    background-color: {PALETTE["border"]};
    color: {PALETTE["text_muted"]};
    border: 1px solid {PALETTE["border"]};
}}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
    background-color: {PALETTE["white"]};
    border: 1px solid {PALETTE["border"]};
    border-radius: 4px;
    padding: 4px 6px;
    selection-background-color: {PALETTE["selection"]};
}}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
    border: 1px solid {PALETTE["primary"]};
}}

QLineEdit:read-only {{
    background-color: {PALETTE["background"]};
    color: {PALETTE["text_muted"]};
}}

QComboBox::drop-down {{
    border: none;
    width: 18px;
}}

QGroupBox {{
    background-color: {PALETTE["panel"]};
    border: 1px solid {PALETTE["border"]};
    border-radius: 8px;
    margin-top: 12px;
    padding: 10px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 4px;
    color: {PALETTE["primary_pressed"]};
}}

QTabWidget::pane {{
    background-color: {PALETTE["panel"]};
    border: 1px solid {PALETTE["border"]};
    border-radius: 8px;
    top: -1px;
}}

QTabBar::tab {{
    background-color: {PALETTE["background"]};
    color: {PALETTE["text_muted"]};
    border: 1px solid {PALETTE["border"]};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 16px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {PALETTE["primary"]};
    color: {PALETTE["white"]};
}}

QTabBar::tab:hover:!selected {{
    background-color: {PALETTE["selection"]};
    color: {PALETTE["text"]};
}}

QTableWidget {{
    background-color: {PALETTE["white"]};
    alternate-background-color: {PALETTE["panel"]};
    gridline-color: {PALETTE["border"]};
    border: 1px solid {PALETTE["border"]};
    border-radius: 6px;
    selection-background-color: {PALETTE["selection"]};
    selection-color: {PALETTE["text"]};
}}

QHeaderView::section {{
    background-color: {PALETTE["primary"]};
    color: {PALETTE["white"]};
    padding: 6px;
    border: none;
    border-right: 1px solid {PALETTE["primary_pressed"]};
}}

QCheckBox {{
    spacing: 6px;
}}

QMessageBox {{
    background-color: {PALETTE["background"]};
}}
"""


def apply_theme(app):
    """Apply the shared Manhunt style sheet to a QApplication instance."""
    app.setStyleSheet(STYLESHEET)
