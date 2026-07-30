from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from personal_reply.browser.models import ThreadContext, ThreadMessage
from personal_reply.config import Config
from personal_reply.time_parse import hours_between

ConversationMode = Literal["respond", "reopen"]


@dataclass(frozen=True)
class ThreadAnalysis:
    mode: ConversationMode
    reason: str
    hours_since_last: float | None
    incoming_text: str | None
    reopen_context: str


def _format_message_summary(message: ThreadMessage) -> str:
    time_part = f" at {message.time_label}" if message.time_label else ""
    who = "you" if message.role == "me" else message.sender
    return f"{who}{time_part}: {message.text.strip()}"


def analyze_thread_state(
    thread: ThreadContext,
    config: Config,
    *,
    now: datetime | None = None,
    force_mode: ConversationMode | None = None,
) -> ThreadAnalysis:
    if force_mode is not None:
        return _build_forced_analysis(thread, force_mode)

    reference = now or datetime.now()
    last = thread.last_message()
    hours_since_last = thread.hours_since_last_message(now=reference)
    thread_context = thread.format_thread_context()
    latest_incoming = thread.latest_incoming_message()

    stale = (
        hours_since_last is not None
        and hours_since_last >= config.stale_after_hours
    )
    last_from_me = last.role == "me"

    if stale:
        return ThreadAnalysis(
            mode="reopen",
            reason=(
                f"Last activity was {hours_since_last:.1f}h ago "
                f"(threshold {config.stale_after_hours}h)."
            ),
            hours_since_last=hours_since_last,
            incoming_text=None,
            reopen_context=_build_reopen_context(
                thread,
                last=last,
                hours_since_last=hours_since_last,
                note="Conversation is stale; start a fresh topic instead of answering old messages.",
            ),
        )

    if config.reopen_when_last_from_me and last_from_me:
        return ThreadAnalysis(
            mode="reopen",
            reason="Your message was last; nothing new from them to reply to.",
            hours_since_last=hours_since_last,
            incoming_text=None,
            reopen_context=_build_reopen_context(
                thread,
                last=last,
                hours_since_last=hours_since_last,
                note="Follow up naturally with a new topic or check-in.",
            ),
        )

    if latest_incoming is None:
        return ThreadAnalysis(
            mode="reopen",
            reason="No incoming message from them in this thread.",
            hours_since_last=hours_since_last,
            incoming_text=None,
            reopen_context=_build_reopen_context(
                thread,
                last=last,
                hours_since_last=hours_since_last,
                note="Start the conversation with a natural opener.",
            ),
        )

    return ThreadAnalysis(
        mode="respond",
        reason="Recent thread with a message from them to answer.",
        hours_since_last=hours_since_last,
        incoming_text=latest_incoming.text.strip(),
        reopen_context="",
    )


def _build_reopen_context(
    thread: ThreadContext,
    *,
    last: ThreadMessage,
    hours_since_last: float | None,
    note: str,
) -> str:
    parts = [note]
    if hours_since_last is not None:
        parts.append(f"Last activity: {hours_since_last:.1f} hours ago.")
    parts.append(f"Last message: {_format_message_summary(last)}")
    recent = thread.format_thread_context(max_messages=6)
    if recent:
        parts.append("Recent thread:")
        parts.append(recent)
    return "\n".join(parts)


def _build_forced_analysis(thread: ThreadContext, mode: ConversationMode) -> ThreadAnalysis:
    last = thread.last_message()
    hours_since_last = thread.hours_since_last_message()
    latest_incoming = thread.latest_incoming_message()
    if mode == "respond":
        incoming = latest_incoming.text.strip() if latest_incoming else thread.last_message().text.strip()
        return ThreadAnalysis(
            mode="respond",
            reason="Forced reply mode.",
            hours_since_last=hours_since_last,
            incoming_text=incoming,
            reopen_context="",
        )
    return ThreadAnalysis(
        mode="reopen",
        reason="Forced reopen mode.",
        hours_since_last=hours_since_last,
        incoming_text=None,
        reopen_context=_build_reopen_context(
            thread,
            last=last,
            hours_since_last=hours_since_last,
            note="Write a fresh opener.",
        ),
    )
