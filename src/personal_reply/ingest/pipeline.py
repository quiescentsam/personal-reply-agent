from __future__ import annotations

import logging

from personal_reply.config import Config
from personal_reply.ingest.whatsapp_txt import parse_whatsapp_dir
from personal_reply.rag.embed import OllamaEmbedder
from personal_reply.rag.store import MessageStore, StoredMessage

logger = logging.getLogger(__name__)


def run_ingest(config: Config, *, mode: str = "overwrite") -> int:
    logger.info("Step 1/5: Scanning exports in %s", config.exports_dir)
    export_files = sorted(config.exports_dir.glob("*.txt"))
    if not export_files:
        raise FileNotFoundError(
            f"No WhatsApp .txt exports found in {config.exports_dir}. "
            "Export a chat and place the .txt file there."
        )
    logger.info("Found %d export file(s): %s", len(export_files), ", ".join(p.name for p in export_files))

    logger.info("Step 2/5: Parsing WhatsApp messages")
    parsed = parse_whatsapp_dir(
        config.exports_dir,
        sender_names=config.sender_names,
        context_messages_before=config.context_messages_before,
        context_messages_after=config.context_messages_after,
        stale_after_hours=config.stale_after_hours,
    )
    if not parsed:
        names = ", ".join(config.sender_names)
        files = ", ".join(path.name for path in export_files)
        raise ValueError(
            f"Found export file(s) ({files}) but no messages matched sender_names "
            f"({names}). Update [ingest].sender_names in config.toml to match how "
            "your name appears in the export."
        )

    contacts = sorted({message.contact for message in parsed})
    logger.info(
        "Parsed %d messages across %d chat(s): %s",
        len(parsed),
        len(contacts),
        ", ".join(contacts),
    )

    store = MessageStore(config.lancedb_uri)
    with OllamaEmbedder(config) as embedder:
        logger.info("Step 3/5: Checking Ollama")
        embedder.ensure_ready()

        total_batches = (len(parsed) + config.embed_batch_size - 1) // config.embed_batch_size
        logger.info(
            "Step 4/5: Embedding %d messages in %d batch(es) of %d",
            len(parsed),
            total_batches,
            config.embed_batch_size,
        )

        def on_batch(batch_index: int, batch_total: int, batch_count: int) -> None:
            logger.info(
                "Embedding batch %d/%d (%d messages)",
                batch_index,
                batch_total,
                batch_count,
            )

        vectors = embedder.embed_many(
            [message.conversation_window for message in parsed],
            batch_size=config.embed_batch_size,
            on_batch=on_batch,
        )

        logger.info("Step 5/5: Writing %d records to %s", len(parsed), config.lancedb_uri)
        records = [
            StoredMessage(
                id=message.id,
                platform=message.platform,
                contact=message.contact,
                text=message.text,
                context_before=message.context_before,
                context_after=message.context_after,
                conversation_window=message.conversation_window,
                timestamp=message.timestamp,
                message_kind=message.message_kind,
                vector=vector,
            )
            for message, vector in zip(parsed, vectors, strict=True)
        ]
        count = store.upsert(records, mode=mode)
        logger.info("Done: ingested %d messages into LanceDB", count)
        return count


def main() -> None:
    from personal_reply.config import load_config

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    config = load_config()
    count = run_ingest(config)
    print(f"Ingested {count} messages into {config.lancedb_uri}")


if __name__ == "__main__":
    main()
