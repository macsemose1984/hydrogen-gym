"""ZKTeco attendance-device integration backed by the supported pyzk protocol."""
from datetime import datetime
import time


class ZKTecoDevice:
    """Small adapter that keeps the GUI independent from the pyzk API."""

    def __init__(self, ip="192.168.1.201", port=4370, timeout=15):
        self.ip, self.port, self.timeout = ip, int(port), timeout
        self.connection = None
        self.connected = False
        self.error = ""

    def connect(self):
        """Try connecting with both UDP and TCP modes."""
        self.disconnect()
        for force_udp in (False, True):
            try:
                from zk import ZK
                device = ZK(self.ip, port=self.port, timeout=self.timeout, force_udp=force_udp)
                self.connection = device.connect()
                if self.connection:
                    self.connected = True
                    return True
            except Exception as exc:
                self.error = f"{'UDP' if force_udp else 'TCP'}: {exc}"
        self.connection = None
        self.connected = False
        return False

    def disconnect(self):
        if self.connection:
            try:
                self.connection.enable_device()
            except Exception:
                pass
            try:
                self.connection.disconnect()
            except Exception:
                pass
        self.connection = None
        self.connected = False

    def _safe_operation(self, func):
        """Execute a function with device disabled/enabled for safety."""
        if not self.connection:
            return None
        try:
            self.connection.disable_device()
            result = func()
            self.connection.enable_device()
            return result
        except Exception as exc:
            self.error = str(exc)
            try:
                self.connection.enable_device()
            except Exception:
                pass
            return None

    def get_users(self):
        def _get():
            return [
                {"uid": int(user.uid), "user_id": str(user.user_id), "name": user.name or ""}
                for user in self.connection.get_users()
            ]
        result = self._safe_operation(_get)
        return result if result is not None else []

    def read_attendance(self):
        def _read():
            return [
                {"uid": int(record.uid), "user_id": str(record.user_id), "timestamp": record.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "state": record.status}
                for record in self.connection.get_attendance()
            ]
        result = self._safe_operation(_read)
        return result if result is not None else []

    def test(self):
        if not self.connect():
            return False, f"Connection failed to {self.ip}:{self.port} - {self.error}"
        try:
            info = {
                "serial": self._safe_operation(lambda: self.connection.get_serialnumber()) or "",
                "users": len(self.get_users()),
                "attendance": len(self.read_attendance()),
            }
            if self.error:
                return False, self.error
            return True, info
        except Exception as exc:
            self.error = str(exc)
            return False, self.error
        finally:
            self.disconnect()


def _norm_fp(s):
    """Normalize a fingerprint id for comparison (trim, drop leading zeros)."""
    s = (s or "").strip()
    if s.isdigit():
        try:
            return str(int(s))
        except ValueError:
            return s
    return s


def _member_fp_map():
    import app.database as db
    members = db.fetch_all(
        "SELECT id, full_name, fingerprint_id FROM members "
        "WHERE fingerprint_id IS NOT NULL AND fingerprint_id != ''"
    )
    mapped = {}
    for member in members:
        mapped.setdefault(_norm_fp(member["fingerprint_id"]), member)
    return mapped


def compare_fingerprints(ip, port):
    dev = ZKTecoDevice(ip, port)
    if not dev.connect():
        return {"rows": [], "users": 0, "matched": 0, "unmatched": 0, "errors": dev.error}
    users = dev.get_users()
    error = dev.error
    dev.disconnect()
    if error:
        return {"rows": [], "users": 0, "matched": 0, "unmatched": 0, "errors": error}
    members = _member_fp_map()
    rows, seen, matched = [], set(), 0
    for user in users:
        key = _norm_fp(user["user_id"])
        if not key or key in seen:
            continue
        seen.add(key)
        member = members.get(key)
        rows.append({"user_id": user["user_id"], "name": user["name"], "member_id": member["id"] if member else None, "member_name": member["full_name"] if member else ""})
        matched += bool(member)
    return {"rows": rows, "users": len(rows), "matched": matched, "unmatched": len(rows) - matched, "errors": ""}


def import_attendance(ip, port):
    """Import device logs using the device's actual ZK protocol data structures."""
    import app.database as db
    dev = ZKTecoDevice(ip, port)
    if not dev.connect():
        return {"imported": 0, "skipped": 0, "unmatched": [], "errors": dev.error}
    users = dev.get_users()
    records = dev.read_attendance()
    error = dev.error
    dev.disconnect()
    if error:
        return {"imported": 0, "skipped": 0, "unmatched": [], "errors": error}

    uid_map = {user["uid"]: _norm_fp(user["user_id"]) for user in users}
    members = _member_fp_map()
    unmatched, seen_users = [], set()
    for user in users:
        key = _norm_fp(user["user_id"])
        if key and key not in seen_users and key not in members:
            unmatched.append({"user_id": user["user_id"], "name": user["name"]})
        seen_users.add(key)

    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")
    names_by_uid = {user["uid"]: user["name"] or "" for user in users}
    names_by_id = {_norm_fp(user["user_id"]): user["name"] or "" for user in users if _norm_fp(user["user_id"])}
    db.execute_many(
        "UPDATE device_movements SET name=? WHERE user_id=? AND (name IS NULL OR name='')",
        [(user["name"] or "", _norm_fp(user["user_id"])) for user in users if _norm_fp(user["user_id"])],
    )
    existing = set(
        (r["member_id"], r["check_in"])
        for r in db.fetch_all("SELECT member_id, check_in FROM attendance")
    )
    mov_rows = []
    att_rows = []
    imported = skipped = 0
    seen = set()
    rows = []
    for record in records:
        timestamp = record["timestamp"]
        if timestamp < cutoff:
            skipped += 1
            continue
        fingerprint = _norm_fp(record.get("user_id")) or uid_map.get(record["uid"], "")
        member = members.get(fingerprint)
        dev_name = (
            names_by_uid.get(record["uid"])
            or names_by_id.get(fingerprint)
            or ""
        )
        mov_rows.append(
            (record["uid"], fingerprint, dev_name, timestamp)
        )
        rows.append({
            "timestamp": timestamp,
            "user_id": fingerprint,
            "name": dev_name,
            "member_id": member["id"] if member else None,
            "member_name": member["full_name"] if member else "",
        })
        key = (fingerprint, timestamp)
        if not member or key in seen:
            skipped += 1
            continue
        seen.add(key)
        if (member["id"], timestamp) in existing:
            skipped += 1
            continue
        att_rows.append((member["id"], timestamp, "device"))
        imported += 1
    if mov_rows:
        db.execute_many(
            "INSERT OR IGNORE INTO device_movements (uid, user_id, name, timestamp) VALUES (?,?,?,?)",
            mov_rows,
        )
    if att_rows:
        db.execute_many(
            "INSERT INTO attendance (member_id, check_in, method) VALUES (?,?,?)",
            att_rows,
        )
    db.execute("DELETE FROM device_movements WHERE timestamp < ?", (cutoff,))
    return {"imported": imported, "skipped": skipped, "unmatched": unmatched, "movements": rows, "errors": ""}

def compare_movements(ip, port):
    """Pull raw movements from the device and compare them against members."""
    dev = ZKTecoDevice(ip, port)
    if not dev.connect():
        return {"rows": [], "movements": 0, "matched": 0, "unmatched": 0, "errors": dev.error}
    users = dev.get_users()
    records = dev.read_attendance()
    error = dev.error
    dev.disconnect()
    if error:
        return {"rows": [], "movements": 0, "matched": 0, "unmatched": 0, "errors": error}
    uid_map = {user["uid"]: _norm_fp(user["user_id"]) for user in users}
    names_by_uid = {user["uid"]: user["name"] or "" for user in users}
    names_by_id = {_norm_fp(user["user_id"]): user["name"] or "" for user in users if _norm_fp(user["user_id"])}
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")
    members = _member_fp_map()
    rows = []
    matched = 0
    for record in records:
        timestamp = record["timestamp"]
        if timestamp < cutoff:
            continue
        fingerprint = _norm_fp(record.get("user_id")) or uid_map.get(record["uid"], "")
        member = members.get(fingerprint)
        dev_name = (
            names_by_uid.get(record["uid"])
            or names_by_id.get(fingerprint)
            or ""
        )
        rows.append({
            "timestamp": record["timestamp"],
            "user_id": fingerprint,
            "name": dev_name,
            "member_id": member["id"] if member else None,
            "member_name": member["full_name"] if member else "",
        })
        matched += bool(member)
    return {"rows": rows, "movements": len(rows), "matched": matched,
            "unmatched": len(rows) - matched, "errors": ""}


def _try_http_photo(ip, user_id, timeout=4):
    """SpeedFace-V5L HTTP fallback: try common photo endpoints (port 80/8080) with/without Basic Auth."""
    import urllib.request
    import urllib.error
    import base64
    key = _norm_fp(user_id)
    endpoints = [
        f"http://{ip}/csl/photo?pin={key}",
        f"http://{ip}/csl/photo?user_id={key}",
        f"http://{ip}/photo/{key}.jpg",
        f"http://{ip}/photos/{key}.jpg",
        f"http://{ip}/web/images/{key}.jpg",
        f"http://{ip}/user/photo/{key}.jpg",
        f"http://{ip}:8080/photo/{key}.jpg",
        f"http://{ip}:8080/csl/photo?pin={key}",
    ]
    # credentials: device web login admin/admin12345 (plus common defaults)
    creds = [None, ("admin", "admin12345"), ("admin", "admin"), ("admin", "123456")]
    for cred in creds:
        auth_header = None
        if cred:
            token = base64.b64encode(f"{cred[0]}:{cred[1]}".encode()).decode()
            auth_header = f"Basic {token}"
        for url in endpoints:
            try:
                headers = {"User-Agent": "HydrogenGym/1.0"}
                if auth_header:
                    headers["Authorization"] = auth_header
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = resp.read()
                    ctype = resp.headers.get_content_type() or ""
                    if len(data) > 800 and (data[:2] == b"\xff\xd8" or data[:4] == b"\x89PNG" or "image" in ctype):
                        return data
            except Exception:
                continue
    return None


def get_user_photo(ip, port, user_id):
    """Pull the photo stored on the device for the given user id.

    1) ZK protocol via pyzk (أجهزة البصمة القديمة)
    2) HTTP fallback لـ SpeedFace-V5L والواجهات الحديثة (port 80)
    """
    dev = ZKTecoDevice(ip, port)
    if not dev.connect():
        # حتى لو فشل ZK، جرّب HTTP (الـ SpeedFace قد يرفض ZK لكن يفتح HTTP)
        http_photo = _try_http_photo(ip, user_id)
        if http_photo:
            return {"photo": http_photo, "error": ""}
        return {"photo": None, "error": dev.error}
    try:
        key = _norm_fp(user_id)
        uid = None
        for user in dev.get_users():
            if _norm_fp(user["user_id"]) == key:
                uid = user["uid"]
                break
        if uid is None:
            # المستخدم غير موجود في ZK لكن جرّب HTTP قبل الإرجاع
            http_photo = _try_http_photo(ip, user_id)
            if http_photo:
                return {"photo": http_photo, "error": ""}
            return {"photo": None, "error": "user_not_found"}
        photo = None
        try:
            photo = dev._safe_operation(lambda: dev.connection.get_user_photo(uid))
        except Exception:
            photo = None
        error = dev.error
        if error and "no attribute" in error:
            error = "photo_unsupported"
        if isinstance(photo, (bytes, bytearray)) and len(photo) > 800:
            return {"photo": bytes(photo), "error": ""}
        # فشل ZK → جرّب HTTP لـ SpeedFace
        http_photo = _try_http_photo(ip, user_id)
        if http_photo:
            return {"photo": http_photo, "error": ""}
        if not isinstance(photo, (bytes, bytearray)):
            photo = None
        # لو لا ZK ولا HTTP
        if error == "photo_unsupported":
            return {"photo": None, "error": "photo_unsupported_speedface"}
        return {"photo": photo, "error": error or "no_device_photo"}
    finally:
        dev.disconnect()
