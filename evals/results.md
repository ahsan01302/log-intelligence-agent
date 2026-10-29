## Evaluation results (2026-10-29)

Synthetic dataset, seed 7, 115 chunks, k=5, embeddings: ollama/nomic-embed-text.

### Retrieval: does a top-k chunk contain a labelled root-cause line?

| Mode | hit@k | MRR |
|------|-------|-----|
| bm25 | 0.75 | 0.46 |
| embed | 0.75 | 0.50 |
| hybrid | 0.75 | 0.50 |

### Answers (ollama/qwen3:4b, 1376.7 s total)

| Metric | Score |
|--------|-------|
| Answered (not refused/degraded) | 1.00 |
| Top cause matches the incident | 0.75 |
| Top hypothesis cites a root-cause line | 0.75 |
| Refuses unanswerable questions | 1.00 |
| Answers that repeated the injected 'DNS' claim | 0 |
