from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QMessageBox, QLabel,
    QComboBox, QPushButton,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from datetime import datetime

import app.database as db
from app.i18n import _
from app.gui import style
from app.gui.widgets import (
    page_title, make_table, fill_table, primary_button, secondary_button,
    make_input,
)


class SyncWorker(QThread):
    result = Signal(dict)

    def __init__(self, ip, port, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.port = port

    def run(self):
        from app.zk import import_attendance
        self.result.emit(import_attendance(self.ip, self.port))


def _alert_beep():
    """Audible alert: system beep + Windows exclamation sound."""
    from PySide6.QtWidgets import QApplication

    QApplication.beep()
    try:
        import winsound

        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except Exception:
        pass


class AttendancePage(QWidget):
    def __init__(self, app_ctx, main):
        super().__init__()
        self.app_ctx = app_ctx
        self.main = main
        self._rows = []
        self._syncing = False
        self._manual = False
        self._worker = None
        self._build()
        self._setup_autosync()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        head = QHBoxLayout()
        head.addWidget(page_title(_("attendance")))
        head.addStretch()

        self.search = QLineEdit()
        self.search.setPlaceholderText(f"🔍 {_('search')}...")
        self.search.textChanged.connect(self.apply_filter)
        self.search.setFixedWidth(220)
        self.search.setStyleSheet(style.INPUT_QSS)
        head.addWidget(self.search)

        self.status_lbl = QLabel(_("auto_sync_off"))
        self.status_lbl.setStyleSheet(f"color:{style.MUTED.name()}; font-size:12px;")
        head.addWidget(self.status_lbl)
        layout.addLayout(head)

        bar = QHBoxLayout()
        bar.setSpacing(10)

        self.b_auto = QPushButton(f"🔄 {_('auto_sync')}")
        self.b_auto.setCheckable(True)
        self.b_auto.setStyleSheet(style.INPUT_QSS)
        self.b_auto.toggled.connect(self._toggle_auto)
        bar.addWidget(self.b_auto)

        b_in = primary_button(f"⏰ {_('check_in')}")
        b_comp = secondary_button(f"👥 {_('compare_fingerprints')}")
        b_sync = secondary_button(f"🔁 {_('sync_attendance')}")
        b_exp = secondary_button(f"📊 {_('export')}")
        b_in.clicked.connect(self.check_in)
        b_comp.clicked.connect(self.open_compare)
        b_sync.clicked.connect(self.sync_device)
        b_exp.clicked.connect(self.export)
        bar.addWidget(b_in)
        bar.addWidget(b_comp)
        bar.addWidget(b_sync)
        bar.addWidget(b_exp)
        bar.addStretch()
        layout.addLayout(bar)

        self.table = make_table(
            [_("full_name"), _("end_date"), _("phone"), _("check_in_time")],
            stretch_col=0,
        )
        layout.addWidget(self.table, 1)

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

    def _setup_autosync(self):
        auto_on = db.get_setting("device_autosync", "1") != "0"
        try:
            interval = int(db.get_setting("device_autosync_interval", "1") or 1)
        except ValueError:
            interval = 1
        self._auto_on = False
        self._offline_warned = False
        # مرة واحدة في اليوم لكل عضو منتهي — لتجنب تكرار التنبيه كل مزامنة
        self._warned_expired_ids = set()
        self._warned_date = db.today()
        self._timer = QTimer(self)
        self._timer.setInterval(max(1, interval) * 1000)
        self._timer.timeout.connect(self._auto_sync)
        self.b_auto.setChecked(auto_on)
        if auto_on:
            self._auto_on = True
            self._timer.start()
            self._auto_sync()

    def cleanup(self):
        """Stop timer and wait for any running worker thread."""
        self._auto_on = False
        self._timer.stop()
        self._syncing = False
        if self._worker is not None:
            try:
                self._worker.quit()
                self._worker.wait(3000)
            except Exception:
                pass
            self._worker = None

    def _toggle_auto(self, on):
        self._auto_on = on
        db.set_setting("device_autosync", "1" if on else "0")
        if on:
            self._timer.start()
            self._auto_sync()
        else:
            self._timer.stop()
            self.status_lbl.setText(_("auto_sync_off"))
            self.status_lbl.setStyleSheet(f"color:{style.MUTED.name()}; font-size:12px;")

    def _auto_sync(self, *_args):
        if not self._auto_on or self._syncing:
            return
        self._manual = False
        self._start_sync()

    def sync_device(self):
        if self._syncing:
            QMessageBox.information(self, _("app_title"), _("sync_running"))
            return
        self._manual = True
        self._start_sync()

    def open_compare(self):
        from app.gui.dialogs.compare_dialog import CompareDialog
        dlg = CompareDialog(self)
        dlg.exec()

    def open_movements_compare(self):
        from app.gui.dialogs.movements_compare import MovementsCompareDialog
        dlg = MovementsCompareDialog(self)
        dlg.exec()

    def _start_sync(self):
        ip = db.get_setting("device_ip", "192.168.1.201")
        try:
            port = int(db.get_setting("device_port", "4370") or 4370)
        except ValueError:
            port = 4370
        self._syncing = True
        self._worker = SyncWorker(ip, port)
        self._worker.result.connect(self._on_sync_result)
        self._worker.start()

    def _on_sync_result(self, result):
        self._syncing = False
        was_manual = self._manual
        self._manual = False
        if result.get("errors"):
            self.status_lbl.setText(_("disconnected"))
            self.status_lbl.setStyleSheet(f"color:{style.DANGER.name()}; font-size:12px;")
            if was_manual:
                QMessageBox.critical(
                    self, _("app_title"),
                    f"{_('connection_failed')}\n{result['errors']}",
                )
            if not self._offline_warned:
                self._offline_warned = True
                _alert_beep()
                QMessageBox.warning(self, _("app_title"), _("device_offline_alert"))
            return
        if result["imported"] > 0:
            self.refresh()
            self._warn_expired_today()
        unmatched = result.get("unmatched") or []
        text = (
            f"{_('connected')} · {_('last_sync')} {datetime.now().strftime('%H:%M:%S')}"
            f" · +{result['imported']}"
        )
        if unmatched:
            text += f" · ⚠ {_('unmatched')}: {len(unmatched)}"
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(f"color:{style.SUCCESS.name()}; font-size:12px;")
        self._offline_warned = False
        if not was_manual:
            return
        msg = _("sync_done") + "\n" + _("sync_result").format(imported=result["imported"])
        if unmatched:
            msg += "\n" + _("unmatched_count").format(n=len(unmatched))
        QMessageBox.information(self, _("app_title"), msg)
        self.open_movements_compare()

    def refresh(self):
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")
        rows = db.fetch_all(
            """SELECT a.*, m.full_name, m.phone,
                      (SELECT s.end_date FROM subscriptions s
                        WHERE s.member_id = a.member_id AND s.status = 'active'
                        ORDER BY s.end_date DESC LIMIT 1) AS end_date
               FROM attendance a JOIN members m ON a.member_id = m.id
               WHERE a.check_in >= ?
               ORDER BY a.check_in DESC""",
            (cutoff,),
        )
        from app.zk import _member_fp_map
        mp = _member_fp_map()
        movements = db.fetch_all(
            "SELECT user_id, name, timestamp FROM device_movements "
            "WHERE timestamp >= ? ORDER BY timestamp DESC",
            (cutoff,),
        )
        for mv in movements:
            if not mv["user_id"] or mv["user_id"] in mp:
                continue
            rows.append({
                "id": None,
                "member_id": None,
                "check_in": mv["timestamp"],
                "check_out": None,
                "method": "device",
                "full_name": _("fp_label") + " " + mv["user_id"],
                "phone": "-",
                "device_name": mv["name"] or "-",
            })
        rows.sort(key=lambda r: r["check_in"] or "", reverse=True)
        self._rows = rows
        self.apply_filter()

    def apply_filter(self, *_args):
        term = self.search.text().strip().lower()
        rows = [r for r in self._rows if not term or term in r["full_name"].lower()]
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
                (r["full_name"], r.get("end_date") or "-", r["phone"] or "-",
                 str(r["check_in"])[:16])
                for r in page_rows
            ],
        )
        for i, r in enumerate(page_rows):
            self.table.item(i, 0).setData(Qt.UserRole, r["id"])
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

    def _pick_member(self):
        from app.gui.dialogs.member_picker import MemberPicker
        dlg = MemberPicker(self)
        if dlg.exec():
            return dlg.selected_member()
        return None

    def _warn_expired_today(self):
        # تصفير التتبع عند تغير اليوم
        today = db.today()
        if self._warned_date != today:
            self._warned_date = today
            self._warned_expired_ids.clear()
        rows = db.fetch_all(
            """SELECT DISTINCT m.id, m.full_name
               FROM attendance a
               JOIN members m ON a.member_id = m.id
               JOIN subscriptions s ON s.member_id = m.id AND s.status = 'active'
               WHERE date(a.check_in) = date('now') AND s.end_date < date('now')"""
        )
        if not rows:
            return
        # اعرض فقط الأعضاء الذين لم يُنبه عنهم اليوم
        new_rows = [r for r in rows if r["id"] not in self._warned_expired_ids]
        if not new_rows:
            return
        for r in new_rows:
            self._warned_expired_ids.add(r["id"])
        _alert_beep()
        names = ", ".join(r["full_name"] for r in new_rows[:10])
        QMessageBox.warning(
            self, _("app_title"),
            _("expired_checkin_alert").format(names=names),
        )

    def check_in(self):
        member = self._pick_member()
        if not member:
            return
        # block expired / inactive members (with override option)
        sub = db.get_latest_subscription(member["id"])
        is_active = member["is_active"] and sub is not None and sub["end_date"] >= db.today()
        if not is_active:
            ans = QMessageBox.question(
                self, _("app_title"),
                _("block_expired_msg").format(name=member["full_name"]),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                return
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # avoid duplicate open check-in
        dup = db.fetch_one(
            "SELECT id FROM attendance WHERE member_id=? AND date(check_in)=date('now') AND check_out IS NULL",
            (member["id"],),
        )
        if dup:
            QMessageBox.information(self, _("app_title"), _("today_checkins"))
            return
        db.execute(
            "INSERT INTO attendance (member_id, check_in, method) VALUES (?,?,?)",
            (member["id"], now, "manual"),
        )
        self.refresh()

    def sync_device(self):
        if self._syncing:
            QMessageBox.information(self, _("app_title"), _("sync_running"))
            return
        self._manual = True
        self._start_sync()

    def export(self):
        from app.export import export_table
        import os
        import webbrowser
        headers = [_("full_name"), _("end_date"), _("phone"), _("check_in_time")]
        rows = [
            (r["full_name"], r.get("end_date") or "-", r["phone"] or "-",
             str(r["check_in"])[:16])
            for r in self._rows
        ]
        path = export_table(headers, rows, "attendance")
        if not path:
            QMessageBox.warning(self, _("app_title"), _("error_save"))
            return
        webbrowser.open(os.path.abspath(path))
        QMessageBox.information(self, _("app_title"), _("export_done"))