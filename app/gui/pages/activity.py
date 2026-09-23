from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

import app.database as db
from app.i18n import _
from app.gui import style
from app.gui.widgets import page_title, secondary_button, make_table, fill_table


class ActivityPage(QWidget):
    """Recent check-in activity, moved from the dashboard card."""

    def __init__(self, app_ctx, main):
        super().__init__()
        self.app_ctx = app_ctx
        self.main = main
        self._build()

    # ------------------------------------------------------------------ build

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        head = QHBoxLayout()
        head.addWidget(page_title(_("activity")))
        head.addStretch()
        b_refresh = secondary_button(f"\U0001F504 {_('refresh')}")
        b_refresh.clicked.connect(self.refresh)
        head.addWidget(b_refresh)
        layout.addLayout(head)

        self.table = make_table([_("member"), _("date"), _("check_in"), _("end_date")], stretch_col=0)
        self.table.setMinimumHeight(400)
        layout.addWidget(self.table, 1)

    # ------------------------------------------------------------------ data

    def refresh(self, *_args):
        rows = db.fetch_all(
            """SELECT m.full_name, date(a.check_in) AS d, substr(a.check_in,12,5) AS t,
                      (SELECT s.end_date FROM subscriptions s
                        WHERE s.member_id = a.member_id AND s.status = 'active'
                        ORDER BY s.end_date DESC LIMIT 1) AS end_date
               FROM attendance a JOIN members m ON a.member_id=m.id
               ORDER BY a.check_in DESC LIMIT 100"""
        )
        fill_table(self.table,
                   [(r["full_name"], r["d"], r["t"], r["end_date"] or "-") for r in rows])

    def cleanup(self):
        pass
