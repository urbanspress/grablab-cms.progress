# GrabLab CMS

**GrabLab CMS** is a fast, zero-plugin, security-first Content Management System built directly on **GRAB `v1.0.1`** and **Grisp**, with native support for **Grex JS `v1.0.0`** and the upcoming **Grex Visual Theme (`grex-builder`)**.

## Why GrabLab CMS?

- **Zero-Plugin Core:** Every essential CMS feature—custom content types, custom fields, pretty permalinks, automatic 301 redirect history, media library, roles/capabilities, menus, hooks/filters, and query loops—lives natively in core `.grab` modules. No third-party plugin bloat or mystery shortcodes.
- **Exclusive Active Theme Architecture:** Import coded themes (`.grab` + `.grab.html` + `Grex JS v1.0.0`) or install the **Grex Theme Builder** visual theme. Exactly **one** theme is active at a time; activating a new theme automatically deactivates the prior theme and hands 100% exclusive template rendering control (`home`, `single`, `archive`, `header`, `footer`, `404`, `search`) to the active theme.
- **Security & Speed by Default:** Built on GRAB 1.0's prepared SQL (`use data`), Redis/memory caching (`use cache`), in-memory SHA-256 asset fingerprinting (`server.asset`), context-aware `.grab.html` escaping, and `--read-only` container compatibility.

## Ecosystem Position

1. **Step 1 — `grex-js v1.0.0`:** Complete (`urbanspress/grex-js`)
2. **Step 2 — `grablab-cms`:** Active (`urbanspress/grablab-cms`) — **`v0.1.0` Complete** (`v0.2.0` planned)
3. **Step 3 — `grex-builder`:** Planned (`urbanspress/grex-builder`) — Installable Visual Theme & Page/Theme Studio
4. **Step 4 — `groxy-ai`:** Planned (`urbanspress/groxy-ai`) — Autonomous MCP design & CMS agent
5. **Step 5 — `gashboard` + `grabtaculous`:** Planned (`urbanspress/gashboard`) — Desktop VPS control panel & 1-click installer

## Quickstart (`v0.1.0`)

```bash
grab migrate --config grab.data.json
grab run migrations/seed.grab --config grab.data.json
grab serve --platform-config grab.platform.json src/app.grab
```

Verify formatting, type checks, and the full HTTP/database integration suite:

```bash
python tests/integration_test.py
```

## Governance, Specifications & Release Guides

- [`GRABLAB-EXPERT.md`](GRABLAB-EXPERT.md) — Non-negotiable engineering & security invariants
- [`AGENTS.md`](AGENTS.md) — Engineering workflow, model routing, and verification gates
- [`HANDOFF.md`](HANDOFF.md) — Current ownership and pending milestone tasks
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — Milestone roadmap (`v0.1` → `v1.0.0`)
- [`specifications/GRABLAB-SPEC-001.md`](specifications/GRABLAB-SPEC-001.md) — `v0.1.0` architecture & schema specification (`Complete`)
- [`docs/releases/pdf/GRABLAB-v0.1.0-Guide.pdf`](docs/releases/pdf/GRABLAB-v0.1.0-Guide.pdf) — Plain-English `v0.1.0` walkthrough guide for site owners and designers
