from pathlib import Path

import pytest
import yaml

from src.config import load_settings


def test_loads_25_unique_groww_urls_from_repo_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    settings = load_settings()
    urls = [scheme.url for scheme in settings.schemes]
    assert len(urls) == 25
    assert len(set(urls)) == 25
    assert all(url.startswith("https://groww.in/mutual-funds/") for url in urls)
    assert settings.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
    assert settings.llm_provider == "groq"
    assert settings.root == Path(__file__).resolve().parents[1]


def test_unknown_provider_is_rejected(tmp_path, monkeypatch):
    _write_fixture(tmp_path, provider="local-llm")
    monkeypatch.delenv("LLM_MODEL_ID", raising=False)
    with pytest.raises(ValueError, match="llm_provider"):
        load_settings(tmp_path)


def test_duplicate_url_is_rejected(tmp_path):
    _write_fixture(tmp_path, duplicate_url=True)
    with pytest.raises(ValueError, match="duplicate url"):
        load_settings(tmp_path)


def test_non_groww_url_is_rejected(tmp_path):
    _write_fixture(tmp_path, bad_host=True)
    with pytest.raises(ValueError, match="groww.in"):
        load_settings(tmp_path)


def _write_fixture(root: Path, provider="groq", duplicate_url=False, bad_host=False):
    config = root / "config"
    config.mkdir()
    (config / "settings.yaml").write_text(
        "\n".join(
            [
                "embedding_model: sentence-transformers/all-MiniLM-L6-v2",
                "chroma_path: data/chroma",
                f"llm_provider: {provider}",
                "top_k: 4",
                "min_score: 0.35",
                "request_timeout_seconds: 30",
                "",
            ]
        ),
        encoding="utf-8",
    )
    schemes = []
    for index in range(25):
        slug = f"hdfc-scheme-{index}-direct-growth"
        url = f"https://groww.in/mutual-funds/{slug}"
        if bad_host and index == 0:
            url = f"https://example.com/mutual-funds/{slug}"
        if duplicate_url and index == 1:
            url = "https://groww.in/mutual-funds/hdfc-scheme-0-direct-growth"
        schemes.append(
            {
                "slug": slug,
                "name": f"Scheme {index}",
                "url": url,
                "aliases": [f"Scheme {index}"],
            }
        )
    (config / "urls.yaml").write_text(
        yaml.safe_dump({"schemes": schemes}, sort_keys=False),
        encoding="utf-8",
    )
