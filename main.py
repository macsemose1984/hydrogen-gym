import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app.database import init_database
from app.i18n import I18n
from app.gui import style
import app.backup as backup


class AppContext:
    def __init__(self):
        self.qapp = None
        self.user = None
        self.login_window = None
        self.main_window = None
        self._apply_language()

    def _apply_language(self):
        import app.database as db
        lang = db.get_setting("user_lang", "ar")
        I18n().set_language(lang)
        theme = db.get_setting("theme", "dark")
        style.set_theme(theme)
        if self.qapp is not None:
            self.qapp.setStyleSheet(style.MISC_QSS)

    def set_rtl(self):
        self.qapp.setLayoutDirection(Qt.RightToLeft if I18n().is_rtl() else Qt.LeftToRight)

    def open_login(self):
        from app.gui.login import LoginWindow
        if not self.login_window:
            self.login_window = LoginWindow(self)
        self.login_window.show()

    def open_main_window(self, sender=None):
        from app.gui.main_window import MainWindow
        if sender is not None:
            sender.hide()
        self.main_window = MainWindow(self)
        self.main_window.set_user(self.user["full_name"])
        self.main_window.showMaximized()
        self.main_window.show_page("dashboard")

    def show_login(self):
        if self.main_window:
            self.main_window.close()
            self.main_window = None
        if not self.login_window:
            from app.gui.login import LoginWindow
            self.login_window = LoginWindow(self)
        self.login_window.show()

    def restart_ui(self):
        self._apply_language()
        self.set_rtl()
        self.show_login()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    style.set_fonts(app)
    init_database()
    ctx = AppContext()
    ctx.qapp = app
    app.setStyleSheet(style.MISC_QSS)
    try:
        if not backup.backup_today_done():
            backup.backup_database()
    except Exception:
        pass
    ctx.set_rtl()
    ctx.open_login()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()