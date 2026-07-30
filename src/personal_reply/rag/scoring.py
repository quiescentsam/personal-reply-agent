from __future__ import annotations

import math
from datetime import datetime


def parse_row_timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if value is None:
        return datetime.min
    if isinstance(value, str) and value.strip():
        normalized = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return datetime.min
    return datetime.min


def format_conversation_timestamp(timestamp: datetime) -> str:
    if timestamp == datetime.min:
        return "unknown"
    return timestamp.strftime("%d/%m/%y %H:%M")


def recency_score(
    timestamp: datetime,
    *,
    now: datetime | None = None,
    half_life_days: float = 180.0,
) -> float:
    if timestamp == datetime.min:
        return 0.0

    reference = now or datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
    age_days = max((reference - timestamp).total_seconds() / 86_400.0, 0.0)
    return math.exp(-age_days / half_life_days)


def blend_relevance_score(
    vector_score: float,
    recency: float,
    *,
    vector_weight: float,
    recency_weight: float,
) -> float:
    total_weight = vector_weight + recency_weight
    if total_weight <= 0:
        return vector_score
    return (vector_weight * vector_score + recency_weight * recency) / total_weight
