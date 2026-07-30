from datetime import datetime

from personal_reply.rag.context import (
    build_conversation_window_from_entries,
    build_retrieval_query,
    format_chat_lines,
    format_timestamped_chat_line,
)


def test_format_timestamped_chat_line() -> None:
    line = format_timestamped_chat_line(datetime(2024, 12, 12, 7, 59), "Papa New", "Haan")
    assert line == "[12/12/24 07:59] Papa New: Haan"


def test_build_conversation_window_from_entries_includes_times() -> None:
    window = build_conversation_window_from_entries(
        [
            (datetime(2024, 12, 12, 7, 51), "Papa New", "Kahan ho"),
            (datetime(2024, 12, 12, 7, 59), "Sameer", "Neeche"),
            (datetime(2024, 12, 12, 8, 0), "Papa New", "Acha"),
        ]
    )

    assert "[12/12/24 07:51] Papa New: Kahan ho" in window
    assert "[12/12/24 07:59] Sameer: Neeche" in window
    assert "[12/12/24 08:00] Papa New: Acha" in window


def test_format_chat_lines() -> None:
    lines = format_chat_lines([(datetime(2024, 12, 12, 7, 59), "Sameer", "Haan")])
    assert lines == "[12/12/24 07:59] Sameer: Haan"


def test_build_retrieval_query_includes_thread_context() -> None:
    query = build_retrieval_query(
        "Kahan ho?",
        thread_context="[12/12/24 07:51] Papa New: Aa jao",
    )

    assert "[12/12/24 07:51] Papa New: Aa jao" in query
    assert "Incoming: Kahan ho?" in query
