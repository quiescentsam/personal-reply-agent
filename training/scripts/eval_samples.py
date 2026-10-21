#!/usr/bin/env python3
"""Offline eval on valid.jsonl: gold vs trained (and optionally untrained base).

Does not touch the personal_reply app.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import tomllib
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG = _REPO_ROOT / "training" / "config" / "lora.toml"


def _repo_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else _REPO_ROOT / p


def load_config(path: Path) -> dict:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _resolve_model(cfg: dict) -> str:
    model_cfg = cfg.get("model", {})
    if bool(model_cfg.get("use_qlora", False)):
        return str(
            model_cfg.get(
                "qlora_model",
                "mlx-community/Qwen2.5-0.5B-Instruct-4bit",
            )
        )
    return str(model_cfg.get("model", "mlx-community/Qwen2.5-0.5B-Instruct-bf16"))


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _split_messages(messages: list[dict]) -> tuple[list[dict], str]:
    if not messages or messages[-1].get("role") != "assistant":
        raise ValueError("Example must end with an assistant message (gold reply)")
    gold = str(messages[-1]["content"])
    prompt_messages = messages[:-1]
    return prompt_messages, gold


def _user_context(messages: list[dict]) -> str:
    for msg in messages:
        if msg.get("role") == "user":
            return str(msg.get("content", ""))
    return ""


def _build_prompt(tokenizer, prompt_messages: list[dict]) -> str:
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(
            prompt_messages,
            tokenize=False,
            add_generation_prompt=True,
        )
    parts = [f"{msg['role'].upper()}: {msg['content']}" for msg in prompt_messages]
    parts.append("ASSISTANT:")
    return "\n".join(parts)


def _generate_reply(generate, model, tokenizer, prompt: str, max_tokens: int) -> str:
    prediction = generate(
        model,
        tokenizer,
        prompt=prompt,
        max_tokens=max_tokens,
        verbose=False,
    )
    if isinstance(prediction, str) and prediction.startswith(prompt):
        prediction = prediction[len(prompt) :]
    return str(prediction).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=_DEFAULT_CONFIG,
        help="Path to training/config/lora.toml",
    )
    parser.add_argument(
        "--adapter-path",
        type=Path,
        default=None,
        help="Override adapter directory (default: adapters_dir/run_name)",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=8,
        help="Number of validation samples to generate",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=120,
        help="Max new tokens per generation",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Sample seed (default: dataset.seed from config)",
    )
    parser.add_argument(
        "--valid-path",
        type=Path,
        default=None,
        help="Override path to valid.jsonl",
    )
    parser.add_argument(
        "--compare-base",
        action="store_true",
        help="Also generate with the untrained base model (no adapter)",
    )
    parser.add_argument(
        "--base-only",
        action="store_true",
        help="Generate with untrained base only (skip adapter)",
    )
    args = parser.parse_args()

    if args.base_only and args.compare_base:
        raise SystemExit("Use either --base-only or --compare-base, not both.")

    cfg = load_config(args.config.resolve())
    paths = cfg.get("paths", {})
    dataset = cfg.get("dataset", {})
    seed = int(args.seed if args.seed is not None else dataset.get("seed", 42))

    processed_dir = _repo_path(paths.get("processed_dir", "training/data/processed"))
    valid_path = _repo_path(args.valid_path) if args.valid_path else processed_dir / "valid.jsonl"
    if not valid_path.is_file():
        raise SystemExit(f"Missing {valid_path}. Run prepare_dataset.py first.")

    adapters_dir = _repo_path(paths.get("adapters_dir", "training/data/adapters"))
    run_name = str(paths.get("run_name", "whatsapp-style"))
    adapter_path = (
        _repo_path(args.adapter_path)
        if args.adapter_path
        else adapters_dir / run_name
    )

    use_adapter = not args.base_only
    if use_adapter and not adapter_path.is_dir():
        raise SystemExit(
            f"Adapter path not found: {adapter_path}. Run train_lora.py first "
            "(or pass --base-only to eval the untrained model)."
        )

    rows = _load_jsonl(valid_path)
    if not rows:
        raise SystemExit(f"No examples in {valid_path}")

    rng = random.Random(seed)
    sample_n = min(args.n, len(rows))
    samples = rng.sample(rows, sample_n)
    model_id = _resolve_model(cfg)

    try:
        from mlx_lm import generate, load
    except ImportError as exc:
        raise SystemExit(
            'mlx-lm is required for eval. Install with:\n'
            '  pip install "mlx-lm[train]"\n'
            f"Original error: {exc}"
        ) from exc

    print(f"Loading model={model_id}")
    base_model = base_tokenizer = None
    trained_model = trained_tokenizer = None

    if args.compare_base or args.base_only:
        print("Loading untrained base (no adapter)")
        base_model, base_tokenizer = load(model_id)

    if use_adapter:
        print(f"Loading trained model + adapter={adapter_path}")
        trained_model, trained_tokenizer = load(model_id, adapter_path=str(adapter_path))

    gold_lens: list[int] = []
    base_lens: list[int] = []
    trained_lens: list[int] = []

    for i, row in enumerate(samples, start=1):
        messages = row["messages"]
        prompt_messages, gold = _split_messages(messages)
        context = _user_context(prompt_messages)
        gold_lens.append(len(gold))

        print("=" * 72)
        print(f"Sample {i}/{sample_n}")
        print("- context -")
        print(context[:1200] + ("…" if len(context) > 1200 else ""))
        print("- gold (your actual reply) -")
        print(gold)

        if base_model is not None:
            prompt = _build_prompt(base_tokenizer, prompt_messages)
            base_pred = _generate_reply(
                generate, base_model, base_tokenizer, prompt, args.max_tokens
            )
            base_lens.append(len(base_pred))
            print("- untrained base -")
            print(base_pred)

        if trained_model is not None:
            prompt = _build_prompt(trained_tokenizer, prompt_messages)
            trained_pred = _generate_reply(
                generate, trained_model, trained_tokenizer, prompt, args.max_tokens
            )
            trained_lens.append(len(trained_pred))
            label = "- trained (base + LoRA) -" if args.compare_base else "- trained model -"
            print(label)
            print(trained_pred)

    print("=" * 72)
    print("Length stats (characters)")
    print(
        f"  gold     mean={statistics.mean(gold_lens):.1f} "
        f"median={statistics.median(gold_lens):.1f}"
    )
    if base_lens:
        print(
            f"  base     mean={statistics.mean(base_lens):.1f} "
            f"median={statistics.median(base_lens):.1f}"
        )
    if trained_lens:
        print(
            f"  trained  mean={statistics.mean(trained_lens):.1f} "
            f"median={statistics.median(trained_lens):.1f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
