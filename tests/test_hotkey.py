from __future__ import annotations

from unittest.mock import MagicMock, patch

from personal_reply.hotkey import (
    accessibility_trusted,
    host_app_name,
    request_accessibility_trust,
    start_hotkey_listener,
)


def test_request_accessibility_trust_short_circuits_when_trusted() -> None:
    with patch("personal_reply.hotkey.accessibility_trusted", return_value=True):
        assert request_accessibility_trust() is True


def test_request_accessibility_trust_prompts_when_untrusted() -> None:
    with (
        patch("personal_reply.hotkey.accessibility_trusted", return_value=False),
        patch("personal_reply.hotkey.AXIsProcessTrustedWithOptions", create=True) as prompt,
    ):
        prompt.return_value = False
        with patch.dict(
            "sys.modules",
            {
                "ApplicationServices": MagicMock(
                    AXIsProcessTrustedWithOptions=prompt,
                )
            },
        ):
            assert request_accessibility_trust(prompt=True) is False
        prompt.assert_called_once_with({"AXTrustedCheckOptionPrompt": True})


def test_start_hotkey_listener_skips_without_accessibility() -> None:
    callback = MagicMock()
    with patch("personal_reply.hotkey.accessibility_trusted", return_value=False):
        listener, thread = start_hotkey_listener(callback)
    assert listener is None
    assert thread is None
    callback.assert_not_called()


def test_start_hotkey_listener_registers_when_trusted() -> None:
    callback = MagicMock()
    fake_listener = MagicMock()
    with (
        patch("personal_reply.hotkey.accessibility_trusted", return_value=True),
        patch("pynput.keyboard.GlobalHotKeys", return_value=fake_listener) as hotkeys,
    ):
        listener, thread = start_hotkey_listener(callback)
    assert listener is fake_listener
    assert thread is not None
    hotkeys.assert_called_once_with({"<cmd>+<shift>+r": callback})


def test_host_app_name_detects_terminal() -> None:
    with patch("personal_reply.hotkey.sys.argv", ["/usr/bin/python3"]):
        assert host_app_name() == "Terminal"
