from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)

_APP_NAME = "Personal Reply"


def _escape_applescript(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def show_notification(
    *,
    title: str = _APP_NAME,
    subtitle: str = "",
    message: str = "",
) -> None:
    """Show a macOS notification without requiring a bundled Info.plist."""
    parts = [f'display notification "{_escape_applescript(message)}"']
    parts.append(f'with title "{_escape_applescript(title)}"')
    if subtitle:
        parts.append(f'subtitle "{_escape_applescript(subtitle)}"')
    script = " ".join(parts)
    try:
        subprocess.run(["osascript", "-e", script], check=False, capture_output=True)
    except OSError as exc:
        logger.warning("Could not show notification: %s", exc)
