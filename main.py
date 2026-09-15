import sqlite3
from fastapi import FastAPI
from datetime import datetime

app = FastAPI()

# 1. Initialize the database safely when the script loads
conn = sqlite3.connect("report.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer TEXT NOT NULL,
        product TEXT NOT NULL,
        amount REAL NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
""")

conn.commit()


@app.get("/health")
def health():
    return {"name": "PDF Generator", "version": "v1.1", "status": "running"}
