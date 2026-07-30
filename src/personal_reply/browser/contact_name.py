from __future__ import annotations

import re

_STATUS_PATTERNS = (
    re.compile(r"last seen", re.I),
    re.compile(r"\bonline\b", re.I),
    re.compile(r"\btyping\b", re.I),
    re.compile(r"\brecording\b", re.I),
    re.compile(r"^today at \d", re.I),
    re.compile(r"^yesterday at \d", re.I),
)


def is_status_text(value: str) -> bool:
    text = value.strip()
    if not text:
        return True
    return any(pattern.search(text) for pattern in _STATUS_PATTERNS)


def infer_contact_from_messages(
    raw_messages: list[dict[str, str]],
    *,
    sender_names: tuple[str, ...],
) -> str | None:
    """Guess contact from incoming message senders when header parsing fails."""
    names = {name.casefold() for name in sender_names}
    counts: dict[str, int] = {}
    for item in raw_messages:
        sender = item.get("sender", "").strip()
        if not sender or sender.casefold() in names or sender == "me":
            continue
        if is_status_text(sender):
            continue
        counts[sender] = counts.get(sender, 0) + 1
    if not counts:
        return None
    return max(counts, key=counts.get)


def resolve_contact_name(
    contact: str,
    raw_messages: list[dict[str, str]],
    *,
    sender_names: tuple[str, ...],
) -> str:
    cleaned = contact.strip()
    if cleaned and not is_status_text(cleaned):
        return cleaned

    inferred = infer_contact_from_messages(raw_messages, sender_names=sender_names)
    if inferred:
        return inferred

    if cleaned:
        raise ValueError(
            f"Could not read WhatsApp contact name (got status text: '{cleaned}'). "
            "Make sure a chat is open and the header is visible."
        )
    raise ValueError("WhatsApp contact name is empty.")
