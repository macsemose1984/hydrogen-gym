from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

import app.database as db
from app.i18n import _
from app.gui import style
from app.gui.widgets import make_table, fill_table, primary_button, secondary_button, window_controls


class MovementsCompareDialog(QDialog):
    """Show ALL device movements (matched and unmatched) from the raw log,
    link unmatched fingerprints to members and import matched ones."""

    def __init__(self, parent=None):
        super().__init__(parent)
        window_controls(self)
        self._rows = []
        self.setWindowTitle(_("movements_compare"))
        self.resize(680, 520)
        self.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        self.info = QLabel()
        self.info.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px;")
        lay.addWidget(self.info)

        self.search = QLineEdit()
        self.search.setPlaceholderText(f"\U0001F50D {_('search')}...")
        self.search.textChanged.connect(self.apply_filter)
        self.search.setStyleSheet(style.INPUT_QSS)
        lay.addWidget(self.search)

        self.table = make_table(
            [_("time"), _("fingerprint_id"), _("name_on_device"), _("matched_member")],
            stretch_col=3,
        )
        lay.addWidget(self.table, 1)

        btns = QHBoxLayout()
        b_assign = primary_button(f"\U0001F517 {_('link_member')}")
        b_import = primary_button(f"\U0001F4E5 {_('import_matched')}")
        b_refresh = secondary_button(f"\U0001F504 {_('refresh')}")
        b_close = secondary_button(_("close"))
        b_assign.clicked.connect(self.assign_member)
        b_import.clicked.connect(self.import_matched)
        b_refresh.clicked.connect(self.reload)
        b_close.clicked.connect(self.accept)
        btns.addWidget(b_assign)
        btns.addWidget(b_import)
        btns.addWidget(b_refresh)
        btns.addStretch()
        btns.addWidget(b_close)
        lay.addLayout(btns)

        self.reload()

    def reload(self):
        from app.zk import _member_fp_map
        mp = _member_fp_map()
        self._total = db.fetch_one("SELECT COUNT(*) c FROM device_movements")["c"] or 0
        movements = db.fetch_all(
            "SELECT id, uid, user_id, name, timestamp FROM device_movements "
            "ORDER BY timestamp DESC LIMIT 2000"
        )
        self._rows = []
        for mv in movements:
            m = mp.get(mv["user_id"])
            self._rows.append({
                "id": mv["id"],
                "timestamp": mv["timestamp"],
                "user_id": mv["user_id"],
                "name": mv["name"],
                "member_id": m["id"] if m else None,
                "member_name": m["full_name"] if m else "",
            })
        self._render()

    def _filtered(self):
        term = self.search.text().strip().lower()
        if not term:
            return self._rows
        return [
            r for r in self._rows
            if term in (r["user_id"] or "").lower()
            or term in (r["name"] or "").lower()
            or term in (r["member_name"] or "").lower()
            or term in (r["timestamp"] or "").lower()
        ]

    def _render(self):
        rows = self._filtered()
        fill_table(
            self.table,
            [(r["timestamp"], r["user_id"] or "-", r["name"] or "-", r["member_name"] or "-")
             for r in rows],
        )
        tint = QColor(style.DANGER)
        tint.setAlpha(45)
        for i, r in enumerate(rows):
            self.table.item(i, 0).setData(Qt.UserRole, r)
            if not r["member_id"]:
                for c in range(4):
                    it = self.table.item(i, c)
                    if it is not None:
                        it.setBackground(tint)
        matched = sum(1 for r in rows if r["member_id"])
        shown = f"{_('movements')}: {len(rows)}"
        if self._total and self._total > len(self._rows):
            shown += f" / {self._total}"
        self.info.setText(
            f"{shown} \u2022 "
            f"{_('matched')}: {matched} \u2022 "
            f"{_('unmatched')}: {len(rows) - matched}"
        )
        self.info.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px;")

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

    def import_matched(self):
        existing = set(
            (r["member_id"], r["check_in"])
            for r in db.fetch_all("SELECT member_id, check_in FROM attendance")
        )
        att_rows = []
        for r in self._rows:
            if not r["member_id"]:
                continue
            if (r["member_id"], r["timestamp"]) in existing:
                continue
            att_rows.append((r["member_id"], r["timestamp"], "device"))
        imported = db.execute_many(
            "INSERT INTO attendance (member_id, check_in, method) VALUES (?,?,?)",
            att_rows,
        ) if att_rows else 0
        QMessageBox.information(
            self, _("app_title"), _("sync_result").format(imported=imported)
        )
