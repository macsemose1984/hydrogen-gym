from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFrame,
)
from PySide6.QtCore import Qt

import app.database as db
from app.i18n import _
from app.gui import style
from app.gui.widgets import logo_label


class LoginWindow(QWidget):
    def __init__(self, app_ctx):
        super().__init__()
        self.app_ctx = app_ctx
        self.setWindowTitle(_("login"))
        self.resize(420, 560)
        self.setStyleSheet(style.LOGIN_QSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 30, 40, 30)
        root.setSpacing(10)
        root.addStretch()

        self.logo = logo_label(110)
        root.addWidget(self.logo)

        title = QLabel(_("app_title"))
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("LoginTitle")
        title.setStyleSheet(style.LOGIN_QSS)
        root.addWidget(title)

        sub = QLabel(_("app_subtitle"))
        sub.setAlignment(Qt.AlignCenter)
        sub.setObjectName("LoginSub")
        sub.setStyleSheet(style.LOGIN_QSS)
        root.addWidget(sub)

        root.addSpacing(30)

        card = QFrame()
        card.setObjectName("LoginCard")
        card.setStyleSheet(style.LOGIN_QSS)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(26, 26, 26, 26)
        lay.setSpacing(14)

        u_lbl = QLabel(_("username"))
        u_lbl.setStyleSheet("color:#cbd5e1; font-size:13px; font-weight:600;")
        lay.addWidget(u_lbl)
        self.username = QLineEdit()
        self.username.setStyleSheet(style.INPUT_QSS)
        lay.addWidget(self.username)

        p_lbl = QLabel(_("password"))
        p_lbl.setStyleSheet("color:#cbd5e1; font-size:13px; font-weight:600;")
        lay.addWidget(p_lbl)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setStyleSheet(style.INPUT_QSS)
        self.password.returnPressed.connect(self.do_login)
        lay.addWidget(self.password)

        self.btn = QPushButton(_("login_btn"))
        self.btn.setObjectName("Primary")
        self.btn.setStyleSheet(style.BTN_QSS)
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.clicked.connect(self.do_login)
        lay.addWidget(self.btn)

        self.err = QLabel("")
        self.err.setAlignment(Qt.AlignCenter)
        self.err.setObjectName("LoginErr")
        self.err.setStyleSheet(style.LOGIN_QSS)
        lay.addWidget(self.err)

        root.addWidget(card)
        root.addStretch()

        footer = QLabel("تصميم عوني جرادات 0796161401")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color:#64748b; font-size:12px; padding-bottom:4px;")
        root.addWidget(footer)

    def do_login(self):
        u = self.username.text().strip()
        p = self.password.text().strip()
        row = db.fetch_one(
            "SELECT * FROM users WHERE username=? AND password=?", (u, p)
        )
        if row:
            self.app_ctx.user = row
            try:
                db.set_current_user(row["username"])
            except Exception:
                pass
            db.set_setting("user_lang", row["language"] or "en")
            self.app_ctx.open_main_window(self)
        else:
            self.err.setText(_("login_error"))