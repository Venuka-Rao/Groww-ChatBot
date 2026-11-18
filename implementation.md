# Implementation: Groww Mutual Fund FAQ Assistant

**Source:** [architecture.md](architecture.md) and [PRD.md](PRD.md)

Python 3.11 prototype. Ingestion is a CLI (`load → chunk → embed → Chroma`). The chat UI calls one function, `ask`, which checks guardrails, retrieves, and then generates.

Build in the order below. Each step writes files the next step reads.

| Step | Writes |
| --- | --- |
| Scrape | `data/artifacts/load/<run_id>/` |
| Chunk | `data/artifacts/chunks/<run_id>.jsonl` |
| Embed + store | `data/chroma/` and `data/artifacts/current.json` |
| Retrieve | `data/artifacts/retrieve/<query_id>.json` |
| Answer | `data/artifacts/generate/<query_id>.json` |

`run_id` is UTC `YYYYMMDDTHHMMSSZ` from the start of a scrape. The freshness line uses the date of that run: `Last updated from sources: 2026-11-16`.

## 1. Creating the directory

```text
config/settings.yaml          # model, Chroma path, top_k, min_score
config/urls.yaml              # the 25 Groww URLs
.env.example
src/config.py                 # reads yaml + .env
src/facts.py                  # fact, advice, and performance phrases
src/pipeline/load.py
src/pipeline/chunk.py
src/pipeline/embed.py
src/pipeline/ingest.py        # load, then chunk, then embed
src/pipeline/retrieve.py
src/pipeline/generate.py
src/pipeline/ask.py           # guardrails → retrieve or template → generate
src/guardrails/pii.py
src/guardrails/intent.py
src/guardrails/templates.py
src/prompts/system.txt
src/ui/app.py
data/artifacts/               # created at runtime
data/chroma/                  # created at runtime
tests/
```

`requirements.txt`: `httpx`, `beautifulsoup4`, `pyyaml`, `python-dotenv`, `chromadb`, `sentence-transformers`, `groq`, `streamlit`, `pytest`.

`.gitignore`: `.env`, `.venv/`, `__pycache__/`, `data/chroma/`.

`config/settings.yaml`:

```yaml
embedding_model: sentence-transformers/all-MiniLM-L6-v2
chroma_path: data/chroma
llm_provider: groq
top_k: 4
min_score: 0.35
request_timeout_seconds: 30
```

`.env.example`:

```text
LLM_MODEL_ID=qwen/qwen3.8-27b
GROQ_API_KEY=
```

`LLM_MODEL_ID` is read on each answer. It is not a constant in pipeline code. Optional keys `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `MISTRAL_API_KEY` exist so the provider in `settings.yaml` can change without a code edit.

`config/urls.yaml` is the only fetch list. One entry per scheme, all 25 from the PRD:

```yaml
schemes:
  - slug: hdfc-large-cap-fund-direct-growth
    name: HDFC Large Cap Fund Direct Growth
    url: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
    aliases:
      - HDFC Large Cap Fund
      - HDFC Large Cap
```

`load_settings()` resolves paths from the repo root (the folder that contains `config/`). Startup fails if the file does not contain exactly those 25 unique `groww.in` URLs.

## 2. Scraping

`python -m src.pipeline.load` fetches each URL in `urls.yaml` once.

For each scheme:

- GET that URL only. Do not queue links found on the page.
- Follow redirects only when the final URL is still in the allowlist. If it is not, store a failure and discard the body.
- On timeout or HTTP error, write a page record with the error and continue. One bad URL does not stop the run.
- Save extracted text, not raw HTML.

Extraction order:

1. If the page has `<script id="__NEXT_DATA__">`, read the scheme fields from that JSON and turn them into lines such as `Expense ratio: …`.
2. Otherwise use BeautifulSoup. Drop `script` and `style`. Turn table rows into `label: value` lines.

If the HTML contains a factsheet link, save that URL on the page record. Do not GET it. It is only a citation target for performance questions.

Page file `data/artifacts/load/<run_id>/<slug>.json`:

```json
{
  "slug": "hdfc-large-cap-fund-direct-growth",
  "scheme_name": "HDFC Large Cap Fund Direct Growth",
  "requested_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
  "final_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
  "http_status": 200,
  "fetched_at": "2026-11-16T14:30:02Z",
  "text": "Expense ratio: ...",
  "factsheet_url": "",
  "error": ""
}
```

`manifest.json` in the same folder lists `run_id`, `loaded_at`, `successes`, and `failures`. If every URL fails, exit non-zero so later steps do not index an empty corpus.

## 3. Chunking

`python -m src.pipeline.chunk --run-id <run_id>` reads successful page records and writes `data/artifacts/chunks/<run_id>.jsonl`.

These pages are fact blocks, so split on labels rather than a token window.

1. Skip failed pages and empty text.
2. Match lines to a fact type using the phrases in `src/facts.py`: expense ratio, exit load, minimum SIP, lock-in, riskometer, benchmark, statement download.
3. Keep consecutive lines of the same fact type in one chunk.
4. Start every chunk body with the scheme name: `HDFC Large Cap Fund Direct Growth. Expense ratio: 0.99%`.
5. If a page has no labeled facts, split on headings and mark those chunks `other`.

```json
{
  "chunk_id": "hdfc-large-cap-fund-direct-growth:expense_ratio:0",
  "scheme_slug": "hdfc-large-cap-fund-direct-growth",
  "scheme_name": "HDFC Large Cap Fund Direct Growth",
  "fact_type": "expense_ratio",
  "source_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
  "factsheet_url": "",
  "text": "HDFC Large Cap Fund Direct Growth. Expense ratio: 0.99%"
}
```

`chunk_id` is `{slug}:{fact_type}:{index}`. Do not merge two pages into one chunk. Chunking does not embed and does not call an LLM.

## 4. Embedding

`python -m src.pipeline.embed --run-id <run_id>` embeds each chunk’s `text` with `sentence-transformers/all-MiniLM-L6-v2` (the model in `settings.yaml`).

- Use the same model id later for the user query.
- Batch size 32.
- Skip encoding when the target collection already exists and its count equals the number of chunks.
- Write `data/artifacts/embed/<run_id>.json` with the model id, collection name, chunk file, and vector count.

`python -m src.pipeline.ingest` runs scrape, chunk, and embed in that order.

## 5. Storing data in the vector DB

Engine is Chroma, persistent at `chroma_path`.

- Collection name: `hdfc-` + sanitized model id + `-` + lowercased `run_id`, trimmed to 63 characters. Example: `hdfc-all-minilm-l6-v2-20261116t143000z`.
- Create it with cosine space (`hnsw:space = cosine`). A different embedding model gets a new collection.
- Vector id is `chunk_id`. The document is `text`.
- Metadata: `chunk_id`, `scheme_slug`, `scheme_name`, `fact_type`, `source_url`, `factsheet_url`. Use `""` when there is no factsheet.
- After a successful store, write `data/artifacts/current.json` with `run_id`, `loaded_at`, `embedding_model`, `collection`, `chunk_file`, and `vector_count`. Retrieval reads this pointer.

A restart reopens `data/chroma/` and does not re-scrape.

## 6. Retrieval logic

`ask(question)` is the only query entry. Order:

1. **PII.** If the message matches a personal identifier, ask the user to resend without it and stop. Write nothing to disk.
2. **Intent.** Label the question before any model call.
3. **Template.** Advice, performance, and out-of-corpus questions use a fixed reply and one link. They do not call the LLM.
4. **Retrieve.** Fact and how-to questions embed the query and search the collection named in `current.json`.
5. **Generate.** The LLM sees the system prompt plus those chunks only.

Intent labels, first match wins:

| Label | When | What happens |
| --- | --- | --- |
| `refuse_advice` | buy, sell, hold, “should I”, “which fund should I pick”, portfolio | Fixed refusal. Link the named scheme page, or the first URL in `urls.yaml` if none was named |
| `redirect_factsheet` | returns, CAGR, alpha, “which performed better” | Fixed reply. No numbers. Link the stored factsheet URL, or the scheme page if there is no factsheet |
| `how_to` | statement or capital-gains download | Retrieve, then generate |
| `out_of_corpus` | an AMC or scheme that is not one of the 25 | Say it is outside the covered pages. One link to the first covered page |
| `answer` | a covered fact (expense ratio, exit load, SIP, lock-in, riskometer, benchmark, or another field on a named scheme) | Retrieve, then generate |

Advice wins over a scheme name. “Should I buy HDFC Small Cap?” is a refusal, and the link may be that scheme’s page.

Retrieval:

- Embed the query with the model id in `current.json`. Abort if it differs from `settings.yaml`.
- When the intent found a scheme, filter with `where={"scheme_slug": scheme_slug}`. A how-to with no scheme searches the whole collection.
- A fact question with no scheme does not borrow another fund’s number. Ask which covered scheme, and include one covered link.
- Chroma cosine distance converts to similarity as `1 - distance`. Keep a hit when similarity is at least `min_score`.
- Citation is the winning chunk’s `source_url`.
- Below `min_score`, do not call the LLM. Say the fact was not found and cite the scheme page when the scheme is known.
- Write `data/artifacts/retrieve/<query_id>.json` with the query, chunk ids, scores, and `citation_url`.

Generation:

- System prompt in `src/prompts/system.txt`: facts only, at most three sentences, exactly one markdown link from the retrieved URLs, no advice, no return math, no facts from model memory.
- Provider comes from `settings.yaml` (default Groq). Model id comes from `LLM_MODEL_ID`.
- After the model replies, keep the text only if it has at most three sentences and exactly one URL, and that URL is the retrieval citation. Otherwise replace it with the not-found template.
- Store answer text, citation URL, refusal flag, and model id under `data/artifacts/generate/`.
- The UI adds `Last updated from sources: <date>` from `current.json`. The date is the scrape date, not the time of the question.

Refusal copy:

```text
I can only share published facts such as expense ratio, exit load, and lock-in. I can’t suggest whether to buy or sell.

###### Source link
[HDFC Small Cap Fund Direct Growth — Groww](url)
```

## 7. UI

`streamlit run src/ui/app.py` is one screen. The layout and colors come from the Stitch export, which is the visual source of truth:

- `stitch_hdfc_mutual_fund_factsheet_assistant.zip`
- `design/stitch/stitch_hdfc_mutual_fund_factsheet_assistant/calm_fintech_assistant/DESIGN.md`
- `design/stitch/stitch_hdfc_mutual_fund_factsheet_assistant/hdfc_scheme_facts_desktop/code.html`

Use the Groww tokens in `DESIGN.md` (`#FFFFFF`, `#F8F8F8`, `#E9E9EB`, `#44475B`, `#7C7E8C`, `#A1A3AD`, `#04B488`, `#E9FAF3`) and Inter. Do not add the Stitch site header (Screener, Compare, search, account).

- Notice bar, exact string: `Facts-only. No investment advice.`, plus `25 HDFC DIRECT SCHEMES`.
- Welcome line naming facts about the covered HDFC schemes.
- Suggested queries that send:
  1. `What is the expense ratio of HDFC Large Cap Fund?`
  2. `What is the exit load of HDFC Mid Cap Fund?`
  3. `What is the minimum SIP of HDFC Small Cap Fund?`
- A cited answer is a card: the fact, then **Source link** and one Groww link, then `Last updated from sources: <date>`.
- A refusal or a missing fact uses the same card with the title “Facts-only reply.”
- Composer placeholder: `Ask a published fact`.
- No login and no saved chat. Page load does not scrape again.

## 8. Guardrail edge cases and test cases

Guardrails live in `src/guardrails/` and in the compliance check after generation. Tests go in `tests/test_pii.py`, `tests/test_intent.py`, and `tests/test_compliance.py`. Use fixture text and a mocked LLM. Do not put real identifiers or API keys in test files.

### Edge cases

| Case | Expected behavior |
| --- | --- |
| PAN, Aadhaar, email, mobile, long account number, or “OTP” plus digits | Reply asks for the question again. The identifier is not echoed and is not written to logs, Chroma, retrieve traces, or generate files |
| A number that is a fact, such as `0.99%` or the year `2024` | Not treated as PII |
| “Should I buy HDFC Small Cap?” | `refuse_advice`, even though the scheme is in the corpus. One link. No second scheme suggested |
| “Which fund returned more?” or “Is this beating the benchmark?” | `redirect_factsheet`. No calculated or compared return. One factsheet or scheme link |
| Two covered funds compared | Same redirect. The single link is the first scheme mentioned |
| Axis, SBI, or any scheme outside the 25 | `out_of_corpus`. No expense ratio or other fact from model memory |
| “What is the expense ratio?” with no scheme | Ask which covered scheme. Do not answer with an arbitrary fund’s ratio |
| Covered scheme, but the field is missing or the score is below `min_score` | “I couldn’t find that fact on the official page,” plus that scheme’s URL. No guessed number |
| How-to and the pages have no download steps | Same not-found reply. Do not invent steps |
| Model returns two links, a fourth sentence, or a URL that was not retrieved | Discard that text and use the not-found template |
| Scrape HTTP error or redirect off the allowlist | Failure on the manifest. Chunker skips it. Other pages still index |
| Same `run_id` embedded twice | Second run does not re-embed |
| Embedding model id changed in settings | New collection name. Queries use the collection in `current.json` |
| `LLM_MODEL_ID` changed in `.env` | Next answer records the new model id. No code change |

### Test cases

**PII**

- `ABCDE1234F` is detected. The reply does not contain `ABCDE1234F`.
- `user@example.com` and a 10-digit mobile starting with 9 are detected.
- `Expense ratio is 0.99%` is not detected.

**Intent**

- `Should I buy HDFC Small Cap?` → `refuse_advice`, scheme slug is the small-cap fund.
- `Which of these two funds performed better, HDFC Large Cap or HDFC Liquid Fund?` → `redirect_factsheet`.
- `Expense ratio of Axis Bluechip Fund?` → `out_of_corpus`.
- `What is the ELSS lock-in for HDFC ELSS Tax Saver Fund?` → `answer`, ELSS slug.
- `How do I download a capital-gains statement?` → `how_to`.

**Retrieval and answer checks**

- With fixture chunks loaded, `Expense ratio of HDFC Large Cap Fund?` returns the large-cap `expense_ratio` chunk and that page’s URL.
- The same query filtered to the liquid-fund slug does not return the large-cap chunk.
- A mocked model reply with two URLs is replaced by the not-found template.
- A mocked reply with one allowed URL and two sentences is kept.
- A generate artifact for an advice refusal has `refusal: true` and `model_id: template`.

**Scrape and chunk fixtures**

- A local HTML table with an expense-ratio row lands in `text`, and an in-page blog link is never requested.
- A factsheet `href` is stored and not requested.
- Two pages produce chunk ids with different slug prefixes, and each body starts with its own scheme name.
