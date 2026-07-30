from personal_reply.browser.models import ThreadContext, ThreadMessage
from personal_reply.browser.whatsapp_parser import build_thread_context


def test_format_thread_context_includes_message_times() -> None:
    thread = ThreadContext(
        platform="whatsapp",
        contact_or_subject="Papa New",
        messages=[
            ThreadMessage(role="them", sender="Papa New", text="Kahan ho", time_label="9/7/26, 13:52"),
            ThreadMessage(role="me", sender="Sameer", text="Neeche", time_label="9/7/26, 13:53"),
        ],
        compose_selector=None,
    )

    context = thread.format_thread_context()
    assert "[9/7/26, 13:52] Papa New: Kahan ho" in context
    assert "[9/7/26, 13:53] Sameer: Neeche" in context
