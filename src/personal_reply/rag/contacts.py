from __future__ import annotations

import re


def normalize_contact(name: str) -> str:
    return "".join(character for character in name.casefold() if character.isalnum())


def friendly_contact_name(contact: str) -> str:
    """Best-effort display name from export filename or stored contact."""
    label = contact
    for prefix in ("WhatsApp Chat with ", "WhatsAppChatwith", "WhatsAppChatWith"):
        if label.startswith(prefix):
            label = label[len(prefix) :]
            break
    if " " not in label:
        label = re.sub(r"([a-z])([A-Z])", r"\1 \2", label)
    return label.strip() or contact


class ContactNotFoundError(ValueError):
    """Raised when no indexed contact matches the requested name."""


class AmbiguousContactError(ValueError):
    """Raised when multiple indexed contacts match the requested name."""

    def __init__(self, query: str, matches: list[str]) -> None:
        self.query = query
        self.matches = matches
        options = ", ".join(matches)
        super().__init__(
            f"Contact '{query}' matches multiple chats: {options}. "
            "Pass a more specific --contact value."
        )


def resolve_contact(query: str, known_contacts: list[str]) -> str:
    """Map a user-provided contact name to the stored LanceDB contact value."""
    if not query:
        raise ContactNotFoundError("Contact name is required.")

    if not known_contacts:
        raise ContactNotFoundError("No contacts are indexed yet. Run ingest first.")

    exact = [contact for contact in known_contacts if contact.casefold() == query.casefold()]
    if len(exact) == 1:
        return exact[0]

    normalized_query = normalize_contact(query)
    normalized_matches = [
        contact
        for contact in known_contacts
        if normalized_query in normalize_contact(contact)
        or normalize_contact(contact) in normalized_query
    ]

    if len(normalized_matches) == 1:
        return normalized_matches[0]
    if len(normalized_matches) > 1:
        raise AmbiguousContactError(query, sorted(normalized_matches))

    options = ", ".join(friendly_contact_name(contact) for contact in known_contacts)
    raise ContactNotFoundError(
        f"No indexed contact matched '{query}'. Known contacts: {options}"
    )
