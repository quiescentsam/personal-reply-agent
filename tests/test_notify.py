from unittest.mock import patch

from personal_reply.notify import show_notification


def test_show_notification_uses_osascript() -> None:
    with patch("personal_reply.notify.subprocess.run") as run:
        show_notification(title="Personal Reply", subtitle="Done", message='Say "hi"')
    run.assert_called_once()
    command, *_ = run.call_args[0]
    assert command[:2] == ["osascript", "-e"]
    script = command[2]
    assert 'display notification "Say \\"hi\\""' in script
    assert 'with title "Personal Reply"' in script
    assert 'subtitle "Done"' in script
