from __future__ import annotations

import logging
from collections.abc import Callable

import httpx

from personal_reply.config import Config
from personal_reply.rag.errors import OllamaModelError, OllamaUnavailableError

logger = logging.getLogger(__name__)


class OllamaEmbedder:
    def __init__(self, config: Config, client: httpx.Client | None = None) -> None:
        self._config = config
        self._client = client or httpx.Client(
            base_url=config.ollama_base_url,
            timeout=120.0,
        )

    def ensure_ready(self) -> None:
        """Verify Ollama is reachable and the embedding model is available."""
        try:
            response = self._client.get("/api/tags")
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise OllamaUnavailableError(
                f"Cannot reach Ollama at {self._config.ollama_base_url}. "
                "Start it with `ollama serve` or open the Ollama app, then run ingest again."
            ) from exc
        except httpx.HTTPError as exc:
            raise OllamaUnavailableError(
                f"Ollama health check failed at {self._config.ollama_base_url}: {exc}"
            ) from exc

        models = {
            model.get("name", "").split(":")[0]
            for model in response.json().get("models", [])
        }
        required = self._config.embedding_model.split(":")[0]
        if required not in models:
            raise OllamaModelError(
                f"Embedding model '{self._config.embedding_model}' is not available locally. "
                f"Pull it with: ollama pull {self._config.embedding_model}"
            )

        logger.info(
            "Ollama is ready (model=%s, url=%s)",
            self._config.embedding_model,
            self._config.ollama_base_url,
        )

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(
        self,
        texts: list[str],
        *,
        batch_size: int | None = None,
        on_batch: Callable[[int, int, int], None] | None = None,
    ) -> list[list[float]]:
        if not texts:
            return []

        batch_size = batch_size or self._config.embed_batch_size
        total_batches = (len(texts) + batch_size - 1) // batch_size
        vectors: list[list[float]] = []

        for batch_index, start in enumerate(range(0, len(texts), batch_size), start=1):
            batch = texts[start : start + batch_size]
            if on_batch:
                on_batch(batch_index, total_batches, len(batch))

            try:
                response = self._client.post(
                    "/api/embed",
                    json={
                        "model": self._config.embedding_model,
                        "input": batch,
                    },
                )
                response.raise_for_status()
            except httpx.ConnectError as exc:
                raise OllamaUnavailableError(
                    f"Lost connection to Ollama at {self._config.ollama_base_url} "
                    f"while embedding batch {batch_index}/{total_batches}. "
                    "Ensure Ollama stays running and retry ingest."
                ) from exc
            except httpx.HTTPError as exc:
                raise RuntimeError(
                    f"Ollama embedding failed for batch {batch_index}/{total_batches}: {exc}"
                ) from exc

            payload = response.json()
            batch_vectors = payload.get("embeddings")
            if not batch_vectors or len(batch_vectors) != len(batch):
                raise RuntimeError(
                    f"Ollama returned {len(batch_vectors or [])} embeddings "
                    f"for batch {batch_index}/{total_batches}, expected {len(batch)}."
                )
            vectors.extend(batch_vectors)

        return vectors

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> OllamaEmbedder:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
