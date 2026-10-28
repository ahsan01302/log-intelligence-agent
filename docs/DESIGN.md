# Log Intelligence Agent v2 — Design

Status: **personal project, in progress.** Not deployed, not used in production.

## 1. Problem

An on-call engineer gets paged and faces thousands of noisy log lines. They need a
*likely* cause quickly, with pointers to the exact lines that support it, so they can
check it themselves instead of trusting a chatbot.

v1 (tag `v1`) proved the idea with LangChain + Ollama + FAISS, but it embeds one
line per chunk, never indexes uploaded files, gives no citations, has a path-traversal bug
in `/upload`, loads the index with pickle, and has no tests or evals. v2 fixes that.

## 2. Goals and non-goals

Goals
- Answer questions about a set of log files with **cited** evidence (`file:line` ranges).
- Say **"insufficient evidence"** rather than guess when retrieval finds nothing relevant.
- Run fully locally and for free (Ollama). Paid providers are optional and off by default.
- Measure quality: retrieval hit@k and answer evals on labelled synthetic incidents.
- Treat log content as **untrusted input** (prompt injection, path tricks).

Non-goals
- Real-time streaming ingestion, multi-tenant auth, or a production deployment.
- Automated remediation. The tool only explains; humans act.
- Using any employer data. Only self-generated synthetic logs.

## 3. Architecture

```text
  log files ──► parser ──► chunker ──► index (BM25 + embeddings) ──► retriever
  (upload/CLI)  (ts, level,  (time window /     (safe on-disk format,       │
                 req-id,      request-id;        no pickle)                 ▼
                 file:line)   keeps line range)                  prompt builder (untrusted
                                                                  log text fenced, cited ids)
                                                                         │
                                                                         ▼
                                                     provider (Ollama default; optional
                                                     Anthropic/OpenAI) ──► structured answer
                                                                         │       (Pydantic)
                                    FastAPI · Typer CLI · Angular ◄──────┘
```

Package layout (`src/log_intel/`): `config.py` (pydantic-settings), `generator/`,
`parsing.py`, `chunking.py`, `index/`, `retrieval.py`, `providers/`, `answer.py`,
`api.py`, `cli.py`, `history.py`. The web UI is an Angular app in `frontend/`.

### Key decisions
| Decision | Choice | Why |
|----------|--------|-----|
| Chunk unit | Time window (default 30 s) or shared request id | Incidents span many lines; one-line chunks lose context |
| Retrieval | BM25 + embeddings, reciprocal-rank fusion | Logs are full of exact tokens (error codes, ids) that BM25 catches and embeddings miss |
| Index storage | JSON/NumPy files, never pickle | v1 used `allow_dangerous_deserialization=True` |
| Answer shape | Pydantic model: `hypotheses[]` each with `cause`, `confidence`, `citations[]`; or `insufficient_evidence` | Testable, and the UI can link citations back to lines |
| Config | pydantic-settings, `LOGINTEL_` env prefix, `.env` optional | Removes hardcoded `/app/vectorstore`, `host.docker.internal`, `../logs` |
| Degraded mode | If the LLM is unreachable, return ranked evidence chunks without a hypothesis | Still useful during an outage; failure is explicit |

## 4. Data

- **Synthetic generator (M2):** seeded, deterministic multi-service logs with injected
  incidents (e.g. DB pool exhaustion, upstream timeout, bad deploy, disk full). Each run
  writes ground-truth labels: incident type, root-cause lines, and time span.
- **LogHub (decision):** not bundled. Its datasets are published for research use, and redistributing them in this repo isn't clearly permitted. The parser's fallback handles common LogHub-style formats (leading timestamp + level word), and users can index files they download themselves.

## 5. Security

- Upload filenames are reduced to a basename, then checked against an allowlist pattern,
  and the resolved path must stay inside `upload_dir` (fixes v1 traversal).
- Upload size is capped (`max_upload_mb`).
- Log text is placed inside clearly delimited blocks, and the system prompt says it is data,
  not instructions. Eval cases include injected lines such as "ignore previous instructions".
- No secrets in the repo. `.env` is gitignored, and `.env.example` documents the variables.

## 6. Evaluation

- **Retrieval (M4):** hit@k and MRR. A hit means a retrieved chunk overlaps a labelled
  root-cause line.
- **Answers (M7):** for each labelled incident: correct cause category, at least one valid
  citation, no fabricated citations, "insufficient evidence" on unanswerable questions,
  and injection resistance. Results go in a README table with the model name and date.

## 7. Acceptance criteria

| Milestone | Done when |
|-----------|-----------|
| M1 | This doc exists; `uv sync` works on Python 3.12; `Settings` loads defaults and env overrides; `uv run pytest` passes; `.env.example` is present |
| M2 | `log-intel generate --seed N` is deterministic; labels file matches the injected incidents; tests pass (LogHub not bundled, see §4) |
| M3 | Parser handles the synthetic format and a generic timestamp + level fallback; every chunk keeps file + line range; time-window and request-id chunking are tested |
| M4 | Index saves and loads without pickle; hybrid retrieval beats BM25-only or embeddings-only on hit@5 over the synthetic set (numbers recorded) |
| M5 | Ollama provider by default; structured answer validated by Pydantic; "insufficient evidence" path and degraded mode tested; injection cases in tests |
| M6 | `/upload` traversal fixed with a regression test; upload triggers indexing; Typer CLI `index`/`ask`; the UI shows citations |
| M7 | Answer eval table in README; CI runs ruff + pytest on 3.12; README has GIF and diagram; review pass done |

## 8. Honest-claims rules for the README

- Say "personal project", never "production-ready".
- Terraform stays labelled "design only, not deployed".
- LangChain is used at a basic level. Don't claim more.

## 9. Decisions made during the v2 rebuild (2026-10-29)

- **LangChain removed.** The v2 code talks to Ollama, Anthropic and OpenAI over plain HTTP
  (`httpx`) behind a two-method provider interface. That's fewer dependencies, and the request
  shape is unit-tested with mocked transports. v1 (tag `v1`) used LangChain.
- **FAISS replaced** by NumPy cosine search over normalised vectors plus an in-house BM25. At
  MVP scale (thousands of chunks) this is fast, and it removes the pickle-based persistence.
- **Terraform removed.** v1 only defined an empty ECS cluster and an unsecured S3 bucket and was
  never applied. Deployment is local Docker Compose, which is honest about the project's scope.
- **Re-index on every upload.** All uploaded files are re-parsed and re-embedded, so every file
  stays searchable. Simple and correct at MVP scale; incremental indexing is future work.
- **Angular UI replaced Streamlit** (2026-10-29). Streamlit reran the whole script on every
  interaction and couldn't link citations to highlighted lines. The Angular 22 app
  (`frontend/`) talks to the same API through a `/api` proxy (dev server or nginx), so the
  analysis behaviour is unchanged. Investigations are now saved server-side in SQLite
  (`history.py`) for the History page.
