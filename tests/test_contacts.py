import pytest

from personal_reply.rag.contacts import (
    AmbiguousContactError,
    ContactNotFoundError,
    friendly_contact_name,
    normalize_contact,
    resolve_contact,
)


def test_normalize_contact_strips_spaces_and_case() -> None:
    assert normalize_contact("Papa New") == "papanew"
    assert normalize_contact("WhatsAppChatwithPapaNew") == "whatsappchatwithpapanew"


def test_friendly_contact_name_from_export_filename() -> None:
    assert friendly_contact_name("WhatsAppChatwithPapaNew") == "Papa New"
    assert friendly_contact_name("WhatsApp Chat with Alex") == "Alex"


def test_resolve_contact_matches_partial_name() -> None:
    resolved = resolve_contact("Papa New", ["WhatsAppChatwithPapaNew"])
    assert resolved == "WhatsAppChatwithPapaNew"


def test_resolve_contact_is_case_insensitive() -> None:
    resolved = resolve_contact("papa new", ["WhatsAppChatwithPapaNew"])
    assert resolved == "WhatsAppChatwithPapaNew"


def test_resolve_contact_raises_when_missing() -> None:
    with pytest.raises(ContactNotFoundError, match="No indexed contact matched"):
        resolve_contact("Alex", ["WhatsAppChatwithPapaNew"])


def test_resolve_contact_raises_when_ambiguous() -> None:
    with pytest.raises(AmbiguousContactError):
        resolve_contact("Papa", ["Papa New", "Papa Old"])
