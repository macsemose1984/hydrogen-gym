from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QPushButton, QLabel, QFrame, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QKeySequence, QShortcut

from app.i18n import _
from app.gui import style
from app.gui.pages.dashboard import DashboardPage
from app.gui.pages.members import MembersPage
from app.gui.pages.plans import PlansPage
from app.gui.pages.subscriptions import SubscriptionsPage
from app.gui.pages.payments import PaymentsPage
from app.gui.pages.attendance import AttendancePage
from app.gui.pages.coaches import CoachesPage
from app.gui.pages.employees import EmployeesPage
from app.gui.pages.reports import ReportsPage
from app.gui.pages.whatsapp import WhatsAppPage
from app.gui.pages.settings import SettingsPage
from app.gui.pages.expenses import ExpensesPage
from app.gui.pages.daily_statement import DailyStatementPage
from app.gui.pages.trash import TrashPage
from app.gui.pages.charts import ChartsPage
from app.gui.pages.activity import ActivityPage


class MainWindow(QMainWindow):
    def __init__(self, app_ctx):
        super().__init__()
        self.app_ctx = app_ctx
        self.setWindowTitle(_("app_title"))
        self.resize(1100, 700)
        self.setMinimumSize(900, 620)

        self.pages = {}
        self.nav_buttons = []
        self._build()

        # Keyboard shortcuts: F2 quick check-in, F3 quick payment
        self.sc_checkin = QShortcut(QKeySequence("F2"), self)
        self.sc_checkin.activated.connect(self._shortcut_checkin)
        self.sc_payment = QShortcut(QKeySequence("F3"), self)
        self.sc_payment.activated.connect(self._shortcut_payment)

        # ADMS push receiver (fingerprint device pushes attendance/photos)
        self._adms = None
        self._start_adms()

        # Auto-refresh dashboard every 60 seconds
        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(60000)
        self._auto_timer.timeout.connect(self._auto_refresh)
        self._auto_timer.start()

    def _build(self):
        central = QWidget()
        central.setStyleSheet(f"background:{style.BG.name()};")
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_sidebar())
        layout.addWidget(self._build_content(), 1)
        # طبّق الصلاحيات بعد بناء الـ sidebar والـ topbar معاً
        self._apply_permissions()

    def _build_sidebar(self):
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(248)
        side.setStyleSheet(style.SIDEBAR_QSS)

        lay = QVBoxLayout(side)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(18, 18, 18, 0)
        from app.gui.widgets import logo_label
        logo = logo_label(40)
        brand_row.addWidget(logo)
        brand = QLabel(_("app_title"))
        brand.setObjectName("Brand")
        brand.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        brand_row.addWidget(brand)
        brand_row.addStretch()
        lay.addLayout(brand_row)

        sub = QLabel(_("app_subtitle"))
        sub.setObjectName("BrandSub")
        sub.setStyleSheet(style.SIDEBAR_QSS)
        lay.addWidget(sub)

        needs = [
            ("dashboard", "📊", DashboardPage),
            ("members", "👥", MembersPage),
            ("subscriptions", "🔁", SubscriptionsPage),
            ("activity", "📜", ActivityPage),
            ("payments", "💳", PaymentsPage),
            ("attendance", "🕐", AttendancePage),
            ("employees", "👔", EmployeesPage),
            ("reports", "📈", ReportsPage),
            ("whatsapp", "💬", WhatsAppPage),
            ("expenses", "💸", ExpensesPage),
            ("daily_statement", "🧾", DailyStatementPage),
            ("charts", "📊", ChartsPage),
            ("trash", "🗑️", TrashPage),
        ]
        for key, icon, page_cls in needs:
            from app.gui import widgets
            btn = widgets.nav_button(f"{icon}  {_(key)}")
            btn.clicked.connect(lambda checked=False, k=key: self.show_page(k))
            lay.addWidget(btn)
            self.nav_buttons.append((key, btn))
            self.pages[key] = page_cls(self.app_ctx, self)

        self.pages["plans"] = PlansPage(self.app_ctx, self)
        self.pages["coaches"] = CoachesPage(self.app_ctx, self)
        self.pages["settings"] = SettingsPage(self.app_ctx, self)

        self._apply_permissions()

        return side

    def _build_content(self):
        wrapper = QFrame()
        wrapper.setStyleSheet(f"background:{style.BG.name()};")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(14)

        topbar = QHBoxLayout()
        self.user_label = QLabel("")
        self.user_label.setStyleSheet(
            f"color:{style.TEXT.name()}; font-size:14px; font-weight:bold;"
        )
        topbar.addWidget(self.user_label)
        topbar.addStretch()
        self.live_label = QLabel("")
        self.live_label.setStyleSheet(f"color:{style.MUTED.name()}; font-size:12px;")
        topbar.addWidget(self.live_label)
        self._build_theme_toggle(topbar)
        # زر الخروج في أقصى اليسار (نهاية الـ topbar في RTL)
        self.logout_btn = QPushButton("\U0001F6AA")
        self.logout_btn.setToolTip(_("logout"))
        self.logout_btn.setFixedWidth(42)
        self.logout_btn.setStyleSheet(
            f"background:{style.FIELD.name()}; border:1px solid {style.BORDER.name()}; "
            f"border-radius:8px; font-size:16px; color:{style.TEXT.name()};"
        )
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        self.logout_btn.clicked.connect(self._logout)
        topbar.addWidget(self.logout_btn)
        layout.addLayout(topbar)

        self.stack = QStackedWidget()
        for key, page in self.pages.items():
            self.stack.addWidget(page)
        layout.addWidget(self.stack, 1)

        footer = QLabel("تصميم عوني جرادات | 0796161401 | iorijaradat@gmail.com")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(f"color:{style.MUTED.name()}; font-size:11px; padding-top:6px;")
        layout.addWidget(footer)
        return wrapper

    def _build_theme_toggle(self, topbar):
        self.theme_btn = QPushButton("🌓")
        self.theme_btn.setToolTip(_("theme_toggle"))
        self.theme_btn.setFixedWidth(42)
        self.theme_btn.setStyleSheet(
            f"background:{style.FIELD.name()}; border:1px solid {style.BORDER.name()}; "
            f"border-radius:8px; font-size:16px; color:{style.TEXT.name()};"
        )
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setToolTip(_("settings"))
        self.settings_btn.setFixedWidth(42)
        self.settings_btn.setStyleSheet(
            f"background:{style.FIELD.name()}; border:1px solid {style.BORDER.name()}; "
            f"border-radius:8px; font-size:16px; color:{style.TEXT.name()};"
        )
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.clicked.connect(lambda: self.show_page("settings"))
        topbar.addWidget(self.settings_btn)
        self.coaches_btn = QPushButton("🏋️‍♂️")
        self.coaches_btn.setToolTip(_("coaches"))
        self.coaches_btn.setFixedWidth(42)
        self.coaches_btn.setStyleSheet(
            f"background:{style.FIELD.name()}; border:1px solid {style.BORDER.name()}; "
            f"border-radius:8px; font-size:16px; color:{style.TEXT.name()};"
        )
        self.coaches_btn.setCursor(Qt.PointingHandCursor)
        self.coaches_btn.clicked.connect(lambda: self.show_page("coaches"))
        topbar.addWidget(self.coaches_btn)
        self.plans_btn = QPushButton("📋")
        self.plans_btn.setToolTip(_("plans"))
        self.plans_btn.setFixedWidth(42)
        self.plans_btn.setStyleSheet(
            f"background:{style.FIELD.name()}; border:1px solid {style.BORDER.name()}; "
            f"border-radius:8px; font-size:16px; color:{style.TEXT.name()};"
        )
        self.plans_btn.setCursor(Qt.PointingHandCursor)
        self.plans_btn.clicked.connect(lambda: self.show_page("plans"))
        topbar.addWidget(self.plans_btn)
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)
        topbar.addWidget(self.theme_btn)

    def _toggle_theme(self):
        mode = style.toggle_theme()
        self.theme_btn.setText("☀️" if mode == "dark" else "🌙")
        db = __import__("app.database", fromlist=["set_setting"])
        db.set_setting("theme", mode)
        self.setStyleSheet("")

    def _apply_permissions(self):
        role = (self.app_ctx.user or {}).get("role", "admin") if isinstance(self.app_ctx.user, dict) else getattr(self.app_ctx.user, "get", lambda k,d=None: "admin")("role", "admin")
        # reception: لا يرى الإعدادات، السلة، الخطط، المدربين، المصاريف، كشف الحساب اليومي
        if role == "reception":
            restricted = {"settings", "trash", "plans", "coaches", "expenses", "daily_statement"}
            for k, btn in self.nav_buttons:
                if k in restricted:
                    btn.setVisible(False)
            # topbar buttons
            if hasattr(self, "settings_btn"):
                self.settings_btn.setVisible(False)
            if hasattr(self, "coaches_btn"):
                self.coaches_btn.setVisible(False)
            if hasattr(self, "plans_btn"):
                self.plans_btn.setVisible(False)

    def show_page(self, key, tab=None):
        role = (self.app_ctx.user or {}).get("role", "admin") if isinstance(self.app_ctx.user, dict) else getattr(self.app_ctx.user, "get", lambda k,d=None: "admin")("role", "admin")
        restricted = {"settings", "trash", "plans", "coaches", "expenses", "daily_statement"} if role == "reception" else set()
        if key in restricted:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, _("app_title"), _("no_permission"))
            return
        self.stack.setCurrentWidget(self.pages[key])
        for k, btn in self.nav_buttons:
            btn.setChecked(k == key)
        page = self.pages[key]
        if hasattr(page, "refresh"):
            page.refresh()
        if tab is not None and hasattr(page, "goto_tab"):
            page.goto_tab(tab)

    def _shortcut_checkin(self):
        self.show_page("attendance")
        page = self.pages["attendance"]
        if hasattr(page, "check_in"):
            page.check_in()

    def _shortcut_payment(self):
        from app.gui.dialogs.subscription_dialog import QuickPaymentDialog
        dlg = QuickPaymentDialog(self.app_ctx, self)
        if dlg.exec():
            page = self.pages.get("payments")
            if page is not None and hasattr(page, "refresh"):
                page.refresh()

    def set_user(self, full_name):
        self.user_label.setText(f"{_('welcome')} 👋 {full_name}")

    def set_live_info(self, text):
        self.live_label.setText(text)

    def _logout(self):
        self.app_ctx.show_login()
        self.close()

    def _start_adms(self):
        import app.database as db
        if db.get_setting("adms_enabled", "0") != "1":
            return
        try:
            port = int(db.get_setting("adms_port", "8090") or 8090)
        except ValueError:
            port = 8090
        try:
            from app.adms import AdmsServer, signals as adms_signals
            from PySide6.QtCore import Qt
            self._adms = AdmsServer(port)
            self._adms.start()
            adms_signals.expired_checkin.connect(
                self._adms_expired_checkin, Qt.QueuedConnection
            )
        except Exception:
            self._adms = None

    def adms_restart(self):
        if self._adms:
            try:
                self._adms.stop()
            except Exception:
                pass
            self._adms = None
        self._start_adms()

    def _adms_expired_checkin(self, names):
        from app.gui.pages.attendance import _alert_beep
        from PySide6.QtWidgets import QMessageBox
        _alert_beep()
        QMessageBox.warning(
            self, _("app_title"),
            _("expired_checkin_alert").format(names=", ".join(names[:10])),
        )

    def _auto_refresh(self):
        """Refresh the currently visible page if it supports refresh()."""
        current = self.stack.currentWidget()
        if hasattr(current, "refresh"):
            current.refresh()

    def closeEvent(self, event):
        """Stop background threads before closing to avoid QThread-destroyed warnings."""
        self._auto_timer.stop()
        try:
            if self._adms:
                self._adms.stop()
        except Exception:
            pass
        for page in self.pages.values():
            if hasattr(page, "cleanup"):
                page.cleanup()
        try:
            from app import backup
            # Always take a safety backup on close to ensure no data loss
            backup.backup_database()
            backup.cleanup_backups(30)
        except Exception as e:
            print(f"Auto-backup failed: {e}")

        event.accept()
