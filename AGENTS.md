# GrabLab CMS Engineering Instructions (`AGENTS.md`)

**Repositories:** `urbanspress/grablab-cms.progress` (active development) / `urbanspress/grablab-cms.stable` (verified releases) (`C:\Development\grablab-cms`)  
**Role:** Step 2 of the GRAB Post-1.0 Ecosystem — Flagship Savvy CMS (`v1.5.0` Admin UI & Universal Profile Studio) built on **GRAB `v1.1.0`** and **Grex JS `v1.0.0`**.

---

## Core Architecture Rules
1. **Read `GRABLAB-EXPERT.md` first** before any specification or implementation edit.
2. **Keep scope strictly inside the CMS layer:** Treat `GRAB v1.1.0` (`grab` CLI, `Grisp`, `use data`, `use cache`, `server.asset`, `grab mcp`) and `Grex JS v1.0.0` (`grex.elements.json`, `createTheme`, `createClassManager`, `ForEach`, `useQuery`) as already-unlocked external runtimes. Never duplicate `grex-js` source files or core GRAB Go compiler code here.
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

### Codex Model + Effort Tiers

End every Codex turn with **Recommended Next Model & Effort Tier**. Name one exact model and effort level from the row for the next task and give the reason in one sentence. Use the second option when the first is unavailable.

| Next task | Preferred Codex tier | Alternate Codex tier |
|---|---|---|
| Stage 1, pre-implementation specifications (`*-SPEC-*.md`) and roadmaps | GPT-6.2 Sol (Medium) | GPT-6.1 Sol (Medium) |
| Stages 2 and 4, cross-layer security and contract audits and pre-release sign-offs | GPT-6.2 Astra (High) | |
| Stage 3, core multi-file implementation and unit or DOM suites | GPT-6.2 Sol (High) | GPT-6.1 Terra (High) |
| Quick UI tweaks, packaging and snapshot syncs | GPT-6 Luna (Medium) | GPT-6.1 Sol (Medium) |

---

## Mandatory Verification Gate
NEVER mark a milestone or implementation task complete until:
1. `grab check` passes on all `.grab` and `.grab.html` files with zero errors.
2. `grab format --write` (or `--check`) confirms canonical formatting.
3. All automated DOM/WCAG AA audits (`commerce_dom_audit.mjs`, `author_dom_audit.mjs`, `profile_dom_audit.mjs`) and integration/release test suites (`integration_test.py`, `commerce_test.py`, `author_test.py`, `release_v100_test.py`, `release_v110_test.py`, `release_v140_test.py`, `release_v150_test.py`) pass **100%**.
4. For any frontend/UI design milestone, the project owner has inspected live preview / Light & Dark screenshots and given explicit **Visual Approval** before any `git commit`, `git tag`, or `git push`.

---

## Frontend & UI Design Standards (`ADR-027c`)
- **Universal profile.** All four authenticated roles share six vertical tabs on `/admin/profile`: My Profile, Security, Notifications, Billing & Subscriptions, Data Export, and Delete Account. Each selected panel uses the responsive card grid. The two-tier admin header stays sticky. The cards expand in place without an internal scrollbar.
- **Header navigation.** Keep visible text on every menu link. Posts and Pages are the two owner-approved exceptions with decorative WordPress-style SVGs. The viewer menu contains only the text link to Profile.
- **Strict Pure `Grex JS v1.0.0` & WCAG AA Lock:** Zero `div`, zero `innerHTML` writes, zero `eval()`, zero React/Tailwind bloat, full keyboard navigation (`Tab`, `Enter`, `Space`, `Arrow` keys, `Escape` focus restoration), ARIA roles, and Light + Dark WCAG AA `>= 4.5:1` contrast.
- **SemVer Tier & Human Visual Approval Gate:** Every frontend/UI design release MUST ship as a **`MINOR` (`1.x.0`)** SemVer release (`ADR-027c`) and MUST pause for **Owner Visual Approval** before permanent commit, tag, or push to `origin` or `stable`.

---

## Two-Repository Workflow & Release Protection
- **Repository Roles:**
  - `origin` (`https://github.com/urbanspress/grablab-cms.progress.git`): Active development repository for ongoing work, specifications, and in-progress milestone commits.
  - `stable` (`https://github.com/urbanspress/grablab-cms.stable.git`): Production release repository for 100% verified milestone releases only.
- **Strict `stable` Protection:** All AI agents and models MUST push work-in-progress commits, drafts, and specs ONLY to `origin` (`urbanspress/grablab-cms.progress`). Pushing to `stable` (`urbanspress/grablab-cms.stable`) is strictly forbidden unless the milestone is 100% `Complete` in `docs/ROADMAP.md`, all verification gates pass 100%, and `HANDOFF.md` records no pending milestone tasks.
- **Synchronized Releases & Assets:** Whenever a completed milestone (`v0.1.0`, `v0.2.0`, …, `v1.0.0`, `v1.0.1`, …) is promoted to `stable`, push `main` and annotated version tags in ascending chronological order to both `origin` and `stable`, generate the plain-English walkthrough PDF (`docs/releases/pdf/GrabLab-<tag>-Guide.pdf`), and publish/attach matching GitHub Releases and assets to **both** repositories (`urbanspress/grablab-cms.progress` and `urbanspress/grablab-cms.stable`).
- Do not commit, push, or tag a release without explicit owner approval.

### SemVer (MAJOR.MINOR.PATCH) & Release Compatibility Matrix Standard
1. **Strict `MAJOR.MINOR.PATCH` Semantic Versioning (`ADR-027c`):**
   - **`1.0.x` (`PATCH`):** Strictly for non-breaking bug fixes, security hardening, documentation polish, and cross-layer audit patches (`100%` drop-in compatible).
   - **`1.x.0` (`MINOR`):** For backwards-compatible new features, additive standard library/runtime capabilities, or new MCP/CMS/Builder endpoints.
   - **`2.0.0` (`MAJOR`):** Reserved for breaking architectural or contract changes—**never used without explicit project-owner approval (`ADR-027c`)**.
2. **Mandatory Release Compatibility Badge & Matrix Block:**
   - Every GitHub Release (`v1.0.1`, `v1.1.0`, etc.) across both `.progress` and `.stable` repositories MUST display at the top of its release notes:
     1. A **Release Type & Affected Layers** summary callout (`PATCH (v1.0.x)` vs. `MINOR (v1.x.0)`, which layer(s) changed, and whether any neighboring layer requires an upgrade).
     2. An **Ecosystem Compatibility Matrix** Markdown table covering all five layers:

````markdown
### Release Type & Affected Layers
- **Release Version & SemVer Tier:** `v<X.Y.Z>` (`PATCH 1.0.x — Non-Breaking Bug/Security/Audit Patch` | `MINOR 1.x.0 — Backwards-Compatible Feature Release`)
- **Affected Layer(s):** `<Layer Name>` (`urbanspress/<repo>`)
- **Neighboring Layer Upgrade Required?** `No — 100% drop-in compatible` (or explicit version requirement if `Yes`)

| Ecosystem Layer | Repository | Required Version Range | Touched in This Release? | Neighbor Upgrade Required? |
|---|---|---|---|---|
| **Core Language, Bytecode VM & Grisp Server** | `urbanspress/grab` | `>= v1.1.0 (< v2.0.0)` | `Yes` / `No` | `No` |
| **Reactive Frontend Runtime & 20-Element Library** | `urbanspress/grex-js` | `>= v1.0.0 (< v2.0.0)` | `Yes` / `No` | `No` |
| **Flagship Zero-Plugin CMS** | `urbanspress/grablab-cms` | `>= v1.0.1 (< v2.0.0)` | `Yes` / `No` | `No` |
| **Exclusive `mode: "visual"` Theme & Studio** | `urbanspress/grex-builder` | `>= v1.0.0 (< v2.0.0)` | `Yes` / `No` | `No` |
| **Autonomous Design, Content & SEO Agent** | `urbanspress/groxy-ai` | `>= v0.1.0` | `Yes` / `No` | `No` |
````

### Mandatory Milestone Snapshot Rule
- **Ecosystem Snapshot Sync:** At the end of every milestone (before closing the milestone or pushing release promotions), every agent MUST run:
  ```powershell
  powershell -ExecutionPolicy Bypass -File C:\Development\GRAB\scripts\sync-notebook-sources.ps1
  ```
  so `C:\Development\ECOSYSTEM-SNAPSHOT.md` always reflects the latest Git branches, commits, tags, `AGENTS.md`, `*-EXPERT.md`, `HANDOFF.md`, `docs\ROADMAP.md`, and `specifications\*.md` across all discovered `C:\Development\*` repositories.

---

## Tandem Handoff Protocol
- **Google Antigravity <-> OpenAI Codex:**
  - If an issue remains unresolved after 2 attempts on `Google Hydrogen (Extra)` (or equivalent frontier tier), stop editing, revert only the failed attempt's files (never overwrite pre-existing uncommitted work), record what was tried in `HANDOFF.md`, update `Current Owner` in `HANDOFF.md`, and report readiness to hand off.
  - On pickup (`use-antigravity` or `use-codex`), immediately read `GRABLAB-EXPERT.md`, `AGENTS.md`, and `HANDOFF.md`, verify baseline checks, and continue the next pending task.
