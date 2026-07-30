from __future__ import annotations

from typing import Any

import httpx

from personal_reply.config import Config


class OllamaChatClient:
    def __init__(self, config: Config, client: httpx.Client | None = None) -> None:
        self._config = config
        self._client = client or httpx.Client(
            base_url=config.ollama_base_url,
            timeout=180.0,
        )

    def chat(self, messages: list[dict[str, str]]) -> str:
        response = self._client.post(
            "/api/chat",
            json={
                "model": self._config.chat_model,
                "messages": messages,
                "stream": False,
            },
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        message = payload.get("message", {})
        content = message.get("content", "")
        return str(content).strip()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> OllamaChatClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
