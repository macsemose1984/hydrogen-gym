from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
)
from PySide6.QtCore import QDate

import app.database as db
from app.i18n import _
from app.gui import style
from app.gui.widgets import (
    page_title, primary_button, secondary_button, make_date,
    form_field,
)


class ReportsPage(QWidget):
    def __init__(self, app_ctx, main):
        super().__init__()
        self.app_ctx = app_ctx
        self.main = main
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        layout.addWidget(page_title(_("reports")))

        self.help = QLabel(_("reports_help"))
        self.help.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px;")
        layout.addWidget(self.help)

        # Report type card
        from PySide6.QtWidgets import QFrame
        card = QFrame()
        card.setObjectName("Card")
        card.setStyleSheet(style.CARD_QSS)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 24, 24, 24)
        cl.setSpacing(16)

        self.type = QComboBox()
        self.type.addItems([
            _("attendance_report"), _("attendance_days_report"), _("financial_report"),
            _("active_members_report"), _("expired_members_report"),
            _("members_report"), _("profit_loss_report"),
            _("renewal_report"), _("coach_members_report"),
            _("coach_members_names_report"), _("plan_members_report"),
            _("payroll_report"), _("expiring_subs_report"),
            _("expenses_by_category_report"), _("coach_earnings_report"),
            _("daily_profit_report"),
        ])
        self.type.setStyleSheet(style.INPUT_QSS)
        form_field(cl, _("report_type"), self.type)

        dates = QHBoxLayout()
        dates.addWidget(QLabel(_("from_date")))
        self.date_from = make_date()
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        dates.addWidget(self.date_from)
        dates.addWidget(QLabel(_("to_date")))
        self.date_to = make_date()
        dates.addWidget(self.date_to)
        dates.addStretch()
        cl.addLayout(dates)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems([_("html"), _("excel")])
        self.format_combo.setStyleSheet(style.INPUT_QSS)
        self.format_combo.setMaximumWidth(120)
        form_field(cl, _("format"), self.format_combo)

        self.method_lbl = QLabel(_("daily"))
        self.method_lbl.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px;")
        self.method = QComboBox()
        self.method.addItem(_("all"), "all")
        self.method.addItem(_("daily"), "daily")
        self.method.setStyleSheet(style.INPUT_QSS)
        self.method.setVisible(False)
        cl.addWidget(self.method_lbl)
        cl.addWidget(self.method)

        self.plan_lbl = QLabel(_("plan"))
        self.plan_lbl.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px;")
        self.plan_combo = QComboBox()
        for p_ in db.fetch_all("SELECT id, name FROM plans WHERE is_active=1 ORDER BY name"):
            self.plan_combo.addItem(p_["name"], p_["id"])
        self.plan_combo.setStyleSheet(style.INPUT_QSS)
        self.plan_lbl.setVisible(False)
        self.plan_combo.setVisible(False)
        cl.addWidget(self.plan_lbl)
        cl.addWidget(self.plan_combo)

        # member filter for attendance_days_report
        from PySide6.QtWidgets import QLineEdit
        self.member_lbl = QLabel(_("member"))
        self.member_lbl.setStyleSheet(f"color:{style.MUTED.name()}; font-size:13px;")
        self.member_search = QLineEdit()
        self.member_search.setPlaceholderText(f"🔍 {_('search')}...")
        self.member_search.setStyleSheet(style.INPUT_QSS)
        self.member_search.textChanged.connect(self._filter_members)
        self.member_combo = QComboBox()
        self.member_combo.setStyleSheet(style.INPUT_QSS)
        self._all_members = db.fetch_all("SELECT id, full_name, phone FROM members ORDER BY full_name")
        self._fill_members(self._all_members)
        self.member_lbl.setVisible(False)
        self.member_search.setVisible(False)
        self.member_combo.setVisible(False)
        cl.addWidget(self.member_lbl)
        cl.addWidget(self.member_search)
        cl.addWidget(self.member_combo)

        self.type.currentIndexChanged.connect(self._toggle)

        b_row = QHBoxLayout()
        b_export = primary_button(f"📄 {_('export_pdf')}")
        b_export.clicked.connect(self.export)
        b_row.addWidget(b_export)
        b_row.addStretch()
        cl.addLayout(b_row)

        layout.addWidget(card)
        layout.addStretch()

    def _fill_members(self, members):
        self.member_combo.blockSignals(True)
        self.member_combo.clear()
        self.member_combo.addItem(f"— {_('all')} —", None)
        for m in members:
            self.member_combo.addItem(f"{m['full_name']} ({m['phone'] or '-'})", m["id"])
        self.member_combo.blockSignals(False)

    def _filter_members(self, *_args):
        term = self.member_search.text().strip().lower()
        if not term:
            self._fill_members(self._all_members)
            return
        filtered = [m for m in self._all_members if term in f"{m['full_name']} {m['phone'] or ''}".lower()]
        self._fill_members(filtered)

    def _toggle(self, *_args):
        is_fin = self.type.currentIndex() == 2
        self.method.setVisible(is_fin)
        self.method_lbl.setVisible(is_fin)
        if not is_fin:
            self.method.setCurrentIndex(0)
        is_plan = self.type.currentIndex() == 10
        self.plan_lbl.setVisible(is_plan)
        self.plan_combo.setVisible(is_plan)
        is_days = self.type.currentIndex() == 1
        self.member_lbl.setVisible(is_days)
        self.member_search.setVisible(is_days)
        self.member_combo.setVisible(is_days)
        if is_days:
            # refresh members list when shown
            self._all_members = db.fetch_all("SELECT id, full_name, phone FROM members ORDER BY full_name")
            self._filter_members()

    def export(self):
        import app.reports as reports
        t = self.type.currentIndex()
        frm = self.date_from.date().toString("yyyy-MM-dd")
        to = self.date_to.date().toString("yyyy-MM-dd")
        if t == 0:
            reports.attendance_report(frm, to)
        elif t == 1:
            reports.attendance_days_report(frm, to, self.member_combo.currentData())
        elif t == 2:
            reports.financial_report(frm, to, self.method.currentData())
        elif t == 3:
            reports.active_members_report()
        elif t == 4:
            reports.expired_members_report()
        elif t == 5:
            reports.members_report()
        elif t == 6:
            reports.profit_loss_report(frm, to)
        elif t == 7:
            reports.renewal_report(frm, to)
        elif t == 8:
            reports.coach_members_report()
        elif t == 9:
            reports.coach_members_names_report()
        elif t == 10:
            reports.plan_members_report(self.plan_combo.currentData())
        elif t == 11:
            reports.salary_report(frm, to)
        elif t == 12:
            reports.expiring_subs_report()
        elif t == 13:
            reports.expenses_by_category_report(frm, to)
        elif t == 14:
            reports.coach_earnings_report()
        elif t == 15:
            reports.daily_profit_report(frm, to)
