from personal_reply.browser.whatsapp_parser import build_thread_context


def test_build_thread_context_marks_user_messages_as_me() -> None:
    thread = build_thread_context(
        contact="Papa New",
        raw_messages=[
            {"sender": "Papa New", "text": "Kahan ho"},
            {"sender": "Sameer", "text": "Neeche"},
            {"sender": "Papa New", "text": "Acha"},
        ],
        sender_names=("Sameer",),
        compose_selector="footer div[contenteditable='true']",
    )

    assert thread.contact_or_subject == "Papa New"
    assert thread.messages[1].role == "me"
    assert thread.latest_incoming_text() == "Acha"
    assert "Papa New: Kahan ho" in thread.format_thread_context()


def test_latest_incoming_skips_empty_trailing_messages() -> None:
    thread = build_thread_context(
        contact="Alex",
        raw_messages=[
            {"sender": "Alex", "text": "Hello"},
            {"sender": "Sameer", "text": "Hi"},
            {"sender": "Alex", "text": ""},
        ],
        sender_names=("Sameer",),
        compose_selector=None,
    )

    assert thread.latest_incoming_text() == "Hello"
