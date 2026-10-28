import hashlib
import json

import pytest

from log_intel.config import Settings
from log_intel.index import tokenize
from log_intel.providers import ProviderError


class FakeEmbedder:
    """Deterministic hashed bag-of-words vectors; no network."""

    name = "fake/embed"

    def __init__(self, fail: bool = False):
        self.fail = fail

    def embed(self, texts):
        if self.fail:
            raise ProviderError("embedder down")
        out = []
        for text in texts:
            vec = [0.0] * 64
            for tok in tokenize(text):
                vec[int(hashlib.md5(tok.encode()).hexdigest(), 16) % 64] += 1.0
            out.append(vec)
        return out


class FakeLLM:
    """Returns canned replies in order; an Exception reply is raised, a callable reply is
    called with the user prompt."""

    name = "fake/llm"

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def complete_json(self, system, user, schema):
        self.calls.append({"system": system, "user": user, "schema": schema})
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(reply, Exception):
            raise reply
        if callable(reply):
            reply = reply(user)
        return reply if isinstance(reply, str) else json.dumps(reply)


@pytest.fixture
def settings(tmp_path, monkeypatch):
    for key in list(__import__("os").environ):
        if key.startswith("LOGINTEL_"):
            monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)
    return Settings(
        index_dir=tmp_path / "index",
        upload_dir=tmp_path / "uploads",
        history_path=tmp_path / "history.db",
        max_upload_mb=1,
    )
