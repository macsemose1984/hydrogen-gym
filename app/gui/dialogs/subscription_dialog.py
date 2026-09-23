from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox,
    QDoubleSpinBox, QDateEdit, QLineEdit, QTextEdit, QPushButton,
    QMessageBox, QCheckBox, QWidget,
)
from PySide6.QtCore import Qt, QDate

import app.database as db
from app.i18n import _
from app.gui import style
from app.gui.widgets import primary_button, secondary_button, form_field, window_controls


class SubscriptionDialog(QDialog):
    def __init__(self, app_ctx, parent=None, record=None, is_renewal=False):
        super().__init__(parent)
        window_controls(self)
        self.app_ctx = app_ctx
        self.record = record
        self.is_renewal = is_renewal
        self._manual_end = False
        self._syncing_end = False
        self._members = []
        self._plans = []

        self.setWindowTitle(_("renew_subscription") if is_renewal or not record else _("edit"))
        self.resize(520, 620)
        self.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        grid = QGridLayout()
        grid.setSpacing(12)
        r = 0

        self._members = db.fetch_all(
            "SELECT id, full_name, phone FROM members WHERE is_active=1 ORDER BY full_name"
        )
        self.search = QLineEdit()
        self.search.setPlaceholderText(f"🔍 {_('search')}...")
        self.search.setStyleSheet(style.INPUT_QSS)
        self.search.textChanged.connect(self._filter_members)
        form_field(grid, _("search"), self.search)
        r += 1

        self.member = QComboBox()
        self.member.setStyleSheet(style.INPUT_QSS)
        self.member.currentIndexChanged.connect(self._member_changed)
        form_field(grid, _("member") + " *", self.member)
        self._fill_members(self._members)
        r += 1

        self._plans = db.fetch_all(
            "SELECT id, name, price, duration_days, sessions FROM plans WHERE is_active=1 ORDER BY name"
        )
        self.plan = QComboBox()
        for p in self._plans:
            self.plan.addItem(f"{p['name']} - {p['duration_days']} {_('days')}", p["id"])
        self.plan.currentIndexChanged.connect(self._plan_changed)
        self.plan.setStyleSheet(style.INPUT_QSS)
        form_field(grid, _("select_plan") + " *", self.plan)
        r += 1

        self._coaches = db.fetch_all(
            "SELECT id, full_name FROM coaches WHERE is_active=1 ORDER BY full_name"
        )
        self.coach = QComboBox()
        self.coach.addItem(f"— {_('no_coach')} —", None)
        for c in self._coaches:
            self.coach.addItem(c["full_name"], c["id"])
        self.coach.setStyleSheet(style.INPUT_QSS)
        form_field(grid, _("coach"), self.coach)
        r += 1

        self.start = QDateEdit()
        self.start.setCalendarPopup(True)
        self.start.setDisplayFormat("yyyy-MM-dd")
        self.start.setDate(QDate.currentDate())
        self.start.dateChanged.connect(self._start_changed)
        self.start.setStyleSheet(style.INPUT_QSS)
        start_row = QHBoxLayout()
        start_lbl = QLabel(_("start_date"))
        start_lbl.setStyleSheet("color:%s;font-size:13px;font-weight:600;" % style.MUTED.name())
        start_row.addWidget(start_lbl)
        start_row.addWidget(self.start, 1)
        self.start_today_chk = QCheckBox(_("start_today"))
        self.start_today_chk.setChecked(True)
        self.start_today_chk.toggled.connect(self._start_today_toggled)
        self.start_today_chk.setStyleSheet(f"color:{style.MUTED.name()};")
        start_row.addWidget(self.start_today_chk)
        grid.addLayout(start_row, r, 0, 1, 2)
        r += 1

        end_row = QHBoxLayout()
        self.end = QDateEdit()
        self.end.setCalendarPopup(True)
        self.end.setDisplayFormat("yyyy-MM-dd")
        self.end.setDate(QDate.currentDate().addMonths(1))
        self.end.dateChanged.connect(self._end_user_changed)
        self.end.setStyleSheet(style.INPUT_QSS)
        end_lbl = QLabel(_("end_date"))
        end_lbl.setStyleSheet("color:%s;font-size:13px;font-weight:600;" % style.MUTED.name())
        end_row.addWidget(end_lbl)
        end_row.addWidget(self.end, 1)
        self.auto_chk = QCheckBox(_("auto_end"))
        self.auto_chk.setChecked(record is None or is_renewal)
        self.auto_chk.toggled.connect(self._auto_toggled)
        self.auto_chk.setStyleSheet(f"color:{style.MUTED.name()};")
        end_row.addWidget(self.auto_chk)
        grid.addLayout(end_row, r, 0, 1, 2)
        r += 1

        self.price = QDoubleSpinBox()
        self.price.setRange(0, 1000000)
        self.price.setDecimals(2)
        self.price.setStyleSheet(style.INPUT_QSS)
        form_field(grid, _("amount"), self.price)
        r += 1

        self.method = QComboBox()
        self.method.addItems([_("cash"), _("card"), _("transfer")])
        self.method.setStyleSheet(style.INPUT_QSS)
        form_field(grid, _("payment_method"), self.method)
        r += 1
        self.payment_date = QDateEdit()
        self.payment_date.setCalendarPopup(True)
        self.payment_date.setDisplayFormat("yyyy-MM-dd")
        self.payment_date.setDate(QDate.currentDate())
        self.payment_date.setStyleSheet(style.INPUT_QSS)
        form_field(grid, _("payment_date"), self.payment_date)
        r += 1

        # إضافة دفعة ثانية — ملغاة حسب الطلب (تُضاف عبر زر سجل المدفوعات)
        self.split_chk = QCheckBox(_("add_second_payment"))
        self.split_chk.setStyleSheet(f"color:{style.MUTED.name()};")
        self.split_chk.toggled.connect(self._split_toggled)
        self.split_chk.setVisible(False)
        self.split_chk.setChecked(False)
        grid.addWidget(self.split_chk, r, 0, 1, 2)
        r += 1

        # صف طريقة/مبلغ ثانية (يظهر عند تفعيل التقسيم)
        self.split_row = QWidget()
        split_lay = QHBoxLayout(self.split_row)
        split_lay.setContentsMargins(0, 0, 0, 0)
        split_lay.setSpacing(8)
        self.method2 = QComboBox()
        self.method2.addItems([_("card"), _("transfer"), _("cash")])
        self.method2.setStyleSheet(style.INPUT_QSS)
        self.amount2 = QDoubleSpinBox()
        self.amount2.setRange(0, 1000000)
        self.amount2.setDecimals(2)
        self.amount2.setStyleSheet(style.INPUT_QSS)
        self.amount2.setPrefix(_("amount") + " 2: ")
        split_lay.addWidget(self.method2, 1)
        split_lay.addWidget(self.amount2, 1)
        grid.addWidget(self.split_row, r, 0, 1, 2)
        r += 1
        self.split_row.setVisible(False)
        self.method2.setVisible(False)
        self.amount2.setVisible(False)

        self.ref = QLineEdit()
        self.ref.setStyleSheet(style.INPUT_QSS)
        form_field(grid, _("reference"), self.ref)
        r += 1

        n_lbl = QLabel(_("notes"))
        n_lbl.setStyleSheet("color:%s;font-size:13px;font-weight:600;" % style.MUTED.name())
        grid.addWidget(n_lbl, r, 0)
        self.notes = QLineEdit()
        self.notes.setPlaceholderText(_("notes"))
        self.notes.setStyleSheet(style.INPUT_QSS)
        grid.addWidget(self.notes, r, 1)
        r += 1

        lay.addLayout(grid)

        self._load()
        self._sync_price()

        btns = QHBoxLayout()
        b_save = primary_button(_("save"))
        b_cancel = secondary_button(_("cancel"))
        b_save.clicked.connect(self.save)
        b_cancel.clicked.connect(self.reject)
        btns.addWidget(b_cancel)
        btns.addStretch()
        btns.addWidget(b_save)
        lay.addLayout(btns)

    # ---------- helpers ----------
    def _fill_members(self, members):
        current = self.member.currentData()
        self.member.blockSignals(True)
        self.member.clear()
        for m in members:
            self.member.addItem(f"{m['full_name']} ({m['phone']})", m["id"])
        # restore previous selection if still present
        idx = self.member.findData(current) if current is not None else -1
        self.member.setCurrentIndex(idx if idx >= 0 else 0)
        self.member.blockSignals(False)

    def _filter_members(self, *_args):
        term = self.search.text().strip().lower()
        if not term:
            self._fill_members(self._members)
            return
        matches = [
            m for m in self._members
            if term in f"{m['full_name']} {m['phone']}".lower()
        ]
        self._fill_members(matches)

    def _load(self):
        rec = self.record
        if not rec:
            self._manual_end = False
            if self._plans and self._plans[0]["duration_days"]:
                self._syncing_end = True
                try:
                    self.end.setDate(self.start.date().addDays(self._plans[0]["duration_days"]))
                finally:
                    self._syncing_end = False
            self._manual_end = False
            return

        # select member (include the record's member even if now inactive)
        mid = rec.get("member_id")
        if mid is not None:
            if not any(m["id"] == mid for m in self._members):
                extra = db.fetch_one(
                    "SELECT id, full_name, phone FROM members WHERE id=?", (mid,))
                if extra:
                    self._members.append(extra)
                    self._fill_members(self._members)
            idx = next((i for i, m in enumerate(self._members) if m["id"] == mid), 0)
            self.member.setCurrentIndex(idx)
        # select plan if present
        pid = rec.get("plan_id")
        if pid is not None:
            idx = next((i for i, p in enumerate(self._plans) if p["id"] == pid), 0)
            self.plan.setCurrentIndex(idx)
        # select coach (index 0 is "no coach")
        cidx = self.coach.findData(rec.get("coach_id"))
        self.coach.setCurrentIndex(cidx if cidx >= 0 else 0)
        if rec.get("price_paid") is not None:
            self.price.setValue(rec["price_paid"])
        if rec.get("payment_method") and rec["payment_method"] in (self.method.itemText(i) for i in range(self.method.count())):
            self.method.setCurrentText(rec["payment_method"])
        # payment_date (fetch latest from payments table since rec is a subscription)
        payment_date_val = None
        if rec.get("id"):
            pay_rec = db.fetch_one("SELECT payment_date FROM payments WHERE subscription_id=? ORDER BY id DESC LIMIT 1", (rec["id"],))
            if pay_rec:
                payment_date_val = pay_rec["payment_date"]
        
        if payment_date_val:
            _pd = QDate.fromString(payment_date_val, "yyyy-MM-dd")
            if _pd.isValid():
                self.payment_date.setDate(_pd)
            else:
                self.payment_date.setDate(QDate.currentDate())
        else:
            self.payment_date.setDate(QDate.currentDate())
        # reference from linked payment
        if rec.get("id"):
            # خيار الدفعة الثانية ملغى — يبقى مخفي حتى في التعديل (الإضافة عبر سجل المدفوعات)
            self.split_chk.setVisible(False)
            self.split_chk.setChecked(False)
            self._split_toggled(False)
            pay = db.fetch_one(
                "SELECT reference_number FROM payments WHERE subscription_id=? ORDER BY id DESC LIMIT 1",
                (rec["id"],),
            )
            if pay and pay["reference_number"]:
                self.ref.setText(pay["reference_number"])
            try:
                pass
            except Exception:
                pass
        # Renewal: create NEW subscription — reset dates to new period, not copy old
        if self.is_renewal:
            # start = day after old end if still active, else today
            try:
                old_end_str = rec.get("end_date") or ""
                old_end = QDate.fromString(old_end_str, "yyyy-MM-dd")
                today = QDate.currentDate()
                if old_end.isValid() and old_end >= today:
                    new_start = old_end.addDays(1)
                else:
                    new_start = today
            except Exception:
                new_start = QDate.currentDate()
            self.start_today_chk.blockSignals(True)
            self.start_today_chk.setChecked(new_start == QDate.currentDate())
            self.start_today_chk.blockSignals(False)
            self.start.setDate(new_start)
            self._manual_end = False
            self.auto_chk.setChecked(True)
            self._auto_sync_end()
            # price already synced via _sync_price above (renewal), ensure notes/reference fresh
            self.notes.setText("")
            self.ref.clear()
            return
        # start/end dates if present — otherwise keep today logic for pure member-preselected renewal
        if rec.get("start_date"):
            self.start_today_chk.blockSignals(True)
            self.start_today_chk.setChecked(False)
            self.start_today_chk.blockSignals(False)
            self.start.setDate(QDate.fromString(rec["start_date"], "yyyy-MM-dd"))
            if rec.get("end_date"):
                self.end.setDate(QDate.fromString(rec["end_date"], "yyyy-MM-dd"))
                self._manual_end = True
                self.notes.setText(rec.get("notes") or "")
                return
        # member-only preselection (e.g. double-click from Members page) → keep auto end-date
        self._manual_end = False
        self._auto_sync_end()
        if rec.get("notes"):
            self.notes.setText(rec.get("notes") or "")

    def _member_changed(self, *_args):
        self._auto_sync_end()
        mid = self.member.currentData()
        if mid:
            row = db.fetch_one("SELECT coach_id FROM members WHERE id=?", (mid,))
            cidx = self.coach.findData(row["coach_id"] if row else None)
            self.coach.setCurrentIndex(cidx if cidx >= 0 else 0)

    def _plan_changed(self, *_args):
        self._sync_price()
        self._auto_sync_end()

    def _start_changed(self, *_args):
        self._auto_sync_end()

    def _start_today_toggled(self, checked):
        if checked:
            self.start.setDate(QDate.currentDate())
            self._start_changed()

    def _end_user_changed(self, *_args):
        if not self._syncing_end:
            self._manual_end = True

    def _auto_toggled(self, checked):
        if checked:
            self._manual_end = False
            self._auto_sync_end()

    def _auto_sync_end(self):
        if self._manual_end or not self.auto_chk.isChecked():
            return
        plan = self._current_plan()
        if plan and plan["duration_days"] > 0:
            suggested = self.start.date().addDays(plan["duration_days"])
            if self.end.date() != suggested:
                self._syncing_end = True
                try:
                    self.end.setDate(suggested)
                finally:
                    self._syncing_end = False

    def _current_plan(self):
        idx = self.plan.currentIndex()
        if 0 <= idx < len(self._plans):
            return self._plans[idx]
        return None

    def _split_toggled(self, checked):
        self.split_row.setVisible(checked)
        self.method2.setVisible(checked)
        self.amount2.setVisible(checked)
        if checked and self.amount2.value() == 0 and self.price.value() > 0:
            self.amount2.setValue(round(self.price.value() / 2, 2))

    def _sync_price(self, *_args):
        if self.record is None or self.is_renewal:
            plan = self._current_plan()
            if plan:
                self.price.setValue(plan["price"])

    def save(self):
        if self.member.count() == 0:
            QMessageBox.warning(self, _("app_title"), _("no_data"))
            return
        plan = self._current_plan()
        if not plan:
            QMessageBox.warning(self, _("app_title"), _("select_plan"))
            return
        if self.end.date() < self.start.date():
            QMessageBox.warning(self, _("app_title"), _("error_save"))
            return

        member_id = self.member.currentData()
        coach_id = self.coach.currentData()
        start = self.start.date().toString("yyyy-MM-dd")
        end = self.end.date().toString("yyyy-MM-dd")
        method = self.method.currentText()
        notes = self.notes.text().strip()

        # تقسيم الدفعة
        is_split = self.split_chk.isChecked()
        amt_total = float(self.price.value())
        # في حالة التعديل: المبلغ الثاني هو دفعة إضافية (ليست تقسيم)
        is_edit_second = is_split and self.record and self.record.get("id") and not self.is_renewal
        if is_edit_second:
            amt2 = float(self.amount2.value())
            if amt2 <= 0:
                QMessageBox.warning(self, _("app_title"), _("split_amount_error"))
                return
            method2 = self.method2.currentText()
            pay_methods = None
            pay_method_str = None  # سيُحسب بعد الإدراج
        elif is_split:
            amt2 = float(self.amount2.value())
            if amt2 <= 0 or amt2 >= amt_total:
                QMessageBox.warning(self, _("app_title"), _("split_amount_error"))
                return
            method2 = self.method2.currentText()
            if method2 == method:
                QMessageBox.warning(self, _("app_title"), _("split_method_error"))
                return
            pay_methods = [(method, amt_total - amt2), (method2, amt2)]
            pay_method_str = f"{method}+{method2}"
        else:
            pay_methods = [(method, amt_total)]
            pay_method_str = method

        # for log: member name
        _m = db.fetch_one("SELECT full_name FROM members WHERE id=?", (member_id,))
        _mname = _m["full_name"] if _m else str(member_id)
        if self.record and self.is_renewal:
            # renewal: keep the old subscription as history, add a new one + payment
            db.execute(
                "UPDATE subscriptions SET status='inactive' WHERE member_id=? AND status='active'",
                (member_id,),
            )
            sub_id = db.execute(
                """INSERT INTO subscriptions (member_id, plan_id, coach_id, start_date, end_date,
                   remaining_sessions, price_paid, payment_method, status, notes)
                   VALUES (?,?,?,?,?,?,?,?, 'active', ?)""",
                (member_id, plan["id"], coach_id, start, end, plan["sessions"], amt_total,
                 pay_method_str, notes),
            )
            for pm, amt in pay_methods:
                db.execute(
                    """INSERT INTO payments (member_id, subscription_id, amount, payment_date,
                       payment_method, reference_number) VALUES (?,?,?,?,?,?)""",
                    (member_id, sub_id, amt, self.payment_date.date().toString("yyyy-MM-dd"), pm, self.ref.text().strip()),
                )
            db.log_user_action("تجديد اشتراك", "اشتراك", _mname, f"خطة: {plan['name']} | {start}→{end} | {amt_total:.2f} ({pay_method_str})")
        elif self.record and self.record.get("id"):
            if is_edit_second:
                # إضافة دفعة ثانية للاشتراك الحالي بدون حذف القديمة
                amt2 = float(self.amount2.value())
                method2 = self.method2.currentText()
                db.execute(
                    """UPDATE subscriptions SET member_id=?, plan_id=?, coach_id=?, start_date=?,
                       end_date=?, notes=? WHERE id=?""",
                    (member_id, plan["id"], coach_id, start, end, notes, self.record["id"]),
                )
                db.execute(
                    """INSERT INTO payments (member_id, subscription_id, amount, payment_date,
                       payment_method, reference_number) VALUES (?,?,?,?,?,?)""",
                    (member_id, self.record["id"], amt2, db.today(), method2, self.ref.text().strip()),
                )
                # حدّث الإجمالي وطريقة الدفع في الاشتراك
                total = db.fetch_one("SELECT COALESCE(SUM(amount),0) AS t FROM payments WHERE subscription_id=?", (self.record["id"],))["t"]
                methods = db.fetch_all("SELECT DISTINCT payment_method FROM payments WHERE subscription_id=?", (self.record["id"],))
                mstr = "+".join(m["payment_method"] for m in methods if m["payment_method"]) if methods else method
                db.execute("UPDATE subscriptions SET price_paid=?, payment_method=? WHERE id=?", (total, mstr, self.record["id"]))
                db.log_user_action("إضافة دفعة ثانية", "دفعة", _mname, f"{amt2:.2f} {method2} للاشتراك #{self.record['id']} → الإجمالي {total:.2f}")
            else:
                db.execute(
                    """UPDATE subscriptions SET member_id=?, plan_id=?, coach_id=?, start_date=?,
                       end_date=?, price_paid=?, payment_method=?, notes=? WHERE id=?""",
                    (member_id, plan["id"], coach_id, start, end, amt_total,
                     pay_method_str, notes, self.record["id"]),
                )
                # أعد كتابة الدفعات للاشتراك (يدعم التحويل من مفرد إلى مقسّم)
                db.execute("DELETE FROM payments WHERE subscription_id=?", (self.record["id"],))
                for pm, amt in pay_methods:
                    db.execute(
                        """INSERT INTO payments (member_id, subscription_id, amount, payment_date,
                           payment_method, reference_number) VALUES (?,?,?,?,?,?)""",
                        (member_id, self.record["id"], amt, db.today(), pm, self.ref.text().strip()),
                    )
                db.log_user_action("تعديل اشتراك", "اشتراك", _mname, f"خطة: {plan['name']} | {start}→{end} ({pay_method_str})")
        else:
            now = db.today()
            # mark previous active subscriptions of this member as inactive
            db.execute(
                "UPDATE subscriptions SET status='inactive' WHERE member_id=? AND status='active'",
                (member_id,),
            )
            sub_id = db.execute(
                """INSERT INTO subscriptions (member_id, plan_id, coach_id, start_date, end_date,
                   remaining_sessions, price_paid, payment_method, status, notes)
                   VALUES (?,?,?,?,?,?,?,?, 'active', ?)""",
                (member_id, plan["id"], coach_id, start, end, plan["sessions"], amt_total,
                 pay_method_str, notes),
            )
            for pm, amt in pay_methods:
                db.execute(
                    """INSERT INTO payments (member_id, subscription_id, amount, payment_date,
                       payment_method, reference_number) VALUES (?,?,?,?,?,?)""",
                    (member_id, sub_id, amt, now, pm, self.ref.text().strip()),
                )
            db.log_user_action("إضافة اشتراك", "اشتراك", _mname, f"خطة: {plan['name']} | {start}→{end} | {amt_total:.2f} ({pay_method_str})")
        self.accept()


from PySide6.QtWidgets import (
    QDialog as _QDialog, QVBoxLayout as _VBox, QHBoxLayout as _HBox,
    QLabel as _Lbl, QComboBox as _Combo, QDoubleSpinBox as _DSpin,
    QMessageBox as _Msg, QLineEdit as _LE,
)
from PySide6.QtCore import Qt as _Qt


class QuickPaymentDialog(_QDialog):
    """Minimal one-shot payment entry shown from the dashboard."""
    def __init__(self, app_ctx, parent=None):
        super().__init__(parent)
        window_controls(self)
        self.app_ctx = app_ctx
        self.setWindowTitle(_("quick_payment"))
        self.resize(420, 300)
        self.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")
        lay = _VBox(self); lay.setContentsMargins(24, 24, 24, 24); lay.setSpacing(12)

        # --- member search + combo ---
        lay.addWidget(_Lbl(_("member") + " *"))
        self._all_members = db.fetch_all(
            "SELECT id, full_name, phone FROM members WHERE is_active=1 ORDER BY full_name"
        )
        self.search = _LE()
        self.search.setPlaceholderText(f"🔍 {_('search')}...")
        self.search.setStyleSheet(style.INPUT_QSS)
        self.search.textChanged.connect(self._filter_members)
        lay.addWidget(self.search)

        self.member = QComboBox()
        self.member.setStyleSheet(style.INPUT_QSS)
        self.member.setMinimumHeight(36)
        self._fill_members(self._all_members)
        lay.addWidget(self.member)

        lay.addWidget(_Lbl(_("payment_method")))
        self.method = QComboBox()
        self.method.addItems([_("cash"), _("card"), _("transfer")])
        self.method.setStyleSheet(style.INPUT_QSS)
        lay.addWidget(self.method)

        lay.addWidget(_Lbl(_("amount") + " *"))
        self.amount = _DSpin()
        self.amount.setRange(0.01, 1000000)
        self.amount.setDecimals(2)
        self.amount.setStyleSheet(style.INPUT_QSS)
        lay.addWidget(self.amount)

        lay.addWidget(_Lbl(_("reference")))
        self.ref = make_input() if (make_input := lambda: __import__('app.gui.widgets', fromlist=['make_input']).make_input()) else None
        from app.gui.widgets import make_input
        self.ref = make_input()
        lay.addWidget(self.ref)

        btns = _HBox(); btns.addStretch()
        b_save = primary_button(_("save")); b_save.clicked.connect(self.save)
        b_cancel = secondary_button(_("cancel")); b_cancel.clicked.connect(self.reject)
        btns.addWidget(b_cancel); btns.addWidget(b_save)
        lay.addLayout(btns)

    def save(self):
        if self.member.currentData() is None:
            _Msg.warning(self, _("app_title"), _("no_data"))
            return
        try:
            amt = float(self.amount.value())
        except (ValueError, TypeError):
            _Msg.warning(self, _("app_title"), _("error_save"))
            return
        if amt <= 0:
            _Msg.warning(self, _("app_title"), _("error_save"))
            return
        db.execute(
            """INSERT INTO payments (member_id, subscription_id, amount, payment_date,
               payment_method, reference_number) VALUES (?,?,?,?,?,?)""",
            (self.member.currentData(), None, amt, db.today(), self.method.currentText(), self.ref.text().strip()),
        )
        _Msg.information(self, _("app_title"), _("success_save"))
        self.accept()

    def _fill_members(self, members):
        current = self.member.currentData()
        self.member.blockSignals(True)
        self.member.clear()
        for m in members:
            self.member.addItem(f"{m['full_name']} ({m['phone']})", m["id"])
        idx = self.member.findData(current) if current is not None else -1
        self.member.setCurrentIndex(idx if idx >= 0 else 0)
        self.member.blockSignals(False)

    def _filter_members(self, *_args):
        term = self.search.text().strip().lower()
        if not term:
            self._fill_members(self._all_members)
            return
        matches = [
            m for m in self._all_members
            if term in f"{m['full_name']} {m['phone']}".lower()
        ]
        self._fill_members(matches)