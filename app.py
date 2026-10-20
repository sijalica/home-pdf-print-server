from flask import Flask, render_template, request
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from pathlib import Path
from uuid import uuid4
import sqlite3
from contextlib import closing
import subprocess
import os
import re

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
UPLOAD_DIR = Path(app.instance_path) / "uploads"
DATABASE_PATH = Path(app.instance_path) / "print-server.sqlite3"

@app.get("/")
def home():
    return render_template("index.html")

@app.post("/upload")
def upload():
    submitted_by = request.form.get("submitted_by", "").strip()

    if not submitted_by or len(submitted_by) > 80:
        return {"error": "Enter your name using 1 to 80 characters."}, 400

    document = request.files.get("document")

    if document is None or document.filename == "":
        return {"error": "Please select a file."}, 400

    if not document.filename.lower().endswith(".pdf"):
        return {"error": "Only PDF files are accepted."}, 400

    try:
        reader = PdfReader(document.stream, strict=True)

        if reader.is_encrypted:
            return {"error": "Encrypted PDFs are not supported."}, 400

        page_count = len(reader.pages)

    except PdfReadError:
        return {"error": "The file could not be read as a valid PDF."}, 400

    if page_count < 1 or page_count > 100:
        return {"error": "The PDF must contain between 1 and 100 pages."}, 400

    job_id = uuid4().hex
    saved_path = UPLOAD_DIR / f"{job_id}.pdf"

    document.stream.seek(0)

    with saved_path.open("xb") as destination:
        document.save(destination)

    try:
        with closing(sqlite3.connect(DATABASE_PATH)) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO print_jobs
                        (id, original_filename, page_count, status, submitted_by)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (job_id, document.filename, page_count, "saved", submitted_by),
                )
    except sqlite3.Error:
        saved_path.unlink(missing_ok=True)
        app.logger.exception("Could not record uploaded job")
        return {"error": "Could not record the upload. Please try again."}, 500

    try:
        result = subprocess.run(
            [
                "lp",
                "-d", "HP_LaserJet_Professional_P1102",
                "-n", "1",
                str(saved_path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
            env={**os.environ, "LC_ALL": "C"},
        )
    except subprocess.TimeoutExpired:
        app.logger.exception("Print submission timed out")
        return {
            "error": "Print submission is uncertain. Check the queue before retrying.",
            "job_id": job_id,
        }, 503
    except (subprocess.CalledProcessError, OSError):
        app.logger.exception("Could not submit print job")
        return {
            "error": "Could not submit the document to the printer.",
            "job_id": job_id,
        }, 503

    match = re.search(
        r"request id is HP_LaserJet_Professional_P1102-(\d+)",
        result.stdout,
    )

    if match is None:
        return {
            "error": "Submission returned without a readable job ID. Do not resubmit; check CUPS.",
            "job_id": job_id,
        }, 503

    cups_job_id = int(match.group(1))

    try:
        with closing(sqlite3.connect(DATABASE_PATH)) as connection:
            with connection:
                connection.execute(
                    """
                    UPDATE print_jobs
                    SET cups_job_id = ?, status = ?
                    WHERE id = ?
                    """,
                    (cups_job_id, "submitted", job_id),
                )
    except sqlite3.Error:
        app.logger.exception("Print submitted but database update failed")
        return {
            "error": "Already submitted to CUPS, but history could not be updated. Do not resubmit.",
            "job_id": job_id,
            "cups_job_id": cups_job_id,
        }, 500

    return {
        "message": "Submitted to CUPS; physical printing is not yet confirmed.",
        "submitted_by": submitted_by,
        "job_id": job_id,
        "cups_job_id": cups_job_id,
        "printer_response": result.stdout.strip(),
        "filename": document.filename,
        "pages": page_count,
    }
