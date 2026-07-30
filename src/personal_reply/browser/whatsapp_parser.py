from __future__ import annotations

from datetime import datetime
from typing import Literal

from personal_reply.browser.models import ThreadContext, ThreadMessage
from personal_reply.time_parse import parse_flexible_timestamp


def normalize_sender_names(sender_names: tuple[str, ...]) -> set[str]:
    return {name.casefold() for name in sender_names}


def classify_role(sender: str, sender_names: set[str]) -> Literal["them", "me"]:
    if sender.casefold() in sender_names:
        return "me"
    return "them"


def build_thread_context(
    *,
    contact: str,
    raw_messages: list[dict[str, str]],
    sender_names: tuple[str, ...],
    compose_selector: str | None,
) -> ThreadContext:
    names = normalize_sender_names(sender_names)
    messages: list[ThreadMessage] = []
    for item in raw_messages:
        sender = item.get("sender", "").strip()
        text = item.get("text", "").strip()
        if not sender and not text:
            continue
        role = classify_role(sender, names)
        time_label = (item.get("time") or "").strip() or None
        parsed_at = parse_flexible_timestamp(time_label) if time_label else None
        if parsed_at == datetime.min:
            parsed_at = None
        messages.append(
            ThreadMessage(
                role=role,
                sender=sender or "Unknown",
                text=text,
                time_label=time_label,
                parsed_at=parsed_at,
            )
        )

    if not contact.strip():
        raise ValueError("WhatsApp contact name is empty.")
    if not messages:
        raise ValueError("No messages found in WhatsApp thread.")

    return ThreadContext(
        platform="whatsapp",
        contact_or_subject=contact.strip(),
        messages=messages,
        compose_selector=compose_selector,
    )
