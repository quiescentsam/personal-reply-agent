from __future__ import annotations

from playwright.sync_api import Page

from personal_reply.browser.contact_name import resolve_contact_name
from personal_reply.browser.errors import (
    WhatsAppComposeError,
    WhatsAppTabNotFoundError,
    WhatsAppThreadReadError,
)
from personal_reply.browser.models import ThreadContext
from personal_reply.browser.whatsapp_dom import WHATSAPP_EXTRACT_SCRIPT
from personal_reply.browser.whatsapp_parser import build_thread_context


def read_whatsapp_thread(
    page: Page,
    *,
    sender_names: tuple[str, ...],
) -> ThreadContext:
    if "web.whatsapp.com" not in (page.url or ""):
        raise WhatsAppTabNotFoundError(
            f"Active tab is not WhatsApp Web: {page.url or '(empty url)'}"
        )

    payload = page.evaluate(WHATSAPP_EXTRACT_SCRIPT)
    raw_messages = list(payload.get("messages", []))
    try:
        contact = resolve_contact_name(
            str(payload.get("contact", "")),
            raw_messages,
            sender_names=sender_names,
        )
        return build_thread_context(
            contact=contact,
            raw_messages=raw_messages,
            sender_names=sender_names,
            compose_selector=payload.get("composeSelector"),
        )
    except ValueError as exc:
        raise WhatsAppThreadReadError(str(exc)) from exc


def write_whatsapp_compose(
    page: Page,
    *,
    compose_selector: str | None,
    text: str,
) -> None:
    if not compose_selector:
        raise WhatsAppComposeError(
            "WhatsApp compose box not found. Open a chat and make sure the message box is visible."
        )
    if not text.strip():
        raise WhatsAppComposeError("Cannot type an empty reply.")

    page.bring_to_front()
    compose = page.locator(compose_selector).first
    try:
        compose.wait_for(state="visible", timeout=5000)
    except Exception as exc:
        raise WhatsAppComposeError(
            "WhatsApp compose box is not visible. Select a chat and try again."
        ) from exc

    compose.click()
    page.keyboard.press("Meta+A")
    page.keyboard.press("Backspace")
    page.keyboard.insert_text(text)
