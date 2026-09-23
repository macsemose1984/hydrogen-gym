from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QMessageBox, QFrame, QDialog, QGridLayout,
)
from PySide6.QtCore import Qt

import app.database as db
from app.i18n import I18n, _
from app.gui import style
from app.gui.widgets import (
    page_title, primary_button, secondary_button, danger_button, make_input,
    form_field, make_combo, make_table, fill_table,
    section_title,
)


class SettingsPage(QWidget):
    def __init__(self, app_ctx, main):
        super().__init__()
        self.app_ctx = app_ctx
        self.main = main
        self._build()

    def _build(self):
        from PySide6.QtWidgets import QGridLayout, QScrollArea
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        layout.addWidget(page_title(_("settings")))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        layout.addWidget(scroll)

        content = QFrame()
        content.setStyleSheet(f"background:{style.BG.name()};")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(18)
        scroll.setWidget(content)

        # ---- General settings section ----
        card = QFrame()
        card.setObjectName("Card")
        card.setStyleSheet(style.CARD_QSS)
        gcl = QVBoxLayout(card)
        gcl.setContentsMargins(26, 24, 26, 24)
        gcl.setSpacing(14)

        gcl.addWidget(section_title(_("general_settings")))

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(20)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnMinimumWidth(0, 150)

        self.gym_name = make_input()
        self.gym_name.setText(db.get_setting("gym_name", ""))
        self.gym_name.setMinimumHeight(40)
        form_field(grid, _("gym_name"), self.gym_name)

        self.gym_phone = make_input()
        self.gym_phone.setText(db.get_setting("gym_phone", ""))
        self.gym_phone.setMinimumHeight(40)
        form_field(grid, _("whatsapp"), self.gym_phone)

        self.currency = make_input()
        self.currency.setText(db.get_setting("currency", ""))
        self.currency.setMinimumHeight(40)
        form_field(grid, _("currency"), self.currency)

        self.lang = QComboBox()
        self.lang.addItem(_("arabic"), "ar")
        self.lang.addItem(_("english"), "en")
        cur = I18n().get_language()
        self.lang.setCurrentIndex(0 if cur == "ar" else 1)
        self.lang.setStyleSheet(style.INPUT_QSS)
        self.lang.setMinimumHeight(40)
        form_field(grid, _("language"), self.lang)

        gcl.addLayout(grid)

        btns = QHBoxLayout()
        b_save = primary_button(_("save"))
        b_save.clicked.connect(self.save)
        btns.addWidget(b_save)
        btns.addStretch()
        gcl.addLayout(btns)

        cl.addWidget(card)

        # ---- ZKTeco device section ----
        dev_card = QFrame()
        dev_card.setObjectName("Card")
        dev_card.setStyleSheet(style.CARD_QSS)
        dcl = QVBoxLayout(dev_card)
        dcl.setContentsMargins(26, 24, 26, 24)
        dcl.setSpacing(14)

        dcl.addWidget(section_title(_("device_section")))

        dgrid = QGridLayout()
        dgrid.setHorizontalSpacing(24)
        dgrid.setVerticalSpacing(20)
        dgrid.setColumnStretch(0, 0)
        dgrid.setColumnStretch(1, 1)
        dgrid.setColumnMinimumWidth(0, 150)

        self.device_ip = make_input()
        self.device_ip.setText(db.get_setting("device_ip", "192.168.1.201"))
        self.device_ip.setMinimumHeight(40)
        form_field(dgrid, _("device_ip"), self.device_ip)

        self.device_port = make_input()
        self.device_port.setText(db.get_setting("device_port", "4370"))
        self.device_port.setMinimumHeight(40)
        form_field(dgrid, _("device_port"), self.device_port)

        dcl.addLayout(dgrid)

        dbtns = QHBoxLayout()
        b_test = secondary_button(_("test_connection"))
        b_test.clicked.connect(self.test_device)
        b_sync = primary_button(_("sync_attendance"))
        b_sync.clicked.connect(self.sync_device)
        dbtns.addWidget(b_test)
        dbtns.addWidget(b_sync)
        dbtns.addStretch()
        dcl.addLayout(dbtns)

        cl.addWidget(dev_card)

        # ---- Backup section ----
        bck_card = QFrame()
        bck_card.setObjectName("Card")
        bck_card.setStyleSheet(style.CARD_QSS)
        bcl = QVBoxLayout(bck_card)
        bcl.setContentsMargins(26, 24, 26, 24)
        bcl.setSpacing(14)

        bcl.addWidget(section_title(_("backup")))

        self.backup_lbl = QLabel("")
        self.backup_lbl.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px;")
        self._update_backup_label()
        bcl.addWidget(self.backup_lbl)

        bbtns = QHBoxLayout()
        b_backup = primary_button(_("backup_now"))
        b_backup.clicked.connect(self.backup_now)
        b_restore = secondary_button(_("restore_backup"))
        b_restore.clicked.connect(self.restore_backup)
        bbtns.addWidget(b_backup)
        bbtns.addWidget(b_restore)
        bbtns.addStretch()
        bcl.addLayout(bbtns)

        cl.addWidget(bck_card)

        # ---- Direct receiving (ADMS) section ----
        adms_card = QFrame()
        adms_card.setObjectName("Card")
        adms_card.setStyleSheet(style.CARD_QSS)
        acl = QVBoxLayout(adms_card)
        acl.setContentsMargins(26, 24, 26, 24)
        acl.setSpacing(14)

        acl.addWidget(section_title(_("adms_title")))

        agrid = QGridLayout()
        agrid.setHorizontalSpacing(24)
        agrid.setVerticalSpacing(20)
        agrid.setColumnStretch(0, 0)
        agrid.setColumnStretch(1, 1)
        agrid.setColumnMinimumWidth(0, 150)

        self.adms_enabled = QComboBox()
        self.adms_enabled.addItem(_("disabled"), "0")
        self.adms_enabled.addItem(_("enabled"), "1")
        self.adms_enabled.setCurrentIndex(0 if db.get_setting("adms_enabled", "0") != "1" else 1)
        self.adms_enabled.setStyleSheet(style.INPUT_QSS)
        self.adms_enabled.setMinimumHeight(40)
        form_field(agrid, _("adms_enabled"), self.adms_enabled)

        self.adms_port = make_input()
        self.adms_port.setText(db.get_setting("adms_port", "8090"))
        self.adms_port.setMinimumHeight(40)
        form_field(agrid, _("adms_port"), self.adms_port)

        acl.addLayout(agrid)

        from app.adms import get_local_ip
        ip_hint = QLabel(_("adms_ip_hint").format(ip=get_local_ip()))
        ip_hint.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px;")
        ip_hint.setWordWrap(True)
        acl.addWidget(ip_hint)

        abtns = QHBoxLayout()
        b_adms_save = secondary_button(_("save"))
        b_adms_save.clicked.connect(self.save)
        abtns.addWidget(b_adms_save)
        abtns.addStretch()
        acl.addLayout(abtns)

        cl.addWidget(adms_card)

        # ---- Users & Permissions ----
        users_card = QFrame()
        users_card.setObjectName("Card")
        users_card.setStyleSheet(style.CARD_QSS)
        ucl = QVBoxLayout(users_card)
        ucl.setContentsMargins(26, 24, 26, 24)
        ucl.setSpacing(14)
        ucl.addWidget(section_title(_("user_management")))
        # permissions hint
        perm_hint = QLabel(_("perm_hint"))
        perm_hint.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px;")
        perm_hint.setWordWrap(True)
        ucl.addWidget(perm_hint)
        self.users_table = make_table([_("username"), _("full_name"), _("role")], stretch_col=1)
        self.users_table.setMinimumHeight(180)
        ucl.addWidget(self.users_table)
        ubtns = QHBoxLayout()
        b_uadd = primary_button(f"➕ {_('add')}")
        b_uedit = secondary_button(f"✏️ {_('edit')}")
        b_udel = danger_button(f"🗑️ {_('delete')}")
        b_uadd.clicked.connect(self._add_user)
        b_uedit.clicked.connect(self._edit_user)
        b_udel.clicked.connect(self._delete_user)
        ubtns.addWidget(b_uadd)
        ubtns.addWidget(b_uedit)
        ubtns.addWidget(b_udel)
        ubtns.addStretch()
        ucl.addLayout(ubtns)
        cl.addWidget(users_card)
        self._refresh_users()

        # ---- User actions log (حركات اليوزر: إضافة/تعديل/حذف) ----
        log_card = QFrame()
        log_card.setObjectName("Card")
        log_card.setStyleSheet(style.CARD_QSS)
        lcl = QVBoxLayout(log_card)
        lcl.setContentsMargins(26, 24, 26, 24)
        lcl.setSpacing(14)
        lcl.addWidget(section_title(_("user_movements_log")))
        log_hint = QLabel("سجل حركات اليوزر: إضافة عضو/مشترك/دفعة/حذف — آخر 24 ساعة")
        log_hint.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px;")
        log_hint.setWordWrap(True)
        lcl.addWidget(log_hint)
        log_btns = QHBoxLayout()
        b_log = primary_button(f"🖨️ {_('print_24h_report')}")
        b_log.clicked.connect(self.print_user_actions_24h)
        log_btns.addWidget(b_log)
        log_btns.addStretch()
        lcl.addLayout(log_btns)
        cl.addWidget(log_card)
        cl.addStretch()

    def restore_backup(self):
        from PySide6.QtWidgets import QDialog, QListWidget, QListWidgetItem
        import app.backup as bk
        backups = bk.list_backups()
        if not backups:
            QMessageBox.information(self, _("app_title"), _("no_backup"))
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(_("restore_backup_title"))
        dlg.resize(420, 360)
        dlg.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)
        lst = QListWidget()
        lst.setStyleSheet(style.INPUT_QSS)
        for b in backups:
            kb = b["size"] / 1024
            item = QListWidgetItem(f"🗓️ {b['date']}   ({kb:.0f} KB)")
            item.setData(Qt.UserRole, b["path"])
            lst.addItem(item)
        lay.addWidget(lst)
        btns = QHBoxLayout()
        b_ok = primary_button(_("restore_backup"))
        b_cancel = secondary_button(_("cancel"))
        lay.addLayout(btns)
        btns.addWidget(b_cancel)
        btns.addStretch()
        btns.addWidget(b_ok)

        chosen = {"path": None}

        def _pick():
            row = lst.currentRow()
            if row < 0:
                return
            chosen["path"] = lst.item(row).data(Qt.UserRole)
            dlg.accept()

        b_ok.clicked.connect(_pick)
        b_cancel.clicked.connect(dlg.reject)
        if dlg.exec() != dlg.Accepted or not chosen["path"]:
            return
        if QMessageBox.question(self, _("app_title"), _("restore_backup_confirm")) != QMessageBox.Yes:
            return
        ok, msg = bk.restore_database(chosen["path"])
        if ok:
            QMessageBox.information(self, _("app_title"), msg)
        else:
            QMessageBox.critical(self, _("app_title"), msg)
        self._update_backup_label()

    def backup_now(self):
        import app.backup as bk
        path = bk.backup_database()
        if path:
            QMessageBox.information(self, _("app_title"), _("backup_done"))
        else:
            QMessageBox.warning(self, _("app_title"), _("error_save"))
        self._update_backup_label()

    def _update_backup_label(self):
        import app.backup as bk
        last = bk.last_backup_date()
        if last:
            self.backup_lbl.setText(_("last_backup").format(date=last))
        else:
            self.backup_lbl.setText(_("no_backup"))

    def _device_args(self):
        ip = self.device_ip.text().strip() or "192.168.1.201"
        try:
            port = int(self.device_port.text().strip() or "4370")
        except ValueError:
            port = 4370
        return ip, port

    def test_device(self):
        from app.zk import ZKTecoDevice
        ip, port = self._device_args()
        dev = ZKTecoDevice(ip, port)
        ok, info = dev.test()
        if not ok:
            QMessageBox.critical(self, _("app_title"), f"{_('connection_failed')}\n{ip}:{port}\n{info}")
            return
        db.set_setting("device_ip", ip)
        db.set_setting("device_port", str(port))
        QMessageBox.information(
            self, _("app_title"),
            _("connected_success") + "\n\n" + _("connected_info").format(
                serial=info.get("serial") or "-",
                users=info.get("users") or 0,
                attendance=info.get("attendance") or 0,
            ),
        )

    def sync_device(self):
        from app.zk import import_attendance
        ip, port = self._device_args()
        result = import_attendance(ip, port)
        db.set_setting("device_ip", ip)
        db.set_setting("device_port", str(port))
        if result.get("errors"):
            QMessageBox.critical(self, _("app_title"), f"{_('connection_failed')}\n{result['errors']}")
            return
        QMessageBox.information(
            self, _("app_title"),
            _("sync_done") + "\n" + _("sync_result").format(imported=result["imported"]),
        )

    def print_user_actions_24h(self):
        import app.reports as reports
        reports.user_actions_24h_report()

    # ---- users ----
    def _refresh_users(self):
        rows = db.fetch_all("SELECT * FROM users ORDER BY role, username")
        fill_table(self.users_table, [(r["username"], r["full_name"] or "-", _(r["role"]) if r["role"] in ("admin","reception") else r["role"]) for r in rows])
        for i, r in enumerate(rows):
            self.users_table.item(i, 0).setData(Qt.UserRole, r["id"])

    def _selected_user_id(self):
        row = self.users_table.currentRow()
        if row < 0:
            QMessageBox.information(self, _("app_title"), _("select_member"))
            return None
        return int(self.users_table.item(row, 0).data(Qt.UserRole))

    def _add_user(self):
        dlg = UserDialog(self.app_ctx, self)
        if dlg.exec():
            self._refresh_users()
            db.log_user_action("إضافة يوزر", "يوزر", dlg.username.text().strip(), f"دور: {dlg.role.currentData()}")

    def _edit_user(self):
        uid = self._selected_user_id()
        if uid is None:
            return
        rec = db.fetch_one("SELECT * FROM users WHERE id=?", (uid,))
        dlg = UserDialog(self.app_ctx, self, record=rec)
        if dlg.exec():
            self._refresh_users()
            db.log_user_action("تعديل يوزر", "يوزر", rec["username"], f"→ {dlg.username.text().strip()}")

    def _delete_user(self):
        uid = self._selected_user_id()
        if uid is None:
            return
        rec = db.fetch_one("SELECT * FROM users WHERE id=?", (uid,))
        if rec and rec["username"] == "admin" and db.fetch_all("SELECT id FROM users").__len__() == 1:
            QMessageBox.warning(self, _("app_title"), _("cannot_delete_last_admin"))
            return
        if QMessageBox.question(self, _("app_title"), _("confirm_delete")) != QMessageBox.Yes:
            return
        db.execute("DELETE FROM users WHERE id=?", (uid,))
        db.log_user_action("حذف يوزر", "يوزر", rec["username"] if rec else str(uid), "")
        self._refresh_users()

    def save(self):
        db.set_setting("gym_name", self.gym_name.text().strip())
        db.set_setting("gym_phone", self.gym_phone.text().strip())
        db.set_setting("currency", self.currency.text().strip())
        db.set_setting("device_ip", self.device_ip.text().strip())
        db.set_setting("device_port", self.device_port.text().strip())
        db.set_setting("adms_enabled", self.adms_enabled.currentData())
        db.set_setting("adms_port", self.adms_port.text().strip() or "8090")
        _restart = getattr(self.app_ctx, "adms_restart", None)
        if _restart:
            _restart()
        db.set_setting("user_lang", self.lang.currentData())
        old = I18n().get_language()
        new = self.lang.currentData()
        if new != old:
            I18n().set_language(new)
            self.app_ctx.restart_ui()
        else:
            QMessageBox.information(self, _("app_title"), _("settings_saved"))


class UserDialog(QDialog):
    def __init__(self, app_ctx, parent=None, record=None):
        super().__init__(parent)
        self.record = record
        self.setWindowTitle(_("edit") if record else _("add"))
        self.resize(420, 320)
        self.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)
        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(0, 1)
        # username
        self.username = QLineEdit()
        self.username.setStyleSheet(style.INPUT_QSS)
        form_field(grid, _("username") + " *", self.username)
        # full name
        self.full_name = QLineEdit()
        self.full_name.setStyleSheet(style.INPUT_QSS)
        form_field(grid, _("full_name"), self.full_name)
        # password
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setStyleSheet(style.INPUT_QSS)
        self.password.setPlaceholderText("••••" if record else "")
        form_field(grid, _("password") + (" *" if not record else ""), self.password)
        # role
        self.role = QComboBox()
        self.role.addItem(_("admin"), "admin")
        self.role.addItem(_("reception"), "reception")
        self.role.setStyleSheet(style.INPUT_QSS)
        form_field(grid, _("role") + " *", self.role)
        # perm hint per role
        self.hint = QLabel(_("perm_hint_reception") if self.role.currentData() == "reception" else _("perm_hint_admin"))
        self.hint.setStyleSheet(f"color:{style.MUTED.name()}; font-size:12px;")
        self.hint.setWordWrap(True)
        self.role.currentIndexChanged.connect(self._update_hint)
        grid.addWidget(self.hint, grid.rowCount(), 0, 1, 2)
        lay.addLayout(grid)
        if record:
            self.username.setText(record["username"])
            self.full_name.setText(record["full_name"] or "")
            idx = self.role.findData(record["role"])
            self.role.setCurrentIndex(idx if idx >= 0 else 0)
            self._update_hint()
        btns = QHBoxLayout()
        b_save = primary_button(_("save"))
        b_cancel = secondary_button(_("cancel"))
        b_save.clicked.connect(self.save)
        b_cancel.clicked.connect(self.reject)
        btns.addWidget(b_cancel)
        btns.addStretch()
        btns.addWidget(b_save)
        lay.addLayout(btns)

    def _update_hint(self):
        is_rec = self.role.currentData() == "reception"
        self.hint.setText(_("perm_hint_reception") if is_rec else _("perm_hint_admin"))

    def save(self):
        u = self.username.text().strip()
        p = self.password.text().strip()
        fn = self.full_name.text().strip()
        role = self.role.currentData()
        if not u:
            QMessageBox.warning(self, _("app_title"), _("error_save"))
            return
        if not self.record and not p:
            QMessageBox.warning(self, _("app_title"), _("error_save"))
            return
        # duplicate username check
        existing = db.fetch_one("SELECT id FROM users WHERE username=?", (u,))
        if existing and (not self.record or existing["id"] != self.record["id"]):
            QMessageBox.warning(self, _("app_title"), _("username_exists"))
            return
        if self.record:
            if p:
                db.execute("UPDATE users SET username=?, password=?, full_name=?, role=? WHERE id=?",
                           (u, p, fn, role, self.record["id"]))
            else:
                db.execute("UPDATE users SET username=?, full_name=?, role=? WHERE id=?",
                           (u, fn, role, self.record["id"]))
        else:
            db.execute("INSERT INTO users (username, password, full_name, role) VALUES (?,?,?,?)",
                       (u, p, fn, role))
        self.accept()
