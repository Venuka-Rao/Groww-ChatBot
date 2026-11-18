# PRD: Groww Mutual Fund FAQ Assistant

**Status:** Draft for prototype  
**Product:** Facts-only FAQ assistant for a fixed set of HDFC mutual fund scheme pages on Groww  
**Audience:** Retail users comparing schemes; support and content teams answering repetitive mutual fund questions  
**Type:** Working RAG prototype (not an advice product)

## 1. Problem

People looking at mutual fund schemes on Groww repeatedly ask the same factual questions: expense ratio, exit load, minimum SIP, ELSS lock-in, riskometer, benchmark, and how to download statements. Those facts live on public scheme pages, but they are scattered and easy to misstate.

This prototype answers those facts from a closed set of official public pages, with one source link on every answer. It does not give investment advice, compare returns, or handle personal data.

## 2. Users

| User | Job to be done |
| --- | --- |
| Retail user comparing schemes | Look up a specific fact about one of the covered schemes without reading the full page |
| Support / content team | Answer a repetitive mutual fund question with a short, cited reply they can reuse |

The assistant is a demo of retrieval-augmented generation. It is built so each pipeline stage is visible and stored, not hidden inside a single black-box call.

## 3. Goals

1. Answer factual questions about the 25 listed schemes using only those public pages.
2. Attach exactly one citation link to every answer, including refusals that still point the user somewhere useful.
3. Refuse opinion, portfolio, and “should I buy/sell” questions with a short facts-only message and a relevant educational link.
4. Keep every answer to three sentences or fewer, and stamp it with when sources were last loaded.
5. Show the RAG path explicitly: load → chunk → embed → store → retrieve → generate.

## 4. Out of scope

- Investment advice, suitability, buy/sell/hold, or portfolio construction.
- Computing, ranking, or comparing returns or performance.
- Scraping any URL other than the 25 scheme pages listed below (no internal links, no blogs, no app screenshots, no backend).
- Accepting or storing PAN, Aadhaar, account numbers, OTPs, emails, or phone numbers.
- User accounts, chat history persistence, multi-user auth, or production support tooling.
- Live NAV, order placement, or statement download on the user’s behalf. “How do I download a capital-gains statement?” is answered as a how-to from public pages, not by fetching a user’s statement.

## 5. Corpus

Scrape and store **only** these 25 pages. Do not follow links inside them.

1. https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
2. https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
3. https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
4. https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
5. https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth
6. https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth
7. https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth
8. https://groww.in/mutual-funds/hdfc-large-mid-cap-fund-direct-growth
9. https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth
10. https://groww.in/mutual-funds/hdfc-dividend-yield-fund-direct-growth
11. https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth
12. https://groww.in/mutual-funds/hdfc-business-cycle-fund-direct-growth
13. https://groww.in/mutual-funds/hdfc-pharma-and-healthcare-fund-direct-growth
14. https://groww.in/mutual-funds/hdfc-transportation-and-logistics-fund-direct-growth
15. https://groww.in/mutual-funds/hdfc-nifty-50-index-fund-direct-growth
16. https://groww.in/mutual-funds/hdfc-bse-sensex-index-fund-direct-growth
17. https://groww.in/mutual-funds/hdfc-arbitrage-fund-direct-growth
18. https://groww.in/mutual-funds/hdfc-aggressive-hybrid-fund-direct-plan-growth
19. https://groww.in/mutual-funds/hdfc-conservative-hybrid-fund-direct-growth
20. https://groww.in/mutual-funds/hdfc-equity-savings-fund-direct-growth
21. https://groww.in/mutual-funds/hdfc-medium-term-opportunities-fund-direct-growth
22. https://groww.in/mutual-funds/hdfc-short-term-fund-direct-plan-growth
23. https://groww.in/mutual-funds/hdfc-liquid-fund-direct-growth
24. https://groww.in/mutual-funds/hdfc-overnight-fund-direct-growth
25. https://groww.in/mutual-funds/hdfc-money-market-fund-direct-growth

**AMC in scope:** HDFC Mutual Fund, direct-growth plans as published on these Groww pages.  
**Schemes in scope:** the 25 slugs above (large cap, equity, ELSS, mid cap, balanced advantage, small cap, multi cap, large & mid cap, focused, dividend yield, defence, business cycle, pharma & healthcare, transportation & logistics, Nifty 50 index, BSE Sensex index, arbitrage, aggressive hybrid, conservative hybrid, equity savings, corporate bond, short term, liquid, overnight, money market).

If a page is missing a fact, the assistant says it could not find that fact on the official page and still cites the page. It does not fill the gap from memory or from another site.

## 6. User experience

Tiny single-screen chat.

- **Welcome line** that names what the assistant can do (facts about the covered HDFC schemes).
- **Three example questions** the user can click or send, covering different fact types (for example expense ratio, ELSS lock-in, and how to download a capital-gains statement).
- **Standing note:** “Facts-only. No investment advice.”
- **Answer:** at most three sentences, one citation link, and a line `Last updated from sources: <date>`.
- **Refusal:** polite, facts-only, no opinion, plus one relevant educational link (a covered scheme page or another official public page already in the source list). No buy/sell language.

### Question classes

| Class | Examples | Behavior |
| --- | --- | --- |
| Fact, in corpus | “Expense ratio of HDFC Large Cap Fund?”, “ELSS lock-in?”, “Minimum SIP?”, “Exit load?”, “Riskometer / benchmark?” | Answer from retrieved chunks. One citation. |
| How-to, in corpus | “How to download a capital-gains statement?” | Short steps grounded in the retrieved page. One citation. |
| Returns / performance | “Which fund returned more last year?”, “Is this beating the benchmark?” | Do not compute or compare. Point to the official factsheet or scheme page. |
| Advice / portfolio | “Should I buy this?”, “Which fund should I pick?”, “Sell my ELSS?” | Refuse. Facts-only message + one educational link. |
| Out of corpus | A scheme or AMC not in the 25 pages | Say it is outside the covered schemes. Do not answer from general knowledge. |
| PII | Message contains PAN, Aadhaar, account number, OTP, email, or phone | Do not store it. Ask the user to resend the question without personal details. Do not echo the identifier back. |

**Decision rule (W1):** identify the exact fact asked. If the question is a fact the corpus can support, answer it. If it asks for a judgment, a comparison of returns, or anything outside the 25 pages, refuse or redirect. Do not answer a neighboring fact the user did not ask.

## 7. Functional requirements

### FR-1 Source of truth

Answers use only text loaded from the 25 URLs. The model may not add expense ratios, loads, lock-ins, benchmarks, or SIP minimums from its own knowledge.

### FR-2 Citation

Every response includes exactly one source link. The link is one of the 25 URLs (or, for a returns question, the official factsheet URL only when that URL was present on a scraped page and stored with the page). The citation is the page the retrieved fact came from, not a generic homepage.

### FR-3 Length and stamp

The answer body is at most three sentences. Each answer ends with `Last updated from sources: <ISO date of the last successful load>`.

### FR-4 Advice refusal

Opinionated or portfolio questions get a polite refusal that restates the facts-only boundary and includes one relevant educational link. The refusal does not hint at a recommendation.

### FR-5 No performance math

The assistant does not calculate, rank, or compare returns, CAGR, alpha, or rolling performance. If asked, it links to the official factsheet or scheme page and says the numbers live there.

### FR-6 No PII

The app does not accept or persist PAN, Aadhaar, account numbers, OTPs, emails, or phone numbers. Inputs that look like those identifiers are dropped before they are written to logs, the vector store, or any sample Q&A file.

### FR-7 Stage visibility

Each RAG stage writes an explicit artifact the demo can show:

| Stage | Artifact |
| --- | --- |
| Load | Raw page text plus URL, scheme name, and fetch timestamp |
| Chunk | Chunk records with chunk id, source URL, and text |
| Embed | Vector ids tied to chunk ids, using the configured embedding model |
| Retrieve | For a query: top chunks, scores, and the source URL chosen as the citation |
| Generate | Final answer text, citation URL, refusal flag, and model id used |

### FR-8 Config, not hardcoded models

Embedding model, vector store, LLM provider, and LLM model id are read from configuration and `.env`. Changing them does not require editing pipeline code.

## 8. RAG pipeline (phased)

Build and run the stages in this order. Later stages consume the stored output of earlier stages.

### Phase 1 — Data loading

- Fetch each of the 25 URLs once per run.
- Store raw text, final URL, HTTP status, and fetch time.
- Do not enqueue or fetch links found in the page.
- A failed URL is recorded and excluded from chunking. The run still completes for the pages that succeeded.
- `Last updated from sources` is the timestamp of this successful load.

### Phase 2 — Chunking

Chunking strategy is chosen from the shape of these pages (scheme fact blocks: expense ratio, exit load, minimum SIP, lock-in, riskometer, benchmark, statement how-to), not a generic token split that cuts a fact in half.

Requirements for the strategy:

- A chunk keeps one fact (or one tightly related fact group) together with the scheme name, so retrieval can answer “expense ratio of X” without mixing schemes.
- Every chunk stores `source_url` and scheme identity in metadata.
- Chunk records are written to disk (or a table) before embedding, so the demo can show the chunks independently of the vector index.

The coding agent picks the concrete splitter (section/heading split, fact-field split, or a small recursive split with an overlap that does not merge two schemes) and documents that choice in the README.

### Phase 3 — Embedding

- Model: `sentence-transformers/all-MiniLM-L6-v2` (default; overridable in config).
- The same model id is used at ingestion and at query time.
- Embeddings are written into the vector store with chunk id and source metadata. Do not re-embed on every query if the index already matches the current model id and corpus version.

### Phase 4 — Vector store

- Engine: ChromaDB for this exercise (overridable in config so the setting is not buried in code).
- One collection per corpus version (or a collection name that includes the embedding model id) so a model change does not silently mix vectors.
- Persist the database on disk so a restart does not require a re-scrape unless the operator asks for one.

### Phase 5 — Retrieval

- Embed the user query with the same embedding model used at ingestion.
- Query the same ChromaDB collection.
- Return the top chunks with scores and source URLs.
- Persist the retrieval trace (query, chunk ids, scores, chosen citation URL) so the demo can show why that link was used.
- If the top score is below the configured minimum, do not answer from the model’s memory. Say the fact was not found and cite the closest covered scheme page only when the scheme itself was identified; otherwise state that the question is outside the corpus.

### Phase 6 — Generation

- Provider: Groq, using an API key from `.env`.
- Model id: read from `.env` (problem statement names `qwen/qwen3.8-27b`; treat that string as the configured model id, not a hardcoded constant).
- The config also allows Gemini, OpenAI, Anthropic, and Mistral so the provider can be swapped without changing prompts or retrieval.
- System prompt encodes: facts only, at most three sentences, one citation, refuse advice, no return math, no PII, answer only from the retrieved chunks.
- The prompt receives retrieved chunks and their URLs. It does not receive the rest of the corpus.

## 9. Configuration

| Setting | Default for this exercise | Where |
| --- | --- | --- |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` | Config file |
| Vector DB | ChromaDB, local persistent path | Config file |
| LLM provider | Groq | Config file |
| LLM model id | From `.env` (example: `qwen/qwen3.8-27b`) | `.env` |
| Other providers | Gemini, OpenAI, Anthropic, Mistral selectable in config | Config file + `.env` keys |
| Corpus URL list | The 25 Groww URLs | Config or data file, not scattered in code |
| Retrieval `top_k` and minimum score | Set in config | Config file |
| Source freshness label | Date of last successful load | Written by the loader |

API keys live only in `.env`. `.env` is not committed. The sample Q&A file and README contain no keys.

## 10. Guardrails

- **Public sources only.** No screenshots of the Groww app backend. No third-party blogs as sources.
- **No PII** in prompts logged for the demo, in Chroma metadata, or in the sample Q&A file.
- **No performance claims.** No computed or comparative return language in the answer text.
- **Citation wording** names the fact and the page, for example: “Expense ratio is … ([HDFC Large Cap Fund — Groww](url)).”
- **Safe refusal tone:** short, polite, no lecture, no alternative recommendation. Example shape: “I can only share published facts such as expense ratio, exit load, and lock-in. I can’t suggest whether to buy or sell. You can read the scheme page here: <link>.”
- **Disclaimer in the UI, always visible:** “Facts-only. No investment advice.”

## 11. Deliverables

| Deliverable | Contents |
| --- | --- |
| Working prototype | Hosted app or notebook. If hosting is not possible, a demo video of 3 minutes or less that shows load, chunks, retrieval, an answer, and a refusal. |
| Source list | CSV or Markdown of the URLs actually used (the 25 pages; 15–25 is the allowed submission range, this project uses all 25). |
| README | Setup steps, AMC and scheme scope, chunking choice, config knobs, and known limits. |
| Sample Q&A | 5–10 queries with the assistant’s answers and links, including at least one refusal and one “not found / out of scope” case. |
| Disclaimer snippet | The exact UI string: “Facts-only. No investment advice.” |
| Stage artifacts | Stored outputs for load, chunk, embed/index, and retrieve so a reviewer can inspect the RAG path. |

## 12. Acceptance criteria

1. A question about expense ratio, exit load, minimum SIP, ELSS lock-in, riskometer, or benchmark for a covered scheme returns that fact, one of the 25 URLs, and the last-updated line, in three sentences or fewer.
2. “How do I download a capital-gains statement?” returns a short how-to grounded in retrieved text plus one link, or a clear not-found if the pages do not contain the steps.
3. “Should I buy HDFC Small Cap?” (or any buy/sell/which-fund question) is refused, with the disclaimer tone and one educational link, and does not name a preferred scheme.
4. “Which of these two funds performed better?” does not contain a comparison or a calculated return. It points at the factsheet or scheme page.
5. A question about a scheme outside the 25 is not answered with an invented fact.
6. A message containing a PAN-shaped or phone-shaped string is not written to the vector store, logs used in the sample file, or the answer.
7. Switching the LLM model id in `.env` changes the model used on the next request without a code edit. Ingestion and query both use the embedding model named in config.
8. After a pipeline run, a reviewer can open stored load, chunk, and retrieval artifacts and see the citation URL on the retrieved chunk that supported the answer.
9. The UI shows a welcome line, three example questions, and the note “Facts-only. No investment advice.”
10. README setup from a clean environment produces a running prototype using only public pages and local config.

## 13. Known limits (to state in the README)

- Corpus is 25 HDFC direct-growth pages on Groww at the time of the last load. Facts drift; the stamp is the load date, not a live quote.
- Groww page layout can change and break extraction. Failed URLs are reported, not silently filled.
- The assistant is not a SEBI-registered adviser and is not a substitute for the scheme information document or factsheet.
- Statement download is explained, not performed. The assistant never sees the user’s account.
- Embedding quality depends on `all-MiniLM-L6-v2` and the chosen chunks. Low-score queries fail closed (not found) rather than guessing.
- Provider quotas and model ids (Groq and the optional Gemini / OpenAI / Anthropic / Mistral paths) depend on the operator’s keys.

## 14. Skills this prototype is meant to show

| Id | Skill | What “done” looks like |
| --- | --- | --- |
| W1 | Thinking like a model | Each query is classified as answer, refuse, redirect-to-factsheet, or not-in-corpus before generation. The reply addresses the fact that was asked. |
| W2 | LLMs and prompting | Instructions force concise phrasing, a single citation, and a polite refusal. Wording stays stable across providers. |
| W3 | RAG only | Small-corpus retrieval over the 25 pages, with citations taken from retrieved metadata. No tool use beyond this corpus. |

## 15. Suggested build order

1. Config, `.env` template, and the URL list.
2. Loader and stored raw pages.
3. Chunker and stored chunks (document the strategy in the README).
4. Embed with `all-MiniLM-L6-v2` into persistent ChromaDB.
5. Retriever that writes a trace.
6. Generator with Groq, model id from `.env`, plus the refusal and citation rules.
7. Tiny UI (welcome, three examples, disclaimer, answer with link and date).
8. Sample Q&A file (5–10) and source-list file.
