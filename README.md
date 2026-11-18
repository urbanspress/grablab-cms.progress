# GrabLab CMS

**GrabLab CMS** is a fast, zero-plugin, security-first Content Management System built directly on **GRAB `v1.1.0`** (`use crypto`, `use env`, `use data`, `use cache`, `server.asset`, `--allow-scripts`) and **Grisp**, with native support for **Grex JS `v1.0.0`** and the upcoming **Grex Visual Theme (`grex-builder`)**.

## Why GrabLab CMS?

- **Zero-Plugin Core:** Every essential CMS feature—custom content types, custom fields, pretty permalinks, automatic 301 redirect history, authentication, roles/capabilities, optional OAuth2/PKCE social login, hooks/filters, query loops, Media Library, Navigation Menus, Taxonomies, and `grab mcp` CMS tools—lives natively in core `.grab` modules.
- **Exclusive Active Theme Architecture:** Import coded themes (`.grab` + `.grab.html` + `Grex JS v1.0.0`) or install the **Grex Theme Builder** visual theme. Exactly **one** theme is active at a time; activating a new theme via `/admin/themes` automatically deactivates the prior theme and hands 100% exclusive template rendering control (`home`, `single`, `archive`, `header`, `footer`, `404`, `search`) to the active theme.
- **Security & Speed by Default:** Native Argon2id password hashing (`use crypto`), SHA-256 hashed session tokens with `HttpOnly` + `SameSite=Lax` cookies and login rotation, `cache.limit` brute-force protection, disabled-by-default OAuth2/PKCE with AES-256-GCM encrypted secrets (`GRABLAB_MASTER_KEY`), `X-CSRF-Token` validation, magic-byte-verified uploads confined to `--allow-write uploads` with mandatory `alt` text, strict `script-src 'self'` CSP (`--allow-scripts`), capability-gated MCP tools with `grex.elements.json` + WCAG AA checks, prepared SQL (`use data`), and `--read-only` root compatibility.

## Ecosystem Position

1. **Step 1 — `grex-js v1.0.0`:** Complete (`urbanspress/grex-js.progress` / `urbanspress/grex-js.stable`)
2. **Step 2 — `grablab-cms`:** Complete (`urbanspress/grablab-cms.progress` / `urbanspress/grablab-cms.stable`) — **`v1.1.0` Zero-Plugin E-Commerce Core** (`Approved & Frozen — Complete` on `origin` and `stable`)
3. **Step 3 — Grex Theme Builder:** Complete (`urbanspress/grex-builder.progress` / `urbanspress/grex-builder.stable`) — **`v1.0.0` Installable Visual Theme & Page/Theme Studio**
4. **Step 4 — `groxy-ai`:** Ready to launch (`urbanspress/groxy-ai.progress` / `urbanspress/groxy-ai.stable`) — Autonomous MCP design & SEO agent
5. **Step 5 — `gashboard` + `grabtaculous`:** Planned (`urbanspress/gashboard.progress` / `urbanspress/gashboard.stable`) — Desktop VPS control panel & 1-click installer

## Quickstart (`v1.0.0` on `GRAB v1.1.0`)

```bash
grab migrate --db-config grab.data.json --allow-db main:migrate migrations/003_v04_schema.grab
grab run --db-config grab.data.json --allow-db main:read-write --allow-read . migrations/seed.grab
grab serve --addr 127.0.0.1:8080 --allow-scripts --db-config grab.data.json --allow-db main:read-write --platform-config grab.platform.json --allow-cache cms:read-write --allow-cache cms:limit --allow-env GRABLAB_MASTER_KEY,GRABLAB_UPLOAD_DIR,GRABLAB_MAX_UPLOAD_BYTES --allow-read . --allow-write uploads --static public --max-body-bytes 15728640 src/app.grab
```

On first launch without a bootstrap admin, open `http://127.0.0.1:8080/setup` to create the primary administrator account, then manage entries, media, menus, taxonomies, types, themes, settings, and users under `/admin`.

For production container hosting with a `--read-only` root filesystem and scoped writable `storage/`, `uploads/`, and `/static/grex/` (`public/grex/`) mounts, see [`deploy/docker-compose.yml`](deploy/docker-compose.yml) and [`deploy/README.md`](deploy/README.md).

Verify formatting, compiler checks, integration contracts, and the full `v1.0.0` clean-install E2E release suite:

```bash
python tests/integration_test.py
python tests/release_v100_test.py
python tests/commerce_test.py
python tests/release_v110_test.py
node tests/commerce_dom_audit.mjs
```

## Governance, Specifications & Release Guides

- [`GRABLAB-EXPERT.md`](GRABLAB-EXPERT.md) — Non-negotiable engineering & security invariants
- [`AGENTS.md`](AGENTS.md) — Engineering workflow, model routing, and verification gates
- [`HANDOFF.md`](HANDOFF.md) — Current ownership and milestone log
- [`CHANGELOG.md`](CHANGELOG.md) — Complete version history (`v0.1.0` → `v1.1.0`)
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — Milestone roadmap (`v0.1` → `v1.1.0` Complete, `v1.2.0` Planned)
- [`deploy/README.md`](deploy/README.md) — Hardened `--read-only` Docker Compose & Grisp deployment guide
- [`specifications/GRABLAB-SPEC-001.md`](specifications/GRABLAB-SPEC-001.md) — `v0.1.0` core architecture & schema (`Complete`)
- [`specifications/GRABLAB-SPEC-002.md`](specifications/GRABLAB-SPEC-002.md) — `v0.2.0` exclusive theme engine, template parts, hooks & query loop (`Complete`)
- [`specifications/GRABLAB-SPEC-003.md`](specifications/GRABLAB-SPEC-003.md) — `v0.3.0` users, roles/capabilities, auth, OAuth2/PKCE & Grex admin (`Complete`)
- [`specifications/GRABLAB-SPEC-004.md`](specifications/GRABLAB-SPEC-004.md) — `v0.4.0` media library, navigation menus, taxonomies & `grab mcp` CMS tools (`Complete`)
- [`specifications/GRABLAB-SPEC-100.md`](specifications/GRABLAB-SPEC-100.md) — `v1.0.0` Production `v1.x` Stability & Hardening Freeze (`Approved & Frozen`)
- [`specifications/GRABLAB-SPEC-110.md`](specifications/GRABLAB-SPEC-110.md) — `v1.1.0` Zero-Plugin E-Commerce Core (`Approved & Frozen — Complete`)
- [`docs/releases/pdf/GrabLab-v1.0.0-Guide.pdf`](docs/releases/pdf/GrabLab-v1.0.0-Guide.pdf) — Plain-English `v1.0.0` Production Walkthrough Guide for site owners, designers, and operators
- [`docs/releases/pdf/GrabLab-v1.0.1-Guide.pdf`](docs/releases/pdf/GrabLab-v1.0.1-Guide.pdf) — Plain-English `v1.0.1` Pre-Step-4 Cross-Layer Audit & Patch Guide
- [`docs/releases/pdf/GrabLab-CMS-v1.1.0-Guide.pdf`](docs/releases/pdf/GrabLab-CMS-v1.1.0-Guide.pdf) — Plain-English `v1.1.0` Zero-Plugin E-Commerce Core Walkthrough Guide
