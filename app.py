from flask import Flask, render_template, request
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from pathlib import Path
from uuid import uuid4

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
UPLOAD_DIR = Path(app.instance_path) / "uploads"

@app.get("/")
def home():
    return render_template("index.html")

@app.post("/upload")
def upload():
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

    return {
        "message": "PDF saved; not printed.",
        "job_id": job_id,
        "filename": document.filename,
        "pages": page_count,
    }
