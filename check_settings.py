import sqlite3
conn = sqlite3.connect(r'D:\hydrogen-gym\app\data\hydrogen.db')
cursor = conn.cursor()
cursor.execute('SELECT key, value FROM settings WHERE key LIKE "device_%"')
for row in cursor.fetchall():
    print(row)
conn.close()