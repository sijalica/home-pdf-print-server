"""Loopback-only household PDF printer. Names are not authenticated identities."""
import hmac
import json
import os
import re
import secrets
import shutil
import sqlite3
import subprocess
import sys
from uuid import uuid4

from flask import Flask, abort, redirect, render_template, request, session, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from common import ROOT, INSTANCE, UPLOADS, QUEUE, database, upload_path, update, remove_upload

app = Flask(__name__)
app.config.update(
    SECRET_KEY=(INSTANCE / 'secret.key').read_text().strip(),
    MAX_CONTENT_LENGTH=20 * 1024**2,
    MAX_FORM_PARTS=8,
    MAX_FORM_MEMORY_SIZE=64 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Strict',
    # HTTP exists only on local loopback ends of an encrypted SSH tunnel.
    SESSION_COOKIE_SECURE=False,
    TRUSTED_HOSTS=['127.0.0.1', 'localhost'],
)
signer = URLSafeTimedSerializer(app.secret_key, salt='print-form-v1')

@app.after_request
def headers(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'none'; style-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
    return response

@app.get('/')
def home():
    session.setdefault('owner', secrets.token_hex(32))
    token = signer.dumps({'owner': session['owner'], 'nonce': secrets.token_hex(32)})
    return render_template('index.html', token=token)

@app.errorhandler(413)
def too_large(error):
    return render_template('error.html', message='The upload request exceeds 20 MiB. Choose a smaller PDF.'), 413

@app.errorhandler(400)
def bad_request(error):
    return render_template('error.html', message='Invalid request. Open a fresh upload page and try again.'), 400

@app.get('/jobs/<job_id>')
def result(job_id):
    with database() as db:
        job = db.execute('SELECT * FROM print_jobs WHERE id = ?', (job_id,)).fetchone()
    if not job or not session.get('owner') or job['owner_token'] != session['owner']:
        abort(404)
    return render_template('result.html', job=job)

@app.post('/upload')
def upload():
    try:
        token = request.form.get('token', '')
        signed = signer.loads(token, max_age=3600)
        if not session.get('owner') or not hmac.compare_digest(signed['owner'], session['owner']):
            abort(400)
    except (BadSignature, SignatureExpired, KeyError, TypeError):
        abort(400)

    name = request.form.get('submitted_by', '').strip()
    document = request.files.get('document')
    if not 1 <= len(name) <= 80 or any(ord(c) < 32 for c in name):
        return render_template('error.html', message='Enter a name of 1–80 characters.'), 400
    if not document or not document.filename or not document.filename.lower().endswith('.pdf'):
        return render_template('error.html', message='Choose a PDF file.'), 400
    filename = document.filename.replace('\\', '/').split('/')[-1][:200]
    filename = ''.join(c for c in filename if ord(c) >= 32)
    job_id = uuid4().hex
    # Serialize the reservation: two concurrent POSTs cannot submit the same token twice.
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        previous = db.execute('SELECT id FROM print_jobs WHERE submission_token = ?', (token,)).fetchone()
        if previous:
            return redirect(url_for('result', job_id=previous['id']), code=303)
        outstanding = db.execute("SELECT count(*) FROM print_jobs WHERE status NOT IN ('completed','failed','canceled','rejected')").fetchone()[0]
        if outstanding >= 20 or shutil.disk_usage(INSTANCE).free < 1024**3:
            return render_template('error.html', message='Server storage or pending-job limit reached. Ask the operator to review.'), 503
        db.execute('''INSERT INTO print_jobs
            (id, original_filename, page_count, status, submitted_by, owner_token, submission_token, cups_title)
            VALUES (?, ?, 1, 'validating', ?, ?, ?, ?)''',
            (job_id, filename, name, session['owner'], token, f'home-print-{job_id}'))
    path = upload_path(job_id)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as output:
            document.save(output)
        validation = subprocess.run(
            [sys.executable, str(ROOT / 'validate_pdf.py'), str(path)],
            capture_output=True, text=True, timeout=15, check=True,
        )
        pages = json.loads(validation.stdout)['pages']
        update(job_id, page_count=pages, status='submitting')
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        update(job_id, status='rejected', error_message='PDF could not be validated or stored.')
        remove_upload(job_id)
        return redirect(url_for('result', job_id=job_id), code=303)

    try:
        printed = subprocess.run(
            ['lp', '-d', QUEUE, '-n', '1', '-t', f'home-print-{job_id}', str(path)],
            capture_output=True, text=True, check=True, timeout=30,
            env={**os.environ, 'LC_ALL': 'C'},
        )
        match = re.search(r'request id is ' + re.escape(QUEUE) + r'-(\d+)', printed.stdout)
        if not match:
            raise ValueError('No readable CUPS ID')
        update(job_id, cups_job_id=int(match.group(1)), status='submitted')
    except (subprocess.SubprocessError, OSError, ValueError, sqlite3.Error):
        # CUPS may already have accepted the job. Never automatically print it again.
        app.logger.exception('Submission requires review: %s', job_id)
        try:
            update(job_id, status='needs_review', error_message='Submission outcome uncertain. Do not resubmit; ask the operator to check CUPS.')
        except sqlite3.Error:
            app.logger.exception('Could not persist uncertainty: %s', job_id)
    return redirect(url_for('result', job_id=job_id), code=303)
