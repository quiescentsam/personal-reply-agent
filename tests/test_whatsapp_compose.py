from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from personal_reply.browser.errors import WhatsAppComposeError
from personal_reply.browser.whatsapp import write_whatsapp_compose


def test_write_whatsapp_compose_types_text() -> None:
    page = MagicMock()
    compose = MagicMock()
    page.locator.return_value.first = compose

    write_whatsapp_compose(
        page,
        compose_selector="footer div[contenteditable='true']",
        text="On my way",
    )

    page.bring_to_front.assert_called_once()
    page.locator.assert_called_once_with("footer div[contenteditable='true']")
    compose.wait_for.assert_called_once_with(state="visible", timeout=5000)
    compose.click.assert_called_once()
    page.keyboard.press.assert_any_call("Meta+A")
    page.keyboard.press.assert_any_call("Backspace")
    page.keyboard.insert_text.assert_called_once_with("On my way")


def test_write_whatsapp_compose_requires_selector() -> None:
    page = MagicMock()
    with pytest.raises(WhatsAppComposeError, match="compose box not found"):
        write_whatsapp_compose(page, compose_selector=None, text="hi")


def test_write_whatsapp_compose_rejects_empty_text() -> None:
    page = MagicMock()
    with pytest.raises(WhatsAppComposeError, match="empty"):
        write_whatsapp_compose(page, compose_selector="footer div", text="   ")
