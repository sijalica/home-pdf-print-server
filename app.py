from flask import Flask, render_template, request
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from pathlib import Path
from uuid import uuid4
import sqlite3
from contextlib import closing

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

    return {
        "message": "PDF saved; not printed.",
        "submitted_by": submitted_by,
        "job_id": job_id,
        "filename": document.filename,
        "pages": page_count,
    }
