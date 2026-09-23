from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor

import app.database as db
from app.i18n import _
from app.gui import style
from app.gui.widgets import make_table, fill_table, primary_button, secondary_button, window_controls


class _CompareWorker(QThread):
    result = Signal(dict)

    def __init__(self, ip, port, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.port = port

    def run(self):
        from app.zk import compare_fingerprints
        try:
            self.result.emit(compare_fingerprints(self.ip, self.port))
        except Exception as e:
            self.result.emit(
                {"rows": [], "users": 0, "matched": 0, "unmatched": 0, "errors": str(e)}
            )


class CompareDialog(QDialog):
    """Compare device fingerprints against members and link unmatched ones."""

    def __init__(self, parent=None):
        super().__init__(parent)
        window_controls(self)
        self._rows = []
        self._worker = None
        self.setWindowTitle(_("compare_fingerprints"))
        self.resize(580, 480)
        self.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        self.info = QLabel(_("connecting") + "...")
        self.info.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px;")
        lay.addWidget(self.info)

        self.search = QLineEdit()
        self.search.setPlaceholderText(f"\U0001F50D {_('search')}...")
        self.search.textChanged.connect(self.apply_filter)
        self.search.setStyleSheet(style.INPUT_QSS)
        lay.addWidget(self.search)

        self.table = make_table(
            [_("fingerprint_id"), _("name_on_device"), _("matched_member")],
            stretch_col=2,
        )
        lay.addWidget(self.table, 1)

        btns = QHBoxLayout()
        b_assign = primary_button(f"👤 {_('assign_member')}")
        b_refresh = secondary_button(f"🔁 {_('refresh')}")
        b_close = secondary_button(_("close"))
        b_assign.clicked.connect(self.assign_member)
        b_refresh.clicked.connect(self.reload)
        b_close.clicked.connect(self.accept)
        btns.addWidget(b_assign)
        btns.addWidget(b_refresh)
        btns.addStretch()
        btns.addWidget(b_close)
        lay.addLayout(btns)

        self.reload()

    def reload(self):
        ip = db.get_setting("device_ip", "192.168.1.201")
        try:
            port = int(db.get_setting("device_port", "4370") or 4370)
        except ValueError:
            port = 4370
        self.info.setText(_("connecting") + "...")
        self.info.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px;")
        self.table.setRowCount(0)
        self._rows = []
        self._worker = _CompareWorker(ip, port, self)
        self._worker.result.connect(self._show_result)
        self._worker.start()

    def _show_result(self, data):
        if data.get("errors"):
            self.info.setText(f"{_('connection_failed')}: {data['errors']}")
            self.info.setStyleSheet(f"color:{style.DANGER.name()}; font-size:13px;")
            self.table.setRowCount(0)
            return
        self._rows = data["rows"]
        self._render()
        self.info.setText(
            f"{_('device_users')}: {data['users']} · "
            f"{_('matched')}: {data['matched']} · "
            f"{_('unmatched')}: {data['unmatched']}"
        )
        self.info.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px;")

    def _filtered(self):
        term = self.search.text().strip().lower()
        if not term:
            return self._rows
        return [
            r for r in self._rows
            if term in (r["user_id"] or "").lower()
            or term in (r["name"] or "").lower()
            or term in (r["member_name"] or "").lower()
        ]

    def _render(self):
        rows = self._filtered()
        fill_table(
            self.table,
            [(r["user_id"], r["name"] or "-", r["member_name"] or "—")
             for r in rows],
        )
        tint = QColor(style.DANGER)
        tint.setAlpha(45)
        for i, r in enumerate(rows):
            self.table.item(i, 0).setData(Qt.UserRole, r)
            if not r["member_id"]:
                for c in range(3):
                    it = self.table.item(i, c)
                    if it is not None:
                        it.setBackground(tint)

    def apply_filter(self, *_args):
        if not self._rows:
            return
        self._render()

    def assign_member(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, _("app_title"), _("select_row"))
            return
        item = self.table.item(row, 0)
        if item is None:
            return
        rec = item.data(Qt.UserRole)
        if rec["member_id"]:
            QMessageBox.information(self, _("app_title"), _("already_matched"))
            return
        from app.gui.dialogs.member_picker import MemberPicker
        dlg = MemberPicker(self)
        if not dlg.exec():
            return
        m = dlg.selected_member()
        if not m:
            return
        dup = db.fetch_one(
            "SELECT id FROM members WHERE fingerprint_id=? AND id!=?",
            (rec["user_id"], m["id"]),
        )
        if dup:
            QMessageBox.warning(self, _("app_title"), _("fp_in_use"))
            return
        db.execute(
            "UPDATE members SET fingerprint_id=? WHERE id=?",
            (rec["user_id"], m["id"]),
        )
        QMessageBox.information(
            self, _("app_title"), _("fp_assigned").format(name=m["full_name"])
        )
        self.reload()
