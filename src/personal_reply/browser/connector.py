from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import httpx
from playwright.sync_api import Browser, Page, Playwright, sync_playwright

from personal_reply.browser.errors import BrowserConnectionError, WhatsAppTabNotFoundError


def _debug_endpoint_available(debug_url: str) -> bool:
    urls = [debug_url]
    if "localhost" in debug_url:
        urls.append(debug_url.replace("localhost", "127.0.0.1"))
    for url in urls:
        try:
            response = httpx.get(f"{url}/json/version", timeout=2.0)
            if response.status_code == 200:
                return True
        except httpx.HTTPError:
            continue
    return False


def _pick_whatsapp_page(browser: Browser) -> Page:
    candidates: list[Page] = []
    for context in browser.contexts:
        for page in context.pages:
            if "web.whatsapp.com" in (page.url or ""):
                candidates.append(page)

    if not candidates:
        raise WhatsAppTabNotFoundError(
            "No WhatsApp Web tab found. Open https://web.whatsapp.com and select a chat."
        )

    return candidates[-1]


@contextmanager
def connect_to_chrome(
    *,
    debug_url: str = "http://localhost:9222",
) -> Iterator[Page]:
    if not _debug_endpoint_available(debug_url):
        raise BrowserConnectionError(
            f"Cannot reach Chrome CDP at {debug_url}. "
            "Steps: 1) Run: ./scripts/launch_chrome_debug.sh "
            "(starts a separate debug Chrome; your regular Chrome can stay open). "
            "2) Open https://web.whatsapp.com in that window and select a chat. "
            "3) Retry suggest --from-browser. "
            "If the debug port still fails, relaunch with the launch script."
        )

    playwright: Playwright | None = None
    browser: Browser | None = None
    try:
        playwright = sync_playwright().start()
        browser = playwright.chromium.connect_over_cdp(debug_url)
        page = _pick_whatsapp_page(browser)
        page.bring_to_front()
        yield page
    except (BrowserConnectionError, WhatsAppTabNotFoundError):
        raise
    except Exception as exc:
        raise BrowserConnectionError(
            f"Failed to attach Playwright to Chrome at {debug_url}: {exc}"
        ) from exc
    finally:
        if browser is not None:
            browser.close()
        if playwright is not None:
            playwright.stop()
