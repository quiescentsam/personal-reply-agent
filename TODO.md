# TODO — Personal Reply Agent

Implementation checklist. See [PLAN.md](PLAN.md) for architecture and phase details.

---

## Phase 1 — WhatsApp RAG foundation

- [x] **scaffold** — Create `pyproject.toml`, `config.toml`, and `src/personal_reply/` package layout
- [x] **ingest** — Build WhatsApp `.txt` parser; extract user-sent messages with `context_before` metadata
- [x] **rag-store** — Implement LanceDB store + Ollama embedding client + vector search retrieval
- [x] **llm-reply** — Build prompt template and Ollama chat client for style-matched replies
- [x] **cli** — Add `python -m personal_reply suggest --text "..."` for testing without browser

---

## Phase 2 — WhatsApp browser reader

- [x] **browser-connector** — Playwright CDP connector to existing Chrome (`port 9222`)
- [x] **browser-whatsapp** — WhatsApp Web DOM adapter (thread read + compose selector)
- [x] **launch-script** — `scripts/launch_chrome_debug.sh`
- [x] **cli-browser** — `personal_reply suggest --from-browser`

---

## Phase 3 — Menubar app

- [x] **menubar** — rumps tray app with **Suggest Reply**, **Re-ingest**, **Settings**, **Quit**
- [x] **hotkey** — Global **Cmd+Shift+R** via `pynput`
- [x] **clipboard** — Auto-copy suggestion + notification on success
- [x] **docs** — First-run guide: Chrome debug setup, WhatsApp export instructions

---

## Phase 4 — WhatsApp polish (optional)

- [x] **insert-reply** — Type suggestion into WhatsApp compose box via Playwright
- [x] **reopen-mode** — Draft fresh openers when thread is stale or your message was last
- [x] **research-subagent** — Web search for weather, sports, news; main agent auto-invokes from conversation
- [ ] **re-ingest** — Background or menu-triggered re-ingest of new exports
- [x] **per-contact** — Contact tags with blended affinity scoring (direct contact weighted higher)

---

## Phase 5 — Gmail support

- [ ] **gmail-ingest** — Gmail mbox parser + pipeline integration
- [ ] **gmail-browser** — Gmail DOM adapter (same `ThreadContext` interface)
- [ ] **gmail-retrieval** — Platform-aware search when on Gmail tab
- [ ] **gmail-menubar** — Accept Gmail tabs alongside WhatsApp Web

---

## Progress

| ID | Task | Status |
|----|------|--------|
| scaffold | Project structure + config | done |
| ingest | WhatsApp `.txt` parser | done |
| rag-store | LanceDB + Ollama embeddings | done |
| llm-reply | Prompt + Ollama chat | done |
| cli | Text-only suggest command | done |
| browser | CDP + WhatsApp adapter | done |
| menubar | Tray app + hotkey | done |
| docs | Setup guide in README | done |
| gmail | Gmail ingest + browser (Phase 5) | pending |

**Repo bootstrap:** README, PLAN, TODO, `.gitignore` — done.
