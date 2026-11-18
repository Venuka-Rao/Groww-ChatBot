"""Embed chunk text and store the vectors in a persistent Chroma collection.

The collection name includes the embedding model id and the run id. A second
run against the same collection skips encoding when the vector count already
matches the chunk file.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import chromadb

from src.config import Settings, load_settings
from src.pipeline.chunk import latest_run_id

BATCH_SIZE = 32


def embed_run(run_id: str | None = None, settings: Settings | None = None, encoder=None) -> str:
    settings = settings or load_settings()
    run_id = run_id or latest_run_id(settings.root)
    chunk_path = settings.root / "data" / "artifacts" / "chunks" / f"{run_id}.jsonl"
    if not chunk_path.is_file():
        raise FileNotFoundError(f"Missing chunk file: {chunk_path}")
    chunks = _read_chunks(chunk_path)
    if not chunks:
        raise ValueError(f"Chunk file is empty: {chunk_path}")

    name = collection_name(settings.embedding_model, run_id)
    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(settings.chroma_path))
    collection, skipped = _prepare_collection(client, name, settings.embedding_model, len(chunks))

    if not skipped:
        vectors = _encode(chunks, settings.embedding_model, encoder)
        _upsert(collection, chunks, vectors)

    vector_count = collection.count()
    chunk_file = chunk_path.relative_to(settings.root).as_posix()
    _write_json(
        settings.root / "data" / "artifacts" / "embed" / f"{run_id}.json",
        {
            "run_id": run_id,
            "embedding_model": settings.embedding_model,
            "collection": name,
            "chunk_file": chunk_file,
            "vector_count": vector_count,
            "skipped_reembed": skipped,
        },
    )
    _write_json(
        settings.root / "data" / "artifacts" / "current.json",
        {
            "run_id": run_id,
            "loaded_at": _loaded_at(settings.root, run_id),
            "embedding_model": settings.embedding_model,
            "collection": name,
            "chunk_file": chunk_file,
            "vector_count": vector_count,
        },
    )
    return name


def collection_name(model_id: str, run_id: str) -> str:
    """hdfc-<model>-<run_id>, at most 63 characters, from the configured model id."""
    model = re.sub(r"[^a-z0-9]+", "-", model_id.lower()).strip("-")
    org_prefix = "sentence-transformers-"
    if model.startswith(org_prefix):
        model = model[len(org_prefix):]
    suffix = re.sub(r"[^a-z0-9]+", "", run_id.lower())
    base = f"hdfc-{model}-{suffix}"
    if len(base) <= 63:
        return base
    room = 63 - len(suffix) - len("hdfc-") - 1
    trimmed = model[:room].strip("-")
    return f"hdfc-{trimmed}-{suffix}"


def _prepare_collection(client, name: str, model_id: str, chunk_count: int):
    metadata = {"hnsw:space": "cosine", "embedding_model": model_id}
    existing = _collection_names(client)
    if name in existing:
        collection = client.get_collection(name)
        if collection.count() == chunk_count:
            return collection, True
        client.delete_collection(name)
    collection = client.create_collection(name=name, metadata=metadata)
    return collection, False


def _collection_names(client) -> set[str]:
    names = set()
    for item in client.list_collections():
        names.add(item.name if hasattr(item, "name") else str(item))
    return names


def _encode(chunks: list[dict], model_id: str, encoder) -> list[list[float]]:
    if encoder is None:
        from sentence_transformers import SentenceTransformer

        encoder = SentenceTransformer(model_id)
    texts = [chunk["text"] for chunk in chunks]
    encoded = encoder.encode(texts, batch_size=BATCH_SIZE, show_progress_bar=False)
    return [_as_floats(vector) for vector in encoded]


def _upsert(collection, chunks: list[dict], vectors: list[list[float]]) -> None:
    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start : start + BATCH_SIZE]
        collection.upsert(
            ids=[chunk["chunk_id"] for chunk in batch],
            embeddings=vectors[start : start + BATCH_SIZE],
            documents=[chunk["text"] for chunk in batch],
            metadatas=[_metadata(chunk) for chunk in batch],
        )


def _metadata(chunk: dict) -> dict:
    return {
        "chunk_id": str(chunk["chunk_id"]),
        "scheme_slug": str(chunk["scheme_slug"]),
        "scheme_name": str(chunk["scheme_name"]),
        "fact_type": str(chunk["fact_type"]),
        "source_url": str(chunk["source_url"]),
        "factsheet_url": str(chunk.get("factsheet_url") or ""),
    }


def _read_chunks(path: Path) -> list[dict]:
    chunks = []
    seen = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        chunk = json.loads(line)
        chunk_id = chunk["chunk_id"]
        if chunk_id in seen:
            raise ValueError(f"Duplicate chunk id: {chunk_id}")
        seen.add(chunk_id)
        chunks.append(chunk)
    return chunks


def _loaded_at(root: Path, run_id: str) -> str:
    manifest_path = root / "data" / "artifacts" / "load" / run_id / "manifest.json"
    if not manifest_path.is_file():
        return ""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return str(manifest.get("loaded_at", ""))


def _as_floats(vector) -> list[float]:
    if hasattr(vector, "tolist"):
        vector = vector.tolist()
    return [float(value) for value in vector]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Embed a chunk file into Chroma.")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    settings = load_settings()
    run_id = args.run_id or latest_run_id(settings.root)
    name = embed_run(run_id, settings)
    artifact = json.loads(
        (settings.root / "data" / "artifacts" / "embed" / f"{run_id}.json").read_text(encoding="utf-8")
    )
    print(f"collection: {name}")
    print(f"vector_count: {artifact['vector_count']}")
    print(f"skipped_reembed: {artifact['skipped_reembed']}")


if __name__ == "__main__":
    main()
