# Personal Reply Agent

A local macOS menubar app that learns how you write from WhatsApp chat exports, then suggests style-matched replies while you chat in WhatsApp Web.

Everything runs locally: **LanceDB** for vector search, **Ollama** for embeddings and generation, **Playwright** to read the active browser thread.

## Status

Phase 1–3 are in place: WhatsApp ingest, LanceDB RAG, browser-based suggest via Chrome CDP, and a macOS menubar app with global hotkey. See [TODO.md](TODO.md).

## What it does

1. Ingests your **WhatsApp `.txt` exports** and indexes messages you sent
2. On hotkey (**Cmd+Shift+R**), reads the open WhatsApp Web thread in Chrome
3. Retrieves similar past replies from LanceDB
4. Generates a suggestion via Ollama. For active threads it replies; for stale threads it drafts a fresh opener, then types it into WhatsApp compose (and copies to clipboard).

Gmail support is planned for Phase 5.

## Docs

| File | Purpose |
|------|---------|
| [PLAN.md](PLAN.md) | Architecture, design decisions, phased delivery |
| [TODO.md](TODO.md) | Implementation checklist |

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium

# Pull Ollama models
ollama pull nomic-embed-text
ollama pull llama3.2

# Ingest WhatsApp export (shows step-by-step logs)
python -m personal_reply ingest

# List indexed contacts
python -m personal_reply contacts

# Phase 2: agent debug Chrome (separate from your daily Chrome)
# 1. Keep using your normal Chrome as usual
# 2. Launch the agent's debug Chrome (own profile, port 9222)
./scripts/launch_chrome_debug.sh
# 3. Log into WhatsApp Web once in the debug Chrome window, select a chat
python -m personal_reply suggest --from-browser --verbose
python -m personal_reply suggest --from-browser --research --verbose

# Manual mode (no browser)
python -m personal_reply suggest --contact "Papa New" --text "Kahan ho?" --verbose

# Phase 3: menubar app (no args launches tray icon)
python -m personal_reply
python -m personal_reply --verbose   # log RAG + prompt to terminal on each suggest
# Or: personal-reply-menubar
```

### Menubar app

1. Start Ollama and the agent's debug Chrome (`./scripts/launch_chrome_debug.sh`). Your regular Chrome can stay open.
2. Launch the tray app: `python -m personal_reply`
3. Open a WhatsApp Web chat in debug Chrome.
4. Press **Cmd+Shift+R** or choose **Suggest Reply** from the menu.
5. For timely topics (weather, sports, news), choose **Research & Suggest** instead.
6. The suggestion is typed into the WhatsApp compose box (and copied to clipboard). Press Enter to send.

**Stale threads:** If the last activity is older than `stale_after_hours` (default 48h), or your message was last, the agent drafts a **new conversation opener** instead of answering old messages. Re-ingest after upgrading so opener examples are indexed (`message_kind = reopen`).

**Contact tags:** Add shared style groups under `[contacts.tags]` in `config.toml` (e.g. `parent`, `family`, `friend`). RAG searches all tagged contacts together and ranks the active chat higher (`contact_match_weight`) while same-tag contacts contribute at `category_match_weight` (default 0.65).

**Web research subagent:** With `research.auto = true` (default), the main agent reads the thread and decides whether to search the web for timely topics (weather, sports, news) before drafting. Use `--research` or menubar → **Research & Suggest** to force research every time. Configure under `[research]` in `config.toml`.

**macOS permissions:** On first launch the app requests **Accessibility** via a system dialog. If Cmd+Shift+R still does not work, use menu → **Enable Hotkey** — it re-prompts and opens **System Settings → Privacy & Security → Accessibility**. Enable **Python** (and **Terminal** or **Cursor** if listed), then choose **Enable Hotkey** again.

**Settings:** Opens `config.toml` in your default editor and shows current model paths.

```bash
# Re-ingest from CLI (also available in menubar)
python -m personal_reply ingest
```

## Privacy

All message data and embeddings stay under `data/` on your machine. No cloud APIs.
