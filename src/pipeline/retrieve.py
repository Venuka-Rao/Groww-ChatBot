"""Embed a question and search the collection named in current.json."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import chromadb

from src.config import Settings, load_settings

_ENCODERS: dict = {}


@dataclass
class Hit:
    chunk_id: str
    score: float
    fact_type: str
    source_url: str
    scheme_name: str
    text: str


@dataclass
class Retrieval:
    query_id: str
    query: str
    scheme_slug: str
    embedding_model: str
    collection: str
    hits: list[Hit] = field(default_factory=list)
    citation_url: str = ""
    above_threshold: bool = False


def retrieve(
    query: str,
    scheme_slug: str | None = None,
    *,
    query_id: str,
    settings: Settings | None = None,
    encoder=None,
) -> Retrieval:
    settings = settings or load_settings()
    current = _read_current(settings.root)
    if current["embedding_model"] != settings.embedding_model:
        raise ValueError("current.json embedding model does not match settings.yaml")

    model_id = current["embedding_model"]
    vector = _encode_query(query, model_id, encoder)
    client = chromadb.PersistentClient(path=str(settings.chroma_path))
    collection = client.get_collection(current["collection"])
    query_kwargs = {
        "query_embeddings": [vector],
        "n_results": settings.top_k,
        "include": ["documents", "metadatas", "distances"],
    }
    if scheme_slug:
        query_kwargs["where"] = {"scheme_slug": scheme_slug}
    result = collection.query(**query_kwargs)
    hits = _hits(result)
    winner = hits[0] if hits else None
    above = winner is not None and winner.score >= settings.min_score
    retrieval = Retrieval(
        query_id=query_id,
        query=query,
        scheme_slug=scheme_slug or "",
        embedding_model=model_id,
        collection=current["collection"],
        hits=hits,
        citation_url=winner.source_url if winner else "",
        above_threshold=above,
    )
    _write_trace(settings.root, retrieval)
    return retrieval


def _encode_query(query: str, model_id: str, encoder) -> list[float]:
    if encoder is None:
        encoder = _ENCODERS.get(model_id)
        if encoder is None:
            from sentence_transformers import SentenceTransformer

            encoder = SentenceTransformer(model_id)
            _ENCODERS[model_id] = encoder
    encoded = encoder.encode([query], batch_size=32, show_progress_bar=False)
    vector = encoded[0]
    if hasattr(vector, "tolist"):
        vector = vector.tolist()
    return [float(value) for value in vector]


def _hits(result: dict) -> list[Hit]:
    ids = (result.get("ids") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    documents = (result.get("documents") or [[]])[0]
    hits = []
    for chunk_id, distance, metadata, document in zip(ids, distances, metadatas, documents):
        metadata = metadata or {}
        hits.append(
            Hit(
                chunk_id=chunk_id,
                score=1 - float(distance),
                fact_type=str(metadata.get("fact_type", "")),
                source_url=str(metadata.get("source_url", "")),
                scheme_name=str(metadata.get("scheme_name", "")),
                text=str(document or ""),
            )
        )
    hits.sort(key=lambda hit: hit.score, reverse=True)
    return hits


def _read_current(root: Path) -> dict:
    path = root / "data" / "artifacts" / "current.json"
    if not path.is_file():
        raise FileNotFoundError("current.json is missing. Run ingest first.")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_trace(root: Path, retrieval: Retrieval) -> None:
    payload = {
        "query_id": retrieval.query_id,
        "query": retrieval.query,
        "scheme_slug": retrieval.scheme_slug,
        "embedding_model": retrieval.embedding_model,
        "collection": retrieval.collection,
        "hits": [
            {
                "chunk_id": hit.chunk_id,
                "score": round(hit.score, 4),
                "fact_type": hit.fact_type,
                "source_url": hit.source_url,
            }
            for hit in retrieval.hits
        ],
        "citation_url": retrieval.citation_url,
        "above_threshold": retrieval.above_threshold,
    }
    path = root / "data" / "artifacts" / "retrieve" / f"{retrieval.query_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
