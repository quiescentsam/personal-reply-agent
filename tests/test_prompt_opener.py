from personal_reply.reply.prompt import build_opener_messages


def test_build_opener_messages_uses_reopen_context() -> None:
    messages = build_opener_messages(
        user_name="Sam",
        reopen_context="Conversation is stale.\nLast message: you: See you",
        examples=[],
        contact="Papa New",
    )
    user_content = messages[1]["content"]
    assert "restart the conversation" in user_content.lower()
    assert "Conversation is stale" in user_content
    assert "Incoming message to reply to" not in user_content


def test_build_opener_messages_includes_research_context() -> None:
    messages = build_opener_messages(
        user_name="Sam",
        reopen_context="Conversation is stale.",
        examples=[],
        research_context="Cricket match tonight.",
    )
    user_content = messages[1]["content"]
    assert "Timely topics from web research" in user_content
    assert "Cricket match tonight" in user_content
