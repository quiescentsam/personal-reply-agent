from pathlib import Path

from personal_reply.ingest.whatsapp_txt import parse_whatsapp_export


def test_parse_marks_reopen_after_gap(tmp_path: Path) -> None:
    export = tmp_path / "WhatsApp Chat with Papa New.txt"
    export.write_text(
        "\n".join(
            [
                "1/1/26, 10:00 - Papa New: Hi",
                "1/1/26, 10:01 - Sameer: Hey",
                "1/5/26, 10:00 - Sameer: Long time no chat",
            ]
        ),
        encoding="utf-8",
    )

    messages = parse_whatsapp_export(
        export,
        sender_names=("Sameer",),
        stale_after_hours=48,
    )
    assert len(messages) == 2
    assert messages[0].message_kind == "reply"
    assert messages[1].message_kind == "reopen"
