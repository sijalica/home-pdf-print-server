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

        if "cups_job_id" not in columns:
            connection.execute(
                "ALTER TABLE print_jobs ADD COLUMN cups_job_id INTEGER"
            )

print("CUPS job ID column is ready.")
