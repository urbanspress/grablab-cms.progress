# GrabLab CMS v0.1 Specification (`GRABLAB-SPEC-001`)

**Status:** Draft — Awaiting Owner Approval  
**Target Milestone:** `grablab-cms v0.1.0`  
**Owner:** Project Owner (`urbanspress`) · **Author:** Google Antigravity  
**Platform Baseline:** GRAB `v1.0.1` (`use data`, `use cache`, `use server`, `server.asset`, `grab mcp`) & Grex JS `v1.0.0` (`grex.elements.json`, `createTheme`, `createClassManager`, `ForEach`, `useQuery`)

> **Approval Gate:** No `GrabLab` application code (`.grab`, `.grab.html`, or SQL migrations) may be written until the project owner approves this specification.

---

## 1. Purpose & Architectural Principles

GrabLab CMS `v0.1.0` establishes the foundational data model, content-type/custom-field registry, WordPress-style pretty permalink router with automatic `301` redirect history, and the **Exclusive Active Theme** manifest contract (`theme.json`).

1. **Zero-Plugin Core:** All CMS capabilities live directly in core `.grab` modules. There is no plugin loader, no runtime code evaluation, and no third-party hook injection.
2. **Exclusive Active Theme Ownership:** Only **one** theme is active at any time. Activating a theme atomically deactivates the prior theme and grants 100% exclusive template rendering control (`home`, `single`, `archive`, `header`, `footer`, `404`, `search`) to the active theme—whether it is a coded `.grab`/`.grab.html` theme or the installable **Grex Theme Builder** visual theme (`Step 3`).
3. **External Platform Runtimes:** GrabLab consumes `GRAB v1.0.1` and `Grex JS v1.0.0` as already-unlocked external runtimes without duplicating core Go compiler code or `grex-js` source modules.
4. **Security & Precision:** Mandatory prepared SQL (`use data`), exact `GrabInteger`/`GrabDecimal` types (no float coercion for currency or IDs), `use cache` deterministic invalidation, and `--read-only` container compatibility.

---

## 2. Database Schema & Migrations (`use data`)

All tables are defined in versioned `grab migrate` SQL migrations compatible with **SQLite** (development/single-node), **MariaDB**, and **PostgreSQL**. Exact decimal values use `TEXT` in SQLite and `DECIMAL(19,4)` in MariaDB/PostgreSQL. Timestamps use ISO-8601 UTC `TEXT` (or `TIMESTAMP` mapped to ISO-8601 text).

### 2.1 `site_settings`
Stores global site configuration and the single active theme pointer.

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `key` | `TEXT` (`VARCHAR(128)`) | `PRIMARY KEY` | e.g., `site_title`, `active_theme_slug`, `home_entry_id` |
| `value` | `TEXT` | `NOT NULL` | JSON or scalar text |
| `updated_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |

### 2.2 `content_types`
Defines built-in (`page`, `post`) and custom content types (e.g., `product`, `project`, `faq`).

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY` | Auto-increment / sequence |
| `slug` | `TEXT` (`VARCHAR(64)`) | `UNIQUE NOT NULL` | Lowercase ASCII `[a-z0-9_-]` |
| `label_singular` | `TEXT` | `NOT NULL` | Display name (e.g., `"Post"`) |
| `label_plural` | `TEXT` | `NOT NULL` | Display name (e.g., `"Posts"`) |
| `permalink_pattern` | `TEXT` | `NOT NULL` | e.g., `"/:slug"` (pages) or `"/blog/:slug"` (posts) |
| `has_archive` | `INTEGER` | `NOT NULL DEFAULT 1` | `1` = yes, `0` = no |
| `archive_slug` | `TEXT` | `NULL` | e.g., `"blog"` for `/blog` |
| `is_system` | `INTEGER` | `NOT NULL DEFAULT 0` | `1` for built-in `page`/`post` (cannot be deleted) |
| `created_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |

### 2.3 `field_definitions`
Defines typed custom fields attached to a `content_type`.

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY` | Auto-increment |
| `content_type_id` | `INTEGER` | `NOT NULL REFERENCES content_types(id) ON DELETE CASCADE` | Owning type |
| `field_key` | `TEXT` (`VARCHAR(64)`) | `NOT NULL` | Lowercase ASCII `[a-z0-9_]` |
| `label` | `TEXT` | `NOT NULL` | Human-readable field label |
| `field_type` | `TEXT` | `NOT NULL` | `text` \| `rich_text` \| `integer` \| `decimal` \| `boolean` \| `date` \| `url` \| `json` |
| `is_required` | `INTEGER` | `NOT NULL DEFAULT 0` | `1` = required, `0` = optional |
| `default_value` | `TEXT` | `NULL` | Stringified default |
| `sort_order` | `INTEGER` | `NOT NULL DEFAULT 0` | Display order |
| **Constraint** | `UNIQUE(content_type_id, field_key)` | | Prevents duplicate field keys per type |

### 2.4 `entries`
Stores content items (pages, posts, and custom content type entries).

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY` | Auto-increment |
| `content_type_id` | `INTEGER` | `NOT NULL REFERENCES content_types(id)` | Owning type |
| `slug` | `TEXT` (`VARCHAR(190)`) | `NOT NULL` | Normalized lowercase URL segment |
| `full_path` | `TEXT` (`VARCHAR(255)`) | `UNIQUE NOT NULL` | Resolved canonical path (e.g., `"/about"`, `"/blog/hello-world"`) |
| `title` | `TEXT` | `NOT NULL` | Entry title |
| `status` | `TEXT` | `NOT NULL DEFAULT 'draft'` | `draft` \| `published` \| `archived` |
| `body_html` | `TEXT` | `NOT NULL DEFAULT ''` | Main content body or Grex JSON payload |
| `custom_fields_json` | `TEXT` | `NOT NULL DEFAULT '{}'` | Validated JSON map of custom field values (exact strings for `decimal`/`integer`) |
| `meta_title` | `TEXT` | `NOT NULL DEFAULT ''` | SEO title override |
| `meta_description` | `TEXT` | `NOT NULL DEFAULT ''` | SEO description |
| `published_at` | `TEXT` | `NULL` | ISO-8601 UTC |
| `created_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |
| `updated_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |

### 2.5 `slug_history`
Records previous `full_path` values whenever a published entry's slug or permalink changes, enabling automatic `301 Moved Permanently` redirects.

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY` | Auto-increment |
| `old_path` | `TEXT` (`VARCHAR(255)`) | `UNIQUE NOT NULL` | Normalized prior path (e.g., `"/old-about"`) |
| `entry_id` | `INTEGER` | `NOT NULL REFERENCES entries(id) ON DELETE CASCADE` | Target entry |
| `created_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |

### 2.6 `themes`
Tracks installed themes and enforces the **Single Active Theme** invariant.

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `slug` | `TEXT` (`VARCHAR(64)`) | `PRIMARY KEY` | Directory name under `themes/<slug>` |
| `name` | `TEXT` | `NOT NULL` | Display name |
| `version` | `TEXT` | `NOT NULL` | SemVer string |
| `engine` | `TEXT` | `NOT NULL` | `coded` \| `grex-visual` |
| `is_active` | `INTEGER` | `NOT NULL DEFAULT 0` | Exactly one row may have `is_active = 1` |
| `manifest_json` | `TEXT` | `NOT NULL` | Validated `theme.json` snapshot |
| `installed_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |

---

## 3. Content Type & Custom Field Registry

1. **Seeded Defaults:** On initial migration/seed, GrabLab registers two system content types:
   - `page` (`permalink_pattern: "/:slug"`, `has_archive: 0`, `is_system: 1`)
   - `post` (`permalink_pattern: "/blog/:slug"`, `has_archive: 1`, `archive_slug: "blog"`, `is_system: 1`)
2. **Custom Type Registration:** New types must have unique `slug` (`[a-z0-9_-]`), valid `permalink_pattern` containing `:slug`, and non-colliding `archive_slug`.
3. **Field Validation Contract:** When creating or updating an `entry`, `custom_fields_json` is validated against `field_definitions`:
   - `integer`: valid whole-number `GrabInteger` string/value.
   - `decimal`: valid base-10 `GrabDecimal` string (never float).
   - `boolean`: `yes`/`no` or `true`/`false`.
   - `url`: must pass safe URL scheme validation (`http://`, `https://`, or relative `/...`; `javascript:` and `data:` rejected).
   - `json`: valid JSON object/array.
   - Missing `is_required` fields fail deterministically with a structured validation error before DB write.

---

## 4. Pretty Permalink Router & `301` Redirect History

### 4.1 Reserved System Prefixes
The following top-level path prefixes are **unconditionally reserved** and MUST NEVER be claimed by an entry `full_path`, `archive_slug`, or `slug_history.old_path`:
- `/admin` (and `/admin/*`)
- `/api` (and `/api/*`)
- `/static` (and `/static/*`)
- `/_health`, `/_ready`
- `/robots.txt`, `/sitemap.xml`, `/favicon.ico`

### 4.2 Request Resolution Order (`GET` / `HEAD`)
For any incoming request not matched by a reserved system route:
1. **Normalize Path:** Lowercase, strip trailing slash (except `/`), reject `..` or null bytes.
2. **Homepage (`/`):** Resolve `site_settings.home_entry_id` if set; otherwise render the active theme's `home` template.
3. **Archive Match:** If normalized path matches `/<archive_slug>` for a content type with `has_archive = 1`, load published entries for that type and render the active theme's `archive` template.
4. **Published Entry Match:** Look up `entries.full_path = <path>` where `status = 'published'`. If found, render the active theme's `single` template with entry + custom fields + active theme context.
5. **`301` Redirect History Lookup:** If no published entry matches, look up `slug_history.old_path = <path>` joined to `entries` where `status = 'published'`.
   - If found, respond with **`301 Moved Permanently`** (`Location: <entry.full_path>`).
6. **404 Not Found:** Otherwise render the active theme's `404` template with HTTP status `404`.

### 4.3 Atomic Slug Update & Loop Prevention
When an entry's `slug` (and thus `full_path`) changes while `status = 'published'`, inside a single `use data` transaction:
1. Verify the new `full_path` is not reserved and not already used by another entry.
2. Delete any `slug_history` row where `old_path = <new_full_path>` (prevents redirect loops if a slug is later restored).
3. Insert `<old_full_path>` into `slug_history` pointing to `entry.id`.
4. Update `entries.slug` and `entries.full_path`.
5. Invalidate `use cache` keys for both `<old_full_path>` and `<new_full_path>`.

---

## 5. `theme.json` Exclusive Theme Manifest Contract

Every theme lives in `themes/<slug>/` and MUST include a valid `theme.json` manifest:

```json
{
  "schemaVersion": "1.0.0",
  "slug": "default-starter",
  "name": "Default Starter",
  "version": "1.0.0",
  "engine": "coded",
  "author": "Urbanspress",
  "grexJsVersion": "1.0.0",
  "templates": {
    "home": "templates/home.grab.html",
    "single": "templates/single.grab.html",
    "archive": "templates/archive.grab.html",
    "header": "templates/parts/header.grab.html",
    "footer": "templates/parts/footer.grab.html",
    "404": "templates/404.grab.html",
    "search": "templates/search.grab.html"
  },
  "assets": {
    "styles": ["assets/theme.css"],
    "scripts": []
  }
}
```

### 5.1 Manifest Validation & Security Rules
- `slug` MUST match directory name and `[a-z0-9-]+`.
- `engine` MUST be `"coded"` (standard `.grab.html` templates + optional Grex JS) or `"grex-visual"` (installed by **Step 3 `grex-builder`**).
- All `templates` and `assets` paths MUST be relative, normalized, and strictly confined inside `themes/<slug>/` (no `..`, no symlinks escaping theme root, no sensitive files).
- **Required slots:** `home`, `single`, `archive`, `404` MUST exist on disk for coded themes (or be backed by Grex layout definitions for `"grex-visual"` themes).

### 5.2 Exclusive Activation Invariant
Calling `activate_theme(slug)` inside a `use data` transaction:
1. Verifies `themes/<slug>/theme.json` passes validation.
2. Sets `is_active = 0` on **all** rows in `themes`.
3. Sets `is_active = 1` on `slug` and updates `site_settings['active_theme_slug']`.
4. Invalidates the `use cache` active-theme key so all Grisp workers immediately switch to the new theme with zero overlap or style leakage.

---

## 6. `v0.1.0` Acceptance Criteria

Before `v0.1.0` is marked complete:
1. `grab check` and `grab format` pass with zero errors on all `.grab` and `.grab.html` files.
2. Automated tests verify:
   - Migration idempotency & seeded `page` / `post` content types.
   - Custom content type + typed custom field creation and strict validation (including exact `decimal` and safe `url` checks).
   - Pretty permalink routing (`/about`, `/blog/hello-world`), archive routing (`/blog`), reserved prefix protection (`/admin`, `/api`, `/static`, `/_health`, `/_ready`), and `404` handling.
   - Slug change recording `slug_history`, serving `301 Moved Permanently`, and preventing redirect loops when reverting a slug.
   - `theme.json` manifest validation (rejecting path traversal) and atomic single-active-theme switching.
3. `docs/releases/pdf/GrabLab-v0.1.0-Guide.pdf` plain-English walkthrough guide is generated.
