# GRABLAB-SPEC-100: Production `v1.0.0` Stability & Hardening Freeze

**Status:** Approved & Frozen for `v1.0.0` Release  
**Milestone:** `v1.0.0` — Production CMS Release  
**Runtime Baseline:** GRAB `v1.0.1`+ (verified on `GRAB 1.1.0` CLI / Grisp HTTP Engine) & Grex JS `v1.0.0`  
**Owner:** Project Owner (`urbanspress/grablab-cms`)

---

## 1. Purpose & Stability Guarantee

`GRABLAB-SPEC-100` freezes all public contracts of **GrabLab CMS `v1.x`** across database migrations, theme manifests, native hooks/filters, content querying, `grab mcp` AI authoring tools, and hardened `--read-only` container deployment.

No breaking changes to the contracts frozen in this specification are permitted within the `v1.x` release line:
1. Core remains **zero-plugin**; extensibility is delivered strictly through the **Exclusive Active Theme** model and core-approved declarative hooks/filters.
2. All semantic HTML in both starter themes and Admin UI enforces **zero wrapper `<div>` bloat** and semantic elements (`<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<aside>`, `<footer>`).
3. Financial/numeric custom fields with type `decimal` preserve **exact string precision** via `GrabDecimal` (never binary floats).
4. All container deployments run with an immutable application layer (`--read-only` root filesystem) and strictly scoped writable storage mounts.

---

## 2. Frozen Database Schema Contract (`001`–`003`)

GrabLab CMS supports **SQLite**, **PostgreSQL**, and **MariaDB** via `grab.data.json` and cumulative `data.migrate` scripts in `migrations/`:

| Migration File | Schema Version(s) | Engine Target | Frozen Tables & Indexes |
|---|---|---|---|
| `migrations/001_schema.grab` | `[1]` | SQLite (primary) / Core relational layout | Tables: `site_settings`, `content_types`, `field_definitions`, `entries`, `slug_history`, `themes`. Indexes: `idx_field_definitions_type`, `idx_entries_type_status`, `idx_slug_history_entry`. |
| `migrations/002_auth_schema.grab` | `[1, 2]` | SQLite + Auth/RBAC extension | Adds tables: `users`, `sessions`, `oauth_accounts`. Alters `entries` adding `author_id`. Indexes: `idx_sessions_user`, `idx_sessions_expires`, `idx_oauth_user`, `idx_entries_author`. |
| `migrations/003_v04_schema.grab` | `[1, 2, 3]` | SQLite (production complete) | Adds tables: `media`, `menus`, `menu_items`, `taxonomies`, `terms`, `entry_terms`. Indexes: `idx_media_uploader`, `idx_media_mime`, `idx_menus_location`, `idx_menu_items_menu`, `idx_terms_tax`, `idx_entry_terms_term`. |
| `migrations/003_v04_schema_postgres.grab` | `[1, 2, 3]` | PostgreSQL (`grablab_v04_cms_schema_postgres`) | Parity schema across versions `1`–`3` with PostgreSQL native types (`BIGSERIAL`, `TIMESTAMPTZ`, `TEXT`, `INTEGER`). |
| `migrations/003_v04_schema_mariadb.grab` | `[1, 2, 3]` | MariaDB (`grablab_v04_cms_schema_mariadb`) | Parity schema across versions `1`–`3` with MariaDB native types (`BIGINT AUTO_INCREMENT`, `VARCHAR`, `LONGTEXT`, `InnoDB`). |

### Migration Guarantees
- **Incremental & Direct Fresh Install:** Running `001` → `002` → `003` sequentially produces the identical final schema as running `003` directly against an empty database.
- **Idempotent Seed (`migrations/seed.grab`):** Seeds starter settings, `post` and `page` system content types (with `subtitle` and `reading_minutes` custom fields), starter entries (`/about`, `/blog/hello-world`), `default-starter` active theme, `category` (including `uncategorized`) and `post_tag` taxonomies, and the `main-nav` primary navigation menu without duplicating rows when executed repeatedly.
- **One-Time `/setup` Bootstrap:** An uninitialized database locks public admin creation after the first `admin` account is created via `/setup` (supporting `argon2id` password hashing).

---

## 3. Frozen `theme.json` Exclusive Active Theme Manifest

Exactly one theme may be active at any time (`site_settings` active theme + single active theme invariant). Switching themes via `POST /api/themes/activate` or `POST /api/admin/themes/activate` (`themes:manage` + CSRF token) atomically updates the active theme and invalidates all rendered/query caches.

### 3.1 Required & Supported Top-Level Fields
- `schemaVersion`: Must equal `"1.0.0"`.
- `slug`: Lowercase alphanumeric/hyphen identifier (`[a-z0-9-]{1,64}`), matching `themes/<slug>`.
- `name`: Human-readable theme title.
- `version`: SemVer string (e.g., `"1.0.0"`).
- `mode`: `"coded"` (filesystem `.grab.html` templates) or `"visual"` (**Grex Theme Builder** `grex.elements.json`).
- `engine`: `"coded"` or `"grex-visual"`.
- `capabilities`: Allowlist subset of:
  - `"templates"`
  - `"parts"`
  - `"hooks:theme"`
  - `"grex:visual"`
  - `"assets:static"`
- `templates` (coded mode): Must include required slots `home`, `single`, `archive`, `404` (optional `search`) referencing `.grab.html` files inside the theme directory.
- `parts` (optional): Named template partials (`header`, `footer`, `card`, `sidebar`, etc.).
- `grexElements` (visual mode): Path to Grex Elements document (defaults to `"grex.elements.json"`), validated via `validate_grex_elements_doc` across `home`, `single`, `archive`, `404` (and optional `search`/`parts`).
- `themeHooks` (optional, requires `"hooks:theme"` capability): Declarative hook bindings only.

### 3.2 Hard Security Boundaries (`GRAB-E401`)
- Third-party plugin manifests (`plugins` or arbitrary executable `hooks` keys) are **rejected with `GRAB-E401`**.
- Allowed theme hook names: `theme:head_meta`, `theme:before_render`, `query:modify_args`, `content:before_save`.
- Allowed theme handler identifiers: `theme_meta_generator`, `theme_meta_brand`, `theme_query_defaults`, `theme_before_render_badge`, `theme_before_save_meta`.
- Package & directory safety limits (`GRAB-E401`):
  - Max directory depth: `8`
  - Max files per theme: `250`
  - Max single file size: `5,242,880` bytes (5 MB)
  - Max total theme size: `26,214,400` bytes (25 MB)
  - Blocked files/patterns: `.git`, `.env`, `.ssh`, `id_rsa`, `id_ed25519`, `.DS_Store`, `*.pem`, `*.key`
  - Blocked executable extensions: `.exe`, `.dll`, `.so`, `.dylib`, `.sh`, `.bat`, `.cmd`, `.ps1`, `.py`, `.php`, `.rb`, `.pl`, `.go`, `.wasm`, `.msi`, `.jar`
  - Permitted file extensions: `.json`, `.grab.html`, `.css`, `.js` (restricted to `assets/`), `.svg`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.woff2`
- Visual Grex templates additionally reject `<div>`, `<script>`, `<iframe>`, `<object>`, `<style>`, inline `on*` attributes, `innerHTML`, unsafe URL protocols (`javascript:`, unsanitized `data:`), and nesting deeper than `24` levels.

---

## 4. Native Hooks & Filters API

Core exposes four deterministic runtime functions inside `src/app.grab`:
- `registerHook(registry, hook_name, source, priority, handler_name)`
- `registerFilter(registry, filter_name, source, priority, handler_name)`
- `runHook(stmts, registry, hook_name, payload)`
- `applyFilter(registry, filter_name, initial_val, ctx)`

### Contract Rules
1. **Source Attribution:** `source` must equal `"core"` or `"theme:" + active_slug`. Any unregistered or cross-theme source raises `GRAB-E401`.
2. **Deterministic Ordering:** Handlers execute in ascending integer `priority`, tie-broken strictly by registration sequence (`seq`).
3. **Core Default Registrations:**
   - `content:before_save` → `core_normalize_entry_before_save`
   - `content:after_publish` → `core_invalidate_after_publish`
   - `theme:head_meta` → `core_default_head_meta`
   - `theme:before_render` → `core_prepare_render_context`
   - `query:modify_args` → `core_clamp_query_args`

---

## 5. `query_entries` Filter & `use cache` Invalidation Contract

Both internal template Query Loops and `GET /api/query` execute through `query_entries` using prepared SQL statements exclusively.

### 5.1 Frozen Parameters
- `content_type`: Slug of the target content type (optional).
- `status`: Forced to `"published"` when `is_public=yes`; otherwise accepts `"published"`, `"draft"`, `"archived"`, or `"all"`.
- Custom field filter: `field_key`, `field_op` (`"eq"` | `"neq"` | `"contains"`), `field_value`.
- Taxonomy term filter (`filter_by_term` object or top-level parameters):
  - `taxonomy`, `term_slug`, `term_id`, `include_children` (boolean)
  - Hierarchical descendant BFS up to depth `8`, capped at `16` bound term IDs in prepared SQL `IN (...)`.
- Full-text substring filter: `search`.
- Sorting & pagination: `sort_by` (`"published_at"` | `"created_at"` | `"updated_at"` | `"title"` | `"id"`), `sort_dir` (`"asc"` | `"desc"`), `page` (`>= 1`), `per_page` (`1..100`, default `10`).

### 5.2 Deterministic `use cache` Key & Invalidation
- Cache key format (TTL `120,000` ms):
  ```text
  query:<t_epoch>:<g_epoch>:<ct_epoch>:<theme_slug>:<content_type>:<status>:<sort_by>:<sort_dir>:<page>:<per_page>:<field_key>:<field_op>:<field_value>:t:<term_taxonomy>:<term_slug>:<term_id>:<ic_flag>:q:<search>
  ```
- Deterministic epoch invalidation fires synchronously upon:
  - Entry creation, update, deletion, status change, or slug rename (`entries`, `pages`, `301` slug history)
  - Content type or custom field schema updates
  - Taxonomy/term assignment or hierarchy changes
  - Active theme switch

---

## 6. `grab mcp` CMS Tool Schemas

Exposed over JSON-RPC 2.0 at `POST /api/mcp` as well as REST tool discovery/execution at `GET /api/mcp/tools` and `POST /api/mcp/tools/{name}`. Compatible with GRAB's stdio `grab mcp` bridge and external AI clients.

### Authentication
- Bearer MCP token issued via `POST /api/auth/mcp-token`, or authenticated session cookie paired with `X-CSRF-Token`.

### Frozen `v1.x` Tool Registry
| Tool Name | Required Permission | Input Highlights | Frozen Safety Behavior |
|---|---|---|---|
| `list_content_types` | `admin:access` | No required params | Returns registered content types and field schemas (`string`, `text`, `integer`, `decimal`, `boolean`, `date`). |
| `query_entries` | Auth + role policy | `content_type`, `status`, `field_key`, `field_op`, `field_value`, `filter_by_term`, `search`, `sort_by`, `sort_dir`, `page`, `per_page` | `viewer` role cannot query non-published entries; executes identically to public/admin `query_entries`. |
| `create_entry_draft` | `entries:create` | `content_type_slug`, `title`, `slug`, `excerpt`, `body`, `custom_fields`, `grex_layout` | **Always enforces `status: "draft"`** and returns `status_enforced: "draft"` — AI agents cannot bypass editorial review to publish directly. |
| `update_entry_layout` | `entries:update:own` (with owner check) or `entries:update:any` | `entry_id`, `grex_layout` (or `layout`) | Runs `audit_grex_tree_walk` + `render_validated_grex_html`. Rejects unsafe tags (`<div>`, `<script>`, etc.), unsafe URLs, or missing accessibility metadata with HTTP `422` (`error: "grex_validation_failed"`). |
| `list_media` | `media:read` | Optional pagination/filter | Lists uploaded media assets (`id`, MIME metadata, dimensions, `alt_text` / `is_decorative`, immutable `/media/{id}/{filename}` path). |
| `list_menus` | `admin:access` | Optional location filter | Returns menus and resolved `menu_items` linking cleanly to current entry permalinks. |

---

## 7. `--read-only` Container Deployment & Runtime Security Profile

GrabLab CMS `v1.0.0` is engineered for read-only container execution (`read_only: true`) under GRAB `1.1.0` (`grab serve`) or Grisp workers:

### 7.1 Strictly Scoped Writable Mounts
All application source (`src/`, `themes/`, `migrations/`, `grab.data.json`, `grab.platform.json`) remains mounted read-only inside the container image. Only runtime state and builder/media storage require writable mounts:
1. **`storage/` (`./storage:/app/storage`)** — SQLite database (`storage/grablab.db`, WAL/SHM files when SQLite is active).
2. **`uploads/` / `storage/uploads/` (`./uploads:/app/uploads`, `GRABLAB_UPLOAD_DIR=/app/uploads`)** — Scoped by `--allow-write /app/uploads`; binary uploads are validated by magic-byte MIME sniffing (`image/png`, `image/jpeg`, `image/webp`, `image/gif`, `application/pdf`; `415` on SVG/HTML/scripts) and served with `X-Content-Type-Options: nosniff`, `Content-Security-Policy: default-src 'none'`, `ETag`, and `Cache-Control: public, max-age=31536000, immutable`.
3. **`/static/grex/` (`./public/grex:/app/public/grex`)** — Mounted writable so **Grex Theme Builder** (`grex-builder`) visual tokens (`tokens.css`) and compiled Grex bundles (`grex.js`) can be updated without rebuilding the immutable CMS container image, served automatically by `server.asset` under `/static/grex/...`.

### 7.2 Required GRAB CLI Capabilities
Production `grab serve` invocations must grant only minimal explicit permissions:
- `--allow-public` (bind HTTP listener when exposed behind reverse proxy/container network)
- `--allow-scripts` (permit Grex ES modules on Admin / Builder routes)
- `--allow-env GRABLAB_MASTER_KEY,GRABLAB_UPLOAD_DIR,GRABLAB_MAX_UPLOAD_BYTES,GRABLAB_ADMIN_EMAIL,GRABLAB_ADMIN_PASSWORD,GRABLAB_ADMIN_NAME`
- `--allow-read /app`
- `--allow-write /app/uploads`
- `--db-config /app/grab.data.json --allow-db main:read-write`
- `--platform-config /app/grab.platform.json --allow-cache cms:read-write --allow-cache cms:limit`
- `--trusted-proxy <cidr>` (set via environment / deploy config; never commit production IPs or secrets to Git)

### 7.3 Operational Probes
- `GET /_health` → `200 OK` (`{"status":"ok"}`)
- `GET /_ready` → `200 OK` (`{"status":"ready","in_flight":<int>,"max_concurrency":<int>}`)
- Permanent `301 Moved Permanently` redirects resolve historical slugs from `slug_history` automatically with cycle/reserved-prefix guards.

---

## 8. Release Verification Gate (`v1.0.0`)

Before tagging or publishing `v1.0.0`, all checks below must pass 100%:
1. `grab check` passes across every `.grab` and `.grab.html` file in the repository.
2. Canonical formatting check (`grab format` stdout matches on-disk bytes) passes across all `.grab` files.
3. Zero wrapper `<div>` elements appear in starter theme templates, visual Grex fixture renders, or Admin UI markup.
4. `python tests/integration_test.py` (`v0.4.0` baseline contracts) and `python tests/release_v100_test.py` (`v1.0.0` E2E fresh install, lifecycle, MCP, exclusive coded/visual theme switch, read-only layout & deploy validation) pass **100%**.
