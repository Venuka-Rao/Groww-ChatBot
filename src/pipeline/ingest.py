"""Run scrape, then chunk, then embed."""

from src.pipeline.chunk import chunk_run
from src.pipeline.embed import embed_run
from src.pipeline.load import load_corpus


def ingest() -> str:
    run_id = load_corpus()
    chunk_run(run_id)
    embed_run(run_id)
    return run_id


def main() -> None:
    run_id = ingest()
    print(f"run_id: {run_id}")


if __name__ == "__main__":
    main()
