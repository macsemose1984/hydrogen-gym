from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QMessageBox, QDialog, QComboBox, QPushButton,
)
from PySide6.QtCore import Qt

import app.database as db
import app.whatsapp as wa
from app.i18n import _
from app.gui import style
from app.gui.widgets import (
    page_title, make_table, fill_table, primary_button, secondary_button,
    danger_button, form_field, make_input,
)


class CoachesPage(QWidget):
    def __init__(self, app_ctx, main):
        super().__init__()
        self.app_ctx = app_ctx
        self.main = main
        self._rows = []
        self._build()
        self.table.cellDoubleClicked.connect(self._on_double_click)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        head = QHBoxLayout()
        head.addWidget(page_title(_("coaches")))
        head.addStretch()
        b_add = primary_button(f"➕ {_('add_coach')}")
        b_add.clicked.connect(self.add_coach)
        b_del = danger_button(f"🗑️ {_('delete')}")
        b_del.clicked.connect(self.delete_coach)
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

        self.filter = QComboBox()
        self.filter.addItems([_("all"), _("active"), _("inactive")])
        self.filter.currentIndexChanged.connect(self.apply_filter)
        self.filter.setStyleSheet(style.INPUT_QSS)
        bar.addWidget(self.filter)
        layout.addLayout(bar)

        self.table = make_table(
            [_("full_name"), _("phone"), _("specialty"), _("status"), _("whatsapp")],
            stretch_col=0,
        )
        layout.addWidget(self.table, 1)

        btn_row = QHBoxLayout()
        b_edit = secondary_button(f"✏️ {_('edit')}")
        b_edit.clicked.connect(self.edit_coach)
        btn_row.addWidget(b_edit)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def refresh(self):
        self._rows = db.fetch_all("SELECT * FROM coaches ORDER BY id")
        self.apply_filter()

    def apply_filter(self, *_args):
        term = self.search.text().strip().lower()
        mode = self.filter.currentIndex()  # 0 all, 1 active, 2 inactive
        rows = []
        for r in self._rows:
            if term and term not in f"{r['full_name']} {r['specialty']}".lower():
                continue
            if mode == 1 and not r["is_active"]:
                continue
            if mode == 2 and r["is_active"]:
                continue
            rows.append(r)
        fill_table(
            self.table,
            [
                (r["full_name"], r["phone"] or "-", r["specialty"] or "-",
                 (_("active") if r["is_active"] else _("inactive")), "")
                for r in rows
            ],
        )
        for i, r in enumerate(rows):
            self.table.item(i, 0).setData(Qt.UserRole, r["id"])
            btn = QPushButton(_("whatsapp"))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(28)
            phone = (r["phone"] or "").strip()
            btn.setEnabled(bool(phone))
            if phone:
                btn.clicked.connect(lambda _=False, p=phone: wa.open_whatsapp(p))
            self.table.setCellWidget(i, 4, btn)

    def selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, _("app_title"), _("select_member"))
            return None
        item = self.table.item(row, 0)
        return int(item.data(Qt.UserRole)) if item and item.data(Qt.UserRole) else None

    def add_coach(self):
        dlg = CoachDialog(self.app_ctx, self)
        if dlg.exec():
            self.refresh()

    def edit_coach(self):
        cid = self.selected_id()
        if cid is None:
            return
        rec = db.fetch_one("SELECT * FROM coaches WHERE id=?", (cid,))
        dlg = CoachDialog(self.app_ctx, self, record=rec)
        if dlg.exec():
            self.refresh()

    def delete_coach(self):
        cid = self.selected_id()
        if cid is None:
            return
        if QMessageBox.question(self, _("app_title"), _("confirm_delete")) == QMessageBox.Yes:
            db.execute("DELETE FROM coaches WHERE id=?", (cid,))
            self.refresh()

    def _on_double_click(self, row, col):
        self.edit_coach()

    def export(self):
        from app.export import export_table
        import os
        import webbrowser
        headers = [_("full_name"), _("phone"), _("specialty"), _("status")]
        rows = [
            (r["full_name"], r["phone"] or "-", r["specialty"] or "-",
             (_("active") if r["is_active"] else _("inactive")))
            for r in self._rows
        ]
        path = export_table(headers, rows, "coaches")
        if not path:
            QMessageBox.warning(self, _("app_title"), _("error_save"))
            return
        webbrowser.open(os.path.abspath(path))
        QMessageBox.information(self, _("app_title"), _("export_done"))


class CoachDialog(QDialog):
    def __init__(self, app_ctx, parent=None, record=None):
        super().__init__(parent)
        self.app_ctx = app_ctx
        self.record = record
        self.setWindowTitle(_("edit_coach") if record else _("add_coach"))
        self.resize(420, 420)
        self.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnMinimumWidth(0, 150)
        r = 0

        def _field(label, widget):
            nonlocal r
            lbl = QLabel(label)
            lbl.setStyleSheet("color:%s;font-size:13px;font-weight:600;" % style.MUTED.name())
            grid.addWidget(lbl, r, 0)
            grid.addWidget(widget, r, 1)
            r += 1

        self.name = make_input(placeholder=_("full_name"))
        self.name.setText(record["full_name"] if record else "")
        self.name.setMinimumHeight(40)
        _field(_("full_name") + " *", self.name)

        self.phone = make_input(placeholder=_("phone"))
        self.phone.setText(record["phone"] if record else "")
        self.phone.setMinimumHeight(40)
        _field(_("phone"), self.phone)

        self.specialty = make_input(placeholder=_("specialty"))
        self.specialty.setText(record["specialty"] if record else "")
        self.specialty.setMinimumHeight(40)
        _field(_("specialty"), self.specialty)

        self.is_active = QComboBox()
        self.is_active.addItems([_("active"), _("inactive")])
        if record and not record["is_active"]:
            self.is_active.setCurrentIndex(1)
        self.is_active.setStyleSheet(style.INPUT_QSS)
        self.is_active.setMinimumHeight(40)
        _field(_("status"), self.is_active)

        lay.addLayout(grid)

        n_lbl = QLabel(_("notes"))
        n_lbl.setStyleSheet("color:%s;font-size:13px;font-weight:600;" % style.MUTED.name())
        lay.addWidget(n_lbl)
        self.notes = QLineEdit()
        self.notes.setPlaceholderText(_("notes"))
        self.notes.setText(record["notes"] if record else "")
        self.notes.setStyleSheet(style.INPUT_QSS)
        lay.addWidget(self.notes)

        btns = QHBoxLayout()
        b_save = primary_button(_("save"))
        b_cancel = secondary_button(_("cancel"))
        b_save.clicked.connect(self.save)
        b_cancel.clicked.connect(self.reject)
        btns.addWidget(b_cancel)
        btns.addStretch()
        btns.addWidget(b_save)
        lay.addLayout(btns)

    def save(self):
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, _("app_title"), _("error_save"))
            return
        phone = self.phone.text().strip()
        specialty = self.specialty.text().strip()
        is_active = 1 if self.is_active.currentIndex() == 0 else 0
        notes = self.notes.text().strip()
        if self.record:
            db.execute(
                """UPDATE coaches SET full_name=?, phone=?, specialty=?, is_active=?, notes=?
                   WHERE id=?""",
                (name, phone, specialty, is_active, notes, self.record["id"]),
            )
        else:
            db.execute(
                """INSERT INTO coaches (full_name, phone, specialty, is_active, notes)
                   VALUES (?,?,?,?,?)""",
                (name, phone, specialty, is_active, notes),
            )
        self.accept()
