# Training — LoRA / QLoRA style adapter

Standalone offline workflow to fine-tune a small MLX instruct model on your WhatsApp reply style.

**Does not change the personal_reply app.** The menubar / RAG / Ollama path is untouched. Adapters produced here are not wired into suggest yet.

## Layout

```
training/
├── README.md
├── PLAN.md
├── config/lora.toml          # model, LoRA, train hyperparams, paths
├── scripts/
│   ├── prepare_dataset.py    # WhatsApp .txt → train.jsonl + valid.jsonl
│   ├── train_lora.py         # MLX LoRA / QLoRA via mlx_lm.lora
│   └── eval_samples.py       # side-by-side gold vs model on valid set
└── data/
    ├── raw/                  # drop WhatsApp Chat with *.txt here
    ├── processed/            # train.jsonl, valid.jsonl
    └── adapters/<run-name>/  # LoRA weights + run metadata
```

`valid.jsonl` (not `val.jsonl`) is required by mlx-lm.

## Setup

From the repo root on Apple Silicon (Python 3.11+). This is a [uv](https://docs.astral.sh/uv/) project — use the project environment, not a hand-rolled venv/`pip`.

```bash
uv sync --native-tls
uv pip install "mlx-lm[train]" --native-tls
```

`mlx-lm` is only needed for training/eval, not for the menubar app.

## Workflow

Run everything from the repo root with `uv run` so the project env is used.

1. Put WhatsApp `.txt` exports in `training/data/raw/` (or override with `--raw-dir`).
2. Edit `training/config/lora.toml` if needed (`sender_names` must match your name in the exports — e.g. `Sameer`).
3. Build the dataset:

```bash
uv run python training/scripts/prepare_dataset.py
# equivalent explicit path:
uv run python training/scripts/prepare_dataset.py --raw-dir training/data/raw
```

4. Train (LoRA by default; set `use_qlora = true` in config for a 4-bit base):

```bash
uv run python training/scripts/train_lora.py
# or preview:
uv run python training/scripts/train_lora.py --dry-run
```

5. Qualitative eval (after training):

```bash
# gold vs trained only
uv run python training/scripts/eval_samples.py --n 8

# gold vs untrained base vs trained (best for before/after comparison)
uv run python training/scripts/eval_samples.py --n 8 --compare-base

# untrained base only (before you train, or sanity check)
uv run python training/scripts/eval_samples.py --n 8 --base-only
```


Each sample prints **context**, **gold** (your real reply), then **untrained base** and/or **trained** so you can judge style match by eye.
## Config notes

| Key | Meaning |
|-----|---------|
| `model.model` | MLX instruct base for LoRA (default Qwen2.5-0.5B bf16) |
| `model.qlora_model` + `use_qlora = true` | 4-bit base → QLoRA |
| `lora.rank` / `scale` / `dropout` | LoRA hyperparameters (mlx-lm `lora_parameters`) |
| `train.iters` | Training steps |
| `train.mask_prompt` | Loss on assistant tokens only |
| `paths.run_name` | Adapter folder name under `data/adapters/` |

## WhatsApp export format assumptions

Standalone parser (duplicated on purpose — no import from `src/personal_reply`):

- Lines like `[1/15/24, 10:30:45 AM] Name: message` or `1/15/24, 10:30 - Name: message`
- Your messages attributed to names in `dataset.sender_names` (default `You`)
- Contact inferred from filename (`WhatsApp Chat with Alice.txt` → `Alice`)
- Media-only / deleted placeholders are dropped
- Each example: 1–3 prior messages as user context → your reply as assistant

## Memory tips

- Default base is **Qwen2.5-0.5B** for fast Mac iteration; bump to 1.5B/3B later if style quality plateaus.
- If LoRA OOM: set `use_qlora = true`, `batch_size = 1`, lower `max_seq_length`, or enable `grad_checkpoint`.
- Small corpora (<50 examples): keep rank and iters low to avoid memorization.
