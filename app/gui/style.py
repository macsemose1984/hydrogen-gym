from PySide6.QtGui import QColor, QFont

# Segoe UI is bundled with Windows and renders Arabic and English consistently.
FONT_FAMILY = "Segoe UI"

# ---- current palette (mutated by set_theme) ----
PRIMARY = QColor("#0f172a")
SECONDARY = QColor("#1e293b")
ACCENT = QColor("#f97316")
ACCENT_LIGHT = QColor("#fb923c")
SUCCESS = QColor("#22c55e")
DANGER = QColor("#ef4444")
DANGER_BORDER = QColor("#fecaca")
DANGER_HOVER = QColor("#fef2f2")
WARNING = QColor("#f59e0b")
BG = QColor("#f1f5f9")
CARD = QColor("#ffffff")
TEXT = QColor("#1e293b")
MUTED = QColor("#64748b")
SELECTION = QColor("#ffedd5")
BORDER = QColor("#e2e8f0")
FIELD = QColor("#f8fafc")
PLACEHOLDER = QColor("#94a3b8")

PALETTES = {
    "light": {
        "PRIMARY": QColor("#0f172a"),
        "SECONDARY": QColor("#1e293b"),
        "ACCENT": QColor("#f97316"),
        "ACCENT_LIGHT": QColor("#fb923c"),
        "SUCCESS": QColor("#22c55e"),
        "DANGER": QColor("#ef4444"),
        "DANGER_BORDER": QColor("#fecaca"),
        "DANGER_HOVER": QColor("#fef2f2"),
        "BG": QColor("#f1f5f9"),
        "CARD": QColor("#ffffff"),
        "TEXT": QColor("#1e293b"),
        "MUTED": QColor("#64748b"),
        "SELECTION": QColor("#ffedd5"),
        "BORDER": QColor("#e2e8f0"),
        "FIELD": QColor("#f8fafc"),
        "PLACEHOLDER": QColor("#94a3b8"),
        "WARNING": QColor("#f59e0b"),
    },
    "dark": {
        "PRIMARY": QColor("#0f172a"),
        "SECONDARY": QColor("#1e293b"),
        "ACCENT": QColor("#fb923c"),
        "ACCENT_LIGHT": QColor("#f97316"),
        "SUCCESS": QColor("#22c55e"),
        "DANGER": QColor("#ef4444"),
        "DANGER_BORDER": QColor("#7f1d1d"),
        "DANGER_HOVER": QColor("#3b1616"),
        "BG": QColor("#0b1120"),
        "CARD": QColor("#16223a"),
        "TEXT": QColor("#e2e8f0"),
        "MUTED": QColor("#94a3b8"),
        "SELECTION": QColor("#7c2d12"),
        "BORDER": QColor("#2a3a55"),
        "FIELD": QColor("#1e2c47"),
        "PLACEHOLDER": QColor("#64748b"),
        "WARNING": QColor("#fbbf24"),
    },
}

CURRENT_THEME = "dark"


def _apply(pal):
    global PRIMARY, SECONDARY, ACCENT, ACCENT_LIGHT, SUCCESS, DANGER
    global DANGER_BORDER, DANGER_HOVER, BG, CARD, TEXT, MUTED, SELECTION, BORDER, FIELD
    global PLACEHOLDER
    global WARNING
    PRIMARY = pal["PRIMARY"]
    SECONDARY = pal["SECONDARY"]
    ACCENT = pal["ACCENT"]
    ACCENT_LIGHT = pal["ACCENT_LIGHT"]
    SUCCESS = pal["SUCCESS"]
    DANGER = pal["DANGER"]
    DANGER_BORDER = pal["DANGER_BORDER"]
    DANGER_HOVER = pal["DANGER_HOVER"]
    BG = pal["BG"]
    CARD = pal["CARD"]
    TEXT = pal["TEXT"]
    MUTED = pal["MUTED"]
    SELECTION = pal["SELECTION"]
    BORDER = pal["BORDER"]
    FIELD = pal["FIELD"]
    PLACEHOLDER = pal["PLACEHOLDER"]
    WARNING = pal["WARNING"]


def toggle_theme():
    """Toggle between 'light' and 'dark' themes."""
    mode = "light" if CURRENT_THEME == "dark" else "dark"
    set_theme(mode)
    return mode


def set_theme(mode):
    """mode: 'light' | 'dark'."""
    global CURRENT_THEME
    if mode not in PALETTES:
        mode = "dark"
    CURRENT_THEME = mode
    _apply(PALETTES[mode])
    _build_qss()


# ---- QSS strings (rebuilt on theme change) ----
SIDEBAR_QSS = ""
CARD_QSS = ""
BTN_QSS = ""
INPUT_QSS = ""
TABLE_QSS = ""
MISC_QSS = ""
LOGIN_QSS = ""


def _build_qss():
    global SIDEBAR_QSS, CARD_QSS, BTN_QSS, INPUT_QSS, TABLE_QSS, MISC_QSS, LOGIN_QSS
    hex = lambda c: c.name()

    SIDEBAR_QSS = f"""
QWidget#Sidebar {{ background: {hex(PRIMARY)}; }}
QWidget#Sidebar QLabel#Brand {{ color: white; font-size: 21px; font-weight: 700; padding: 18px 10px 10px 10px; }}
QWidget#Sidebar QLabel#BrandSub {{ color: {hex(ACCENT_LIGHT)}; font-size: 11px; padding: 0 16px 20px 16px; }}
QPushButton#Nav {{ color: #cbd5e1; background: transparent; border: none; text-align: left;
                  padding: 12px 16px; font-size: 14px; font-weight: 500; border-radius: 9px; margin: 2px 10px; }}
QPushButton#Nav:hover {{ background: {hex(SECONDARY)}; color: white; }}
QPushButton#Nav:checked {{ background: {hex(ACCENT)}; color: white; font-weight: 700; }}
QPushButton#Nav:checked:hover {{ background: {hex(ACCENT_LIGHT)}; }}
    QPushButton#Logout {{ color: {hex(DANGER)}; background: transparent; border: 1px solid {hex(DANGER_BORDER)}; text-align: left;
                         padding: 13px 18px; font-size: 14px; border-radius: 10px; margin: 8px 10px; }}
    QPushButton#Logout:hover {{ background: {hex(DANGER)}; color: white; border-color: {hex(DANGER)}; }}
    QPushButton#Logout:pressed {{ background: #7f1d1d; }}
"""

    CARD_QSS = f"""
QFrame#Card, QFrame#StatCard, QFrame#ChartBox {{
    background: {hex(CARD)}; border: 1px solid {hex(BORDER)}; border-radius: 16px;
}}
QLabel#StatValue {{ font-size: 28px; font-weight: 700; color: {hex(TEXT)}; }}
QLabel#StatLabel {{ font-size: 12px; font-weight: 600; color: {hex(MUTED)}; }}
QLabel#StatIcon {{ font-size: 23px; }}
QLabel#PageTitle {{ font-size: 24px; font-weight: 700; color: {hex(TEXT)}; padding: 2px 0 8px; }}
"""

    BTN_QSS = f"""
QPushButton {{ border-radius: 9px; padding: 9px 16px; font-size: 13px; font-weight: 600; min-height: 20px; }}
QPushButton:focus {{ outline: none; }}
QPushButton#Primary {{ background: {hex(ACCENT)}; color: white; border: none; min-height: 38px; }}
QPushButton#Primary:hover {{ background: {hex(ACCENT_LIGHT)}; }}
QPushButton#Primary:pressed {{ background: {hex(SECONDARY)}; }}
QPushButton#Primary:disabled {{ background: {hex(BORDER)}; color: {hex(MUTED)}; }}
QPushButton#Secondary {{ background: {hex(CARD)}; color: {hex(TEXT)}; border: 1px solid {hex(BORDER)}; min-height: 38px; }}
QPushButton#Secondary:hover {{ background: {hex(FIELD)}; border-color: {hex(MUTED)}; }}
QPushButton#Secondary:pressed {{ background: {hex(BORDER)}; }}
QPushButton#Secondary:disabled {{ color: {hex(MUTED)}; border-color: {hex(BORDER)}; }}
QPushButton#Success {{ background: {hex(SUCCESS)}; color: white; border: none; min-height: 38px; }}
QPushButton#Success:hover {{ background: #16a34a; }}
QPushButton#Success:pressed {{ background: #15803d; }}
QPushButton#Success:disabled {{ background: {hex(BORDER)}; color: {hex(MUTED)}; }}
QPushButton#Danger {{ background: {hex(CARD)}; color: {hex(DANGER)}; border: 1px solid {hex(DANGER_BORDER)}; min-height: 38px; }}
QPushButton#Danger:hover {{ background: {hex(DANGER_HOVER)}; border-color: {hex(DANGER)}; }}
QPushButton#Danger:pressed {{ background: {hex(DANGER_BORDER)}; }}
QPushButton#Danger:disabled {{ color: {hex(MUTED)}; border-color: {hex(BORDER)}; }}
QPushButton#Ghost {{ background: transparent; color: {hex(MUTED)}; border: 1px dashed {hex(BORDER)}; }}
QPushButton#Ghost:hover {{ color: {hex(TEXT)}; border-color: {hex(MUTED)}; }}
"""

    INPUT_QSS = f"""
QLineEdit, QComboBox, QDateEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
    background: {hex(FIELD)}; border: 1px solid {hex(BORDER)}; border-radius: 10px;
    padding: 9px 12px; font-size: 13px; color: {hex(TEXT)};
    selection-background-color: {hex(ACCENT)}; selection-color: white;
}}
QLineEdit::placeholder, QTextEdit::placeholder {{ color: {hex(PLACEHOLDER)}; }}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 2px solid {hex(ACCENT)}; background: {hex(CARD)};
}}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox QAbstractItemView {{ background: {hex(CARD)}; color: {hex(TEXT)};
    border: 1px solid {hex(BORDER)}; border-radius: 8px; padding: 4px;
    selection-background-color: {hex(ACCENT)}; selection-color: white; }}
QDateEdit::drop-down {{ border: none; width: 20px; }}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background: {hex(FIELD)}; border: none; border-radius: 4px; margin: 2px;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{ background: {hex(BORDER)}; }}
QCalendarWidget QWidget {{ alternate-background-color: {hex(FIELD)}; }}
QCalendarWidget QToolButton {{ background: {hex(CARD)}; color: {hex(TEXT)}; border: none; border-radius: 6px; padding: 4px 8px; }}
QCalendarWidget QToolButton:hover {{ background: {hex(FIELD)}; }}
QCalendarWidget QAbstractItemView {{ background: {hex(CARD)}; color: {hex(TEXT)}; }}
QCalendarWidget QAbstractItemView:selected {{ background: {hex(ACCENT)}; color: white; }}
QCalendarWidget QAbstractItemView:disabled {{ color: {hex(MUTED)}; }}
"""

    TABLE_QSS = f"""
QTableWidget {{ background: {hex(CARD)}; border: 1px solid {hex(BORDER)}; border-radius: 14px;
               gridline-color: {hex(BORDER)}; font-size: 13px; alternate-background-color: {hex(FIELD)}; }}
QTableWidget::item {{ padding: 10px 12px; border: none; }}
QTableWidget::item:selected {{ background: {hex(SELECTION)}; color: {hex(TEXT)}; }}
QTableWidget::item:hover:!selected {{ background: {hex(FIELD)}; }}
QHeaderView::section {{ background: {hex(PRIMARY)}; color: white; font-weight: bold;
                       padding: 11px 10px; border: none; border-bottom: 2px solid {hex(BORDER)};
                       font-size: 12px; }}
QTableCornerButton::section {{ background: {hex(PRIMARY)}; border: none; }}
"""

    MISC_QSS = f"""
QWidget {{ color: {hex(TEXT)}; font-family: {FONT_FAMILY}; }}
QDialog {{ background: {hex(CARD)}; }}
QMessageBox {{ background: {hex(CARD)}; color: {hex(TEXT)}; }}
QLabel {{ color: {hex(TEXT)}; }}
QGroupBox {{ color: {hex(TEXT)}; font-weight: 700; border: 1px solid {hex(BORDER)}; border-radius: 12px; margin-top: 12px; padding: 14px; }}
QGroupBox::title {{ subcontrol-origin: margin; padding: 0 8px; color: {hex(ACCENT)}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {hex(BORDER)}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {hex(MUTED)}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {hex(BORDER)}; border-radius: 4px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: {hex(MUTED)}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QTabWidget::pane {{ border: 1px solid {hex(BORDER)}; border-radius: 12px; top: -1px; }}
QTabBar::tab {{ background: {hex(FIELD)}; padding: 9px 20px; border-radius: 8px; margin-right: 4px; color: {hex(MUTED)}; }}
QTabBar::tab:hover:!selected {{ background: {hex(BORDER)}; color: {hex(TEXT)}; }}
QTabBar::tab:selected {{ background: {hex(ACCENT)}; color: white; font-weight: bold; }}
QMenu {{ background: {hex(CARD)}; color: {hex(TEXT)}; border: 1px solid {hex(BORDER)}; border-radius: 8px; padding: 6px; }}
QMenu::item {{ padding: 8px 18px; border-radius: 6px; }}
QMenu::item:selected {{ background: {hex(ACCENT)}; color: white; }}
QToolTip {{ background: {hex(SECONDARY)}; color: white; border: 1px solid {hex(BORDER)}; border-radius: 6px; padding: 6px; }}
"""

    LOGIN_QSS = f"""
QWidget {{ background: {hex(PRIMARY)}; color: white; font-family: {FONT_FAMILY}; }}
QFrame#LoginCard {{ background: {hex(SECONDARY)}; border: 1px solid {hex(BORDER)}; border-radius: 18px; }}
QLabel#LoginTitle {{ font-size: 30px; font-weight: bold; color: {hex(ACCENT)}; }}
QLabel#LoginSub {{ color: #94a3b8; font-size: 13px; }}
QLabel#LoginErr {{ color: #fca5a5; font-size: 12px; }}
"""


def set_fonts(app):
    f = QFont(FONT_FAMILY, 10)
    app.setFont(f)


set_theme("dark")
