from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from personal_reply.config import Config
from personal_reply.rag.contact_attributes import ContactAttributes
from personal_reply.research.search import SearchResult
from personal_reply.research.subagent import (
    _parse_queries,
    plan_search_queries,
    run_research_subagent,
    should_invoke_research,
    summarize_research,
)


def _config(*, enabled: bool = True, auto_on_reopen: bool = False) -> Config:
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
        research_enabled=enabled,
        research_auto=True,
        research_max_queries=2,
        research_max_results_per_query=2,
        research_auto_on_reopen=auto_on_reopen,
    )


def test_parse_queries_strips_numbering() -> None:
    raw = "1. weather Mumbai today\n2) cricket score\n"
    assert _parse_queries(raw, max_queries=3) == [
        "weather Mumbai today",
        "cricket score",
    ]


def test_should_invoke_research_parses_yes() -> None:
    chat = MagicMock()
    chat.chat.return_value = "YES"

    assert should_invoke_research(
        chat,
        mode="reopen",
        contact="Papa New",
        incoming_text=None,
        thread_context="Long time no chat",
        reopen_context="Stale thread",
        hours_since_last=72.0,
    ) is True


def test_should_invoke_research_parses_no() -> None:
    chat = MagicMock()
    chat.chat.return_value = "NO"

    assert not should_invoke_research(
        chat,
        mode="respond",
        contact="Papa New",
        incoming_text="On my way",
        thread_context="Papa New: Kahan ho?\nSameer: On my way",
        reopen_context=None,
        hours_since_last=0.5,
    )


def test_should_invoke_research_falls_back_to_reopen_on_error() -> None:
    chat = MagicMock()
    chat.chat.side_effect = RuntimeError("down")

    assert should_invoke_research(
        chat,
        mode="reopen",
        contact=None,
        incoming_text=None,
        thread_context="",
        reopen_context="Stale",
        hours_since_last=48.0,
    ) is True


def test_plan_search_queries_uses_chat_output(monkeypatch: pytest.MonkeyPatch) -> None:
    chat = MagicMock()
    chat.chat.return_value = "1. IPL news today\n2. Mumbai weather forecast"

    queries = plan_search_queries(
        chat,
        thread_context="Long time no chat",
        contact="Papa New",
        mode="reopen",
        incoming_text=None,
        reopen_context="Stale thread",
        max_queries=2,
    )

    assert queries == ["IPL news today", "Mumbai weather forecast"]
    chat.chat.assert_called_once()


def test_plan_search_queries_falls_back_on_empty_response() -> None:
    chat = MagicMock()
    chat.chat.return_value = ""

    queries = plan_search_queries(
        chat,
        thread_context="",
        contact="Papa New",
        mode="reopen",
        incoming_text=None,
        reopen_context=None,
        max_queries=2,
    )

    assert len(queries) == 2
    assert any("weather" in q.casefold() for q in queries)


def test_run_research_subagent_disabled_returns_none() -> None:
    chat = MagicMock()
    assert run_research_subagent(
        chat,
        config=_config(enabled=False),
        thread_context="hello",
        contact="Papa New",
        mode="respond",
        incoming_text="Hi",
    ) is None
    chat.chat.assert_not_called()


def test_run_research_subagent_returns_brief(monkeypatch: pytest.MonkeyPatch) -> None:
    chat = MagicMock()
    chat.chat.side_effect = [
        "weather Mumbai\nsports news",
        "Rain tomorrow. Big match tonight.",
    ]

    def fake_search(query: str, *, max_results: int) -> list[SearchResult]:
        return [
            SearchResult(
                title=f"Result for {query}",
                snippet="snippet text",
                url="https://example.com",
            )
        ]

    monkeypatch.setattr(
        "personal_reply.research.subagent.search_web",
        fake_search,
    )

    brief = run_research_subagent(
        chat,
        config=_config(),
        thread_context="Long time",
        contact="Papa New",
        mode="reopen",
        reopen_context="Stale",
    )

    assert brief is not None
    assert brief.queries == ("weather Mumbai", "sports news")
    assert "Rain tomorrow" in brief.summary
    assert brief.snippets


def test_summarize_research_without_results() -> None:
    chat = MagicMock()
    assert (
        summarize_research(
            chat,
            contact=None,
            mode="reopen",
            queries=["weather"],
            results=[],
            thread_context="",
        )
        == "No useful web results found."
    )
    chat.chat.assert_not_called()
