from datetime import datetime, timedelta

import pytest

from personal_reply.rag.scoring import (
    blend_relevance_score,
    format_conversation_timestamp,
    recency_score,
)


def test_recency_score_is_higher_for_newer_messages() -> None:
    now = datetime(2026, 7, 9, 12, 0)
    recent = recency_score(now - timedelta(days=1), now=now, half_life_days=180)
    older = recency_score(now - timedelta(days=365), now=now, half_life_days=180)

    assert recent > older
    assert 0.0 < older < recent <= 1.0


def test_blend_relevance_score_weights_vector_and_recency() -> None:
    blended = blend_relevance_score(
        0.8,
        0.4,
        vector_weight=0.7,
        recency_weight=0.3,
    )

    assert blended == pytest.approx(0.68)


def test_format_conversation_timestamp() -> None:
    assert format_conversation_timestamp(datetime(2024, 12, 12, 7, 59)) == "12/12/24 07:59"
