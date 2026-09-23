"""ADMS / HTTPPUSH receiver for ZKTeco face devices.

The SpeedFace-V5L pushes attendance records (ATTLOG) and face photos
(ATTPHOTO) over HTTP to a configured server. This module runs a small
HTTPServer that accepts those pushes and imports them into the app.

Device setup (one time, on the device):
  Comm -> Server: PC IP + port below, enable photo upload.
"""
import base64
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import app.database as db

from PySide6.QtCore import QObject, Signal


class _Signals(QObject):
    """Cross-thread notifications to the UI (main window)."""

    expired_checkin = Signal(list)


signals = _Signals()

PHOTOS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "photos",
)

# Response for GET /iclock/cdata?options=all (modern ADMS format).
OPTIONS_TEXT = (
    "ATTLOGStamp=\n"
    "OPERLOGStamp=\n"
    "ATTPHOTOStamp=None\n"
    "ErrorDelay=60\n"
    "Delay=30\n"
    "TransTimes=00:00;14:05\n"
    "TransInterval=1\n"
    "TransFlag=TransData AttLog OpLog AttPhoto EnrollUser ChgUser EnrollFP ChgFP UserPic\n"
    "MultiBioDataSupport=0:1:0:0:0:0:0:0:0:0\n"
    "Realtime=1\n"
    "Encrypt=None"
)


def _query(path, key):
    if "?" not in path:
        return ""
    for part in path.split("?", 1)[1].split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            if k == key:
                return v
    return ""


def import_attlog(raw):
    """Import ATTLOG push: tab-separated `PIN=<pin>\t<ts>\t<status>\t<workcode>` lines."""
    text = raw.decode("ascii", errors="replace")
    imported = 0
    expired = set()
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("PIN="):
            continue
        flds = line.split("\t")
        if len(flds) < 2:
            continue
        pin = flds[0].split("=", 1)[1].strip()
        ts = flds[1].strip()
        member = db.fetch_one(
            "SELECT id, full_name FROM members WHERE fingerprint_id=?", (pin,)
        )
        if not member:
            continue
        exists = db.fetch_one(
            "SELECT id FROM attendance WHERE member_id=? AND check_in=?",
            (member["id"], ts),
        )
        if exists:
            continue
        db.execute(
            "INSERT INTO attendance (member_id, check_in, method) VALUES (?,?,?)",
            (member["id"], ts, "device"),
        )
        imported += 1
        sub = db.fetch_one(
            "SELECT end_date FROM subscriptions WHERE member_id=? AND status='active'"
            " ORDER BY end_date DESC LIMIT 1",
            (member["id"],),
        )
        if sub and sub["end_date"] and str(sub["end_date"]) < db.today():
            expired.add(member["full_name"])
    if expired:
        signals.expired_checkin.emit(sorted(expired))
    return imported


def import_attphoto(raw, pin_q):
    """Import ATTPHOTO push: PIN line + `CMD=uploadphoto<base64>` / `CMD=realupload<base64>`."""
    body = raw.decode("ascii", errors="replace")
    req_pin = pin_q
    if not req_pin:
        for ln in body.split("CMD=")[0].splitlines():
            if ln.startswith("PIN="):
                req_pin = ln.split("=", 1)[1].strip()
                break
    pin = ""
    if req_pin:
        chunks = [
            c for c in req_pin.replace(".jpg", "").replace(".", "-").split("-")
            if c.isdigit()
        ]
        if len(chunks) == 2:
            pin = chunks[1]
        elif chunks:
            pin = min(chunks, key=len)
    data = ""
    for marker in ("CMD=uploadphoto", "CMD=realupload"):
        if marker in body:
            data = body.split(marker)[1]
            break
    if not pin or not data:
        return None
    try:
        photo = base64.b64decode(data)
    except Exception:
        return None
    if not photo:
        return None
    try:
        os.makedirs(PHOTOS_DIR, exist_ok=True)
        path = os.path.join(PHOTOS_DIR, "member_{}.jpg".format(pin))
        with open(path, "wb") as fh:
            fh.write(photo)
    except OSError:
        return None
    member = db.fetch_one(
        "SELECT id, photo_path FROM members WHERE fingerprint_id=?", (pin,)
    )
    if member and not member.get("photo_path"):
        db.execute("UPDATE members SET photo_path=? WHERE id=?", (path, member["id"]))
    return path


class _Handler(BaseHTTPRequestHandler):
    server_version = "HydrogenGym/1.0"

    def log_message(self, fmt, *args):
        pass

    def _reply(self, text):
        data = text.encode("ascii", errors="replace")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        try:
            if "/iclock/getrequest" in self.path:
                self._reply("OK")
            elif "/iclock/cdata" in self.path:
                self._reply(OPTIONS_TEXT)
            else:
                self._reply("OK")
        except Exception:
            try:
                self._reply("ERR")
            except Exception:
                pass

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            if "/iclock/devicecmd" in self.path:
                self._reply("OK")
                return
            if "/iclock/cdata" in self.path:
                table = _query(self.path, "table").upper()
                if table == "ATTPHOTO":
                    ok = bool(import_attphoto(raw, _query(self.path, "PIN")))
                    self._reply("OK" if ok else "ERR")
                    return
                if table == "ATTLOG":
                    import_attlog(raw)
                    self._reply("OK")
                    return
            self._reply("OK")
        except Exception:
            try:
                self._reply("ERR")
            except Exception:
                pass


class AdmsServer:
    def __init__(self, port):
        self._httpd = HTTPServer(("0.0.0.0", port), _Handler)
        self._thread = threading.Thread(
            target=self._httpd.serve_forever, daemon=True
        )

    def start(self):
        self._thread.start()
        return self

    def stop(self):
        try:
            self._httpd.shutdown()
        except Exception:
            pass
        try:
            self._httpd.server_close()
        except Exception:
            pass


def get_local_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "127.0.0.1"
