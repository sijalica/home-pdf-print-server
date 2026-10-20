import sqlite3
from contextlib import closing
from pathlib import Path

database_path = (
    Path(__file__).resolve().parent
    / "instance"
    / "print-server.sqlite3"
)

with closing(sqlite3.connect(database_path)) as connection:
    with connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(print_jobs)")
        }

        if "submitted_by" not in columns:
            connection.execute("""
                ALTER TABLE print_jobs
                ADD COLUMN submitted_by TEXT NOT NULL DEFAULT 'Unknown'
            """)

print("Submitter column is ready.")
