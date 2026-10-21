#!/usr/bin/env python3
"""Run MLX LoRA / QLoRA fine-tuning via mlx_lm.lora.

Reads training/config/lora.toml, expects train.jsonl + valid.jsonl under
processed_dir, writes a YAML config mlx-lm understands, then trains into
adapters_dir/<run_name>/.

Does not modify the personal_reply app.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG = _REPO_ROOT / "training" / "config" / "lora.toml"


def _repo_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else _REPO_ROOT / p


def load_config(path: Path) -> dict:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _resolve_model(cfg: dict) -> tuple[str, str]:
    model_cfg = cfg.get("model", {})
    use_qlora = bool(model_cfg.get("use_qlora", False))
    if use_qlora:
        model = str(
            model_cfg.get(
                "qlora_model",
                "mlx-community/Qwen2.5-0.5B-Instruct-4bit",
            )
        )
        method = "qlora"
    else:
        model = str(model_cfg.get("model", "mlx-community/Qwen2.5-0.5B-Instruct-bf16"))
        method = "lora"
    return model, method


def _yaml_escape(value: str) -> str:
    return json.dumps(value)


def write_mlx_yaml(path: Path, payload: dict) -> None:
    """Write a minimal YAML file without requiring PyYAML at prepare time."""
    lines: list[str] = [
        "# Auto-generated for mlx_lm.lora — do not edit by hand while training.",
        f"# source: {payload.get('_source_config', '')}",
        "",
    ]
    skip = {"_source_config"}
    for key, value in payload.items():
        if key in skip:
            continue
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        elif isinstance(value, str):
            lines.append(f"{key}: {_yaml_escape(value)}")
        elif isinstance(value, dict):
            lines.append(f"{key}:")
            for nested_key, nested_val in value.items():
                if isinstance(nested_val, bool):
                    rendered = "true" if nested_val else "false"
                elif isinstance(nested_val, (int, float)):
                    rendered = str(nested_val)
                else:
                    rendered = _yaml_escape(str(nested_val))
                lines.append(f"  {nested_key}: {rendered}")
        elif value is None:
            lines.append(f"{key}: null")
        else:
            lines.append(f"{key}: {_yaml_escape(str(value))}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_mlx_payload(cfg: dict, *, processed_dir: Path, adapter_path: Path, source: Path) -> dict:
    model, _method = _resolve_model(cfg)
    lora = cfg.get("lora", {})
    train = cfg.get("train", {})
    dataset = cfg.get("dataset", {})

    return {
        "_source_config": str(source),
        "model": model,
        "train": True,
        "data": str(processed_dir),
        "adapter_path": str(adapter_path),
        "fine_tune_type": str(lora.get("fine_tune_type", "lora")),
        "num_layers": int(lora.get("num_layers", 16)),
        "batch_size": int(train.get("batch_size", 1)),
        "iters": int(train.get("iters", 600)),
        "learning_rate": float(train.get("learning_rate", 1e-5)),
        "steps_per_report": int(train.get("steps_per_report", 10)),
        "steps_per_eval": int(train.get("steps_per_eval", 50)),
        "val_batches": int(train.get("val_batches", 10)),
        "max_seq_length": int(train.get("max_seq_length", 1024)),
        "mask_prompt": bool(train.get("mask_prompt", True)),
        "grad_checkpoint": bool(train.get("grad_checkpoint", False)),
        "seed": int(dataset.get("seed", 42)),
        "lora_parameters": {
            "rank": int(lora.get("rank", 16)),
            "dropout": float(lora.get("dropout", 0.0)),
            "scale": float(lora.get("scale", 20.0)),
        },
    }


def build_command(cfg: dict, *, config_path: Path) -> tuple[list[str], Path, Path, dict]:
    paths = cfg.get("paths", {})
    processed_dir = _repo_path(paths.get("processed_dir", "training/data/processed"))
    adapters_dir = _repo_path(paths.get("adapters_dir", "training/data/adapters"))
    run_name = str(paths.get("run_name", "whatsapp-style"))
    adapter_path = adapters_dir / run_name

    train_jsonl = processed_dir / "train.jsonl"
    valid_jsonl = processed_dir / "valid.jsonl"
    if not train_jsonl.is_file():
        raise SystemExit(f"Missing {train_jsonl}. Run prepare_dataset.py first.")
    if not valid_jsonl.is_file():
        print(f"Warning: {valid_jsonl} missing; training without validation loss.")

    model, method = _resolve_model(cfg)
    adapter_path.mkdir(parents=True, exist_ok=True)

    mlx_yaml = adapter_path / "mlx_lora_config.yaml"
    payload = _build_mlx_payload(
        cfg,
        processed_dir=processed_dir,
        adapter_path=adapter_path,
        source=config_path,
    )
    write_mlx_yaml(mlx_yaml, payload)

    which = shutil.which("mlx_lm.lora")
    if which:
        cmd = [which, "--config", str(mlx_yaml)]
    else:
        # Preferred module form per mlx-lm (python -m mlx_lm.lora is deprecated)
        cmd = [sys.executable, "-m", "mlx_lm", "lora", "--config", str(mlx_yaml)]

    meta = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "mlx_config_path": str(mlx_yaml),
        "method": method,
        "model": model,
        "adapter_path": str(adapter_path),
        "processed_dir": str(processed_dir),
        "lora_parameters": payload["lora_parameters"],
        "train": {
            "iters": payload["iters"],
            "batch_size": payload["batch_size"],
            "learning_rate": payload["learning_rate"],
            "mask_prompt": payload["mask_prompt"],
            "max_seq_length": payload["max_seq_length"],
        },
        "command": cmd,
    }
    return cmd, adapter_path, mlx_yaml, meta


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=_DEFAULT_CONFIG,
        help="Path to training/config/lora.toml",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write mlx YAML and print the train command, then exit",
    )
    args = parser.parse_args()
    config_path = args.config.resolve()
    cfg = load_config(config_path)

    cmd, adapter_path, mlx_yaml, meta = build_command(cfg, config_path=config_path)
    print(f"Wrote mlx-lm config: {mlx_yaml}")
    print("Training command:")
    print("  " + " ".join(cmd))
    if args.dry_run:
        meta_path = adapter_path / "run_metadata.json"
        meta["dry_run"] = True
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return 0

    meta_path = adapter_path / "run_metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"\nAdapter output: {adapter_path}")
    print('Ensure deps: pip install "mlx-lm[train]"\n')
    try:
        result = subprocess.run(cmd, cwd=str(_REPO_ROOT), check=False)
    except FileNotFoundError as exc:
        raise SystemExit(
            "Could not launch mlx_lm lora. Install with:\n"
            '  pip install "mlx-lm[train]"\n'
            f"Original error: {exc}"
        ) from exc

    meta["exit_code"] = result.returncode
    meta["finished_at"] = datetime.now(timezone.utc).isoformat()
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    if result.returncode != 0:
        raise SystemExit(result.returncode)

    print(f"\nDone. Adapter + metadata at {adapter_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
