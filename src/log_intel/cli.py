"""Command line: log-intel generate | index | ask | eval | serve"""

import json
from pathlib import Path

import typer

from log_intel.config import Settings
from log_intel.generator import write_dataset
from log_intel.index import IndexLoadError
from log_intel.providers import ProviderError, make_embedder, make_llm
from log_intel.service import LogIntelService

app = typer.Typer(help="Cited root-cause hypotheses from application logs.", no_args_is_help=True)


def _service(with_llm: bool = True) -> LogIntelService:
    settings = Settings()
    llm = None
    if with_llm:
        try:
            llm = make_llm(settings)
        except ProviderError as e:
            typer.secho(f"LLM disabled: {e}", fg="yellow", err=True)
    return LogIntelService(settings, llm, make_embedder(settings))


@app.command()
def generate(
    out: Path = typer.Option(Path("data/synthetic"), help="Output folder"),
    seed: int = typer.Option(7, help="Random seed; the same seed gives identical output"),
    minutes: int = typer.Option(60, min=10, help="Length of the simulated period"),
) -> None:
    """Write a synthetic log with injected incidents and its labels.json."""
    log_path, labels_path = write_dataset(out, seed, minutes)
    typer.echo(f"wrote {log_path} and {labels_path}")


@app.command()
def index(paths: list[Path] = typer.Argument(..., exists=True, dir_okay=False)) -> None:
    """Build the index from log files."""
    idx = _service(with_llm=False).reindex(paths)
    kind = "hybrid (BM25 + embeddings)" if idx.has_vectors else "BM25 only (embedder unavailable)"
    typer.echo(f"indexed {len(idx.chunks)} chunks from {len(paths)} file(s): {kind}")


@app.command()
def ask(
    question: str,
    top_k: int = typer.Option(5, min=1, max=20),
    mode: str = typer.Option("hybrid", help="hybrid | bm25 | embed"),
    as_json: bool = typer.Option(False, "--json", help="Print the raw JSON answer"),
) -> None:
    """Ask a question about the indexed logs."""
    if mode not in ("hybrid", "bm25", "embed"):
        raise typer.BadParameter("must be hybrid, bm25 or embed", param_hint="--mode")
    try:
        answer = _service().ask(question, top_k, mode)  # type: ignore[arg-type]
    except IndexLoadError as e:
        typer.secho(str(e), fg="red", err=True)
        raise typer.Exit(1) from e
    if as_json:
        typer.echo(answer.model_dump_json(indent=2))
        return
    typer.secho(f"[{answer.status}] {answer.model or 'no model'}", bold=True)
    for i, h in enumerate(answer.hypotheses, 1):
        cites = ", ".join(f"{c.file}:{c.start_line}-{c.end_line}" for c in h.citations)
        typer.echo(f"\n{i}. {h.cause}  (confidence: {h.confidence})\n   evidence: {cites}")
        if h.explanation:
            typer.echo(f"   {h.explanation}")
        for step in h.next_steps:
            typer.echo(f"   - {step}")
    if answer.status != "answered":
        for e in answer.evidence[:3]:
            typer.echo(f"\n{e.file}:{e.start_line}-{e.end_line}\n{e.text[:400]}")
    for note in answer.notes:
        typer.secho(f"note: {note}", fg="yellow")


@app.command("eval")
def run_eval(
    labels: Path = typer.Option(Path("data/synthetic/labels.json"), exists=True),
    k: int = typer.Option(5, min=1),
    answers: bool = typer.Option(False, help="Also evaluate LLM answers (slow on CPU)"),
    out: Path = typer.Option(Path("evals/results.md")),
) -> None:
    """Score retrieval (hit@k, MRR) and optionally answers against labels.json."""
    from log_intel.evals import evaluate

    report = evaluate(_service(with_llm=answers), labels, k, answers)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report.markdown, encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(report.data, indent=2), encoding="utf-8")
    typer.echo(report.markdown)


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the HTTP API."""
    import uvicorn

    uvicorn.run("log_intel.api:create_app", factory=True, host=host, port=port)


if __name__ == "__main__":
    app()
