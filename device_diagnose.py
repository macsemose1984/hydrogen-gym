#!/usr/bin/env python
"""Diagnostic tool for ZKTeco device connection issues."""
import sys
sys.path.insert(0, r"D:\hydrogen-gym")

import app.database as db
from app.zk import ZKTecoDevice, compare_fingerprints, import_attendance


def main():
    ip = db.get_setting("device_ip", "192.168.0.100")
    try:
        port = int(db.get_setting("device_port", "4370") or 4370)
    except ValueError:
        port = 4370

    print(f"=== ZKTeco Device Diagnostic ===")
    print(f"Configured IP: {ip}")
    print(f"Configured Port: {port}")
    print()

    # Test basic connection
    print("1. Testing connection...")
    dev = ZKTecoDevice(ip, port, timeout=15)
    if dev.connect():
        print(f"   [OK] Connected successfully")
        print(f"   Serial: {dev._safe_operation(lambda: dev.connection.get_serialnumber()) or 'Unknown'}")

        # Get users
        print("2. Reading users...")
        users = dev.get_users()
        print(f"   Found {len(users)} users")
        for u in users[:5]:
            print(f"     UID={u['uid']}, ID={u['user_id']}, Name={u['name']}")

        # Read attendance
        print("3. Reading attendance records...")
        records = dev.read_attendance()
        print(f"   Found {len(records)} attendance records")
        for r in records[:5]:
            print(f"     UID={r['uid']}, Time={r['timestamp']}, State={r['state']}")

        dev.disconnect()
        print("4. Disconnected")
    else:
        print(f"   [FAIL] Connection failed: {dev.error}")
        print()
        print("Troubleshooting tips:")
        print("  - Verify the device IP address is correct")
        print("  - Ensure the device is on the same network")
        print("  - Check if port 4370 is open (try telnet IP 4370)")
        print("  - Some devices require UDP mode (force_udp=True)")
        print("  - Try pinging the device IP")
        print("  - Check firewall settings")
        return 1

    print()
    print("5. Testing fingerprint comparison...")
    result = compare_fingerprints(ip, port)
    if result.get("errors"):
        print(f"   ✗ Error: {result['errors']}")
    else:
        print(f"   Users on device: {result['users']}")
        print(f"   Matched: {result['matched']}")
        print(f"   Unmatched: {result['unmatched']}")

    print()
    print("6. Testing attendance import...")
    result = import_attendance(ip, port)
    if result.get("errors"):
        print(f"   ✗ Error: {result['errors']}")
    else:
        print(f"   Imported: {result['imported']}")
        print(f"   Skipped: {result['skipped']}")
        print(f"   Unmatched users: {len(result.get('unmatched', []))}")

    print()
    print("=== Diagnostic Complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())