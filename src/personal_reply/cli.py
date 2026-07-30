from __future__ import annotations

import argparse
import logging
import sys

from personal_reply.browser.errors import (
    BrowserConnectionError,
    WhatsAppComposeError,
    WhatsAppTabNotFoundError,
    WhatsAppThreadReadError,
)
from personal_reply.config import load_config
from personal_reply.ingest.pipeline import run_ingest
from personal_reply.rag.contact_list import list_contacts
from personal_reply.rag.contacts import AmbiguousContactError, ContactNotFoundError, friendly_contact_name
from personal_reply.rag.errors import OllamaModelError, OllamaUnavailableError
from personal_reply.rag.store import MessageStore
from personal_reply.reply.generate import ReplyGenerator
from personal_reply.reply.verbose import SuggestResult, format_verbose


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="personal-reply",
        description="Local RAG agent that suggests replies in your voice.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Ingest WhatsApp exports into LanceDB")
    ingest_parser.add_argument(
        "--mode",
        choices=["overwrite", "append"],
        default="overwrite",
        help="How to write into the LanceDB table",
    )
    ingest_parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Hide step-by-step ingest logs",
    )

    suggest_parser = subparsers.add_parser("suggest", help="Suggest a reply for incoming text")
    suggest_parser.add_argument(
        "--from-browser",
        action="store_true",
        help="Read the active WhatsApp Web tab from Chrome instead of --text/--contact",
    )
    suggest_parser.add_argument(
        "--text",
        default=None,
        help="Incoming message text to reply to",
    )
    suggest_parser.add_argument(
        "--contact",
        default=None,
        help="Who you are chatting with (used to filter style examples)",
    )
    suggest_parser.add_argument(
        "--thread-context",
        default=None,
        help="Optional recent thread transcript",
    )
    suggest_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print RAG retrieval results and prompt sent to the chat model",
    )
    suggest_parser.add_argument(
        "--no-insert",
        action="store_true",
        help="With --from-browser, copy to clipboard only (do not type into compose)",
    )
    suggest_parser.add_argument(
        "--force-reply",
        action="store_true",
        help="With --from-browser, always reply to the latest message (skip reopen mode)",
    )
    suggest_parser.add_argument(
        "--force-reopen",
        action="store_true",
        help="With --from-browser, always draft a conversation opener",
    )
    suggest_parser.add_argument(
        "--research",
        action="store_true",
        help="Force web research before suggesting (default: main agent decides from conversation)",
    )

    subparsers.add_parser(
        "contacts",
        help="List contacts available for contact-aware suggestions",
    )

    return parser


def _print_suggest_result(result: str | SuggestResult) -> None:
    if isinstance(result, SuggestResult):
        print(format_verbose(result), file=sys.stderr)
        print(result.suggestion)
    else:
        print(result)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    config = load_config()

    if args.command == "ingest":
        logging.basicConfig(
            level=logging.WARNING if args.quiet else logging.INFO,
            format="%(levelname)s: %(message)s",
        )
        try:
            count = run_ingest(config, mode=args.mode)
        except (OllamaUnavailableError, OllamaModelError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(f"Ingested {count} messages into {config.lancedb_uri}")
        return 0

    if args.command == "suggest":
        if args.from_browser:
            if args.text or args.contact or args.thread_context:
                print(
                    "Warning: --text/--contact/--thread-context are ignored with --from-browser.",
                    file=sys.stderr,
                )
            if args.force_reply and args.force_reopen:
                parser.error("Use only one of --force-reply or --force-reopen.")
            force_mode = None
            if args.force_reply:
                force_mode = "respond"
            elif args.force_reopen:
                force_mode = "reopen"
            try:
                with ReplyGenerator(config) as generator:
                    result = generator.suggest_from_browser(
                        verbose=args.verbose,
                        insert_into_compose=not args.no_insert,
                        force_mode=force_mode,
                        research=args.research,
                    )
            except (
                BrowserConnectionError,
                WhatsAppTabNotFoundError,
                WhatsAppThreadReadError,
                WhatsAppComposeError,
                ContactNotFoundError,
                AmbiguousContactError,
            ) as exc:
                print(f"Error: {exc}", file=sys.stderr)
                return 1
            _print_suggest_result(result)
            return 0

        if not args.text or not args.contact:
            parser.error("--text and --contact are required unless --from-browser is set")

        try:
            with ReplyGenerator(config) as generator:
                result = generator.suggest(
                    args.text,
                    thread_context=args.thread_context,
                    contact=args.contact,
                    verbose=args.verbose,
                    research=args.research,
                )
        except (ContactNotFoundError, AmbiguousContactError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        _print_suggest_result(result)
        return 0

    if args.command == "contacts":
        store = MessageStore(config.lancedb_uri)
        rows = list_contacts(store, platform=config.platform)
        if not rows:
            print("No contacts indexed yet. Run ingest first.")
            return 1
        for stored_name, count in rows:
            tags = config.contact_attributes.display_tags_for_contact(stored_name)
            if not tags:
                tags = config.contact_attributes.display_tags_for_contact(
                    friendly_contact_name(stored_name)
                )
            tag_text = ", ".join(tags) if tags else "-"
            print(
                f"{friendly_contact_name(stored_name)}\t{count}\t{tag_text}\t({stored_name})"
            )
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
