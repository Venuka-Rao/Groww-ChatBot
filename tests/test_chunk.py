import json
from pathlib import Path

from src.config import Settings
from src.pipeline.chunk import chunk_page, chunk_run

LARGE_CAP = {
    "slug": "hdfc-large-cap-fund-direct-growth",
    "scheme_name": "HDFC Large Cap Fund Direct Growth",
    "requested_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    "http_status": 200,
    "factsheet_url": "",
    "error": "",
    "text": "\n".join(
        [
            "Scheme name: HDFC Large Cap Fund Direct Growth",
            "Expense ratio: 1.0",
            "Base expense ratio: 0.82",
            "Exit load: Exit load of 1% if redeemed within 1 year",
            "Minimum SIP: 100",
            "Minimum investment: 100",
            "Benchmark: NIFTY 100 TRI",
            "Benchmark name: NIFTY 100 Total Return Index",
            "Riskometer: Very High",
        ]
    ),
}

ELSS = {
    "slug": "hdfc-elss-tax-saver-fund-direct-growth",
    "scheme_name": "HDFC ELSS Tax Saver Fund Direct Growth",
    "requested_url": "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-growth",
    "http_status": 200,
    "factsheet_url": "https://www.hdfcfund.com/docs/factsheet.pdf",
    "error": "",
    "text": "\n".join(
        [
            "Scheme name: HDFC ELSS Tax Saver Fund Direct Growth",
            "Lock-in: 3 years",
        ]
    ),
}


def test_labeled_facts_become_separate_chunks():
    chunks = chunk_page(LARGE_CAP)
    by_type = {chunk["fact_type"]: chunk for chunk in chunks}
    assert "Expense ratio: 1.0" in by_type["expense_ratio"]["text"]
    assert "Base expense ratio: 0.82" in by_type["expense_ratio"]["text"]
    assert by_type["exit_load"]["chunk_id"].endswith(":exit_load:0")
    assert "Minimum SIP: 100" in by_type["min_sip"]["text"]
    assert "Minimum investment: 100" in by_type["min_sip"]["text"]
    assert "Benchmark name:" in by_type["benchmark"]["text"]
    assert by_type["riskometer"]["fact_type"] == "riskometer"
    assert all(chunk["text"].startswith("HDFC Large Cap Fund Direct Growth. ") for chunk in chunks)
    assert all(chunk["source_url"] == LARGE_CAP["requested_url"] for chunk in chunks)


def test_scheme_name_containing_elss_is_not_a_lock_in_chunk():
    chunks = chunk_page(ELSS)
    lock = next(chunk for chunk in chunks if chunk["fact_type"] == "lock_in")
    assert lock["text"].startswith("HDFC ELSS Tax Saver Fund Direct Growth. Lock-in:")
    assert lock["factsheet_url"].endswith("factsheet.pdf")
    scheme_line = next(chunk for chunk in chunks if "Scheme name:" in chunk["text"])
    assert scheme_line["fact_type"] == "other"


def test_two_pages_keep_their_own_chunk_ids():
    large = chunk_page(LARGE_CAP)
    elss = chunk_page(ELSS)
    large_ids = {chunk["chunk_id"] for chunk in large}
    elss_ids = {chunk["chunk_id"] for chunk in elss}
    assert large_ids.isdisjoint(elss_ids)
    assert all(chunk["scheme_slug"] == LARGE_CAP["slug"] for chunk in large)
    assert all(chunk["scheme_slug"] == ELSS["slug"] for chunk in elss)


def test_page_without_known_labels_emits_other_chunks():
    record = {
        "slug": "hdfc-overnight-fund-direct-growth",
        "scheme_name": "HDFC Overnight Fund Direct Growth",
        "requested_url": "https://groww.in/mutual-funds/hdfc-overnight-fund-direct-growth",
        "factsheet_url": "",
        "text": "Overview\nThis fund invests in overnight instruments.\nHoldings\nTreasury bills.",
    }
    chunks = chunk_page(record)
    assert chunks
    assert all(chunk["fact_type"] == "other" for chunk in chunks)
    assert chunks[0]["text"].startswith("HDFC Overnight Fund Direct Growth. Overview")


def test_empty_and_failed_pages_are_skipped(tmp_path):
    run_id = "20261116T153518Z"
    load_dir = tmp_path / "data" / "artifacts" / "load" / run_id
    load_dir.mkdir(parents=True)
    _write(load_dir / "hdfc-large-cap-fund-direct-growth.json", LARGE_CAP)
    empty = dict(ELSS)
    empty["text"] = ""
    empty["error"] = "HTTP 404"
    empty["http_status"] = 404
    _write(load_dir / "hdfc-elss-tax-saver-fund-direct-growth.json", empty)
    _write(
        load_dir / "manifest.json",
        {
            "run_id": run_id,
            "successes": [LARGE_CAP["slug"]],
            "failures": [{"slug": ELSS["slug"], "error": "HTTP 404"}],
        },
    )
    settings = Settings(
        root=tmp_path,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        chroma_path=tmp_path / "chroma",
        llm_provider="groq",
        top_k=4,
        min_score=0.35,
        request_timeout_seconds=5,
        llm_model_id="",
        schemes=(),
    )
    path = chunk_run(run_id, settings)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows
    assert all(row["scheme_slug"] == LARGE_CAP["slug"] for row in rows)


def test_chunk_module_does_not_embed_or_call_a_model():
    source = Path("src/pipeline/chunk.py").read_text(encoding="utf-8").lower()
    assert "chromadb" not in source
    assert "groq" not in source
    assert "sentence_transformers" not in source


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")
