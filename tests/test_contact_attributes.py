from personal_reply.rag.contact_attributes import ContactAttributes


def test_tags_for_contact_matches_friendly_and_stored_names() -> None:
    attrs = ContactAttributes(
        _tags_by_normalized_key={
            "papanew": frozenset({"parent", "family", "muslim"}),
        }
    )
    assert attrs.tags_for_contact("Papa New") == frozenset({"parent", "family", "muslim"})
    assert attrs.tags_for_contact("WhatsAppChatwithPapaNew") == frozenset(
        {"parent", "family", "muslim"}
    )


def test_peer_contacts_includes_shared_tag_contacts() -> None:
    attrs = ContactAttributes(
        _tags_by_normalized_key={
            "papanew": frozenset({"parent", "family"}),
            "mamanew": frozenset({"parent", "family"}),
            "tridibdas": frozenset({"friend"}),
        }
    )
    peers = attrs.peer_contacts(
        "WhatsAppChatwithPapaNew",
        ["WhatsAppChatwithPapaNew", "WhatsAppChatwithMamaNew", "WhatsAppChatwithTridibDas"],
    )
    assert peers == {"WhatsAppChatwithPapaNew", "WhatsAppChatwithMamaNew"}


def test_peer_contacts_without_tags_is_direct_only() -> None:
    attrs = ContactAttributes.empty()
    peers = attrs.peer_contacts("WhatsAppChatwithTridibDas", ["WhatsAppChatwithTridibDas"])
    assert peers == {"WhatsAppChatwithTridibDas"}


def test_peer_contacts_unindexed_with_tags_returns_indexed_peers_only() -> None:
    attrs = ContactAttributes(
        _tags_by_normalized_key={
            "papanew": frozenset({"parent", "family", "muslim"}),
            "amaanjio": frozenset({"family", "muslim"}),
        }
    )
    peers = attrs.peer_contacts(
        "Amaan Jio",
        ["WhatsAppChatwithPapaNew"],
    )
    assert peers == {"WhatsAppChatwithPapaNew"}
