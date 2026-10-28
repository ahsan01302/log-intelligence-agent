import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from log_intel.config import Settings


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    # Isolate from the developer's shell and any local .env file.
    for key in list(os.environ):
        if key.startswith("LOGINTEL_"):
            monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)


def test_defaults_are_local_and_free():
    s = Settings()
    assert s.provider == "ollama"
    assert s.ollama_base_url == "http://localhost:11434"
    assert s.llm_model == "qwen3:4b"
    assert s.embed_model == "nomic-embed-text"
    assert s.top_k == 5
    assert s.window_seconds == 30


def test_default_paths_are_relative_not_hardcoded():
    s = Settings()
    assert not s.index_dir.is_absolute()
    assert not s.upload_dir.is_absolute()


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("LOGINTEL_TOP_K", "8")
    monkeypatch.setenv("LOGINTEL_OLLAMA_BASE_URL", "http://ollama:11434")
    monkeypatch.setenv("LOGINTEL_INDEX_DIR", "/tmp/idx")
    s = Settings()
    assert s.top_k == 8
    assert s.ollama_base_url == "http://ollama:11434"
    assert s.index_dir == Path("/tmp/idx")


def test_dotenv_file_is_read(tmp_path):
    (tmp_path / ".env").write_text("LOGINTEL_WINDOW_SECONDS=60\n", encoding="utf-8")
    assert Settings().window_seconds == 60


def test_env_beats_dotenv(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("LOGINTEL_TOP_K=3\n", encoding="utf-8")
    monkeypatch.setenv("LOGINTEL_TOP_K", "7")
    assert Settings().top_k == 7


def test_unknown_provider_rejected(monkeypatch):
    monkeypatch.setenv("LOGINTEL_PROVIDER", "made-up")
    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize("field,value", [("TOP_K", "0"), ("WINDOW_SECONDS", "0"),
                                          ("MAX_UPLOAD_MB", "0")])
def test_non_positive_numbers_rejected(monkeypatch, field, value):
    monkeypatch.setenv(f"LOGINTEL_{field}", value)
    with pytest.raises(ValidationError):
        Settings()


def test_api_key_is_secret_and_optional(monkeypatch):
    assert Settings().api_key is None
    monkeypatch.setenv("LOGINTEL_API_KEY", "sk-test-not-real")
    s = Settings()
    assert s.api_key.get_secret_value() == "sk-test-not-real"
    assert "sk-test-not-real" not in repr(s)
