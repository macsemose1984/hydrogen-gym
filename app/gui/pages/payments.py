from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QMessageBox, QDialog, QDoubleSpinBox, QComboBox,
)
from PySide6.QtCore import Qt, QDate

import app.database as db
from app.i18n import _
from app.gui import style
from app.gui.widgets import (
    page_title, make_table, fill_table, primary_button, secondary_button,
    danger_button, make_date, form_field, make_combo, make_input,
)


class PaymentsPage(QWidget):
    """المدفوعات الآن تعرض سجل الاشتراكات (مثل الصورة) — لا تكرار."""
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
        head.addWidget(page_title(_("payments")))
        head.addStretch()
        # دفعة جديدة الآن تفتح تجديد اشتراك (يُنشئ سجل واحد فقط)
        b_add = primary_button(f"➕ {_('quick_payment')}")
        b_add.clicked.connect(self.add_payment)
        b_hist = secondary_button(f"📋 {_('payments_history')}")
        b_hist.clicked.connect(self.show_payments_history)
        b_del = danger_button(f"🗑️ {_('delete')}")
        b_del.clicked.connect(self.delete_payment)
        b_inv = secondary_button(f"🧾 {_('print_invoice')}")
        b_inv.clicked.connect(self.print_invoice)
        b_exp = secondary_button(f"📊 {_('export')}")
        b_exp.clicked.connect(self.export)
        head.addWidget(b_add)
        head.addWidget(b_hist)
        head.addWidget(b_del)
        head.addWidget(b_inv)
        head.addWidget(b_exp)
        layout.addLayout(head)

        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(f"🔍 {_('search')}...")
        self.search.textChanged.connect(self.apply_filter)
        self.search.setStyleSheet(style.INPUT_QSS)
        bar.addWidget(self.search, 1)
        layout.addLayout(bar)

        # نفس أعمدة سجل الاشتراكات في الصورة
        self.table = make_table(
            [_("member"), _("plan_name"), _("start_date"), _("end_date"),
             _("paid"), _("payment_method"), _("payment_date"), _("status"), _("notes")],
            stretch_col=0,
        )
        layout.addWidget(self.table, 1)
        self.table.setColumnWidth(6, 110)

        # pagination 50
        self._page = 0
        self._page_size = 50
        self._filtered = []
        pag = QHBoxLayout()
        self.btn_prev = secondary_button("‹")
        self.btn_prev.clicked.connect(self._prev_page)
        self.lbl_page = QLabel("")
        self.lbl_page.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px;")
        self.lbl_page.setAlignment(Qt.AlignCenter)
        self.btn_next = secondary_button("›")
        self.btn_next.clicked.connect(self._next_page)
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["50", "100", "الكل"])
        self.page_size_combo.setStyleSheet(style.INPUT_QSS)
        self.page_size_combo.setMaximumWidth(90)
        self.page_size_combo.currentIndexChanged.connect(self._change_page_size)
        pag.addWidget(self.btn_prev)
        pag.addWidget(self.lbl_page)
        pag.addWidget(self.btn_next)
        pag.addStretch()
        pag.addWidget(QLabel(_("show") + ":"))
        pag.addWidget(self.page_size_combo)
        layout.addLayout(pag)

        self.total_lbl = QLabel("")
        self.total_lbl.setStyleSheet(
            f"color:{style.ACCENT.name()}; font-size:16px; font-weight:bold;"
        )
        layout.addWidget(self.total_lbl)

        btn_row = QHBoxLayout()
        b_edit = secondary_button(f"✏️ {_('edit')}")
        b_edit.clicked.connect(self.edit_payment)
        b_renew = secondary_button(f"🔄 {_('renew_subscription')}")
        b_renew.clicked.connect(self.add_payment)
        btn_row.addWidget(b_edit)
        btn_row.addWidget(b_renew)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _status_text(self, end_date, status):
        today = db.today()
        if status != "active":
            return _("inactive")
        if end_date < today:
            return _("expired")
        return _("active")

    def refresh(self):
        # سجل واحد لكل اشتراك (مثل صورة سجل الاشتراكات) — لا تكرار مع payments
        self._rows = db.fetch_all(
            """SELECT s.*, m.full_name, p.name AS plan_name,
                      (SELECT payment_date FROM payments WHERE subscription_id=s.id ORDER BY id DESC LIMIT 1) AS last_payment_date
               FROM subscriptions s
               JOIN members m ON s.member_id = m.id
               JOIN plans p ON s.plan_id = p.id
               ORDER BY s.id DESC"""
        )
        self.apply_filter()

    def apply_filter(self, *_args):
        term = self.search.text().strip().lower()
        rows = [
            r for r in self._rows
            if not term or term in f"{r['full_name']} {r['plan_name']} {r['payment_method']}".lower()
        ]
        self._filtered = rows
        self._page = 0
        total = sum(r["price_paid"] for r in rows)
        self.total_lbl.setText(
            f"{_('total')}: {total:.2f} {db.get_setting('currency', '')}  |  "
            f"{_('total_revenue')} {len(rows)}"
        )
        self._render_page()

    def _render_page(self):
        total = len(self._filtered)
        ps = self._page_size if self._page_size else total
        pages = max(1, (total + ps - 1) // ps) if ps else 1
        if self._page >= pages:
            self._page = max(0, pages - 1)
        start = self._page * ps if ps else 0
        end = start + ps if ps else total
        page_rows = self._filtered[start:end] if ps else self._filtered
        fill_table(
            self.table,
            [
                (r["full_name"], r["plan_name"] or "-",
                 r["start_date"], r["end_date"],
                 f'{r["price_paid"]:.2f}', r["payment_method"] or "-",
                 r["last_payment_date"] or "-",
                 self._status_text(r["end_date"], r["status"]), r["notes"] or "")
                for r in page_rows
            ],
        )
        for i, r in enumerate(page_rows):
            self.table.item(i, 0).setData(Qt.UserRole, r["id"])
            self.table.item(i, 0).setData(Qt.UserRole + 1, r["member_id"])
        self.lbl_page.setText(f"{self._page + 1}/{pages}  ({total})")
        self.btn_prev.setEnabled(self._page > 0)
        self.btn_next.setEnabled(self._page + 1 < pages)

    def _prev_page(self):
        if self._page > 0:
            self._page -= 1
            self._render_page()

    def _next_page(self):
        ps = self._page_size if self._page_size else len(self._filtered)
        pages = max(1, (len(self._filtered) + ps - 1) // ps) if ps else 1
        if self._page + 1 < pages:
            self._page += 1
            self._render_page()

    def _change_page_size(self, idx):
        txt = self.page_size_combo.currentText()
        self._page_size = 0 if txt == "الكل" else int(txt) if txt.isdigit() else 50
        self._page = 0
        self._render_page()

    def selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, _("app_title"), _("select_member"))
            return None
        item = self.table.item(row, 0)
        return int(item.data(Qt.UserRole))

    def selected_member_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.data(Qt.UserRole + 1)) if item.data(Qt.UserRole + 1) else None

    def add_payment(self):
        # دفعة جديدة = تجديد اشتراك (سجل واحد فقط)
        from app.gui.dialogs.subscription_dialog import SubscriptionDialog
        dlg = SubscriptionDialog(self.app_ctx, self)
        if dlg.exec():
            self.refresh()
            # حدّث صفحة الاشتراكات أيضاً
            try:
                if hasattr(self.main, "pages") and "subscriptions" in self.main.pages:
                    self.main.pages["subscriptions"].refresh()
            except Exception:
                pass

    def edit_payment(self):
        sid = self.selected_id()
        if sid is None:
            return
        rec = db.fetch_one(
            """SELECT s.*, m.full_name, p.name AS plan_name
               FROM subscriptions s JOIN members m ON s.member_id=m.id
               JOIN plans p ON s.plan_id=p.id WHERE s.id=?""", (sid,))
        if not rec:
            return
        from app.gui.dialogs.subscription_dialog import SubscriptionDialog
        dlg = SubscriptionDialog(self.app_ctx, self, record=rec)
        if dlg.exec():
            self.refresh()

    def print_invoice(self):
        sid = self.selected_id()
        if sid is None:
            return
        pay = db.fetch_one("SELECT id FROM payments WHERE subscription_id=? ORDER BY id DESC LIMIT 1", (sid,))
        if pay:
            from app.invoice import print_invoice_pdf
            path = print_invoice_pdf(pay["id"])
            if not path:
                QMessageBox.warning(self, _("app_title"), _("error_save"))
            return
        # لا يوجد payment مرتبط — اطبع إيصال الاشتراك مباشرة
        rec = db.fetch_one(
            """SELECT s.*, m.full_name, m.phone, p.name AS plan_name, p.duration_days
               FROM subscriptions s JOIN members m ON s.member_id=m.id
               JOIN plans p ON s.plan_id=p.id WHERE s.id=?""", (sid,))
        if not rec:
            return
        from app.invoice import print_receipt_pdf
        import os, webbrowser
        path = print_receipt_pdf(rec)
        if path and os.path.exists(path):
            webbrowser.open(os.path.abspath(path))

    def delete_payment(self):
        sid = self.selected_id()
        if sid is None:
            return
        if QMessageBox.question(self, _("app_title"), _("confirm_delete")) == QMessageBox.Yes:
            db.move_to_trash("subscriptions", sid)
            self.refresh()

    def export(self):
        from app.export import export_table
        import os
        import webbrowser
        headers = [_("member"), _("plan_name"), _("start_date"), _("end_date"),
                   _("paid"), _("payment_method"), _("status"), _("notes")]
        rows = [
            (r["full_name"], r["plan_name"] or "-",
             r["start_date"], r["end_date"], r["price_paid"],
             r["payment_method"] or "-", self._status_text(r["end_date"], r["status"]), r["notes"] or "")
            for r in self._rows
        ]
        path = export_table(headers, rows, "payments_as_subscriptions")
        if not path:
            QMessageBox.warning(self, _("app_title"), _("error_save"))
            return
        webbrowser.open(os.path.abspath(path))
        QMessageBox.information(self, _("app_title"), _("export_done"))

    def show_payments_history(self):
        # إذا كان هناك عضو محدد في الجدول → اعرض دفعات ذلك العضو فقط، وإلا اعرض الكل
        mid = self.selected_member_id()
        member_name = None
        if mid is not None:
            row = db.fetch_one("SELECT full_name FROM members WHERE id=?", (mid,))
            member_name = row["full_name"] if row else None
        dlg = PaymentsHistoryDialog(self.app_ctx, self, member_id=mid, member_name=member_name)
        dlg.exec()
        self.refresh()

    def _on_double_click(self, row, col):
        self.edit_payment()


class PaymentsHistoryDialog(QDialog):
    """سجل المدفوعات التفصيلي — يعرض كل دفعات payments (حتى المنفصلة) مع الربط بالاشتراك."""
    def __init__(self, app_ctx, parent=None, member_id=None, member_name=None):
        super().__init__(parent)
        self.app_ctx = app_ctx
        self.member_id = member_id
        title = _("payments_history") + (f" — {member_name}" if member_name else "")
        self.setWindowTitle(title)
        self.resize(880, 520)
        self.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)
        head = QLabel(title)
        head.setStyleSheet(f"color:{style.ACCENT.name()}; font-size:16px; font-weight:bold;")
        lay.addWidget(head)
        # search
        self.search = QLineEdit()
        self.search.setPlaceholderText(f"🔍 {_('search')}...")
        self.search.setStyleSheet(style.INPUT_QSS)
        self.search.textChanged.connect(self.apply_filter)
        lay.addWidget(self.search)
        self.table = make_table(
            [_("date"), _("member"), _("plan_name"), _("amount"), _("payment_method"), _("reference"), _("notes")],
            stretch_col=1,
        )
        lay.addWidget(self.table, 1)
        self.total = QLabel("")
        self.total.setStyleSheet(f"color:{style.ACCENT.name()}; font-size:14px; font-weight:bold;")
        lay.addWidget(self.total)
        btns = QHBoxLayout()
        b_add = primary_button(f"➕ {_('add_payment')}")
        b_add.clicked.connect(self._add)
        b_edit = secondary_button(f"✏️ {_('edit')}")
        b_edit.clicked.connect(self._edit)
        b_del = danger_button(f"🗑️ {_('delete')}")
        b_del.clicked.connect(self._delete)
        b_close = secondary_button(_("close"))
        b_close.clicked.connect(self.accept)
        b_exp = secondary_button(f"📊 {_('export')}")
        b_exp.clicked.connect(self.export)
        btns.addWidget(b_add)
        btns.addWidget(b_edit)
        btns.addWidget(b_del)
        btns.addStretch()
        btns.addWidget(b_exp)
        btns.addWidget(b_close)
        lay.addLayout(btns)
        self._rows = []
        self.refresh()
        self.table.cellDoubleClicked.connect(self._edit)

    def refresh(self):
        if self.member_id is not None:
            self._rows = db.fetch_all(
                """SELECT p.*, m.full_name, pl.name AS plan_name
                   FROM payments p
                   JOIN members m ON p.member_id=m.id
                   LEFT JOIN subscriptions s ON p.subscription_id=s.id
                   LEFT JOIN plans pl ON s.plan_id=pl.id
                   WHERE p.member_id=? ORDER BY p.payment_date DESC, p.id DESC""",
                (self.member_id,),
            )
        else:
            self._rows = db.fetch_all(
                """SELECT p.*, m.full_name, pl.name AS plan_name
                   FROM payments p
                   JOIN members m ON p.member_id=m.id
                   LEFT JOIN subscriptions s ON p.subscription_id=s.id
                   LEFT JOIN plans pl ON s.plan_id=pl.id
                   ORDER BY p.payment_date DESC, p.id DESC"""
            )
        self.apply_filter()

    def _selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, _("app_title"), _("select_member"))
            return None
        # نحتاج id الدفعة — مخزن في _filtered عبر apply_filter
        if not hasattr(self, "_filtered") or not self._filtered:
            return None
        # استخدم الصفوف المفلترة الحالية
        term = self.search.text().strip().lower()
        filtered = [r for r in self._rows if not term or term in f"{r['full_name']} {r['reference_number'] or ''} {r['plan_name'] or ''}".lower()]
        if 0 <= row < len(filtered):
            return int(filtered[row]["id"])
        return None

    def _delete(self):
        pid = self._selected_id()
        if pid is None:
            return
        if QMessageBox.question(self, _("app_title"), _("confirm_delete")) != QMessageBox.Yes:
            return
        # احفظ بيانات قبل الحذف لتحديث الاشتراك
        pay = db.fetch_one("SELECT subscription_id, amount FROM payments WHERE id=?", (pid,))
        db.move_to_trash("payments", pid)
        if pay and pay["subscription_id"]:
            # حدّث إجمالي المدفوع في الاشتراك
            sid = pay["subscription_id"]
            total = db.fetch_one("SELECT COALESCE(SUM(amount),0) AS t FROM payments WHERE subscription_id=?", (sid,))
            total_val = total["t"] if total else 0
            methods = db.fetch_all("SELECT DISTINCT payment_method FROM payments WHERE subscription_id=?", (sid,))
            mstr = "+".join(m["payment_method"] for m in methods if m["payment_method"]) if methods else ""
            if total_val == 0:
                mstr = ""
            db.execute("UPDATE subscriptions SET price_paid=?, payment_method=? WHERE id=?", (total_val, mstr, sid))
            db.log_user_action("حذف دفعة", "دفعة", f"#{pid}", f"اشتراك #{sid} → الجديد {total_val:.2f}")
        else:
            db.log_user_action("حذف دفعة", "دفعة", f"#{pid}", "")
        self.refresh()

    def _add(self):
        if self.member_id is None:
            QMessageBox.information(self, _("app_title"), _("select_member"))
            return
        from PySide6.QtWidgets import QDialog, QGridLayout, QLineEdit, QDoubleSpinBox, QComboBox, QDateEdit
        from PySide6.QtCore import QDate
        dlg = QDialog(self)
        dlg.setWindowTitle(_("add_payment"))
        dlg.resize(380, 300)
        dlg.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)
        grid = QGridLayout()
        dt = QDateEdit()
        dt.setCalendarPopup(True)
        dt.setDisplayFormat("yyyy-MM-dd")
        dt.setDate(QDate.currentDate())
        dt.setStyleSheet(style.INPUT_QSS)
        grid.addWidget(QLabel(_("date")), 0, 0)
        grid.addWidget(dt, 0, 1)
        amt = QDoubleSpinBox()
        amt.setRange(0.01, 1000000)
        amt.setDecimals(2)
        amt.setValue(10.00)
        amt.setStyleSheet(style.INPUT_QSS)
        grid.addWidget(QLabel(_("amount")), 1, 0)
        grid.addWidget(amt, 1, 1)
        meth = QComboBox()
        meth.addItems([_("cash"), _("card"), _("transfer")])
        meth.setStyleSheet(style.INPUT_QSS)
        grid.addWidget(QLabel(_("payment_method")), 2, 0)
        grid.addWidget(meth, 2, 1)
        ref = QLineEdit()
        ref.setStyleSheet(style.INPUT_QSS)
        ref.setPlaceholderText(_("reference"))
        grid.addWidget(QLabel(_("reference")), 3, 0)
        grid.addWidget(ref, 3, 1)
        notes = QLineEdit()
        notes.setStyleSheet(style.INPUT_QSS)
        notes.setPlaceholderText(_("notes"))
        grid.addWidget(QLabel(_("notes")), 4, 0)
        grid.addWidget(notes, 4, 1)
        lay.addLayout(grid)
        btns = QHBoxLayout()
        b_ok = primary_button(_("save"))
        b_cancel = secondary_button(_("cancel"))
        def _save():
            if amt.value() <= 0:
                QMessageBox.warning(dlg, _("app_title"), _("error_save"))
                return
            pay_date = dt.date().toString("yyyy-MM-dd")
            # ربط بآخر اشتراك نشط للعضو إن وجد
            sub = db.fetch_one("SELECT id FROM subscriptions WHERE member_id=? ORDER BY id DESC LIMIT 1", (self.member_id,))
            sid = sub["id"] if sub else None
            db.execute(
                """INSERT INTO payments (member_id, subscription_id, amount, payment_date, payment_method, reference_number, notes)
                   VALUES (?,?,?,?,?,?,?)""",
                (self.member_id, sid, amt.value(), pay_date, meth.currentText(), ref.text().strip(), notes.text().strip()),
            )
            if sid:
                total = db.fetch_one("SELECT COALESCE(SUM(amount),0) AS t FROM payments WHERE subscription_id=?", (sid,))
                total_val = total["t"] if total else 0
                methods = db.fetch_all("SELECT DISTINCT payment_method FROM payments WHERE subscription_id=?", (sid,))
                mstr = "+".join(m["payment_method"] for m in methods if m["payment_method"]) if methods else meth.currentText()
                db.execute("UPDATE subscriptions SET price_paid=?, payment_method=? WHERE id=?", (total_val, mstr, sid))
            db.log_user_action("إضافة دفعة (سجل المدفوعات)", "دفعة", self.member_id, f"{amt.value():.2f} {meth.currentText()}")
            dlg.accept()
        b_ok.clicked.connect(_save)
        b_cancel.clicked.connect(dlg.reject)
        btns.addWidget(b_cancel)
        btns.addStretch()
        btns.addWidget(b_ok)
        lay.addLayout(btns)
        if dlg.exec():
            self.refresh()

    def _edit(self, row=None, col=None):
        pid = self._selected_id()
        if pid is None:
            return
        rec = db.fetch_one("SELECT * FROM payments WHERE id=?", (pid,))
        if not rec:
            return
        # حوار تعديل دفعة مع التاريخ
        from PySide6.QtWidgets import QDialog, QGridLayout, QLineEdit, QDoubleSpinBox, QComboBox, QDateEdit
        from PySide6.QtCore import QDate
        dlg = QDialog(self)
        dlg.setWindowTitle(_("edit"))
        dlg.resize(360, 260)
        dlg.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)
        grid = QGridLayout()
        dt = QDateEdit()
        dt.setCalendarPopup(True)
        dt.setDisplayFormat("yyyy-MM-dd")
        try:
            dt.setDate(QDate.fromString(rec["payment_date"], "yyyy-MM-dd"))
        except Exception:
            dt.setDate(QDate.currentDate())
        dt.setStyleSheet(style.INPUT_QSS)
        grid.addWidget(QLabel(_("date")), 0, 0)
        grid.addWidget(dt, 0, 1)
        amt = QDoubleSpinBox()
        amt.setRange(0.01, 1000000)
        amt.setDecimals(2)
        amt.setValue(rec["amount"])
        amt.setStyleSheet(style.INPUT_QSS)
        grid.addWidget(QLabel(_("amount")), 1, 0)
        grid.addWidget(amt, 1, 1)
        meth = QComboBox()
        meth.addItems([_("cash"), _("card"), _("transfer"), f"{_('cash')}+{_('card')}", f"{_('cash')}+{_('transfer')}"])
        meth.setStyleSheet(style.INPUT_QSS)
        idx = meth.findText(rec["payment_method"])
        if idx >= 0:
            meth.setCurrentIndex(idx)
        else:
            meth.setCurrentText(rec["payment_method"] or "")
        grid.addWidget(QLabel(_("payment_method")), 2, 0)
        grid.addWidget(meth, 2, 1)
        ref = QLineEdit(rec["reference_number"] or "")
        ref.setStyleSheet(style.INPUT_QSS)
        grid.addWidget(QLabel(_("reference")), 3, 0)
        grid.addWidget(ref, 3, 1)
        lay.addLayout(grid)
        btns = QHBoxLayout()
        b_ok = primary_button(_("save"))
        b_cancel = secondary_button(_("cancel"))
        def _save():
            if amt.value() <= 0:
                QMessageBox.warning(dlg, _("app_title"), _("error_save"))
                return
            pay_date = dt.date().toString("yyyy-MM-dd")
            db.execute("UPDATE payments SET amount=?, payment_method=?, reference_number=?, payment_date=? WHERE id=?",
                       (amt.value(), meth.currentText(), ref.text().strip(), pay_date, pid))
            if rec["subscription_id"]:
                sid = rec["subscription_id"]
                total = db.fetch_one("SELECT COALESCE(SUM(amount),0) AS t FROM payments WHERE subscription_id=?", (sid,))
                total_val = total["t"] if total else 0
                methods = db.fetch_all("SELECT DISTINCT payment_method FROM payments WHERE subscription_id=?", (sid,))
                mstr = "+".join(m["payment_method"] for m in methods if m["payment_method"]) if methods else ""
                db.execute("UPDATE subscriptions SET price_paid=?, payment_method=? WHERE id=?", (total_val, mstr, sid))
            db.log_user_action("تعديل دفعة", "دفعة", f"#{pid}", f"{amt.value():.2f} {meth.currentText()} {pay_date}")
            dlg.accept()
        b_ok.clicked.connect(_save)
        b_cancel.clicked.connect(dlg.reject)
        btns.addWidget(b_cancel)
        btns.addStretch()
        btns.addWidget(b_ok)
        lay.addLayout(btns)
        if dlg.exec():
            self.refresh()

    def apply_filter(self, *_a):
        term = self.search.text().strip().lower()
        rows = [r for r in self._rows if not term or term in f"{r['full_name']} {r['reference_number'] or ''} {r['plan_name'] or ''}".lower()]
        self._filtered = rows
        fill_table(self.table, [
            (r["payment_date"], r["full_name"], r["plan_name"] or "-",
             f"{r['amount']:.2f}", r["payment_method"] or "-", r["reference_number"] or "-", r["notes"] or "-")
            for r in rows
        ])
        for i, r in enumerate(rows):
            self.table.item(i, 0).setData(Qt.UserRole, r["id"])
        total = sum(r["amount"] for r in rows)
        curr = db.get_setting("currency", "")
        self.total.setText(f"{_('total')}: {total:.2f} {curr}  |  {len(rows)}")

    def export(self):
        from app.export import export_table
        import webbrowser, os
        headers = [_("date"), _("member"), _("plan_name"), _("amount"), _("payment_method"), _("reference"), _("notes")]
        rows = [(r["payment_date"], r["full_name"], r["plan_name"] or "-", r["amount"], r["payment_method"] or "-", r["reference_number"] or "-", r["notes"] or "-") for r in self._rows]
        path = export_table(headers, rows, "payments_history")
        if path:
            webbrowser.open(os.path.abspath(path))


class PaymentDialog(QDialog):
    def __init__(self, app_ctx, parent=None, record=None):
        super().__init__(parent)
        self.app_ctx = app_ctx
        self.record = record
        self._members = []
        self.setWindowTitle(_("edit") if record else _("quick_payment"))
        self.resize(440, 500)
        self.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(0, 1)

        self._all_members = db.fetch_all(
            "SELECT id, full_name, phone FROM members WHERE is_active=1 ORDER BY full_name"
        )
        self._members = list(self._all_members)
        self.member_search = QLineEdit()
        self.member_search.setPlaceholderText(f"🔍 {_('search')}...")
        self.member_search.setStyleSheet(style.INPUT_QSS)
        self.member_search.textChanged.connect(self._filter_members)
        form_field(grid, _("search"), self.member_search)
        self.member = make_combo([f"{m['full_name']} ({m['phone']})" for m in self._members])
        form_field(grid, _("member") + " *", self.member)

        self.amount = QDoubleSpinBox()
        self.amount.setRange(0, 1000000)
        self.amount.setDecimals(2)
        self.amount.setStyleSheet(style.INPUT_QSS)
        form_field(grid, _("amount") + " *", self.amount)

        self.method = make_combo([_("cash"), _("card"), _("transfer")])
        form_field(grid, _("payment_method"), self.method)

        self.ref = make_input()
        form_field(grid, _("reference"), self.ref)

        self.date = make_date()
        form_field(grid, _("date"), self.date)

        self.notes = make_input()
        self.notes.setPlaceholderText(_("notes"))
        form_field(grid, _("notes"), self.notes)

        lay.addLayout(grid)

        self._load()

        btns = QHBoxLayout()
        b_save = primary_button(_("save"))
        b_cancel = secondary_button(_("cancel"))
        b_save.clicked.connect(self.save)
        b_cancel.clicked.connect(self.reject)
        btns.addWidget(b_cancel)
        btns.addStretch()
        btns.addWidget(b_save)
        lay.addLayout(btns)

    def _fill_members(self, members):
        # keep current selection if possible
        cur_id = None
        if self.member.count() > 0 and self.member.currentIndex() >= 0 and self._members:
            try:
                cur_id = self._members[self.member.currentIndex()]["id"]
            except Exception:
                cur_id = None
        self.member.blockSignals(True)
        # also block lineEdit signals during refill
        self.member.clear()
        self._members = list(members)
        for m in self._members:
            self.member.addItem(f"{m['full_name']} ({m['phone'] or '-'})")
        # restore selection
        if cur_id is not None:
            idx = next((i for i, m in enumerate(self._members) if m["id"] == cur_id), -1)
            if idx >= 0:
                self.member.setCurrentIndex(idx)
        self.member.blockSignals(False)

    def _filter_members(self, text):
        term = text.strip().lower()
        if not term:
            self._fill_members(self._all_members)
            return
        filtered = [m for m in self._all_members if term in f"{m['full_name']} {m['phone'] or ''}".lower()]
        self._fill_members(filtered)

    def _load(self):
        rec = self.record
        if not rec:
            if self._members:
                self.member.setCurrentIndex(0)
            return
        # ensure record member is in list even if filtered
        if not any(m["id"] == rec["member_id"] for m in self._all_members):
            extra = db.fetch_one("SELECT id, full_name, phone FROM members WHERE id=?", (rec["member_id"],))
            if extra:
                self._all_members.append(extra)
                self._all_members.sort(key=lambda x: x["full_name"])
        self._fill_members(self._all_members)
        idx = next((i for i, m in enumerate(self._members) if m["id"] == rec["member_id"]), 0)
        self.member.setCurrentIndex(idx)
        self.amount.setValue(rec["amount"])
        texts = [self.method.itemText(i) for i in range(self.method.count())]
        if rec["payment_method"] in texts:
            self.method.setCurrentText(rec["payment_method"])
        self.ref.setText(rec["reference_number"])
        self.notes.setText(rec["notes"] or "")
        from PySide6.QtCore import QDate as _QDate
        self.date.setDate(_QDate.fromString(rec["payment_date"], "yyyy-MM-dd"))

    def save(self):
        if self.member.count() == 0 or self.amount.value() <= 0:
            QMessageBox.warning(self, _("app_title"), _("error_save"))
            return
        member_id = self._members[self.member.currentIndex()]["id"]
        date_str = self.date.date().toString("yyyy-MM-dd")
        ref = self.ref.text().strip()
        notes = self.notes.text().strip()
        if self.record:
            db.execute(
                """UPDATE payments SET member_id=?, amount=?, payment_date=?,
                   payment_method=?, reference_number=?, notes=? WHERE id=?""",
                (member_id, self.amount.value(), date_str,
                 self.method.currentText(), ref, notes, self.record["id"]),
            )
        else:
            db.execute(
                """INSERT INTO payments (member_id, amount, payment_date, payment_method, reference_number, notes)
                   VALUES (?,?,?,?,?,?)""",
                (member_id, self.amount.value(), date_str,
                 self.method.currentText(), ref, notes),
            )
        self.accept()