# Changelog

All notable releases of **GrabLab CMS** (`urbanspress/grablab-cms`) are documented in this file.

## `[v1.0.0]` — 2026-11-14 (Production CMS Release)

### Added
- **Stability & Hardening Freeze (`specifications/GRABLAB-SPEC-100.md`):** Froze all `v1.x` public CMS contracts, including `001`–`003` database schemas across SQLite, PostgreSQL, and MariaDB; `theme.json` Exclusive Active Theme manifests (`mode: "coded"` and `mode: "visual"`); native Hooks & Filters API (`registerHook`, `runHook`, `registerFilter`, `applyFilter`); `query_entries` (`filter_by_term`) and `use cache` invalidation keys; the 6 `grab mcp` CMS tool schemas; and the `--read-only` container deployment profile.
- **End-to-End Production Release Suite (`tests/release_v100_test.py`):** Verified fresh empty-DB installs (`001 -> 002 -> 003` and direct `003`), PostgreSQL/MariaDB schema parity, idempotent `seed.grab`, `/setup` admin bootstrap lock, custom content types + `GrabDecimal` precision, isolated media uploads, hierarchical taxonomies & tags, `301` slug rename history + dynamic navigation menu permalink updates, query caching + deterministic invalidation, `grab mcp` `1.0.0` draft enforcement & WCAG `422` checks, exclusive `coded` <-> `visual` theme switching, repo-wide `grab check` + canonical `grab format`, and zero wrapper-`<div>` template/admin HTML validation.
- **Hardened `--read-only` Production Deployment Bundle (`deploy/docker-compose.yml`, `deploy/README.md`):** Added Docker Compose and Grisp deployment templates demonstrating `read_only: true` (`--read-only`), `--allow-scripts`, `--allow-env`, `--allow-write`, `--allow-read`, `--allow-db`, `--allow-cache`, `--workers` scaling options, and scoped writable volume mounts for `storage/`, `uploads/`, and `/static/grex/` (`public/grex`) with zero hardcoded secrets or production IPs.
- **Plain-English Release Guide (`docs/releases/pdf/GrabLab-v1.0.0-Guide.pdf`):** Generated production walkthrough guide (`docs/releases/generate_v100_guide.py` & HTML source).

### Changed
- Updated runtime generator metadata, login badge, seed banner, and `grab mcp` `initialize` server version metadata from pre-`1.0` tags to `v1.0.0` / `1.0.0`.
- Updated `docs/ROADMAP.md`, `HANDOFF.md`, and `README.md` to mark **GrabLab CMS `v1.0.0`** `Complete`.

---

## `[v0.4.0]` — 2026-11-14

- Added Media Library safe binary upload pipeline (`crypto.random_hex` filenames under `--allow-write`, magic-byte sniffing, PNG/JPEG/WebP/GIF pixel dimensions, SVG/executable/path-traversal rejection, mandatory `alt_text`/`is_decorative` `422` validation, `nosniff`, `CSP: default-src 'none'`, immutable `ETag` serving).
- Added hierarchical Navigation Menus (`primary`, `footer`, `mobile`) with dynamic permalink resolution when entry slugs change and semantic `<nav><ul><li><a>` markup.
- Added Taxonomies & Terms (`category` hierarchical, `post_tag` flat, custom taxonomies with reserved-prefix `409` protection, `/category/:slug`, `/tag/:slug`, and `/<archive_slug>/:slug` routes, `query_entries` `filter_by_term` + `use cache` epoch invalidation).
- Added capability-gated `grab mcp` CMS tools (`list_content_types`, `query_entries`, `create_entry_draft` draft enforcement, `update_entry_layout` with `grex.elements.json` & WCAG AA `422` checks, `list_media`, `list_menus`).
- Generated `docs/releases/pdf/GrabLab-v0.4.0-Guide.pdf`.

## `[v0.3.0]` — 2026-11-14

- Added users, sessions, and RBAC (`admin`, `editor`, `author`, `viewer`) with `/setup` first-admin lock, `use crypto` `argon2id` password hashing, `HttpOnly` + `SameSite=Lax` session rotation, `cache.limit` brute-force protection, and `X-CSRF-Token` validation.
- Added disabled-by-default OAuth2/PKCE (`S256` + `state`) login toggles (`GRABLAB_MASTER_KEY` AES-256-GCM secret storage).
- Added CSRF-protected Grex JS `v1.0.0` Admin Dashboard (`--allow-scripts`, zero wrapper `<div>` elements) and 1-click Exclusive Active Theme switcher (`mode: "coded"` <-> `mode: "visual"`).
- Generated `docs/releases/pdf/GrabLab-v0.3.0-Guide.pdf`.

## `[v0.2.0]` — 2026-11-13

- Added Exclusive Active Theme Engine (`theme.json` manifest validation, `GRAB-E401` plugin/archive security checks, coded `.grab.html` and visual `grex.elements.json` modes), template parts (`header`, `footer`, `card`, `sidebar`), native core-and-theme-scoped Hooks & Filters API, and prepared-SQL `query_entries` + `use cache` invalidation.
- Generated `docs/releases/pdf/GrabLab-v0.2.0-Guide.pdf`.

## `[v0.1.0]` — 2026-11-13

- Bootstrapped GrabLab CMS core (`src/app.grab`), SQLite/PostgreSQL/MariaDB `001` migrations, custom content types and custom fields (`GrabDecimal`/`GrabInteger` fidelity), pretty permalinks, `301` slug history redirects, and the `default-starter` theme.
- Generated `docs/releases/pdf/GRABLAB-v0.1.0-Guide.pdf`.
