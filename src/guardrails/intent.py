"""Rule-based question labels. No model call."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.config import Scheme
from src.facts import ADVICE_PHRASES, FACT_PHRASES, PERFORMANCE_PHRASES

OTHER_AMCS = (
    "parag parikh",
    "motilal",
    "bandhan",
    "mirae",
    "nippon",
    "quant",
    "kotak",
    "axis",
    "icici",
    "sbi",
    "uti",
)


@dataclass(frozen=True)
class Intent:
    label: str
    scheme_slug: str = ""
    scheme_name: str = ""
    fact_type: str = ""
    second_scheme_slug: str = ""


def classify(text: str, schemes: tuple[Scheme, ...]) -> Intent:
    lowered = " ".join(text.lower().split())
    found = _match_schemes(lowered, schemes)
    first = found[0] if found else None
    second = found[1] if len(found) > 1 else None
    fact_type = _match_fact(lowered)

    def intent(label: str) -> Intent:
        return Intent(
            label=label,
            scheme_slug=first.slug if first else "",
            scheme_name=first.name if first else "",
            fact_type=fact_type,
            second_scheme_slug=second.slug if second else "",
        )

    if _any_phrase(lowered, ADVICE_PHRASES):
        return intent("refuse_advice")
    compared = second is not None and re.search(r"\b(which|better|vs|versus)\b", lowered)
    if _any_phrase(lowered, PERFORMANCE_PHRASES) or compared:
        return intent("redirect_factsheet")
    if _any_phrase(lowered, FACT_PHRASES["statement_howto"]):
        return intent("how_to")
    if _outside_corpus(lowered, first):
        return intent("out_of_corpus")
    if fact_type and first:
        return intent("answer")
    if fact_type and first is None:
        return intent("answer")
    if first is not None:
        return intent("answer")
    return intent("out_of_corpus")


def _match_schemes(text: str, schemes: tuple[Scheme, ...]) -> list[Scheme]:
    candidates: list[tuple[int, int, Scheme]] = []
    for scheme in schemes:
        for alias in (scheme.name, *scheme.aliases):
            needle = alias.lower()
            start = text.find(needle)
            if start >= 0:
                candidates.append((start, -len(needle), scheme))
    candidates.sort()
    found: list[Scheme] = []
    spans: list[tuple[int, int]] = []
    seen: set[str] = set()
    for start, neg_len, scheme in candidates:
        end = start + (-neg_len)
        if any(start < span_end and end > span_start for span_start, span_end in spans):
            continue
        spans.append((start, end))
        if scheme.slug in seen:
            continue
        seen.add(scheme.slug)
        found.append(scheme)
    return found


def _match_fact(text: str) -> str:
    best = ""
    best_len = 0
    for fact_type, phrases in FACT_PHRASES.items():
        for phrase in phrases:
            if len(phrase) > best_len and _contains_phrase(text, phrase):
                best = fact_type
                best_len = len(phrase)
    return best


def _outside_corpus(text: str, matched: Scheme | None) -> bool:
    if matched is not None or "fund" not in text:
        return False
    if "hdfc" in text:
        return True
    return any(_contains_phrase(text, amc) for amc in OTHER_AMCS)


def _any_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    return any(_contains_phrase(text, phrase) for phrase in phrases)


def _contains_phrase(text: str, phrase: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(phrase.lower()) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None
