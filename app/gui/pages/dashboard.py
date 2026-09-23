from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QTableWidgetItem, QFrame,
)
from PySide6.QtCore import Qt

import app.database as db
from app.i18n import _
from app.gui import style
from app.gui.widgets import (
    stat_card, page_title, make_table, fill_table, primary_button,
    secondary_button, success_button,
)


class DashboardPage(QWidget):
    def __init__(self, app_ctx, main):
        super().__init__()
        self.app_ctx = app_ctx
        self.main = main
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        layout.addWidget(page_title(_("dashboard")))

        grid = QGridLayout()
        grid.setSpacing(16)
        cards = [
            ("👥", "0", _("total_members")),
            ("✅", "0", _("active_members")),
            ("⏳", "0", _("expired_members")),
            ("💰", "0", _("monthly_revenue")),
        ]
        for i, (icon, val, cap) in enumerate(cards):
            grid.addWidget(stat_card(icon, val, cap), 0, i)
        layout.addLayout(grid)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        b_new = primary_button(f"➕ {_('quick_member')}")
        b_checkin = success_button(f"⏰ {_('quick_checkin')}")
        b_pay = secondary_button(f"💳 {_('quick_payment')}")
        b_new.clicked.connect(self._goto_members)
        b_checkin.clicked.connect(self._goto_checkin)
        b_pay.clicked.connect(self._quick_payment)
        for b in (b_new, b_checkin, b_pay):
            actions.addWidget(b)
        actions.addStretch()
        layout.addLayout(actions)

        # ---- notification slot (in-app alerts) ----
        self._notif_container = QHBoxLayout()
        self._notif_container.addStretch()
        layout.addLayout(self._notif_container)

        bottom = QHBoxLayout()
        bottom.setSpacing(16)

        exp_card = self._card_box(_("expiring_soon"))
        self.exp_table = make_table([_("member"), _("end_date"), _("remaining_days")])
        self.exp_table.setMinimumHeight(260)
        exp_card[1].addWidget(self.exp_table)
        bottom.addLayout(exp_card[0], 1)

        expd_card = self._card_box(_("expired_subscriptions"))
        self.expired_table = make_table([_("member"), _("end_date"), _("overdue_days")])
        self.expired_table.setMinimumHeight(260)
        expd_card[1].addWidget(self.expired_table)
        bottom.addLayout(expd_card[0], 1)

        layout.addLayout(bottom)

        # ---- notification slot (in-app alerts) ----
        self._notif_container = QHBoxLayout()
        self._notif_container.addStretch()
        layout.addLayout(self._notif_container)

        # ---- hint to open dedicated charts page ----
        hint = QLabel(f"📊 {_('charts_hint')}")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{style.MUTED.name()}; font-size:12px;")
        layout.addWidget(hint)

    def _card_box(self, title, button=None):
        lay = QVBoxLayout()
        lay.setSpacing(8)
        hdr = QHBoxLayout()
        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color:{style.TEXT.name()}; font-size:15px; font-weight:bold;"
        )
        hdr.addWidget(lbl)
        hdr.addStretch()
        if button is not None:
            hdr.addWidget(button)
        lay.addLayout(hdr)
        return lay, lay

    def refresh(self):
        total = db.fetch_one("SELECT COUNT(*) c FROM members")
        active = db.fetch_one(
            """SELECT COUNT(DISTINCT s.member_id) c FROM subscriptions s
               WHERE s.status='active' AND s.end_date >= date('now')"""
        )
        today = db.fetch_one(
            """SELECT COUNT(DISTINCT s.member_id) c FROM subscriptions s
               WHERE s.status='active' AND s.end_date < date('now')"""
        )
        revenue = db.fetch_one(
            """SELECT COALESCE(SUM(amount),0) c FROM payments
               WHERE strftime('%Y-%m', payment_date)=strftime('%Y-%m','now')"""
        )
        vals = [str(x["c"]) for x in (total, active, today)]
        vals.append(f"{revenue['c']:.2f} {db.get_setting('currency', '')}")
        grid = self.layout().itemAt(1).layout()
        icons = ["👥", "✅", "⏳", "💰"]
        caps = [_("total_members"), _("active_members"), _("expired_members"), _("monthly_revenue")]
        for i in range(4):
            item = grid.itemAtPosition(0, i)
            w = item.widget()
            w.layout().itemAt(1).widget().setText(vals[i])
            w.layout().itemAt(1).widget().setStyleSheet(style.CARD_QSS)

        exp = db.fetch_all(
            """SELECT m.full_name, s.member_id, s.end_date
               FROM subscriptions s JOIN members m ON s.member_id=m.id
               WHERE s.status='active' AND s.end_date BETWEEN date('now') AND date('now','+7 day')
               ORDER BY s.end_date"""
        )
        from datetime import datetime as _dt
        rows = []
        for r in exp:
            days = (_dt.strptime(r["end_date"], "%Y-%m-%d").date() - _dt.now().date()).days
            rows.append((r["full_name"], r["end_date"], f"{days}"))
        fill_table(self.exp_table, rows)
        for i, r in enumerate(exp):
            self.exp_table.item(i, 0).setData(Qt.UserRole, r["member_id"])

        expd = db.fetch_all(
            """SELECT m.full_name, s.member_id, s.end_date
               FROM subscriptions s JOIN members m ON s.member_id=m.id
               WHERE s.status='active' AND s.end_date < date('now')
               ORDER BY s.end_date DESC LIMIT 20"""
        )
        erows = []
        for r in expd:
            days = (_dt.now().date() - _dt.strptime(r["end_date"], "%Y-%m-%d").date()).days
            erows.append((r["full_name"], r["end_date"], f"{days}"))
        fill_table(self.expired_table, erows)
        for i, r in enumerate(expd):
            self.expired_table.item(i, 0).setData(Qt.UserRole, r["member_id"])

        # ---- in-app notification for expiring subscriptions ----
        for i in range(self._notif_container.count()):
            w = self._notif_container.itemAt(i).widget()
            if w:
                w.deleteLater()
        while self._notif_container.count():
            self._notif_container.takeAt(0)
        self._notif_container.addStretch()

        if rows:
            from app.gui.widgets import notification_bar
            msg = _("expiring_notification").replace("{n}", str(len(rows)))
            bar = notification_bar(msg, "warning")
            bar.clicked = None
            bar.mousePressEvent = lambda evt: self.main.show_page("subscriptions")
            self._notif_container.insertWidget(0, bar)


    def _goto_members(self):
        self.main.show_page("members")

    def _goto_checkin(self):
        self.main.show_page("attendance")

    def _goto_payments(self):
        self.main.show_page("payments")

    def _quick_payment(self):
        from app.gui.dialogs.subscription_dialog import QuickPaymentDialog
        dlg = QuickPaymentDialog(self.app_ctx, self)
        dlg.exec()