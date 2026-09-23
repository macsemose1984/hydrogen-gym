import os
import shutil
from datetime import datetime

import app.database as db

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")


def backup_database():
    """Copy the current DB to backups/ with a timestamp. Returns backup path or None."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if not os.path.exists(db.DB_PATH):
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(BACKUP_DIR, f"hydrogen_{stamp}.db")
    # avoid collisions when backups are created within the same second
    n = 1
    while os.path.exists(dst):
        dst = os.path.join(BACKUP_DIR, f"hydrogen_{stamp}_{n}.db")
        n += 1
    # use SQLite backup API for a safe, consistent copy
    src_conn = db.get_connection()
    try:
        dst_conn = __import__("sqlite3").connect(dst)
        try:
            src_conn.backup(dst_conn)
            dst_conn.commit()
        finally:
            dst_conn.close()
    except Exception:
        # fallback to a plain file copy
        try:
            src_conn.close()
        except Exception:
            pass
        shutil.copy2(db.DB_PATH, dst)
    finally:
        try:
            src_conn.close()
        except Exception:
            pass
    return dst


def last_backup_date():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    files = [f for f in os.listdir(BACKUP_DIR) if f.startswith("hydrogen_") and f.endswith(".db")]
    if not files:
        return None
    dates = sorted(f.split("_")[1].split(".")[0] for f in files)
    return dates[-1]


def backup_today_done():
    last = last_backup_date()
    if not last:
        return False
    return last[:8] == datetime.now().strftime("%Y%m%d")


def cleanup_backups(keep=30):
    """Delete oldest backup files, keeping only the newest `keep`."""
    if not os.path.isdir(BACKUP_DIR):
        return 0
    files = sorted(
        f for f in os.listdir(BACKUP_DIR)
        if f.startswith("hydrogen_") and f.endswith(".db")
    )
    removed = 0
    for f in files[:-keep]:
        try:
            os.remove(os.path.join(BACKUP_DIR, f))
            removed += 1
        except OSError:
            pass
    return removed


def list_backups():
    """Return list of {file, path, size, date} sorted newest first."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    out = []
    for f in os.listdir(BACKUP_DIR):
        if f.startswith("hydrogen_") and f.endswith(".db"):
            p = os.path.join(BACKUP_DIR, f)
            out.append({
                "file": f,
                "path": p,
                "size": os.path.getsize(p),
                "date": f.replace("hydrogen_", "").replace(".db", "").replace("_", " "),
            })
    out.sort(key=lambda x: x["file"], reverse=True)
    return out


def restore_database(backup_path):
    """Replace the live DB with the given backup file (a safety backup is taken first).

    Returns (ok, message).
    """
    if not os.path.exists(backup_path):
        return False, "النسخة غير موجودة"
    # read the chosen backup into memory FIRST, so a same-second safety
    # backup can never clobber it
    with open(backup_path, "rb") as f:
        payload = f.read()
    if not payload:
        return False, "النسخة فارغة"
    # keep a safety copy of the current data before overwriting
    safety = backup_database()
    try:
        with open(db.DB_PATH, "wb") as f:
            f.write(payload)
        return True, "تمت الاستعادة بنجاح" + (f"\n(تم حفظ نسخة أمان: {os.path.basename(safety)})" if safety else "")
    except Exception as e:
        return False, f"فشلت الاستعادة: {e}"
