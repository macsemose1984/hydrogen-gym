from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
)
from PySide6.QtCore import QDate

import app.database as db
from app.i18n import _
from app.gui import style
from app.gui.widgets import (
    page_title, make_table, fill_table, primary_button, secondary_button, make_date,
)
from app.invoice import print_daily_statement


class DailyStatementPage(QWidget):
    def __init__(self, app_ctx, main):
        super().__init__()
        self.app_ctx = app_ctx
        self.main = main
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        head = QHBoxLayout()
        head.addWidget(page_title(_("daily_statement")))
        head.addStretch()
        layout.addLayout(head)

        bar = QHBoxLayout()
        bar.addWidget(QLabel(_("date")))
        self.date = make_date()
        self.date.setDate(QDate.currentDate())
        self.date.setDisplayFormat("yyyy-MM-dd")
        self.date.setCalendarPopup(True)
        self.date.setEnabled(True)
        self.date.setReadOnly(False)
        self.date.setWrapping(False)
        # يسمح بالكتابة المباشرة + التقويم + تحديث تلقائي عند التغيير
        self.date.setStyleSheet(style.INPUT_QSS + " QDateEdit { padding: 6px 10px; }")
        self.date.dateChanged.connect(self.refresh)
        self.date.setToolTip(_("date_edit_tip"))
        bar.addWidget(self.date)
        b_refresh = primary_button(f"\u21bb {_('refresh')}")
        b_refresh.clicked.connect(self.refresh)
        bar.addWidget(b_refresh)
        b_print = primary_button(f"\U0001F5A8 {_('print')}")
        b_print.clicked.connect(self.print_statement)
        bar.addWidget(b_print)
        bar.addStretch()
        layout.addLayout(bar)

        card = QFrame()
        card.setObjectName("Card")
        card.setStyleSheet(style.CARD_QSS)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 16)
        title1 = QLabel(_("paid_subscriptions"))
        title1.setStyleSheet(f"color:{style.ACCENT.name()}; font-size:15px; font-weight:bold;")
        cl.addWidget(title1)
        self.subs_table = make_table(
            [_("member"), _("plan"), _("amount"), _("payment_method"), _("date")],
            stretch_col=1,
        )
        self.subs_table.cellDoubleClicked.connect(self.edit_subscription_payment)
        cl.addWidget(self.subs_table)
        self.subs_total = QLabel("")
        self.subs_total.setStyleSheet(f"color:{style.ACCENT.name()}; font-size:15px; font-weight:bold;")
        cl.addWidget(self.subs_total)
        self.subs_table.setColumnWidth(4, 100)
        b_edit_sub = secondary_button(f"✏️ {_('edit')}")
        b_edit_sub.clicked.connect(self.edit_subscription_payment)
        cl.addWidget(b_edit_sub)
        layout.addWidget(card)

        card2 = QFrame()
        card2.setObjectName("Card")
        card2.setStyleSheet(style.CARD_QSS)
        cl2 = QVBoxLayout(card2)
        cl2.setContentsMargins(16, 14, 16, 16)
        title2 = QLabel(_("expenses"))
        title2.setStyleSheet(f"color:{style.ACCENT.name()}; font-size:15px; font-weight:bold;")
        cl2.addWidget(title2)
        self.exp_table = make_table(
            [_("description"), _("category"), _("amount")],
            stretch_col=1,
        )
        self.exp_table.cellDoubleClicked.connect(self.edit_expense)
        cl2.addWidget(self.exp_table)
        self.exp_total = QLabel("")
        self.exp_total.setStyleSheet(f"color:{style.ACCENT.name()}; font-size:15px; font-weight:bold;")
        cl2.addWidget(self.exp_total)
        b_edit_exp = secondary_button(f"✏️ {_('edit')}")
        b_edit_exp.clicked.connect(self.edit_expense)
        cl2.addWidget(b_edit_exp)
        layout.addWidget(card2)

        layout.addStretch()

    def refresh(self):
        day = self.date.date().toString("yyyy-MM-dd")
        currency = db.get_setting("currency", "")
        subs = db.fetch_all(
            """SELECT p.id, p.payment_date, p.subscription_id, p.amount, p.payment_method, m.full_name, pm.name AS plan_name
                FROM payments p
                JOIN members m ON p.member_id = m.id
                LEFT JOIN subscriptions s ON p.subscription_id = s.id
                LEFT JOIN plans pm ON s.plan_id = pm.id
                WHERE p.payment_date = ? ORDER BY p.id""",
            (day,),
        )
        self._subs_rows = subs
        rows = [(r["full_name"], r["plan_name"] or "-", f'{r["amount"]:.2f} {currency}', r["payment_method"], r["payment_date"]) for r in subs]
        fill_table(self.subs_table, rows)
        for i, r in enumerate(subs):
            self.subs_table.item(i, 0).setData(0x0100, r["id"])
            self.subs_table.item(i, 4).setData(0x0100, r["payment_date"])
        subs_total = sum(r["amount"] for r in subs)
        method_totals = {}
        for r in subs:
            m = r["payment_method"] or ""
            method_totals[m] = method_totals.get(m, 0) + r["amount"]
        parts = [
            f"{_('total_paid')}: {subs_total:.2f} {currency}",
            f"{_('total_cash')}: {method_totals.get('نقدي', 0):.2f} {currency}",
            f"{_('total_card')}: {method_totals.get('بطاقة', 0):.2f} {currency}",
            f"{_('total_transfer')}: {method_totals.get('تحويل بنكي', 0):.2f} {currency}",
        ]
        self.subs_total.setText(" | ".join(parts))

        exps = db.fetch_all(
            "SELECT id, description, category, amount FROM expenses WHERE expense_date = ? ORDER BY id",
            (day,),
        )
        self._exps_rows = exps
        rows2 = [(r["description"], r["category"] or "-", f'{r["amount"]:.2f} {currency}') for r in exps]
        fill_table(self.exp_table, rows2)
        for i, r in enumerate(exps):
            self.exp_table.item(i, 0).setData(0x0100, r["id"])
        exp_total = sum(r["amount"] for r in exps)
        self.exp_total.setText(f"{_('total_expenses')}: {exp_total:.2f} {currency}")

    def edit_subscription_payment(self, *_args):
        row = self.subs_table.currentRow()
        if row < 0 or not hasattr(self, "_subs_rows") or row >= len(self._subs_rows):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, _("app_title"), _("select_member"))
            return
        pid = self._subs_rows[row]["id"]
        rec = db.fetch_one("SELECT * FROM payments WHERE id=?", (pid,))
        if not rec:
            return
        from PySide6.QtWidgets import QDialog, QGridLayout, QLineEdit, QDoubleSpinBox, QComboBox, QHBoxLayout
        from PySide6.QtWidgets import QMessageBox as _Msg
        dlg = QDialog(self)
        dlg.setWindowTitle(_("edit"))
        dlg.resize(380, 260)
        dlg.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)
        grid = QGridLayout()
        from app.gui.widgets import make_date as _make_date
        from PySide6.QtCore import QDate as _QDate
        date_edit = _make_date()
        _d = _QDate.fromString((rec["payment_date"] or "")[:10], "yyyy-MM-dd")
        if _d.isValid():
            date_edit.setDate(_d)
        else:
            date_edit.setDate(_QDate.currentDate())
        date_edit.setDisplayFormat("yyyy-MM-dd")
        date_edit.setCalendarPopup(True)
        amt = QDoubleSpinBox()
        amt.setRange(0.01, 1000000)
        amt.setDecimals(2)
        amt.setValue(rec["amount"])
        amt.setStyleSheet(style.INPUT_QSS)
        grid.addWidget(QLabel(_("date")), 0, 0)
        grid.addWidget(date_edit, 0, 1)
        grid.addWidget(QLabel(_("amount")), 1, 0)
        grid.addWidget(amt, 1, 1)
        meth = QComboBox()
        meth.addItems([_("cash"), _("card"), _("transfer")])
        meth.setStyleSheet(style.INPUT_QSS)
        idx = meth.findText(rec["payment_method"])
        if idx >= 0:
            meth.setCurrentIndex(idx)
        else:
            meth.setCurrentText(rec["payment_method"] or "")
        grid.addWidget(QLabel(_("payment_method")), 2, 0)
        grid.addWidget(meth, 2, 1)
        lay.addLayout(grid)
        btns = QHBoxLayout()
        from app.gui.widgets import primary_button as _pb, secondary_button as _sb
        b_ok = _pb(_("save"))
        b_cancel = _sb(_("cancel"))
        def _save():
            if amt.value() <= 0:
                _Msg.warning(dlg, _("app_title"), _("error_save"))
                return
            new_date = date_edit.date().toString("yyyy-MM-dd")
            db.execute("UPDATE payments SET amount=?, payment_method=?, payment_date=? WHERE id=?", (amt.value(), meth.currentText(), new_date, pid))
            if rec["subscription_id"]:
                sid = rec["subscription_id"]
                total = db.fetch_one("SELECT COALESCE(SUM(amount),0) AS t FROM payments WHERE subscription_id=?", (sid,))
                total_val = total["t"] if total else 0
                methods = db.fetch_all("SELECT DISTINCT payment_method FROM payments WHERE subscription_id=?", (sid,))
                mstr = "+".join(m["payment_method"] for m in methods if m["payment_method"]) if methods else meth.currentText()
                db.execute("UPDATE subscriptions SET price_paid=?, payment_method=? WHERE id=?", (total_val, mstr, sid))
            db.log_user_action("تعديل دفعة (كشف يومي)", "دفعة", f"#{pid}", f"{amt.value():.2f} {meth.currentText()}")
            dlg.accept()
        b_ok.clicked.connect(_save)
        b_cancel.clicked.connect(dlg.reject)
        btns.addWidget(b_cancel)
        btns.addStretch()
        btns.addWidget(b_ok)
        lay.addLayout(btns)
        if dlg.exec():
            self.refresh()

    def edit_expense(self, *_args):
        row = self.exp_table.currentRow()
        if row < 0 or not hasattr(self, "_exps_rows") or row >= len(self._exps_rows):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, _("app_title"), _("select_member"))
            return
        eid = self._exps_rows[row]["id"]
        rec = db.fetch_one("SELECT * FROM expenses WHERE id=?", (eid,))
        if not rec:
            return
        from PySide6.QtWidgets import QDialog, QGridLayout, QLineEdit, QDoubleSpinBox, QHBoxLayout
        from PySide6.QtWidgets import QMessageBox as _Msg
        dlg = QDialog(self)
        dlg.setWindowTitle(_("edit"))
        dlg.resize(400, 280)
        dlg.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)
        grid = QGridLayout()
        desc = QLineEdit(rec["description"])
        desc.setStyleSheet(style.INPUT_QSS)
        grid.addWidget(QLabel(_("description")), 0, 0)
        grid.addWidget(desc, 0, 1)
        cat = QLineEdit(rec["category"] or "")
        cat.setStyleSheet(style.INPUT_QSS)
        grid.addWidget(QLabel(_("category")), 1, 0)
        grid.addWidget(cat, 1, 1)
        amt = QDoubleSpinBox()
        amt.setRange(0.01, 1000000)
        amt.setDecimals(2)
        amt.setValue(rec["amount"])
        amt.setStyleSheet(style.INPUT_QSS)
        grid.addWidget(QLabel(_("amount")), 2, 0)
        grid.addWidget(amt, 2, 1)
        from app.gui.widgets import make_date as _make_date2
        from PySide6.QtCore import QDate as _QDate2
        date_edit = _make_date2()
        _d2 = _QDate2.fromString((rec["expense_date"] or "")[:10], "yyyy-MM-dd")
        if _d2.isValid():
            date_edit.setDate(_d2)
        else:
            date_edit.setDate(_QDate2.currentDate())
        date_edit.setDisplayFormat("yyyy-MM-dd")
        date_edit.setCalendarPopup(True)
        grid.addWidget(QLabel(_("date")), 3, 0)
        grid.addWidget(date_edit, 3, 1)
        lay.addLayout(grid)
        btns = QHBoxLayout()
        from app.gui.widgets import primary_button as _pb, secondary_button as _sb
        b_ok = _pb(_("save"))
        b_cancel = _sb(_("cancel"))
        def _save():
            if not desc.text().strip() or amt.value() <= 0:
                _Msg.warning(dlg, _("app_title"), _("error_save"))
                return
            new_date = date_edit.date().toString("yyyy-MM-dd")
            db.execute("UPDATE expenses SET description=?, category=?, amount=?, expense_date=? WHERE id=?",
                       (desc.text().strip(), cat.text().strip(), amt.value(), new_date, eid))
            db.log_user_action("تعديل مصروف (كشف يومي)", "مصروف", desc.text().strip(), f"{amt.value():.2f}")
            dlg.accept()
        b_ok.clicked.connect(_save)
        b_cancel.clicked.connect(dlg.reject)
        btns.addWidget(b_cancel)
        btns.addStretch()
        btns.addWidget(b_ok)
        lay.addLayout(btns)
        if dlg.exec():
            self.refresh()

    def print_statement(self):
        day = self.date.date().toString("yyyy-MM-dd")
        print_daily_statement(day)