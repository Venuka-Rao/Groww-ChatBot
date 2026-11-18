"""Search a saved MiniLM index. Used when Chroma is not on disk, including Vercel."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

from src.config import Settings, load_settings
from src.pipeline.retrieve import Hit, Retrieval

MODEL_DIR = "models/minilm"
INDEX_DIR = "data/index"
MAX_LENGTH = 256


def use_portable_index(settings: Settings) -> bool:
    if os.getenv("VERCEL"):
        return True
    if os.getenv("INDEX_BACKEND", "").strip().lower() == "portable":
        return True
    return not settings.chroma_path.exists()


def search_index(
    query: str,
    scheme_slug: str | None,
    *,
    query_id: str,
    settings: Settings,
) -> Retrieval:
    index = _load_index(settings.root)
    if index["embedding_model"] != settings.embedding_model:
        raise ValueError("portable index embedding model does not match settings.yaml")
    vector = encode_texts([query], settings.root)[0]
    scores = index["vectors"] @ vector
    order = np.argsort(-scores)
    hits: list[Hit] = []
    for position in order:
        chunk = index["chunks"][int(position)]
        if scheme_slug and chunk["scheme_slug"] != scheme_slug:
            continue
        hits.append(
            Hit(
                chunk_id=str(chunk["chunk_id"]),
                score=float(scores[int(position)]),
                fact_type=str(chunk.get("fact_type", "")),
                source_url=str(chunk.get("source_url", "")),
                scheme_name=str(chunk.get("scheme_name", "")),
                text=str(chunk.get("text", "")),
            )
        )
        if len(hits) >= settings.top_k:
            break
    winner = hits[0] if hits else None
    above = winner is not None and winner.score >= settings.min_score
    return Retrieval(
        query_id=query_id,
        query=query,
        scheme_slug=scheme_slug or "",
        embedding_model=index["embedding_model"],
        collection="portable-minilm",
        hits=hits,
        citation_url=winner.source_url if winner else "",
        above_threshold=above,
    )


def export_index(settings: Settings | None = None) -> int:
    """Encode the current chunk file with the same ONNX model Vercel uses."""
    settings = settings or load_settings()
    current_path = settings.root / "data" / "artifacts" / "current.json"
    if not current_path.is_file():
        raise FileNotFoundError("current.json is missing. Run ingest first.")
    current = json.loads(current_path.read_text(encoding="utf-8"))
    chunk_path = settings.root / str(current["chunk_file"])
    chunks = [
        json.loads(line)
        for line in chunk_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    vectors = encode_texts([str(chunk["text"]) for chunk in chunks], settings.root)
    out_dir = settings.root / INDEX_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / "vectors.npy", vectors.astype(np.float32))
    (out_dir / "chunks.jsonl").write_text(
        "".join(json.dumps(chunk, ensure_ascii=False) + "\n" for chunk in chunks),
        encoding="utf-8",
    )
    manifest = {
        "embedding_model": settings.embedding_model,
        "encoder": "onnx-quantized-minilm",
        "chunk_file": str(current["chunk_file"]).replace("\\", "/"),
        "vector_count": len(chunks),
        "loaded_at": str(current.get("loaded_at", "")),
        "run_id": str(current.get("run_id", "")),
    }
    (out_dir / "index.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return len(chunks)


def encode_texts(texts: list[str], root: Path) -> np.ndarray:
    tokenizer, session = _session(root)
    encoded = tokenizer.encode_batch(texts)
    width = max(len(item.ids) for item in encoded)
    ids = np.zeros((len(encoded), width), dtype=np.int64)
    mask = np.zeros((len(encoded), width), dtype=np.int64)
    types = np.zeros((len(encoded), width), dtype=np.int64)
    for row, item in enumerate(encoded):
        ids[row, : len(item.ids)] = item.ids
        mask[row, : len(item.attention_mask)] = item.attention_mask
    feeds = {}
    for spec in session.get_inputs():
        if "input_ids" in spec.name:
            feeds[spec.name] = ids
        elif "attention_mask" in spec.name:
            feeds[spec.name] = mask
        elif "token_type" in spec.name:
            feeds[spec.name] = types
    hidden = session.run(None, feeds)[0]
    weights = mask.astype(np.float32)[:, :, None]
    summed = (hidden * weights).sum(axis=1)
    counts = np.clip(weights.sum(axis=1), 1e-9, None)
    vectors = summed / counts
    norms = np.clip(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-9, None)
    return (vectors / norms).astype(np.float32)


def _load_index(root: Path) -> dict:
    index_dir = root / INDEX_DIR
    manifest_path = index_dir / "index.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("data/index is missing. Run py -3 -m src.pipeline.portable")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunks = [
        json.loads(line)
        for line in (index_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    vectors = np.load(index_dir / "vectors.npy")
    if len(chunks) != len(vectors):
        raise ValueError("portable index vectors do not match chunks")
    manifest["chunks"] = chunks
    manifest["vectors"] = vectors
    return manifest


_TOKENIZER = None
_SESSION = None


def _session(root: Path):
    global _TOKENIZER, _SESSION
    if _SESSION is None:
        import onnxruntime as ort
        from tokenizers import Tokenizer

        model_dir = root / MODEL_DIR
        tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        tokenizer.enable_truncation(max_length=MAX_LENGTH)
        tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
        _TOKENIZER = tokenizer
        _SESSION = ort.InferenceSession(
            str(model_dir / "model_quantized.onnx"),
            providers=["CPUExecutionProvider"],
        )
    return _TOKENIZER, _SESSION


def main() -> None:
    count = export_index()
    print(f"vector_count: {count}")


if __name__ == "__main__":
    main()
