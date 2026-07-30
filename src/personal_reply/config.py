from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


from personal_reply.rag.contact_attributes import ContactAttributes

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.toml"


@dataclass(frozen=True)
class Config:
    ollama_base_url: str
    embedding_model: str
    chat_model: str
    exports_dir: Path
    lancedb_uri: Path
    sender_names: tuple[str, ...]
    top_k: int
    platform: str
    user_name: str
    embed_batch_size: int
    context_messages_before: int
    context_messages_after: int
    candidate_multiplier: int
    vector_weight: float
    recency_weight: float
    recency_half_life_days: float
    contact_match_weight: float
    category_match_weight: float
    chrome_debug_port: int
    chrome_debug_url: str
    insert_into_compose: bool
    stale_after_hours: float
    reopen_when_last_from_me: bool
    contact_attributes: ContactAttributes
    research_enabled: bool
    research_auto: bool
    research_max_queries: int
    research_max_results_per_query: int
    research_auto_on_reopen: bool

    def resolve(self, path: Path) -> Path:
        if path.is_absolute():
            return path
        return PROJECT_ROOT / path


def load_config(path: Path | None = None) -> Config:
    config_path = path or DEFAULT_CONFIG_PATH
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    root = config_path.parent
    paths = raw["paths"]
    ingest = raw.get("ingest", {})
    rag = raw.get("rag", {})
    reply = raw.get("reply", {})
    browser = raw.get("browser", {})
    research = raw.get("research", {})
    ollama = raw["ollama"]

    debug_port = int(browser.get("chrome_debug_port", 9222))

    return Config(
        ollama_base_url=ollama["base_url"],
        embedding_model=ollama["embedding_model"],
        chat_model=ollama["chat_model"],
        exports_dir=root / paths["exports_dir"],
        lancedb_uri=root / paths["lancedb_uri"],
        sender_names=tuple(ingest.get("sender_names", ["You"])),
        top_k=int(rag.get("top_k", 8)),
        platform=str(rag.get("platform", "whatsapp")),
        user_name=str(reply.get("user_name", "Sam")),
        embed_batch_size=int(ingest.get("embed_batch_size", 32)),
        context_messages_before=int(ingest.get("context_messages_before", 3)),
        context_messages_after=int(ingest.get("context_messages_after", 2)),
        candidate_multiplier=int(rag.get("candidate_multiplier", 5)),
        vector_weight=float(rag.get("vector_weight", 0.7)),
        recency_weight=float(rag.get("recency_weight", 0.3)),
        recency_half_life_days=float(rag.get("recency_half_life_days", 180)),
        contact_match_weight=float(rag.get("contact_match_weight", 1.0)),
        category_match_weight=float(rag.get("category_match_weight", 0.65)),
        chrome_debug_port=debug_port,
        chrome_debug_url=str(browser.get("chrome_debug_url", f"http://localhost:{debug_port}")),
        insert_into_compose=bool(browser.get("insert_into_compose", True)),
        stale_after_hours=float(reply.get("stale_after_hours", 48)),
        reopen_when_last_from_me=bool(reply.get("reopen_when_last_from_me", True)),
        contact_attributes=ContactAttributes.from_config(config_path),
        research_enabled=bool(research.get("enabled", True)),
        research_auto=bool(research.get("auto", True)),
        research_max_queries=int(research.get("max_queries", 2)),
        research_max_results_per_query=int(research.get("max_results_per_query", 3)),
        research_auto_on_reopen=bool(research.get("auto_on_reopen", False)),
    )
