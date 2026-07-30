from datetime import datetime

from personal_reply.rag.retrieve import RetrievedMessage
from personal_reply.reply.prompt import build_messages


def test_build_messages_includes_relevance_scores_and_date() -> None:
    messages = build_messages(
        user_name="Sam",
        incoming_text="Kahan ho?",
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
                vector_score=0.61,
                recency_score=0.52,
                score=0.58,
            )
        ],
        contact="Papa New",
    )

    user_content = messages[1]["content"]
    assert "Example 1 (relevance: 0.58, your reply: 12/12/24 07:59):" in user_content
    assert "Papa New: Kahan ho" in user_content


def test_build_messages_includes_research_context() -> None:
    messages = build_messages(
        user_name="Sam",
        incoming_text="Kahan ho?",
        examples=[],
        research_context="Rain expected tomorrow in Mumbai.",
    )
    user_content = messages[1]["content"]
    assert "Timely topics from web research" in user_content
    assert "Rain expected tomorrow" in user_content
