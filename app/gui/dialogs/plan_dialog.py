from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QSpinBox, QDoubleSpinBox, QTextEdit, QPushButton, QMessageBox,
)
from PySide6.QtCore import Qt

import app.database as db
from app.i18n import _
from app.gui import style
from app.gui.widgets import primary_button, secondary_button, form_field, window_controls


class PlanDialog(QDialog):
    def __init__(self, record, parent=None):
        super().__init__(parent)
        window_controls(self)
        self.record = record
        self.setWindowTitle(_("plans"))
        self.resize(460, 480)
        self.setStyleSheet(f"background:{style.CARD.name()}; font-family:{style.FONT_FAMILY};")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        grid = QGridLayout()
        grid.setSpacing(12)
        r = 0

        self.name = QLineEdit(record["name"] if record else "")
        self.name.setStyleSheet(style.INPUT_QSS)
        form_field(grid, _("plan_name") + " *", self.name)
        r += 1

        self.duration = QSpinBox()
        self.duration.setRange(1, 3660)
        self.duration.setValue(record["duration_days"] if record else 30)
        self.duration.setStyleSheet(style.INPUT_QSS)
        form_field(grid, _("duration") + " *", self.duration)
        r += 1

        self.price = QDoubleSpinBox()
        self.price.setRange(0, 1000000)
        self.price.setDecimals(2)
        self.price.setValue(record["price"] if record else 0)
        self.price.setStyleSheet(style.INPUT_QSS)
        form_field(grid, _("price") + " *", self.price)
        r += 1

        self.sessions = QSpinBox()
        self.sessions.setRange(0, 10000)
        self.sessions.setValue(record["sessions"] if record else 0)
        self.sessions.setStyleSheet(style.INPUT_QSS)
        form_field(grid, _("sessions"), self.sessions)
        r += 1

        lay.addLayout(grid)

        d_lbl = QLabel(_("description"))
        d_lbl.setStyleSheet("color:%s;font-size:13px;font-weight:600;" % style.MUTED.name())
        lay.addWidget(d_lbl)
        self.desc = QTextEdit(record["description"] if record else "")
        self.desc.setFixedHeight(70)
        self.desc.setStyleSheet(style.INPUT_QSS)
        lay.addWidget(self.desc)

        btns = QHBoxLayout()
        b_save = primary_button(_("save"))
        b_cancel = secondary_button(_("cancel"))
        b_save.clicked.connect(self.save)
        b_cancel.clicked.connect(self.reject)
        btns.addWidget(b_cancel)
        btns.addStretch()
        btns.addWidget(b_save)
        lay.addLayout(btns)

    def save(self):
        if not self.name.text().strip() or self.duration.value() <= 0:
            QMessageBox.warning(self, _("app_title"), _("error_save"))
            return
        if self.record:
            db.execute(
                "UPDATE plans SET name=?, duration_days=?, price=?, sessions=?, description=? WHERE id=?",
                (self.name.text().strip(), self.duration.value(), self.price.value(),
                 self.sessions.value(), self.desc.toPlainText(), self.record["id"]),
            )
        else:
            db.execute(
                "INSERT INTO plans (name, duration_days, price, sessions, description) VALUES (?,?,?,?,?)",
                (self.name.text().strip(), self.duration.value(), self.price.value(),
                 self.sessions.value(), self.desc.toPlainText()),
            )
        self.accept()