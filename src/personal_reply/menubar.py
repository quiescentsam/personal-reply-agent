from __future__ import annotations

import logging
import subprocess
import threading

import rumps

from personal_reply.app_service import (
    IngestError,
    SuggestError,
    format_settings_summary,
    reingest_exports,
    suggest_and_copy,
)
from personal_reply.config import DEFAULT_CONFIG_PATH, load_config
from personal_reply.hotkey import (
    accessibility_instructions,
    accessibility_trusted,
    open_accessibility_settings,
    request_accessibility_trust,
    start_hotkey_listener,
)
from personal_reply.main_thread import run_on_main_thread
from personal_reply.notify import show_notification

logger = logging.getLogger(__name__)


class PersonalReplyApp(rumps.App):
    def __init__(self, *, verbose: bool = False) -> None:
        super().__init__("Reply", title="💬")
        self.config = load_config()
        self.verbose = verbose
        self._busy = False
        self._last_suggestion = ""
        self._hotkey_listener = None
        self._hotkey_thread = None
        self.menu = [
            "Suggest Reply",
            "Research & Suggest",
            "Enable Hotkey",
            "Re-ingest exports",
            "Settings",
            None,
            "Quit",
        ]
        self._setup_hotkey_on_launch()

    def _on_main(self, func) -> None:
        run_on_main_thread(func)

    def _setup_hotkey_on_launch(self) -> None:
        if not accessibility_trusted():
            request_accessibility_trust(prompt=True)
        self._try_register_hotkey()
        if not accessibility_trusted():
            rumps.Timer(self._show_hotkey_setup_help, 1.5).start()

    def _show_hotkey_setup_help(self, _: object | None = None) -> None:
        if accessibility_trusted() and self._hotkey_listener is not None:
            return
        rumps.alert("Enable Cmd+Shift+R", accessibility_instructions())
        open_accessibility_settings()

    def _try_register_hotkey(self) -> bool:
        if self._hotkey_listener is not None:
            return True
        self._hotkey_listener, self._hotkey_thread = start_hotkey_listener(self._on_hotkey)
        return self._hotkey_listener is not None

    @rumps.clicked("Enable Hotkey")
    def on_enable_hotkey_clicked(self, _: object) -> None:
        request_accessibility_trust(prompt=True)
        if self._try_register_hotkey():
            show_notification(subtitle="Hotkey enabled", message="Cmd+Shift+R is ready.")
            return
        rumps.alert("Enable Cmd+Shift+R", accessibility_instructions())
        open_accessibility_settings()

    def _on_hotkey(self) -> None:
        self._on_main(self._handle_hotkey)

    def _handle_hotkey(self) -> None:
        show_notification(
            subtitle="Suggesting reply...",
            message="Reading WhatsApp Web thread",
        )
        self._run_suggest_async(source="hotkey", research=False)

    @rumps.clicked("Suggest Reply")
    def on_suggest_clicked(self, _: object) -> None:
        self._run_suggest_async(source="menu", research=False)

    @rumps.clicked("Research & Suggest")
    def on_research_suggest_clicked(self, _: object) -> None:
        self._run_suggest_async(source="research-menu", research=True)

    @rumps.clicked("Re-ingest exports")
    def on_reingest_clicked(self, _: object) -> None:
        if self._busy:
            rumps.alert("Busy", "Another action is already running.")
            return
        self._busy = True
        self.title = "⏳"

        def task() -> None:
            try:
                count = reingest_exports(self.config)
            except IngestError as exc:
                self._on_main(lambda: rumps.alert("Ingest failed", str(exc)))
            else:
                self._on_main(
                    lambda: show_notification(
                        subtitle="Ingest complete",
                        message=f"Indexed {count} messages",
                    )
                )
            finally:
                self._on_main(self._set_idle)

        threading.Thread(target=task, name="personal-reply-ingest", daemon=True).start()

    @rumps.clicked("Settings")
    def on_settings_clicked(self, _: object) -> None:
        summary = format_settings_summary(self.config)
        if not accessibility_trusted():
            summary += "\n\nHotkey: disabled — use Enable Hotkey in the menu."
        rumps.alert("Settings", summary)
        try:
            subprocess.run(["open", str(DEFAULT_CONFIG_PATH)], check=False)
        except OSError as exc:
            logger.warning("Could not open config file: %s", exc)

    def _set_idle(self) -> None:
        self._busy = False
        self.title = "💬"

    def _set_busy(self) -> None:
        self._busy = True
        self.title = "⏳"

    def _run_suggest_async(self, *, source: str, research: bool = False) -> None:
        if self._busy:
            show_notification(
                subtitle="Busy",
                message="Wait for the current action to finish.",
            )
            return

        self._set_busy()
        # Playwright must run on the main thread; defer so the menu bar can update first.
        rumps.Timer(
            lambda timer: self._run_suggest_on_main(timer, source, research),
            0.1,
        ).start()

    def _run_suggest_on_main(self, timer: rumps.Timer, source: str, research: bool) -> None:
        timer.stop()
        try:
            suggestion, inserted, mode = suggest_and_copy(
                self.config,
                verbose=self.verbose,
                research=research,
            )
        except SuggestError as exc:
            rumps.alert("Suggest failed", str(exc))
        else:
            preview = suggestion if len(suggestion) <= 120 else f"{suggestion[:117]}..."
            if inserted and mode == "reopen":
                subtitle = "New topic drafted"
            elif inserted:
                subtitle = "Typed into compose"
            elif research:
                subtitle = "Researched & copied"
            else:
                subtitle = "Copied to clipboard"
            self._last_suggestion = suggestion
            show_notification(subtitle=subtitle, message=preview)
            logger.info("Suggestion via %s: %s", source, preview)
        finally:
            self._set_idle()


def main(*, verbose: bool = False) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if verbose:
        logger.info("Verbose mode enabled — RAG details print to this terminal on suggest.")
    PersonalReplyApp(verbose=verbose).run()
