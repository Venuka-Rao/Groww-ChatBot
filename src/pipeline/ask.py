"""Query entry: PII, intent, retrieve or a fixed template, then generate."""

from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.config import Scheme, Settings, load_settings
from src.facts import FACT_PHRASES
from src.guardrails.intent import Intent, classify
from src.guardrails.pii import PII_RESEND, find_pii
from src.guardrails.templates import (
    move_inline_link,
    not_found,
    out_of_corpus,
    redirect_factsheet,
    refuse_advice,
    which_scheme,
)
from src.pipeline.generate import compliant, generate
from src.pipeline.retrieve import Retrieval, retrieve


@dataclass
class Answer:
    query_id: str
    intent: str
    refusal: bool
    text: str
    citation_url: str
    model_id: str
    source_stamp: str


def ask(question: str, settings: Settings | None = None, encoder=None, complete=None) -> Answer:
    settings = settings or load_settings()
    query_id = _query_id()
    if find_pii(question):
        return Answer(query_id, "pii", False, PII_RESEND, "", "", "")

    intent = classify(question, settings.schemes)
    fallback = settings.schemes[0]
    scheme = _scheme_by_slug(settings, intent.scheme_slug)
    stamp = _source_stamp(settings.root)

    if intent.label == "refuse_advice":
        text, url = refuse_advice(scheme, fallback)
        return _store(settings, query_id, intent.label, text, url, True, "template", stamp)
    if intent.label == "redirect_factsheet":
        name, url = _factsheet_target(settings, scheme or fallback)
        text, url = redirect_factsheet(name, url)
        return _store(settings, query_id, intent.label, text, url, True, "template", stamp)
    if intent.label == "out_of_corpus":
        text, url = out_of_corpus(fallback)
        return _store(settings, query_id, intent.label, text, url, True, "template", stamp)
    if intent.label == "answer" and intent.fact_type and not intent.scheme_slug:
        text, url = which_scheme(fallback)
        return _store(settings, query_id, intent.label, text, url, False, "template", stamp)

    retrieval = retrieve(
        question,
        intent.scheme_slug or None,
        query_id=query_id,
        settings=settings,
        encoder=encoder,
    )
    if not retrieval.above_threshold or not _chunks_support(intent, retrieval):
        text, url = _missing_fact(intent, scheme, fallback)
        return _store(settings, query_id, intent.label, text, url, False, "template", stamp)

    draft, model_id = generate(
        question,
        intent.label,
        intent.scheme_name,
        retrieval.hits,
        settings,
        complete=complete,
    )
    if not compliant(draft, retrieval.citation_url):
        name = intent.scheme_name or fallback.name
        text, url = not_found(name, retrieval.citation_url or (scheme.url if scheme else fallback.url))
        return _store(settings, query_id, intent.label, text, url, False, model_id, stamp)
    shown = move_inline_link(draft, retrieval.citation_url, intent.scheme_name or fallback.name)
    return _store(
        settings,
        query_id,
        intent.label,
        shown,
        retrieval.citation_url,
        False,
        model_id,
        stamp,
    )


def _chunks_support(intent: Intent, retrieval: Retrieval) -> bool:
    """Fail closed when the retrieved text does not contain the asked fact."""
    if intent.label == "how_to":
        phrases = FACT_PHRASES["statement_howto"]
    elif intent.fact_type:
        phrases = FACT_PHRASES[intent.fact_type]
    else:
        return bool(retrieval.hits)
    blob = " ".join(hit.text.lower() for hit in retrieval.hits)
    return any(phrase.lower() in blob for phrase in phrases)


def _missing_fact(intent: Intent, scheme: Scheme | None, fallback: Scheme) -> tuple[str, str]:
    if scheme is not None:
        return not_found(scheme.name, scheme.url)
    if intent.label == "how_to":
        return not_found(fallback.name, fallback.url)
    return out_of_corpus(fallback)


def _factsheet_target(settings: Settings, scheme: Scheme) -> tuple[str, str]:
    factsheet = _stored_factsheet(settings.root, scheme.slug)
    if factsheet:
        return scheme.name, factsheet
    return scheme.name, scheme.url


def _stored_factsheet(root: Path, slug: str) -> str:
    current_path = root / "data" / "artifacts" / "current.json"
    if not current_path.is_file():
        return ""
    current = json.loads(current_path.read_text(encoding="utf-8"))
    page = root / "data" / "artifacts" / "load" / current["run_id"] / f"{slug}.json"
    if not page.is_file():
        return ""
    return str(json.loads(page.read_text(encoding="utf-8")).get("factsheet_url") or "")


def _scheme_by_slug(settings: Settings, slug: str) -> Scheme | None:
    for scheme in settings.schemes:
        if scheme.slug == slug:
            return scheme
    return None


def _source_stamp(root: Path) -> str:
    path = root / "data" / "artifacts" / "current.json"
    if not path.is_file():
        return ""
    loaded_at = str(json.loads(path.read_text(encoding="utf-8")).get("loaded_at", ""))
    return loaded_at[:10]


def _store(
    settings: Settings,
    query_id: str,
    label: str,
    text: str,
    citation_url: str,
    refusal: bool,
    model_id: str,
    source_stamp: str,
) -> Answer:
    payload = {
        "query_id": query_id,
        "intent": label,
        "text": text,
        "citation_url": citation_url,
        "refusal": refusal,
        "model_id": model_id,
        "source_stamp": source_stamp,
    }
    path = settings.root / "data" / "artifacts" / "generate" / f"{query_id}.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
    return Answer(query_id, label, refusal, text, citation_url, model_id, source_stamp)


def _query_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return stamp + uuid.uuid4().hex[:6]


def _print_answer(answer: Answer) -> None:
    print(answer.text)
    if answer.source_stamp:
        print(f"Last updated from sources: {answer.source_stamp}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a factual question.")
    parser.add_argument("--query", default="")
    args = parser.parse_args()
    if args.query.strip():
        print("Answer:", end=" ")
        _print_answer(ask(args.query))
        return
    print("Facts-only. No investment advice.")
    print("Type a question and press Enter. Type exit to stop.")
    print()
    while True:
        try:
            question = input("Question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if question.lower() in {"exit", "quit"}:
            return
        if not question:
            continue
        print("Answer:", end=" ")
        try:
            _print_answer(ask(question))
        except Exception as exc:
            print(exc)
            print()


if __name__ == "__main__":
    main()
