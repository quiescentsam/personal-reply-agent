from __future__ import annotations


class BrowserConnectionError(ConnectionError):
    """Raised when Playwright cannot attach to Chrome via CDP."""


class WhatsAppTabNotFoundError(RuntimeError):
    """Raised when no suitable WhatsApp Web tab is open."""


class WhatsAppThreadReadError(RuntimeError):
    """Raised when the WhatsApp thread could not be parsed from the page."""


class WhatsAppComposeError(RuntimeError):
    """Raised when the suggestion could not be typed into the compose box."""
