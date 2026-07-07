# Personal Reply Agent

A local macOS menubar app that learns how you write from WhatsApp chat exports, then suggests style-matched replies while you chat in WhatsApp Web.

Everything runs locally: **LanceDB** for vector search, **Ollama** for embeddings and generation, **Playwright** to read the active browser thread.

## Status

Early scaffolding. See [PLAN.md](PLAN.md) for architecture and phased delivery. Track work in [TODO.md](TODO.md).

## What it does

1. Ingests your **WhatsApp `.txt` exports** and indexes messages you sent
2. On hotkey (**Cmd+Shift+R**), reads the open WhatsApp Web thread in Chrome
3. Retrieves similar past replies from LanceDB
4. Generates a suggestion via Ollama and copies it to the clipboard

Gmail support is planned for Phase 5.

## Docs

| File | Purpose |
|------|---------|
| [PLAN.md](PLAN.md) | Architecture, design decisions, phased delivery |
| [TODO.md](TODO.md) | Implementation checklist |

## Quick start (once implemented)

```bash
# Install (coming in Phase 1)
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Pull Ollama models
ollama pull nomic-embed-text
ollama pull llama3.2

# Ingest WhatsApp export
python -m personal_reply.ingest.pipeline

# Run menubar app (Phase 3)
python -m personal_reply
```

## Privacy

All message data and embeddings stay under `data/` on your machine. No cloud APIs.
