import io
import re

import httpx
import pytest
from conftest import FakeEmbedder, FakeLLM
from fastapi.testclient import TestClient

from log_intel.api import create_app
from log_intel.generator import generate
from log_intel.providers import AnthropicLLM, OllamaEmbedder, OllamaLLM, OpenAILLM, ProviderError
from log_intel.service import safe_filename


def REPLY(prompt):
    # Cite the first chunk the model was actually shown.
    first = re.search(r'<log_chunk id="(C\d+)"', prompt)[1]
    return {
        "logs_answer_the_question": True,
        "hypotheses": [
            {
                "cause": "pool exhausted",
                "explanation": "connections exhausted",
                "confidence": "high",
                "citations": [first],
                "next_steps": [],
            }
        ],
    }


@pytest.fixture
def client(settings):
    return TestClient(create_app(settings, llm=FakeLLM(REPLY), embedder=FakeEmbedder()))


def _log_bytes():
    lines, _ = generate(seed=1, minutes=10)
    return ("\n".join(lines) + "\n").encode()


def test_upload_indexes_and_ask_answers_with_citations(client):
    r = client.post("/upload", files={"file": ("app.log", _log_bytes())})
    assert r.status_code == 201, r.text
    assert r.json()["chunks"] > 0 and r.json()["embeddings"] is True
    r = client.post("/ask", json={"question": "Why are orders failing?"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "answered"
    assert body["hypotheses"][0]["citations"][0]["file"] == "app.log"


def test_upload_path_traversal_stays_inside_upload_dir(client, settings):
    # Regression for v1: "../escaped.txt" was written outside the logs folder.
    r = client.post(
        "/upload", files={"file": ("../escaped.txt", b"2026-03-14T09:00:00Z INFO a x\n")}
    )
    assert r.status_code == 201
    assert r.json()["filename"] == "escaped.txt"
    assert (settings.upload_dir / "escaped.txt").exists()
    assert not (settings.upload_dir.parent / "escaped.txt").exists()


@pytest.mark.parametrize("name", ["..\\..\\evil.log", "/etc/passwd.log", "....log/../x.log"])
def test_hostile_names_are_reduced_to_basenames(name):
    assert "/" not in safe_filename(name) and "\\" not in safe_filename(name)


@pytest.mark.parametrize(
    ("name", "status"), [("evil.exe", 415), ("", 400), ("bad name!.log", 400), ("..", 400)]
)
def test_bad_names_and_types_are_rejected(client, name, status):
    r = client.post("/upload", files={"file": (name, b"data")})
    assert r.status_code in (status, 422)


def test_upload_size_limit(client):
    r = client.post("/upload", files={"file": ("big.log", io.BytesIO(b"a" * (1024 * 1024 + 1)))})
    assert r.status_code == 413
    assert not list((client.app.state.service.settings.upload_dir).glob("*"))


def test_same_name_uploads_do_not_overwrite(client):
    for _ in range(2):
        assert client.post("/upload", files={"file": ("a.log", _log_bytes())}).status_code == 201
    assert client.get("/health").json()["files"] == 2


def test_ask_before_upload_is_409_and_validates_input(client):
    assert client.post("/ask", json={"question": "why is it down?"}).status_code == 409
    assert client.post("/ask", json={"question": ""}).status_code == 422
    assert client.get("/ask").status_code == 405  # questions never go in the URL


def test_health(client):
    assert client.get("/health").json() == {
        "status": "ok",
        "files": 0,
        "chunks": 0,
        "embeddings": False,
        "llm": "fake/llm",
        "provider": "ollama",
        "embed_model": "nomic-embed-text",
        "max_upload_mb": 1,
        "default_top_k": 5,
    }


def test_health_counts_files_indexed_from_the_cli(settings):
    # v2 quirk: an index built by `log-intel index` showed "files: 0" in the UI.
    lines, _ = generate(seed=2, minutes=10)
    log = settings.upload_dir.parent / "cli.log"
    log.write_text("\n".join(lines), encoding="utf-8")
    app = create_app(settings, llm=FakeLLM(REPLY), embedder=FakeEmbedder())
    app.state.service.reindex([log])
    assert TestClient(app).get("/health").json()["files"] == 1


def test_investigations_are_saved_listed_fetched_and_deleted(client):
    client.post("/upload", files={"file": ("app.log", _log_bytes())})
    first = client.post("/ask", json={"question": "Why are orders failing?"}).json()
    second = client.post("/ask", json={"question": "Why is the db down?"}).json()
    assert first["id"] and second["id"] and first["id"] != second["id"]

    items = client.get("/history").json()
    assert [i["question"] for i in items] == ["Why is the db down?", "Why are orders failing?"]
    assert items[0]["top_cause"] == "pool exhausted" and items[0]["status"] == "answered"

    full = client.get(f"/history/{first['id']}").json()
    assert full["answer"]["hypotheses"][0]["citations"][0]["file"] == "app.log"

    assert client.delete(f"/history/{first['id']}").status_code == 204
    assert client.get(f"/history/{first['id']}").status_code == 404
    assert client.delete(f"/history/{first['id']}").status_code == 404
    assert len(client.get("/history").json()) == 1


def test_failed_asks_are_not_saved(client):
    assert client.post("/ask", json={"question": "anything?"}).status_code == 409
    assert client.get("/history").json() == []


def _mock(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_ollama_request_shape_and_think_stripping(settings):
    seen = {}

    def handler(request):
        seen.update(__import__("json").loads(request.content))
        return httpx.Response(200, json={"message": {"content": '<think>hmm</think>{"a": 1}'}})

    out = OllamaLLM(settings, _mock(handler)).complete_json("sys", "user", {"type": "object"})
    assert out == '{"a": 1}'
    assert (
        seen["think"] is False and seen["stream"] is False and seen["format"] == {"type": "object"}
    )
    # Context window is set explicitly so Ollama never silently truncates the log evidence.
    assert seen["options"] == {"temperature": 0, "num_ctx": 8192, "num_predict": 1024}


def test_ollama_errors_become_provider_errors(settings):
    down = _mock(lambda r: (_ for _ in ()).throw(httpx.ConnectError("refused")))
    with pytest.raises(ProviderError):
        OllamaLLM(settings, down).complete_json("s", "u", {})
    bad = _mock(lambda r: httpx.Response(404, text="model not found"))
    with pytest.raises(ProviderError, match="404"):
        OllamaEmbedder(settings, bad).embed(["x"])


def test_paid_providers_need_a_key_and_send_it_in_headers(settings):
    with pytest.raises(ProviderError, match="LOGINTEL_API_KEY"):
        AnthropicLLM(settings)
    keyed = settings.model_copy(update={"api_key": __import__("pydantic").SecretStr("sk-test")})
    seen = {}

    def anthropic(request):
        seen["anthropic"] = request.headers["x-api-key"]
        return httpx.Response(200, json={"content": [{"type": "text", "text": "{}"}]})

    def openai(request):
        seen["openai"] = request.headers["authorization"]
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    assert AnthropicLLM(keyed, _mock(anthropic)).complete_json("s", "u", {}) == "{}"
    assert OpenAILLM(keyed, _mock(openai)).complete_json("s", "u", {}) == "{}"
    assert seen == {"anthropic": "sk-test", "openai": "Bearer sk-test"}
