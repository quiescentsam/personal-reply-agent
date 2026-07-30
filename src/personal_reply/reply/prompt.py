from __future__ import annotations

from personal_reply.rag.retrieve import RetrievedMessage


def build_messages(
    *,
    user_name: str,
    incoming_text: str,
    examples: list[RetrievedMessage],
    thread_context: str | None = None,
    contact: str | None = None,
    research_context: str | None = None,
) -> list[dict[str, str]]:
    example_blocks: list[str] = []
    for index, example in enumerate(examples, start=1):
        block = [f"Example {index} (relevance: {example.score:.2f}, your reply: {example.formatted_timestamp}):"]
        if example.conversation_window:
            block.append("Conversation (each line is [date time] sender: message):")
            block.append(example.conversation_window)
        else:
            if example.context_before:
                block.append(f"Before:\n{example.context_before}")
            block.append(f"Your reply: {example.text}")
            if example.context_after:
                block.append(f"After:\n{example.context_after}")
        example_blocks.append("\n".join(block))

    examples_text = "\n\n".join(example_blocks) if example_blocks else "No examples available."

    system = (
        f"You write replies as {user_name}. "
        "Match the tone, length, punctuation, and formality of the examples. "
        "Do not mention AI, suggestions, or that you are drafting a message. "
        "Understand the incoming message and reply to it in a natural way. "
        "Be respectful and polite as normally done in a conversation. "
        "address the person by past examples and not contact name"
        "Return only the reply text. Keep the reply short and concise like examples"
    )
    if contact:
        system += f" You are replying to {contact}."

    user_parts = [
        "Here are examples of how you write" + (f" to {contact}" if contact else "") + ":",
        examples_text,
        "",
        "Incoming message to reply to:",
        incoming_text,
    ]
    if thread_context:
        user_parts.extend(["", "Recent thread context (with message times):", thread_context])
    if research_context:
        user_parts.extend(["", "Timely topics from web research (optional to use):", research_context])

    user_parts.append("")
    user_parts.append("Write one natural reply to the incoming message.")

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n".join(user_parts)},
    ]


def _format_examples(examples: list[RetrievedMessage], *, label: str) -> str:
    example_blocks: list[str] = []
    for index, example in enumerate(examples, start=1):
        block = [f"Example {index} (relevance: {example.score:.2f}, {label}: {example.formatted_timestamp}):"]
        if example.conversation_window:
            block.append("Conversation (each line is [date time] sender: message):")
            block.append(example.conversation_window)
        else:
            if example.context_before:
                block.append(f"Before:\n{example.context_before}")
            block.append(f"Your message: {example.text}")
            if example.context_after:
                block.append(f"After:\n{example.context_after}")
        example_blocks.append("\n".join(block))
    return "\n\n".join(example_blocks) if example_blocks else "No examples available."


def build_opener_messages(
    *,
    user_name: str,
    reopen_context: str,
    examples: list[RetrievedMessage],
    contact: str | None = None,
    research_context: str | None = None,
) -> list[dict[str, str]]:
    examples_text = _format_examples(examples, label="your opener")

    system = (
        f"You write messages as {user_name}. "
        "The conversation has gone quiet or is stale. "
        "Start a fresh, natural topic or friendly check-in in the same voice as the examples. "
        "Do not answer old messages or questions from the past. "
        "Do not mention AI, suggestions, or that you are drafting a message. "
        "Return only the message text. Keep it short and concise like the examples."
    )
    if contact:
        system += f" You are messaging {contact}."

    user_parts = [
        "Here are examples of how you restart conversations"
        + (f" with {contact}" if contact else "")
        + ":",
        examples_text,
        "",
        "Current situation:",
        reopen_context,
    ]
    if research_context:
        user_parts.extend(["", "Timely topics from web research (optional to use):", research_context])
    user_parts.extend([
        "",
        "Write one natural opener to restart the conversation.",
    ])

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n".join(user_parts)},
    ]
