from datetime import datetime

from personal_reply.rag.retrieve import RetrievedMessage
from personal_reply.reply.verbose import SuggestResult, format_verbose


def test_format_verbose_includes_rag_and_prompt() -> None:
    result = SuggestResult(
        suggestion="Haan",
        examples=[
            RetrievedMessage(
                id="1",
                platform="whatsapp",
                contact="Papa New",
                text="Neeche",
                context_before="Papa New: Kahan ho",
                context_after="Papa New: Acha",
                conversation_window="Papa New: Kahan ho\nSameer: Neeche\nPapa New: Acha",
                timestamp=datetime(2024, 12, 12, 7, 59),
                vector_score=0.91,
                recency_score=0.55,
                score=0.80,
            )
        ],
        messages=[
            {"role": "system", "content": "You write replies as Sam."},
            {"role": "user", "content": "Incoming message to reply to:\nKahan ho?"},
        ],
        contact_label="Papa New",
        stored_contact="WhatsAppChatwithPapaNew",
    )

    output = format_verbose(result)

    assert "=== RAG retrieval ===" in output
    assert "score=0.8000 (vector=0.9100, recency=0.5500, affinity=1.00)" in output
    assert "date: 12/12/24 07:59" in output
    assert "Neeche" in output
    assert "conversation_window:" in output
    assert "=== Prompt to chat agent ===" in output
    assert "=== Suggestion ===" in output


def test_format_verbose_includes_research() -> None:
    result = SuggestResult(
        suggestion="How about the match tonight?",
        examples=[],
        messages=[],
        research_queries=("cricket news today", "weather Mumbai"),
        research_summary="India plays tonight. Rain expected tomorrow.",
    )

    output = format_verbose(result)

    assert "=== Web research subagent ===" in output
    assert "cricket news today" in output
    assert "India plays tonight" in output
