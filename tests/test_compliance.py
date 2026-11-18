import json

import chromadb

from src.config import Settings, load_settings
from src.pipeline.ask import ask
from src.pipeline.generate import compliant
from src.pipeline.retrieve import retrieve

LARGE_URL = "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
LIQUID_URL = "https://groww.in/mutual-funds/hdfc-liquid-fund-direct-growth"
LARGE_ID = "hdfc-large-cap-fund-direct-growth:expense_ratio:0"
LIQUID_ID = "hdfc-liquid-fund-direct-growth:expense_ratio:0"


class AlwaysLarge:
    def encode(self, texts, batch_size=32, show_progress_bar=False):
        return [[1.0, 0.0] for _ in texts]


class FakeEncoder:
    def encode(self, texts, batch_size=32, show_progress_bar=False):
        vectors = []
        for text in texts:
            lowered = text.lower()
            if "large cap" in lowered:
                vectors.append([1.0, 0.0])
            elif "liquid" in lowered:
                vectors.append([0.0, 1.0])
            else:
                vectors.append([0.0, 0.0])
        return vectors


def test_retrieval_returns_the_matching_scheme_chunk(tmp_path):
    settings = _settings(tmp_path)
    _build_index(tmp_path, settings)
    found = retrieve(
        "Expense ratio of HDFC Large Cap Fund?",
        "hdfc-large-cap-fund-direct-growth",
        query_id="q-large",
        settings=settings,
        encoder=FakeEncoder(),
    )
    assert found.above_threshold
    assert found.hits[0].chunk_id == LARGE_ID
    assert found.citation_url == LARGE_URL


def test_scheme_filter_excludes_the_other_fund(tmp_path):
    settings = _settings(tmp_path)
    _build_index(tmp_path, settings)
    found = retrieve(
        "Expense ratio of HDFC Large Cap Fund?",
        "hdfc-liquid-fund-direct-growth",
        query_id="q-liquid",
        settings=settings,
        encoder=FakeEncoder(),
    )
    assert all(hit.chunk_id != LARGE_ID for hit in found.hits)
    assert found.hits[0].chunk_id == LIQUID_ID


def test_two_urls_are_replaced_and_one_url_is_kept(tmp_path):
    settings = _settings(tmp_path)
    _build_index(tmp_path, settings)
    citation = LARGE_URL
    kept = ask(
        "Expense ratio of HDFC Large Cap Fund?",
        settings=settings,
        encoder=FakeEncoder(),
        complete=lambda messages, settings: (
            "The expense ratio is 1.0%. "
            "See [HDFC Large Cap Fund Direct Growth — Groww](" + citation + ")."
        ),
    )
    assert citation in kept.text
    assert kept.refusal is False
    fact, _, rest = kept.text.partition("\n")
    assert citation not in fact
    assert rest.strip().startswith("###### Source link")
    assert citation in rest

    replaced = ask(
        "Expense ratio of HDFC Large Cap Fund?",
        settings=settings,
        encoder=FakeEncoder(),
        complete=lambda messages, settings: f"See {citation} and {LIQUID_URL}. Extra. Fourth sentence.",
    )
    assert LIQUID_URL not in replaced.text
    assert "couldn’t find that fact" in replaced.text


def test_unretrieved_url_and_fourth_sentence_are_discarded(tmp_path):
    settings = _settings(tmp_path)
    _build_index(tmp_path, settings)

    replaced = ask(
        "Expense ratio of HDFC Large Cap Fund?",
        settings=settings,
        encoder=FakeEncoder(),
        complete=lambda messages, settings: f"Look here: [Other — Groww]({LIQUID_URL}).",
    )
    assert LIQUID_URL not in replaced.text
    assert "couldn’t find that fact" in replaced.text
    assert replaced.citation_url == LARGE_URL

    long_reply = ask(
        "Expense ratio of HDFC Large Cap Fund?",
        settings=settings,
        encoder=FakeEncoder(),
        complete=lambda messages, settings: (
            "One. Two. Three. Four. "
            "See [HDFC Large Cap Fund Direct Growth — Groww](" + LARGE_URL + ")."
        ),
    )
    assert "Four." not in long_reply.text
    assert "couldn’t find that fact" in long_reply.text


def test_missing_fact_and_howto_do_not_invent(tmp_path):
    settings = _settings(tmp_path)
    _build_index(tmp_path, settings)
    calls = {"n": 0}

    def complete(messages, settings):
        calls["n"] += 1
        return "Invented exit load is 9%. Open the app and download the file."

    missing = ask(
        "What is the exit load of HDFC Large Cap Fund?",
        settings=settings,
        encoder=FakeEncoder(),
        complete=complete,
    )
    assert calls["n"] == 0
    assert missing.citation_url == LARGE_URL
    assert "9%" not in missing.text
    assert "couldn’t find that fact" in missing.text

    howto = ask(
        "How do I download a capital-gains statement?",
        settings=settings,
        encoder=AlwaysLarge(),
        complete=complete,
    )
    assert calls["n"] == 0
    assert "download the file" not in howto.text
    assert "couldn’t find that fact" in howto.text
    assert howto.citation_url == LARGE_URL


def test_templates_do_not_call_the_model(tmp_path):
    settings = _settings(tmp_path)
    calls = {"n": 0}

    def complete(messages, settings):
        calls["n"] += 1
        return "The expense ratio is 1.0% and the other fund returned 20%."

    no_scheme = ask("What is the expense ratio?", settings=settings, complete=complete)
    assert calls["n"] == 0
    assert "Say which covered HDFC scheme" in no_scheme.text
    assert "1.0%" not in no_scheme.text

    outside = ask("Expense ratio of SBI Bluechip Fund?", settings=settings, complete=complete)
    assert calls["n"] == 0
    assert outside.intent == "out_of_corpus"
    assert "1.0%" not in outside.text
    assert outside.citation_url == LARGE_URL

    compared = ask(
        "Which of these two funds performed better, HDFC Large Cap or HDFC Liquid Fund?",
        settings=settings,
        complete=complete,
    )
    assert calls["n"] == 0
    assert compared.intent == "redirect_factsheet"
    assert compared.citation_url == LARGE_URL
    assert LIQUID_URL not in compared.text
    assert "20%" not in compared.text

    beating = ask("Is this beating the benchmark?", settings=settings, complete=complete)
    assert beating.intent == "redirect_factsheet"
    assert "20%" not in beating.text
    assert beating.citation_url == LARGE_URL


def test_model_id_is_read_from_env_on_each_answer(tmp_path):
    settings = _settings(tmp_path)
    _build_index(tmp_path, settings)
    env = tmp_path / ".env"
    reply = (
        "The expense ratio is 1.0%. "
        "See [HDFC Large Cap Fund Direct Growth — Groww](" + LARGE_URL + ")."
    )

    env.write_text("LLM_MODEL_ID=first-model\n", encoding="utf-8")
    first = ask(
        "Expense ratio of HDFC Large Cap Fund?",
        settings=settings,
        encoder=FakeEncoder(),
        complete=lambda messages, settings: reply,
    )
    env.write_text("LLM_MODEL_ID=second-model\n", encoding="utf-8")
    second = ask(
        "Expense ratio of HDFC Large Cap Fund?",
        settings=settings,
        encoder=FakeEncoder(),
        complete=lambda messages, settings: reply,
    )
    assert first.model_id == "first-model"
    assert second.model_id == "second-model"


def test_queries_use_the_collection_named_in_current_json(tmp_path):
    settings = _settings(tmp_path)
    _build_index(tmp_path, settings)
    client = chromadb.PersistentClient(path=str(settings.chroma_path))
    other = client.create_collection("other-model", metadata={"hnsw:space": "cosine"})
    other.upsert(
        ids=["other:expense_ratio:0"],
        embeddings=[[1.0, 0.0]],
        documents=["Other Fund. Expense ratio: 9.99"],
        metadatas=[
            {
                "chunk_id": "other:expense_ratio:0",
                "scheme_slug": "hdfc-large-cap-fund-direct-growth",
                "scheme_name": "Other Fund",
                "fact_type": "expense_ratio",
                "source_url": "https://example.com/other",
                "factsheet_url": "",
            }
        ],
    )
    found = retrieve(
        "Expense ratio of HDFC Large Cap Fund?",
        "hdfc-large-cap-fund-direct-growth",
        query_id="q-current",
        settings=settings,
        encoder=FakeEncoder(),
    )
    assert found.collection == "test-faq"
    assert found.hits[0].chunk_id == LARGE_ID
    assert "9.99" not in found.hits[0].text


def test_advice_refusal_is_stored_as_a_template(tmp_path):
    settings = _settings(tmp_path)
    answer = ask(
        "Should I buy HDFC Small Cap?",
        settings=settings,
        complete=lambda messages, settings: "buy it",
    )
    assert answer.refusal
    assert answer.model_id == "template"
    assert "Liquid" not in answer.text
    artifact = json.loads(
        (tmp_path / "data" / "artifacts" / "generate" / f"{answer.query_id}.json").read_text(encoding="utf-8")
    )
    assert artifact["refusal"] is True
    assert artifact["model_id"] == "template"


def test_sentence_and_link_check():
    url = LARGE_URL
    assert compliant(
        "The expense ratio is 1.0%. See [HDFC Large Cap Fund Direct Growth — Groww](" + url + ").",
        url,
    )
    assert not compliant(f"See {url} and {LIQUID_URL}.", url)


def _settings(root):
    real = load_settings()
    return Settings(
        root=root,
        embedding_model=real.embedding_model,
        chroma_path=root / "chroma",
        llm_provider="groq",
        top_k=4,
        min_score=0.35,
        request_timeout_seconds=5,
        llm_model_id="test-model",
        schemes=real.schemes,
    )


def _build_index(root, settings):
    (root / "data" / "artifacts").mkdir(parents=True)
    (root / "data" / "artifacts" / "current.json").write_text(
        json.dumps(
            {
                "run_id": "test",
                "loaded_at": "2026-11-16T00:00:00Z",
                "embedding_model": settings.embedding_model,
                "collection": "test-faq",
                "chunk_file": "data/artifacts/chunks/test.jsonl",
                "vector_count": 2,
            }
        ),
        encoding="utf-8",
    )
    client = chromadb.PersistentClient(path=str(settings.chroma_path))
    collection = client.create_collection("test-faq", metadata={"hnsw:space": "cosine"})
    collection.upsert(
        ids=[LARGE_ID, LIQUID_ID],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        documents=[
            "HDFC Large Cap Fund Direct Growth. Expense ratio: 1.0",
            "HDFC Liquid Fund Direct Growth. Expense ratio: 0.2",
        ],
        metadatas=[
            {
                "chunk_id": LARGE_ID,
                "scheme_slug": "hdfc-large-cap-fund-direct-growth",
                "scheme_name": "HDFC Large Cap Fund Direct Growth",
                "fact_type": "expense_ratio",
                "source_url": LARGE_URL,
                "factsheet_url": "",
            },
            {
                "chunk_id": LIQUID_ID,
                "scheme_slug": "hdfc-liquid-fund-direct-growth",
                "scheme_name": "HDFC Liquid Fund Direct Growth",
                "fact_type": "expense_ratio",
                "source_url": LIQUID_URL,
                "factsheet_url": "",
            },
        ],
    )
