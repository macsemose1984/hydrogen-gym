from PySide6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QMessageBox, QComboBox,
)
from PySide6.QtCore import Qt

import app.database as db
from app.i18n import _
from app.gui import style
from app.gui.widgets import (
    page_title, make_table, fill_table, primary_button, secondary_button,
    danger_button,
)
from app.gui.dialogs.subscription_dialog import SubscriptionDialog


class SubscriptionsPage(QWidget):
    def __init__(self, app_ctx, main):
        super().__init__()
        self.app_ctx = app_ctx
        self.main = main
        self._rows = []
        self._build()
        self.table.cellDoubleClicked.connect(self._on_double_click)
        self.refresh()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        head = QHBoxLayout()
        head.addWidget(page_title(_("subscriptions")))
        head.addStretch()
        b_del = danger_button(f"🗑️ {_('delete')}")
        b_del.clicked.connect(self.delete_subscription)
        b_exp = secondary_button(f"📊 {_('export')}")
        b_exp.clicked.connect(self.export)
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
        self.filter.addItems([_("all"), _("active"), _("expired")])
        self.filter.setCurrentIndex(1)
        self.filter.currentIndexChanged.connect(self.apply_filter)
        self.filter.setStyleSheet(style.INPUT_QSS)
        bar.addWidget(self.filter)
        layout.addLayout(bar)

        self.table = make_table(
            [_("member"), _("plan_name"), _("coach"), _("start_date"), _("end_date"),
             _("paid"), _("remaining_sessions"), _("status"), _("notes")],
            stretch_col=0,
        )
        layout.addWidget(self.table, 1)

        # pagination 50 (client-side slice, 50 widget فقط بدل 343)
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

        btn_row = QHBoxLayout()
        b_edit = secondary_button(f"✏️ {_('edit')}")
        b_wa = secondary_button(f"💬 {_('send_whatsapp')}")
        b_renew = secondary_button(f"🔄 {_('renew_subscription')}")
        b_hist = secondary_button(f"📋 {_('subscription_history')}")
        b_rcpt = secondary_button(f"🧾 {_('print_receipt')}")
        b_edit.clicked.connect(self.edit_subscription)
        b_wa.clicked.connect(self.send_whatsapp)
        b_renew.clicked.connect(self.renew_subscription)
        b_hist.clicked.connect(self.show_history)
        b_rcpt.clicked.connect(self.print_receipt)
        for b in (b_edit, b_wa, b_renew, b_hist, b_rcpt):
            btn_row.addWidget(b)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def refresh(self):
        all_subs = db.fetch_all(
            """SELECT s.*, m.full_name, p.name AS plan_name, c.full_name AS coach_name
               FROM subscriptions s
               JOIN members m ON s.member_id = m.id
               JOIN plans p ON s.plan_id = p.id
               LEFT JOIN coaches c ON s.coach_id = c.id
               ORDER BY s.id DESC"""
        )
        seen = set()
        self._rows = []
        self._member_subs = {}
        for r in all_subs:
            mid = r["member_id"]
            if mid not in self._member_subs:
                self._member_subs[mid] = []
            self._member_subs[mid].append(r)
            if mid not in seen:
                seen.add(mid)
                self._rows.append(r)
        self.apply_filter()

    def _status_text(self, end_date, status):
        today = db.today()
        if status != "active":
            return _("inactive")
        if end_date < today:
            return _("expired")
        return _("active")

    def apply_filter(self, *_args):
        term = self.search.text().strip().lower()
        mode = self.filter.currentIndex()  # 0 all, 1 active, 2 expired
        today = db.today()
        rows = []
        for r in self._rows:
            if term and term not in f"{r['full_name']} {r['plan_name']}".lower():
                continue
            st = self._status_text(r["end_date"], r["status"])
            is_exp = r["end_date"] < today
            if mode == 1 and (st != _("active") or r["status"] != "active"):
                continue
            if mode == 2 and not is_exp:
                continue
            rows.append(r)
        self._filtered = rows
        self._page = 0
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
                (r["full_name"], r["plan_name"], r["coach_name"] or "-",
                 r["start_date"], r["end_date"],
                 f'{r["price_paid"]:.2f}', r["remaining_sessions"],
                 self._status_text(r["end_date"], r["status"]), r["notes"])
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
        if txt == "الكل":
            self._page_size = 0
        else:
            try:
                self._page_size = int(txt)
            except ValueError:
                self._page_size = 50
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
        data = item.data(Qt.UserRole + 1)
        return int(data) if data is not None else None

    def show_history(self):
        mid = self.selected_member_id()
        if mid is None:
            QMessageBox.information(self, _("app_title"), _("select_member"))
            return
        subs = self._member_subs.get(mid, [])
        if not subs:
            return
        member_name = subs[0]["full_name"]
        dlg = SubscriptionHistoryDialog(self.app_ctx, mid, member_name, subs, self)
        dlg.exec()

    def new_subscription(self):
        dlg = SubscriptionDialog(self.app_ctx, self)
        if dlg.exec():
            self.refresh()

    def edit_subscription(self):
        sid = self.selected_id()
        if sid is None:
            return
        rec = db.fetch_one(
            """SELECT s.*, m.full_name, p.name AS plan_name
               FROM subscriptions s
               JOIN members m ON s.member_id = m.id
               JOIN plans p ON s.plan_id = p.id
               WHERE s.id=?""",
            (sid,),
        )
        dlg = SubscriptionDialog(self.app_ctx, self, record=rec)
        if dlg.exec():
            self.refresh()

    def renew_subscription(self):
        sid = self.selected_id()
        if sid is None:
            return
        rec = db.fetch_one(
            """SELECT s.*, m.full_name, p.name AS plan_name
               FROM subscriptions s
               JOIN members m ON s.member_id = m.id
               JOIN plans p ON s.plan_id = p.id
               WHERE s.id=?""",
            (sid,),
        )
        dlg = SubscriptionDialog(self.app_ctx, self, record=rec, is_renewal=True)
        if dlg.exec():
            self.refresh()

    def print_receipt(self):
        sid = self.selected_id()
        if sid is None:
            return
        rec = db.fetch_one(
            """SELECT s.*, m.full_name, m.phone, p.name AS plan_name, p.duration_days
               FROM subscriptions s
               JOIN members m ON s.member_id = m.id
               JOIN plans p ON s.plan_id = p.id
               WHERE s.id=?""",
            (sid,),
        )
        if not rec:
            QMessageBox.warning(self, _("app_title"), _("error_save"))
            return
        from app.invoice import print_receipt_pdf
        import os
        import webbrowser
        path = print_receipt_pdf(rec)
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, _("app_title"), _("error_save"))
            return
        webbrowser.open(os.path.abspath(path))

    def _on_double_click(self, row, col):
        # النقر المزدوج يفتح تجديد الاشتراك مباشرة مع اختيار العضو تلقائياً
        sid = self.table.item(row, 0).data(Qt.UserRole) if self.table.item(row, 0) else None
        if sid is None:
            return
        rec = db.fetch_one(
            """SELECT s.*, m.full_name, p.name AS plan_name
               FROM subscriptions s
               JOIN members m ON s.member_id = m.id
               JOIN plans p ON s.plan_id = p.id
               WHERE s.id=?""",
            (sid,),
        )
        if not rec:
            return
        dlg = SubscriptionDialog(self.app_ctx, self, record=rec, is_renewal=True)
        if dlg.exec():
            self.refresh()

    def delete_subscription(self):
        sid = self.selected_id()
        if sid is None:
            return
        if QMessageBox.question(self, _("app_title"), _("confirm_delete")) == QMessageBox.Yes:
            db.move_to_trash("subscriptions", sid)
            self.refresh()

    def send_whatsapp(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, _("app_title"), _("select_member"))
            return
        self.main.show_page("whatsapp", tab="expiring")

    def export(self):
        from app.export import export_table
        import os
        import webbrowser
        headers = [_("member"), _("plan_name"), _("coach"), _("start_date"),
                   _("end_date"), _("paid"), _("remaining_sessions"),
                   _("status"), _("notes")]
        rows = [
            (r["full_name"], r["plan_name"], r["coach_name"] or "-",
             r["start_date"], r["end_date"], r["price_paid"],
             r["remaining_sessions"],
             self._status_text(r["end_date"], r["status"]), r["notes"])
            for r in self._rows
        ]
        path = export_table(headers, rows, "subscriptions")
        if not path:
            QMessageBox.warning(self, _("app_title"), _("error_save"))
            return
        webbrowser.open(os.path.abspath(path))
        QMessageBox.information(self, _("app_title"), _("export_done"))


class SubscriptionHistoryDialog(QDialog):
    def __init__(self, app_ctx, member_id, member_name, subs, parent=None):
        super().__init__(parent)
        self.app_ctx = app_ctx
        self.member_id = member_id
        self.setWindowTitle(f"{_('subscription_history')} - {member_name}")
        self.resize(750, 450)
        self.setStyleSheet(
            f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        title = QLabel(f"{_('subscription_history')}: {member_name}")
        title.setStyleSheet(f"color:{style.ACCENT.name()}; font-size:15px; font-weight:bold;")
        lay.addWidget(title)

        headers = [_("plan_name"), _("start_date"), _("end_date"),
                   _("paid"), _("payment_method"), _("status"), _("notes")]
        self.table = make_table(headers, stretch_col=0)
        lay.addWidget(self.table, 1)

        btn_row = QHBoxLayout()
        b_renew = primary_button(f"\U0001f504 {_('renew_subscription')}")
        b_renew.clicked.connect(self._renew)
        b_add_pay = primary_button(f"➕ {_('add_payment')}")
        b_add_pay.clicked.connect(self._add_payment)
        b_edit = secondary_button(f"✏️ {_('edit')}")
        b_edit.clicked.connect(self._edit)
        b_delete = danger_button(f"🗑️ {_('delete')}")
        b_delete.clicked.connect(self._delete)
        b_close = secondary_button(_("close"))
        b_close.clicked.connect(self.accept)
        btn_row.addWidget(b_renew)
        btn_row.addWidget(b_add_pay)
        btn_row.addWidget(b_edit)
        btn_row.addWidget(b_delete)
        btn_row.addStretch()
        btn_row.addWidget(b_close)
        lay.addLayout(btn_row)

        self._fill(subs)

    def _status_text(self, end_date, status):
        today = db.today()
        if status != "active":
            return _("inactive")
        if end_date < today:
            return _("expired")
        return _("active")

    def _fill(self, subs):
        today = db.today()
        rows = []
        for r in subs:
            st = self._status_text(r["end_date"], r["status"])
            rows.append((
                r["plan_name"] or "-",
                r["start_date"],
                r["end_date"],
                f'{r["price_paid"]:.2f}',
                r["payment_method"] or "-",
                st,
                r["notes"] or "-",
            ))
        fill_table(self.table, rows)
        for i, r in enumerate(subs):
            self.table.item(i, 0).setData(Qt.UserRole, r["id"])

    def _selected_sid(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, _("app_title"), _("select_member"))
            return None
        return int(self.table.item(row, 0).data(Qt.UserRole))

    def _edit(self):
        from app.gui.dialogs.subscription_dialog import SubscriptionDialog
        sid = self._selected_sid()
        if sid is None:
            return
        rec = db.fetch_one(
            """SELECT s.*, m.full_name, p.name AS plan_name
               FROM subscriptions s
               JOIN members m ON s.member_id = m.id
               JOIN plans p ON s.plan_id = p.id
               WHERE s.id=?""",
            (sid,),
        )
        dlg = SubscriptionDialog(self.app_ctx, self, record=rec)
        if dlg.exec():
            all_subs = db.fetch_all(
                """SELECT s.*, m.full_name, p.name AS plan_name
                   FROM subscriptions s
                   JOIN members m ON s.member_id = m.id
                   JOIN plans p ON s.plan_id = p.id
                   WHERE s.member_id=? ORDER BY s.id DESC""",
                (self.member_id,),
            )
            self._fill(all_subs)
            try:
                if self.parent() and hasattr(self.parent(), "refresh"):
                    self.parent().refresh()
            except Exception:
                pass

    def _delete(self):
        sid = self._selected_sid()
        if sid is None:
            return
        if QMessageBox.question(self, _("app_title"), _("confirm_delete")) != QMessageBox.Yes:
            return
        db.move_to_trash("subscriptions", sid)
        all_subs = db.fetch_all(
            """SELECT s.*, m.full_name, p.name AS plan_name
               FROM subscriptions s
               JOIN members m ON s.member_id = m.id
               JOIN plans p ON s.plan_id = p.id
               WHERE s.member_id=? ORDER BY s.id DESC""",
            (self.member_id,),
        )
        self._fill(all_subs)
        try:
            if self.parent() and hasattr(self.parent(), "refresh"):
                self.parent().refresh()
        except Exception:
            pass
        if not all_subs:
            self.accept()

    def _add_payment(self):
        sid = self._selected_sid()
        if sid is None:
            return
        rec = db.fetch_one(
            """SELECT s.*, m.full_name, p.name AS plan_name
               FROM subscriptions s
               JOIN members m ON s.member_id = m.id
               JOIN plans p ON s.plan_id = p.id
               WHERE s.id=?""",
            (sid,),
        )
        if not rec:
            return
        # حوار دفعة ثانية لنفس الاشتراك: التاريخ، المبلغ، طريقة الدفع، المرجع، الملاحظات
        from PySide6.QtWidgets import QDialog, QGridLayout, QLineEdit, QDoubleSpinBox, QComboBox, QDateEdit
        from PySide6.QtCore import QDate
        dlg = QDialog(self)
        dlg.setWindowTitle(_("add_payment"))
        dlg.resize(380, 300)
        dlg.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)
        lay.addWidget(QLabel(f"{_('subscription_history')}: {rec['full_name']} — {rec['plan_name']} ({rec['price_paid']:.2f} {db.get_setting('currency','')})"))
        grid = QGridLayout()
        grid.setSpacing(10)
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
        amt.setStyleSheet(style.INPUT_QSS)
        amt.setValue(10.00)
        grid.addWidget(QLabel(_("amount")), 1, 0)
        grid.addWidget(amt, 1, 1)
        meth = QComboBox()
        meth.addItems([_("cash"), _("card"), _("transfer"), f"{_('cash')}+{_('card')}", f"{_('cash')}+{_('transfer')}"])
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
            db.execute(
                """INSERT INTO payments (member_id, subscription_id, amount, payment_date, payment_method, reference_number, notes)
                   VALUES (?,?,?,?,?,?,?)""",
                (rec["member_id"], sid, amt.value(), pay_date, meth.currentText(), ref.text().strip(), notes.text().strip()),
            )
            # حدّث إجمالي المدفوع في الاشتراك ليطابق مجموع الدفعات
            total = db.fetch_one("SELECT COALESCE(SUM(amount),0) AS t FROM payments WHERE subscription_id=?", (sid,))["t"]
            # أيضاً حدّث طريقة الدفع لتجمع الطرق
            methods = db.fetch_all("SELECT DISTINCT payment_method FROM payments WHERE subscription_id=?", (sid,))
            mstr = "+".join(m["payment_method"] for m in methods if m["payment_method"])
            db.execute("UPDATE subscriptions SET price_paid=?, payment_method=? WHERE id=?", (total, mstr or rec["payment_method"], sid))
            db.log_user_action("إضافة دفعة ثانية", "دفعة", rec["full_name"], f"{amt.value():.2f} {meth.currentText()} للاشتراك #{sid} بتاريخ {pay_date}")
            dlg.accept()
        b_ok.clicked.connect(_save)
        b_cancel.clicked.connect(dlg.reject)
        btns.addWidget(b_cancel)
        btns.addStretch()
        btns.addWidget(b_ok)
        lay.addLayout(btns)
        if dlg.exec():
            all_subs = db.fetch_all(
                """SELECT s.*, m.full_name, p.name AS plan_name
                   FROM subscriptions s
                   JOIN members m ON s.member_id = m.id
                   JOIN plans p ON s.plan_id = p.id
                   WHERE s.member_id=? ORDER BY s.id DESC""",
                (self.member_id,),
            )
            self._fill(all_subs)
            try:
                if self.parent() and hasattr(self.parent(), "refresh"):
                    self.parent().refresh()
            except Exception:
                pass

    def _renew(self):
        from app.gui.dialogs.subscription_dialog import SubscriptionDialog
        sid = self._selected_sid()
        if sid is None:
            return
        rec = db.fetch_one(
            """SELECT s.*, m.full_name, p.name AS plan_name
               FROM subscriptions s
               JOIN members m ON s.member_id = m.id
               JOIN plans p ON s.plan_id = p.id
               WHERE s.id=?""",
            (sid,),
        )
        dlg = SubscriptionDialog(self.app_ctx, self, record=rec, is_renewal=True)
        if dlg.exec():
            all_subs = db.fetch_all(
                """SELECT s.*, m.full_name, p.name AS plan_name
                   FROM subscriptions s
                   JOIN members m ON s.member_id = m.id
                   JOIN plans p ON s.plan_id = p.id
                   WHERE s.member_id=? ORDER BY s.id DESC""",
                (self.member_id,),
            )
            self._fill(all_subs)
            try:
                if self.parent() and hasattr(self.parent(), "refresh"):
                    self.parent().refresh()
            except Exception:
                pass

