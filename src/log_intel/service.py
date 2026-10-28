"""Ingest, index and ask: the shared core behind the API, CLI and UI."""

import re
import threading
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from log_intel.answer import Answer, answer_question
from log_intel.chunking import build_chunks
from log_intel.config import Settings
from log_intel.index import Index, IndexLoadError, Mode
from log_intel.parsing import parse_file
from log_intel.providers import LLM, Embedder

ALLOWED_SUFFIXES = {".log", ".txt"}
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")
READ_BLOCK = 1024 * 1024


class UploadRejected(ValueError):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def safe_filename(name: str | None) -> str:
    """Reduce a client-supplied name to a plain basename, or reject it."""
    base = PurePosixPath((name or "").replace("\\", "/")).name
    if not SAFE_NAME.fullmatch(base) or base in {".", ".."}:
        raise UploadRejected("file name must be letters, digits, '.', '_' or '-' (max 100)")
    if Path(base).suffix.lower() not in ALLOWED_SUFFIXES:
        raise UploadRejected("only .log and .txt files are accepted", status=415)
    return base


class LogIntelService:
    def __init__(self, settings: Settings, llm: LLM | None, embedder: Embedder | None):
        self.settings = settings
        self.llm = llm
        self.embedder = embedder
        self._lock = threading.Lock()
        self.index: Index | None = None
        try:
            self.index = Index.load(settings.index_dir)
        except IndexLoadError:
            self.index = None

    def files(self) -> list[Path]:
        d = self.settings.upload_dir
        return (
            sorted(p for p in d.iterdir() if p.suffix.lower() in ALLOWED_SUFFIXES)
            if d.exists()
            else []
        )

    def save_upload(self, name: str | None, stream: BinaryIO) -> Path:
        upload_dir = self.settings.upload_dir.resolve()
        upload_dir.mkdir(parents=True, exist_ok=True)
        base = safe_filename(name)
        target = upload_dir / base
        stem, suffix, n = target.stem, target.suffix, 1
        while target.exists():  # never overwrite an earlier upload
            target = upload_dir / f"{stem}-{n}{suffix}"
            n += 1
        if target.resolve().parent != upload_dir:
            raise UploadRejected("invalid file path")

        limit = self.settings.max_upload_mb * 1024 * 1024
        size = 0
        tmp = target.with_name(target.name + ".part")
        try:
            with tmp.open("wb") as out:
                while block := stream.read(READ_BLOCK):
                    size += len(block)
                    if size > limit:
                        raise UploadRejected(
                            f"file exceeds {self.settings.max_upload_mb} MB", status=413
                        )
                    out.write(block)
            if size == 0:
                raise UploadRejected("file is empty")
            tmp.replace(target)
        finally:
            tmp.unlink(missing_ok=True)
        return target

    def reindex(self, paths: list[Path] | None = None) -> Index:
        """Rebuild the index from every uploaded file (or the given paths)."""
        with self._lock:
            records = [r for p in (paths or self.files()) for r in parse_file(p)]
            chunks = build_chunks(
                records,
                strategy=self.settings.chunk_strategy,
                window_seconds=self.settings.window_seconds,
                max_lines=self.settings.max_chunk_lines,
            )
            index = Index.build(chunks, self.embedder)
            index.save(self.settings.index_dir)
            self.index = index
            return index

    def ask(self, question: str, top_k: int | None = None, mode: Mode = "hybrid") -> Answer:
        if self.index is None:
            raise IndexLoadError("no logs indexed yet; upload or index a log file first")
        hits = self.index.search(question, top_k or self.settings.top_k, mode, self.embedder)
        answer = answer_question(question, hits, self.llm)
        if not self.index.has_vectors:
            answer.notes.append("index has no embeddings (embedder was unavailable); BM25 only")
        return answer
