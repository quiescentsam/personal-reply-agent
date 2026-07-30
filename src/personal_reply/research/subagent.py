from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from personal_reply.config import Config
from personal_reply.llm.ollama_client import OllamaChatClient
from personal_reply.research.search import SearchResult, search_web

logger = logging.getLogger(__name__)

_MAX_QUERY_LEN = 120


@dataclass(frozen=True)
class ResearchBrief:
    queries: tuple[str, ...]
    snippets: tuple[str, ...]
    summary: str


def _parse_queries(raw: str, *, max_queries: int) -> list[str]:
    queries: list[str] = []
    for line in raw.splitlines():
        cleaned = re.sub(r"^\s*\d+[\).\]]\s*", "", line.strip())
        cleaned = cleaned.strip("-•* ")
        if not cleaned or len(cleaned) < 4:
            continue
        if cleaned.casefold().startswith("query"):
            continue
        queries.append(cleaned[:_MAX_QUERY_LEN])
        if len(queries) >= max_queries:
            break
    return queries


def _default_queries(contact: str | None) -> list[str]:
    from datetime import datetime

    today = datetime.now().strftime("%B %d %Y")
    location = "India"
    queries = [
        f"weather forecast {location} {today}",
        "cricket sports news today",
    ]
    if contact:
        queries.append(f"conversation topics with {contact}")
    return queries[:2]


def should_invoke_research(
    chat: OllamaChatClient,
    *,
    mode: str,
    contact: str | None,
    incoming_text: str | None,
    thread_context: str,
    reopen_context: str | None,
    hours_since_last: float | None,
) -> bool:
    situation = reopen_context or thread_context or incoming_text or "No thread context."
    hours_text = (
        f"{hours_since_last:.1f}" if hours_since_last is not None else "unknown"
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You decide if a quick web search would help draft a WhatsApp message. "
                "Say YES when timely outside info would help: stale threads needing a fresh topic, "
                "small-talk openers, weather, sports, news, or hobbies mentioned or implied. "
                "Say NO for simple replies (ok, thanks, on my way), logistics, emotional support, "
                "or when a direct personal answer from context is enough. "
                "Reply with one word only: YES or NO."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Mode: {mode}\n"
                f"Contact: {contact or 'unknown'}\n"
                f"Hours since last message: {hours_text}\n"
                f"Incoming: {incoming_text or '(none)'}\n"
                f"Thread:\n{situation[:2000]}"
            ),
        },
    ]
    try:
        raw = chat.chat(messages).strip().casefold()
        return raw.startswith("yes") or raw == "y"
    except Exception as exc:
        logger.warning("Research decision failed: %s", exc)
        return mode == "reopen"


def plan_search_queries(
    chat: OllamaChatClient,
    *,
    thread_context: str,
    contact: str | None,
    mode: str,
    incoming_text: str | None,
    reopen_context: str | None,
    max_queries: int,
) -> list[str]:
    situation = reopen_context or thread_context or incoming_text or "No thread context."
    messages = [
        {
            "role": "system",
            "content": (
                "You plan short web search queries to help restart or continue a WhatsApp chat. "
                "Focus on timely topics: weather, sports, news, or hobbies implied by the thread. "
                f"Return exactly {max_queries} lines. Each line is one search query only. No numbering prose."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Mode: {mode}\n"
                f"Contact: {contact or 'unknown'}\n"
                f"Incoming message: {incoming_text or '(none — conversation starter)'}\n"
                f"Thread / situation:\n{situation}"
            ),
        },
    ]
    try:
        raw = chat.chat(messages)
        queries = _parse_queries(raw, max_queries=max_queries)
        if queries:
            return queries
    except Exception as exc:
        logger.warning("Query planning failed: %s", exc)
    return _default_queries(contact)[:max_queries]


def summarize_research(
    chat: OllamaChatClient,
    *,
    contact: str | None,
    mode: str,
    queries: list[str],
    results: list[SearchResult],
    thread_context: str,
) -> str:
    if not results:
        return "No useful web results found."

    lines = []
    for index, item in enumerate(results, start=1):
        lines.append(f"{index}. {item.title}: {item.snippet} ({item.url})")
    evidence = "\n".join(lines)

    messages = [
        {
            "role": "system",
            "content": (
                "Summarize web search results into 2-4 short talking points for a WhatsApp message. "
                "Be factual, concise, and conversational. No links. No mention of searching the web."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Mode: {mode}\n"
                f"Contact: {contact or 'unknown'}\n"
                f"Thread context:\n{thread_context or '(none)'}\n\n"
                f"Search queries: {', '.join(queries)}\n\n"
                f"Results:\n{evidence}\n\n"
                "Write brief talking points only."
            ),
        },
    ]
    return chat.chat(messages)


def run_research_subagent(
    chat: OllamaChatClient,
    *,
    config: Config,
    thread_context: str,
    contact: str | None,
    mode: str,
    incoming_text: str | None = None,
    reopen_context: str | None = None,
) -> ResearchBrief | None:
    if not config.research_enabled:
        return None

    queries = plan_search_queries(
        chat,
        thread_context=thread_context,
        contact=contact,
        mode=mode,
        incoming_text=incoming_text,
        reopen_context=reopen_context,
        max_queries=config.research_max_queries,
    )

    collected: list[SearchResult] = []
    snippets: list[str] = []
    for query in queries:
        hits = search_web(query, max_results=config.research_max_results_per_query)
        for hit in hits:
            collected.append(hit)
            label = f"{hit.title}: {hit.snippet}".strip(": ")
            if label:
                snippets.append(label)

    summary = summarize_research(
        chat,
        contact=contact,
        mode=mode,
        queries=queries,
        results=collected,
        thread_context=thread_context or reopen_context or "",
    )
    return ResearchBrief(
        queries=tuple(queries),
        snippets=tuple(snippets[:12]),
        summary=summary.strip(),
    )
