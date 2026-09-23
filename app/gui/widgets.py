from PySide6.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QLineEdit,
    QDateEdit, QSpinBox, QDoubleSpinBox, QCalendarWidget, QSizePolicy,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QIcon

import os

from app.gui import style
from app.i18n import _


def window_controls(dialog):
    """Add maximize/minimize buttons to a dialog's title bar."""
    dialog.setWindowFlags(
        dialog.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint
    )


def card(parent=None):
    frame = QFrame(parent)
    frame.setObjectName("Card")
    frame.setStyleSheet(style.CARD_QSS)
    return frame


def nav_button(text, checkable=True):
    btn = QPushButton(text)
    btn.setObjectName("Nav")
    btn.setCheckable(checkable)
    btn.setCursor(Qt.PointingHandCursor)
    return btn


def primary_button(text):
    btn = QPushButton(text)
    btn.setObjectName("Primary")
    btn.setCursor(Qt.PointingHandCursor)
    btn.setMinimumHeight(38)
    return btn


def secondary_button(text):
    btn = QPushButton(text)
    btn.setObjectName("Secondary")
    btn.setCursor(Qt.PointingHandCursor)
    btn.setMinimumHeight(38)
    return btn


def danger_button(text):
    btn = QPushButton(text)
    btn.setObjectName("Danger")
    btn.setCursor(Qt.PointingHandCursor)
    btn.setMinimumHeight(38)
    return btn


def success_button(text):
    btn = QPushButton(text)
    btn.setObjectName("Success")
    btn.setCursor(Qt.PointingHandCursor)
    btn.setMinimumHeight(38)
    return btn


def label(text="", cls="PageTitle"):
    lbl = QLabel(text)
    if cls:
        lbl.setObjectName(cls)
        lbl.setStyleSheet(style.CARD_QSS)
    return lbl


def page_title(text):
    return label(text, "PageTitle")


def section_title(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color:{style.ACCENT.name()}; font-size:15px; font-weight:bold;"
    )
    return lbl


def stat_card(icon, value, caption, color=style.ACCENT):
    cardf = QFrame()
    cardf.setObjectName("StatCard")
    cardf.setStyleSheet(style.CARD_QSS)
    lay = QVBoxLayout(cardf)
    lay.setContentsMargins(18, 16, 18, 16)
    lay.setSpacing(4)

    top = QHBoxLayout()
    ic = QLabel(icon)
    ic.setObjectName("StatIcon")
    ic.setStyleSheet(style.CARD_QSS)
    top.addWidget(ic)
    top.addStretch()
    lay.addLayout(top)

    val = QLabel(value)
    val.setObjectName("StatValue")
    val.setStyleSheet(style.CARD_QSS)
    lay.addWidget(val)

    cap = QLabel(caption)
    cap.setObjectName("StatLabel")
    cap.setStyleSheet(style.CARD_QSS)
    lay.addWidget(cap)
    return cardf


def make_table(headers, stretch_col=1):
    table = QTableWidget()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setSelectionMode(QTableWidget.SingleSelection)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(42)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    if stretch_col >= 0:
        table.horizontalHeader().setSectionResizeMode(stretch_col, QHeaderView.Stretch)
    table.setStyleSheet(style.TABLE_QSS)
    table.setShowGrid(False)
    return table


def make_input(width=None, placeholder=""):
    edit = QLineEdit()
    if width:
        edit.setFixedWidth(width)
    if placeholder:
        edit.setPlaceholderText(placeholder)
    edit.setStyleSheet(style.INPUT_QSS)
    return edit


def make_combo(items=None):
    cb = QComboBox()
    if items:
        cb.addItems(items)
    cb.setStyleSheet(style.INPUT_QSS)
    return cb


def make_date():
    de = QDateEdit()
    de.setCalendarPopup(True)
    de.setDisplayFormat("yyyy-MM-dd")
    de.setDate(QDate.currentDate())
    de.setStyleSheet(style.INPUT_QSS)
    return de


def form_field(parent_lay, text, widget):
    lbl = QLabel(text)
    lbl.setStyleSheet("color:%s; font-size:13px; font-weight:600;" % style.MUTED.name())
    if isinstance(parent_lay, QGridLayout):
        row = parent_lay.rowCount()
        parent_lay.addWidget(lbl, row, 0)
        parent_lay.addWidget(widget, row, 1)
    else:
        parent_lay.addWidget(lbl)
        parent_lay.addWidget(widget)


def clear_table(table):
    table.setRowCount(0)


def logo_path():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "assets", "logo.svg",
    )


def logo_pixmap(size):
    from PySide6.QtGui import QPixmap, QPainter
    path = logo_path()
    if not os.path.exists(path):
        return None
    
    if path.lower().endswith(".svg"):
        from PySide6.QtSvg import QSvgRenderer
        renderer = QSvgRenderer(path)
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        renderer.render(painter)
        painter.end()
        return pm
    else:
        pm = QPixmap(path)
        if not pm.isNull():
            return pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        return None


def logo_label(size):
    lbl = QLabel()
    pm = logo_pixmap(size)
    if pm is not None:
        lbl.setPixmap(pm)
    lbl.setAlignment(Qt.AlignCenter)
    return lbl


def fill_table(table, rows, hidden_cols=None):
    table.setRowCount(0)
    table.setRowCount(len(rows))
    hidden_cols = hidden_cols or set()
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            item = QTableWidgetItem(str(value))
            if c not in hidden_cols:
                table.setItem(r, c, item)


def notification_bar(text, type="info"):
    """Create a dismissible notification bar (QFrame with text + close button)."""
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QHBoxLayout, QPushButton, QFrame

    frame = QFrame()
    frame.setObjectName("Notification")
    bg = str(style.WARNING.name()) if type == "warning" else str(style.ACCENT.name())
    frame.setStyleSheet(
        f"#Notification {{ background: {bg}; border-radius: 10px; }}"
        f"QLabel {{ color: white; font-size: 12px; }}"
        f"QPushButton {{ background: transparent; color: white; border: none; font-size: 14px; padding: 0 6px; }}"
        f"QPushButton:hover {{ opacity: 0.7; }}"
    )
    frame.setMinimumHeight(36)
    lay = QHBoxLayout(frame)
    lay.setContentsMargins(12, 4, 8, 4)
    lay.setSpacing(8)

    icon = {"info": "ℹ️", "warning": "⚠️", "error": "❌"}.get(type, "ℹ️")
    lbl = QLabel(f"{icon} {text}")
    lbl.setWordWrap(True)
    lay.addWidget(lbl, 1)

    btn = QPushButton("✕")
    lay.addWidget(btn)
    btn.clicked.connect(frame.hide)

    frame.hide_timer = QTimer(frame)
    frame.hide_timer.setSingleShot(True)
    frame.hide_timer.timeout.connect(frame.hide)
    frame.hide_timer.start(8000)
    return frame
