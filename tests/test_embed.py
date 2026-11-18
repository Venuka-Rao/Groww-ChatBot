import json

from src.config import Settings
from src.pipeline.embed import collection_name, embed_run


class FakeEncoder:
    def __init__(self):
        self.calls = 0

    def encode(self, texts, batch_size=32, show_progress_bar=False):
        assert batch_size == 32
        self.calls += 1
        return [[float(len(text)), 1.0] for text in texts]


def test_collection_name_changes_with_the_model_id():
    run_id = "20261116T153518Z"
    first = collection_name("sentence-transformers/all-MiniLM-L6-v2", run_id)
    second = collection_name("sentence-transformers/all-MiniLM-L12-v2", run_id)
    assert first == "hdfc-all-minilm-l6-v2-20261116t153518z"
    assert first != second
    assert len(first) <= 63


def test_embed_stores_metadata_and_skips_the_second_run(tmp_path):
    run_id = "20261116T153518Z"
    _write_run(tmp_path, run_id)
    settings = _settings(tmp_path)
    encoder = FakeEncoder()

    name = embed_run(run_id, settings, encoder)
    assert name == collection_name(settings.embedding_model, run_id)
    assert encoder.calls == 1

    artifact = json.loads((tmp_path / "data" / "artifacts" / "embed" / f"{run_id}.json").read_text(encoding="utf-8"))
    assert artifact["vector_count"] == 2
    assert artifact["skipped_reembed"] is False
    assert artifact["embedding_model"] == settings.embedding_model

    again = embed_run(run_id, settings, encoder)
    assert again == name
    assert encoder.calls == 1
    skipped = json.loads((tmp_path / "data" / "artifacts" / "embed" / f"{run_id}.json").read_text(encoding="utf-8"))
    assert skipped["skipped_reembed"] is True

    import chromadb

    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    collection = client.get_collection(name)
    stored = collection.get(ids=["hdfc-large-cap-fund-direct-growth:expense_ratio:0"])
    assert stored["metadatas"][0]["source_url"] == "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
    assert stored["metadatas"][0]["factsheet_url"] == ""


def _settings(root):
    return Settings(
        root=root,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        chroma_path=root / "chroma",
        llm_provider="groq",
        top_k=4,
        min_score=0.35,
        request_timeout_seconds=5,
        llm_model_id="",
        schemes=(),
    )


def _write_run(root, run_id):
    load_dir = root / "data" / "artifacts" / "load" / run_id
    load_dir.mkdir(parents=True)
    (load_dir / "manifest.json").write_text(
        json.dumps({"run_id": run_id, "loaded_at": "2026-11-16T15:35:28Z", "successes": [], "failures": []}),
        encoding="utf-8",
    )
    chunks = [
        {
            "chunk_id": "hdfc-large-cap-fund-direct-growth:expense_ratio:0",
            "scheme_slug": "hdfc-large-cap-fund-direct-growth",
            "scheme_name": "HDFC Large Cap Fund Direct Growth",
            "fact_type": "expense_ratio",
            "source_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
            "factsheet_url": "",
            "text": "HDFC Large Cap Fund Direct Growth. Expense ratio: 1.0",
        },
        {
            "chunk_id": "hdfc-large-cap-fund-direct-growth:exit_load:0",
            "scheme_slug": "hdfc-large-cap-fund-direct-growth",
            "scheme_name": "HDFC Large Cap Fund Direct Growth",
            "fact_type": "exit_load",
            "source_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
            "factsheet_url": "",
            "text": "HDFC Large Cap Fund Direct Growth. Exit load: 1%",
        },
    ]
    chunk_path = root / "data" / "artifacts" / "chunks" / f"{run_id}.jsonl"
    chunk_path.parent.mkdir(parents=True)
    chunk_path.write_text("\n".join(json.dumps(chunk) for chunk in chunks) + "\n", encoding="utf-8")
