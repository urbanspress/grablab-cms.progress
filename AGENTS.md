# GrabLab CMS Engineering Instructions (`AGENTS.md`)

**Repositories:** `urbanspress/grablab-cms.progress` (active development) / `urbanspress/grablab-cms.stable` (verified releases) (`C:\Development\grablab-cms`)  
**Role:** Step 2 of the GRAB Post-1.0 Ecosystem — Flagship Savvy CMS built on **GRAB `v1.0.1`** and **Grex JS `v1.0.0`**.

---

## Core Architecture Rules
1. **Read `GRABLAB-EXPERT.md` first** before any specification or implementation edit.
2. **Keep scope strictly inside the CMS layer:** Treat `GRAB v1.0.1` (`grab` CLI, `Grisp`, `use data`, `use cache`, `server.asset`, `grab mcp`) and `Grex JS v1.0.0` (`grex.elements.json`, `createTheme`, `createClassManager`, `ForEach`, `useQuery`) as already-unlocked external runtimes. Never duplicate `grex-js` source files or core GRAB Go compiler code here.
3. **Zero-Plugin Core + Exclusive Active Theme:** Never introduce a third-party plugin loader. Only one theme may be active at a time, owning 100% of template rendering (`home`, `single`, `archive`, `header`, `footer`, `404`, `search`).
4. **Spec-First Approval Gate:** Do NOT write `GrabLab` application code until the active milestone specification (starting with `specifications/GRABLAB-SPEC-001.md`) is explicitly approved by the project owner.

---

## User Communication
- The project owner is a non-coder directing development in plain English. Always explain changes, errors, and design choices simply.
- Handle all file edits and terminal commands directly; do not ask the project owner to perform routine coding or command-line work.

---

## Model Routing & Effort Levels
Advise the project owner which Antigravity model and effort level to select for the next step so AI Pro quota is used efficiently:
- **`Google Hydrogen (Medium)`:** Pre-implementation specifications (`*-SPEC-*.md`), documentation, governance updates, and single-module edits.
- **`Google Hydrogen (High)`:** Standard feature milestone implementations (`v0.4.0`, `v1.0.0` build & release).
- **`Orchestrator (Argon)`:** Second-opinion pre-`v1.0.0` security/DOM/contract audits, multi-repo cross-layer integrations, and complex refactors where Argon-level planning + automated delegation saves tokens.
- **`Google Hydrogen (Extra)`:** Reserved for autonomous AI engines (`Groxy AI`), multi-server orchestration (`Gashboard + Grabtaculous + grabman`), and stubborn cross-layer bugs.
- **Mandatory Pause & Swap Prompt Rule:** Every active AI agent MUST pause at milestone boundaries or before high-risk cross-layer/pre-`v1.0.0` audits and explicitly tell the user when to switch to `Orchestrator (Argon)`, including a clear 1-sentence reason why `Orchestrator (Argon)` is recommended next.

---

## Mandatory Verification Gate
NEVER mark a milestone or implementation task complete until:
1. `grab check` passes on all `.grab` and `.grab.html` files with zero errors.
2. `grab format --write` (or `--check`) confirms canonical formatting.
3. All automated integration tests (routing, 301 slug history, `use data` SQLite/MariaDB/PostgreSQL contracts, `use cache` invalidation, exclusive theme switching, CSRF/XSS security) pass **100%**.

---

## Two-Repository Workflow & Release Protection
- **Repository Roles:**
  - `origin` (`https://github.com/urbanspress/grablab-cms.progress.git`): Active development repository for ongoing work, specifications, and in-progress milestone commits.
  - `stable` (`https://github.com/urbanspress/grablab-cms.stable.git`): Production release repository for 100% verified milestone releases only.
- **Strict `stable` Protection:** All AI agents and models MUST push work-in-progress commits, drafts, and specs ONLY to `origin` (`urbanspress/grablab-cms.progress`). Pushing to `stable` (`urbanspress/grablab-cms.stable`) is strictly forbidden unless the milestone is 100% `Complete` in `docs/ROADMAP.md`, all verification gates pass 100%, and `HANDOFF.md` records no pending milestone tasks.
- **Synchronized Releases & Assets:** Whenever a completed milestone (`v0.1.0`, `v0.2.0`, …, `v1.0.0`) is promoted to `stable`, push `main` and annotated version tags in ascending chronological order to both `origin` and `stable`, generate the plain-English walkthrough PDF (`docs/releases/pdf/GrabLab-<tag>-Guide.pdf`), and publish/attach matching GitHub Releases and assets to **both** repositories (`urbanspress/grablab-cms.progress` and `urbanspress/grablab-cms.stable`).
- Do not commit, push, or tag a release without explicit owner approval.

---

## Tandem Handoff Protocol
- **Google Antigravity <-> OpenAI Codex:**
  - If an issue remains unresolved after 2 attempts on `Google Hydrogen (Extra)` (or equivalent frontier tier), stop editing, revert only the failed attempt's files (never overwrite pre-existing uncommitted work), record what was tried in `HANDOFF.md`, update `Current Owner` in `HANDOFF.md`, and report readiness to hand off.
  - On pickup (`use-antigravity` or `use-codex`), immediately read `GRABLAB-EXPERT.md`, `AGENTS.md`, and `HANDOFF.md`, verify baseline checks, and continue the next pending task.
