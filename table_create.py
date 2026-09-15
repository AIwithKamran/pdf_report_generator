import sqlite3

conn = sqlite3.connect("report.db")
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
""")

conn.commit()
conn.close()

print("✅ 'reports' table ready.")