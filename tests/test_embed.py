import json

import httpx
import pytest

from personal_reply.config import Config
from personal_reply.rag.contact_attributes import ContactAttributes
from personal_reply.rag.embed import OllamaEmbedder
from personal_reply.rag.errors import OllamaModelError, OllamaUnavailableError


def _config() -> Config:
    return Config(
        ollama_base_url="http://localhost:11434",
        embedding_model="nomic-embed-text",
        chat_model="llama3.2",
        exports_dir=__import__("pathlib").Path("data/exports"),
        lancedb_uri=__import__("pathlib").Path("data/style.lance"),
        sender_names=("Sameer",),
        top_k=8,
        platform="whatsapp",
        user_name="Sam",
        embed_batch_size=2,
        context_messages_before=3,
        context_messages_after=2,
        candidate_multiplier=5,
        vector_weight=0.7,
        recency_weight=0.3,
        recency_half_life_days=180,
        chrome_debug_port=9222,
        chrome_debug_url="http://localhost:9222",
        insert_into_compose=True,
        stale_after_hours=48,
        reopen_when_last_from_me=True,
        contact_match_weight=1.0,
        category_match_weight=0.65,
        contact_attributes=ContactAttributes.empty(),
        research_enabled=True,
        research_auto=True,
        research_max_queries=2,
        research_max_results_per_query=3,
        research_auto_on_reopen=False,
    )


def test_embed_many_batches_requests() -> None:
    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        calls.append(payload)
        embeddings = [[0.1, 0.2] for _ in payload["input"]]
        return httpx.Response(200, json={"embeddings": embeddings})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="http://localhost:11434")

    with OllamaEmbedder(_config(), client=client) as embedder:
        vectors = embedder.embed_many(["a", "b", "c"], batch_size=2)

    assert len(vectors) == 3
    assert len(calls) == 2
    assert calls[0]["input"] == ["a", "b"]
    assert calls[1]["input"] == ["c"]


def test_ensure_ready_raises_when_ollama_unreachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="http://localhost:11434")

    with OllamaEmbedder(_config(), client=client) as embedder:
        with pytest.raises(OllamaUnavailableError, match="Cannot reach Ollama"):
            embedder.ensure_ready()


def test_ensure_ready_raises_when_model_missing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": "llama3.2"}]})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="http://localhost:11434")

    with OllamaEmbedder(_config(), client=client) as embedder:
        with pytest.raises(OllamaModelError, match="nomic-embed-text"):
            embedder.ensure_ready()
