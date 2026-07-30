from __future__ import annotations

from datetime import datetime

from personal_reply.rag.scoring import format_conversation_timestamp

ChatLineEntry = tuple[datetime, str, str]


def format_chat_line(sender: str, text: str) -> str:
    return f"{sender}: {text}"


def format_timestamped_chat_line(timestamp: datetime, sender: str, text: str) -> str:
    label = format_conversation_timestamp(timestamp)
    if label == "unknown":
        return format_chat_line(sender, text)
    return f"[{label}] {sender}: {text}"


def format_chat_lines(entries: list[ChatLineEntry]) -> str:
    return "\n".join(
        format_timestamped_chat_line(timestamp, sender, text)
        for timestamp, sender, text in entries
        if text.strip()
    )


def build_conversation_window(
    *,
    context_before: str,
    sender: str,
    text: str,
    context_after: str,
) -> str:
    """Backward-compatible builder for plain-text context parts."""
    parts: list[str] = []
    if context_before:
        parts.append(context_before)
    parts.append(format_chat_line(sender, text))
    if context_after:
        parts.append(context_after)
    return "\n".join(parts)


def build_conversation_window_from_entries(entries: list[ChatLineEntry]) -> str:
    return format_chat_lines(entries)


def format_thread_message(
    sender: str,
    text: str,
    *,
    time_label: str | None = None,
) -> str:
    if time_label and time_label.strip():
        return f"[{time_label.strip()}] {sender}: {text}"
    return format_chat_line(sender, text)


def build_retrieval_query(incoming_text: str, thread_context: str | None = None) -> str:
    """Build the text we embed when searching for similar past conversations."""
    incoming = incoming_text.strip()
    if thread_context and thread_context.strip():
        return f"{thread_context.strip()}\nIncoming: {incoming}"
    return incoming


def build_reopen_retrieval_query(
    *,
    contact: str | None,
    reopen_context: str,
) -> str:
    label = contact or "contact"
    return f"Reopen conversation with {label} after a time gap.\n{reopen_context.strip()}"
