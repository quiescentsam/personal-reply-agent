from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from personal_reply.app_service import (
    IngestError,
    SuggestError,
    format_settings_summary,
    reingest_exports,
    suggest_and_copy,
    suggest_from_browser,
)
from personal_reply.clipboard import copy_to_clipboard
from personal_reply.reply.verbose import SuggestResult
from personal_reply.rag.errors import OllamaUnavailableError


def test_copy_to_clipboard_uses_pbcopy() -> None:
    with patch("personal_reply.clipboard.subprocess.run") as run:
        copy_to_clipboard("hello there")
    run.assert_called_once()
    args, kwargs = run.call_args
    assert args[0] == ["pbcopy"]
    assert kwargs["input"] == b"hello there"
    assert kwargs["check"] is True


def test_suggest_from_browser_logs_verbose_output(capsys) -> None:
    config = MagicMock()
    verbose_result = SuggestResult(
        suggestion="reply text",
        examples=[],
        messages=[{"role": "user", "content": "hello"}],
        mode="reopen",
        mode_reason="stale",
    )
    with patch("personal_reply.app_service.ReplyGenerator") as generator_cls:
        generator = generator_cls.return_value.__enter__.return_value
        generator.suggest_from_browser.return_value = verbose_result
        assert suggest_from_browser(config, verbose=True) == ("reply text", "reopen")
    captured = capsys.readouterr()
    assert "=== Conversation mode ===" in captured.err
    assert captured.out.strip() == "reply text"


def test_suggest_from_browser_returns_trimmed_text() -> None:
    config = MagicMock()
    with patch("personal_reply.app_service.ReplyGenerator") as generator_cls:
        generator = generator_cls.return_value.__enter__.return_value
        generator.suggest_from_browser.return_value = SuggestResult(
            suggestion="  hi Sam  ",
            examples=[],
            messages=[],
            mode="respond",
        )
        assert suggest_from_browser(config) == ("hi Sam", "respond")


def test_suggest_from_browser_maps_known_errors() -> None:
    config = MagicMock()
    with patch("personal_reply.app_service.ReplyGenerator") as generator_cls:
        generator = generator_cls.return_value.__enter__.return_value
        generator.suggest_from_browser.side_effect = OllamaUnavailableError("down")
        with pytest.raises(SuggestError, match="down"):
            suggest_from_browser(config)


def test_suggest_and_copy_copies_result() -> None:
    config = MagicMock()
    config.insert_into_compose = True
    with (
        patch(
            "personal_reply.app_service.suggest_from_browser",
            return_value=("reply text", "respond"),
        ) as suggest,
        patch("personal_reply.app_service.copy_to_clipboard") as copy,
    ):
        assert suggest_and_copy(config) == ("reply text", True, "respond")
    suggest.assert_called_once_with(
        config=config,
        insert_into_compose=True,
        verbose=False,
        research=False,
    )
    copy.assert_called_once_with("reply text")


def test_reingest_exports_maps_errors() -> None:
    config = MagicMock()
    with patch("personal_reply.app_service.run_ingest", side_effect=FileNotFoundError("missing")):
        with pytest.raises(IngestError, match="missing"):
            reingest_exports(config)


def test_format_settings_summary_includes_paths() -> None:
    config = MagicMock()
    config.chat_model = "llama3.1:8b"
    config.embedding_model = "nomic-embed-text"
    config.exports_dir = "/tmp/exports"
    config.lancedb_uri = "/tmp/style.lance"
    config.chrome_debug_url = "http://localhost:9222"
    config.insert_into_compose = True
    summary = format_settings_summary(config)
    assert "llama3.1:8b" in summary
    assert "nomic-embed-text" in summary
    assert "Cmd+Shift+R" in summary
    assert "/tmp/exports" in summary
