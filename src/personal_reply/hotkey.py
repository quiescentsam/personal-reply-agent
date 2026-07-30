from __future__ import annotations

import logging
import subprocess
import sys
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pynput.keyboard import GlobalHotKeys

logger = logging.getLogger(__name__)

_ACCESSIBILITY_SETTINGS_URL = (
    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
)


def accessibility_trusted() -> bool:
    try:
        from ApplicationServices import AXIsProcessTrusted
    except ImportError:
        logger.debug("ApplicationServices unavailable; skipping accessibility check")
        return True

    return bool(AXIsProcessTrusted())


def request_accessibility_trust(*, prompt: bool = True) -> bool:
    """Ask macOS to grant Accessibility to this process (shows a system dialog)."""
    if accessibility_trusted():
        return True

    try:
        from ApplicationServices import AXIsProcessTrustedWithOptions
    except ImportError:
        logger.debug("ApplicationServices unavailable; cannot request accessibility")
        return True

    options = {"AXTrustedCheckOptionPrompt": True} if prompt else None
    return bool(AXIsProcessTrustedWithOptions(options))


def host_app_name() -> str:
    parent = sys.argv[0]
    if "Cursor" in parent or "cursor" in parent:
        return "Cursor"
    if "iTerm" in parent:
        return "iTerm"
    if "Terminal" in parent or parent.rsplit("/", 1)[-1].startswith("python"):
        return "Terminal"
    return "the app running this command"


def accessibility_instructions() -> str:
    host = host_app_name()
    return (
        "Cmd+Shift+R needs Accessibility permission.\n\n"
        "1. macOS may show a system dialog — click Open System Settings.\n"
        "2. In Privacy & Security → Accessibility, enable:\n"
        "   • Python\n"
        f"   • {host} (if listed)\n"
        "3. Return here and choose Enable Hotkey again.\n\n"
        "Suggest Reply from the menu works without the hotkey."
    )


def open_accessibility_settings() -> None:
    subprocess.run(["open", _ACCESSIBILITY_SETTINGS_URL], check=False)


def start_hotkey_listener(
    callback: Callable[[], None],
    *,
    combo: str = "<cmd>+<shift>+r",
) -> tuple[GlobalHotKeys | None, threading.Thread | None]:
    if not accessibility_trusted():
        logger.warning(
            "Accessibility permission not granted; global hotkey disabled. "
            "Use menu → Enable Hotkey to request permission."
        )
        return None, None

    from pynput import keyboard

    listener = keyboard.GlobalHotKeys({combo: callback})
    thread = threading.Thread(
        target=listener.start,
        name="personal-reply-hotkey",
        daemon=True,
    )
    thread.start()
    logger.info("Global hotkey registered: Cmd+Shift+R")
    return listener, thread
