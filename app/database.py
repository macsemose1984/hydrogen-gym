import json
import os
import sqlite3
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "hydrogen.db")


def _ensure_dir():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_connection():
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def _execute(query, params=None, fetch=None):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params or ())
        result = None
        if fetch == "one":
            result = cur.fetchone()
            result = dict(result) if result else None
        elif fetch == "all":
            result = [dict(r) for r in cur.fetchall()]
        elif fetch == "lastid":
            result = cur.lastrowid
        conn.commit()
        return result
    finally:
        conn.close()


def fetch_one(query, params=None):
    return _execute(query, params, "one")


def fetch_all(query, params=None):
    return _execute(query, params, "all")


def execute(query, params=None):
    return _execute(query, params, "lastid")


def execute_many(query, rows):
    """Execute a query for many parameter rows with a single connection."""
    if not rows:
        return 0
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.executemany(query, rows)
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def today():
    return datetime.now().strftime("%Y-%m-%d")


def add_days(date_str, days):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return (d + timedelta(days=days)).strftime("%Y-%m-%d")


def init_database():
    _ensure_dir()
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'admin',
        full_name TEXT NOT NULL,
        language TEXT DEFAULT 'ar',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        duration_days INTEGER NOT NULL,
        price REAL NOT NULL,
        sessions INTEGER DEFAULT 0,
        description TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        address TEXT,
        gender TEXT,
        birth_date TEXT,
        photo_path TEXT,
        fingerprint_id TEXT,
        notes TEXT,
        join_date TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        plan_id INTEGER NOT NULL,
        coach_id INTEGER,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        remaining_sessions INTEGER DEFAULT 0,
        price_paid REAL NOT NULL,
        payment_method TEXT DEFAULT 'cash',
        status TEXT DEFAULT 'active',
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (member_id) REFERENCES members(id),
        FOREIGN KEY (plan_id) REFERENCES plans(id)
    );

    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        subscription_id INTEGER,
        amount REAL NOT NULL,
        payment_date TEXT NOT NULL,
        payment_method TEXT DEFAULT 'cash',
        reference_number TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (member_id) REFERENCES members(id),
        FOREIGN KEY (subscription_id) REFERENCES subscriptions(id)
    );

    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        check_in TEXT NOT NULL,
        check_out TEXT,
        method TEXT DEFAULT 'manual',
        FOREIGN KEY (member_id) REFERENCES members(id)
    );

    CREATE TABLE IF NOT EXISTS device_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uid INTEGER,
        user_id TEXT,
        name TEXT,
        timestamp TEXT,
        UNIQUE (uid, timestamp)
    );

    CREATE INDEX IF NOT EXISTS idx_dm_timestamp ON device_movements(timestamp);
    CREATE INDEX IF NOT EXISTS idx_dm_user ON device_movements(user_id);

    CREATE TABLE IF NOT EXISTS message_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER,
        phone TEXT,
        template TEXT,
        message TEXT,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'sent'
    );

    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expense_date TEXT NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS coaches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        phone TEXT,
        specialty TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        full_name TEXT NOT NULL,
        phone TEXT DEFAULT '',
        position TEXT DEFAULT '',
        monthly_salary REAL DEFAULT 0,
        hire_date TEXT,
        notes TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS employee_payrolls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        payment_date TEXT NOT NULL,
        salary_month TEXT DEFAULT '',
        amount REAL NOT NULL,
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    );

    CREATE TABLE IF NOT EXISTS employee_advances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        advance_date TEXT NOT NULL,
        amount REAL NOT NULL,
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    );

    CREATE TABLE IF NOT EXISTS employee_leaves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        leave_type TEXT DEFAULT '',
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        deduction REAL DEFAULT 0,
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    );

    CREATE TABLE IF NOT EXISTS employee_overtime (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        overtime_date TEXT NOT NULL,
        hours REAL DEFAULT 0,
        amount REAL NOT NULL,
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    );

    CREATE TABLE IF NOT EXISTS trash (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name TEXT NOT NULL,
        record_id INTEGER,
        snapshot TEXT NOT NULL,
        deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS user_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        action TEXT NOT NULL,
        target_type TEXT DEFAULT '',
        target_name TEXT DEFAULT '',
        details TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_user_actions_created ON user_actions(created_at);
    CREATE INDEX IF NOT EXISTS idx_user_actions_user ON user_actions(username);

    -- Performance indexes for 300+ members
    CREATE INDEX IF NOT EXISTS idx_sub_end ON subscriptions(end_date);
    CREATE INDEX IF NOT EXISTS idx_sub_member ON subscriptions(member_id);
    CREATE INDEX IF NOT EXISTS idx_sub_plan ON subscriptions(plan_id);
    CREATE INDEX IF NOT EXISTS idx_att_checkin ON attendance(check_in);
    CREATE INDEX IF NOT EXISTS idx_att_member ON attendance(member_id);
    CREATE INDEX IF NOT EXISTS idx_pay_date ON payments(payment_date);
    CREATE INDEX IF NOT EXISTS idx_pay_member ON payments(member_id);
    CREATE INDEX IF NOT EXISTS idx_members_name ON members(full_name);
    """)

    # migration: add coach_id to existing subscriptions tables
    sub_cols = [row[1] for row in cur.execute("PRAGMA table_info(subscriptions)").fetchall()]
    if "coach_id" not in sub_cols:
        cur.execute("ALTER TABLE subscriptions ADD COLUMN coach_id INTEGER")

    mem_cols = [row[1] for row in cur.execute("PRAGMA table_info(members)").fetchall()]
    if "coach_id" not in mem_cols:
        cur.execute("ALTER TABLE members ADD COLUMN coach_id INTEGER")

    leave_cols = [row[1] for row in cur.execute("PRAGMA table_info(employee_leaves)").fetchall()]
    if "deduction" not in leave_cols:
        cur.execute("ALTER TABLE employee_leaves ADD COLUMN deduction REAL DEFAULT 0")

    if cur.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO users (username, password, role, full_name) VALUES (?,?,?,?)",
            ("admin", "admin123", "admin", "المدير"),
        )

    defaults = {
        "gym_name": "هايدروجين جم",
        "gym_phone": "",
        "currency": "د.أ",
        "wa_daily_reminder": "1",
        "wa_days_before": "3",
        "device_autosync": "1",
        "device_autosync_interval": "1",
    }
    for k, v in defaults.items():
        cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?,?)", (k, v))

    # device_autosync stays as configured (default ON) - user preference

    conn.commit()
    conn.close()


def get_setting(key, default=""):
    row = fetch_one("SELECT value FROM settings WHERE key=?", (key,))
    return row["value"] if row else default


def set_setting(key, value):
    execute(
        "INSERT INTO settings (key, value) VALUES (?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def get_latest_subscription(member_id):
    return fetch_one(
        """SELECT s.*, p.name AS plan_name, p.price AS plan_price
           FROM subscriptions s JOIN plans p ON s.plan_id = p.id
           WHERE s.member_id = ?
           ORDER BY s.end_date DESC LIMIT 1""",
        (member_id,),
    )


def delete_member(mid):
    """حذف عضو مع كل ما يرتبط به (دفعات، اشتراكات، حضور، رسائل)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM payments WHERE member_id=? OR subscription_id IN "
            "(SELECT id FROM subscriptions WHERE member_id=?)",
            (mid, mid),
        )
        cur.execute("DELETE FROM subscriptions WHERE member_id=?", (mid,))
        cur.execute("DELETE FROM attendance WHERE member_id=?", (mid,))
        cur.execute("DELETE FROM message_log WHERE member_id=?", (mid,))
        cur.execute("DELETE FROM members WHERE id=?", (mid,))
        conn.commit()
    finally:
        conn.close()


def delete_subscription(sid):
    """حذف اشتراك مع دفعاته المرتبطة."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM payments WHERE subscription_id=?", (sid,))
        cur.execute("DELETE FROM subscriptions WHERE id=?", (sid,))
        conn.commit()
    finally:
        conn.close()


def delete_plan(pid):
    """حذف خطة مع الاشتراكات والدفعات المرتبطة بها."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM subscriptions WHERE plan_id=?", (pid,))
        for r in cur.fetchall():
            cur.execute("DELETE FROM payments WHERE subscription_id=?", (r["id"],))
            cur.execute("DELETE FROM subscriptions WHERE id=?", (r["id"],))
        cur.execute("DELETE FROM plans WHERE id=?", (pid,))
        conn.commit()
    finally:
        conn.close()


def toggle_employee(eid):
    """تبديل حالة الموظف (نشط/غير نشط)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT is_active FROM employees WHERE id=?", (eid,))
        row = cur.fetchone()
        if not row:
            return False
        new_status = 0 if row[0] else 1
        cur.execute("UPDATE employees SET is_active=? WHERE id=?", (new_status, eid))
        conn.commit()
        return new_status == 1
    finally:
        conn.close()


def delete_employee(eid):
    """حذف موظف مع كل السجلات المرتبطة (رواتب، سلف، إجازات، ساعات إضافية)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM employee_payrolls WHERE employee_id=?", (eid,))
        cur.execute("DELETE FROM employee_advances WHERE employee_id=?", (eid,))
        cur.execute("DELETE FROM employee_leaves WHERE employee_id=?", (eid,))
        cur.execute("DELETE FROM employee_overtime WHERE employee_id=?", (eid,))
        cur.execute("DELETE FROM employees WHERE id=?", (eid,))
        conn.commit()
    finally:
        conn.close()


# ---------------- trash / recycle bin ----------------

def move_to_trash(table_name, record_id):
    """Capture a full snapshot (parent + children) and hard-delete it.

    Supported: members, subscriptions, plans, payments.
    Returns the trash id or None.
    """
    snap = _snapshot(table_name, record_id)
    if snap is None:
        return None
    if table_name == "members":
        delete_member(record_id)
    elif table_name == "subscriptions":
        delete_subscription(record_id)
    elif table_name == "plans":
        delete_plan(record_id)
    elif table_name == "payments":
        execute("DELETE FROM payments WHERE id=?", (record_id,))
    return execute(
        "INSERT INTO trash (table_name, record_id, snapshot) VALUES (?,?,?)",
        (table_name, record_id, json.dumps(snap, ensure_ascii=False)),
    )


def _snapshot(table_name, record_id):
    if table_name == "members":
        member = fetch_one("SELECT * FROM members WHERE id=?", (record_id,))
        if not member:
            return None
        return {
            "member": member,
            "subscriptions": fetch_all(
                "SELECT * FROM subscriptions WHERE member_id=?", (record_id,)),
            "payments": fetch_all(
                "SELECT * FROM payments WHERE member_id=?", (record_id,)),
            "attendance": fetch_all(
                "SELECT * FROM attendance WHERE member_id=?", (record_id,)),
            "message_log": fetch_all(
                "SELECT * FROM message_log WHERE member_id=?", (record_id,)),
        }
    if table_name == "subscriptions":
        sub = fetch_one("SELECT * FROM subscriptions WHERE id=?", (record_id,))
        if not sub:
            return None
        return {
            "subscription": sub,
            "payments": fetch_all(
                "SELECT * FROM payments WHERE subscription_id=?", (record_id,)),
        }
    if table_name == "plans":
        plan = fetch_one("SELECT * FROM plans WHERE id=?", (record_id,))
        if not plan:
            return None
        subs = fetch_all("SELECT * FROM subscriptions WHERE plan_id=?", (record_id,))
        payments = []
        for s in subs:
            payments += fetch_all("SELECT * FROM payments WHERE subscription_id=?", (s["id"],))
        return {"plan": plan, "subscriptions": subs, "payments": payments}
    if table_name == "payments":
        pay = fetch_one("SELECT * FROM payments WHERE id=?", (record_id,))
        if not pay:
            return None
        return {"payment": pay}
    return None


def restore_from_trash(trash_id):
    """Restore a trashed record and its children. Returns True on success."""
    row = fetch_one("SELECT * FROM trash WHERE id=?", (trash_id,))
    if not row:
        return False
    snap = json.loads(row["snapshot"])
    conn = get_connection()
    try:
        cur = conn.cursor()
        if "member" in snap:
            m = snap["member"]
            _reinsert(cur, "members", m)
            mid = cur.lastrowid
            sub_map = {}
            for s in snap.get("subscriptions", []):
                _reinsert(cur, "subscriptions", s, member_id=mid)
                sub_map[s["id"]] = cur.lastrowid
            for p in snap.get("payments", []):
                _reinsert(cur, "payments", p, member_id=mid,
                          subscription_id=sub_map.get(p.get("subscription_id")))
            for a in snap.get("attendance", []):
                _reinsert(cur, "attendance", a, member_id=mid)
            for lg in snap.get("message_log", []):
                _reinsert(cur, "message_log", lg, member_id=mid)
        elif "subscription" in snap:
            s = snap["subscription"]
            _reinsert(cur, "subscriptions", s)
            sid = cur.lastrowid
            for p in snap.get("payments", []):
                _reinsert(cur, "payments", p, subscription_id=sid)
        elif "plan" in snap:
            pl = snap["plan"]
            _reinsert(cur, "plans", pl)
            pid = cur.lastrowid
            sub_map = {}
            for s in snap.get("subscriptions", []):
                _reinsert(cur, "subscriptions", s, plan_id=pid)
                sub_map[s["id"]] = cur.lastrowid
            for p in snap.get("payments", []):
                _reinsert(cur, "payments", p, subscription_id=sub_map.get(p.get("subscription_id")))
        elif "payment" in snap:
            _reinsert(cur, "payments", snap["payment"])
        cur.execute("DELETE FROM trash WHERE id=?", (trash_id,))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def _reinsert(cur, table, record, **overrides):
    """Insert a row ignoring its autoincrement id; returns new id via lastrowid.

    `overrides` replaces column values (e.g. remapped foreign keys).
    """
    row = dict(record)
    row.pop("id", None)
    row.update(overrides)
    cols = list(row.keys())
    vals = [row[c] for c in cols]
    q = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})"
    cur.execute(q, vals)


def list_trash():
    """Return trash entries with a human label for display."""
    rows = fetch_all("SELECT * FROM trash ORDER BY id DESC")
    out = []
    for r in rows:
        snap = json.loads(r["snapshot"])
        label = ""
        if "member" in snap:
            label = snap["member"].get("full_name", "")
        elif "subscription" in snap:
            label = f"اشتراك #{snap['subscription']['id']}"
        elif "plan" in snap:
            label = snap["plan"].get("name", "")
        elif "payment" in snap:
            label = f"دفعة #{snap['payment']['id']}"
        out.append({
            "id": r["id"],
            "table_name": r["table_name"],
            "label": label,
            "deleted_at": str(r["deleted_at"])[:16],
        })
    return out


def delete_from_trash(trash_id):
    execute("DELETE FROM trash WHERE id=?", (trash_id,))


def clear_trash():
    execute("DELETE FROM trash")


# ---------------- user actions log (حركات اليوزر) ----------------

_current_user = "admin"

def set_current_user(username):
    global _current_user
    _current_user = username or "admin"

def get_current_user():
    return _current_user

def log_user_action(action, target_type="", target_name="", details=""):
    """سجل حركة اليوزر: إضافة/تعديل/حذف عضو/اشتراك/دفعة/موظف..."""
    try:
        username = get_current_user()
        execute(
            "INSERT INTO user_actions (username, action, target_type, target_name, details) VALUES (?,?,?,?,?)",
            (username, action, target_type, target_name, details),
        )
    except Exception:
        pass

def fetch_user_actions_24h():
    return fetch_all(
        "SELECT * FROM user_actions WHERE created_at >= datetime('now', '-1 day') ORDER BY created_at DESC"
    )
