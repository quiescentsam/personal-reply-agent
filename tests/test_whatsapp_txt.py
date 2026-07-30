from pathlib import Path

from personal_reply.ingest.whatsapp_txt import _contact_from_filename, parse_whatsapp_export


def test_parse_whatsapp_export_extracts_user_messages(tmp_path: Path) -> None:
    export = tmp_path / "WhatsApp Chat with Alex.txt"
    export.write_text(
        "\n".join(
            [
                "[1/15/24, 10:30:45 AM] Alex: Hey are you free tomorrow?",
                "[1/15/24, 10:31:10 AM] You: Yeah should work",
                "[1/15/24, 10:31:20 AM] Alex: Cool, 3pm?",
                "[1/15/24, 10:32:00 AM] You: Sounds good",
            ]
        ),
        encoding="utf-8",
    )

    messages = parse_whatsapp_export(export, sender_names=("You",))

    assert len(messages) == 2
    assert messages[0].contact == "Alex"
    assert messages[0].text == "Yeah should work"
    assert "[15/01/24 10:30] Alex: Hey are you free tomorrow?" in messages[0].context_before
    assert messages[1].text == "Sounds good"
    assert "[15/01/24 10:31] Alex: Cool, 3pm?" in messages[1].context_before
    assert "[15/01/24 10:31] You: Yeah should work" in messages[0].conversation_window


def test_parse_whatsapp_export_captures_context_after(tmp_path: Path) -> None:
    export = tmp_path / "WhatsApp Chat with Alex.txt"
    export.write_text(
        "\n".join(
            [
                "1/15/24, 10:30 - Alex: Hey are you free tomorrow?",
                "1/15/24, 10:31 - You: Yeah should work",
                "1/15/24, 10:32 - Alex: Cool, 3pm?",
                "1/15/24, 10:33 - You: Sounds good",
                "1/15/24, 10:34 - Alex: Great",
            ]
        ),
        encoding="utf-8",
    )

    messages = parse_whatsapp_export(
        export,
        sender_names=("You",),
        context_messages_before=2,
        context_messages_after=2,
    )

    assert "[15/01/24 10:32] Alex: Cool, 3pm?" in messages[0].context_after
    assert "[15/01/24 10:32] Alex: Cool, 3pm?" in messages[0].conversation_window
    assert messages[1].context_after == "[15/01/24 10:34] Alex: Great"


def test_parse_whatsapp_export_supports_dash_format_and_custom_sender(tmp_path: Path) -> None:
    export = tmp_path / "WhatsAppChatwithPapaNew.txt"
    export.write_text(
        "\n".join(
            [
                "12/12/24, 07:51 - Papa New: Pahuch gaye Jahanabad",
                "12/12/24, 07:59 - Sameer: Haan",
                "12/12/24, 07:59 - Papa New: Badiya",
                "12/12/24, 10:56 - Sameer: Belan mil gya lucky ko",
            ]
        ),
        encoding="utf-8",
    )

    messages = parse_whatsapp_export(export, sender_names=("Sameer",))

    assert len(messages) == 2
    assert messages[0].text == "Haan"
    assert "[12/12/24 07:51] Papa New: Pahuch gaye Jahanabad" in messages[0].context_before
    assert "[12/12/24 07:59] Papa New: Badiya" in messages[0].context_after
    assert messages[1].text == "Belan mil gya lucky ko"


def test_contact_from_filename_without_spaces() -> None:
    export = Path("/tmp/WhatsAppChatwithPapaNew.txt")
    from personal_reply.ingest.whatsapp_txt import _contact_from_filename

    assert _contact_from_filename(export) == "Papa New"
