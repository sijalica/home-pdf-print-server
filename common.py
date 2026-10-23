"""Shared paths, database migration and private-file helpers."""
import os
import re
import sqlite3
from pathlib import Path
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parent
INSTANCE = Path(os.environ.get('PRINT_INSTANCE', ROOT / 'instance')).resolve()
UPLOADS = INSTANCE / 'uploads'
DATABASE = INSTANCE / 'print-server.sqlite3'
QUEUE = 'HP_LaserJet_Professional_P1102'
TERMINAL = ('completed', 'canceled', 'failed', 'rejected')

@contextmanager
def database():
    connection = sqlite3.connect(DATABASE, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()

def initialize():
    INSTANCE.mkdir(mode=0o700, parents=True, exist_ok=True)
    UPLOADS.mkdir(mode=0o700, exist_ok=True)
    with database() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS print_jobs (
            id TEXT PRIMARY KEY, original_filename TEXT NOT NULL,
            page_count INTEGER NOT NULL CHECK(page_count > 0),
            status TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )''')
        columns = {r['name'] for r in db.execute('PRAGMA table_info(print_jobs)')}
        additions = {
            'submitted_by': "TEXT NOT NULL DEFAULT 'Unknown'",
            'cups_job_id': 'INTEGER', 'completed_at': 'TEXT',
            'file_deleted_at': 'TEXT', 'owner_token': 'TEXT',
            'submission_token': 'TEXT', 'error_message': 'TEXT',
            'cups_title': 'TEXT', 'terminal_at': 'TEXT',
        }
        for name, definition in additions.items():
            if name not in columns:
                db.execute(f'ALTER TABLE print_jobs ADD COLUMN {name} {definition}')
        db.execute('CREATE UNIQUE INDEX IF NOT EXISTS unique_submission ON print_jobs(submission_token)')
    os.chmod(DATABASE, 0o600)
    secret = INSTANCE / 'secret.key'
    if not secret.exists():
        import secrets
        with secret.open('x') as output:
            os.chmod(secret, 0o600)
            output.write(secrets.token_hex(32))

def upload_path(job_id):
    if not re.fullmatch(r'[0-9a-f]{32}', job_id):
        raise ValueError('Invalid application job ID')
    path = UPLOADS / f'{job_id}.pdf'
    if path.is_symlink():
        raise ValueError('Refusing symbolic link')
    return path

def update(job_id, **fields):
    allowed = {'status','page_count','cups_job_id','completed_at','file_deleted_at',
               'error_message','cups_title','terminal_at'}
    if not fields or not set(fields) <= allowed:
        raise ValueError('Invalid fields')
    with database() as db:
        assignments = ', '.join(f'{key} = ?' for key in fields)
        db.execute(f'UPDATE print_jobs SET {assignments} WHERE id = ?',
                   (*fields.values(), job_id))

def remove_upload(job_id):
    # Missing file is safe: a previous run may have deleted it before a DB failure.
    upload_path(job_id).unlink(missing_ok=True)
    with database() as db:
        db.execute('UPDATE print_jobs SET file_deleted_at = CURRENT_TIMESTAMP WHERE id = ?', (job_id,))
