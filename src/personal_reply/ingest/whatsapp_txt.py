from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from personal_reply.rag.context import (
    build_conversation_window_from_entries,
    format_chat_lines,
)
from personal_reply.time_parse import hours_between, parse_flexible_timestamp

# [1/15/24, 10:30:45 AM] Name: message
# 1/15/24, 10:30 - Name: message
_MESSAGE_LINE = re.compile(
    r"^(?:\[)?"
    r"(\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?)"
    r"(?:\])?\s*[-–]?\s*"
    r"([^:]+):\s"
    r"(.*)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedMessage:
    id: str
    platform: str
    contact: str
    text: str
    context_before: str
    context_after: str
    conversation_window: str
    timestamp: datetime
    message_kind: str = "reply"


@dataclass(frozen=True)
class _ChatLine:
    sender: str
    text: str
    timestamp: datetime
    contact: str


def _parse_timestamp(raw: str) -> datetime:
    return parse_flexible_timestamp(raw)


def _is_reopen_message(
    chat_lines: list[_ChatLine],
    index: int,
    *,
    stale_after_hours: float,
) -> bool:
    if index == 0:
        return True
    current = chat_lines[index]
    previous = chat_lines[index - 1]
    gap = hours_between(previous.timestamp, current.timestamp)
    if gap is None:
        return False
    return gap >= stale_after_hours


def _contact_from_filename(path: Path) -> str:
    stem = path.stem
    for prefix in ("WhatsApp Chat with ", "WhatsAppChatwith", "WhatsAppChatWith"):
        if stem.startswith(prefix):
            stem = stem[len(prefix) :]
            break
    if " " not in stem:
        stem = re.sub(r"([a-z])([A-Z])", r"\1 \2", stem)
    return stem.strip() or path.stem


def _stable_id(platform: str, contact: str, timestamp: datetime, text: str) -> str:
    key = f"{platform}:{contact}:{timestamp.isoformat()}:{text}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def parse_whatsapp_export(
    path: Path,
    *,
    sender_names: tuple[str, ...] = ("You",),
    context_messages_before: int = 3,
    context_messages_after: int = 2,
    stale_after_hours: float = 48.0,
) -> list[ParsedMessage]:
    """Parse a WhatsApp .txt export and return user messages with conversation context."""
    contact = _contact_from_filename(path)
    sender_set = {name.casefold() for name in sender_names}
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    parsed_rows: list[tuple[str, str, datetime, str]] = []
    current_sender = ""
    current_timestamp = datetime.min
    current_text: list[str] = []

    def flush() -> None:
        if not current_sender or not current_text:
            return
        parsed_rows.append(
            (
                current_sender,
                " ".join(current_text).strip(),
                current_timestamp,
                contact,
            )
        )

    for line in lines:
        match = _MESSAGE_LINE.match(line)
        if match:
            flush()
            timestamp_raw, sender, text = match.groups()
            current_sender = sender.strip()
            current_timestamp = _parse_timestamp(timestamp_raw)
            current_text = [text.strip()]
            continue

        if current_text and line.strip():
            current_text.append(line.strip())

    flush()

    chat_lines = [
        _ChatLine(sender=sender, text=text, timestamp=timestamp, contact=chat_contact)
        for sender, text, timestamp, chat_contact in parsed_rows
        if text
    ]

    outgoing: list[ParsedMessage] = []
    for index, line in enumerate(chat_lines):
        if line.sender.casefold() not in sender_set:
            continue

        before = chat_lines[max(0, index - context_messages_before) : index]
        after = chat_lines[index + 1 : index + 1 + context_messages_after]
        before_entries = [(item.timestamp, item.sender, item.text) for item in before]
        after_entries = [(item.timestamp, item.sender, item.text) for item in after]
        window_entries = before_entries + [(line.timestamp, line.sender, line.text)] + after_entries
        context_before = format_chat_lines(before_entries)
        context_after = format_chat_lines(after_entries)
        conversation_window = build_conversation_window_from_entries(window_entries)

        message_kind = "reopen" if _is_reopen_message(
            chat_lines,
            index,
            stale_after_hours=stale_after_hours,
        ) else "reply"

        outgoing.append(
            ParsedMessage(
                id=_stable_id("whatsapp", line.contact, line.timestamp, line.text),
                platform="whatsapp",
                contact=line.contact,
                text=line.text,
                context_before=context_before,
                context_after=context_after,
                conversation_window=conversation_window,
                timestamp=line.timestamp,
                message_kind=message_kind,
            )
        )

    return outgoing


def parse_whatsapp_dir(
    exports_dir: Path,
    *,
    sender_names: tuple[str, ...] = ("You",),
    context_messages_before: int = 3,
    context_messages_after: int = 2,
    stale_after_hours: float = 48.0,
) -> list[ParsedMessage]:
    messages: list[ParsedMessage] = []
    for path in sorted(exports_dir.glob("*.txt")):
        messages.extend(
            parse_whatsapp_export(
                path,
                sender_names=sender_names,
                context_messages_before=context_messages_before,
                context_messages_after=context_messages_after,
                stale_after_hours=stale_after_hours,
            )
        )
    return messages
