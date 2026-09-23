from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QSizePolicy, QMessageBox,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont, QPixmap
import os

import app.database as db
from app.i18n import _
from app.gui import style
from app.gui.widgets import (
    make_table, fill_table, primary_button, secondary_button,
    make_input, window_controls,
)
from app.gui.dialogs.subscription_dialog import SubscriptionDialog


class MemberPassportDialog(QDialog):
    """Comprehensive single-member view: profile card, subscription timeline,
    and payment history.  Opened from MembersPage via double-click."""

    def __init__(self, app_ctx, parent, member_id):
        super().__init__(parent)
        window_controls(self)
        self.app_ctx = app_ctx
        self.member_id = member_id
        self.member = db.fetch_one(
            "SELECT * FROM members WHERE id=?", (member_id,))
        if not self.member:
            QMessageBox.warning(self, _("app_title"), _("no_data"))
            self.reject()
            return
        self.setWindowTitle(_("member_passport"))
        self.resize(900, 800)
        self.setStyleSheet(
            f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};"
        )
        self._build()

    # ------------------------------------------------------------------ build
    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # ---- profile card ----
        card = self._profile_card()
        layout.addWidget(card)

        # ---- subscription timeline ----
        tl_box = QFrame()
        tl_box.setObjectName("Card")
        tl_box.setStyleSheet(style.CARD_QSS)
        tl_lay = QVBoxLayout(tl_box)
        tl_lay.setContentsMargins(16, 14, 16, 14)
        tl_lay.setSpacing(8)
        tl_lbl = QLabel(_("subscriptions_list"))
        tl_lbl.setStyleSheet(
            f"color:{style.TEXT.name()}; font-size:15px; font-weight:bold;"
        )
        tl_lay.addWidget(tl_lbl)
        self._timeline_widget = QFrame()
        tl_lay.addWidget(self._timeline_widget)
        layout.addWidget(tl_box, 2)

        # ---- payment history ----
        pay_box = QFrame()
        pay_box.setObjectName("Card")
        pay_box.setStyleSheet(style.CARD_QSS)
        pay_lay = QVBoxLayout(pay_box)
        pay_lay.setContentsMargins(16, 14, 16, 14)
        pay_lay.setSpacing(8)
        pay_lbl = QLabel(_("payments"))
        pay_lbl.setStyleSheet(
            f"color:{style.TEXT.name()}; font-size:15px; font-weight:bold;"
        )
        pay_lay.addWidget(pay_lbl)
        self.table = make_table(
            [_("date"), _("amount"), _("payment_method"), _("reference")],
            stretch_col=0,
        )
        pay_lay.addWidget(self.table, 2)
        layout.addWidget(pay_box, 2)

        # ---- attendance history ----
        att_box = QFrame()
        att_box.setObjectName("Card")
        att_box.setStyleSheet(style.CARD_QSS)
        att_lay = QVBoxLayout(att_box)
        att_lay.setContentsMargins(16, 14, 16, 14)
        att_lay.setSpacing(8)
        att_hdr = QHBoxLayout()
        att_lbl = QLabel(_("attendance_history"))
        att_lbl.setStyleSheet(
            f"color:{style.TEXT.name()}; font-size:15px; font-weight:bold;"
        )
        att_hdr.addWidget(att_lbl)
        att_hdr.addStretch()
        self.att_this_month = QLabel("")
        self.att_best_month = QLabel("")
        for lbl in (self.att_this_month, self.att_best_month):
            lbl.setStyleSheet(f"color:{style.MUTED.name()}; font-size:12px;")
        att_hdr.addWidget(self.att_this_month)
        att_hdr.addWidget(self.att_best_month)
        att_lay.addLayout(att_hdr)
        self.att_table = make_table(
            [_("date"), _("check_in_time"), _("method")],
            stretch_col=0,
        )
        att_lay.addWidget(self.att_table, 2)
        layout.addWidget(att_box, 2)

        # ---- buttons ----
        btns = QHBoxLayout()
        btns.addStretch()
        b_renew = primary_button(f"🔄 {_('renew_subscription')}")
        b_renew.clicked.connect(self._renew)
        btns.addWidget(b_renew)
        b_print = secondary_button(f"🖨 {_('export_pdf')}")
        b_print.clicked.connect(self._print_passport)
        btns.addWidget(b_print)
        b_close = secondary_button(_("close"))
        b_close.clicked.connect(self.accept)
        btns.addWidget(b_close)
        layout.addLayout(btns)

        self._load_timeline()
        self._load_payments()
        self._load_attendance()

    # ------------------------------------------------------------------ ui
    def _profile_card(self):
        card = QFrame()
        card.setObjectName("Card")
        card.setStyleSheet(style.CARD_QSS)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)

        body = QHBoxLayout()
        body.setSpacing(16)
        self.photo_lbl = QLabel()
        self.photo_lbl.setFixedSize(96, 96)
        self.photo_lbl.setAlignment(Qt.AlignCenter)
        self.photo_lbl.setStyleSheet(
            f"background:{style.FIELD.name()}; border:1px solid {style.BORDER.name()};"
            f"border-radius:8px; font-size:32px; color:{style.MUTED.name()};"
        )
        self._load_photo()
        body.addWidget(self.photo_lbl)
        right = QVBoxLayout()
        right.setSpacing(6)

        top = QHBoxLayout()
        name_lbl = QLabel(self.member["full_name"])
        name_lbl.setStyleSheet(
            f"color:{style.TEXT.name()}; font-size:18px; font-weight:bold;"
        )
        top.addWidget(name_lbl)
        top.addStretch()
        tags = QHBoxLayout()
        status = _("active") if self.member["is_active"] else _("inactive")
        color = style.SUCCESS.name() if self.member["is_active"] else style.MUTED.name()
        stag = QLabel(status.upper())
        stag.setStyleSheet(f"color:{color}; font-size:11px; font-weight:bold; padding:2px 8px; border-radius:4px;")
        stag.setAlignment(Qt.AlignCenter)
        stag.setFixedWidth(80)
        tags.addWidget(stag)
        top.addLayout(tags)
        right.addLayout(top)

        info = QHBoxLayout()
        info.setSpacing(24)
        info.addWidget(self._info_row("🆔", _("member_code"), self.member["code"]))
        info.addWidget(self._info_row("📱", _("phone"), self.member["phone"] or "-"))
        info.addWidget(self._info_row("✉️", _("email"), self.member["email"] or "-"))
        info.addStretch()
        right.addLayout(info)

        info2 = QHBoxLayout()
        info2.setSpacing(24)
        info2.addWidget(self._info_row("📅", _("join_date"), self.member["join_date"]))
        if self.member.get("fingerprint_id"):
            info2.addWidget(self._info_row("🔢", _("fingerprint_id"), self.member["fingerprint_id"]))
        info2.addStretch()
        right.addLayout(info2)
        body.addLayout(right, 1)
        lay.addLayout(body)
        return card

    def _load_photo(self):
        path = (self.member or {}).get("photo_path") or ""
        if path and os.path.exists(path):
            try:
                _pix = QPixmap(path)
                if not _pix.isNull():
                    self.photo_lbl.setPixmap(
                        _pix.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    )
                    return
            except Exception:
                pass
        self.photo_lbl.setText("\U0001F464")

    @staticmethod
    def _info_row(icon, label, value):
        h = QHBoxLayout()
        h.setSpacing(6)
        icol = QLabel(icon)
        icol.setFixedWidth(20)
        h.addWidget(icol)
        lbl = QLabel(f"<b>{_(label)}</b>: {value}")
        lbl.setStyleSheet(f"color:{style.TEXT.name()}; font-size:13px;")
        h.addWidget(lbl)
        w = QFrame()
        w.setLayout(h)
        return w

    def _build_timeline(self):
        """Build a vertical timeline of subscriptions."""
        subs = db.fetch_all(
            """SELECT * FROM subscriptions
               WHERE member_id=? ORDER BY start_date DESC""",
            (self.member_id,),
        )
        lay = self._timeline_widget.layout()
        if lay is None:
            lay = QVBoxLayout(self._timeline_widget)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(8)
        for child in list(lay.children()):
            child.deleteLater()
        if not subs:
            lay.addWidget(QLabel(_("no_data")))
            return

        for s in subs:
            item = self._sub_timeline_item(s)
            lay.addWidget(item)

    def _sub_timeline_item(self, sub):
        plan = db.fetch_one("SELECT name, duration_days FROM plans WHERE id=?", (sub["plan_id"],))
        plan_name = plan["name"] if plan else "-"
        status_text = _("active") if sub["status"] == "active" else _("expired")
        is_active = sub["status"] == "active"
        color = style.SUCCESS.name() if is_active else style.MUTED.name()
        card = QFrame()
        card.setStyleSheet(style.CARD_QSS)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)

        title = QHBoxLayout()
        title.addWidget(QLabel(f"📅 {sub['start_date']}  →  {sub['end_date']}"))
        title.addStretch()
        stag = QLabel(status_text.upper())
        stag.setStyleSheet(f"color:{color}; font-size:10px; font-weight:bold; padding:1px 6px; border-radius:3px;")
        stag.setAlignment(Qt.AlignCenter)
        title.addWidget(stag)
        lay.addLayout(title)

        lay.addWidget(QLabel(f"{_(plan_name) if False else plan_name} • {_('price')} {sub['price_paid']:.2f}"))
        lay.addWidget(QLabel(f"{sub.get('remaining_sessions', 0)} {_('remaining_sessions')}"))

        if not is_active:
            lay.addStretch()
            btn_lay = QHBoxLayout()
            btn_lay.addStretch()
            b_renew = primary_button(f"🔄 {_('renew_subscription')}")
            b_renew.clicked.connect(lambda _, s=sub: self._renew_with_record(s))
            btn_lay.addWidget(b_renew)
            lay.addLayout(btn_lay)
        return card

    def _renew(self):
        dlg = SubscriptionDialog(self.app_ctx, self, record=None)
        # pre-select member
        idx = next((i for i, m in enumerate(db.fetch_all(
            "SELECT id FROM members WHERE is_active=1 ORDER BY full_name")) if m["id"] == self.member_id), 0)
        if dlg.exec():
            self._load_timeline()
            self._load_payments()

    def _renew_with_record(self, sub):
        # fetch full subscription record for the dialog
        rec = db.fetch_one("SELECT s.*, m.full_name FROM subscriptions s JOIN members m ON s.member_id=m.id WHERE s.id=?", (sub["id"],))
        dlg = SubscriptionDialog(self.app_ctx, self, record=rec, is_renewal=True)
        if dlg.exec():
            self._load_timeline()
            self._load_payments()

    def _load_timeline(self):
        self._build_timeline()

    def _load_payments(self):
        rows = db.fetch_all(
            """SELECT * FROM payments WHERE member_id=? ORDER BY payment_date DESC""",
            (self.member_id,),
        )
        self._payment_rows = rows
        fill_table(
            self.table,
            [(r["payment_date"], f"{r['amount']:.2f}", r["payment_method"] or "-",
               r["reference_number"] or "-") for r in rows],
        )

    def _load_attendance(self):
        rows = db.fetch_all(
            """SELECT date(check_in) AS d, check_in, method
               FROM attendance WHERE member_id=? ORDER BY check_in DESC LIMIT 30""",
            (self.member_id,),
        )
        fill_table(
            self.att_table,
            [(r["d"], str(r["check_in"])[11:16], r["method"] or "-") for r in rows],
        )
        try:
            this_month = db.fetch_one(
                """SELECT COUNT(*) AS c FROM attendance
                   WHERE member_id=? AND date(check_in) >= date('now','start of month')""",
                (self.member_id,),
            )
            best = db.fetch_one(
                """SELECT strftime('%Y-%m', check_in) AS m, COUNT(*) AS c FROM attendance
                   WHERE member_id=? GROUP BY m ORDER BY c DESC, m DESC LIMIT 1""",
                (self.member_id,),
            )
        except Exception:
            this_month = best = None
        self.att_this_month.setText(f"{_('this_month')}: {this_month['c'] if this_month else 0}")
        self.att_best_month.setText(f"{_('best_month')}: {best['c'] if best else 0}" + (f" ({best['m']})" if best else ""))

    def _print_passport(self):
        """Open the member's full passport in the browser, like reports."""
        try:
            from app.invoice import open_passport_html
            path = open_passport_html(self.member, self._payment_rows)
            if not path:
                QMessageBox.warning(self, _("app_title"), _("error_save"))
        except Exception as exc:
            QMessageBox.critical(self, _("app_title"), f"{_('error_save')}\n{exc}")
