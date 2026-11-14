# GrabLab CMS v0.4 Specification (`GRABLAB-SPEC-004`)

**Status:** Complete (`v0.4.0`)  
**Target Milestone:** `grablab-cms v0.4.0`  
**Owner:** Project Owner (`urbanspress`) · **Author:** Google Antigravity  
**Platform Baseline:** GRAB `v1.1.0` (`use data`, `use cache`, `use crypto`, `use env`, `use server`, `server.asset`, `grab serve --allow-write --allow-scripts`, `grab mcp`) & Grex JS `v1.0.0` (`grex.elements.json`, `auditAccessibility`, `createTheme`, `createClassManager`, `ForEach`, `useQuery`, `Form`, `Input`, `Select`, `Nav`, `Modal`)

> **Spec-First Gate:** Per `AGENTS.md`, no `v0.4.0` application code or migrations may be written until `GRABLAB-SPEC-004.md` is explicitly approved by the project owner.

---

## 1. Purpose & Architectural Principles

GrabLab CMS `v0.4.0` completes the core content-management, navigation, media, and AI-interoperability layer on top of `v0.1.0` (Data & Permalinks), `v0.2.0` (Exclusive Theme Engine & Query Loops), and `v0.3.0` (RBAC Auth, CSRF & Grex Admin Dashboard):

1. **Zero-Plugin Core Modules:** Media uploads, navigation menus, taxonomies, and `grab mcp` AI tools are implemented as native `.grab` core modules—never third-party plugins, arbitrary shortcodes, or runtime eval hooks.
2. **Read-Only Container & Upload Isolation:** Core code and `PreparedApp` static assets (`server.asset`) remain 100% compatible with `--read-only` Grisp containers. Uploaded media files are strictly confined to a single configured `--allow-write` directory (`GRABLAB_UPLOAD_DIR`).
3. **WCAG AA & Semantic Grex Markup by Default:** Image media enforces `alt` text metadata, navigation menus render semantic `<nav>` + `<ul>`/`<li>`/`<a>` markup via `Grex JS v1.0.0` with zero wrapper-`<div>` bloat, and AI-authored layouts pass `grex.elements.json` + `auditAccessibility` validation before saving.
4. **Capability-Gated AI Interoperability (`grab mcp`):** **Groxy AI** (`Step 4`) and **Grex Theme Builder** (`Step 3`) interact with GrabLab through structured, schema-validated `grab mcp` tools that enforce the exact same RBAC capabilities, slug reservations, and `use cache` invalidation rules as the Admin UI.
5. **Cross-Database Parity:** All `v0.4.0` tables (`media`, `menus`, `menu_items`, `taxonomies`, `terms`, `entry_terms`) ship with idempotent migrations for SQLite, MariaDB, and PostgreSQL using literal prepared SQL (`use data`) and exact `GrabInteger` IDs/sizes/sort orders.

---

## 2. Database Schema & Migrations (`use data`)

New tables are introduced in `migrations/003_v04_schema.grab` (SQLite), `migrations/003_v04_schema_mariadb.grab` (MariaDB), and `migrations/003_v04_schema_postgres.grab` (PostgreSQL). Each migration file carries `version: 1` (`grablab_v01_schema*`), `version: 2` (`grablab_v03_auth_schema*`), and `version: 3` (`grablab_v04_cms_schema*`) so both fresh installs and upgrades from `v0.1`–`v0.3` remain 100% idempotent.

### 2.1 `media`
Stores uploaded asset metadata. Raw file bytes are stored on disk under `GRABLAB_UPLOAD_DIR` at `storage_path`, never in the database.

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY` | Auto-increment / sequence |
| `filename` | `TEXT` (`VARCHAR(128)`) | `UNIQUE NOT NULL` | Safe randomized filename (`<32-hex>.<ext>`) |
| `original_name` | `TEXT` (`VARCHAR(255)`) | `NOT NULL` | Sanitized display name (no path separators) |
| `storage_path` | `TEXT` (`VARCHAR(255)`) | `UNIQUE NOT NULL` | Relative path under `GRABLAB_UPLOAD_DIR` (e.g., `2026/11/<hex>.png`) |
| `mime_type` | `TEXT` (`VARCHAR(128)`) | `NOT NULL` | Verified by magic-byte sniffing (e.g., `image/png`, `application/pdf`) |
| `byte_size` | `INTEGER` | `NOT NULL` | Exact `GrabInteger` file size in bytes |
| `width` | `INTEGER` | `NULL` | Pixel width for images (`NULL` for documents) |
| `height` | `INTEGER` | `NULL` | Pixel height for images (`NULL` for documents) |
| `alt_text` | `TEXT` (`VARCHAR(512)`) | `NOT NULL DEFAULT ''` | WCAG AA alternative text |
| `is_decorative` | `INTEGER` | `NOT NULL DEFAULT 0` | `1` = explicitly marked decorative (`alt=""` + `aria-hidden="true"`) |
| `caption` | `TEXT` | `NOT NULL DEFAULT ''` | Optional caption |
| `sha256_hex` | `TEXT` (`VARCHAR(64)`) | `NOT NULL` | Content digest for `ETag` cache-busting and integrity |
| `uploader_id` | `INTEGER` | `NULL REFERENCES users(id) ON DELETE SET NULL` | Uploading user for `media:*_own` checks |
| `created_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |
| `updated_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |

### 2.2 `menus`
Stores named navigation menus and their optional theme slot assignment.

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY` | Auto-increment / sequence |
| `slug` | `TEXT` (`VARCHAR(100)`) | `UNIQUE NOT NULL` | Machine slug (e.g., `main-nav`, `footer-links`) |
| `name` | `TEXT` (`VARCHAR(120)`) | `NOT NULL` | Human-readable title |
| `location` | `TEXT` (`VARCHAR(32)`) | `NULL` | `primary` \| `footer` \| `mobile` \| `NULL` (unassigned); at most one menu per active location |
| `created_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |
| `updated_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |

### 2.3 `menu_items`
Stores ordered, arbitrarily nested menu links belonging to a `menus` row.

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY` | Auto-increment / sequence |
| `menu_id` | `INTEGER` | `NOT NULL REFERENCES menus(id) ON DELETE CASCADE` | Owning menu |
| `parent_id` | `INTEGER` | `NULL REFERENCES menu_items(id) ON DELETE CASCADE` | Parent item for nested submenus (max depth `4`) |
| `label` | `TEXT` (`VARCHAR(160)`) | `NOT NULL` | Visible link text |
| `link_type` | `TEXT` (`VARCHAR(16)`) | `NOT NULL` | `entry` \| `external` |
| `entry_id` | `INTEGER` | `NULL REFERENCES entries(id) ON DELETE SET NULL` | Required when `link_type = 'entry'` |
| `external_url` | `TEXT` (`VARCHAR(512)`) | `NULL` | Required when `link_type = 'external'`; `https://` or `http://` only |
| `target_blank` | `INTEGER` | `NOT NULL DEFAULT 0` | `1` adds `target="_blank" rel="noopener noreferrer"` |
| `css_class` | `TEXT` (`VARCHAR(120)`) | `NOT NULL DEFAULT ''` | Optional sanitized CSS class token(s) |
| `sort_order` | `INTEGER` | `NOT NULL DEFAULT 0` | Exact `GrabInteger` sibling order |
| `created_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |
| `updated_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |

### 2.4 `taxonomies`
Defines built-in (`category`, `post_tag`) and custom taxonomies.

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY` | Auto-increment / sequence |
| `slug` | `TEXT` (`VARCHAR(64)`) | `UNIQUE NOT NULL` | e.g., `category`, `post_tag`, `topic` |
| `label_singular` | `TEXT` (`VARCHAR(80)`) | `NOT NULL` | e.g., `Category`, `Tag` |
| `label_plural` | `TEXT` (`VARCHAR(80)`) | `NOT NULL` | e.g., `Categories`, `Tags` |
| `is_hierarchical` | `INTEGER` | `NOT NULL DEFAULT 0` | `1` = parent/child tree (Categories); `0` = flat (Tags) |
| `archive_slug` | `TEXT` (`VARCHAR(64)`) | `UNIQUE NOT NULL` | URL prefix (e.g., `category` -> `/category/:slug`, `tag` -> `/tag/:slug`) |
| `content_type_slugs_json` | `TEXT` | `NOT NULL DEFAULT '["post"]'` | JSON array of attached `content_types.slug` values |
| `is_system` | `INTEGER` | `NOT NULL DEFAULT 0` | `1` for built-in `category` and `post_tag` |
| `created_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |

### 2.5 `terms`
Stores individual terms within a taxonomy.

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY` | Auto-increment / sequence |
| `taxonomy_id` | `INTEGER` | `NOT NULL REFERENCES taxonomies(id) ON DELETE CASCADE` | Owning taxonomy |
| `parent_id` | `INTEGER` | `NULL REFERENCES terms(id) ON DELETE SET NULL` | Only allowed when `taxonomies.is_hierarchical = 1` |
| `slug` | `TEXT` (`VARCHAR(120)`) | `NOT NULL` | URL-safe slug, unique per taxonomy (`UNIQUE(taxonomy_id, slug)`) |
| `name` | `TEXT` (`VARCHAR(120)`) | `NOT NULL` | Display name |
| `description` | `TEXT` | `NOT NULL DEFAULT ''` | Archive description |
| `sort_order` | `INTEGER` | `NOT NULL DEFAULT 0` | Exact `GrabInteger` order |
| `created_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |
| `updated_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |

### 2.6 `entry_terms`
Many-to-many join table linking `entries` and `terms`.

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `entry_id` | `INTEGER` | `NOT NULL REFERENCES entries(id) ON DELETE CASCADE` | Linked entry |
| `term_id` | `INTEGER` | `NOT NULL REFERENCES terms(id) ON DELETE CASCADE` | Linked term |
| `created_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |
| **Primary Key** | `PRIMARY KEY(entry_id, term_id)` | | Prevents duplicate term assignments |

### 2.7 Seed Defaults (`migrations/seed.grab`)
- Seed built-in taxonomies `category` (`archive_slug: "category"`, `is_hierarchical: 1`, `is_system: 1`, attached to `["post"]`) and `post_tag` (`archive_slug: "tag"`, `is_hierarchical: 0`, `is_system: 1`, attached to `["post"]`) if missing.
- Seed a default `Uncategorized` term under `category` and a default `primary` menu (`main-nav`) pointing to `Home` (`/`) and `Blog` (`/blog`) if `menus` is empty.

---

## 3. Media Library & Safe Upload Pipeline (`/admin/media`)

### 3.1 Capability Matrix Extension
| Capability | `admin` | `editor` | `author` | `viewer` |
| --- | --- | --- | --- | --- |
| `media:read` | Yes | Yes | Yes | No (`403`) |
| `media:upload` | Yes | Yes | Yes | No (`403`) |
| `media:update_own` | Yes | Yes | Yes | No (`403`) |
| `media:update_any` | Yes | Yes | No (`403`) | No (`403`) |
| `media:delete_own` | Yes | Yes | Yes | No (`403`) |
| `media:delete_any` | Yes | Yes | No (`403`) | No (`403`) |
| `menus:manage` | Yes | Yes | No (`403`) | No (`403`) |
| `taxonomies:manage` | Yes | Yes | No (`403`) | No (`403`) |

### 3.2 Strict Upload Security Pipeline
Every upload to `POST /api/admin/media/upload` (requiring valid session + `media:upload` + `X-CSRF-Token`) MUST pass all checks in order before any byte is written to disk:

1. **Size Limit:** Reject payloads exceeding `GRABLAB_MAX_UPLOAD_BYTES` (default `10485760` = 10 MiB) with `413 Payload Too Large`.
2. **Allowlisted MIME Types & Magic-Byte Sniffing:**
   - Never trust the client-supplied `Content-Type` or filename extension alone.
   - Inspect the file header magic bytes:
     - `image/png` (`.png`): `\x89PNG\r\n\x1a\n`
     - `image/jpeg` (`.jpg`): `\xFF\xD8\xFF`
     - `image/webp` (`.webp`): `RIFF` at offset `0` + `WEBP` at offset `8`
     - `image/gif` (`.gif`): `GIF87a` or `GIF89a`
     - `application/pdf` (`.pdf`): `%PDF-`
   - **SVG (`image/svg+xml`) and executable/HTML/script types are rejected (`415 Unsupported Media Type`)** to eliminate stored-XSS and active-content upload vectors.
   - If the declared extension/MIME contradicts the sniffed magic bytes, reject with `415 Unsupported Media Type`.
3. **Dimension Extraction:** For allowlisted raster images (`png`, `jpeg`, `webp`, `gif`), parse `width` and `height` from image headers in memory. Corrupt/truncated headers are rejected (`400 Bad Request`).
4. **Path-Traversal & Symlink Prevention:**
   - Strip all directory components from `original_name`, reject `..`, `/`, `\`, and NUL (`\x00`) bytes, and truncate display name to `255` chars.
   - Generate the on-disk filename strictly using `crypto.random_hex using 16` + canonical extension (e.g., `2026/11/a3f9...c1.png`).
   - Resolve `GRABLAB_UPLOAD_DIR` (`--allow-write`, default `./uploads`) and verify the destination path stays strictly inside `GRABLAB_UPLOAD_DIR` with no symlink escapes.
5. **`--read-only` Container Compatibility:**
   - GrabLab never writes uploads to `public/`, `themes/`, or `/tmp`. Only `GRABLAB_UPLOAD_DIR` requires `--allow-write` in `grab serve`.
6. **WCAG AA Mandatory `alt` Text Enforcement:**
   - Image uploads (`image/*`) MUST supply either a non-empty `alt_text` or explicit `is_decorative = true`. Missing both returns `422 Unprocessable Entity` (`{ "error": "alt_text_required" }`).
   - `/admin/media` provides an accessible upload modal (`Form`, `Input`, `Select`) that enforces `alt` text (or decorative checkbox) before submission and allows editing `alt_text`/`caption` inline (`PATCH /api/admin/media/:id`).

### 3.3 Safe Media Serving (`GET /media/:id/:filename`)
- Looks up `media` by `id` (and verifies `filename` matches `media.filename`; otherwise `404`).
- Streams the file from `GRABLAB_UPLOAD_DIR/<storage_path>` with mandatory hardening headers:
  - `Content-Type: <verified_mime_type>`
  - `X-Content-Type-Options: nosniff`
  - `Content-Security-Policy: default-src 'none'`
  - `ETag: "<sha256_hex>"`
  - `Cache-Control: public, max-age=31536000, immutable`

---

## 4. Navigation Menus & Drag/Order Builder (`/admin/menus`)

### 4.1 Named Menu Locations & Exclusive Slot Assignment
- Core supports three standard theme locations: `primary`, `footer`, and `mobile`.
- Assigning a menu to a `location` atomically clears `location = NULL` on any other menu previously holding that slot inside a `use data` transaction and invalidates `use cache` keys `menu:loc:<location>`.
- Themes render menus via a core helper `render_menu(location, current_path)` exposed to `.grab.html` templates and template parts (`header`, `footer`).

### 4.2 Link Resolution & Security Validation
1. **Internal Entry Links (`link_type = "entry"`):**
   - Stores `entry_id` (foreign key to `entries(id)`).
   - At render/query time, `get_menu_tree(location)` joins `entries` to resolve `entries.full_path` dynamically (only including `entries.status = 'published'` on public routes).
   - When an entry's slug changes (`v0.1` 301 history), `invalidate_entry_caches` also invalidates `menu:loc:*` so navigation links immediately reflect the new canonical permalink without manual edits.
2. **External URLs (`link_type = "external"`):**
   - Strictly validated to begin with `https://` or `http://` (case-insensitive scheme check, rejecting `javascript:`, `data:`, `vbscript:`, `file:`, and protocol-relative `//` URLs with `400 Bad Request`).
3. **Nested Hierarchy & Cycle Prevention:**
   - `parent_id` must belong to the same `menu_id`.
   - Maximum nesting depth is `4` levels; any save creating a cycle or exceeding depth `4` is rejected with `400 Bad Request`.

### 4.3 Semantic `Grex JS v1.0.0` Rendering & `/admin/menus` Builder
- **Frontend Markup:** `render_menu` outputs semantic `<nav aria-label="<menu_name>">` containing nested `<ul>`, `<li>`, and `<a href="...">` elements matching `Grex JS v1.0.0` `Nav` conventions—zero wrapper `<div>` elements, and `aria-current="page"` on the active link matching `req.path`.
- **Admin Builder (`/admin/menus`):**
  - Requires `menus:manage` (`admin` or `editor`) and `X-CSRF-Token`.
  - Uses `Grex JS v1.0.0` components (`ForEach`, `Form`, `Input`, `Select`, `Modal`) to create menus, assign `primary` / `footer` / `mobile` locations, pick published entries or validated external URLs, and reorder/nest items via **both drag-and-drop and keyboard-accessible Move Up / Move Down / Indent / Outdent buttons**.

---

## 5. Taxonomies, Terms & Query Loop Integration

### 5.1 Built-In & Custom Taxonomies (`/admin/taxonomies`)
- **Built-In:** `category` (`is_hierarchical = 1`, `archive_slug = "category"`) and `post_tag` (`is_hierarchical = 0`, `archive_slug = "tag"`).
- **Custom Taxonomies:** `admin` and `editor` (`taxonomies:manage`) can create custom taxonomies (`POST /api/admin/taxonomies`) specifying `slug`, `label_singular`, `label_plural`, `is_hierarchical`, `archive_slug`, and `content_type_slugs` (attaching to `post`, `page`, or any custom content type).
- **Reserved Prefix Protection:** `archive_slug` MUST NOT collide with reserved system prefixes (`/admin`, `/api`, `/static`, `/media`, `/_health`, `/_ready`, `/login`, `/logout`, `/setup`, `/search`) or existing `content_types.archive_slug` values (`409 Conflict`).
- **Hierarchical Terms:** When `is_hierarchical = 1`, terms may set `parent_id` within the same `taxonomy_id` (cycle-checked). When `is_hierarchical = 0`, `parent_id` MUST be `NULL`.

### 5.2 Pretty Archive URLs (`/category/:slug`, `/tag/:slug`, `/<archive_slug>/:slug`)
- Public router resolves `GET /<archive_slug>/:term_slug` (e.g., `/category/tutorials`, `/tag/grab`, `/topic/performance`):
  - Looks up `taxonomies` by `archive_slug` and `terms` by `(taxonomy_id, slug)`.
  - Returns `404` via the active theme's `404` template if either is missing.
  - Queries published entries via `query_entries` with `filter_by_term` and renders using the active exclusive theme's `archive` template (`use cache` keyed by `route:<path>:epoch:<query_epoch>`).

### 5.3 `query_entries` Integration (`filter_by_term`)
`query_entries` (`src/app.grab`) is extended with prepared-SQL `filter_by_term` support:
- Parameters:
  - `filter_by_term`: `{ taxonomy: "<slug>", term_slug: "<slug>", include_children: true|false }` (or shorthand `term_id: <int>`).
- Behavior:
  - Joins `entry_terms` (`INNER JOIN entry_terms et ON et.entry_id = e.id`) using literal prepared SQL bindings—never string concatenation.
  - When `include_children` is `true` on a hierarchical taxonomy, expands descendant term IDs (up to depth `8`) before binding.
  - Term assignments on entries (`PUT /api/admin/entries/:id` or `/api/admin/entries/:id/terms`) automatically bump `query:epoch` in `use cache` so archive pages and query loops update immediately.

---

## 6. Native `grab mcp` CMS Tools & AI Guardrails

To support **Step 4 (`groxy-ai`)** and **Step 3 (Grex Theme Builder)**, GrabLab exposes structured, capability-gated CMS tools via `grab mcp` (and matching `/api/mcp/tools/*` service handlers).

### 6.1 Authentication & RBAC Guardrails
- Every `grab mcp` invocation MUST present a scoped MCP token / session principal bound to an active `users` row (`is_active = 1`).
- Every tool checks `role_has_capability(user.role, required_cap)` before executing. `viewer` tokens are denied (`403`) on all write tools and draft reads.
- **No Secret Leakage:** `password_hash`, `csrf_secret`, `oauth_accounts`, `client_secret`, and `GRABLAB_MASTER_KEY` are never returned by any MCP tool.
- **Draft-Only AI Creation:** `create_entry_draft` ALWAYS sets `status = 'draft'` (even if a caller passes `status: "published"`), requiring human or explicit `entries:publish` workflow approval to go live.

### 6.2 Tool Contracts

| Tool Name | Required Capability | Purpose & Guardrails |
| --- | --- | --- |
| `list_content_types` | `admin:access` | Returns registered `content_types` (`slug`, `label_singular`, `label_plural`, `permalink_pattern`, `has_archive`, `archive_slug`) and their `field_definitions`. |
| `query_entries` | `entries:read_all` (or `author` own + published) | Executes prepared-SQL `query_entries` with optional `content_type`, `status`, `filter_by_term`, `search`, `limit` (max `100`), and `offset`. |
| `create_entry_draft` | `entries:create` | Creates a `draft` entry (`status = 'draft'`), validates `slug` against reserved prefixes, validates `custom_fields` against `field_definitions` (exact `integer`/`decimal`/`url`/`json` types), attaches optional `term_ids`, and invalidates `query:epoch`. |
| `update_entry_layout` | `entries:update_own` or `entries:update_any` | Updates an entry's Grex layout tree (`grex_layout_json` / rendered `body_html`). **MUST** pass two mandatory validation gates before saving (see 6.3). |
| `list_media` | `media:read` | Lists uploaded `media` items (`id`, `filename`, `url`, `mime_type`, `width`, `height`, `alt_text`, `is_decorative`, `byte_size`) with optional `mime_prefix` and pagination (`limit` max `100`). |
| `list_menus` | `admin:access` | Returns all `menus` and their resolved `menu_items` hierarchy (`location`, `label`, `link_type`, resolved `url`, `children`). |

### 6.3 `update_entry_layout` Mandatory Grex + Accessibility Validation
Before `update_entry_layout` persists any layout to `entries`, GrabLab runs:
1. **`grex.elements.json` Schema & `securityRules` Gate:**
   - Every node in the layout tree MUST use an element type defined in `grex.elements.json`.
   - Enforces `securityRules`: rejects `no-wrapper-div` violations, inline `<script>` / `on*` event attributes, `javascript:` URLs, `eval`, and `innerHTML` sinks.
2. **`auditAccessibility` (WCAG AA) Gate:**
   - Verifies every image node references valid `alt` text (non-empty `alt` or explicit `is_decorative: true` from `media` or node props).
   - Verifies heading hierarchy (no skipped heading levels without reason, single `<h1>` rule on full-page layouts) and interactive controls have accessible labels (`aria-label` or visible text).
   - If either gate fails, `update_entry_layout` rejects the write with `422 Unprocessable Entity` and returns structured `violations[]` so **Groxy AI** can self-correct.

---

## 7. Acceptance & Test Gates

Milestone `v0.4.0` cannot be marked complete until all gates pass **100%**:

1. **GRAB Compiler & Format Gate:**
   - `grab check` passes on all `.grab` and `.grab.html` files with zero errors.
   - `grab format --check` confirms canonical formatting across all `.grab` files.
2. **Database & Migration Gate:**
   - `003_v04_schema` migrations run idempotently on SQLite (upgrading from `v0.3` and migrating fresh) and pass schema parity checks for MariaDB and PostgreSQL.
3. **Media Library & Upload Security Tests:**
   - Valid PNG/JPEG/WebP/GIF/PDF uploads succeed, generate randomized `crypto.random_hex` filenames under `GRABLAB_UPLOAD_DIR`, extract image dimensions, and serve with `X-Content-Type-Options: nosniff` and `Content-Security-Policy: default-src 'none'`.
   - Spoofed MIME/extension (e.g., `.png` containing HTML/script bytes) and SVG uploads are rejected (`415`).
   - Path-traversal filenames (`../../etc/passwd`, `..\x`) are sanitized/rejected, and uploads never write outside `GRABLAB_UPLOAD_DIR` (`--read-only` root compatible).
   - Image upload without `alt_text` and without `is_decorative = true` is rejected (`422`).
4. **Navigation Menus & Permalink Resolution Tests:**
   - Assigning a menu to `primary` atomically clears `primary` from any prior menu and invalidates `menu:loc:primary`.
   - Internal `entry` menu items dynamically reflect updated `entries.full_path` after a slug rename.
   - `javascript:` / `data:` external URLs and cyclic `parent_id` hierarchies are rejected (`400`).
   - Rendered theme output uses semantic `<nav>` + `<ul>`/`<li>`/`<a>` with `aria-current="page"` and zero wrapper `<div>` tags.
5. **Taxonomies & Query Loop Tests:**
   - Built-in `category` (hierarchical) and `post_tag` (flat) plus custom taxonomies attach to content types and reject reserved `archive_slug` collisions (`409`).
   - `query_entries` with `filter_by_term` (including `include_children: true`) returns exact matching published entries via prepared SQL.
   - `/category/:slug` and `/tag/:slug` render the active exclusive theme's `archive` template and return `404` for unknown terms.
6. **`grab mcp` CMS Tools & AI Guardrail Tests:**
   - Unauthenticated or `viewer`-role calls to `create_entry_draft` / `update_entry_layout` are rejected (`401`/`403`).
   - `create_entry_draft` forces `status = 'draft'` and validates custom fields and reserved slugs.
   - `update_entry_layout` rejects `grex.elements.json` violations (`<script>`, wrapper `<div>`, `javascript:` URLs) and `auditAccessibility` failures (missing `alt` text) with `422`, and accepts valid semantic layouts.
   - `list_content_types`, `query_entries`, `list_media`, and `list_menus` return accurate structured JSON with zero leaked secrets.
7. **Admin UI & Security Tests:**
   - `/admin/media`, `/admin/menus`, and `/admin/taxonomies` enforce RBAC capabilities and `X-CSRF-Token` (`403` on missing/invalid token) and render with `Grex JS v1.0.0` (`--allow-scripts`).
8. **Release Guide Gate:**
   - `docs/releases/pdf/GrabLab-v0.4.0-Guide.pdf` plain-English walkthrough guide is generated upon milestone completion.
