from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QMessageBox, QDialog, QDoubleSpinBox,
)
from PySide6.QtCore import Qt, QDate

import app.database as db
from app.i18n import _
from app.gui import style
from app.gui.widgets import (
    page_title, make_table, fill_table, primary_button, secondary_button,
    danger_button, make_date, form_field, make_input,
)


class ExpensesPage(QWidget):
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
        head.addWidget(page_title(_("expenses")))
        head.addStretch()
        b_add = primary_button(f"➕ {_('add_expense')}")
        b_add.clicked.connect(self.add_expense)
        b_edit = secondary_button(f"✏️ {_('edit')}")
        b_edit.clicked.connect(self.edit_expense)
        b_del = danger_button(f"🗑️ {_('delete')}")
        b_del.clicked.connect(self.delete_expense)
        b_exp = secondary_button(f"📊 {_('export')}")
        b_exp.clicked.connect(self.export)
        head.addWidget(b_add)
        head.addWidget(b_edit)
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
            [_("expense_date"), _("description"), _("category"), _("amount"), _("notes")],
            stretch_col=1,
        )
        layout.addWidget(self.table, 1)

        self.total_lbl = QLabel("")
        self.total_lbl.setStyleSheet(f"color:{style.ACCENT.name()}; font-size:16px; font-weight:bold;")
        layout.addWidget(self.total_lbl)



    def refresh(self):
        self._rows = db.fetch_all("SELECT * FROM expenses ORDER BY expense_date DESC, id DESC")
        self.apply_filter()

    def apply_filter(self, *_args):
        term = self.search.text().strip().lower()
        rows = [
            r for r in self._rows
            if not term or term in f"{r['description']} {r['category'] or ''} {r['notes'] or ''}".lower()
        ]
        fill_table(
            self.table,
            [
                (r["expense_date"], r["description"], r["category"] or "-",
                 f'{r["amount"]:.2f}', r["notes"] or "")
                for r in rows
            ],
        )
        for i, r in enumerate(rows):
            self.table.item(i, 0).setData(Qt.UserRole, r["id"])
        total = sum(r["amount"] for r in rows)
        self.total_lbl.setText(
            f"{_('expense_total')}: {total:.2f} {db.get_setting('currency', '')}"
        )

    def selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, _("app_title"), _("select_member"))
            return None
        item = self.table.item(row, 0)
        return int(item.data(Qt.UserRole)) if item and item.data(Qt.UserRole) else None

    def add_expense(self):
        dlg = ExpenseDialog(self.app_ctx, self)
        if dlg.exec():
            self.refresh()

    def edit_expense(self):
        eid = self.selected_id()
        if eid is None:
            return
        rec = db.fetch_one("SELECT * FROM expenses WHERE id=?", (eid,))
        dlg = ExpenseDialog(self.app_ctx, self, record=rec)
        if dlg.exec():
            self.refresh()

    def delete_expense(self):
        eid = self.selected_id()
        if eid is None:
            return
        if QMessageBox.question(self, _("app_title"), _("confirm_delete")) == QMessageBox.Yes:
            db.execute("DELETE FROM expenses WHERE id=?", (eid,))
            self.refresh()

    def export(self):
        from app.export import export_table
        import os
        import webbrowser
        headers = [_("expense_date"), _("description"), _("category"),
                   _("amount"), _("notes")]
        rows = [
            (r["expense_date"], r["description"], r["category"] or "-",
             r["amount"], r["notes"] or "")
            for r in self._rows
        ]
        path = export_table(headers, rows, "expenses")
        if not path:
            QMessageBox.warning(self, _("app_title"), _("error_save"))
            return
        webbrowser.open(os.path.abspath(path))
        QMessageBox.information(self, _("app_title"), _("export_done"))

    def _on_double_click(self, row, col):
        self.edit_expense()


class ExpenseDialog(QDialog):
    def __init__(self, app_ctx, parent=None, record=None):
        super().__init__(parent)
        self.app_ctx = app_ctx
        self.record = record
        self.setWindowTitle(_("edit_expense") if record else _("add_expense"))
        self.resize(400, 360)
        self.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(0, 1)

        self.date = make_date()
        form_field(grid, _("expense_date"), self.date)

        self.description = make_input()
        form_field(grid, _("description"), self.description)

        self.category = make_input()
        self.category.setPlaceholderText(_("category"))
        form_field(grid, _("category"), self.category)

        self.amount = QDoubleSpinBox()
        self.amount.setRange(0, 1000000)
        self.amount.setDecimals(2)
        self.amount.setStyleSheet(style.INPUT_QSS)
        form_field(grid, _("amount") + " *", self.amount)

        self.notes = make_input()
        self.notes.setPlaceholderText(_("notes"))
        form_field(grid, _("notes"), self.notes)

        lay.addLayout(grid)

        if record:
            self.date.setDate(QDate.fromString(record["expense_date"], "yyyy-MM-dd"))
            self.description.setText(record["description"])
            self.category.setText(record["category"] or "")
            self.amount.setValue(record["amount"])
            self.notes.setText(record["notes"] or "")

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
        desc = self.description.text().strip()
        if not desc or self.amount.value() <= 0:
            QMessageBox.warning(self, _("app_title"), _("error_save"))
            return
        date_str = self.date.date().toString("yyyy-MM-dd")
        category = self.category.text().strip()
        notes = self.notes.text().strip()
        if self.record:
            db.execute(
                """UPDATE expenses SET expense_date=?, description=?, amount=?,
                   category=?, notes=? WHERE id=?""",
                (date_str, desc, self.amount.value(), category, notes, self.record["id"]),
            )
        else:
            db.execute(
                """INSERT INTO expenses (expense_date, description, amount, category, notes)
                   VALUES (?,?,?,?,?)""",
                (date_str, desc, self.amount.value(), category, notes),
            )
        self.accept()
