"""Split saved scheme pages into fact-sized chunks.

Reads data/artifacts/load/<run_id> and writes data/artifacts/chunks/<run_id>.jsonl.
Does not embed and does not call a model.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from src.config import Settings, load_settings
from src.facts import FACT_PHRASES


def chunk_run(run_id: str | None = None, settings: Settings | None = None) -> Path:
    settings = settings or load_settings()
    run_id = run_id or latest_run_id(settings.root)
    load_dir = settings.root / "data" / "artifacts" / "load" / run_id
    manifest = json.loads((load_dir / "manifest.json").read_text(encoding="utf-8"))
    failed = {item["slug"] for item in manifest.get("failures", [])}

    chunks: list[dict] = []
    for slug in manifest.get("successes", []):
        if slug in failed:
            continue
        record = json.loads((load_dir / f"{slug}.json").read_text(encoding="utf-8"))
        if record.get("error") or not str(record.get("text", "")).strip():
            continue
        if record.get("http_status") not in (200, "200"):
            continue
        chunks.extend(chunk_page(record))

    out_path = settings.root / "data" / "artifacts" / "chunks" / f"{run_id}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(chunk, ensure_ascii=False) for chunk in chunks]
    out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return out_path


def chunk_page(record: dict) -> list[dict]:
    """One page in, fact chunks out. Never reads another page."""
    lines = [line.strip() for line in str(record.get("text", "")).splitlines() if line.strip()]
    if not lines:
        return []
    typed = [(line, match_fact_type(line)) for line in lines]
    if not any(fact_type for _, fact_type in typed):
        return _chunks_for_groups(record, _heading_groups(lines))

    groups: list[tuple[str, list[str]]] = []
    for line, fact_type in typed:
        if fact_type and groups and groups[-1][0] == fact_type:
            groups[-1][1].append(line)
            continue
        groups.append((fact_type or "other", [line]))
    return _chunks_for_groups(record, groups)


def match_fact_type(line: str) -> str | None:
    """Match the label before the colon. The longest phrase wins."""
    label = line.split(":", 1)[0] if ":" in line else line
    lowered = label.lower()
    best_type = None
    best_len = 0
    for fact_type, phrases in FACT_PHRASES.items():
        for phrase in phrases:
            if len(phrase) <= best_len:
                continue
            if _contains_phrase(lowered, phrase):
                best_type = fact_type
                best_len = len(phrase)
    return best_type


def latest_run_id(root: Path) -> str:
    load_root = root / "data" / "artifacts" / "load"
    manifests = sorted(path.parent.name for path in load_root.glob("*/manifest.json"))
    if not manifests:
        raise FileNotFoundError(f"No load manifest under {load_root}")
    return manifests[-1]


def _heading_groups(lines: list[str]) -> list[tuple[str, list[str]]]:
    """Used only when a page has no recognized fact label."""
    has_heading = any(":" not in line for line in lines)
    if not has_heading:
        return [("other", [line]) for line in lines]
    groups: list[tuple[str, list[str]]] = []
    current: list[str] = []
    for line in lines:
        if ":" not in line:
            if current:
                groups.append(("other", current))
            current = [line]
        else:
            current.append(line)
    if current:
        groups.append(("other", current))
    return groups


def _chunks_for_groups(record: dict, groups: list[tuple[str, list[str]]]) -> list[dict]:
    counts: dict[str, int] = {}
    chunks = []
    scheme_name = str(record.get("scheme_name", "")).strip()
    slug = str(record["slug"])
    for fact_type, group_lines in groups:
        index = counts.get(fact_type, 0)
        counts[fact_type] = index + 1
        body = f"{scheme_name}. " + " ".join(group_lines)
        chunks.append(
            {
                "chunk_id": f"{slug}:{fact_type}:{index}",
                "scheme_slug": slug,
                "scheme_name": scheme_name,
                "fact_type": fact_type,
                "source_url": record.get("requested_url", ""),
                "factsheet_url": record.get("factsheet_url") or "",
                "text": body,
            }
        )
    return chunks


def _contains_phrase(text: str, phrase: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(phrase.lower()) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunk a saved load run into fact records.")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    path = chunk_run(args.run_id)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["fact_type"]] = counts.get(row["fact_type"], 0) + 1
    print(f"chunks: {path}")
    print(f"count: {len(rows)}")
    for fact_type in sorted(counts):
        print(f"  {fact_type}: {counts[fact_type]}")


if __name__ == "__main__":
    main()
