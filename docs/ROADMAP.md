# GrabLab CMS Roadmap

**Repository:** `urbanspress/grablab-cms`  
**Platform Runtimes:** GRAB `v1.0.1` + Grex JS `v1.0.0`

**Status Labels:**
- **Draft / In Review** — Specification drafted; awaiting owner approval before code implementation.
- **Approved** — Authorized by project owner for implementation.
- **Complete** — Implemented, `grab check` clean, 100% tests passing, and walkthrough guide generated.
- **Planned** — Upcoming milestone in the GrabLab CMS sequence.

---

## `v0.1` — Core Content Types, Custom Fields, Pretty Permalinks & 301 Slug History

**Status:** Draft / In Review (`specifications/GRABLAB-SPEC-001.md`)

Scope:
- `use data` schema & migrations for `site_settings`, `content_types`, `field_definitions`, `entries`, `slug_history`, and `themes` (SQLite-first, MariaDB/PostgreSQL-compatible, exact `GrabDecimal`/`GrabInteger` types).
- Content Type & Custom Field registry (built-in `page` and `post` plus user-defined types and typed custom fields).
- WordPress-style pretty permalink router (`/:slug` and type patterns like `/blog/:slug`) with reserved system-prefix protection (`/admin`, `/api`, `/static`, `/_health`, `/_ready`) and automatic `301 Moved Permanently` redirect history on slug changes.
- `theme.json` exclusive theme manifest contract & atomic single-active-theme switching.
- `use cache` invalidation keys for entries, routes, and active theme state.

---

## `v0.2` — Exclusive Theme Engine, Template Parts, Native Hooks/Filters & Query Loop Engine

**Status:** Planned

Scope:
- **Exclusive Theme Engine:**
  - Safe coded theme import (`.grab` + `.grab.html` + `Grex JS v1.0.0` static assets via `server.asset` and `themes/<slug>/theme.json` validation).
  - First-class **Grex Visual Theme Contract** so **Step 3 (`grex-builder`)** installs as a selectable theme that disables any prior theme and takes 100% exclusive template rendering control (`home`, `single`, `archive`, `header`, `footer`, `404`, `search`).
- **Template Parts:** Reusable `header`, `footer`, `sidebar`, and partial `.grab.html` / Grex sections.
- **Native Hooks & Filters:** Deterministic core `.grab` lifecycle hooks/filters (e.g., `before_render`, `after_save_entry`, `head_meta`, `footer_scripts`) without third-party plugins.
- **Query Loop Engine:** Declarative, prepared-SQL query loops for archives, recent posts, filtered custom content types, and pagination.

---

## `v0.3` — Users, Roles/Capabilities, Auth & CSRF-Protected Admin Dashboard

**Status:** Planned

Scope:
- `users`, `sessions`, and role/capability tables (`admin`, `editor`, `author`, `viewer`) with secure password hashing and session cookies (`HttpOnly`, `SameSite=Lax`, `Secure`).
- CSRF-protected Admin Dashboard built with `.grab.html` and `Grex JS v1.0.0` reactive components (`ForEach`, `Form`, `Tabs`, `Modal`, `createTheme`).
- **1-Click Theme / Grex Switcher:** Visual Themes dashboard allowing site owners to switch between installed coded themes and the **Grex Builder** visual theme with instant atomic deactivation of the prior theme.
- Content editor, custom type/field manager, and permalink/redirect inspector.

---

## `v0.4` — Media Library, Menus, Taxonomies & `grab mcp` CMS Tools

**Status:** Planned

Scope:
- **Media Library:** Confined uploads under writable media mounts, MIME/extension allowlists, metadata (`alt`, dimensions), and cache-busted serving (`--read-only` root compatible).
- **Navigation Menus:** Ordered multi-level menu builder bound to active theme `header`/`footer` slots.
- **Taxonomies:** Categories, tags, and custom hierarchical/flat taxonomies with pretty archive permalinks.
- **`grab mcp` CMS Tools:** Schema/content-type/route inspection helpers so **Step 4 (`groxy-ai`)** can scaffold content types, entries, and Grex layouts safely.

---

## `v1.0.0` — Production CMS Release

**Status:** Planned

Scope:
- Full multi-worker **Grisp** (`--workers`) + Redis (`use cache`) + PostgreSQL/MariaDB/SQLite verification.
- Security audit (CSRF, XSS, SSRF, path traversal, capability boundaries, `--read-only` container check).
- Performance benchmarks, `grabtaculous` 1-click deployment template compatibility, and `v1.0.0` Plain-English Walkthrough PDF.
