from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from personal_reply.rag.retrieve import RetrievedMessage

ConversationMode = Literal["respond", "reopen"]


@dataclass(frozen=True)
class SuggestResult:
    suggestion: str
    examples: list[RetrievedMessage]
    messages: list[dict[str, str]]
    contact_label: str | None = None
    stored_contact: str | None = None
    mode: ConversationMode = "respond"
    mode_reason: str | None = None
    hours_since_last: float | None = None
    research_queries: tuple[str, ...] = ()
    research_summary: str | None = None


def format_verbose(result: SuggestResult) -> str:
    lines = ["=== Conversation mode ==="]
    lines.append(f"mode: {result.mode}")
    if result.mode_reason:
        lines.append(f"reason: {result.mode_reason}")
    if result.hours_since_last is not None:
        lines.append(f"hours_since_last: {result.hours_since_last:.1f}")

    if result.research_summary:
        lines.append("")
        lines.append("=== Web research subagent ===")
        if result.research_queries:
            lines.append(f"queries: {', '.join(result.research_queries)}")
        lines.append(result.research_summary)

    lines.append("")
    lines.append("=== RAG retrieval ===")
    if not result.examples:
        lines.append("(no examples retrieved)")
    else:
        for index, example in enumerate(result.examples, start=1):
            lines.append(
                f"[{index}] score={example.score:.4f} "
                f"(vector={example.vector_score:.4f}, recency={example.recency_score:.4f}, "
                f"affinity={example.affinity_weight:.2f})"
            )
            lines.append(f"  date: {example.formatted_timestamp}")
            lines.append(f"  contact: {example.contact}")
            lines.append(f"  your_reply: {example.text}")
            if example.conversation_window:
                lines.append("  conversation_window:")
                for window_line in example.conversation_window.splitlines():
                    lines.append(f"    {window_line}")
            else:
                if example.context_before:
                    lines.append(f"  context_before: {example.context_before}")
                if example.context_after:
                    lines.append(f"  context_after: {example.context_after}")

    lines.append("")
    lines.append("=== Prompt to chat agent ===")
    if result.contact_label:
        lines.append(f"contact: {result.contact_label}")
        if result.stored_contact and result.stored_contact != result.contact_label:
            lines.append(f"stored_contact: {result.stored_contact}")
        if result.stored_contact is None and result.contact_label:
            lines.append("retrieval: tag peers only (contact not ingested)")
    lines.append(f"messages: {len(result.messages)}")

    for index, message in enumerate(result.messages, start=1):
        lines.append("")
        lines.append(f"--- message {index}: {message['role']} ---")
        lines.append(message["content"])

    lines.append("")
    lines.append("=== Suggestion ===")
    return "\n".join(lines)
