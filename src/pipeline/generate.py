"""Call the configured LLM with the retrieved chunks only."""

from __future__ import annotations

import os
import re

from pathlib import Path

from dotenv import load_dotenv

from src.config import Settings
from src.pipeline.retrieve import Hit

_URL = re.compile(r"https?://[^\s)\]]+")
_SENTENCE = re.compile(r"(?<=[.!?])(?=\s|$)")
_PROMPT = Path(__file__).resolve().parents[1] / "prompts" / "system.txt"


def generate(
    question: str,
    intent_label: str,
    scheme_name: str,
    hits: list[Hit],
    settings: Settings,
    complete=None,
) -> tuple[str, str]:
    system = _PROMPT.read_text(encoding="utf-8").strip()
    user = _user_message(question, intent_label, scheme_name, hits)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    if complete is None:
        complete = provider_complete
    text = complete(messages, settings).strip()
    model_id = _model_id(settings)
    return text, model_id


def provider_complete(messages: list[dict], settings: Settings) -> str:
    """Answers go to Groq only. Embeddings stay on the Hugging Face model."""
    load_dotenv(settings.root / ".env", override=True)
    model = os.getenv("LLM_MODEL_ID", "").strip()
    if not model:
        raise ValueError("LLM_MODEL_ID is missing from .env")
    if settings.llm_provider != "groq":
        raise ValueError("llm_provider must be groq")
    return _groq(messages, model)


def compliant(text: str, citation_url: str) -> bool:
    urls = _URL.findall(text)
    if len(urls) != 1 or urls[0] != citation_url:
        return False
    return len(_sentences(text)) <= 3


def _user_message(question: str, intent_label: str, scheme_name: str, hits: list[Hit]) -> str:
    lines = [
        f"Intent: {intent_label}",
        f"Scheme: {scheme_name or 'not named'}",
        f"Question: {question}",
        "",
        "Retrieved chunks:",
    ]
    for index, hit in enumerate(hits, start=1):
        lines.extend(
            [
                f"{index}. url: {hit.source_url}",
                f"   fact_type: {hit.fact_type}",
                f"   text: {hit.text}",
            ]
        )
    return "\n".join(lines)


def _sentences(text: str) -> list[str]:
    parts = _SENTENCE.split(text.strip())
    return [part.strip() for part in parts if part.strip()]


def _model_id(settings: Settings) -> str:
    load_dotenv(settings.root / ".env", override=True)
    return os.getenv("LLM_MODEL_ID", "").strip()


def _require_key(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is missing from .env")
    return value


def _groq(messages: list[dict], model: str) -> str:
    from groq import Groq

    response = Groq(api_key=_require_key("GROQ_API_KEY")).chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
    )
    return response.choices[0].message.content or ""

