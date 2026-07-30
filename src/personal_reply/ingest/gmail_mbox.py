from __future__ import annotations

from pathlib import Path

from personal_reply.ingest.whatsapp_txt import ParsedMessage


def parse_gmail_mbox(
    path: Path,
    *,
    user_emails: tuple[str, ...] = (),
) -> list[ParsedMessage]:
    """Phase 5 stub — Gmail mbox ingest is not implemented yet."""
    raise NotImplementedError(
        "Gmail mbox ingest is planned for Phase 5. "
        f"Received path: {path}, user_emails: {user_emails}"
    )
