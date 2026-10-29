"""LLM and embedding clients over plain HTTP. Ollama is the default (local and free);
Anthropic and OpenAI are optional and need LOGINTEL_API_KEY."""

import json
import re
from typing import Any, Protocol

import httpx

from log_intel.config import Settings

THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)


class ProviderError(RuntimeError):
    """The model could not be reached or returned something unusable."""


class LLM(Protocol):
    name: str

    def complete_json(self, system: str, user: str, schema: dict[str, Any]) -> str: ...


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def _post(client: httpx.Client, url: str, **kwargs: Any) -> dict[str, Any]:
    try:
        resp = client.post(url, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        body = e.response.text[:300]
        raise ProviderError(f"{url} returned {e.response.status_code}: {body}") from e
    except (httpx.HTTPError, ValueError) as e:
        raise ProviderError(f"{url} failed: {e}") from e


class OllamaLLM:
    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self.name = f"ollama/{settings.llm_model}"
        self.model = settings.llm_model
        self.url = settings.ollama_base_url.rstrip("/") + "/api/chat"
        self.options = {
            "temperature": 0,
            "num_ctx": settings.llm_num_ctx,
            "num_predict": settings.llm_max_tokens,
        }
        self.client = client or httpx.Client(timeout=settings.llm_timeout_s)

    def complete_json(self, system: str, user: str, schema: dict[str, Any]) -> str:
        data = _post(
            self.client,
            self.url,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "format": schema,  # Ollama structured outputs: constrain to the JSON schema
                "think": False,  # qwen3 would otherwise spend its budget on hidden reasoning
                "stream": False,
                "options": self.options,
            },
        )
        try:
            content = data["message"]["content"]
        except (KeyError, TypeError) as e:
            raise ProviderError(f"unexpected Ollama response: {str(data)[:200]}") from e
        return THINK_BLOCK.sub("", content).strip()


class OllamaEmbedder:
    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self.name = f"ollama/{settings.embed_model}"
        self.model = settings.embed_model
        self.url = settings.ollama_base_url.rstrip("/") + "/api/embed"
        self.batch = settings.embed_batch_size
        self.client = client or httpx.Client(timeout=settings.llm_timeout_s)

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch):
            data = _post(
                self.client,
                self.url,
                json={"model": self.model, "input": texts[i : i + self.batch]},
            )
            vectors = data.get("embeddings")
            if not isinstance(vectors, list) or len(vectors) != len(texts[i : i + self.batch]):
                raise ProviderError("Ollama returned the wrong number of embeddings")
            out.extend(vectors)
        return out


class AnthropicLLM:
    URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        if not settings.api_key:
            raise ProviderError("LOGINTEL_API_KEY is required for the anthropic provider")
        self.name = f"anthropic/{settings.llm_model}"
        self.model = settings.llm_model
        self.key = settings.api_key.get_secret_value()
        self.client = client or httpx.Client(timeout=settings.llm_timeout_s)

    def complete_json(self, system: str, user: str, schema: dict[str, Any]) -> str:
        data = _post(
            self.client,
            self.URL,
            headers={"x-api-key": self.key, "anthropic-version": "2023-06-01"},
            json={
                "model": self.model,
                "max_tokens": 2048,
                "temperature": 0,
                "system": system
                + "\n\nReply with only a JSON object matching this schema:\n"
                + json.dumps(schema),
                "messages": [{"role": "user", "content": user}],
            },
        )
        try:
            return "".join(b["text"] for b in data["content"] if b.get("type") == "text")
        except (KeyError, TypeError) as e:
            raise ProviderError("unexpected Anthropic response") from e


class OpenAILLM:
    URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        if not settings.api_key:
            raise ProviderError("LOGINTEL_API_KEY is required for the openai provider")
        self.name = f"openai/{settings.llm_model}"
        self.model = settings.llm_model
        self.key = settings.api_key.get_secret_value()
        self.client = client or httpx.Client(timeout=settings.llm_timeout_s)

    def complete_json(self, system: str, user: str, schema: dict[str, Any]) -> str:
        data = _post(
            self.client,
            self.URL,
            headers={"Authorization": f"Bearer {self.key}"},
            json={
                "model": self.model,
                "temperature": 0,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "answer", "schema": schema},
                },
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError("unexpected OpenAI response") from e


def make_llm(settings: Settings) -> LLM:
    providers = {"ollama": OllamaLLM, "anthropic": AnthropicLLM, "openai": OpenAILLM}
    return providers[settings.provider](settings)


def make_embedder(settings: Settings) -> Embedder:
    # Embeddings always come from Ollama, so a paid provider is never needed to index.
    return OllamaEmbedder(settings)
