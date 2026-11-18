# HDFC scheme facts

A facts-only assistant for 25 HDFC Mutual Fund direct-growth schemes on Groww. It answers from the saved scheme pages, cites one source, and refuses investment advice.

## Scope

- Schemes: the 25 Groww URLs in `config/urls.yaml`.
- Facts: expense ratio, exit load, minimum SIP, lock-in, riskometer, benchmark, and other fields published on those pages.
- Answers stay within three sentences, include one source link, and end with `Last updated from sources: <date>`.
- Personal details are not stored. Return comparisons and buy/sell questions are refused.

The assistant does not follow links off those 25 pages, and it does not invent a fact that is missing from the saved text.

## Setup

Python 3.11 or newer. On this machine, use `py -3` because `python` may be the Windows Store stub.

```powershell
py -3 -m pip install -r requirements-local.txt
copy .env.example .env
```

Put your Groq key in `.env`:

```text
LLM_MODEL_ID=qwen/qwen3.8-27b
GROQ_API_KEY=
```

`.env` is not committed. Embeddings stay local on `sentence-transformers/all-MiniLM-L6-v2`. Answers go to Groq only.

## Run the chat

The current corpus is already embedded. Start the UI:

```powershell
py -3 -m streamlit run src/ui/app.py
```

Open the local URL Streamlit prints. The screen has three suggested questions, a dark-mode switch, and a box labeled “Ask a published fact.”

A terminal chat is also available:

```powershell
py -3 -m src.pipeline.ask
```

Type a question after `Question:`. Type `exit` to stop.

## Rebuild the corpus

This fetches the 25 pages again, then chunks and embeds them.

```powershell
py -3 -m src.pipeline.ingest
```

Stage files are written under `data/artifacts/`. The Chroma database is `data/chroma/` and is gitignored.

## Tests

```powershell
py -3 -m pytest -q
```

## Deploy on Vercel

The hosted app is the page in `web/index.html` plus the FastAPI app in `app.py`. Vercel has no disk for Chroma, so that deploy searches the saved MiniLM index in `data/index/` with the ONNX model in `models/minilm/`. The local Streamlit app is unchanged and still uses Chroma.

1. On Vercel, choose **Add New → Project** and import `Venuka-Rao/Groww-ChatBot`.
2. Leave the framework as FastAPI when Vercel detects `app.py`. Root directory stays the repository root.
3. Add environment variables:
   - `LLM_MODEL_ID` = `qwen/qwen3.8-27b`
   - `GROQ_API_KEY` = your Groq key
4. Deploy. The first answer is slower because the function loads the embedding model.

After a fresh ingest, rebuild the file Vercel searches before you push:

```powershell
py -3 -m src.pipeline.portable
```

## Known limits

- Four original Groww URLs returned HTTP 404 and were replaced with the current pages for the same schemes. See `config/urls.yaml`.
- The saved pages do not include steps for downloading a capital-gains statement, so that question is answered as not found.
- The index is the last successful scrape, not a live page view. The freshness line shows that scrape date.
- The visual layout comes from `design/stitch/` and `stitch_hdfc_mutual_fund_factsheet_assistant.zip`. Product behavior is defined in `PRD.md`, `architecture.md`, and `implementation.md`.
