"""Hybrid BM25 + embedding index, stored as JSON and .npy. Loading never unpickles."""

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Literal

import numpy as np

from log_intel.chunking import Chunk
from log_intel.providers import Embedder, ProviderError

Mode = Literal["hybrid", "bm25", "embed"]
TOKEN = re.compile(r"[a-z0-9_]+(?:[.\-/][a-z0-9_]+)*")
FORMAT_VERSION = 1


class IndexLoadError(RuntimeError):
    """The index is missing, corrupt, or was built differently."""


def tokenize(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tf = [Counter(d) for d in docs]
        self.len = [len(d) for d in docs]
        self.avg = (sum(self.len) / len(docs)) if docs else 0.0
        df = Counter(t for d in docs for t in set(d))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: list[str]) -> np.ndarray:
        out = np.zeros(len(self.tf))
        for i, tf in enumerate(self.tf):
            norm = self.k1 * (1 - self.b + self.b * self.len[i] / (self.avg or 1))
            for t in query:
                f = tf.get(t)
                if f:
                    out[i] += self.idf[t] * f * (self.k1 + 1) / (f + norm)
        return out


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Index:
    def __init__(self, chunks: list[Chunk], vectors: np.ndarray | None, embed_model: str | None):
        self.chunks = chunks
        self.vectors = vectors
        self.embed_model = embed_model
        self.bm25 = BM25([tokenize(c.text) for c in chunks])

    @classmethod
    def build(cls, chunks: list[Chunk], embedder: Embedder | None) -> "Index":
        """Embeds every chunk. If the embedder fails, the index is BM25-only, not broken."""
        vectors, model = None, None
        if embedder and chunks:
            try:
                vectors = _normalize(
                    np.asarray(embedder.embed([c.text for c in chunks]), "float32")
                )
                model = embedder.name
            except ProviderError:
                vectors, model = None, None
        return cls(chunks, vectors, model)

    @property
    def has_vectors(self) -> bool:
        return self.vectors is not None

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        chunks_path = directory / "chunks.json"
        chunks_path.write_text(json.dumps([asdict(c) for c in self.chunks]), encoding="utf-8")
        meta = {
            "format": FORMAT_VERSION,
            "embed_model": self.embed_model,
            "chunks_sha256": _sha256(chunks_path),
        }
        vec_path = directory / "vectors.npy"
        if self.vectors is not None:
            np.save(vec_path, self.vectors, allow_pickle=False)
            meta["vectors_sha256"] = _sha256(vec_path)
        elif vec_path.exists():
            vec_path.unlink()
        (directory / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, directory: Path) -> "Index":
        meta_path = directory / "meta.json"
        if not meta_path.exists():
            raise IndexLoadError(f"no index in {directory}")
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("format") != FORMAT_VERSION:
                raise IndexLoadError("index format changed; rebuild it")
            chunks_path = directory / "chunks.json"
            if _sha256(chunks_path) != meta["chunks_sha256"]:
                raise IndexLoadError("chunks.json checksum mismatch; rebuild the index")
            chunks = [Chunk(**c) for c in json.loads(chunks_path.read_text(encoding="utf-8"))]
            vectors = None
            if "vectors_sha256" in meta:
                vec_path = directory / "vectors.npy"
                if _sha256(vec_path) != meta["vectors_sha256"]:
                    raise IndexLoadError("vectors.npy checksum mismatch; rebuild the index")
                vectors = np.load(vec_path, allow_pickle=False)
                if vectors.shape[0] != len(chunks):
                    raise IndexLoadError("vector count does not match chunk count")
        except (OSError, KeyError, TypeError, ValueError) as e:
            raise IndexLoadError(f"index in {directory} is unreadable: {e}") from e
        return cls(chunks, vectors, meta.get("embed_model"))

    def search(
        self,
        query: str,
        k: int,
        mode: Mode = "hybrid",
        embedder: Embedder | None = None,
    ) -> list[tuple[Chunk, float]]:
        """Reciprocal-rank fusion of BM25 and cosine rankings. Falls back to BM25 when
        vectors or the embedder are unavailable."""
        if not self.chunks:
            return []
        rankings: list[np.ndarray] = []
        if mode in ("hybrid", "bm25"):
            rankings.append(np.argsort(-self.bm25.scores(tokenize(query)), kind="stable"))
        if mode in ("hybrid", "embed") and self.has_vectors and embedder:
            try:
                q = _normalize(np.asarray(embedder.embed([query]), "float32"))[0]
                rankings.append(np.argsort(-(self.vectors @ q), kind="stable"))
            except ProviderError:
                pass
        if not rankings:  # embed-only requested but unavailable
            rankings.append(np.argsort(-self.bm25.scores(tokenize(query)), kind="stable"))
        fused = np.zeros(len(self.chunks))
        for ranking in rankings:
            for rank, idx in enumerate(ranking):
                fused[idx] += 1.0 / (60 + rank + 1)
        top = np.argsort(-fused, kind="stable")[:k]
        return [(self.chunks[i], float(fused[i])) for i in top]


def _normalize(m: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    return m / np.where(norms == 0, 1, norms)
