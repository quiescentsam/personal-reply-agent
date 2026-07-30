from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from personal_reply.rag.contacts import friendly_contact_name, normalize_contact

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass(frozen=True)
class ContactAttributes:
    """Maps contact names to shared style tags (parent, family, friend, etc.)."""

    _tags_by_normalized_key: dict[str, frozenset[str]]

    @classmethod
    def empty(cls) -> ContactAttributes:
        return cls(_tags_by_normalized_key={})

    @classmethod
    def from_config(cls, config_path: Path) -> ContactAttributes:
        with config_path.open("rb") as handle:
            raw = tomllib.load(handle)
        tags_section = raw.get("contacts", {}).get("tags", {})
        tags_by_key: dict[str, frozenset[str]] = {}
        for key, value in tags_section.items():
            if isinstance(value, list):
                tags = frozenset(str(item).casefold() for item in value if str(item).strip())
            else:
                continue
            if tags:
                tags_by_key[normalize_contact(str(key))] = tags
        return cls(_tags_by_normalized_key=tags_by_key)

    def tags_for_contact(self, contact: str) -> frozenset[str]:
        if not contact:
            return frozenset()
        keys = (
            normalize_contact(contact),
            normalize_contact(friendly_contact_name(contact)),
        )
        for key in keys:
            if key in self._tags_by_normalized_key:
                return self._tags_by_normalized_key[key]
        return frozenset()

    def display_tags_for_contact(self, contact: str) -> tuple[str, ...]:
        return tuple(sorted(self.tags_for_contact(contact)))

    def indexed_peers_for_tags(self, contact: str, known_contacts: list[str]) -> set[str]:
        """Indexed contacts that share at least one configured tag with `contact`."""
        tags = self.tags_for_contact(contact)
        if not tags:
            return set()
        return {
            known
            for known in known_contacts
            if self.tags_for_contact(known) & tags
        }

    def peer_contacts(self, contact: str, known_contacts: list[str]) -> set[str]:
        tags = self.tags_for_contact(contact)
        if not tags:
            return {contact}
        peers = self.indexed_peers_for_tags(contact, known_contacts)
        if contact in known_contacts:
            peers.add(contact)
            return peers
        if peers:
            return peers
        return {contact}

    def resolve_config_key(self, contact: str) -> str | None:
        tags = self.tags_for_contact(contact)
        if not tags:
            return None
        for key, key_tags in self._tags_by_normalized_key.items():
            if key_tags == tags:
                return key
        return None
