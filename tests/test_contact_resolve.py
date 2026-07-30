import pytest

from personal_reply.rag.contact_attributes import ContactAttributes
from personal_reply.rag.contact_resolve import resolve_for_retrieval
from personal_reply.rag.contacts import ContactNotFoundError


def test_resolve_uses_tag_peers_when_contact_not_indexed() -> None:
    attrs = ContactAttributes(
        _tags_by_normalized_key={
            "papanew": frozenset({"parent", "family", "muslim"}),
            "amaanjio": frozenset({"family", "muslim"}),
        }
    )
    resolution = resolve_for_retrieval(
        "Amaan Jio",
        ["WhatsAppChatwithPapaNew"],
        attrs,
    )
    assert resolution.stored_contact is None
    assert resolution.contact_label == "Amaan Jio"
    assert resolution.peer_contacts == {"WhatsAppChatwithPapaNew"}
    assert resolution.tag_peers_only is True


def test_resolve_raises_when_no_indexed_tag_overlap() -> None:
    attrs = ContactAttributes(
        _tags_by_normalized_key={
            "amaanjio": frozenset({"family", "muslim"}),
        }
    )
    with pytest.raises(ContactNotFoundError, match="no indexed contact shares those tags"):
        resolve_for_retrieval("Amaan Jio", ["WhatsAppChatwithTridibDas"], attrs)
