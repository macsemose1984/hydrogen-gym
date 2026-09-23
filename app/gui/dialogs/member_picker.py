from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton,
)
from PySide6.QtCore import Qt

import app.database as db
from app.i18n import _
from app.gui import style
from app.gui.widgets import primary_button, secondary_button, window_controls


class MemberPicker(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        window_controls(self)
        self.setWindowTitle(_("select_member"))
        self.resize(360, 480)
        self.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(10)

        self.search = QLineEdit()
        self.search.setPlaceholderText(f"🔍 {_('search')}...")
        self.search.setStyleSheet(style.INPUT_QSS)
        self.search.textChanged.connect(self._filter)
        lay.addWidget(self.search)

        self.listw = QListWidget()
        self._all = db.fetch_all(
            "SELECT id, full_name, phone, code FROM members WHERE is_active=1 ORDER BY full_name"
        )
        for m in self._all:
            item = QListWidgetItem(f"{m['full_name']} — {m['phone'] or '-'}")
            item.setData(Qt.UserRole, m["id"])
            self.listw.addItem(item)
        self.listw.setStyleSheet(
            f"QListWidget {{ background:{style.CARD.name()}; border:1px solid {style.BORDER.name()};"
            f" border-radius:10px; font-size:14px; color:{style.TEXT.name()}; }}"
            f"QListWidget::item {{ padding:10px; }}"
            f"QListWidget::item:selected {{ background:{style.SELECTION.name()}; color:{style.TEXT.name()}; }}"
        )
        self.listw.itemDoubleClicked.connect(lambda _: self.accept())
        lay.addWidget(self.listw, 1)

        btns = QHBoxLayout()
        b_ok = primary_button(_("save"))
        b_cancel = secondary_button(_("cancel"))
        b_ok.clicked.connect(self.accept)
        b_cancel.clicked.connect(self.reject)
        btns.addWidget(b_cancel)
        btns.addStretch()
        btns.addWidget(b_ok)
        lay.addLayout(btns)

    def _filter(self, text):
        term = text.strip().lower()
        for i, m in enumerate(self._all):
            match = not term or term in f"{m['full_name']} {m['phone']} {m['code']}".lower()
            self.listw.item(i).setHidden(not match)

    def selected_member(self):
        item = self.listw.currentItem()
        if item is None:
            return None
        mid = item.data(Qt.UserRole)
        return next((m for m in self._all if m["id"] == mid), None)