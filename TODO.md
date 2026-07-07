# TODO — Personal Reply Agent

Implementation checklist. See [PLAN.md](PLAN.md) for architecture and phase details.

---

## Phase 1 — WhatsApp RAG foundation

- [ ] **scaffold** — Create `pyproject.toml`, `config.toml`, and `src/personal_reply/` package layout
- [ ] **ingest** — Build WhatsApp `.txt` parser; extract user-sent messages with `context_before` metadata
- [ ] **rag-store** — Implement LanceDB store + Ollama embedding client + vector search retrieval
- [ ] **llm-reply** — Build prompt template and Ollama chat client for style-matched replies
- [ ] **cli** — Add `personal_reply.cli suggest --text "..."` for testing without browser

---

## Phase 2 — WhatsApp browser reader

- [ ] **browser-connector** — Playwright CDP connector to existing Chrome (`port 9222`)
- [ ] **browser-whatsapp** — WhatsApp Web DOM adapter (thread read + compose selector)
- [ ] **launch-script** — `scripts/launch_chrome_debug.sh`
- [ ] **cli-browser** — `personal_reply.cli suggest --from-browser`

---

## Phase 3 — Menubar app

- [ ] **menubar** — rumps tray app with **Suggest Reply**, **Re-ingest**, **Settings**, **Quit**
- [ ] **hotkey** — Global **Cmd+Shift+R** via `pynput`
- [ ] **clipboard** — Auto-copy suggestion + notification on success
- [ ] **docs** — First-run guide: Chrome debug setup, WhatsApp export instructions

---

## Phase 4 — WhatsApp polish (optional)

- [ ] **insert-reply** — Type suggestion into WhatsApp compose box via Playwright
- [ ] **re-ingest** — Background or menu-triggered re-ingest of new exports
- [ ] **per-contact** — Weight retrieval by contact (casual vs formal)

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
| scaffold | Project structure + config | pending |
| ingest | WhatsApp `.txt` parser | pending |
| rag-store | LanceDB + Ollama embeddings | pending |
| llm-reply | Prompt + Ollama chat | pending |
| browser | CDP + WhatsApp adapter | pending |
| menubar | Tray app + hotkey | pending |
| docs | Setup guide in README | pending |
| gmail | Gmail ingest + browser (Phase 5) | pending |

**Repo bootstrap:** README, PLAN, TODO, `.gitignore` — done.
