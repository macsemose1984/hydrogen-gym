import os
import webbrowser
from datetime import datetime

import app.database as db
from app.i18n import _


def invoice_html(payment):
    """Build an RTL printable invoice HTML for a payment."""
    currency = db.get_setting("currency", "")
    gym = db.get_setting("gym_name", "هايدروجين جم")
    rec = db.fetch_one(
        """SELECT p.*, m.full_name, m.phone, m.code, pm.name AS plan_name
           FROM payments p
           JOIN members m ON p.member_id = m.id
           LEFT JOIN subscriptions s ON p.subscription_id = s.id
           LEFT JOIN plans pm ON s.plan_id = pm.id
           WHERE p.id=?""",
        (payment["id"],),
    )
    if not rec:
        return None
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>فاتورة - {gym}</title>
<style>
  body {{ font-family:'Segoe UI',Tahoma,Arial,sans-serif; margin:40px; color:#1c1c2e; }}
  .header {{ text-align:center; border-bottom:3px solid #0f172a; padding-bottom:16px; margin-bottom:24px; }}
  .header h1 {{ margin:0; color:#0f172a; font-size:26px; }}
  .header p {{ color:#64748b; margin:4px 0 0; }}
  .meta {{ display:flex; justify-content:space-between; margin-bottom:24px; font-size:14px; }}
  .meta div {{ background:#f8fafc; padding:10px 16px; border-radius:8px; }}
  .amount {{ text-align:center; margin:28px 0; }}
  .amount .num {{ font-size:42px; font-weight:bold; color:#0f172a; }}
  .amount .cur {{ font-size:22px; color:#64748b; }}
  table {{ width:100%; border-collapse:collapse; margin:16px 0; }}
  th {{ background:#0f172a; color:#fff; padding:10px; font-size:13px; }}
  td {{ border:1px solid #e2e8f0; padding:10px; font-size:14px; text-align:center; }}
  .footer {{ margin-top:36px; border-top:1px solid #e2e8f0; padding-top:12px; text-align:center; color:#94a3b8; font-size:12px; }}
  .stamp {{ margin-top:40px; text-align:left; color:#64748b; font-size:13px; }}
</style>
</head>
<body>
  <div class="header">
    <h1>🏋️ {gym}</h1>
    <p>فاتورة رسمية</p>
  </div>
  <div class="meta">
    <div>رقم الفاتورة: <b>#{rec['id']}</b></div>
    <div>التاريخ: <b>{rec['payment_date']}</b></div>
    <div>رقم العضو: <b>{rec['code']}</b></div>
  </div>
  <table>
    <tr><th>اسم العضو</th><th>الهاتف</th><th>الخطة</th><th>طريقة الدفع</th></tr>
    <tr>
      <td>{rec['full_name']}</td>
      <td>{rec['phone']}</td>
      <td>{rec['plan_name'] or '-'}</td>
      <td>{rec['payment_method']}</td>
    </tr>
  </table>
  <div class="amount">
    <span>المبلغ المدفوع: </span>
    <span class="num">{rec['amount']:.2f}</span>
    <span class="cur">{currency}</span>
  </div>
  <div class="stamp">
    التوقيع: ____________________
  </div>
  <div class="footer">
    {gym} © {now.split()[0].split('-')[0]} — تصميم عوني جرادات 0796161401
  </div>
</body>
</html>"""


def payroll_html(employee, month, values, currency):
    """Build a printable payroll HTML for an employee for a given month."""
    gym = db.get_setting("gym_name", "هايدروجين جم")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    name = employee["full_name"]
    emp_code = employee.get("code", "") or ""

    rows_html = ""
    for title, amount, is_total in values:
        cls = "total" if is_total else ""
        rows_html += f'<tr class="{cls}"><td>{title}</td><td class="num">{amount:.2f} {currency}</td></tr>\n'

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>كشف راتب - {gym}</title>
<style>
  body {{ font-family:'Segoe UI',Tahoma,Arial,sans-serif; margin:40px; color:#1c1c2e; }}
  .header {{ text-align:center; border-bottom:3px solid #0f172a; padding-bottom:16px; margin-bottom:24px; }}
  .header h1 {{ margin:0; color:#0f172a; font-size:26px; }}
  .header p {{ color:#64748b; margin:4px 0 0; }}
  .meta {{ display:flex; justify-content:space-between; margin-bottom:24px; font-size:14px; }}
  .meta div {{ background:#f8fafc; padding:10px 16px; border-radius:8px; }}
  table {{ width:100%; border-collapse:collapse; margin:16px 0; }}
  th {{ background:#0f172a; color:#fff; padding:10px; font-size:13px; text-align:center; }}
  td {{ border:1px solid #e2e8f0; padding:10px; font-size:14px; }}
  td.num {{ text-align:right; font-variant-numeric: tabular-nums; }}
  tr.total td {{ font-weight:700; background:#f1f5f9; }}
  .footer {{ margin-top:36px; border-top:1px solid #e2e8f0; padding-top:12px; text-align:center; color:#94a3b8; font-size:12px; }}
</style>
</head>
<body>
  <div class="header">
    <h1>🏋️ {gym}</h1>
    <p>كشف راتب شهري</p>
  </div>
  <div class="meta">
    <div>الموظف: <b>{name}</b></div>
    <div>الكود: <b>{emp_code or '-'}</b></div>
    <div>الشهر: <b>{month}</b></div>
  </div>
  <table>
    <tr><th>البند</th><th>المبلغ</th></tr>
    {rows_html}
  </table>
  <div class="footer">
    {gym} © {now.split()[0].split('-')[0]} — تصميم عوني جرادات 0796161401
  </div>
</body>
</html>"""


def print_payroll_pdf(employee, month, values, currency, output_dir=None):
    """Open the payroll statement in the browser for a correct PDF export."""
    html = payroll_html(employee, month, values, currency)
    if not html:
        return None

    out_dir = output_dir or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "invoices")
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(out_dir, f"payroll_{employee['id']}_{month}_{stamp}.html")

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open("file://" + os.path.abspath(path))
    return path


def print_employee_history_pdf(employee_id, kind, rows, month_label, start, end, output_dir=None):
    """Print filtrated employee history (salary/advance/leave/overtime) per month."""
    employee = db.fetch_one("SELECT * FROM employees WHERE id=?", (employee_id,))
    if not employee:
        return None
    gym = db.get_setting("gym_name", "هايدروجين جم")
    currency = db.get_setting("currency", "")
    kind_titles = {
        "salary": _("view_salaries"),
        "advance": _("view_advances"),
        "leave": _("view_leaves"),
        "overtime": _("view_overtime"),
    }
    title = kind_titles.get(kind, kind)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    headers_map = {
        "salary": [_("payment_date"), _("salary_month"), _("amount"), _("notes")],
        "advance": [_("advance_date"), _("amount"), _("notes")],
        "leave": [_("leave_type"), _("start_date"), _("end_date"), _("deduction"), _("notes")],
        "overtime": [_("overtime_date"), _("overtime_hours"), _("amount"), _("notes")],
    }
    fields_map = {
        "salary": ["payment_date", "salary_month", "amount", "notes"],
        "advance": ["advance_date", "amount", "notes"],
        "leave": ["leave_type", "start_date", "end_date", "deduction", "notes"],
        "overtime": ["overtime_date", "hours", "amount", "notes"],
    }
    headers = headers_map.get(kind, [])
    fields = fields_map.get(kind, [])
    thead = "".join(f"<th>{h}</th>" for h in headers)
    tbody = ""
    total = 0
    for r in rows:
        tds = ""
        for f in fields:
            v = r[f]
            if f in ("amount", "deduction"):
                v = f"{v:.2f} {currency}" if v is not None else "-"
                total += r[f] or 0
            else:
                v = v or "-"
            tds += f"<td>{v}</td>"
        tbody += f"<tr>{tds}</tr>"
    if not tbody:
        tbody = f"<tr><td colspan='{len(headers)}' style='text-align:center;color:#888;padding:24px'>{_('no_data')}</td></tr>"
    total_label = _("leave_total_deduction") if kind == "leave" else _("total")
    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><title>{gym} - {title}</title>
<style>
  body {{ font-family:'Segoe UI',Tahoma,Arial,sans-serif; margin:40px; color:#1c1c2e; }}
  .header {{ text-align:center; border-bottom:3px solid #0f172a; padding-bottom:16px; margin-bottom:24px; }}
  .header h1 {{ margin:0; color:#0f172a; font-size:26px; }}
  .header p {{ color:#64748b; margin:4px 0 0; }}
  .meta {{ display:flex; gap:12px; flex-wrap:wrap; margin:14px 0; }}
  .meta div {{ background:#0f172a; color:#fff; padding:10px 16px; border-radius:10px; font-size:14px; }}
  table {{ width:100%; border-collapse:collapse; margin-top:8px; }}
  th {{ background:#0f172a; color:#fff; padding:10px; font-size:13px; }}
  td {{ border-bottom:1px solid #e2e8f0; padding:9px; font-size:13px; text-align:center; }}
  .footer {{ margin-top:20px; color:#94a3b8; font-size:12px; text-align:center; }}
</style>
</head>
<body>
  <div class="header"><h1>🏋️ {gym}</h1><p>{title} — {employee['full_name']}</p></div>
  <div class="meta"><div>{_('payroll_month')}: <b>{month_label}</b></div><div>{total_label}: <b>{total:.2f} {currency}</b></div><div>{now}</div></div>
  <table><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>
  <div class="footer">{gym} © {now.split()[0].split('-')[0]} — تصميم عوني جرادات 0796161401</div>
</body>
</html>"""
    out_dir = output_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "invoices")
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_month = (month_label or "all").replace("/", "-")
    path = os.path.join(out_dir, f"emp_{kind}_{employee_id}_{safe_month}_{stamp}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def passport_html(member, payments):
    """Build an HTML passport/profile for a member with payment history."""
    currency = db.get_setting("currency", "")
    gym = db.get_setting("gym_name", "هايدروجين جم")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    name = member["full_name"]
    code = member.get("code") or "-"
    phone = member.get("phone") or "-"
    email = member.get("email") or "-"
    join_date = member.get("join_date") or "-"
    active = _("active") if member["is_active"] else _("inactive")
    status_color = "#22c55e" if member["is_active"] else "#64748b"

    # payments table rows
    pay_rows = ""
    if payments:
        for r in payments:
            pay_rows += (
                f"<tr><td>{r['payment_date']}</td><td style='text-align:right'>{r['amount']:.2f} {currency}</td>"
                f"<td>{r['payment_method'] or '-'}</td><td>{r.get('reference_number') or '-'}</td></tr>"
            )
    else:
        pay_rows = f"<tr><td colspan='4' style='text-align:center; color:#94a3b8'>{ _('no_data')}</td></tr>"

    # subscriptions timeline
    subs = db.fetch_all(
        "SELECT s.*, p.name AS plan_name FROM subscriptions s "
        "LEFT JOIN plans p ON s.plan_id = p.id WHERE member_id=? ORDER BY start_date DESC",
        (member["id"],),
    )
    sub_rows = ""
    if subs:
        for s in subs:
            sub_rows += (
                f"<tr><td>{s['start_date']}</td><td>{s['end_date']}</td>"
                f"<td>{s.get('plan_name') or '-'}</td><td style='text-align:right'>{s['price_paid']:.2f} {currency}</td>"
                f"<td>{_('active') if s.get('status') == 'active' else _('expired')}</td></tr>"
            )
    else:
        sub_rows = f"<tr><td colspan='5' style='text-align:center; color:#94a3b8'>{ _('no_data')}</td></tr>"

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>ملف العضو - {gym}</title>
<style>
  body {{ font-family:'Segoe UI',Tahoma,Arial,sans-serif; margin:40px; color:#1c1c2e; }}
  .header {{ text-align:center; border-bottom:3px solid #0f172a; padding-bottom:16px; margin-bottom:24px; }}
  .header h1 {{ margin:0; color:#0f172a; font-size:26px; }}
  .header p {{ color:#64748b; margin:4px 0 0; }}
  .section {{ margin-bottom:28px; }}
  .section h2 {{ color:#0f172a; font-size:18px; border-bottom:1px solid #e2e8f0; padding-bottom:6px; }}
  table {{ width:100%; border-collapse:collapse; margin-top:10px; }}
  th {{ background:#0f172a; color:#fff; padding:8px; font-size:12px; text-align:center; }}
  td {{ border:1px solid #e2e8f0; padding:8px; font-size:13px; }}
  td.num {{ text-align:right; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:bold; }}
  .footer {{ margin-top:36px; border-top:1px solid #e2e8f0; padding-top:12px; text-align:center; color:#94a3b8; font-size:12px; }}
</style>
</head>
<body>
  <div class="header">
    <h1>🏋️ {gym}</h1>
    <p>ملف العضو</p>
  </div>

  <div class="section">
    <h2>🧾 البيانات الشخصية</h2>
    <table>
      <tr><th>الاسم</th><th>الكود</th><th>الهاتف</th><th>البريد</th><th>تاريخ الانضمام</th><th>الحالة</th></tr>
      <tr>
        <td>{name}</td><td>{code}</td><td>{phone}</td><td>{email}</td><td>{join_date}</td>
        <td><span class="badge" style="background:{status_color}20;color:{status_color}">{active}</span></td>
      </tr>
    </table>
  </div>

  <div class="section">
    <h2>📅 تاريخ الاشتراكات</h2>
    <table>
      <tr><th>بداية</th><th>نهاية</th><th>الخطة</th><th class="num">السعر</th><th>الحالة</th></tr>
      {sub_rows}
    </table>
  </div>

  <div class="section">
    <h2>💳 جميع الدفعات</h2>
    <table>
      <tr><th>التاريخ</th><th class="num">المبلغ</th><th>طريقة الدفع</th><th>المرجع</th></tr>
      {pay_rows}
    </table>
  </div>

  <div class="footer">
    {gym} © {now.split()[0].split('-')[0]} — تصميم عوني جرادات 0796161401
  </div>
</body>
</html>"""


def open_passport_html(member, payments):
    """Open the member passport HTML in the default browser (like reports)."""
    import tempfile
    import webbrowser
    html = passport_html(member, payments)
    if not html:
        return None
    fd, path = tempfile.mkstemp(suffix=".html", prefix="passport_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open("file://" + path)
    return path

def print_passport_pdf(member, payments, output_dir=None):
    """Write the passport HTML to the invoices dir and open it in the browser. Returns path or None."""
    html = passport_html(member, payments)
    if not html:
        return None
    out_dir = output_dir or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "invoices")
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(out_dir, f"passport_{member['id']}_{stamp}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open("file://" + path)
    return path


def print_invoice_pdf(payment_id, output_dir=None):
    """Write the invoice HTML to the invoices dir and open it in the browser. Returns path or None."""
    payment = db.fetch_one("SELECT * FROM payments WHERE id=?", (payment_id,))
    if not payment:
        return None
    html = invoice_html(payment)
    if not html:
        return None
    out_dir = output_dir or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "invoices")
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(out_dir, f"invoice_{payment['id']}_{stamp}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open("file://" + path)
    return path


def receipt_html(sub):
    """Build a simple RTL printable receipt for a subscription."""
    gym = db.get_setting("gym_name", "\u0647\u0627\u064a\u062f\u0631\u0648\u062c\u064a\u0646 \u062c\u0645")
    rec = db.fetch_one(
        """SELECT s.*, m.full_name, m.phone, m.code, p.name AS plan_name, p.duration_days
           FROM subscriptions s
           JOIN members m ON s.member_id = m.id
           JOIN plans p ON s.plan_id = p.id
           WHERE s.id=?""",
        (sub["id"],),
    )
    if not rec:
        return None
    currency = db.get_setting("currency", "")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>{gym} - {_('receipt')}</title>
<style>
  body {{ font-family:'Segoe UI',Tahoma,Arial,sans-serif; margin:40px; color:#1c1c2e; }}
  .header {{ text-align:center; border-bottom:3px solid #0f172a; padding-bottom:16px; margin-bottom:24px; }}
  .header h1 {{ margin:0; color:#0f172a; font-size:26px; }}
  .header p {{ color:#64748b; margin:4px 0 0; }}
  .meta {{ display:flex; justify-content:space-between; margin-bottom:24px; font-size:14px; }}
  .meta div {{ background:#f8fafc; padding:10px 16px; border-radius:8px; }}
  .amount {{ text-align:center; margin:28px 0; }}
  .amount .num {{ font-size:42px; font-weight:bold; color:#0f172a; }}
  .amount .cur {{ font-size:22px; color:#64748b; }}
  table {{ width:100%; border-collapse:collapse; margin:16px 0; }}
  th {{ background:#0f172a; color:#fff; padding:10px; font-size:13px; }}
  td {{ border:1px solid #e2e8f0; padding:10px; font-size:14px; text-align:center; }}
  .footer {{ margin-top:36px; border-top:1px solid #e2e8f0; padding-top:12px; text-align:center; color:#94a3b8; font-size:12px; }}
</style>
</head>
<body>
  <div class="header">
    <h1>{gym}</h1>
    <p>{_('receipt')}</p>
  </div>
  <div class="meta">
    <div>{_('receipt_no')}: <b>#{rec['id']}</b></div>
    <div>{_('date')}: <b>{now}</b></div>
    <div>{_('member_code')}: <b>{rec['code']}</b></div>
  </div>
  <table>
    <tr><th>{_('member')}</th><th>{_('phone')}</th><th>{_('plan_name')}</th><th>{_('payment_method')}</th></tr>
    <tr>
      <td>{rec['full_name']}</td>
      <td dir="ltr">{rec['phone']}</td>
      <td>{rec['plan_name']} ({rec['duration_days']} {_('days')})</td>
      <td>{rec['payment_method']}</td>
    </tr>
  </table>
  <table>
    <tr><th>{_('start_date')}</th><th>{_('end_date')}</th></tr>
    <tr><td>{rec['start_date']}</td><td>{rec['end_date']}</td></tr>
  </table>
  <div class="amount">
    <span class="num">{rec['price_paid']:.2f}</span> <span class="cur">{currency}</span>
  </div>
  <div class="footer">{_('thanks_msg')}</div>
</body>
</html>"""


def print_receipt_pdf(sub, output_dir=None):
    """Write the receipt HTML to the invoices dir. Returns path or None."""
    html = receipt_html(sub)
    if not html:
        return None
    out_dir = output_dir or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "invoices")
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(out_dir, f"receipt_{sub['id']}_{stamp}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path



def _method_label(method):
    m = (method or "").strip()
    if m == "\u0646\u0642\u062f\u064a":
        return _("cash")
    if m == "\u0628\u0637\u0627\u0642\u0629":
        return _("card")
    if m == "\u062a\u062d\u0648\u064a\u0644 \u0628\u0646\u0643\u064a":
        return _("bank_transfer")
    return m or _("other")


def daily_statement_html(day):
    """Build an RTL printable HTML daily statement for a given date."""
    gym = db.get_setting("gym_name", "\u0647\u0627\u064a\u062f\u0631\u0648\u062c\u064a\u0646 \u062c\u0645")
    currency = db.get_setting("currency", "")
    subs = db.fetch_all(
        """SELECT p.amount, p.payment_method, m.full_name, pm.name AS plan_name
           FROM payments p
           JOIN members m ON p.member_id = m.id
           LEFT JOIN subscriptions s ON p.subscription_id = s.id
           LEFT JOIN plans pm ON s.plan_id = pm.id
           WHERE p.payment_date = ? ORDER BY p.id""",
        (day,),
    )
    exps = db.fetch_all(
        "SELECT description, category, amount FROM expenses WHERE expense_date = ? ORDER BY id",
        (day,),
    )
    subs_total = sum(r["amount"] for r in subs)
    exp_total = sum(r["amount"] for r in exps)
    net = subs_total - exp_total

    subs_rows = "".join(
        "<tr><td>{}</td><td>{}</td><td>{:.2f}</td><td>{}</td></tr>".format(
            r["full_name"], r["plan_name"] or "-", r["amount"], _method_label(r["payment_method"])
        )
        for r in subs
    )
    methods = {}
    for r in subs:
        m = _method_label(r["payment_method"])
        cur = methods.setdefault(m, [0, 0.0])
        cur[0] += 1
        cur[1] += r["amount"]
    method_rows = "".join(
        "<tr><td>{}</td><td>{}</td><td>{:.2f}</td></tr>".format(m, c, s)
        for m, (c, s) in methods.items()
    )
    exp_rows = "".join(
        "<tr><td>{}</td><td>{}</td><td>{:.2f}</td></tr>".format(
            r["description"], r["category"] or "-", r["amount"]
        )
        for r in exps
    )

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>{gym} - {_("daily_statement")}</title>
<style>
  body {{ font-family:'Segoe UI',Tahoma,Arial,sans-serif; margin:40px; color:#1c1c2e; }}
  .header {{ text-align:center; border-bottom:3px solid #0f172a; padding-bottom:16px; margin-bottom:24px; }}
  .header h1 {{ margin:0; color:#0f172a; font-size:26px; }}
  .header p {{ color:#64748b; margin:4px 0 0; }}
  h2 {{ color:#0f172a; font-size:18px; margin:26px 0 8px; border-bottom:2px solid #e2e8f0; padding-bottom:6px; }}
  table {{ width:100%; border-collapse:collapse; margin:10px 0; }}
  th {{ background:#0f172a; color:#fff; padding:10px; font-size:13px; }}
  td {{ border:1px solid #e2e8f0; padding:10px; font-size:14px; text-align:center; }}
  tr.total td {{ background:#f1f5f9; font-weight:bold; font-size:15px; }}
  .net {{ text-align:center; margin:28px 0; padding:18px; background:#f8fafc; border:2px solid #0f172a; border-radius:8px; }}
  .net .lbl {{ font-size:16px; color:#64748b; }}
  .net .num {{ font-size:34px; font-weight:bold; color:#0f172a; }}
  .net .cur {{ font-size:20px; color:#64748b; }}
  .footer {{ margin-top:36px; border-top:1px solid #e2e8f0; padding-top:12px; text-align:center; color:#94a3b8; font-size:12px; }}
</style>
</head>
<body>
  <div class="header">
    <h1>{gym}</h1>
    <p>{_("daily_statement")} - {day}</p>
  </div>

  <h2>{_("paid_subscriptions")}</h2>
  <table>
    <tr><th>{_("member")}</th><th>{_("plan")}</th><th>{_("amount")}</th><th>{_("payment_method")}</th></tr>
    {subs_rows}
    <tr class="total"><td colspan="3">{_("total")}</td><td>{subs_total:.2f} {currency}</td></tr>
  </table>

  <h2>{_("payment_breakdown")}</h2>
  <table>
    <tr><th>{_("payment_method")}</th><th>{_("count")}</th><th>{_("amount")}</th></tr>
    {method_rows}
    <tr class="total"><td colspan="2">{_("total")}</td><td>{subs_total:.2f} {currency}</td></tr>
  </table>

  <h2>{_("expenses")}</h2>
  <table>
    <tr><th>{_("description")}</th><th>{_("category")}</th><th>{_("amount")}</th></tr>
    {exp_rows}
    <tr class="total"><td colspan="2">{_("total")}</td><td>{exp_total:.2f} {currency}</td></tr>
  </table>

  <div class="net">
    <div class="lbl">{_("net")}</div>
    <div><span class="num">{net:.2f}</span> <span class="cur">{currency}</span></div>
  </div>

  <div class="footer">{gym} - {_("daily_statement")} - {day}</div>
</body>
</html>"""


def print_daily_statement(day, output_dir=None):
    """Write the daily statement HTML to the invoices dir and open it in the browser. Returns path or None."""
    html = daily_statement_html(day)
    if not html:
        return None
    out_dir = output_dir or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "invoices")
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(out_dir, f"daily_statement_{day}_{stamp}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open("file://" + path)
    return path
