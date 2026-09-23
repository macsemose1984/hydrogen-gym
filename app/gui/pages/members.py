from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QMessageBox, QHeaderView, QTableWidgetItem, QComboBox,
    QFileDialog,
)
from PySide6.QtCore import Qt

import app.database as db
from app.i18n import _
from app.gui import style
from app.gui.widgets import (
    page_title, make_table, fill_table, primary_button, secondary_button,
    danger_button,
)
from app.gui.dialogs.member_dialog import MemberDialog
from app.gui.dialogs.member_passport import MemberPassportDialog


class MembersPage(QWidget):
    def __init__(self, app_ctx, main):
        super().__init__()
        self.app_ctx = app_ctx
        self.main = main
        self._rows = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        head = QHBoxLayout()
        head.addWidget(page_title(_("members")))
        head.addStretch()
        b_add = primary_button(f"➕ {_('add_member')}")
        b_add.clicked.connect(self.add_member)
        b_del = danger_button(f"🗑️ {_('delete')}")
        b_del.clicked.connect(self.delete_member)
        b_exp = secondary_button(f"📊 {_('export')}")
        b_exp.clicked.connect(self.export)
        head.addWidget(b_add)
        head.addWidget(b_del)
        b_pass = secondary_button(f"📄 {_('member_passport')}")
        b_pass.clicked.connect(self.open_passport)
        head.addWidget(b_pass)
        head.addWidget(b_exp)
        layout.addLayout(head)

        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(f"🔍 {_('search')}...")
        self.search.textChanged.connect(self.apply_filter)
        self.search.setStyleSheet(style.INPUT_QSS)
        bar.addWidget(self.search, 1)

        self.filter = QComboBox()
        self.filter.addItems([_("all"), _("status_active"), _("status_expiring"), _("status_expired")])
        self.filter.currentIndexChanged.connect(self.apply_filter)
        self.filter.setStyleSheet(style.INPUT_QSS)
        bar.addWidget(self.filter)
        layout.addLayout(bar)

        self.table = make_table(
            [_("member_code"), _("full_name"), _("phone"), _("gender"),
             _("coach"), _("join_date"), _("status")],
            stretch_col=1,
        )
        self.table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table, 1)

        btn_row = QHBoxLayout()
        b_edit = secondary_button(f"✏️ {_('edit')}")
        b_wa = primary_button(f"💬 {_('send_whatsapp')}")
        b_edit.clicked.connect(self.edit_member)
        b_wa.clicked.connect(self.send_whatsapp)
        for b in (b_edit, b_wa):
            btn_row.addWidget(b)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def refresh(self):
        self._rows = db.fetch_all(
            "SELECT m.*, c.full_name AS coach_name, (SELECT s.end_date FROM subscriptions s "
            "WHERE s.member_id = m.id AND s.status = 'active' ORDER BY s.end_date DESC LIMIT 1) AS sub_end "
            "FROM members m LEFT JOIN coaches c ON m.coach_id=c.id ORDER BY m.join_date DESC"
        )
        self.apply_filter()

    def _sub_status(self, r):
        from datetime import datetime
        ed = r.get("sub_end")
        if not ed:
            return 2
        try:
            end = datetime.strptime(ed, "%Y-%m-%d").date()
            today = datetime.strptime(db.today(), "%Y-%m-%d").date()
        except Exception:
            return 2
        diff = (end - today).days
        if diff < 0:
            return 2
        if diff <= 7:
            return 1
        return 0

    def _status_text(self, st):
        return (_("status_active"), _("status_expiring"), _("status_expired"))[st]

    def apply_filter(self, *_args):
        term = self.search.text().strip().lower()
        mode = self.filter.currentIndex()  # 0 all, 1 active, 2 expiring, 3 expired
        from PySide6.QtGui import QColor
        status_colors = {0: QColor("#2e7d32"), 1: QColor("#ef6c00"), 2: QColor("#c62828")}
        rows = []
        for r in self._rows:
            if term and term not in f"{r['full_name']} {r['phone']} {r['code']} {r.get('coach_name') or ''}".lower():
                continue
            st = self._sub_status(r)
            if mode and mode - 1 != st:
                continue
            rows.append(r)
        fill_table(
            self.table,
            [
                (r["code"], r["full_name"], r["phone"], r["gender"],
                 r["coach_name"] or "-", r["join_date"],
                 self._status_text(self._sub_status(r)))
                for r in rows
            ],
        )
        for row_i, r in enumerate(rows):
            item = self.table.item(row_i, 0)
            item.setData(Qt.UserRole, r["id"])
            st = self._sub_status(r)
            bg = QColor(style.SUCCESS.name()).lighter(150) if r["is_active"] else QColor(style.MUTED.name()).lighter(130)
            for c in range(self.table.columnCount()):
                ci = self.table.item(row_i, c)
                if ci:
                    ci.setBackground(bg)
            sc = self.table.item(row_i, 6)
            if sc:
                sc.setForeground(status_colors[st])
                font = sc.font()
                font.setBold(True)
                sc.setFont(font)

    def selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, _("app_title"), _("select_member"))
            return None
        item = self.table.item(row, 0)
        return int(item.data(Qt.UserRole)) if item and item.data(Qt.UserRole) else None

    def open_passport(self):
        mid = self.selected_id()
        if mid is None:
            return
        dlg = MemberPassportDialog(self.app_ctx, self, mid)
        dlg.exec()

    def add_member(self):
        dlg = MemberDialog(None, self.app_ctx, self)
        if dlg.exec():
            self.refresh()

    def edit_member(self):
        mid = self.selected_id()
        if mid is None:
            return
        rec = db.fetch_one("SELECT * FROM members WHERE id=?", (mid,))
        dlg = MemberDialog(rec, self.app_ctx, self)
        if dlg.exec():
            self.refresh()

    def delete_member(self):
        mid = self.selected_id()
        if mid is None:
            return
        if QMessageBox.question(self, _("app_title"), _("confirm_delete")) == QMessageBox.Yes:
            row = db.fetch_one("SELECT full_name FROM members WHERE id=?", (mid,))
            name = row["full_name"] if row else str(mid)
            db.move_to_trash("members", mid)
            db.log_user_action("حذف عضو", "عضو", name, f"ID: {mid}")
            self.refresh()

    def send_whatsapp(self):
        mid = self.selected_id()
        if mid is None:
            return
        self.main.show_page("whatsapp")
        self.main.pages["whatsapp"].set_member(mid)

    def export(self):
        from app.export import export_table
        headers = [_("member_code"), _("full_name"), _("phone"), _("gender"),
                   _("coach"), _("join_date"), _("status")]
        rows = [
            (r["code"], r["full_name"], r["phone"], r["gender"],
             r["coach_name"] or "-", r["join_date"],
             self._status_text(self._sub_status(r)))
            for r in self._rows
        ]
        path = export_table(headers, rows, "members")
        self._open_export(path)

    def _open_export(self, path):
        import os
        import webbrowser
        if not path:
            QMessageBox.warning(self, _("app_title"), _("error_save"))
            return
        webbrowser.open(os.path.abspath(path))
        QMessageBox.information(self, _("app_title"), _("export_done"))

    def _on_double_click(self, row, col):
        # النقر المزدوج الآن يفتح تجديد الاشتراك مباشرة مع اختيار العضو تلقائياً
        mid = self.table.item(row, 0).data(Qt.UserRole) if self.table.item(row, 0) else None
        if mid is None:
            return
        from app.gui.dialogs.subscription_dialog import SubscriptionDialog
        # مرّر عضو مُحدد مسبقاً — سيُختار تلقائياً بدون بحث
        rec = {"member_id": int(mid)}
        dlg = SubscriptionDialog(self.app_ctx, self, record=rec)
        # في حالة التجديد نترك is_renewal=False لأننا ننشئ اشتراك جديد؛
        # _load سيتعامل مع member_id فقط ويحافظ على حساب التاريخ تلقائياً
        if dlg.exec():
            self.refresh()
            # حدّث صفحة الاشتراكات إذا كانت مفتوحة
            try:
                if hasattr(self.main, "pages") and "subscriptions" in self.main.pages:
                    self.main.pages["subscriptions"].refresh()
            except Exception:
                pass