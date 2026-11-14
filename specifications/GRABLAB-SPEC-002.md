# GrabLab CMS v0.2 Specification (`GRABLAB-SPEC-002`)

**Status:** Complete (Owner approved November 13, 2026; verified 100%)  
**Target Milestone:** `grablab-cms v0.2.0`  
**Owner:** Project Owner (`urbanspress`) · **Author:** Google Antigravity  
**Platform Baseline:** GRAB `v1.0.1` (`use data`, `use cache`, `use server`, `server.asset`, `grab mcp`) & Grex JS `v1.0.0` (`grex.elements.json`, `createTheme`, `createClassManager`, `ForEach`, `useQuery`)

> **Approval Gate:** No `GrabLab` `v0.2.0` application code (`.grab`, `.grab.html`, or SQL migrations) may be written until the project owner explicitly approves this specification.

---

## 1. Purpose & Architectural Principles

GrabLab CMS `v0.2.0` builds on the `v0.1.0` data, routing, and `theme.json` foundation to deliver the **Exclusive Theme Engine**, **Reusable Template Parts**, **Native Hooks & Filters**, and the **Query Loop Engine**:

1. **Zero-Plugin Security Guarantee:** Hooks and filters are strictly internal to **GrabLab Core** and the **single Active Theme**. There is no third-party plugin loader, no dynamic `eval`, and no ability for inactive themes or user content to inject runtime code.
2. **Exclusive Active Theme Ownership:** Exactly one theme is active at any time. Activating a coded theme or the **Grex Theme Builder** visual theme (`mode: "visual"`) atomically deactivates the prior theme, clears stale theme caches, and transfers 100% of rendering (`home`, `single`, `archive`, `header`, `footer`, `404`, `search`) and active theme hooks to the new theme.
3. **Zero Wrapper-`<div>` Bloat:** Template parts (`header`, `footer`, `card`, `sidebar`) and Grex JS `v1.0.0` visual components render cleanly as semantic HTML fragments without synthetic wrapper `<div>` elements.
4. **Prepared SQL & Deterministic Caching:** Every Query Loop query executes via literal prepared SQL (`use data`) with parameterized bindings and deterministic `use cache` keys that invalidate automatically on content publish, update, delete, or theme switch.

---

## 2. Exclusive Theme Import, Packaging & Hot-Switch Engine

### 2.1 Theme Directory & `theme.json` Manifest Contract
Every theme resides under `themes/<slug>/` where `<slug>` matches `^[a-z0-9-]{1,64}$`. `themes/<slug>/theme.json` is the canonical manifest:

```json
{
  "schemaVersion": "1.0.0",
  "slug": "default-starter",
  "name": "Default Starter",
  "version": "1.0.0",
  "mode": "coded",
  "engine": "coded",
  "author": "Urbanspress",
  "grexJsVersion": "1.0.0",
  "capabilities": ["templates", "parts", "hooks:theme"],
  "templates": {
    "home": "templates/home.grab.html",
    "single": "templates/single.grab.html",
    "archive": "templates/archive.grab.html",
    "404": "templates/404.grab.html",
    "search": "templates/search.grab.html"
  },
  "parts": {
    "header": "templates/parts/header.grab.html",
    "footer": "templates/parts/footer.grab.html",
    "card": "templates/parts/card.grab.html",
    "sidebar": "templates/parts/sidebar.grab.html"
  },
  "assets": {
    "styles": ["assets/theme.css"],
    "scripts": []
  }
}
```

#### `mode` vs `engine` Compatibility & Visual Theme Contract
- **`mode: "coded"`** (legacy `v0.1.0` `engine: "coded"`): Renders `.grab.html` template files and `.grab.html` template parts, optionally enhanced with `Grex JS v1.0.0` client components (`ForEach`, `useQuery`, `createTheme`). If `mode` is omitted in a `v0.1.0` manifest, `engine` is mapped (`"coded"` -> `"coded"`, `"grex-visual"` -> `"visual"`).
- **`mode: "visual"`** (legacy `engine: "grex-visual"`): First-class contract for **Grex Theme Builder** (`Step 3`). Instead of hand-coded `.grab.html` templates, a `visual` theme supplies:
  - `grex.elements.json` (validated `Grex JS v1.0.0` element tree per template slot: `home`, `single`, `archive`, `404`, `search`, and `parts`: `header`, `footer`, `card`, `sidebar`).
  - `tokens.css` / `createTheme` design token payload.
  - All `visual` element trees MUST pass `Grex JS v1.0.0` `securityRules` (`no-wrapper-div`, `csp-safe`, no `eval`, no raw `innerHTML`, no `javascript:` URLs).

### 2.2 Safe Theme ZIP & Directory Validation
Before a theme is registered in the `themes` table (via ZIP upload or directory import):

1. **Path Traversal & Symlink Rejection:**
   - Reject any archive entry or relative manifest path containing `..`, leading `/`, backslashes (`\`), null bytes, or symlinks resolving outside `themes/<slug>/`.
2. **Sensitive & Disallowed File Rejection:**
   - Reject hidden/sensitive paths (`.git`, `.env`, `.ssh`, `*.pem`, `*.key`, `.DS_Store`).
   - Reject disallowed executable/server extensions inside theme packages: `.exe`, `.dll`, `.so`, `.dylib`, `.sh`, `.bat`, `.cmd`, `.ps1`, `.py`, `.php`, `.rb`, `.pl`, `.go`, `.wasm`.
   - Allowed extensions inside a theme package are strictly: `.json`, `.grab.html`, `.css`, `.js` (only under `assets/` and CSP-safe), `.svg`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.woff2`.
3. **Size & Entry Bounds:**
   - Enforce maximum file count (`<= 250` files), maximum single file size (`<= 5 MB`), and maximum total uncompressed package size (`<= 25 MB`).
4. **Capability Allowlist (`GRAB-E401`):**
   - `capabilities` in `theme.json` may only request from the core allowlist: `["templates", "parts", "hooks:theme", "grex:visual", "assets:static"]`.
   - Any unrecognized or privileged capability (e.g., `fs:write`, `net:outbound`, `db:raw`, `exec:shell`) MUST fail validation immediately with `GRAB-E401` and leave the filesystem and database untouched.
5. **Manifest Integrity:**
   - `slug` must match the target directory name `themes/<slug>/` and pass `is_valid_theme_slug`.
   - Every declared path in `templates`, `parts`, and `assets` must exist inside the validated package and pass confinement checks.

### 2.3 Atomic Hot-Switch Engine
Activating a theme (`activate_theme(slug)`) executes inside a `use data` transaction:
1. Verify `slug` exists in `themes` and passes manifest validation.
2. Execute `UPDATE themes SET is_active = 0` (deactivating the prior theme).
3. Execute `UPDATE themes SET is_active = 1 WHERE slug = :slug`.
4. Upsert `site_settings.active_theme_slug = :slug`.
5. Commit transaction, then:
   - Reload the active theme's manifest and re-register only the active theme's allowed hooks/filters (clearing all hooks from the prior theme).
   - Invalidate `use cache` keys: `theme:active`, `theme:parts:*`, `route:*`, and `query:*`.
   - Serve static assets exclusively from `/static/themes/<active_slug>/...` via `server.asset` (`--read-only` root compatible).

---

## 3. Reusable Template Parts (`header`, `footer`, `card`, `sidebar`)

### 3.1 Named Part Registry
Active themes register reusable template parts under `manifest.parts`:
- Standard part keys: `header`, `footer`, `card`, `sidebar` (plus optional theme-defined named parts matching `^[a-z0-9_-]{1,64}$`).
- **Fallback Behavior:** If a theme does not define an optional part (e.g., `sidebar`), core returns an empty fragment `""` cleanly without throwing a template error. `header` and `footer` are required for `coded` themes unless explicitly marked `null` for minimal/landing templates.

### 3.2 Zero Wrapper-`<div>` Rendering Contract
- **Coded Themes (`.grab.html`):** Core provides `render_part(part_name, context)` which resolves the active theme's part file, binds scoped context (`site`, `nav`, `entry`, `query_item`, `theme`), and injects the rendered semantic HTML directly at the call site without wrapping it in an extra `<div>`.
- **Visual Themes (`mode: "visual"` / `Grex JS v1.0.0`):**
  - Parts are stored as validated `grex.elements.json` fragment trees (`"type": "fragment"` or semantic root element such as `<header>`, `<footer>`, `<article>`, `<aside>`).
  - `Grex JS` renders fragments directly into the parent slot without wrapper `<div>` elements (`securityRules: ["no-wrapper-div", "csp-safe"]`), preserving clean semantic DOM and CSS Grid/Flexbox layouts.

---

## 4. Native Hooks & Filters Registry

### 4.1 Scope & Zero-Plugin Security Boundary
GrabLab `v0.2.0` introduces a deterministic in-process registry with four core primitives:
- `registerHook(hook_name, source, priority, handler_name)`
- `runHook(hook_name, payload)`
- `registerFilter(filter_name, source, priority, handler_name)`
- `applyFilter(filter_name, value, context)`

**Strict Security Rules:**
- **Allowed Sources:** Only `"core"` (GrabLab Core `.grab` modules) and `"theme:<active_slug>"` (declarative/allowlisted handlers declared by the **currently active theme**) may register hooks or filters.
- **No Arbitrary Code Eval:** Handlers are named references to pre-compiled `.grab` functions or declarative core transformations—never raw strings, eval'd JS, or third-party plugin files.
- **Automatic Theme Isolation:** On theme hot-switch, all entries where `source != "core"` are purged before loading the new active theme's registrations. Inactive themes have **zero** active hooks or filters.

### 4.2 Deterministic Priority Ordering
- `priority` is a `GrabInteger` (default `10`; lower numbers run first, e.g., `1` runs before `10`, which runs before `50`).
- Ties on `(hook_name, priority)` are broken deterministically by registration order (`sequence_id` ascending), ensuring identical execution order across all **Grisp** workers.

### 4.3 Core Lifecycle Hooks & Filters (`v0.2.0`)
| Name | Kind | When Fired | Payload / Filtered Value |
| --- | --- | --- | --- |
| `content:before_save` | Filter | Before inserting or updating an entry | Entry draft record (allows normalization, excerpt generation, field defaults) |
| `content:after_publish` | Hook | After an entry transitions to or saves as `published` | Published entry record + `content_type` (triggers cache invalidation & audit log) |
| `theme:head_meta` | Filter | Before rendering `<head>` metadata | Array/record of meta tags, canonical URL, OpenGraph tags, active theme CSS links |
| `theme:before_render` | Hook | Before rendering any public template (`home`, `single`, `archive`, `search`, `404`) | Render context (`route`, `theme`, `entry` or `archive_type`) |
| `query:modify_args` | Filter | Before `query_entries` executes prepared SQL | Normalized query arguments (`content_type`, `status`, `limit`, `page`, `sort`, `filters`) |

---

## 5. Query Loop Engine (`query_entries` + `use cache` Invalidation)

### 5.1 Structured, Injection-Safe Query Parameters
Both coded themes (`.grab.html` archives/partials) and **Grex Theme Builder** visual Query Loops (`ForEach` + `useQuery`) invoke `query_entries(args)` (and HTTP `GET /api/query` for client-side Grex hydration):

| Parameter | Type | Default | Constraints & Validation |
| --- | --- | --- | --- |
| `content_type` | `text` | `""` (all) | Optional `content_types.slug`; validated against `is_valid_slug` |
| `status` | `text` | `"published"` | Public routes force `"published"`; admin/preview contexts may request `"draft"` or `"archived"` |
| `field_key` | `text` | `""` | Optional custom field key (`is_valid_field_key`) to filter on |
| `field_op` | `text` | `"eq"` | Allowlisted operators only: `"eq"`, `"neq"`, `"contains"` |
| `field_value` | `text` | `""` | Parameterized string value bound to prepared SQL |
| `sort_by` | `text` | `"published_at"` | Allowlisted columns only: `"published_at"`, `"created_at"`, `"updated_at"`, `"title"`, `"id"` |
| `sort_dir` | `text` | `"desc"` | Allowlisted only: `"asc"` \| `"desc"` |
| `page` | `integer` | `1` | `GrabInteger >= 1` |
| `per_page` | `integer` | `10` | `GrabInteger` clamped to `1..100` |

### 5.2 Prepared SQL Execution Contract (`use data`)
- **Zero Dynamic SQL Concatenation:** All combinations of `sort_by` + `sort_dir` and optional `content_type` / `status` / custom-field filtering map to pre-registered literal prepared statements (`data.prepare`) at startup.
- **Custom Field Filtering:** Custom field filters match against `entries.custom_fields_json` using parameterized SQLite `json_extract` / PostgreSQL `::jsonb ->> :field_key` / MariaDB `JSON_UNQUOTE(JSON_EXTRACT(...))` bindings, or bounded in-memory post-filter on exact `GrabInteger`/`GrabDecimal` values when cross-DB parity requires it—never string-interpolated SQL.
- **Response Envelope:**
  ```json
  {
    "items": [ { "id": 1, "slug": "...", "full_path": "...", "title": "...", "custom_fields": {}, "published_at": "..." } ],
    "pagination": {
      "page": 1,
      "per_page": 10,
      "total_items": 24,
      "total_pages": 3,
      "has_prev": false,
      "has_next": true
    }
  }
  ```
- **Grex JS `v1.0.0` Integration:** Visual Query Loops bind `useQuery("/api/query?...")` directly into `ForEach` using the active theme's `card` template part, without wrapper `<div>` elements.

### 5.3 Deterministic `use cache` Invalidation
- **Cache Key Format:** `query:<active_theme_slug>:<content_type>:<status>:<sort_by>:<sort_dir>:<page>:<per_page>:<field_hash>`
- **Automatic Invalidation Triggers:**
  1. `content:after_publish` (or any entry create/update/delete/status change) invalidates all `query:*` and `route:*` keys for the affected `content_type` and global queries.
  2. Custom type or `field_definitions` updates invalidate `query:*`.
  3. `activate_theme(slug)` invalidates `theme:active`, `theme:parts:*`, `route:*`, and `query:*`.

---

## 6. Acceptance & Test Gates

Milestone `v0.2.0` cannot be marked complete until all gates pass **100%**:

1. **GRAB Compiler & Format Gate:**
   - `grab check` passes on all `.grab` and `.grab.html` files with zero errors.
   - `grab format --check` confirms canonical formatting across all `.grab` files.
2. **Theme Import Security Rejection Tests:**
   - Rejects ZIP/directory manifests with `..`, backslashes, symlinks escaping theme root, `.git`/`.env`/`.key` files, disallowed executable extensions (`.sh`, `.exe`, `.php`, `.go`), oversized payloads, and unauthorized capabilities (`GRAB-E401`).
3. **Exclusive Hot-Switch Tests:**
   - Switching from `default-starter` to a second test theme (including a `mode: "visual"` Grex contract theme) atomically sets `is_active = 0` on the old theme, `is_active = 1` on the new theme, updates `site_settings.active_theme_slug`, and serves zero assets or hooks from the deactivated theme.
4. **Template Parts & Zero Wrapper-`<div>` Tests:**
   - `header`, `footer`, `card`, and `sidebar` render cleanly inside coded `.grab.html` and visual `grex.elements.json` layouts with no synthetic wrapper `<div>` elements.
5. **Hooks & Filters Priority & Isolation Tests:**
   - `registerHook` / `runHook` and `registerFilter` / `applyFilter` execute in exact ascending `priority` order (`1` -> `10` -> `50`) with deterministic tie-breaking.
   - Inactive theme hooks never fire; disallowed/unregistered hook sources are rejected.
6. **Query Loop & `use cache` Invalidation Tests:**
   - `query_entries` filters accurately by `content_type`, `status`, and custom fields, paginates with exact `GrabInteger` counts, and rejects invalid `sort_by`/`field_op` inputs.
   - Publishing or updating an entry immediately invalidates cached `query_entries` responses so subsequent reads reflect fresh data.
