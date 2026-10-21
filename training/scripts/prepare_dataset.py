#!/usr/bin/env python3
"""Build mlx-lm chat JSONL from WhatsApp .txt exports.

Standalone: does not import personal_reply app code.
Writes train.jsonl and valid.jsonl (mlx-lm expects the name valid.jsonl).
"""

from __future__ import annotations

import argparse
import json
import random
import re
import tomllib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG = _REPO_ROOT / "training" / "config" / "lora.toml"

# [1/15/24, 10:30:45 AM] Name: message
# 1/15/24, 10:30 - Name: message
_MESSAGE_LINE = re.compile(
    r"^(?:\[)?"
    r"(\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?)"
    r"(?:\])?\s*[-–]?\s*"
    r"([^:]+):\s"
    r"(.*)$",
    re.IGNORECASE,
)

_MEDIA_PATTERNS = (
    re.compile(r"^<media omitted>$", re.IGNORECASE),
    re.compile(r"^image omitted$", re.IGNORECASE),
    re.compile(r"^video omitted$", re.IGNORECASE),
    re.compile(r"^audio omitted$", re.IGNORECASE),
    re.compile(r"^sticker omitted$", re.IGNORECASE),
    re.compile(r"^document omitted$", re.IGNORECASE),
    re.compile(r"^gif omitted$", re.IGNORECASE),
    re.compile(r"^contact card omitted$", re.IGNORECASE),
    re.compile(r"^this message was deleted$", re.IGNORECASE),
    re.compile(r"^you deleted this message$", re.IGNORECASE),
)

_TIMESTAMP_FORMATS = (
    "%m/%d/%y, %I:%M:%S %p",
    "%m/%d/%Y, %I:%M:%S %p",
    "%m/%d/%y, %I:%M %p",
    "%m/%d/%Y, %I:%M %p",
    "%m/%d/%y, %H:%M:%S",
    "%m/%d/%Y, %H:%M:%S",
    "%m/%d/%y, %H:%M",
    "%m/%d/%Y, %H:%M",
    "%d/%m/%y, %H:%M:%S",
    "%d/%m/%Y, %H:%M:%S",
    "%d/%m/%y, %H:%M",
    "%d/%m/%Y, %H:%M",
    "%d/%m/%y, %I:%M %p",
    "%d/%m/%Y, %I:%M %p",
)


@dataclass(frozen=True)
class ChatLine:
    sender: str
    text: str
    timestamp: datetime
    contact: str


def _repo_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else _REPO_ROOT / p


def load_config(path: Path) -> dict:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _parse_timestamp(raw: str) -> datetime:
    cleaned = " ".join(raw.strip().split())
    for fmt in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return datetime.min


def _contact_from_filename(path: Path) -> str:
    stem = path.stem
    for prefix in ("WhatsApp Chat with ", "WhatsAppChatwith", "WhatsAppChatWith"):
        if stem.startswith(prefix):
            stem = stem[len(prefix) :]
            break
    if " " not in stem:
        stem = re.sub(r"([a-z])([A-Z])", r"\1 \2", stem)
    return stem.strip() or path.stem


def _is_media_or_empty(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    return any(pat.match(stripped) for pat in _MEDIA_PATTERNS)


def parse_whatsapp_export(path: Path) -> list[ChatLine]:
    contact = _contact_from_filename(path)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    rows: list[ChatLine] = []
    current_sender = ""
    current_timestamp = datetime.min
    current_text: list[str] = []

    def flush() -> None:
        nonlocal current_sender, current_timestamp, current_text
        if not current_sender or not current_text:
            return
        text = " ".join(current_text).strip()
        if text:
            rows.append(
                ChatLine(
                    sender=current_sender,
                    text=text,
                    timestamp=current_timestamp,
                    contact=contact,
                )
            )
        current_sender = ""
        current_text = []

    for line in lines:
        match = _MESSAGE_LINE.match(line)
        if match:
            flush()
            timestamp_raw, sender, text = match.groups()
            current_sender = sender.strip()
            current_timestamp = _parse_timestamp(timestamp_raw)
            current_text = [text.strip()]
            continue
        if current_text and line.strip():
            current_text.append(line.strip())

    flush()
    return rows


def _format_context(before: list[ChatLine]) -> str:
    if not before:
        return "(no prior messages)"
    return "\n".join(f"{line.sender}: {line.text}" for line in before)


def build_examples(
    chat_lines: list[ChatLine],
    *,
    sender_names: tuple[str, ...],
    context_messages_before: int,
    min_reply_chars: int,
    system_prompt: str,
) -> list[dict]:
    sender_set = {name.casefold() for name in sender_names}
    examples: list[dict] = []

    for index, line in enumerate(chat_lines):
        if line.sender.casefold() not in sender_set:
            continue
        if _is_media_or_empty(line.text):
            continue
        if len(line.text.strip()) < min_reply_chars:
            continue

        before = chat_lines[max(0, index - context_messages_before) : index]
        # Skip replies that only follow media-only / empty context if there is no context at all
        # and we have prior lines that were all filtered — still allow reopen-style messages.
        user_content = (
            f"Contact: {line.contact}\n"
            f"Thread so far:\n{_format_context(before)}\n\n"
            "Suggest a reply to the latest message."
        )
        examples.append(
            {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": line.text.strip()},
                ],
                "meta": {
                    "contact": line.contact,
                    "timestamp": line.timestamp.isoformat(),
                },
            }
        )
    return examples


def _write_jsonl(path: Path, rows: list[dict], *, strip_meta: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            payload = {k: v for k, v in row.items() if k != "meta"} if strip_meta else row
            # mlx-lm chat format: only "messages" is required
            fh.write(json.dumps({"messages": payload["messages"]}, ensure_ascii=False) + "\n")


def split_examples(
    examples: list[dict],
    *,
    val_fraction: float,
    seed: int,
) -> tuple[list[dict], list[dict]]:
    if not examples:
        return [], []
    shuffled = list(examples)
    random.Random(seed).shuffle(shuffled)
    if len(shuffled) == 1:
        return shuffled, []
    n_val = max(1, int(round(len(shuffled) * val_fraction)))
    n_val = min(n_val, len(shuffled) - 1)
    val = shuffled[:n_val]
    train = shuffled[n_val:]
    return train, val


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=_DEFAULT_CONFIG,
        help="Path to training/config/lora.toml",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=None,
        help="Override raw WhatsApp .txt directory",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=None,
        help="Override output directory for train/valid JSONL",
    )
    args = parser.parse_args()

    cfg = load_config(args.config.resolve())
    paths = cfg.get("paths", {})
    dataset = cfg.get("dataset", {})

    raw_dir = _repo_path(args.raw_dir or paths.get("raw_dir", "training/data/raw"))
    processed_dir = _repo_path(
        args.processed_dir or paths.get("processed_dir", "training/data/processed")
    )

    sender_names = tuple(dataset.get("sender_names", ["You"]))
    context_before = int(dataset.get("context_messages_before", 3))
    min_reply_chars = int(dataset.get("min_reply_chars", 2))
    val_fraction = float(dataset.get("val_fraction", 0.1))
    seed = int(dataset.get("seed", 42))
    system_prompt = str(
        dataset.get(
            "system_prompt",
            "Reply in my WhatsApp voice: match my tone, length, punctuation, and formality.",
        )
    )

    exports = sorted(raw_dir.glob("*.txt"))
    if not exports:
        raise SystemExit(
            f"No .txt WhatsApp exports found in {raw_dir}. "
            "Drop chat exports there and re-run."
        )

    all_examples: list[dict] = []
    for path in exports:
        chat_lines = parse_whatsapp_export(path)
        built = build_examples(
            chat_lines,
            sender_names=sender_names,
            context_messages_before=context_before,
            min_reply_chars=min_reply_chars,
            system_prompt=system_prompt,
        )
        print(f"{path.name}: {len(chat_lines)} lines → {len(built)} examples")
        all_examples.extend(built)

    train, val = split_examples(all_examples, val_fraction=val_fraction, seed=seed)
    train_path = processed_dir / "train.jsonl"
    valid_path = processed_dir / "valid.jsonl"
    _write_jsonl(train_path, train)
    _write_jsonl(valid_path, val)

    print(
        f"Wrote {len(train)} train → {train_path}\n"
        f"Wrote {len(val)} valid → {valid_path}"
    )
    if len(train) < 50:
        print(
            "Warning: small train set (<50). Prefer more chat history; "
            "keep LoRA rank/iters low to limit overfitting."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
