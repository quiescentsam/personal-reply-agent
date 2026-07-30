from personal_reply.browser.contact_name import (
    infer_contact_from_messages,
    is_status_text,
    resolve_contact_name,
)


def test_is_status_text_detects_last_seen() -> None:
    assert is_status_text("last seen today at 13:52")
    assert not is_status_text("Papa New")


def test_infer_contact_from_messages() -> None:
    contact = infer_contact_from_messages(
        [
            {"sender": "Papa New", "text": "Kahan ho"},
            {"sender": "Sameer", "text": "Neeche"},
            {"sender": "Papa New", "text": "Acha"},
        ],
        sender_names=("Sameer",),
    )
    assert contact == "Papa New"


def test_resolve_contact_falls_back_to_message_senders() -> None:
    contact = resolve_contact_name(
        "last seen today at 13:52",
        [
            {"sender": "Tridib Das", "text": "Hello"},
            {"sender": "Sameer", "text": "Hi"},
        ],
        sender_names=("Sameer",),
    )
    assert contact == "Tridib Das"
