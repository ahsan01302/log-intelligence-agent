# Log Intelligence Agent v2 — Design

Status: **personal project, in progress.** Not deployed, not used in production.

## 1. Problem

An on-call engineer gets paged and faces thousands of noisy log lines. They need a
*likely* cause quickly, with pointers to the exact lines that support it, so they can
check it themselves instead of trusting a chatbot.

v1 (this repo's `main`) proved the idea with LangChain + Ollama + FAISS, but it embeds one
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
- Using any employer data. Only synthetic logs and public LogHub samples (attributed).

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
                                    FastAPI · Typer CLI · Streamlit ◄────┘
```

Package layout (`src/log_intel/`): `config.py` (pydantic-settings), `generator/`,
`parsing.py`, `chunking.py`, `index/`, `retrieval.py`, `providers/`, `answer.py`,
`api.py`, `cli.py`. The v1 `backend/` and `frontend/` stay in place until M6 replaces them.

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
- **LogHub samples (M2):** small excerpts from the public LogHub dataset, with attribution
  and licence noted in `data/README.md`.

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
| M2 | `log-intel generate --seed N` is deterministic; labels file matches the injected incidents; LogHub sample is attributed; tests pass |
| M3 | Parser handles the synthetic format and at least one LogHub format; every chunk keeps file + line range; time-window and request-id chunking are tested |
| M4 | Index saves and loads without pickle; hybrid retrieval beats BM25-only or embeddings-only on hit@5 over the synthetic set (numbers recorded) |
| M5 | Ollama provider by default; structured answer validated by Pydantic; "insufficient evidence" path and degraded mode tested; injection cases in tests |
| M6 | `/upload` traversal fixed with a regression test; upload triggers indexing; Typer CLI `index`/`ask`; Streamlit shows citations |
| M7 | Answer eval table in README; CI runs ruff + pytest on 3.12; README has GIF and diagram; review pass done |

## 8. Honest-claims rules for the README

- Say "personal project", never "production-ready".
- Terraform stays labelled "design only, not deployed".
- LangChain is used at a basic level. Don't claim more.
