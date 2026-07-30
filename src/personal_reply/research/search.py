from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchResult:
    title: str
    snippet: str
    url: str


def search_web(query: str, *, max_results: int = 3) -> list[SearchResult]:
    query = query.strip()
    if not query:
        return []

    try:
        from ddgs import DDGS
    except ImportError as exc:
        raise RuntimeError(
            "Web search requires ddgs. Install with: pip install -e ."
        ) from exc

    results: list[SearchResult] = []
    try:
        for item in DDGS().text(query, max_results=max_results):
            if not item:
                continue
            title = str(item.get("title", "")).strip()
            snippet = str(item.get("body", "")).strip()
            url = str(item.get("href", "")).strip()
            if title or snippet:
                results.append(SearchResult(title=title, snippet=snippet, url=url))
    except Exception as exc:
        logger.warning("Web search failed for %r: %s", query, exc)
    return results
