from __future__ import annotations

from personal_reply.rag.contacts import friendly_contact_name
from personal_reply.rag.store import MessageStore


def list_contacts(store: MessageStore, *, platform: str | None = "whatsapp") -> list[tuple[str, int]]:
    if not store.has_table():
        return []

    table = store.open_table()
    rows = table.search().limit(100_000).to_list()
    counts: dict[str, int] = {}
    for row in rows:
        if platform and row.get("platform") != platform:
            continue
        contact = str(row["contact"])
        counts[contact] = counts.get(contact, 0) + 1

    return sorted(counts.items(), key=lambda item: friendly_contact_name(item[0]).casefold())


def list_contact_names(store: MessageStore, *, platform: str | None = "whatsapp") -> list[str]:
    return [contact for contact, _count in list_contacts(store, platform=platform)]
