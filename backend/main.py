from fastapi import FastAPI, UploadFile, File
from backend.agent import diagnose_logs
import os

app = FastAPI(
    title="AI Log Intelligence Agent"
)

UPLOAD_DIR = "../logs"

os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/")
def root():
    return {
        "status": "running",
        "message": "AI Log Intelligence Agent"
    }


@app.post("/upload")
async def upload_log(file: UploadFile = File(...)):

    file_path = os.path.join(
        UPLOAD_DIR,
        file.filename
    )

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    return {
        "status": "success",
        "filename": file.filename
    }


@app.get("/chat")
def chat(question: str):

    response = diagnose_logs(question)

    return {
        "question": question,
        "response": response
    }