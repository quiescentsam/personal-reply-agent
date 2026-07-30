from __future__ import annotations

from dataclasses import dataclass

from personal_reply.rag.contact_attributes import ContactAttributes
from personal_reply.rag.contacts import (
    AmbiguousContactError,
    ContactNotFoundError,
    friendly_contact_name,
    resolve_contact,
)


@dataclass(frozen=True)
class ContactResolution:
    query: str
    stored_contact: str | None
    contact_label: str
    peer_contacts: set[str]
    tag_peers_only: bool


def resolve_for_retrieval(
    query: str,
    known_contacts: list[str],
    attributes: ContactAttributes,
) -> ContactResolution:
    """Resolve an active chat to indexed contacts, using tag peers when not ingested."""
    if not query.strip():
        raise ContactNotFoundError("Contact name is required.")
    if not known_contacts:
        raise ContactNotFoundError("No contacts are indexed yet. Run ingest first.")

    try:
        stored_contact = resolve_contact(query, known_contacts)
    except AmbiguousContactError:
        raise
    except ContactNotFoundError:
        tag_peers = attributes.indexed_peers_for_tags(query, known_contacts)
        if not tag_peers:
            tags = attributes.display_tags_for_contact(query)
            if tags:
                tag_list = ", ".join(tags)
                known = ", ".join(friendly_contact_name(name) for name in known_contacts)
                raise ContactNotFoundError(
                    f"'{query}' is not ingested (tags: {tag_list}) and no indexed contact "
                    f"shares those tags. Known contacts: {known}. "
                    "Ingest a chat export for this contact or add overlapping tags to an indexed contact."
                )
            raise

        return ContactResolution(
            query=query.strip(),
            stored_contact=None,
            contact_label=friendly_contact_name(query.strip()),
            peer_contacts=tag_peers,
            tag_peers_only=True,
        )

    peer_contacts = attributes.peer_contacts(stored_contact, known_contacts)
    return ContactResolution(
        query=query.strip(),
        stored_contact=stored_contact,
        contact_label=friendly_contact_name(stored_contact),
        peer_contacts=peer_contacts,
        tag_peers_only=False,
    )
