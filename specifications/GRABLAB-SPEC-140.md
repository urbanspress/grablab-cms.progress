# GRABLAB-SPEC-140: `v1.4.0` — Author Mode Book & Series Publishing Module + Embedded Bestseller Radar

**Status:** Approved target; specification in review *(Stage 1 Spec-First Approval Gate — no `v1.4.0` application code may be written until explicit project-owner approval and Stage 2 cross-layer contract audit pass).*  
**Baseline:** GrabLab CMS `v1.1.0` (frozen `GRABLAB-SPEC-110` + `GRABLAB-SPEC-100`), GRAB `v1.1.0`, Grex JS `v1.0.0`, Grex Theme Builder `v1.0.0`  
**SemVer Tier:** `MINOR 1.x.0 — Backwards-Compatible Feature Release` (`ADR-027c`)  
**Interoperates With:** `Groxy AI v1.7.0` (Multi-Genre Storytelling Brain, Hemingway Readability Auditor, `schema.org/Book` & `BookSeries` JSON-LD), `Groxy AI v1.8.0` (Bestseller Radar & `gsc.readonly`), `Plotific Press` (book storefront), `Grex Theme Builder v1.0.0`  
**GRAB core changes required:** **None.** Every capability below runs on frozen GRAB `v1.1.0` (`use data`, `use cache`, `use crypto`, `use http` with `GRAB-E402` outbound allowlisting, `server.asset`, `grab mcp`).

---

## 1. Purpose, Scope & Non-Goals

Adds a native, zero-plugin **Author Mode Book & Series Publishing Module** and **Embedded Bestseller Radar** to GrabLab CMS (`GRABLAB-EXPERT.md` §1): first-class `Author`, `Series`, `Book`, and `Chapter` content types, additive Migration `005` (SQLite, PostgreSQL, MariaDB parity), exact `ADR-025c` base-10 pricing/royalty wire types, direct `v1.1.0` digital/physical product linkage (`download_grants` + `LULU-USPS-001`), XSS-safe `schema.org/Book` & `BookSeries` JSON-LD, `slug_history` `301` redirects, and an embedded `/admin/author/radar` bridge to `Groxy AI v1.7.0` + `v1.8.0`—all rendered with pure `Grex JS v1.0.0` (`divCount === 0`, `innerHTMLWriteCount === 0`).

**In scope:** Migration `005` (`SQLite`/`PostgreSQL`/`MariaDB`), native `author`/`series`/`book`/`chapter` content types, `v1.1.0` commerce product/fulfillment linkage, `schema.org/Book` & `BookSeries` JSON-LD serializer, `/api/admin/author/*` + `/books*` + `/series*` routes, `/admin/author/radar` Groxy AI bridge, two additive MCP tools, pure `Grex JS v1.0.0` admin & reader views, and Section 9 verification suites.

**Non-goals / Never in scope:**
- Third-party plugin loaders or arbitrary runtime script evaluation (`GRABLAB-EXPERT.md` §1).
- Auto-publishing AI-generated outlines, chapters, or radar briefs (`status_enforced: "draft"` is mandatory).
- Silent overwriting of live human manuscripts.
- Modifying frozen `v1.0.0`, `v1.0.1`, or `v1.1.0` schemas, endpoints, or core GRAB `v1.1.0` / `grex-js v1.0.0` source files.

### 1.1 Compatibility Guarantees
- Migrations `001`–`004` and all `SPEC-100` / `SPEC-110` routes, MCP tools, and schemas remain **unchanged**. A `v1.1.0` site upgrades by running Migration `005` only.
- Author Mode is **off by default** (`author_mode_enabled = 0` in `site_settings`); until enabled, all `/api/admin/author/*`, `/admin/author*`, `/books*`, and `/series*` routes return `404` and the admin navigation hides Author Mode items.
- The default `grab.platform.json` remains **unchanged**; outbound calls to `Groxy AI` (`v1.7.0` / `v1.8.0`) are opt-in and strictly governed by `GRAB-E402` exact-origin allowlisting.

---

## 2. Exact-Number Wire Rules & Identifier Validation (`ADR-025c`)

| Concept | Wire Type | Example | Rule |
|---|---|---|---|
| Book list price, digital price, unit cost, USPS postage, net margin | `GrabDecimal` string, 2 fraction digits | `"14.99"` | Regex `^(0|[1-9][0-9]{0,6})\.[0-9]{2}$` (`"0.00"`–`"9999999.99"`). |
| Royalty rate percentage | `GrabDecimal` string, 2 fraction digits | `"70.00"` | `"0.00"`–`"100.00"`; stored internally as `royalty_rate_bp` (`GrabInteger` `0..10000`). |
| `series_position`, `chapter_number`, `word_count`, `page_count`, `reading_minutes`, `sort_order` | `GrabInteger` | `1`, `4200`, `284` | Whole JSON integer or base-10 string; no fraction or exponent. |
| `isbn_13` | Canonical 13-digit string | `"9781955555012"` | Optional; when provided, strips `-`/spaces and validates exact 13 digits + GS1/ISBN-13 check digit. Bad checksum → `422`. |
| `asin` | 10-char uppercase alphanumeric string | `"B0DRTEST01"` | Optional; when provided, must match `^[A-Z0-9]{10}$`. Malformed → `422`. |
| Currency | ISO-4217 string | `"USD"` | Matches `site_settings.currency` (`"USD"`). |

1. **JS floats are rejected:** GRAB's lossless `json.parse` distinguishes `decimal` from `integer` and `string`. Any `decimal`-kind or scientific-notation value in a money, royalty, or integer field → HTTP `422` `{error: "author_validation_failed", field, reason: "float_not_allowed"}`.
2. **Integer internal math:** All price/royalty calculations use integer cents and basis points (`GrabInteger`), converting to `GrabDecimal` strings only at the API/JSON-LD boundary. No IEEE-754 float is ever computed or stored.
3. **Money inputs in UI:** Admin forms use `<Input type="text" inputmode="decimal">` and submit exact strings—never `<input type="number">`.

---

## 3. Additive Migration `005` & Native Author Content Types (`ADR-024f`)

### 3.1 Migration Files (Additive, Idempotent)
| File | Schema Versions | Target |
|---|---|---|
| `migrations/005_author_schema.grab` | `[1, 2, 3, 4, 5]` | SQLite (primary) |
| `migrations/005_author_schema_postgres.grab` | `[1, 2, 3, 4, 5]` | PostgreSQL |
| `migrations/005_author_schema_mariadb.grab` | `[1, 2, 3, 4, 5]` | MariaDB |

Each uses `data.migrate`, creates only new tables (`IF NOT EXISTS`), never alters or drops tables from `001`–`004`, and records schema version `5`. Running `005` directly on an empty database equals `001 → 002 → 003 → 004 → 005` (`SPEC-100` §2 parity). `seed.grab` and `seed_commerce.grab` are **not** modified; optional author seeds live in `migrations/seed_author.grab`.

### 3.2 Tables
| Table | Key Columns | Notes |
|---|---|---|
| `authors` | `id`, `entry_id` (unique FK → `entries`), `pen_name`, `bio_summary`, `website_url`, `social_links_json`, `active`, `created_at`, `updated_at` | Represents an author profile (`content_type = author`). |
| `series` | `id`, `entry_id` (unique FK → `entries`), `author_id` (FK → `authors`), `genre_slug`, `reading_order_mode` (`chronological` \| `publication`), `total_planned_books`, `active`, `created_at`, `updated_at` | Groups books in deterministic reading order (`content_type = series`). |
| `books` | `id`, `entry_id` (unique FK → `entries`), `author_id` (FK → `authors`), `series_id` (nullable FK → `series`), `series_position` (nullable `INTEGER`), `subtitle`, `isbn_13`, `asin`, `edition_format` (`ebook` \| `paperback` \| `hardcover` \| `bundle`), `page_count`, `word_count`, `in_language`, `genre_slug`, `blurb`, `list_price_cents`, `royalty_rate_bp`, `currency`, `product_id` (nullable FK → `products`), `cover_media_id` (nullable FK → `media`), `active`, `created_at`, `updated_at` | Core book record (`content_type = book`), optionally linked to a `v1.1.0` `products` row. |
| `chapters` | `id`, `entry_id` (unique FK → `entries`), `book_id` (FK → `books`), `chapter_number`, `sort_order`, `is_sample` (0/1), `word_count`, `reading_minutes`, `cliffhanger_hook`, `readability_grade_bp` (nullable `INTEGER`), `readability_score` (nullable `INTEGER`), `created_at`, `updated_at` | Ordered manuscript chapters (`content_type = chapter`); `is_sample = 1` exposes a free public reader preview. |
| `author_radar_imports` | `id`, `radar_plan_id` (unique), `genre_slug`, `target_type` (`series` \| `book` \| `chapter`), `entry_id` (FK → `entries`), `payload_sha256`, `imported_by`, `created_at` | Single-winner idempotency & audit ledger for Bestseller Radar / Author Studio imports. |

Indexes: `idx_authors_entry`, `idx_series_author`, `idx_books_author`, `idx_books_series_pos`, `idx_books_isbn`, `idx_books_product`, `idx_chapters_book_sort`, `idx_radar_imports_plan`.

### 3.3 Native Content Types & `v1.1.0` Commerce Linkage
- Registers four native content types in `content_types`:
  - `author` (`/authors/:slug`)
  - `series` (`/series/:slug`)
  - `book` (`/books/:slug`)
  - `chapter` (`/books/chapter/:slug`, or resolved under `/books/:book_slug/sample/:chapter_slug` for public sample previews)
- Because every `Author`, `Series`, `Book`, and `Chapter` is backed by an `entries` row, it natively inherits drafts (`status: "draft"`), RBAC, `slug_history` `301` redirects, and `use cache` invalidation.
- **Direct `v1.1.0` Commerce Linkage (`books.product_id → products.id`):**
  - **Digital Editions (`ebook`):** Linked `products` row (`kind = "digital"`) attaches DRM-free EPUB/PDF assets via `product_digital_files` (`media_id → media`), fulfilling orders through `v1.1.0` hashed `download_grants` (`Cache-Control: no-store`, bounded `download_limit` and `expiry_hours`).
  - **Physical Editions (`paperback` / `hardcover`):** Linked `products` row (`kind = "physical"`) attaches a `product_fulfillment` row enforcing **`LULU-USPS-001`** (`carrier = "lulu_direct"`, `lulu_sku = "LULU-USPS-001"` for matte paperback print-on-demand) or **`carrier = "usps"`** (`usps_service` in `ground_advantage | priority | media_mail`, `max_weight_g <= 31751`, `media_mail_eligible = 1`, `ships_from_country = "US"`).
  - **`products` remains the single source of truth for checkout (`SPEC-110` §3.3):** Updating a book's `list_price_cents` does not silently mutate open carts; syncing a linked `products.price_cents` requires an explicit admin/editor action (`POST /api/admin/author/books/:id/sync-product`) with `X-CSRF-Token` and `commerce:manage`.

---

## 4. XSS-Safe `schema.org/Book` & `BookSeries` JSON-LD + `slug_history` 301 Redirects

### 4.1 `schema.org/Book` & `BookSeries` JSON-LD Renderer
Public `/books/:slug` and `/series/:slug` templates emit structured data inside `<script type="application/ld+json">`:
- **XSS-Safe Serialization:** All serialized JSON strings MUST escape `</script>` (as `<\/script>`), `<` (`\u003c`), `>` (`\u003e`), `&` (`\u0026`), U+2028 (`\u2028`), and U+2029 (`\u2029`) so untrusted book titles, blurbs, or author names can never break out of `<script>`.
- **`schema.org/Book` Fields:** `@context` (`"https://schema.org"`), `@type` (`"Book"`), `name`, `author` (`@type: "Person"`, `name`), `bookFormat` (`https://schema.org/EBook` | `https://schema.org/Paperback` | `https://schema.org/Hardcover`), `isbn` (when present), `numberOfPages` (integer), `inLanguage` (BCP-47), `genre`, `isPartOf` (`@type: "BookSeries"`, `name`, `position` when in a series), and `offers` (`@type: "Offer"`, `priceCurrency: "USD"`, `price` as exact `ADR-025c` `GrabDecimal` string, `availability`).
- **`schema.org/BookSeries` Fields:** `@context` (`"https://schema.org"`), `@type` (`"BookSeries"`), `name`, `author`, `genre`, and ordered `hasPart` array of `Book` summaries with `position`.

### 4.2 `slug_history` 301 Redirects & Cache Invalidation
- Renaming any `author`, `series`, `book`, or `chapter` slug records the previous path in `slug_history` and serves an automatic `301 Moved Permanently` to the new canonical URL.
- Reserved system prefixes (`/admin`, `/api`, `/static`, `/_health`, `/_ready`, `/shop`) are strictly protected from slug collisions (`409`).
- Any create/update/reorder/publish action deterministically invalidates `use cache` keys (`author:book:<id>`, `author:series:<id>`, `author:chapter:<id>`, and route keys).

---

## 5. Embedded Bestseller Radar & Author Co-Writer Bridge (`Groxy AI v1.7.0` + `v1.8.0`)

### 5.1 Admin Author & Radar Endpoints (`/api/admin/author/*`)
All `/api/admin/author/*` routes require an authenticated admin/editor/author session cookie + `X-CSRF-Token` (`403` on missing/invalid CSRF). **MCP Bearer tokens are rejected with `401`** on `/api/admin/author/*` (matching `SPEC-110` §4.1).

| Route | Capability | Purpose |
|---|---|---|
| `GET /api/admin/author/books` | `author:manage` | List books, series assignments, ISBN/ASIN, and linked `v1.1.0` product/fulfillment status. |
| `POST /api/admin/author/books` | `author:manage` | Create/update book metadata (`ADR-025c` `GrabDecimal`/`GrabInteger`, `ISBN-13`/`ASIN` validation). |
| `POST /api/admin/author/books/:id/sync-product` | `author:manage` + `commerce:manage` | Link or sync a book to a `v1.1.0` `products` + `product_digital_files` / `product_fulfillment` (`LULU-USPS-001`) row. |
| `POST /api/admin/author/series` & `/reorder` | `author:manage` | Create series and atomically update `series_position` reading order inside a `data.begin` transaction. |
| `POST /api/admin/author/chapters` & `/reorder` | `author:manage` | Create/update chapters, toggle `is_sample`, and persist deterministic reading order. |
| `POST /api/admin/author/radar/query` | `author:manage` | Bridges to `Groxy AI v1.8.0` (`POST /api/groxy/research/bestseller-radar`) and `v1.7.0` (`GET /api/groxy/author/genres`) over a `GRAB-E402`-allowlisted origin (`cache.limit` rate-limited). |
| `POST /api/admin/author/radar/import` | `author:manage` | Verifies `payload_sha256` + single-use `rtok_res_<hex>` / `atok_<hex>` token, atomically claims `author_radar_imports.radar_plan_id` (`409` on replay/race), and creates `Series`/`Book`/`Chapter` drafts strictly with **`status_enforced: "draft"`**. |
| `POST /api/admin/author/readability-audit` | `author:manage` | Bridges chapter prose to `Groxy AI v1.7.0` (`POST /api/groxy/author/readability-audit`) and stores optional non-destructive grade/score metrics on the draft chapter. |
| `POST /api/admin/author/settings` | `author:settings` (`admin` only) | Toggle `author_mode_enabled`, configure `GRAB-E402`-validated `groxy_ai_origin` (`https://` or `http://127.0.0.1:<port>` for local Groxy worker). |

### 5.2 Outbound Safety (`GRAB-E402`) & Draft-Only Enforcement
- **Origin Allowlist (`GRAB-E402`):** GrabLab validates `groxy_ai_origin` at save time and before every bridge request (rejecting unallowlisted hosts, `file://`, `javascript:`, userinfo, and metadata IPs `169.254.169.254` with `422`/`502`).
- **Draft-Only Import (`status_enforced: "draft"`):** Imported `Series`, `Book`, and `Chapter` outlines from Bestseller Radar or Groxy Storytelling Brain are **always** inserted with `status = 'draft'`. Human authors review, edit, and publish explicitly.
- **Two Additive MCP Tools:**
  - `list_author_catalog` (`author:manage`, read-only): returns `series`, `books`, and `chapters` metadata so Groxy AI can verify continuity without touching live drafts.
  - `create_book_draft` (`author:manage`): creates a `book` + optional `chapter` outline strictly with `status_enforced: "draft"` (cannot set `status: "published"` or mutate `products` prices/stock).

---

## 6. Pure `Grex JS v1.0.0` Author & Reader Views

All new `.grab.html` templates and JS modules (`public/admin/author.js`, `public/author/reader.js`) use **strictly** the 20 semantic elements in `grex.elements.json` and semantic HTML5 (`<main>`, `<article>`, `<section>`, `<nav>`, `<dialog>`, `<details>`):
- **Admin Views:**
  - `/admin/author` — Author Mode dashboard (books, series, sample chapters, linked store status).
  - `/admin/author/books` — Book editor (`ISBN-13`, `ASIN`, `ADR-025c` decimal price/royalty text inputs, `LULU-USPS-001` / EPUB-PDF product linker).
  - `/admin/author/series` — Series manager & keyboard/drag-and-drop reading-order sequencer.
  - `/admin/author/chapters` — Chapter sequencer, `is_sample` toggle, and Hemingway Readability Auditor panel.
  - `/admin/author/radar` — **Embedded Bestseller Radar & Genre Profit Panel** (`Groxy AI v1.8.0` profit-ranked genres, unit economics in exact `GrabDecimal` USD, and 1-click draft import confirmation `<dialog>`).
- **Public Reader Views:**
  - `/books` (catalog), `/books/:slug` (book page + `schema.org/Book` JSON-LD + buy/download CTA), `/series/:slug` (reading-order grid + `schema.org/BookSeries` JSON-LD), and `/books/:slug/sample/:chapter_slug` (distraction-free pure-Grex Web Reader with Light/Dark theme toggle).
- **Zero-DOM-Debt & Accessibility:** `divCount === 0`, `innerHTMLWriteCount === 0`, zero `eval()`/`new Function()`, zero unsafe URL schemes, keyboard navigation (`Enter`/`Space`/`Escape`), and `100%` `auditAccessibility()` pass across Light and Dark themes (`>= 4.5:1` normal text, `>= 3.0:1` large text).

---

## 7. Security, Privacy & Deployment Notes

- **Capabilities:** `author:manage` (`admin`, `editor`, `author` scoped to own entries; `viewer` rejected with `403`) and `author:settings` (`admin` only).
- **Rate Limits (`cache.limit`):** Radar/readability bridge calls bounded per user/IP (`429` on burst).
- **Logging:** Never log session cookies, CSRF secrets, `rtok_res_` / `atok_` approval tokens, or download grant tokens.
- **`--read-only` Container Compatibility:** Zero writes outside configured writable `storage/` and `uploads/` mounts; `server.asset` hashes static JS/CSS in memory.
- **Stable Branch Protection:** `v1.4.0` work stays strictly on `origin` (`urbanspress/grablab-cms.progress`) until all Section 9 gates pass 100%; `stable` remains untouched at `v1.1.0`.

---

## 8. Implementation Order (After Owner Approval & Stage 2 Audit)

1. Migration `005` (`SQLite`, `PostgreSQL`, `MariaDB`) + `migrations/seed_author.grab`.
2. `ADR-025c` numeric, `ISBN-13`, and `ASIN` validators + `schema.org/Book` & `BookSeries` XSS-safe JSON-LD serializer.
3. Native `author`, `series`, `book`, `chapter` CRUD, reading-order transactions, `slug_history` `301`s, and `v1.1.0` `products` / `LULU-USPS-001` / `download_grants` linkage.
4. `/api/admin/author/radar/*` & `/readability-audit` `GRAB-E402` bridge + `author_radar_imports` single-winner ledger + `list_author_catalog` / `create_book_draft` MCP tools.
5. Pure `Grex JS v1.0.0` `/admin/author*` views (including `/admin/author/radar`) and public `/books*` / `/series*` / sample Web Reader views.
6. New test suites (`tests/author_test.py`, `tests/release_v140_test.py`, `tests/author_dom_audit.mjs`), full regression, walkthrough PDF (`docs/releases/pdf/GrabLab-v1.4.0-Guide.pdf`), and Ecosystem Compatibility Matrix.

---

## 9. Section 9 Acceptance Gates (All Must Pass 100%)

1. **`grab check`:** Zero errors across every `.grab` and `.grab.html` file (including Migration `005`, routes, and views).
2. **Canonical format:** `grab format <file>` stdout byte-identical to on-disk bytes for every `.grab` file.
3. **Zero-DOM-debt:** `divCount === 0` and `innerHTMLWriteCount === 0` across all `/admin/author*`, `/books*`, `/series*`, and Web Reader views; zero `eval`/`new Function`; zero unsafe URL schemes.
4. **Accessibility:** `auditAccessibility()` passes `100%`; Light **and** Dark contrast `>= 4.5:1` (normal text), `>= 3.0:1` (large text).
5. **Numeric & Identifier Fidelity (`422`):** Floats/exponents in any price, royalty, or integer field rejected with `422`; invalid `ISBN-13` check digits and malformed `ASIN` rejected with `422`; `"14.99"` and `"70.00"` round-trip byte-exact across SQLite, PostgreSQL, and MariaDB.
6. **Authorization (`401`/`403`):** Missing/invalid `X-CSRF-Token` → `403`; `viewer` on mutating author routes → `403`; `editor`/`author` on `/api/admin/author/settings` → `403`; MCP Bearer token on `/api/admin/author/*` → `401`.
7. **Radar & Concurrency (`409`):** Concurrent/replayed `/api/admin/author/radar/import` with the same `radar_plan_id` or `rtok_res_<hex>` yields **exactly one `201` winner** and **`409` for all losers/replays**; imported entries always land as `status: "draft"`; `GRAB-E402` blocks unallowlisted/SSRF `groxy_ai_origin` URLs.
8. **XSS & JSON-LD Safety:** Titles/blurbs containing `</script><script>alert(1)</script>` are safely escaped in `schema.org/Book` & `BookSeries` `<script type="application/ld+json">` blocks.
9. **`slug_history` & Cache:** Renaming a book, series, author, or chapter slug emits a `301` redirect to the new canonical URL and invalidates `use cache` keys cleanly.
10. **Commerce Linkage (`v1.1.0`):** Digital book purchase issues valid hashed `download_grants`; physical book linkage enforces `LULU-USPS-001` / `usps` carrier constraints without breaking `v1.1.0` checkout.
11. **Regression & New Suites:** Existing `tests/integration_test.py` (13/13), `tests/release_v100_test.py` (5/5), `tests/commerce_test.py` (9/9), and `tests/release_v110_test.py` (5/5) pass unchanged; new `tests/author_test.py`, `tests/release_v140_test.py`, and `tests/author_dom_audit.mjs` pass **100%**.
