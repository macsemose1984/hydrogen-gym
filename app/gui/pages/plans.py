from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox,
    QDialog, QLineEdit,
)
from PySide6.QtCore import Qt

import app.database as db
from app.i18n import _
from app.gui import style
from app.gui.widgets import (
    page_title, make_table, fill_table, primary_button, secondary_button,
    danger_button, make_input, make_combo, form_field, make_date,
)
from app.gui.dialogs.plan_dialog import PlanDialog


class PlansPage(QWidget):
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
        head.addWidget(page_title(_("plans")))
        head.addStretch()
        b_add = primary_button(f"➕ {_('add')}")
        b_add.clicked.connect(self.add_plan)
        b_del = danger_button(f"🗑️ {_('delete')}")
        b_del.clicked.connect(self.delete_plan)
        b_exp = secondary_button(f"📊 {_('export')}")
        b_exp.clicked.connect(self.export)
        head.addWidget(b_add)
        head.addWidget(b_del)
        head.addWidget(b_exp)
        layout.addLayout(head)

        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(f"🔍 {_('search')}...")
        self.search.textChanged.connect(self.apply_filter)
        self.search.setStyleSheet(style.INPUT_QSS)
        bar.addWidget(self.search, 1)
        layout.addLayout(bar)

        self.table = make_table(
            [_("plan_name"), _("duration"), _("price"),
             _("sessions"), _("description"), _("status")],
            stretch_col=4,
        )
        layout.addWidget(self.table, 1)

        btn_row = QHBoxLayout()
        b_edit = secondary_button(f"✏️ {_('edit')}")
        b_edit.clicked.connect(self.edit_plan)
        btn_row.addWidget(b_edit)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def refresh(self):
        self._rows = db.fetch_all("SELECT * FROM plans ORDER BY id")
        self.apply_filter()

    def apply_filter(self, *_args):
        term = self.search.text().strip().lower()
        rows = [
            r for r in self._rows
            if not term or term in f"{r['name']} {r['description'] or ''}".lower()
        ]
        fill_table(
            self.table,
            [
                (r["name"], f"{r['duration_days']} {_('days')}",
                 f'{r["price"]:.2f}', r["sessions"],
                 r["description"], (_("active") if r["is_active"] else _("inactive")))
                for r in rows
            ],
        )
        for i, r in enumerate(rows):
            self.table.item(i, 0).setData(Qt.UserRole, r["id"])

    def selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, _("app_title"), _("select_plan"))
            return None
        item = self.table.item(row, 0)
        return int(item.data(Qt.UserRole))

    def add_plan(self):
        if PlanDialog(None, self).exec():
            self.refresh()

    def edit_plan(self):
        pid = self.selected_id()
        if pid is None:
            return
        rec = db.fetch_one("SELECT * FROM plans WHERE id=?", (pid,))
        if PlanDialog(rec, self).exec():
            self.refresh()

    def delete_plan(self):
        pid = self.selected_id()
        if pid is None:
            return
        if QMessageBox.question(self, _("app_title"), _("confirm_delete")) == QMessageBox.Yes:
            db.move_to_trash("plans", pid)
            self.refresh()

    def export(self):
        from app.export import export_table
        import os
        import webbrowser
        headers = [_("plan_name"), _("duration"), _("price"),
                   _("sessions"), _("description"), _("status")]
        rows = db.fetch_all("SELECT * FROM plans ORDER BY id")
        data = [
            (r["name"], f"{r['duration_days']} {_('days')}", r["price"],
             r["sessions"], r["description"],
             (_("active") if r["is_active"] else _("inactive")))
            for r in rows
        ]
        path = export_table(headers, data, "plans")
        if not path:
            QMessageBox.warning(self, _("app_title"), _("error_save"))
            return
        webbrowser.open(os.path.abspath(path))
        QMessageBox.information(self, _("app_title"), _("export_done"))