import os
import tempfile
import webbrowser
fr
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib
import app.database as db


def _html_page(title, rows, columns, summary=None, rtl=True, landscape=False):
    currency = db.get_setting("currency", "")
    gym = db.get_setting("gym_name", "هايدروجين جم")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lang_dir = "rtl" if rtl else "ltr"
    align = "right" if rtl else "left"
    page = "@page { size: A4 landscape; margin: 10mm; }" if landscape else "@page { size: A4; margin: 12mm; }"

    thead = "".join(f"<th>{c}</th>" for c in columns)
    tbody = ""
    for r in rows:
        tds = "".join(f"<td>{v if v is not None else ''}</td>" for v in r)
        tbody += f"<tr>{tds}</tr>"
    if not tbody:
        tbody = f"<tr><td colspan='{len(columns)}' style='text-align:center;color:#888;padding:24px'>لا توجد بيانات</td></tr>"

    summary_html = ""
    if summary:
        items = "".join(
            f"<div class='sum'>{k}: <b>{v}</b></div>" for k, v in summary.items()
        )
        summary_html = f"<div class='summary'>{items}</div>"

    page = f"""<!DOCTYPE html>
<html lang="ar" dir="{lang_dir}">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  {page}
  body {{ font-family:'Segoe UI',Tahoma,Arial,sans-serif; margin:24px; color:#1c1c2e; text-align:{align}; }}
  h1 {{ color:#0f172a; margin-bottom:4px; }}
  .meta {{ color:#64748b; font-size:13px; margin-bottom:16px; }}
  .summary {{ display:flex; gap:12px; flex-wrap:wrap; margin:14px 0; }}
  .sum {{ background:#0f172a; color:#fff; padding:10px 16px; border-radius:10px; font-size:14px; }}
  table {{ width:100%; border-collapse:collapse; margin-top:8px; }}
  th {{ background:#0f172a; color:#fff; padding:10px 12px; font-size:13px; }}
  td {{ border-bottom:1px solid #e2e8f0; padding:9px 12px; font-size:13px; }}
  tr:nth-child(even) td {{ background:#f8fafc; }}
  .footer {{ margin-top:20px; color:#94a3b8; font-size:12px; text-align:center; }}
  @media print {{
    body {{ margin:8mm; font-size:11px; }}
    h1 {{ font-size:18px; }}
    .meta {{ font-size:11px; margin-bottom:8px; }}
    .summary {{ gap:8px; margin:10px 0; }}
    .sum {{ padding:6px 10px; font-size:12px; }}
    table {{ font-size:11px; }}
    th, td {{ padding:5px 7px; }}
    thead {{ display:table-header-group; }}
    tr {{ page-break-inside:avoid; }}
    .footer {{ font-size:10px; }}
  }}
</style>
</head>
<body>
  <h1>{gym} - {title}</h1>
  <div class="meta">{now}</div>
  {summary_html}
  <table>
    <thead><tr>{thead}</tr></thead>
    <tbody>{tbody}</tbody>
  </table>
  <div class="footer">{gym} © {now.split()[0].split('-')[0]}</div>
</body>
</html>"""
    return page



def _export_excel(title, rows, columns, summary=None):
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill
    from datetime import datetime
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Report"

    ws.merge_cells("A1:F1")
    cell = ws["A1"]
    cell.value = title
    cell.font = Font(bold=True, size=14)
    cell.alignment = Alignment(horizontal="center")

    for col_idx, col_name in enumerate(columns, 1):
        cell = ws.cell(row=2, column=col_idx)
        cell.value = col_name
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")
        cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")

    for row_idx, row_data in enumerate(rows, 3):
        for col_idx, value in enumerate(row_data, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    if summary:
        start_row = 3 + len(rows) + 2
        for i, (k, v) in enumerate(summary.items()):
            ws.cell(row=start_row + i, column=1, value=k).font = Font(bold=True)
            ws.cell(row=start_row + i, column=2, value=v)

    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                val_len = len(str(cell.value)) if cell.value is not None else 0
                if val_len > max_length:
                    max_length = val_len
            except: pass
        ws.column_dimensions[column].width = max_length + 2

    path = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    wb.save(path)
    os.startfile(path)

def _output_report(fmt, title, data, cols, summary=None):
    if fmt == "excel":
        _export_excel(title, data, cols, summary)
    else:
        _open_html(_html_page(title, data, cols, summary)), title, data, cols, summary)
def _open_html(page):
    fd, path = tempfile.mkstemp(suffix=".html", prefix="report_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(page)
    webbrowser.open("file://" + path)



def _export_excel(title, rows, columns, summary=None):
    """Exports data to Excel file and opens it."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Report"

    # Title
    ws.merge_cells("A1:F1")
    cell = ws["A1"]
    cell.value = title
    cell.font = Font(bold=True, size=14)
    cell.alignment = Alignment(horizontal="center")

    # Columns
    for col_idx, col_name in enumerate(columns, 1):
        cell = ws.cell(row=2, column=col_idx)
        cell.value = col_name
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")
        cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")

    # Data
    for row_idx, row_data in enumerate(rows, 3):
        for col_idx, value in enumerate(row_data, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    # Summary
    if summary:
        start_row = 3 + len(rows) + 2
        for i, (k, v) in enumerate(summary.items()):
            ws.cell(row=start_row + i, column=1, value=k).font = Font(bold=True)
            ws.cell(row=start_row + i, column=2, value=v)

    # Auto-adjust columns
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value)
            except: pass
        ws.column_dimensions[column].width = max_length + 2

    path = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    wb.save(path)
    os.startfile(path) # Windows specific

def _period(a="", b=""):
    return f" ({a} إلى {b})" if a and b else ""


def attendance_report(date_from, date_to, method="all", format="html":
    rows = db.fetch_all(
        """SELECT a.check_in, a.check_out,
                  m.full_name, m.phone, a.method
           FROM attendance a JOIN members m ON a.member_id = m.id
           WHERE date(a.check_in) BETWEEN ? AND ?
           ORDER BY a.check_in""",
        (date_from, date_to),
    )
    data = []
    for r in rows:
        ci = str(r["check_in"])[:16]
        co = str(r["check_out"])[:16] if r["check_out"] else "-"
        data.append((ci, co, r["full_name"], r["phone"], r["method"])
    cols = ["التاريخ والوقت", "وقت الخروج", "العضو", "الهاتف", "الطريقة"]
    summary = {"عدد الجلسات": len(data)}
    _output_report(format, "تقرير الحضور" + _period(date_from, date_to), data, cols, summary)


def attendance_days_report(date_from, date_to, member_id=None, format="html":
    """عدد أيام الحضور لكل عضو من تاريخ إلى تاريخ — يحسب اليوم مرة واحدة فقط (DISTINCT).

    إذا حُدّد member_id يعرض العضو المحدد فقط، وإلا يعرض جميع الأعضاء.
    """
    params = [date_from, date_to]
    member_filter = ""
    if member_id is not None:
        member_filter = " AND m.id = ?"
        params.append(member_id)

    rows = db.fetch_all(
        f"""SELECT m.code, m.full_name, m.phone,
                  COUNT(DISTINCT date(a.check_in) AS days_count,
                  MIN(date(a.check_in) AS first_day,
                  MAX(date(a.check_in) AS last_day
           FROM attendance a
           JOIN members m ON a.member_id = m.id
           WHERE date(a.check_in) BETWEEN ? AND ?{member_filter}
           GROUP BY m.id, m.code, m.full_name, m.phone
           ORDER BY days_count DESC, m.full_name""",
        tuple(params),
    )
    data = []
    for r in rows:
        data.append((
            r["code"] or "-",
            r["full_name"],
            r["phone"] or "-",
            str(r["days_count"]),
            r["first_day"] or "-",
            r["last_day"] or "-",
        )
    cols = ["الكود", "اسم العضو", "الهاتف", "عدد أيام الحضور", "أول حضور", "آخر حضور"]
    total_days = sum(r["days_count"] for r in rows)
    title = "تقرير أيام الحضور" + _period(date_from, date_to)
    if member_id is not None and rows:
        title += f" — {rows[0]['full_name']}"
    summary = {
        "عدد الأعضاء": len(data),
        "إجمالي أيام الحضور": total_days,
    }
    # عند اختيار عضو واحد نظهر الأيام فقط بشكل بارز
    if member_id is not None and rows:
        summary = {
            "العضو": rows[0]["full_name"],
            "عدد أيام الحضور": rows[0]["days_count"],
            "الفترة": f"{date_from} إلى {date_to}",
        }
    _output_report(format, title, data, cols, summary)


def financial_report(date_from, date_to, method="all", format="html":
    currency = db.get_setting("currency", "")
    if method == "daily":
        rows = db.fetch_all(
            """SELECT payment_date, payment_method, SUM(amount) AS total
               FROM payments WHERE payment_date BETWEEN ? AND ?
               GROUP BY payment_date, payment_method ORDER BY payment_date""",
            (date_from, date_to),
        )
        data = [(r["payment_date"], r["payment_method"], f'{r["total"]:.2f}') for r in rows]
        cols = ["التاريخ", "الطريقة", "المبلغ"]
        total = sum(r["total"] for r in rows)
        by_method = {}
        for r in rows:
            by_method[r["payment_method"]] = by_method.get(r["payment_method"], 0) + r["total"]
    else:
        rows = db.fetch_all(
            """SELECT p.payment_date, m.full_name, pm.name AS plan_name, p.amount,
                      p.payment_method, p.reference_number
               FROM payments p
               JOIN members m ON p.member_id = m.id
               LEFT JOIN subscriptions s ON p.subscription_id = s.id
               LEFT JOIN plans pm ON s.plan_id = pm.id
               WHERE p.payment_date BETWEEN ? AND ?
               ORDER BY p.payment_date""",
            (date_from, date_to),
        )
        data = [
            (r["payment_date"], r["full_name"], r["plan_name"], f'{r["amount"]:.2f}',
             r["payment_method"], r["reference_number"])
            for r in rows
        ]
        cols = ["التاريخ", "العضو", "الخطة", "المبلغ", "الطريقة", "المرجع"]
        total = sum(r["amount"] for r in rows)
        by_method = {}
        for r in rows:
            by_method[r["payment_method"]] = by_method.get(r["payment_method"], 0) + r["amount"]

    summary = {"إجمالي المدفوعات": f"{total:.2f} {currency}", "عدد العمليات": len(data)}
    for mname, amt in by_method.items():
        summary[f"💰 {mname}"] = f"{amt:.2f} {currency}"
    _output_report(format, "التقرير المالي" + _period(date_from, date_to), data, cols, summary)


def members_report(, format="html":
    rows = db.fetch_all(
        """SELECT m.code, m.full_name, m.phone, m.gender, m.join_date,
                  m.is_active, s.end_date, s.end_date IS NOT NULL AND s.end_date >= date('now') AS has_active
           FROM members m
           LEFT JOIN subscriptions s ON s.id = (SELECT id FROM subscriptions
               WHERE member_id = m.id AND status='active' ORDER BY end_date DESC LIMIT 1)
           ORDER BY m.join_date DESC"""
    )
    data = []
    for r in rows:
        status = "نشط" if r["has_active"] else "منتهي"
        data.append((r["code"], r["full_name"], r["phone"], r["gender"],
                     r["join_date"], ("نشط" if r["is_active"] else "غير نشط"), status, r["end_date"] or "-")
    cols = ["الكود", "الاسم", "الهاتف", "الجنس", "تاريخ الانضمام", "الحالة", "الاشتراك", "تاريخ النهاية"]
    summary = {"إجمالي الأعضاء": len(data)}
    _output_report(format, "تقرير الأعضاء", data, cols, summary)


def _members_by_status(status):
    """status: 'active' | 'expired'"""
    if status == "active":
        cond = "s.status='active' AND s.end_date >= date('now')"
    else:
        cond = "s.status='active' AND s.end_date < date('now')"
    return db.fetch_all(
        f"""SELECT m.code, m.full_name, m.phone, m.gender, m.join_date, s.end_date
            FROM members m
            JOIN subscriptions s ON s.id = (
                SELECT id FROM subscriptions
                WHERE member_id = m.id AND status='active'
                ORDER BY end_date DESC LIMIT 1)
            WHERE {cond}
            ORDER BY m.full_name"""
    )


def _members_report_status(status, title):
    rows = _members_by_status(status)
    data = [
        (r["code"], r["full_name"], r["phone"], r["gender"], r["join_date"],
         r["end_date"] or "-")
        for r in rows
    ]
    cols = ["الكود", "الاسم", "الهاتف", "الجنس", "تاريخ الانضمام", "تاريخ النهاية"]
    summary = {"عدد الأعضاء": len(data)}
    _output_report(format, title, data, cols, summary)


def active_members_report(, format="html":
    _members_report_status("active", "تقرير الأعضاء النشطون")


def expired_members_report(, format="html":
    _members_report_status("expired", "تقرير الأعضاء المنتهية")


def coach_members_report(, format="html":
    """عدد اللاعبين (الأعضاء) لكل مدرب."""
    rows = db.fetch_all(
        """SELECT c.id, c.full_name AS coach_name,
                  COUNT(DISTINCT s.member_id) AS members
           FROM coaches c
           LEFT JOIN subscriptions s ON s.coach_id = c.id
           WHERE c.is_active = 1
           GROUP BY c.id, c.full_name
           ORDER BY members DESC"""
    )
    data = [
        (r["coach_name"], r["members"]) for r in rows
    ]
    cols = ["المدرب", "عدد اللاعبين"]
    total = sum(r["members"] for r in rows)
    summary = {"عدد المدربين": len(data), "إجمالي اللاعبين": total}
    _output_report(format, "تقرير عدد اللاعبين لكل مدرب", data, cols, summary)


def coach_members_names_report(, format="html":
    """أسماء اللاعبين (الأعضاء) لكل مدرب."""
    coaches = db.fetch_all(
        """SELECT c.id, c.full_name AS coach_name,
                  COUNT(DISTINCT s.member_id) AS members
           FROM coaches c
           LEFT JOIN subscriptions s ON s.coach_id = c.id
           WHERE c.is_active = 1
           GROUP BY c.id, c.full_name
           ORDER BY c.full_name"""
    )
    rows = db.fetch_all(
        """SELECT c.full_name AS coach_name, m.full_name AS member_name, m.phone
           FROM coaches c
           JOIN subscriptions s ON s.coach_id = c.id
           JOIN members m ON s.member_id = m.id
           WHERE c.is_active = 1
           ORDER BY c.full_name, m.full_name"""
    )
    data = [(r["coach_name"], r["member_name"], r["phone"] or "-") for r in rows]
    cols = ["المدرب", "اسم اللاعب", "الهاتف"]
    summary = {"عدد المدربين": len(coaches), "إجمالي اللاعبين": len(data)}
    _output_report(format, "تقرير أسماء اللاعبين لكل مدرب", data, cols, summary)



def expenses_by_category_report(date_from="", date_to="", format="html":
    """Expenses grouped by category for a date range."""
    currency = db.get_setting("currency", "")
    where = ""
    params = ()
    if date_from and date_to:
        where = "WHERE expense_date BETWEEN ? AND ?"
        params = (date_from, date_to)
    rows = db.fetch_all(
        "SELECT category, COUNT(*) AS n, COALESCE(SUM(amount),0) AS total "
        "FROM expenses " + where + " GROUP BY category ORDER BY total DESC",
        params,
    )
    w_cat = "التصنيف"
    w_n = "عدد العمليات"
    w_am = "المبلغ"
    w_na = "بدون تصنيف"
    w_t = "إجمالي المصاريف"
    data = [(r["category"] or w_na, r["n"], f"{r['total']:.2f} {currency}") for r in rows]
    summary = {w_t: f"{sum(r['total'] for r in rows):.2f} {currency}"}
    _output_report(format, 
        "تقرير المصاريف حسب الفئة" + _period(date_from, date_to),
        data, [w_cat, w_n, w_am], summary)

def coach_earnings_report(, format="html":
    """Subscription revenue per coach."""
    currency = db.get_setting("currency", "")
    rows = db.fetch_all(
        "SELECT c.full_name, COUNT(*) AS n, COALESCE(SUM(s.price_paid),0) AS total, "
        "COALESCE(SUM(CASE WHEN s.start_date >= date('now','start of month') THEN s.price_paid END),0) AS month_total "
        "FROM subscriptions s JOIN coaches c ON s.coach_id = c.id "
        "GROUP BY s.coach_id ORDER BY total DESC"
    )
    w_co = "المدرب"
    w_n = "عدد الاشتراكات"
    w_m = "إجمالي الشهر الحالي"
    w_t = "الإجمالي"
    data = [(r["full_name"], r["n"], f"{r['month_total']:.2f} {currency}", f"{r['total']:.2f} {currency}") for r in rows]
    summary = {w_t: f"{sum(r['total'] for r in rows):.2f} {currency}"}
    _output_report(format, 
        "تقرير أرباح المدربين",
        data, [w_co, w_n, w_m, w_t], summary)


def generate_daily_profit_chart(date_from, date_to):
    """Generates a line chart of daily profits and saves as image."""
    currency = db.get_setting("currency", "")
    rows = db.fetch_all(
        """SELECT payment_date, payment_method, SUM(amount) AS total
           FROM payments
           WHERE payment_date BETWEEN ? AND ?
           GROUP BY payment_date, payment_method
           ORDER BY payment_date""",
        (date_from, date_to),
    )
    
    if not rows:
        return None

    # Process data for plotting
    dates = sorted(list(set(r["payment_date"] for r in rows)))
    cash_vals = []
    card_vals = []
    trans_vals = []
    totals = []

    for d in dates:
        day_rows = [r for r in rows if r["payment_date"] == d]
        c = sum(r["total"] for r in day_rows if r["payment_method"] in ["نقدي", "cash"])
        ca = sum(r["total"] for r in day_rows if r["payment_method"] in ["بطاقة", "card"])
        t = sum(r["total"] for r in day_rows if r["payment_method"] in ["تحويل", "transfer"])
        cash_vals.append(c)
        card_vals.append(ca)
        trans_vals.append(t)
        totals.append(c + ca + t)

    # Create plot
    plt.figure(figsize=(10, 5))
    plt.plot(dates, cash_vals, label="Cash", color="#2ecc71", marker="o")
    plt.plot(dates, card_vals, label="Card", color="#3498db", marker="o")
    plt.plot(dates, trans_vals, label="Transfer", color="#9b59b6", marker="o")
    plt.plot(dates, totals, label="Total", color="#e74c3c", linewidth=3, marker="s")
    
    plt.title(f"Daily Profits ({date_from} to {date_to})")
    plt.xlabel("Date")
    plt.ylabel(f"Amount ({currency})")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.xticks(rotation=45)
    plt.tight_layout()

    path = f"profit_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(path)
    plt.close()
    return path

def daily_profit_report(date_from, date_to, format="html":
    """الأرباح اليومية مُقسّمة حسب طريقة الدفع (نقدي/بطاقة/تحويل)."""
    currency = db.get_setting("currency", "")
    rows = db.fetch_all(
        """SELECT payment_date, payment_method, COUNT(*) AS n, COALESCE(SUM(amount),0) AS total
           FROM payments
           WHERE payment_date BETWEEN ? AND ?
           GROUP BY payment_date, payment_method
           ORDER BY payment_date, payment_method""",
        (date_from, date_to),
    )
    # group by date
    by_date = {}
    for r in rows:
        d = r["payment_date"]
        if d not in by_date:
            by_date[d] = {"cash": 0.0, "card": 0.0, "transfer": 0.0, "total": 0.0, "n": 0}
        m = r["payment_method"] or ""
        if m == "نقدي" or m == "cash":
            key = "cash"
        elif m == "بطاقة" or m == "card":
            key = "card"
        elif m == "تحويل" or m == "transfer":
            key = "transfer"
        else:
            key = m
        by_date[d][key] += r["total"]
        by_date[d]["total"] += r["total"]
        by_date[d]["n"] += r["n"]
    data = []
    for d in sorted(by_date.keys():
        b = by_date[d]
        data.append((
            d,
            f'{b["cash"]:.2f}',
            f'{b["card"]:.2f}',
            f'{b["transfer"]:.2f}',
            f'{b["total"]:.2f}',
            str(b["n"]),
        )
    cols = ["التاريخ", "نقدي", "بطاقة", "تحويل", "الإجمالي", "عدد الدفعات"]
    total_cash = sum(d[1] for d in data)
    total_card = sum(d[2] for d in data)
    total_transfer = sum(d[3] for d in data)
    total_all = sum(d[4] for d in data)
    total_n = sum(int(d[5]) for d in data)
    summary = {
        "إجمالي النقدي": f"{total_cash:.2f} {currency}",
        "إجمالي البطاقة": f"{total_card:.2f} {currency}",
        "إجمالي التحويل": f"{total_transfer:.2f} {currency}",
        "الإجمالي": f"{total_all:.2f} {currency}",
        "عدد الدفعات": str(total_n),
    }
    _output_report(format, "تقرير الأرباح اليومية" + _period(date_from, date_to),
                          data, cols, summary)


def expiring_subs_report(days=7):
    """الاشتراكات النشطة التي تنتهي خلال أيام محددة."""
    rows = db.fetch_all(
        """SELECT m.full_name AS member_name, m.phone,
                  p.name AS plan_name, s.end_date
           FROM subscriptions s
           JOIN members m ON s.member_id = m.id
           JOIN plans p ON s.plan_id = p.id
           WHERE s.status = 'active'
             AND s.end_date >= date('now')
             AND s.end_date <= date('now', ?)
           ORDER BY s.end_date""",
        ("+" + str(days) + " days",),
    )
    data = [(r["member_name"], r["phone"] or "-", r["plan_name"] or "-", r["end_date"] or "-") for r in rows]
    cols = ["اسم اللاعب", "الهاتف",
            "نوع العضوية", "تاريخ النهاية"]
    summary = {"عدد الاشتراكات": len(data),
               "خلال": str(days) + " أيام"}
    _output_report(format, 
        "الاشتراكات التي تنتهي خلال " + str(days) + " أيام",
        data, cols, summary)


def plan_members_report(plan_id=None, format="html":
    """عدد وأسماء اللاعبين حسب نوع العضوية (الخطة)."""
    if plan_id is not None:
        plan = db.fetch_one("SELECT name FROM plans WHERE id=?", (plan_id,)
        plan_name = plan["name"] if plan else "-"
        rows = db.fetch_all(
            """SELECT m.full_name AS member_name, m.phone,
                      s.end_date
               FROM subscriptions s
               JOIN members m ON s.member_id = m.id
               WHERE s.plan_id = ? AND s.status = 'active'
               ORDER BY m.full_name""",
            (plan_id,),
        )
        data = [(r["member_name"], r["phone"] or "-", r["end_date"] or "-") for r in rows]
        cols = ["اسم اللاعب", "الهاتف", "تاريخ النهاية"]
        summary = {"نوع العضوية": plan_name, "عدد اللاعبين": len(data)}
        _output_report(format, f"تقرير لاعبي {plan_name}", data, cols, summary)
        return
    plans = db.fetch_all(
        """SELECT p.id, p.name AS plan_name,
                  COUNT(DISTINCT s.member_id) AS members
           FROM plans p
           LEFT JOIN subscriptions s ON s.plan_id = p.id
           WHERE p.is_active = 1
           GROUP BY p.id, p.name
           ORDER BY members DESC"""
    )
    rows = db.fetch_all(
        """SELECT p.name AS plan_name, m.full_name AS member_name, m.phone,
                  s.end_date
           FROM plans p
           JOIN subscriptions s ON s.plan_id = p.id
           JOIN members m ON s.member_id = m.id
           WHERE p.is_active = 1
           ORDER BY p.name, m.full_name"""
    )
    data = [(r["plan_name"], r["member_name"], r["phone"] or "-", r["end_date"] or "-") for r in rows]
    cols = ["العضوية", "اسم اللاعب", "الهاتف", "تاريخ النهاية"]
    total = sum(r["members"] for r in plans)
    summary = {"عدد أنواع العضوية": len(plans), "إجمالي اللاعبين": len(data)}
    _output_report(format, "تقرير اللاعبين حسب العضوية", data, cols, summary)


def profit_loss_report(date_from, date_to, format="html":
    """الإيرادات مقابل المصاريف وصافي الربح."""
    currency = db.get_setting("currency", "")
    income = db.fetch_one(
        """SELECT COALESCE(SUM(amount),0) AS c FROM payments
           WHERE payment_date BETWEEN ? AND ?""",
        (date_from, date_to),
    )["c"]
    exp_rows = db.fetch_all(
        """SELECT expense_date, description, amount, category
           FROM expenses WHERE expense_date BETWEEN ? AND ?
           ORDER BY expense_date""",
        (date_from, date_to),
    )
    expenses = sum(r["amount"] for r in exp_rows)
    net = income - expenses

    data = [
        (r["expense_date"], r["description"], r["category"],
         f'{r["amount"]:.2f}') for r in exp_rows
    ]
    cols = ["التاريخ", "الوصف", "الفئة", "المبلغ"]
    summary = {
        "الإيرادات": f"{income:.2f} {currency}",
        "المصاريف": f"{expenses:.2f} {currency}",
        "صافي الربح": f"{net:.2f} {currency}",
    }
    _output_report(format, "تقرير الأرباح والخسائر" + _period(date_from, date_to),
                          data, cols, summary)


def renewal_report(date_from, date_to, format="html":
    """نسبة تجديد الاشتراكات التي انتهت خلال الفترة."""
    currency = db.get_setting("currency", "")
    subs = db.fetch_all(
        """SELECT s.id, s.member_id, s.end_date, s.start_date, m.full_name, m.phone
           FROM subscriptions s JOIN members m ON s.member_id=m.id
           WHERE date(s.end_date) BETWEEN ? AND ?
           ORDER BY s.end_date""",
        (date_from, date_to),
    )
    data = []
    renewed = 0
    for s in subs:
        nxt = db.fetch_one(
            """SELECT id, start_date, end_date FROM subscriptions
               WHERE member_id=? AND start_date > ? AND start_date <= date(?, '+60 day')
               ORDER BY start_date LIMIT 1""",
            (s["member_id"], s["end_date"], s["end_date"]),
        )
        is_renewed = nxt is not None
        if is_renewed:
            renewed += 1
        status = "جدّد ✅" if is_renewed else "لم يجدّد ❌"
        data.append((s["full_name"], s["phone"], s["end_date"], status,
                     nxt["start_date"] if nxt else "-")
    cols = ["الاسم", "الهاتف", "تاريخ الانتهاء", "الحالة", "تاريخ التجديد"]
    rate = (renewed / len(subs) * 100) if subs else 0
    summary = {
        "إجمالي الاشتراكات": len(subs),
        "جدّدوا": renewed,
        "لم يجدّدوا": len(subs) - renewed,
        "نسبة التجديد": f"{rate:.1f}%",
    }
    _output_report(format, "تقرير نسبة التجديد" + _period(date_from, date_to),
                          data, cols, summary)

def user_movements_24h_report():
    """سجل حضور الأعضاء لآخر 24 ساعة (للتوافق)."""
    rows = db.fetch_all(
        """SELECT a.check_in, a.check_out, m.full_name, m.phone, m.code,
                  a.method,
                  (SELECT s.end_date FROM subscriptions s
                   WHERE s.member_id=a.member_id AND s.status='active'
                   ORDER BY s.end_date DESC LIMIT 1) AS end_date
           FROM attendance a
           JOIN members m ON a.member_id=m.id
           WHERE a.check_in >= datetime('now', '-1 day')
             AND lower(m.full_name) NOT IN ('admin','المدير','test')
             AND m.code NOT LIKE 'ADMIN%'
           ORDER BY a.check_in DESC"""
    )
    data = []
    for r in rows:
        ci = str(r["check_in"])[:16] if r["check_in"] else "-"
        co = str(r["check_out"])[:16] if r["check_out"] else "-"
        data.append((
            r["full_name"] or "-",
            r["code"] or "-",
            r["phone"] or "-",
            ci,
            co,
            r["method"] or "-",
            r["end_date"] or "-",
        )
    cols = ["العضو", "الكود", "الهاتف", "وقت الدخول", "وقت الخروج", "الطريقة", "نهاية الاشتراك"]
    summary = {"عدد الحركات (24س)": len(data)}
    title = "سجل حضور الأعضاء — آخر 24 ساعة"
    _output_report(format, title, data, cols, summary)


def user_actions_24h_report():
    """سجل حركات اليوزر (إضافة/تعديل/حذف عضو/اشتراك/دفعة) لآخر 24 ساعة."""
    rows = db.fetch_all(
        """SELECT username, action, target_type, target_name, details, created_at
           FROM user_actions
           WHERE created_at >= datetime('now', '-1 day')
           ORDER BY created_at DESC"""
    )
    data = []
    for r in rows:
        data.append((
            r["created_at"][:16] if r["created_at"] else "-",
            r["username"] or "-",
            r["action"] or "-",
            r["target_type"] or "-",
            r["target_name"] or "-",
            r["details"] or "-",
        )
    cols = ["الوقت", "اليوزر", "الحركة", "النوع", "الاسم", "التفاصيل"]
    summary = {"عدد الحركات (24س)": len(data)}
    title = "سجل حركات اليوزر — آخر 24 ساعة (إضافة/تعديل/حذف)"
    _output_report(format, title, data, cols, summary)


def salary_report(date_from, date_to, format="html":
    """Monthly payroll statement for all employees."""
    currency = db.get_setting("currency", "")
    month = date_from[:7]
    employees = db.fetch_all(
        "SELECT * FROM employees ORDER BY is_active DESC, full_name"
    )
    data = []
    t_basic = t_ot = t_adv = t_leave = t_due = t_paid = t_rem = 0.0
    for e in employees:
        eid = e["id"]
        overtime = db.fetch_one(
            "SELECT COALESCE(SUM(amount),0) AS c FROM employee_overtime WHERE employee_id=? AND overtime_date BETWEEN ? AND ?",
            (eid, date_from, date_to),
        )["c"]
        advances = db.fetch_one(
            "SELECT COALESCE(SUM(amount),0) AS c FROM employee_advances WHERE employee_id=? AND advance_date BETWEEN ? AND ?",
            (eid, date_from, date_to),
        )["c"]
        leaves = db.fetch_one(
            "SELECT COALESCE(SUM(deduction),0) AS c FROM employee_leaves WHERE employee_id=? AND start_date BETWEEN ? AND ?",
            (eid, date_from, date_to),
        )["c"]
        month_alt = "-".join(reversed(month.split("-") if month else ""
        paid = db.fetch_one(
            "SELECT COALESCE(SUM(amount),0) AS c FROM employee_payrolls WHERE employee_id=? AND (salary_month=? OR salary_month=? OR (salary_month=\'\' AND payment_date BETWEEN ? AND ?)",
            (eid, month, month_alt, date_from, date_to),
        )["c"]
        basic = e["monthly_salary"] or 0
        due = basic + overtime - advances - leaves
        remaining = due - paid
        data.append((
            e["full_name"], e["position"] or "-",
            f"{basic:.2f}", f"{overtime:.2f}", f"{advances:.2f}",
            f"{leaves:.2f}", f"{due:.2f}", f"{paid:.2f}", f"{remaining:.2f}",
        )
        t_basic += basic
        t_ot += overtime
        t_adv += advances
        t_leave += leaves
        t_due += due
        t_paid += paid
        t_rem += remaining
    w_emp = "\u0627\u0644\u0645\u0648\u0638\u0641"
    w_pos = "\u0627\u0644\u0648\u0638\u064a\u0641\u0629"
    w_bas = "\u0627\u0644\u0623\u0633\u0627\u0633\u064a"
    w_ove = "\u0627\u0644\u0625\u0636\u0627\u0641\u064a"
    w_adv = "\u0627\u0644\u0633\u0644\u0641"
    w_lea = "\u0627\u0644\u062e\u0635\u0648\u0645\u0627\u062a"
    w_net = "\u0627\u0644\u0635\u0627\u0641\u064a \u0627\u0644\u0645\u0633\u062a\u062d\u0642"
    w_pai = "\u0627\u0644\u0645\u062f\u0641\u0648\u0639"
    w_rem = "\u0627\u0644\u0645\u062a\u0628\u0642\u064a"
    w_cou = "\u0639\u062f\u062f \u0627\u0644\u0645\u0648\u0638\u0641\u064a\u0646"
    w_tba = "\u0625\u062c\u0645\u0627\u0644\u064a \u0627\u0644\u0623\u0633\u0627\u0633\u064a"
    w_tne = "\u0625\u062c\u0645\u0627\u0644\u064a \u0627\u0644\u0635\u0627\u0641\u064a \u0627\u0644\u0645\u0633\u062a\u062d\u0642"
    w_tpa = "\u0625\u062c\u0645\u0627\u0644\u064a \u0627\u0644\u0645\u062f\u0641\u0648\u0639"
    w_tre = "\u0625\u062c\u0645\u0627\u0644\u064a \u0627\u0644\u0645\u062a\u0628\u0642\u064a"
    w_pay = "\u0643\u0634\u0641 \u0627\u0644\u0631\u0648\u0627\u062a\u0628 \u0627\u0644\u0634\u0647\u0631\u064a"
    cols = [w_emp, w_pos, w_bas, w_ove, w_adv, w_lea, w_net, w_pai, w_rem]
    summary = {
        w_cou: len(employees),
        w_tba: f"{t_basic:.2f} {currency}",
        w_tne: f"{t_due:.2f} {currency}",
        w_tpa: f"{t_paid:.2f} {currency}",
        w_tre: f"{t_rem:.2f} {currency}",
    }
    _output_report(format, w_pay + _period(date_from, date_to), data, cols, summary, landscape=True)
