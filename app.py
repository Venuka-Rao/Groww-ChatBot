"""Vercel entrypoint. The local chat remains `streamlit run src/ui/app.py`."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from src.pipeline.ask import ask

app = FastAPI()
PAGE = Path(__file__).resolve().parent / "web" / "index.html"


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@app.get("/")
def home() -> FileResponse:
    return FileResponse(PAGE)


@app.post("/api/ask")
def ask_route(body: Question):
    try:
        answer = ask(body.question.strip())
    except Exception as exc:
        return JSONResponse({"error": _public_error(exc)}, status_code=500)
    return {
        "text": answer.text,
        "intent": answer.intent,
        "refusal": answer.refusal,
        "source_stamp": answer.source_stamp,
        "citation_url": answer.citation_url,
    }


def _public_error(exc: Exception) -> str:
    message = str(exc)
    lowered = message.lower()
    if any(word in lowered for word in ("key", "token", "secret", "authorization")):
        return "The fact lookup could not reach the model. Check the host settings."
    return message or "The fact lookup failed."
