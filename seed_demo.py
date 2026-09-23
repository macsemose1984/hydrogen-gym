"""بذر بيانات تجريبية — تشغيل: python seed_demo.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import init_database
import app.database as db

init_database()

if db.fetch_one("SELECT COUNT(*) AS c FROM members")["c"] > 0:
    print("توجد بيانات مسبقاً — لم تتم إضافة بيانات تجريبية.")
    sys.exit(0)

plans = [
    ("شهري", 30, 25, 0, "وصول يومي كامل لمدة 30 يوماً"),
    ("ثلاثة أشهر", 90, 65, 0, "وصول يومي كامل لمدة 3 أشهر"),
    ("سنوي", 365, 220, 0, "وصول يومي كامل لمدة سنة"),
    ("10 جلسات", 60, 30, 10, "10 جلسات تدريب مفتوحة"),
]
for name, days, price, sess, desc in plans:
    db.execute("INSERT INTO plans (name, duration_days, price, sessions, description) VALUES (?,?,?,?,?)",
               (name, days, price, sess, desc))

demo = [
    ("يتف", "أحمد محمد", "0791234567", "ذكر", "2026-01-15"),
]
for i, (code, name, phone, gender, joined) in enumerate(demo, start=1):
    mid = db.execute("INSERT INTO members (code, full_name, phone, gender, join_date) VALUES (?,?,?,?,?)",
                     (f"HG-{i:04d}", name, phone, gender, joined))

m1 = db.fetch_one("SELECT id FROM members LIMIT 1")
p1 = db.fetch_one("SELECT * FROM plans LIMIT 1")
db.execute("INSERT INTO subscriptions (member_id, plan_id, start_date, end_date, price_paid, payment_method, status) VALUES (?,?,?,?,?,?,?)",
           (m1["id"], p1["id"], "2026-07-01", "2026-07-31", p1["price"], "cash", "active"))
print("تمت إضافة بيانات تجريبية بنجاح ✅")