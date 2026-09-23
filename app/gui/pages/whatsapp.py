from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTextEdit, QMessageBox, QTabWidget,
)
from PySide6.QtCore import Qt

import app.database as db
import app.whatsapp as wa
from app.i18n import _
from app.gui import style
from app.gui.widgets import (
    page_title, make_table, fill_table, primary_button, secondary_button,
)


class SingleSendPanel(QWidget):
    def __init__(self, app_ctx):
        super().__init__()
        self.app_ctx = app_ctx
        self._member = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(12)

        row = QHBoxLayout()
        self.pick = secondary_button(f"👤 {_('select_member')}")
        self.pick.clicked.connect(self._pick)
        row.addWidget(self.pick)
        self.member_lbl = QLabel("—")
        self.member_lbl.setStyleSheet(
            f"color:{style.TEXT.name()}; font-size:14px; font-weight:600;"
        )
        row.addWidget(self.member_lbl)
        row.addStretch()
        lay.addLayout(row)

        t_lbl = QLabel(_("templates"))
        t_lbl.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px; font-weight:600;")
        lay.addWidget(t_lbl)
        self.template = QComboBox()
        self.template.addItems(
            [_("custom"), _("template_welcome"), _("template_renew"),
             _("template_invoice"), _("template_promo")]
        )
        self.template.currentIndexChanged.connect(self._on_template)
        self.template.setStyleSheet(style.INPUT_QSS)
        lay.addWidget(self.template)

        m_lbl = QLabel(_("whatsapp_message"))
        m_lbl.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px; font-weight:600;")
        lay.addWidget(m_lbl)
        self.message = QTextEdit()
        self.message.setFixedHeight(170)
        self.message.setStyleSheet(style.INPUT_QSS)
        lay.addWidget(self.message)

        b_send = primary_button(f"💬 {_('send_whatsapp')}")
        b_send.clicked.connect(self.send)
        lay.addWidget(b_send, 0, Qt.AlignLeft)
        lay.addStretch()

    def _pick(self):
        from app.gui.dialogs.member_picker import MemberPicker
        dlg = MemberPicker(self)
        if dlg.exec():
            self.set_member(dlg.selected_member()["id"])

    def set_member(self, member_id):
        rec = db.fetch_one("SELECT id, full_name, phone FROM members WHERE id=?", (member_id,))
        if rec:
            self._member = dict(rec)
            self.member_lbl.setText(f"{rec['full_name']} — {rec['phone']}")
        self._on_template()

    def _on_template(self, *_args):
        if self.template.currentIndex() == 0:
            return
        key = ["custom", "welcome", "renew", "invoice", "promo"][self.template.currentIndex()]
        member = self._member or {"id": 0, "full_name": "—", "phone": ""}
        self.message.setPlainText(wa.build_message(key, member))

    def send(self):
        if not self._member:
            QMessageBox.information(self, _("app_title"), _("select_member"))
            return
        msg = self.message.toPlainText().strip()
        if not msg:
            QMessageBox.warning(self, _("app_title"), _("error_save"))
            return
        if wa.open_whatsapp(self._member["phone"], msg):
            wa.log_message(self._member["id"], self._member["phone"],
                           str(self.template.currentIndex()), msg)
            QMessageBox.information(self, _("app_title"), _("opening_whatsapp"))
        else:
            QMessageBox.warning(self, _("app_title"), _("phone_invalid"))


class BulkSendPanel(QWidget):
    def __init__(self, app_ctx, expiring_only=False, expired_only=False):
        super().__init__()
        self.app_ctx = app_ctx
        self.expiring_only = expiring_only
        self.expired_only = expired_only
        self._members = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(12)

        if expiring_only or expired_only:
            note_text = _("send_expired") if expired_only else _("send_expiring")
            note = QLabel(f"🔔 {note_text}")
            note.setStyleSheet(f"color:{style.ACCENT.name()}; font-size:13px; font-weight:bold;")
            lay.addWidget(note)

        self.count = QLabel("")
        self.count.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px;")
        lay.addWidget(self.count)

        headers = [_("member"), _("phone")] + ([_("end_date")] if (expiring_only or expired_only) else [])
        self.table = make_table(headers, stretch_col=0)
        lay.addWidget(self.table, 1)

        t_lbl = QLabel(_("templates"))
        t_lbl.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px; font-weight:600;")
        lay.addWidget(t_lbl)
        self.template = QComboBox()
        self.template.addItems(
            [_("custom"), _("template_welcome"), _("template_renew"),
             _("template_invoice"), _("template_promo")]
        )
        self.template.currentIndexChanged.connect(self._on_template)
        self.template.setStyleSheet(style.INPUT_QSS)
        lay.addWidget(self.template)

        m_lbl = QLabel(_("whatsapp_message"))
        m_lbl.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px; font-weight:600;")
        lay.addWidget(m_lbl)
        self.message = QTextEdit()
        self.message.setFixedHeight(120)
        self.message.setStyleSheet(style.INPUT_QSS)
        lay.addWidget(self.message)

        b_send = primary_button(f"💬 {_('send_whatsapp')}")
        b_send.clicked.connect(self.send)
        lay.addWidget(b_send, 0, Qt.AlignLeft)

    def _on_template(self, *_args):
        if self.template.currentIndex() == 0:
            return
        key = ["custom", "welcome", "renew", "invoice", "promo"][self.template.currentIndex()]
        member = self._members[0] if self._members else {"full_name": "—", "phone": ""}
        self.message.setPlainText(wa.build_message(key, member))

    def refresh(self):
        if self.expired_only:
            self._members = wa.list_expired()
        elif self.expiring_only:
            self._members = wa.list_expiring()
        else:
            self._members = wa.list_all_with_phone()
        rows = []
        show_end = self.expiring_only or self.expired_only
        for m in self._members:
            name = m.get("full_name") or m.get("member_name") or ""
            phone = m.get("phone") or ""
            end = m.get("end_date") or ""
            rows.append((name, phone) + ((end,) if show_end else ()))
        fill_table(self.table, rows)
        self.count.setText(f"👥 {len(self._members)}")

    def send(self):
        if not self._members:
            QMessageBox.information(self, _("app_title"), _("no_members_selected"))
            return
        msg = self.message.toPlainText().strip()
        if not msg:
            QMessageBox.warning(self, _("app_title"), _("error_save"))
            return
        opened = 0
        for m in self._members:
            mid = m.get("member_id") or m.get("id")
            if wa.open_whatsapp(m.get("phone") or m.get("member_phone"), msg):
                wa.log_message(mid, m.get("phone") or m.get("member_phone"),
                               str(self.template.currentIndex()), msg)
                opened += 1
        QMessageBox.information(
            self, _("app_title"),
            f"{_('opening_whatsapp')} ({opened})",
        )


class WhatsAppPage(QWidget):
    def __init__(self, app_ctx, main):
        super().__init__()
        self.app_ctx = app_ctx
        self.main = main

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        head = QHBoxLayout()
        head.addWidget(page_title(_("whatsapp")))
        head.addStretch()
        lay.addLayout(head)

        self.tabs = QTabWidget()
        self.single = SingleSendPanel(app_ctx)
        self.bulk = BulkSendPanel(app_ctx)
        self.expiring = BulkSendPanel(app_ctx, expiring_only=True)
        self.expired = BulkSendPanel(app_ctx, expired_only=True)
        self.tabs.addTab(self.single, _("single_send"))
        self.tabs.addTab(self.bulk, _("bulk_send"))
        self.tabs.addTab(self.expiring, _("send_expiring"))
        self.tabs.addTab(self.expired, _("send_expired"))
        lay.addWidget(self.tabs)

    def refresh(self):
        self.bulk.refresh()
        self.expiring.refresh()
        self.expired.refresh()

    def goto_tab(self, name):
        """name in: 'single', 'bulk', 'expiring', 'expired'."""
        target = getattr(self, name, None)
        if target is not None:
            self.tabs.setCurrentWidget(target)
            target.refresh()

    def set_member(self, member_id):
        self.tabs.setCurrentWidget(self.single)
        self.single.set_member(member_id)