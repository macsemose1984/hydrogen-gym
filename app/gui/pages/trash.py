from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QLineEdit,
)
from PySide6.QtCore import Qt

import app.database as db
from app.i18n import _
from app.gui import style
from app.gui.widgets import (
    page_title, make_table, fill_table, primary_button, secondary_button,
    danger_button,
)


class TrashPage(QWidget):
    def __init__(self, app_ctx, main):
        super().__init__()
        self.app_ctx = app_ctx
        self.main = main
        self._rows = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        head = QHBoxLayout()
        head.addWidget(page_title(_("trash")))
        head.addStretch()
        b_restore = primary_button(f"♻️ {_('restore')}")
        b_restore.clicked.connect(self.restore)
        b_empty = danger_button(f"🗑️ {_('empty_trash')}")
        b_empty.clicked.connect(self.empty_trash)
        head.addWidget(b_restore)
        head.addWidget(b_empty)
        layout.addLayout(head)

        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(f"🔍 {_('search')}...")
        self.search.textChanged.connect(self.apply_filter)
        self.search.setStyleSheet(style.INPUT_QSS)
        bar.addWidget(self.search, 1)
        layout.addLayout(bar)

        self.table = make_table(
            [_("table_name"), _("label"), _("deleted_at")],
            stretch_col=1,
        )
        layout.addWidget(self.table, 1)

        self.total_lbl = QLabel("")
        self.total_lbl.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px;")
        layout.addWidget(self.total_lbl)

    def refresh(self):
        self._rows = db.list_trash()
        self.apply_filter()

    def apply_filter(self, *_args):
        term = self.search.text().strip().lower()
        rows = [
            r for r in self._rows
            if not term or term in f"{self._name(r['table_name'])} {r['label']}".lower()
        ]
        fill_table(
            self.table,
            [(self._name(r["table_name"]), r["label"], r["deleted_at"]) for r in rows],
        )
        for i, r in enumerate(rows):
            self.table.item(i, 0).setData(Qt.UserRole, r["id"])
        self.total_lbl.setText(f"🗑️ {len(rows)}")

    def _name(self, table_name):
        return {
            "members": _("members"),
            "subscriptions": _("subscriptions"),
            "plans": _("plans"),
            "payments": _("payments"),
        }.get(table_name, table_name)

    def selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, _("app_title"), _("select_member"))
            return None
        item = self.table.item(row, 0)
        return int(item.data(Qt.UserRole)) if item and item.data(Qt.UserRole) else None

    def restore(self):
        tid = self.selected_id()
        if tid is None:
            return
        if db.restore_from_trash(tid):
            QMessageBox.information(self, _("app_title"), _("restored"))
        else:
            QMessageBox.warning(self, _("app_title"), _("error_save"))
        self.refresh()

    def empty_trash(self):
        if not self._rows:
            return
        if QMessageBox.question(self, _("app_title"), _("confirm_delete")) == QMessageBox.Yes:
            db.clear_trash()
            self.refresh()
