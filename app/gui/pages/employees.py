from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QDialog, QComboBox, QDoubleSpinBox, QTextEdit, QMessageBox, QFrame,
    QPushButton,
)
from PySide6.QtCore import Qt, QDate
from datetime import datetime, timedelta

import app.database as db
import app.whatsapp as wa
from app.i18n import _
from app.gui import style
from app.gui.widgets import (
    page_title, make_table, fill_table, primary_button, secondary_button,
    danger_button, success_button, make_date, form_field, make_input,
)


class EmployeesPage(QWidget):
    def __init__(self, app_ctx, main):
        super().__init__()
        self.app_ctx, self.main, self.rows = app_ctx, main, []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        header = QHBoxLayout()
        header.addWidget(page_title(_("employees")))
        header.addStretch()
        for label, callback, kind in [
            (f"➕ {_('add_employee')}", self.add_employee, "primary"),
            (f"✏️ {_('edit')}", self.edit_employee, "secondary"),
            (f"🗑️ {_('delete')}", self.delete_employee, "danger"),
        ]:
            button = {"primary": primary_button, "secondary": secondary_button, "danger": danger_button}[kind](label)
            button.clicked.connect(callback)
            header.addWidget(button)
        layout.addLayout(header)

        self.search = QLineEdit()
        self.search.setPlaceholderText(_("search"))
        self.search.setStyleSheet(style.INPUT_QSS)
        self.search.textChanged.connect(self.refresh)
        layout.addWidget(self.search)
        self.table = make_table([_("code"), _("full_name"), _("position"), _("phone"), _("monthly_salary"), _("hire_date"), _("whatsapp"), _("status")], stretch_col=1)
        layout.addWidget(self.table, 1)
        self.table.setColumnWidth(7, 80)

        action_cards = QHBoxLayout()
        action_cards.setSpacing(14)
        action_cards.addWidget(self._action_card(
            _("record_transactions"),
            [
                (f"💵 {_('record_salary')}", self.record_salary, success_button),
                (f"⏱️ {_('record_overtime')}", self.record_overtime, primary_button),
                (f"💳 {_('record_advance')}", self.record_advance, secondary_button),
                (f"📅 {_('record_leave')}", self.record_leave, secondary_button),
            ],
        ), 1)
        action_cards.addWidget(self._action_card(
            _("view_employee_details"),
            [
                (f"📋 {_('view_salaries')}", lambda: self.show_history("salary"), secondary_button),
                (f"📋 {_('view_overtime')}", lambda: self.show_history("overtime"), secondary_button),
                (f"📋 {_('view_advances')}", lambda: self.show_history("advance"), secondary_button),
                (f"📋 {_('view_leaves')}", lambda: self.show_history("leave"), secondary_button),
            ],
        ), 1)
        action_cards.addWidget(self._payroll_card(), 1)
        layout.addLayout(action_cards)
        self.summary = QLabel()
        self.summary.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px;")
        layout.addWidget(self.summary)

    def _action_card(self, title, actions):
        card = QFrame(); card.setObjectName("Card"); card.setStyleSheet(style.CARD_QSS)
        layout = QVBoxLayout(card); layout.setContentsMargins(16, 14, 16, 16); layout.setSpacing(10)
        label = QLabel(title); label.setStyleSheet(f"color:{style.TEXT.name()}; font-size:14px; font-weight:bold;")
        layout.addWidget(label)
        grid = QGridLayout(); grid.setHorizontalSpacing(8); grid.setVerticalSpacing(8)
        for index, (text, callback, factory) in enumerate(actions):
            button = factory(text); button.setMinimumHeight(38); button.clicked.connect(callback)
            grid.addWidget(button, index // 2, index % 2)
        layout.addLayout(grid)
        return card

    def _payroll_card(self):
        card = QFrame(); card.setObjectName("Card"); card.setStyleSheet(style.CARD_QSS)
        layout = QVBoxLayout(card); layout.setContentsMargins(16, 14, 16, 16); layout.setSpacing(9)
        title = QLabel(_("monthly_payroll")); title.setStyleSheet(f"color:{style.ACCENT.name()}; font-size:15px; font-weight:bold;")
        note = QLabel(_("payroll_card_help")); note.setWordWrap(True); note.setStyleSheet(f"color:{style.MUTED.name()}; font-size:12px;")
        button = primary_button(f"📊 {_('open_monthly_payroll')}"); button.setMinimumHeight(42); button.clicked.connect(self.show_monthly_payroll)
        layout.addWidget(title); layout.addWidget(note); layout.addStretch(); layout.addWidget(button)
        return card

    def refresh(self, *_args):
        term = self.search.text().strip() if hasattr(self, "search") else ""
        where, params = "", ()
        if term:
            where, params = "WHERE full_name LIKE ? OR code LIKE ? OR phone LIKE ?", (f"%{term}%",) * 3
        self.rows = db.fetch_all(f"SELECT * FROM employees {where} ORDER BY is_active DESC, full_name", params)
        currency = db.get_setting("currency", "")
        fill_table(self.table, [(r["code"] or "-", r["full_name"], r["position"] or "-", r["phone"] or "-", f'{r["monthly_salary"]:.2f} {currency}', r["hire_date"] or "-", "", "") for r in self.rows])
        for index, row in enumerate(self.rows):
            self.table.item(index, 0).setData(Qt.UserRole, row["id"])
            # toggle active/inactive button
            status = row["is_active"]
            toggle_btn = QPushButton(_("inactive") if status else _("active"))
            toggle_btn.setCursor(Qt.PointingHandCursor)
            toggle_btn.setMinimumHeight(28)
            toggle_btn.setStyleSheet(
                f"QPushButton {{ background: {'#e74c3c' if status else '#2ecc71'}; color: white; border: none; border-radius: 10px; padding: 4px 10px; font-size: 11px; }}"
                f"QPushButton:hover {{ opacity: 0.8; }}"
            )
            toggle_btn.clicked.connect(lambda _, idx=index: self._on_toggle(idx))
            self.table.setCellWidget(index, 7, toggle_btn)
            # whatsapp button
            btn = QPushButton(_("whatsapp"))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(28)
            phone = (row["phone"] or "").strip()
            btn.setEnabled(bool(phone))
            if phone:
                btn.clicked.connect(lambda _=False, p=phone: wa.open_whatsapp(p))
            self.table.setCellWidget(index, 6, btn)
        total = sum(r["monthly_salary"] for r in self.rows)
        self.summary.setText(f"{_('employees')}: {len(self.rows)}  |  {_('monthly_salaries_total')}: {total:.2f} {currency}")

    def selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, _("app_title"), _("select_employee"))
            return None
        return self.table.item(row, 0).data(Qt.UserRole)

    def add_employee(self):
        if EmployeeDialog(self.app_ctx, self).exec(): self.refresh()

    def edit_employee(self):
        eid = self.selected_id()
        if eid and EmployeeDialog(self.app_ctx, self, db.fetch_one("SELECT * FROM employees WHERE id=?", (eid,))).exec(): self.refresh()

    def delete_employee(self):
        eid = self.selected_id()
        if eid and QMessageBox.question(self, _("app_title"), _("confirm_delete")) == QMessageBox.Yes:
            db.delete_employee(eid); self.refresh()

    def toggle_employee(self):
        eid = self.selected_id()
        if eid is None:
            return
        active = db.toggle_employee(eid)
        label = _("active") if active else _("inactive")
        QMessageBox.information(self, _("app_title"), f"{_('employee_status')}: {label}")
        self.refresh()

    def _on_toggle(self, index):
        row = self.table.item(index, 0)
        if row is None:
            return
        eid = row.data(Qt.UserRole)
        if eid is None:
            return
        self.toggle_employee()

    def record_salary(self): self._record("salary")
    def record_advance(self): self._record("advance")
    def record_leave(self): self._record("leave")
    def record_overtime(self): self._record("overtime")
    def show_history(self, kind):
        eid = self.selected_id()
        if eid:
            employee = db.fetch_one("SELECT full_name FROM employees WHERE id=?", (eid,))
            HistoryDialog(eid, employee["full_name"], kind, self).exec()

    def _record(self, kind):
        eid = self.selected_id()
        if eid and RecordDialog(self.app_ctx, eid, kind, self).exec(): self.refresh()

    def show_monthly_payroll(self):
        eid = self.selected_id()
        if eid:
            MonthlyPayrollDialog(db.fetch_one("SELECT * FROM employees WHERE id=?", (eid,)), self).exec()


class EmployeeDialog(QDialog):
    def __init__(self, app_ctx, parent=None, record=None):
        super().__init__(parent); self.record = record
        self.setWindowTitle(_("edit_employee") if record else _("add_employee")); self.resize(440, 430)
        self.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")
        layout, grid = QVBoxLayout(self), QGridLayout(); layout.setContentsMargins(24, 24, 24, 24); grid.setSpacing(10)
        self.code, self.name, self.phone, self.position = make_input(), make_input(), make_input(), make_input()
        self.salary = QDoubleSpinBox(); self.salary.setRange(0, 1000000); self.salary.setDecimals(2); self.salary.setStyleSheet(style.INPUT_QSS)
        self.hire_date = make_date(); self.notes = QTextEdit(); self.notes.setStyleSheet(style.INPUT_QSS); self.notes.setMaximumHeight(70)
        for label, field in [(_("code"), self.code), (_("full_name") + " *", self.name), (_("phone"), self.phone), (_("position"), self.position), (_("monthly_salary"), self.salary), (_("hire_date"), self.hire_date), (_("notes"), self.notes)]: form_field(grid, label, field)
        layout.addLayout(grid)
        buttons = QHBoxLayout(); save, cancel = primary_button(_("save")), secondary_button(_("cancel")); save.clicked.connect(self.save); cancel.clicked.connect(self.reject); buttons.addWidget(cancel); buttons.addStretch(); buttons.addWidget(save); layout.addLayout(buttons)
        if record:
            self.code.setText(record["code"] or ""); self.name.setText(record["full_name"]); self.phone.setText(record["phone"] or ""); self.position.setText(record["position"] or ""); self.salary.setValue(record["monthly_salary"]); self.notes.setPlainText(record["notes"] or "")
            if record["hire_date"]: self.hire_date.setDate(QDate.fromString(record["hire_date"], "yyyy-MM-dd"))

    def save(self):
        if not self.name.text().strip(): QMessageBox.warning(self, _("app_title"), _("error_save")); return
        values = (self.code.text().strip() or None, self.name.text().strip(), self.phone.text().strip(), self.position.text().strip(), self.salary.value(), self.hire_date.date().toString("yyyy-MM-dd"), self.notes.toPlainText().strip())
        try:
            if self.record: db.execute("UPDATE employees SET code=?,full_name=?,phone=?,position=?,monthly_salary=?,hire_date=?,notes=? WHERE id=?", values + (self.record["id"],))
            else: db.execute("INSERT INTO employees (code,full_name,phone,position,monthly_salary,hire_date,notes) VALUES (?,?,?,?,?,?,?)", values)
            self.accept()
        except Exception: QMessageBox.warning(self, _("app_title"), _("error_save"))


class RecordDialog(QDialog):
    def __init__(self, app_ctx, employee_id, kind, parent=None, record=None):
        super().__init__(parent); self.employee_id, self.kind, self.record = employee_id, kind, record
        labels = {"salary": _("record_salary"), "advance": _("record_advance"), "leave": _("record_leave"), "overtime": _("record_overtime")}; self.setWindowTitle(labels[kind]); self.resize(400, 330)
        self.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")
        layout, grid = QVBoxLayout(self), QGridLayout(); layout.setContentsMargins(24, 24, 24, 24); grid.setSpacing(10)
        self.date = make_date(); self.amount = QDoubleSpinBox(); self.amount.setRange(0, 1000000); self.amount.setDecimals(2); self.amount.setStyleSheet(style.INPUT_QSS); self.notes = make_input()
        if kind == "leave":
            self.leave_type, self.end_date = make_input(), make_date()
            form_field(grid, _("leave_type"), self.leave_type); form_field(grid, _("start_date"), self.date); form_field(grid, _("end_date"), self.end_date); form_field(grid, _("leave_deduction") + " *", self.amount)
        elif kind == "overtime":
            self.hours = QDoubleSpinBox(); self.hours.setRange(0, 500); self.hours.setDecimals(2); self.hours.setStyleSheet(style.INPUT_QSS)
            form_field(grid, _("overtime_date"), self.date); form_field(grid, _("overtime_hours"), self.hours); form_field(grid, _("overtime_amount") + " *", self.amount)
        else:
            form_field(grid, _("payment_date") if kind == "salary" else _("advance_date"), self.date); form_field(grid, _("amount") + " *", self.amount)
            if kind == "salary": self.month = make_input(); self.month.setPlaceholderText("YYYY-MM"); form_field(grid, _("salary_month"), self.month)
        form_field(grid, _("notes"), self.notes); layout.addLayout(grid)
        buttons = QHBoxLayout(); save, cancel = primary_button(_("save")), secondary_button(_("cancel")); save.clicked.connect(self.save); cancel.clicked.connect(self.reject); buttons.addWidget(cancel); buttons.addStretch(); buttons.addWidget(save); layout.addLayout(buttons)
        if record:
            if kind == "leave":
                self.date.setDate(QDate.fromString(record["start_date"], "yyyy-MM-dd")); self.end_date.setDate(QDate.fromString(record["end_date"], "yyyy-MM-dd")); self.leave_type.setText(record["leave_type"] or ""); self.amount.setValue(record["deduction"] or 0)
            elif kind == "overtime":
                self.date.setDate(QDate.fromString(record["overtime_date"], "yyyy-MM-dd")); self.hours.setValue(record["hours"] or 0); self.amount.setValue(record["amount"])
            elif kind == "salary":
                self.date.setDate(QDate.fromString(record["payment_date"], "yyyy-MM-dd")); self.month.setText(record["salary_month"] or ""); self.amount.setValue(record["amount"])
            else:
                self.date.setDate(QDate.fromString(record["advance_date"], "yyyy-MM-dd")); self.amount.setValue(record["amount"])
            self.notes.setText(record["notes"] or "")

    def save(self):
        day, notes = self.date.date().toString("yyyy-MM-dd"), self.notes.text().strip()
        if self.kind == "leave":
            if self.end_date.date() < self.date.date(): QMessageBox.warning(self, _("app_title"), _("error_save")); return
            values = (self.leave_type.text().strip(), day, self.end_date.date().toString("yyyy-MM-dd"), self.amount.value(), notes)
            if self.record: db.execute("UPDATE employee_leaves SET leave_type=?,start_date=?,end_date=?,deduction=?,notes=? WHERE id=?", values + (self.record["id"],))
            else: db.execute("INSERT INTO employee_leaves (employee_id,leave_type,start_date,end_date,deduction,notes) VALUES (?,?,?,?,?,?)", (self.employee_id,) + values)
        elif self.amount.value() <= 0: QMessageBox.warning(self, _("app_title"), _("error_save")); return
        elif self.kind == "salary":
            month_text = self.month.text().strip()
            if month_text:
                try:
                    month_text = datetime.strptime(month_text, "%m-%Y").strftime("%Y-%m")
                except ValueError:
                    try:
                        month_text = datetime.strptime(month_text, "%Y-%m").strftime("%Y-%m")
                    except ValueError:
                        pass
            values = (day, month_text, self.amount.value(), notes)
            if self.record: db.execute("UPDATE employee_payrolls SET payment_date=?,salary_month=?,amount=?,notes=? WHERE id=?", values + (self.record["id"],))
            else: db.execute("INSERT INTO employee_payrolls (employee_id,payment_date,salary_month,amount,notes) VALUES (?,?,?,?,?)", (self.employee_id,) + values)
        elif self.kind == "overtime":
            values = (day, self.hours.value(), self.amount.value(), notes)
            if self.record: db.execute("UPDATE employee_overtime SET overtime_date=?,hours=?,amount=?,notes=? WHERE id=?", values + (self.record["id"],))
            else: db.execute("INSERT INTO employee_overtime (employee_id,overtime_date,hours,amount,notes) VALUES (?,?,?,?,?)", (self.employee_id,) + values)
        else:
            values = (day, self.amount.value(), notes)
            if self.record: db.execute("UPDATE employee_advances SET advance_date=?,amount=?,notes=? WHERE id=?", values + (self.record["id"],))
            else: db.execute("INSERT INTO employee_advances (employee_id,advance_date,amount,notes) VALUES (?,?,?,?)", (self.employee_id,) + values)
        self.accept()


class HistoryDialog(QDialog):
    def __init__(self, employee_id, employee_name, kind, parent=None):
        super().__init__(parent)
        self.employee_id, self.kind = employee_id, kind
        self.setMinimumSize(760, 480)
        self.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")
        configs = {
            "salary": (_("view_salaries"), "employee_payrolls", "payment_date", [_("payment_date"), _("salary_month"), _("amount"), _("notes")], ["payment_date", "salary_month", "amount", "notes"]),
            "advance": (_("view_advances"), "employee_advances", "advance_date", [_("advance_date"), _("amount"), _("notes")], ["advance_date", "amount", "notes"]),
            "leave": (_("view_leaves"), "employee_leaves", "start_date", [_("leave_type"), _("start_date"), _("end_date"), _("deduction"), _("notes")], ["leave_type", "start_date", "end_date", "deduction", "notes"]),
            "overtime": (_("view_overtime"), "employee_overtime", "overtime_date", [_("overtime_date"), _("overtime_hours"), _("amount"), _("notes")], ["overtime_date", "hours", "amount", "notes"]),
        }
        title, table_name, date_column, headers, fields = configs[kind]
        self.setWindowTitle(f"{title} — {employee_name}")
        layout = QVBoxLayout(self); layout.setContentsMargins(24, 24, 24, 24); layout.setSpacing(14)
        heading = QLabel(f"{title}: {employee_name}")
        heading.setStyleSheet(f"font-size:18px; font-weight:bold; color:{style.TEXT.name()};")
        layout.addWidget(heading)
        # month filter like MonthlyPayrollDialog (YYYY-MM)
        filt = QHBoxLayout()
        filt.addWidget(QLabel(_("payroll_month")))
        self.month = make_input()
        self.month.setPlaceholderText("YYYY-MM")
        self.month.setText(QDate.currentDate().toString("yyyy-MM"))
        self.month.setMaximumWidth(150)
        filt.addWidget(self.month)
        b_show = primary_button(_("calculate"))
        b_show.clicked.connect(self.refresh)
        filt.addWidget(b_show)
        b_all = secondary_button(_("all"))
        b_all.clicked.connect(self._show_all)
        filt.addWidget(b_all)
        b_print = secondary_button(f"🖨 {_('export_pdf')}")
        b_print.clicked.connect(self._print_month)
        filt.addWidget(b_print)
        filt.addStretch()
        layout.addLayout(filt)
        self._status = QLabel("")
        self._status.setStyleSheet(f"color:{style.MUTED.name()}; font-size:12px;")
        layout.addWidget(self._status)
        self.table_name, self.date_column, self.fields = table_name, date_column, fields
        self.table = make_table(headers, stretch_col=len(headers) - 1)
        layout.addWidget(self.table, 1)
        self.total_label = QLabel("")
        self.total_label.setStyleSheet(f"color:{style.ACCENT.name()}; font-size:15px; font-weight:bold;")
        layout.addWidget(self.total_label)
        edit = primary_button(f"✏️ {_('edit_selected')}"); edit.clicked.connect(self.edit_selected)
        delete = danger_button(f"🗑️ {_('delete')}"); delete.clicked.connect(self.delete_selected)
        close = secondary_button(_("close")); close.clicked.connect(self.accept)
        buttons = QHBoxLayout(); buttons.addWidget(delete); buttons.addWidget(edit); buttons.addStretch(); buttons.addWidget(close); layout.addLayout(buttons)
        self.refresh()

    def _show_all(self):
        self.month.setText("")
        self.refresh()

    def _month_range(self):
        txt = self.month.text().strip()
        if not txt:
            return None, None, ""
        # accept YYYY-MM or MM-YYYY
        for fmt in ("%Y-%m", "%m-%Y"):
            try:
                dt = datetime.strptime(txt, fmt)
                txt = dt.strftime("%Y-%m")
                break
            except ValueError:
                continue
        try:
            start = datetime.strptime(txt + "-01", "%Y-%m-%d")
            nxt = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            end = (nxt - timedelta(days=1)).strftime("%Y-%m-%d")
            return start.strftime("%Y-%m-%d"), end, txt
        except ValueError:
            return None, None, txt

    def _print_month(self):
        if not self.rows:
            QMessageBox.information(self, _("app_title"), _("no_data"))
            return
        import os, webbrowser
        from app.invoice import print_employee_history_pdf
        s, e, m = self._month_range()
        path = print_employee_history_pdf(self.employee_id, self.kind, self.rows, m or _("all"), s, e)
        if path and os.path.exists(path):
            webbrowser.open("file://" + os.path.abspath(path))
        else:
            QMessageBox.warning(self, _("app_title"), _("error_save"))

    def refresh(self):
        currency = db.get_setting("currency", "")
        s, e, m = self._month_range()
        if m and s is None:
            self._status.setText(_("invalid_month"))
            fill_table(self.table, [])
            self.total_label.setText("")
            return
        if s and e:
            if self.kind == "salary":
                month_alt = "-".join(reversed(m.split("-"))) if m else ""
                self.rows = db.fetch_all(
                    f"SELECT * FROM {self.table_name} WHERE employee_id=? AND (salary_month=? OR salary_month=? OR (salary_month='' AND payment_date BETWEEN ? AND ?)) ORDER BY {self.date_column} DESC, id DESC",
                    (self.employee_id, m, month_alt, s, e),
                )
                self._status.setText(f"{_('payroll_month')}: {m}")
            else:
                self.rows = db.fetch_all(
                    f"SELECT * FROM {self.table_name} WHERE employee_id=? AND {self.date_column} BETWEEN ? AND ? ORDER BY {self.date_column} DESC, id DESC",
                    (self.employee_id, s, e),
                )
                self._status.setText(f"{_('payroll_month')}: {m}")
        else:
            self.rows = db.fetch_all(f"SELECT * FROM {self.table_name} WHERE employee_id=? ORDER BY {self.date_column} DESC, id DESC", (self.employee_id,))
            self._status.setText(_("all") if not m else "")
        display = []
        for row in self.rows:
            values = []
            for field in self.fields:
                value = row[field]
                values.append(f"{value:.2f} {currency}" if field in ("amount", "deduction") else (value or "-"))
            display.append(tuple(values))
        fill_table(self.table, display)
        for index, row in enumerate(self.rows):
            self.table.item(index, 0).setData(Qt.UserRole, row["id"])
        total_field = "deduction" if self.kind == "leave" else "amount"
        total = sum(row[total_field] or 0 for row in self.rows)
        total_key = "leave_total_deduction" if self.kind == "leave" else "total"
        self.total_label.setText(f"{_(total_key)}: {total:.2f} {currency}")

    def delete_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, _("app_title"), _("select_record")); return
        record_id = self.table.item(row, 0).data(Qt.UserRole)
        if QMessageBox.question(self, _("app_title"), _("confirm_delete")) == QMessageBox.Yes:
            db.execute(f"DELETE FROM {self.table_name} WHERE id=?", (record_id,))
            self.refresh()

    def edit_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, _("app_title"), _("select_record")); return
        record_id = self.table.item(row, 0).data(Qt.UserRole)
        record = next((item for item in self.rows if item["id"] == record_id), None)
        if record and RecordDialog(None, self.employee_id, self.kind, self, record).exec():
            self.accept()


class MonthlyPayrollDialog(QDialog):
    """Monthly payroll statement: basic salary + overtime - deductions."""
    def __init__(self, employee, parent=None):
        super().__init__(parent)
        self.employee = employee
        self.setWindowTitle(f"{_('monthly_payroll')} — {employee['full_name']}")
        self.setMinimumSize(700, 470)
        self.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")
        layout = QVBoxLayout(self); layout.setContentsMargins(24, 24, 24, 24); layout.setSpacing(14)
        controls = QHBoxLayout()
        controls.addWidget(QLabel(_("payroll_month")))
        self.month = make_input(); self.month.setText(QDate.currentDate().toString("yyyy-MM")); self.month.setMaximumWidth(150)
        controls.addWidget(self.month)
        calculate = primary_button(_("calculate")); calculate.clicked.connect(self.refresh)
        controls.addWidget(calculate)
        b_print = secondary_button(f"🖨 {_('export_pdf')}")
        b_print.clicked.connect(self.print_payroll)
        controls.addWidget(b_print)
        controls.addStretch(); layout.addLayout(controls)
        self.table = make_table([_("payroll_section"), _("amount")], stretch_col=0)
        layout.addWidget(self.table, 1)
        self.note = QLabel(); self.note.setWordWrap(True); self.note.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px;")
        layout.addWidget(self.note)
        buttons = QHBoxLayout(); buttons.addStretch(); close = secondary_button(_("close")); close.clicked.connect(self.accept); buttons.addWidget(close); layout.addLayout(buttons)
        self.refresh()

    def refresh(self):
        month = self.month.text().strip()
        self._month = month
        self._currency = db.get_setting("currency", "")
        try:
            start = datetime.strptime(month + "-01", "%Y-%m-%d")
            next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            end = (next_month - timedelta(days=1)).strftime("%Y-%m-%d")
        except ValueError:
            self.note.setText(_("invalid_month")); fill_table(self.table, []); return
        start_text = start.strftime("%Y-%m-%d")
        eid = self.employee["id"]
        overtime = db.fetch_one("SELECT COALESCE(SUM(amount), 0) AS total FROM employee_overtime WHERE employee_id=? AND overtime_date BETWEEN ? AND ?", (eid, start_text, end))["total"]
        advances = db.fetch_one("SELECT COALESCE(SUM(amount), 0) AS total FROM employee_advances WHERE employee_id=? AND advance_date BETWEEN ? AND ?", (eid, start_text, end))["total"]
        leaves = db.fetch_one("SELECT COALESCE(SUM(deduction), 0) AS total FROM employee_leaves WHERE employee_id=? AND start_date BETWEEN ? AND ?", (eid, start_text, end))["total"]
        month_alt = "-".join(reversed(month.split("-"))) if month else ""
        paid = db.fetch_one("SELECT COALESCE(SUM(amount), 0) AS total FROM employee_payrolls WHERE employee_id=? AND (salary_month=? OR salary_month=? OR (salary_month='' AND payment_date BETWEEN ? AND ?))", (eid, month, month_alt, start_text, end))["total"]
        base = self.employee["monthly_salary"] or 0
        due = base + overtime - advances - leaves
        remaining = due - paid
        self._values = [
            (_("basic_salary"), base, False),
            (_("overtime_total"), overtime, False),
            (_("advances_total"), advances, False),
            (_("leave_deduction_total"), leaves, False),
            (_("net_salary_due"), due, True),
            (_("salaries_paid"), paid, False),
            (_("salary_remaining"), remaining, True),
        ]
        rows = [(t, f"{v:.2f} {self._currency}") for t, v, _ in self._values]
        fill_table(self.table, rows)
        self.note.setText(_("payroll_formula"))

    def print_payroll(self):
        if not hasattr(self, "_values"):
            return
        import os
        import webbrowser
        from app.invoice import print_payroll_pdf
        path = print_payroll_pdf(self.employee, self._month, self._values, self._currency)
        if path and os.path.exists(path):
            webbrowser.open("file://" + os.path.abspath(path))
        else:
            QMessageBox.warning(self, _("app_title"), _("error_save"))
