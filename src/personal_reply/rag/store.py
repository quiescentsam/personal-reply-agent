from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import lancedb
import pyarrow as pa

TABLE_NAME = "messages"


@dataclass(frozen=True)
class StoredMessage:
    id: str
    platform: str
    contact: str
    text: str
    context_before: str
    context_after: str
    conversation_window: str
    timestamp: datetime
    vector: list[float]
    message_kind: str = "reply"


def _to_rows(records: list[StoredMessage]) -> list[dict[str, Any]]:
    return [
        {
            "id": record.id,
            "platform": record.platform,
            "contact": record.contact,
            "text": record.text,
            "context_before": record.context_before,
            "context_after": record.context_after,
            "conversation_window": record.conversation_window,
            "timestamp": record.timestamp,
            "vector": record.vector,
            "message_kind": record.message_kind,
        }
        for record in records
    ]


class MessageStore:
    def __init__(self, uri: Path) -> None:
        self._uri = uri
        self._uri.parent.mkdir(parents=True, exist_ok=True)
        self._db = lancedb.connect(str(uri))

    @property
    def table_names(self) -> list[str]:
        return self._db.table_names()

    def has_table(self) -> bool:
        return TABLE_NAME in self.table_names

    def open_table(self):
        return self._db.open_table(TABLE_NAME)

    def upsert(self, records: list[StoredMessage], *, mode: str = "overwrite") -> int:
        if not records:
            return 0

        rows = _to_rows(records)
        if not self.has_table():
            self._db.create_table(TABLE_NAME, data=rows, mode=mode)
            return len(rows)

        table = self.open_table()
        if mode == "overwrite":
            self._db.create_table(TABLE_NAME, data=rows, mode="overwrite")
            return len(rows)

        table.add(rows)
        return len(rows)

    def count(self, *, platform: str | None = None) -> int:
        if not self.has_table():
            return 0
        table = self.open_table()
        if platform:
            return table.count_rows(filter=f"platform = '{platform}'")
        return table.count_rows()

    def schema_vector_dim(self) -> int | None:
        if not self.has_table():
            return None
        table = self.open_table()
        field = table.schema.field("vector")
        if not isinstance(field.type, pa.FixedSizeListType):
            return None
        return field.type.list_size
