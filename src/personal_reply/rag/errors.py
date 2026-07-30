from __future__ import annotations


class OllamaUnavailableError(ConnectionError):
    """Raised when Ollama cannot be reached or is missing a required model."""


class OllamaModelError(RuntimeError):
    """Raised when a configured Ollama model is not available locally."""
