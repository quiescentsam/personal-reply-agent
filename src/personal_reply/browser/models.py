from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from personal_reply.rag.context import format_thread_message
from personal_reply.time_parse import hours_between, parse_flexible_timestamp


@dataclass(frozen=True)
class ThreadMessage:
    role: Literal["them", "me"]
    sender: str
    text: str
    time_label: str | None = None
    parsed_at: datetime | None = None


@dataclass(frozen=True)
class ThreadContext:
    platform: Literal["whatsapp", "gmail"]
    contact_or_subject: str
    messages: list[ThreadMessage]
    compose_selector: str | None = None

    def last_message(self) -> ThreadMessage:
        if not self.messages:
            raise ValueError("Thread has no messages.")
        return self.messages[-1]

    def latest_incoming_message(self) -> ThreadMessage | None:
        for message in reversed(self.messages):
            if message.role == "them" and message.text.strip():
                return message
        return None

    def latest_incoming_text(self) -> str:
        message = self.latest_incoming_message()
        if message is None:
            raise ValueError("No incoming message found in the active WhatsApp thread.")
        return message.text.strip()

    def hours_since_last_message(self, *, now: datetime | None = None) -> float | None:
        last = self.last_message()
        timestamp = last.parsed_at
        if timestamp is None and last.time_label:
            timestamp = parse_flexible_timestamp(last.time_label)
        if timestamp is None or timestamp == datetime.min:
            return None
        reference = now or datetime.now()
        return hours_between(timestamp, reference)

    def format_thread_context(self, *, max_messages: int = 8) -> str:
        recent = self.messages[-max_messages:]
        return "\n".join(
            format_thread_message(message.sender, message.text, time_label=message.time_label)
            for message in recent
            if message.text.strip()
        )
