from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PySide6.QtCore import Qt
from app.gui import style
from app.i18n import _
import app.database as db
from datetime import datetime, timedelta

class ActivationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("activation"))
        self.setFixedSize(400, 250)
        self.setStyleSheet(style.LOGIN_QSS)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(15)

        title = QLabel(_("activation_required"))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        self.serial = QLineEdit()
        self.serial.setPlaceholderText(_("enter_serial_number"))
        self.serial.setStyleSheet(style.INPUT_QSS)
        layout.addWidget(self.serial)

        btn = QPushButton(_("activate"))
        btn.setStyleSheet(style.BTN_QSS)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.do_activate)
        layout.addWidget(btn)

    def do_activate(self):
        key = self.serial.text().strip()
        if not key:
            QMessageBox.warning(self, _("app_title"), _("enter_serial"))
            return

        # Lifetime serial check
        if key == "awnyXXX@0796161401":
            db.set_setting("license_key", key)
            db.set_setting("license_type", "lifetime")
            db.set_setting("activation_date", "lifetime")
            QMessageBox.information(self, _("app_title"), _("activation_success_lifetime"))
            self.accept()
        else:
            # Monthly license
            # In a real app, you'd verify the key with a server. 
            # Here we assume any other non-empty key is a 1-month license for demo.
            db.set_setting("license_key", key)
            db.set_setting("license_type", "monthly")
            db.set_setting("activation_date", datetime.now().strftime("%Y-%m-%d"))
            QMessageBox.information(self, _("app_title"), _("activation_success_monthly"))
            self.accept()
