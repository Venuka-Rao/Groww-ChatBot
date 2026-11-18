"""Fixed replies. These paths do not call a model."""

from __future__ import annotations

import re

from src.config import Scheme

_MD_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_BARE_URL = re.compile(r"https?://[^\s)\]]+")
_CITATION_ONLY = re.compile(
    r"^(see|you can check it here|you can read the scheme page here|"
    r"the published figures are on the official page|a covered page is here)\s*:?\s*$",
    re.IGNORECASE,
)


def with_source(text: str, name: str, url: str) -> str:
    label = name.strip()
    for suffix in (" — Groww", " - Groww"):
        if label.endswith(suffix):
            label = label[: -len(suffix)].strip()
    return f"{text.rstrip()}\n\n###### Source link\n[{label} — Groww]({url})"


def move_inline_link(text: str, url: str, name: str) -> str:
    """Move the one allowed citation onto the line under Source link."""
    label = name

    def grab(match: re.Match) -> str:
        nonlocal label
        if match.group(2) == url:
            label = match.group(1)
        return " "

    body = _BARE_URL.sub(" ", _MD_LINK.sub(grab, text))
    return with_source(_tidy(body), label, url)


def refuse_advice(scheme: Scheme | None, fallback: Scheme) -> tuple[str, str]:
    chosen = scheme or fallback
    text = (
        "I can only share published facts such as expense ratio, exit load, and lock-in. "
        "I can’t suggest whether to buy or sell."
    )
    return with_source(text, chosen.name, chosen.url), chosen.url


def redirect_factsheet(name: str, url: str) -> tuple[str, str]:
    text = "I can’t calculate or compare returns."
    return with_source(text, name, url), url


def out_of_corpus(fallback: Scheme) -> tuple[str, str]:
    text = (
        "That scheme is outside the 25 HDFC direct-growth pages this assistant covers. "
        "I can answer published facts for those pages only."
    )
    return with_source(text, fallback.name, fallback.url), fallback.url


def which_scheme(fallback: Scheme) -> tuple[str, str]:
    text = "Say which covered HDFC scheme you mean, and I can look up that published fact."
    return with_source(text, fallback.name, fallback.url), fallback.url


def not_found(name: str, url: str) -> tuple[str, str]:
    text = "I couldn’t find that fact on the official page."
    return with_source(text, name, url), url


def _tidy(body: str) -> str:
    body = re.sub(r"[ \t]+", " ", body)
    body = re.sub(r"\s+([.,;:!?])", r"\1", body)
    body = re.sub(r"\(\s*\)", "", body)
    kept: list[str] = []
    for part in re.split(r"(?<=[.!?])\s+", body.strip()):
        words = part.strip()
        core = words.rstrip(".!?:").strip()
        if not core or _CITATION_ONLY.match(core):
            continue
        kept.append(words)
    return " ".join(kept).strip()
