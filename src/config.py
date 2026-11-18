"""Load settings and the 25-scheme allowlist from the repo root."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SCHEME_COUNT = 25
ALLOWED_PROVIDERS = ("groq",)
REQUIRED_SETTINGS = (
    "embedding_model",
    "chroma_path",
    "llm_provider",
    "top_k",
    "min_score",
    "request_timeout_seconds",
)


@dataclass(frozen=True)
class Scheme:
    slug: str
    name: str
    url: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class Settings:
    root: Path
    embedding_model: str
    chroma_path: Path
    llm_provider: str
    top_k: int
    min_score: float
    request_timeout_seconds: float
    llm_model_id: str
    schemes: tuple[Scheme, ...]


def load_settings(root: Path | None = None) -> Settings:
    """Read config from the repo root, independent of the process cwd."""
    repo_root = (root or ROOT).resolve()
    load_dotenv(repo_root / ".env")
    raw = _read_yaml(repo_root / "config" / "settings.yaml")
    _require_settings(raw)
    provider = str(raw["llm_provider"]).strip().lower()
    if provider not in ALLOWED_PROVIDERS:
        allowed = ", ".join(ALLOWED_PROVIDERS)
        raise ValueError(f"llm_provider must be one of: {allowed}")
    schemes = load_schemes(repo_root)
    chroma_path = Path(str(raw["chroma_path"]))
    if not chroma_path.is_absolute():
        chroma_path = repo_root / chroma_path
    return Settings(
        root=repo_root,
        embedding_model=str(raw["embedding_model"]).strip(),
        chroma_path=chroma_path,
        llm_provider=provider,
        top_k=int(raw["top_k"]),
        min_score=float(raw["min_score"]),
        request_timeout_seconds=float(raw["request_timeout_seconds"]),
        llm_model_id=os.getenv("LLM_MODEL_ID", "").strip(),
        schemes=schemes,
    )


def load_schemes(root: Path | None = None) -> tuple[Scheme, ...]:
    repo_root = (root or ROOT).resolve()
    raw = _read_yaml(repo_root / "config" / "urls.yaml")
    entries = raw.get("schemes")
    if not isinstance(entries, list):
        raise ValueError("config/urls.yaml must contain a schemes list")
    schemes = tuple(_parse_scheme(entry) for entry in entries)
    _validate_schemes(schemes)
    return schemes


def _read_yaml(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"Missing config file: {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path.name} must be a mapping")
    return loaded


def _require_settings(raw: dict) -> None:
    missing = [key for key in REQUIRED_SETTINGS if raw.get(key) in (None, "")]
    if missing:
        raise ValueError("settings.yaml is missing: " + ", ".join(missing))


def _parse_scheme(entry: object) -> Scheme:
    if not isinstance(entry, dict):
        raise ValueError("Each scheme must be a mapping")
    slug = str(entry.get("slug", "")).strip()
    name = str(entry.get("name", "")).strip()
    url = str(entry.get("url", "")).strip()
    aliases = entry.get("aliases")
    if not slug or not name or not url:
        raise ValueError("Each scheme needs slug, name, and url")
    if not isinstance(aliases, list) or not aliases:
        raise ValueError(f"{slug} needs a non-empty aliases list")
    cleaned = tuple(str(alias).strip() for alias in aliases)
    if any(not alias for alias in cleaned):
        raise ValueError(f"{slug} has a blank alias")
    return Scheme(slug=slug, name=name, url=url, aliases=cleaned)


def _validate_schemes(schemes: tuple[Scheme, ...]) -> None:
    if len(schemes) != EXPECTED_SCHEME_COUNT:
        raise ValueError(
            f"urls.yaml must list {EXPECTED_SCHEME_COUNT} schemes, found {len(schemes)}"
        )
    slugs = [scheme.slug for scheme in schemes]
    urls = [scheme.url for scheme in schemes]
    if len(set(slugs)) != len(slugs):
        raise ValueError("urls.yaml has a duplicate slug")
    if len(set(urls)) != len(urls):
        raise ValueError("urls.yaml has a duplicate url")
    for scheme in schemes:
        parsed = urlparse(scheme.url)
        expected = f"/mutual-funds/{scheme.slug}"
        if parsed.scheme != "https" or parsed.netloc != "groww.in" or parsed.path != expected:
            raise ValueError(f"{scheme.slug} URL must be https://groww.in{expected}")


def main() -> None:
    settings = load_settings()
    model_id = settings.llm_model_id or "(not set)"
    print(f"embedding_model: {settings.embedding_model}")
    print(f"llm_provider: {settings.llm_provider}")
    print(f"schemes: {len(settings.schemes)}")
    print(f"llm_model_id: {model_id}")


if __name__ == "__main__":
    main()
