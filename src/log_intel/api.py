"""HTTP API. Run with: uvicorn log_intel.api:create_app --factory"""

from typing import Literal

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from log_intel.answer import Answer
from log_intel.config import Settings
from log_intel.history import HistoryItem, HistoryStore, Investigation
from log_intel.index import IndexLoadError
from log_intel.providers import LLM, Embedder, ProviderError, make_embedder, make_llm
from log_intel.service import LogIntelService, UploadRejected


class AskRequest(BaseModel):
    # POST body, not a query string, so questions don't end up in access logs.
    question: str = Field(min_length=3, max_length=500)
    top_k: int | None = Field(default=None, ge=1, le=20)
    mode: Literal["hybrid", "bm25", "embed"] = "hybrid"


class UploadResponse(BaseModel):
    filename: str
    files_indexed: int
    chunks: int
    embeddings: bool


class Health(BaseModel):
    status: Literal["ok"]
    files: int
    chunks: int
    embeddings: bool
    llm: str | None
    provider: str
    embed_model: str
    max_upload_mb: int
    default_top_k: int


def _indexed_files(service: LogIntelService) -> int:
    # Count files actually in the index, whether they came from /upload or the CLI.
    return len({c.file for c in service.index.chunks}) if service.index else 0


def create_app(
    settings: Settings | None = None,
    llm: LLM | None = None,
    embedder: Embedder | None = None,
) -> FastAPI:
    settings = settings or Settings()
    if llm is None:
        try:
            llm = make_llm(settings)
        except ProviderError:
            llm = None  # e.g. paid provider without a key: answers run in degraded mode
    service = LogIntelService(settings, llm, embedder or make_embedder(settings))
    history = HistoryStore(settings.history_path)

    app = FastAPI(
        title="Log Intelligence Agent",
        version="0.2.0",
        description="Cited root-cause hypotheses from application logs (personal project).",
    )
    app.state.service = service

    @app.get("/health", response_model=Health)
    def health() -> Health:
        idx = service.index
        return Health(
            status="ok",
            files=_indexed_files(service),
            chunks=len(idx.chunks) if idx else 0,
            embeddings=bool(idx and idx.has_vectors),
            llm=service.llm.name if service.llm else None,
            provider=settings.provider,
            embed_model=settings.embed_model,
            max_upload_mb=settings.max_upload_mb,
            default_top_k=settings.top_k,
        )

    @app.post("/upload", response_model=UploadResponse, status_code=201)
    def upload(file: UploadFile = File(...)) -> UploadResponse:
        try:
            path = service.save_upload(file.filename, file.file)
        except UploadRejected as e:
            raise HTTPException(status_code=e.status, detail=str(e)) from e
        index = service.reindex()
        return UploadResponse(
            filename=path.name,
            files_indexed=_indexed_files(service),
            chunks=len(index.chunks),
            embeddings=index.has_vectors,
        )

    @app.post("/ask", response_model=Answer)
    def ask(req: AskRequest) -> Answer:
        try:
            answer = service.ask(req.question, req.top_k, req.mode)
        except IndexLoadError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
        answer.id = history.add(answer).id
        return answer

    @app.get("/history", response_model=list[HistoryItem])
    def list_history(limit: int = Query(default=50, ge=1, le=200)) -> list[HistoryItem]:
        return history.list(limit)

    @app.get("/history/{item_id}", response_model=Investigation)
    def get_history(item_id: str) -> Investigation:
        item = history.get(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="investigation not found")
        return item

    @app.delete("/history/{item_id}", status_code=204)
    def delete_history(item_id: str) -> None:
        if not history.delete(item_id):
            raise HTTPException(status_code=404, detail="investigation not found")

    return app
