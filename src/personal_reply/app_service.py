from __future__ import annotations

import logging
import sys

from personal_reply.browser.errors import (
    BrowserConnectionError,
    WhatsAppComposeError,
    WhatsAppTabNotFoundError,
    WhatsAppThreadReadError,
)
from personal_reply.clipboard import copy_to_clipboard
from personal_reply.config import Config, DEFAULT_CONFIG_PATH, load_config
from personal_reply.ingest.pipeline import run_ingest
from personal_reply.rag.contacts import AmbiguousContactError, ContactNotFoundError
from personal_reply.rag.errors import OllamaModelError, OllamaUnavailableError
from personal_reply.reply.generate import ReplyGenerator
from personal_reply.reply.verbose import SuggestResult, format_verbose

logger = logging.getLogger(__name__)


class SuggestError(Exception):
    """User-facing failure while generating a reply."""


class IngestError(Exception):
    """User-facing failure while re-ingesting exports."""


def _extract_suggestion(result: str | SuggestResult) -> tuple[str, str]:
    if isinstance(result, SuggestResult):
        return result.suggestion.strip(), result.mode
    return result.strip(), "respond"


def suggest_from_browser(
    config: Config | None = None,
    *,
    insert_into_compose: bool | None = None,
    verbose: bool = False,
    research: bool = False,
) -> tuple[str, str]:
    config = config or load_config()
    try:
        with ReplyGenerator(config) as generator:
            result = generator.suggest_from_browser(
                insert_into_compose=insert_into_compose,
                verbose=verbose,
                research=research,
            )
    except (
        BrowserConnectionError,
        WhatsAppTabNotFoundError,
        WhatsAppThreadReadError,
        WhatsAppComposeError,
        ContactNotFoundError,
        AmbiguousContactError,
        OllamaUnavailableError,
        OllamaModelError,
    ) as exc:
        raise SuggestError(str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected suggest failure")
        raise SuggestError(f"Unexpected error: {exc}") from exc

    suggestion, mode = _extract_suggestion(result)
    if not suggestion:
        raise SuggestError("Model returned an empty suggestion.")
    if verbose and isinstance(result, SuggestResult):
        print(format_verbose(result), file=sys.stderr)
        print(suggestion)
    return suggestion, mode


def suggest_and_copy(
    config: Config | None = None,
    *,
    insert_into_compose: bool | None = None,
    verbose: bool = False,
    research: bool = False,
) -> tuple[str, bool, str]:
    config = config or load_config()
    insert = config.insert_into_compose if insert_into_compose is None else insert_into_compose
    suggestion, mode = suggest_from_browser(
        config=config,
        insert_into_compose=insert,
        verbose=verbose,
        research=research,
    )
    copy_to_clipboard(suggestion)
    return suggestion, insert, mode


def reingest_exports(config: Config | None = None) -> int:
    config = config or load_config()
    try:
        return run_ingest(config)
    except (OllamaUnavailableError, OllamaModelError, FileNotFoundError, ValueError) as exc:
        raise IngestError(str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected ingest failure")
        raise IngestError(f"Unexpected error: {exc}") from exc


def format_settings_summary(config: Config | None = None) -> str:
    config = config or load_config()
    return "\n".join(
        [
            f"Config file: {DEFAULT_CONFIG_PATH}",
            f"Chat model: {config.chat_model}",
            f"Embedding model: {config.embedding_model}",
            f"Exports dir: {config.exports_dir}",
            f"LanceDB: {config.lancedb_uri}",
            f"Chrome CDP: {config.chrome_debug_url}",
            f"Insert into compose: {config.insert_into_compose}",
            f"Stale after: {config.stale_after_hours}h",
            f"Research: {'on' if config.research_enabled else 'off'}",
            f"Hotkey: Cmd+Shift+R",
        ]
    )
