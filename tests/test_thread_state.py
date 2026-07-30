from datetime import datetime
from unittest.mock import MagicMock

from personal_reply.browser.models import ThreadContext, ThreadMessage
from personal_reply.reply.thread_state import analyze_thread_state


def _config(*, stale_after_hours: float = 48.0, reopen_when_last_from_me: bool = True):
    config = MagicMock()
    config.stale_after_hours = stale_after_hours
    config.reopen_when_last_from_me = reopen_when_last_from_me
    return config


def test_stale_thread_uses_reopen_mode() -> None:
    thread = ThreadContext(
        platform="whatsapp",
        contact_or_subject="Papa New",
        messages=[
            ThreadMessage(
                role="them",
                sender="Papa New",
                text="Are you coming?",
                time_label="1/1/26, 10:00",
                parsed_at=datetime(2026, 1, 1, 10, 0),
            ),
        ],
        compose_selector=None,
    )
    now = datetime(2026, 1, 5, 10, 0)
    analysis = analyze_thread_state(thread, _config(), now=now)
    assert analysis.mode == "reopen"
    assert analysis.incoming_text is None
    assert "96.0h" in analysis.reason or "96" in analysis.reason


def test_last_message_from_me_uses_reopen_mode() -> None:
    thread = ThreadContext(
        platform="whatsapp",
        contact_or_subject="Papa New",
        messages=[
            ThreadMessage(
                role="them",
                sender="Papa New",
                text="Ok",
                time_label="7/10/26, 09:00",
                parsed_at=datetime(2026, 7, 10, 9, 0),
            ),
            ThreadMessage(
                role="me",
                sender="Sameer",
                text="See you",
                time_label="7/10/26, 09:05",
                parsed_at=datetime(2026, 7, 10, 9, 5),
            ),
        ],
        compose_selector=None,
    )
    now = datetime(2026, 7, 10, 10, 0)
    analysis = analyze_thread_state(thread, _config(), now=now)
    assert analysis.mode == "reopen"
    assert "Your message was last" in analysis.reason


def test_fresh_incoming_message_uses_respond_mode() -> None:
    thread = ThreadContext(
        platform="whatsapp",
        contact_or_subject="Papa New",
        messages=[
            ThreadMessage(
                role="them",
                sender="Papa New",
                text="Kahan ho?",
                time_label="7/10/26, 09:55",
                parsed_at=datetime(2026, 7, 10, 9, 55),
            ),
        ],
        compose_selector=None,
    )
    now = datetime(2026, 7, 10, 10, 0)
    analysis = analyze_thread_state(thread, _config(), now=now)
    assert analysis.mode == "respond"
    assert analysis.incoming_text == "Kahan ho?"
