from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from personal_reply.rag.embed import OllamaEmbedder
from personal_reply.rag.scoring import (
    blend_relevance_score,
    format_conversation_timestamp,
    parse_row_timestamp,
    recency_score,
)
from personal_reply.rag.store import MessageStore


def _sql_literal(value: str) -> str:
    return value.replace("'", "''")


@dataclass(frozen=True)
class RetrievedMessage:
    id: str
    platform: str
    contact: str
    text: str
    context_before: str
    context_after: str
    conversation_window: str
    timestamp: datetime
    vector_score: float
    recency_score: float
    score: float
    message_kind: str = "reply"
    affinity_weight: float = 1.0

    @property
    def formatted_timestamp(self) -> str:
        return format_conversation_timestamp(self.timestamp)


class StyleRetriever:
    def __init__(self, store: MessageStore, embedder: OllamaEmbedder) -> None:
        self._store = store
        self._embedder = embedder

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 8,
        platform: str | None = "whatsapp",
        contact: str | None = None,
        peer_contacts: set[str] | None = None,
        contact_match_weight: float = 1.0,
        category_match_weight: float = 0.65,
        candidate_multiplier: int = 5,
        vector_weight: float = 0.7,
        recency_weight: float = 0.3,
        recency_half_life_days: float = 180.0,
        message_kind: str | None = None,
        now: datetime | None = None,
    ) -> list[RetrievedMessage]:
        if not self._store.has_table():
            return []

        candidate_k = max(top_k, top_k * candidate_multiplier)
        vector = self._embedder.embed(query)
        search = self._store.open_table().search(vector).limit(candidate_k)
        filters: list[str] = []
        if platform:
            filters.append(f"platform = '{_sql_literal(platform)}'")

        search_contacts = self._search_contacts(contact, peer_contacts)
        if search_contacts:
            if len(search_contacts) == 1:
                only = next(iter(search_contacts))
                filters.append(f"contact = '{_sql_literal(only)}'")
            else:
                quoted = ", ".join(f"'{_sql_literal(name)}'" for name in sorted(search_contacts))
                filters.append(f"contact IN ({quoted})")

        if filters:
            search = search.where(" AND ".join(filters))

        rows = search.to_list()
        if message_kind:
            rows = [row for row in rows if str(row.get("message_kind", "reply")) == message_kind]
        if not rows:
            return []

        ranked: list[RetrievedMessage] = []
        for row in rows:
            row_contact = str(row["contact"])
            affinity = self._affinity_weight(
                row_contact=row_contact,
                contact=contact,
                peer_contacts=peer_contacts,
                contact_match_weight=contact_match_weight,
                category_match_weight=category_match_weight,
            )
            if affinity <= 0:
                continue

            distance = float(row.get("_distance", 0.0))
            vector_score = 1.0 - distance
            timestamp = parse_row_timestamp(row.get("timestamp"))
            recency = recency_score(
                timestamp,
                now=now,
                half_life_days=recency_half_life_days,
            )
            base_score = blend_relevance_score(
                vector_score,
                recency,
                vector_weight=vector_weight,
                recency_weight=recency_weight,
            )
            ranked.append(
                RetrievedMessage(
                    id=str(row["id"]),
                    platform=str(row["platform"]),
                    contact=row_contact,
                    text=str(row["text"]),
                    context_before=str(row.get("context_before", "")),
                    context_after=str(row.get("context_after", "")),
                    conversation_window=str(row.get("conversation_window", "")),
                    timestamp=timestamp,
                    message_kind=str(row.get("message_kind", "reply")),
                    vector_score=vector_score,
                    recency_score=recency,
                    affinity_weight=affinity,
                    score=base_score * affinity,
                )
            )

        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:top_k]

    @staticmethod
    def _search_contacts(
        contact: str | None,
        peer_contacts: set[str] | None,
    ) -> set[str] | None:
        if peer_contacts:
            return set(peer_contacts)
        if contact:
            return {contact}
        return None

    @staticmethod
    def _affinity_weight(
        *,
        row_contact: str,
        contact: str | None,
        peer_contacts: set[str] | None,
        contact_match_weight: float,
        category_match_weight: float,
    ) -> float:
        if not contact:
            if peer_contacts and row_contact in peer_contacts:
                return category_match_weight
            return 1.0 if not peer_contacts else 0.0
        if row_contact == contact:
            return contact_match_weight
        if peer_contacts and row_contact in peer_contacts:
            return category_match_weight
        return 0.0
