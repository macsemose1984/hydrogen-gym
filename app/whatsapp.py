import webbrowser
import urllib.parse
from datetime import datetime, timedelta

import app.database as db


def normalize_phone(phone):
    if not phone:
        return ""
    digits = "".join(ch for ch in str(phone).strip() if ch.isdigit() or ch == "+")
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    if digits.startswith("0") and not digits.startswith("00"):
        digits = "+962" + digits[1:]
    return digits


def build_link(phone, message=""):
    p = normalize_phone(phone)
    if not p:
        return None
    url = f"https://wa.me/{p}"
    if message:
        url += "?text=" + urllib.parse.quote(message)
    return url


def open_whatsapp(phone, message=""):
    url = build_link(phone, message)
    if url:
        webbrowser.open(url)
    return url is not None


def log_message(member_id, phone, template, message, status="sent"):
    return db.execute(
        "INSERT INTO message_log (member_id, phone, template, message, status) "
        "VALUES (?,?,?,?,?)",
        (member_id, phone, template, message, status),
    )


def build_message(template, member, plan=None, end_date=None, due=None):
    gym_name = db.get_setting("gym_name", "هايدروجين جم")
    currency = db.get_setting("currency", "")
    name = member["full_name"] if isinstance(member, dict) else str(member)
    end_fmt = end_date or (plan["end_date"] if plan and "end_date" in plan else "")

    texts = {
        "welcome": (
            f"أهلاً وسهلاً بك {name} في {gym_name} 🏋️\n"
            "نتمنى لك رحلة تدريب موفقة، يسعدنا خدمتك دائماً."
        ),
        "renew": (
            f"عزيزي {name}، نود تذكيرك بأن اشتراكك في {gym_name} سينتهي بتاريخ {end_fmt}.\n"
            "يرجى تجديد اشتراكك للاستمرار في التدريب 💪"
        ),
        "invoice": (
            f"فاتورة اشتراك - {gym_name}\n"
            f"العضو: {name}\n"
            f"المبلغ: {due} {currency}\n"
            "شكراً لثقتكم بنا 🙏"
        ),
        "promo": (
            f"عرض خاص في {gym_name} 🎉\n"
            "صفقات واشتراكات بمزايا مميزة، سارع بالاستفادة من العروض!"
        ),
    }
    return texts.get(template, "")


def list_expired():
    rows = db.fetch_all(
        """SELECT s.id, s.end_date, s.remaining_sessions, p.name AS plan_name,
                  m.id AS member_id, m.full_name, m.phone
           FROM subscriptions s
           JOIN members m ON s.member_id = m.id
           JOIN plans p ON s.plan_id = p.id
           WHERE s.status='active' AND m.phone != ''
             AND s.end_date < ?""",
        (db.today(),),
    )
    return rows


def list_expiring(days=3):
    end_limit = db.add_days(db.today(), days)
    rows = db.fetch_all(
        """SELECT s.id, s.end_date, s.remaining_sessions, p.name AS plan_name,
                  m.id AS member_id, m.full_name, m.phone
           FROM subscriptions s
           JOIN members m ON s.member_id = m.id
           JOIN plans p ON s.plan_id = p.id
           WHERE s.status='active' AND m.phone != ''
             AND s.end_date BETWEEN ? AND ?""",
        (db.today(), end_limit),
    )
    return rows


def list_all_with_phone():
    return db.fetch_all(
        "SELECT id, full_name, phone FROM members WHERE phone != '' AND phone IS NOT NULL"
    )