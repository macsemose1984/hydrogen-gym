from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QFrame,
    QMessageBox, QSizePolicy, QScrollArea, QFileDialog,
)
from PySide6.QtCore import Qt
import os
from PySide6.QtGui import QColor
from datetime import datetime as _dt

import app.database as db
from app.i18n import _
from app.gui import style
from app.gui.widgets import page_title, secondary_button, primary_button


class ChartsPage(QWidget):
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

        self._chart_views = {}

        head = QHBoxLayout()
        head.addWidget(page_title(_("charts")))
        head.addStretch()

        self.period = QComboBox()
        self.period.addItems([_("period_6"), _("period_12")])
        self.period.setStyleSheet(style.INPUT_QSS)
        self.period.setMinimumHeight(36)
        self.period.currentIndexChanged.connect(self.refresh)
        head.addWidget(self.period)

        b_refresh = secondary_button(f"🔄 {_('refresh')}")
        b_refresh.clicked.connect(self.refresh)
        head.addWidget(b_refresh)

        b_export = secondary_button(f"📷 {_('export_pdf')}")
        b_export.clicked.connect(self._export_chart_image)
        head.addWidget(b_export)
        layout.addLayout(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        layout.addWidget(scroll)

        content = QFrame()
        content.setStyleSheet(f"background:{style.BG.name()};")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(16)

        top = QHBoxLayout()
        top.setSpacing(16)
        self._rev_frame = self._chart_box(_("revenue_by_month"))
        self._mem_frame = self._chart_box(_("new_members_chart"))
        top.addWidget(self._rev_frame, 1)
        top.addWidget(self._mem_frame, 1)
        cl.addLayout(top)

        bottom = QHBoxLayout()
        bottom.setSpacing(16)
        self._pay_frame = self._chart_box(_("payment_method_chart"))
        self._plan_frame = self._chart_box(_("plan_chart"))
        bottom.addWidget(self._pay_frame, 1)
        bottom.addWidget(self._plan_frame, 1)
        cl.addLayout(bottom)

        self._hint = QLabel("")
        self._hint.setStyleSheet(f"color:{style.MUTED.name()}; font-size:12px;")
        cl.addWidget(self._hint)

        scroll.setWidget(content)

    # ------------------------------------------------------------------ helpers

    def _chart_box(self, title):
        box = QFrame()
        box.setObjectName("ChartBox")
        box.setStyleSheet(style.CARD_QSS)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(16, 14, 16, 16)
        lay.setSpacing(8)
        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color:{style.TEXT.name()}; font-size:15px; font-weight:bold;"
        )
        lay.addWidget(lbl)
        holder = QFrame()
        holder.setMinimumHeight(280)
        lay.addWidget(holder)
        return box

    @staticmethod
    def _months(n):
        today = _dt.now()
        labels, keys = [], []
        for i in range(n - 1, -1, -1):
            m = today.month - i
            y = today.year
            while m <= 0:
                m += 12
                y -= 1
            while m > 12:
                m -= 12
                y += 1
            key = f"{y}-{m:02d}"
            labels.append(key[5:])
            keys.append(key)
        return keys, labels

    def _swap(self, frame, view):
        lay = frame.layout()
        holder = lay.itemAt(1).widget()
        if holder.layout() is None:
            from PySide6.QtWidgets import QVBoxLayout as _VBox
            _VBox(holder).setContentsMargins(0, 0, 0, 0)
        hl = holder.layout()
        while hl.count():
            item = hl.takeAt(0)
            w = item.widget() if item else None
            if w:
                w.setParent(None)
        hl.addWidget(view)
        self._chart_views[frame] = view

    def _export_chart_image(self):
        """Capture all visible charts into a single PNG."""
        from PySide6.QtGui import QPixmap, QPainter
        views = list(self._chart_views.values())
        if not views:
            QMessageBox.information(self, _("app_title"), _("no_data"))
            return
        pixmaps = []
        for v in views:
            pix = v.grab()
            pixmaps.append(pix)
        total_h = sum(p.height() for p in pixmaps) + 40
        max_w = max(p.width() for p in pixmaps) + 40
        result = QPixmap(max_w, total_h)
        result.fill(Qt.GlobalColor.white)
        p = QPainter(result)
        y = 20
        for pix in pixmaps:
            p.drawPixmap(20, y, pix)
            y += pix.height() + 20
        p.end()
        from datetime import datetime as _dt
        stamp = _dt.now().strftime("%Y%m%d_%H%M%S")
        folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "exports")
        os.makedirs(folder, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(
            self, _("export_pdf"),
            os.path.join(folder, f"charts_{stamp}.png"),
            "صورة PNG (*.png);;All Files (*)",
        )
        if path:
            if result.save(path, "PNG"):
                QMessageBox.information(self, _("app_title"), _("export_done"))
            else:
                QMessageBox.warning(self, _("app_title"), _("error_save"))

    def _bar_chart(self, title, categories, values, color):
        try:
            from PySide6.QtCharts import (
                QChart, QChartView, QBarSeries, QBarSet,
                QBarCategoryAxis, QValueAxis,
            )
            chart = QChart()
            chart.setTitle(title)
            chart.setAnimationOptions(QChart.SeriesAnimations)
            chart.legend().setVisible(False)
            chart.setBackgroundVisible(False)
            bs = QBarSet("")
            bs.setColor(QColor(color))
            bs.append(values)
            series = QBarSeries()
            series.append(bs)
            chart.addSeries(series)
            axis_x = QBarCategoryAxis()
            axis_x.append(categories)
            chart.addAxis(axis_x, Qt.AlignBottom)
            series.attachAxis(axis_x)
            axis_y = QValueAxis()
            chart.addAxis(axis_y, Qt.AlignLeft)
            series.attachAxis(axis_y)
            chart.createDefaultAxes()
            view = QChartView(chart)
            view.setRenderHint(view.renderHints().Antialiasing)
            view.setMinimumSize(0, 280)
            view.setMinimumWidth(100)
            view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            return view
        except Exception:
            parts = ", ".join(f"{c}: {v}" for c, v in zip(categories, values))
            lbl = QLabel(f"{title}\n{parts}")
            lbl.setMinimumHeight(80)
            return lbl

    def _pie_chart(self, title, items, color):
        """items: list of (label, value)"""
        try:
            from PySide6.QtCharts import (
                QChart, QChartView, QPieSeries, QPieSlice,
            )
            chart = QChart()
            chart.setTitle(title)
            chart.setAnimationOptions(QChart.SeriesAnimations)
            chart.legend().setVisible(True)
            chart.legend().setAlignment(Qt.AlignRight)
            chart.setBackgroundVisible(False)
            series = QPieSeries()
            palette = [style.ACCENT, style.SUCCESS, "#3b82f6", "#8b5cf6", "#ec4899", "#f59e0b", style.DANGER, "#10b981"]
            for i, (label, value) in enumerate(items):
                if value <= 0:
                    continue
                sl = QPieSlice(f"{label} ({value:.1f})", value)
                sl.setBrush(QColor(palette[i % len(palette)]))
                series.append(sl)
            chart.addSeries(series)
            view = QChartView(chart)
            view.setRenderHint(view.renderHints().Antialiasing)
            view.setMinimumSize(0, 280)
            view.setMinimumWidth(100)
            view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            return view
        except Exception:
            parts = ", ".join(f"{l}: {v}" for l, v in items)
            lbl = QLabel(f"{title}\n{parts}")
            lbl.setMinimumHeight(80)
            return lbl

    # ------------------------------------------------------------------ data

    def _monthly_revenue(self, months):
        keys, labels = self._months(months)
        start, end = keys[0], keys[-1]
        rows = db.fetch_all(
            """SELECT strftime('%Y-%m', payment_date) AS m,
                      COALESCE(SUM(amount), 0) AS total
               FROM payments
               WHERE strftime('%Y-%m', payment_date) BETWEEN ? AND ?
               GROUP BY m ORDER BY m""",
            (start, end),
        )
        data = {r["m"]: r["total"] for r in rows}
        values = [round(data.get(k, 0), 2) for k in keys]
        return labels, values

    def _monthly_new_members(self, months):
        keys, labels = self._months(months)
        start, end = keys[0], keys[-1]
        rows = db.fetch_all(
            """SELECT strftime('%Y-%m', join_date) AS m, COUNT(*) AS cnt
               FROM members
               WHERE strftime('%Y-%m', join_date) BETWEEN ? AND ?
               GROUP BY m ORDER BY m""",
            (start, end),
        )
        data = {r["m"]: r["cnt"] for r in rows}
        values = [data.get(k, 0) for k in keys]
        return labels, values

    def _revenue_by_method(self, months):
        keys, _labels = self._months(months)
        start, end = keys[0], keys[-1]
        rows = db.fetch_all(
            """SELECT payment_method, COALESCE(SUM(amount), 0) AS total
               FROM payments
               WHERE strftime('%Y-%m', payment_date) BETWEEN ? AND ?
               GROUP BY payment_method ORDER BY total DESC""",
            (start, end),
        )
        trans = {
            "cash": _("cash"),
            "card": _("card"),
            "transfer": _("transfer"),
        }
        return [(trans.get(r["payment_method"], r["payment_method"]), round(r["total"], 2)) for r in rows]

    def _members_by_plan(self):
        rows = db.fetch_all(
            """SELECT p.name AS plan_name, COUNT(s.member_id) AS cnt
               FROM plans p
               LEFT JOIN subscriptions s ON s.plan_id = p.id
               WHERE p.is_active = 1
               GROUP BY p.id, p.name
               ORDER BY cnt DESC"""
        )
        return [(r["plan_name"], float(r["cnt"])) for r in rows if r["cnt"] > 0]

    # ------------------------------------------------------------------ public

    def refresh(self, *_args):
        months = 12 if self.period.currentIndex() == 1 else 6

        # bar — monthly revenue
        labels, values = self._monthly_revenue(months)
        self._swap(self._rev_frame, self._bar_chart(
            _("revenue_by_month"), labels, values, style.ACCENT.name()
        ))

        # bar — new members
        labels2, values2 = self._monthly_new_members(months)
        self._swap(self._mem_frame, self._bar_chart(
            _("new_members_chart"), labels2, values2, "#3b82f6"
        ))

        # pie — revenue by payment method
        items = self._revenue_by_method(months)
        self._swap(self._pay_frame, self._pie_chart(
            _("payment_method_chart"), items, style.SUCCESS.name()
        ))

        # pie — members by plan
        items2 = self._members_by_plan()
        self._swap(self._plan_frame, self._pie_chart(
            _("plan_chart"), items2, "#8b5cf6"
        ))

        # hint
        has_payments = sum(values) > 0 or bool(items)
        has_members = sum(values2) > 0 or bool(items2)
        if not has_payments and not has_members:
            self._hint.setText(_("charts_no_data"))
        else:
            self._hint.setText("")
