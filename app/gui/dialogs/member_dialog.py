from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QComboBox, QDateEdit, QTextEdit, QPushButton, QMessageBox, QFileDialog, QFrame,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QPixmap

import app.database as db
from app.i18n import _
from app.gui import style
from app.gui.widgets import primary_button, secondary_button, form_field, window_controls


class MemberDialog(QDialog):
    def __init__(self, record, app_ctx, parent=None):
        super().__init__(parent)
        window_controls(self)
        self.app_ctx = app_ctx
        self.record = record

        is_new = record is None
        self.setWindowTitle(_("add_member") if is_new else _("edit_member"))
        self.resize(560, 560)

        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(24, 24, 24, 24)
        self.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")

        grid = QGridLayout()
        grid.setSpacing(14)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnMinimumWidth(0, 160)
        r = 0

        def _field(label, widget):
            nonlocal r
            lbl = QLabel(label)
            lbl.setStyleSheet("color:%s;font-size:13px;font-weight:600;" % style.MUTED.name())
            grid.addWidget(lbl, r, 0)
            grid.addWidget(widget, r, 1)
            r += 1

        self.name = QLineEdit(record["full_name"] if record else "")
        self.name.setStyleSheet(style.INPUT_QSS)
        self.name.setMinimumHeight(40)
        _field(_("full_name") + " *", self.name)

        self.phone = QLineEdit(record["phone"] if record else "")
        self.phone.setStyleSheet(style.INPUT_QSS)
        self.phone.setMinimumHeight(40)
        _field(_("phone") + " *", self.phone)

        self.gender = QComboBox()
        self.gender.addItems([_("male"), _("female")])
        if record and record["gender"] == "أنثى":
            self.gender.setCurrentIndex(1)
        self.gender.setStyleSheet(style.INPUT_QSS)
        self.gender.setMinimumHeight(40)
        _field(_("gender"), self.gender)

        self.coach = QComboBox()
        self.coach.addItem(f"— {_('no_coach')} —", None)
        for c in db.fetch_all("SELECT id, full_name FROM coaches WHERE is_active=1 ORDER BY full_name"):
            self.coach.addItem(c["full_name"], c["id"])
        if record and record.get("coach_id"):
            cidx = self.coach.findData(record["coach_id"])
            if cidx < 0:
                extra = db.fetch_one("SELECT id, full_name FROM coaches WHERE id=?", (record["coach_id"],))
                if extra:
                    self.coach.addItem(extra["full_name"], extra["id"])
                    cidx = self.coach.count() - 1
            self.coach.setCurrentIndex(cidx if cidx >= 0 else 0)
        self.coach.setStyleSheet(style.INPUT_QSS)
        self.coach.setMinimumHeight(40)
        _field(_("coach"), self.coach)

        photo_row = QHBoxLayout()
        photo_row.setSpacing(8)
        self.photo_preview = QLabel()
        self.photo_preview.setFixedSize(64, 64)
        self.photo_preview.setAlignment(Qt.AlignCenter)
        self.photo_preview.setStyleSheet(
            f"background:{style.FIELD.name()}; border:1px solid {style.BORDER.name()};"
            f"border-radius:6px; font-size:24px;"
        )
        photo_row.addWidget(self.photo_preview)
        self.photo_path = (record or {}).get("photo_path") or ""
        if self.photo_path and __import__("os").path.exists(self.photo_path):
            _pix = QPixmap(self.photo_path)
            if not _pix.isNull():
                self.photo_preview.setPixmap(_pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.photo_preview.setText("\U0001F464")
        else:
            self.photo_preview.setText("\U0001F464")
        b_photo = secondary_button(f"\U0001F4F7 {_('choose_photo')}")
        b_photo.clicked.connect(self._pick_photo)
        photo_row.addWidget(b_photo)
        b_dev_photo = secondary_button(f"\U0001F4F8 {_('pull_device_photo')}")
        b_dev_photo.clicked.connect(self._pull_device_photo)
        photo_row.addWidget(b_dev_photo)
        photo_row.addStretch()
        _frame = QFrame()
        _frame.setLayout(photo_row)
        _field(_("photo"), _frame)

        self.birth = QDateEdit()
        self.birth.setCalendarPopup(True)
        self.birth.setDisplayFormat("yyyy-MM-dd")
        self.birth.setDate(QDate.currentDate().addYears(-20))
        self.birth.setStyleSheet(style.INPUT_QSS)
        self.birth.setMinimumHeight(40)
        _field(_("birth_date"), self.birth)

        self.code = QLineEdit()
        if record:
            self.code.setText(record["code"])
        else:
            self.code.setText(_auto_code())
        self.code.setStyleSheet(style.INPUT_QSS)
        self.code.setMinimumHeight(40)
        self.code.setEnabled(False)
        _field(_("member_code"), self.code)

        self.fp = QLineEdit(record["fingerprint_id"] if record and record["fingerprint_id"] else "")
        self.fp.setStyleSheet(style.INPUT_QSS)
        self.fp.setMinimumHeight(40)
        _field(_("fingerprint_id"), self.fp)

        self.join = QDateEdit()
        self.join.setCalendarPopup(True)
        self.join.setDisplayFormat("yyyy-MM-dd")
        self.join.setDate(QDate.currentDate())
        if record and record["join_date"]:
            self.join.setDate(QDate.fromString(record["join_date"], "yyyy-MM-dd"))
        self.join.setStyleSheet(style.INPUT_QSS)
        self.join.setMinimumHeight(40)
        _field(_("join_date"), self.join)

        lay.addLayout(grid)

        n_lbl = QLabel(_("notes"))
        n_lbl.setStyleSheet("color:%s;font-size:13px;font-weight:600;" % style.MUTED.name())
        lay.addWidget(n_lbl)
        self.notes = QTextEdit(record["notes"] if record else "")
        self.notes.setFixedHeight(70)
        self.notes.setStyleSheet(style.INPUT_QSS)
        lay.addWidget(self.notes)

        btns = QHBoxLayout()
        b_save = primary_button(_("save"))
        b_cancel = secondary_button(_("cancel"))
        b_save.clicked.connect(self.save)
        b_cancel.clicked.connect(self.reject)
        btns.addWidget(b_cancel)
        btns.addStretch()
        btns.addWidget(b_save)
        lay.addLayout(btns)

    def _pick_photo(self):
        path, _f = QFileDialog.getOpenFileName(
            self, _("choose_photo"), "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not path:
            return
        self.photo_path = path
        _pix = QPixmap(path)
        if not _pix.isNull():
            self.photo_preview.setPixmap(_pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.photo_preview.setText("\U0001F464")

    def _pull_device_photo(self):
        fp = self.fp.text().strip()
        if not fp:
            QMessageBox.information(self, _("app_title"), _("fp_first"))
            return
        from app import zk
        result = zk.get_user_photo(
            db.get_setting("device_ip", "192.168.1.201"),
            db.get_setting("device_port", "4370"),
            fp,
        )
        if result.get("error"):
            err = str(result["error"])
            if "no data" in err.lower():
                QMessageBox.information(self, _("app_title"), _("no_device_photo"))
            elif err == "user_not_found":
                QMessageBox.warning(self, _("app_title"), _("user_not_found"))
            elif err == "photo_unsupported":
                QMessageBox.warning(self, _("app_title"), _("photo_unsupported"))
            elif err == "photo_unsupported_speedface":
                # SpeedFace-V5L: اعرض معلومة بدل تحذير أصفر وافتح اختيار الصورة مباشرة
                QMessageBox.information(self, _("app_title"), _("photo_unsupported_speedface"))
                self._pick_photo()
            else:
                QMessageBox.warning(self, _("app_title"), f"{_('device_fail')}: {err}")
            return
        photo = result.get("photo")
        if not photo:
            QMessageBox.information(self, _("app_title"), _("no_device_photo"))
            return
        import os
        photo_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "photos",
        )
        os.makedirs(photo_dir, exist_ok=True)
        path = os.path.join(photo_dir, f"member_{fp or 'unknown'}.png")
        try:
            with open(path, "wb") as fh:
                fh.write(photo)
        except OSError as exc:
            QMessageBox.warning(self, _("app_title"), f"{_('device_fail')}: {exc}")
            return
        self.photo_path = path
        _pix = QPixmap()
        if _pix.loadFromData(photo):
            self.photo_preview.setPixmap(_pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.photo_preview.setText("\U0001F464")

    def save(self):
        name = self.name.text().strip()
        phone = self.phone.text().strip()
        if not name or not phone:
            QMessageBox.warning(self, _("app_title"), _("error_save"))
            return
        vals = {
            "full_name": name,
            "phone": phone,
            "gender": self.gender.currentText(),
            "birth_date": self.birth.date().toString("yyyy-MM-dd"),
            "fingerprint_id": self.fp.text().strip() or None,
            "notes": self.notes.toPlainText(),
            "join_date": self.join.date().toString("yyyy-MM-dd"),
            "coach_id": self.coach.currentData(),
            "photo_path": self.photo_path or None,
        }
        if self.record:
            db.execute(
                """UPDATE members SET full_name=?, phone=?, gender=?, birth_date=?,
                   fingerprint_id=?, notes=?, join_date=?, coach_id=?, photo_path=? WHERE id=?""",
                (vals["full_name"], vals["phone"], vals["gender"], vals["birth_date"],
                 vals["fingerprint_id"], vals["notes"], vals["join_date"],
                 vals["coach_id"], vals["photo_path"], self.record["id"]),
            )
            db.log_user_action("تعديل عضو", "عضو", vals["full_name"], f"هاتف: {phone}")
        else:
            db.execute(
                """INSERT INTO members (code, full_name, phone, gender,
                   birth_date, fingerprint_id, notes, join_date, coach_id, photo_path)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (self.code.text(), vals["full_name"], vals["phone"], vals["gender"],
                 vals["birth_date"], vals["fingerprint_id"], vals["notes"],
                 vals["join_date"], vals["coach_id"], vals["photo_path"]),
            )
            db.log_user_action("إضافة عضو", "عضو", vals["full_name"], f"كود: {self.code.text()} | هاتف: {phone}")
        self.accept()


def _auto_code():
    row = db.fetch_one(
        "SELECT MAX(CAST(substr(code, 4) AS INTEGER)) AS m FROM members WHERE code LIKE 'HG-%'"
    )
    n = row["m"] if row and row["m"] else 0
    return f"HG-{n + 1:04d}"