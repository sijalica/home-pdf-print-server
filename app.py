from flask import Flask, render_template

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

@app.get("/")
def home():
    return render_template("index.html")

@app.post("/upload")
def upload():
    document = request.files.get("document")

    if document is None or document.filename == "":
        return {"error": "Please select a file."}, 400

    return {
        "message": "File received for this test; not saved or printed.",
        "filename": document.filename,
    }
