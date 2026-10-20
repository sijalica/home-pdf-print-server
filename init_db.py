import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "instance" / "print-server.sqlite3"

with sqlite3.connect(DATABASE_PATH) as connection:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS print_jobs (
            id TEXT PRIMARY KEY,
            original_filename TEXT NOT NULL,
            page_count INTEGER NOT NULL CHECK (page_count > 0),
            status TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            submitted_by TEXT NOT NULL DEFAULT 'Unknown',
            cups_job_id INTEGER,
        )
    """)

print("Database initialized.")
