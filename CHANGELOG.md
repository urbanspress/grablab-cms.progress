# Changelog

All notable releases of **GrabLab CMS** (`urbanspress/grablab-cms`) are documented in this file.

## `[v1.5.0]` — 2026-11-19

- Added the six-tab User Profile Studio for all authenticated roles. Users can edit their display name, choose a local portrait, change their password, revoke other sessions and export their account details.
- Updated the two-tier admin header, Posts and Pages navigation, local Urbanist typography, Light/Dark themes and expandable profile cards.
- Verified both GRAB platform profiles, the DOM and regression suites, and concurrent checkout and author import. Existing databases and adjacent ecosystem layers need no upgrade.

## `[v1.4.1]` — 2026-11-18 (PostgreSQL 18 Taxonomy Query Compatibility Patch)

### Fixed
- **PostgreSQL 18 `DISTINCT` + `ORDER BY COALESCE(...)` Compatibility (`src/app.grab`, `tests/release_v140_test.py`):**
  - Replaced `SELECT DISTINCT ... INNER JOIN entry_terms ... ORDER BY COALESCE(e.published_at, e.created_at) DESC, e.id DESC` in `stmt_query_entries_by_term` with `WHERE EXISTS (SELECT 1 FROM entry_terms et WHERE et.entry_id = e.id AND et.term_id IN (:t0, ..., :t15))` so PostgreSQL 18 executes taxonomy archive and term-filtered queries without error while preserving SQLite/MariaDB/PostgreSQL multi-term deduplication.
  - Added regression assertions verifying `EXISTS (...)` prepared SQL structure and multi-term (`pg18-parent` + `pg18-child`) deduplication in `tests/release_v140_test.py`.
- **Documentation & Release Artifacts:**
  - Generated [`docs/releases/pdf/GrabLab-CMS-v1.4.1-Guide.pdf`](docs/releases/pdf/GrabLab-CMS-v1.4.1-Guide.pdf), [`docs/releases/pdf/GrabLab-CMS-v1.4.1-RELEASE-NOTES.md`](docs/releases/pdf/GrabLab-CMS-v1.4.1-RELEASE-NOTES.md), and `dist/grablab-cms-v1.4.1-bundle.zip` (`SHA256SUMS.txt`).

---

## `[v1.4.0]` — 2026-11-18 (Author Mode Book & Series Publishing Module + Embedded Bestseller Radar)

### Added
- **Additive Migration `005` & Native Author Content Types (`migrations/005_author_schema*.grab`, `migrations/seed_author.grab`):** Added `authors`, `series`, `books`, `chapters`, and `author_radar_imports` across SQLite, PostgreSQL, and MariaDB parity while keeping `001`–`004` schemas and `seed.grab` / `seed_commerce.grab` untouched. Author Mode stays off by default (`author_mode_enabled = "0"` -> `404` across `/api/admin/author/*`, `/admin/author*`, `/books*`, and `/series*`) until enabled by an administrator.
- **Exact `ADR-025c` Pricing/Royalty & Identifier Validation (`src/app.grab`):** Enforced exact base-10 `GrabDecimal` (`"0.00"`) and `GrabInteger` wire types with integer cent/basis-point calculations (`422` on raw JS floats or exponent notation), GS1 `ISBN-13` check-digit validation, `^[A-Z0-9]{10}$` `ASIN` validation, and reserved-prefix `409` slug guards.
- **Direct `v1.1.0` Commerce & Fulfillment Linkage (`POST /api/admin/author/books/:id/sync-product`):** Links digital books (`ebook`) to `products` + `product_digital_files` (DRM-free EPUB/PDF via hashed `download_grants` with `Cache-Control: no-store`) and physical editions (`paperback` / `hardcover`) to `product_fulfillment` (`LULU-USPS-001` matte paperback or USPS-only `ground_advantage` / `priority` / `media_mail` <= `31751 g`), preserving `products` as checkout source of truth and `409 price_changed` open-cart protection.
- **XSS-Safe `schema.org/Book` & `BookSeries` JSON-LD + `slug_history` `301`s (`src/app.grab`):** Escapes `</script>`, `<`, `>`, `&`, `U+2028`, and `U+2029` inside `<script type="application/ld+json">` on `/books/:slug` and `/series/:slug`, records slug renames in `slug_history` for `301` redirects, and deterministically invalidates `use cache` keys.
- **Embedded Bestseller Radar, Readability Bridge & Additive MCP Tools (`/admin/author/radar`, `src/app.grab`):** Bridges `/api/admin/author/radar/query`, `/radar/import`, and `/readability-audit` to `Groxy AI v1.7.0` + `v1.8.0` over `GRAB-E402`-allowlisted origins (`admin`-only `author:settings`, CSRF `403`, MCP Bearer `401` on `/api/admin/author/*`), enforces single-winner atomic `201`/`409` claiming on `author_radar_imports.radar_plan_id` (`status_enforced: "draft"`), and adds `list_author_catalog` + `create_book_draft` (`status_enforced: "draft"`) MCP tools.
- **Pure `Grex JS v1.0.0` Author Dashboard & Sample Web Reader (`public/admin/author.js`, `public/author/reader.js`, `public/author/reader.css`, `src/views/author/reader.grab.html`, `themes/default-starter/templates/{books,book,series}.grab.html`):** Delivered `/admin/author*` tabs (Overview, Books, Series Sequencer, Chapters & Readability, Bestseller Radar) and distraction-free sample chapter Web Reader with `divCount === 0`, `innerHTMLWriteCount === 0`, keyboard `Escape`/focus restoration, and Light & Dark WCAG AA contrast (`>= 4.5:1`).
- **Verification & Release Artifacts:** Added `tests/author_test.py`, `tests/release_v140_test.py`, `tests/author_dom_audit.mjs`, `docs/releases/pdf/GrabLab-CMS-v1.4.0-Guide.pdf`, `docs/releases/pdf/GrabLab-CMS-v1.4.0-RELEASE-NOTES.md`, and `dist/grablab-cms-v1.4.0-bundle.zip`.

---

## `[v1.1.0]` — 2026-11-17 (Zero-Plugin E-Commerce Core)

### Added
- **Additive Migration `004` & Commerce Schema (`migrations/004_commerce_schema*.grab`, `migrations/seed_commerce.grab`):** Added `products`, `product_digital_files`, `product_fulfillment`, `customers`, `carts`, `cart_items`, `coupons`, `coupon_redemptions`, `orders`, `order_items`, `order_audit`, `download_grants`, `idempotency_keys`, `payment_events`, and `commerce_events` with SQLite, PostgreSQL, and MariaDB parity while keeping `001`–`003` tables and `slug_history` `301` redirects intact.
- **Exact `ADR-025c` USD Money & Deterministic Totals Engine (`src/app.grab`, `tests/commerce_vectors.json`):** Implemented integer-cent storage and exact `"0.00"` `GrabDecimal` / `GrabInteger` wire serialization/validation rejecting floats and scientific notation with HTTP `422` (`float_not_allowed`), deterministic pro-rata coupon allocation, flat-rate shipping per carrier group, configurable tax tables, and `$99,999,999.99` total caps.
- **Cart, Coupons, Guest-First Checkout & USPS-Only Carrier Enforcement:** Added `GET /api/commerce/session`, `POST /api/commerce/cart`, `/coupon/apply`, `/checkout`, `GET /api/commerce/products`, `/shop`, `/shop/{slug}`, `/shop/cart`, `/shop/order/{number}?t=...`, and `GET /api/commerce/download/{token}` with opaque SHA-256-hashed cart/order/download tokens, CSRF rotation on login/logout, cart-scoped `Idempotency-Key` protection (`409` / `403` / `422`), conditional stock & coupon decrements, `409 price_changed` checks, USPS-only + `lulu_direct` fulfillment validation (`LULU-USPS-001`), ISBN-13 validation, and `GRAB-E402` allowlisted HTTPS payment redirects.
- **Opt-In GRAB Native Signed Webhook Profile (`deploy/grab.platform.commerce.json`, `deploy/connectors/grablab-payment/`):** Added opt-in signed payment webhook acceptance (`POST /api/commerce/webhooks/payment` -> `make receive_payment_event using event`) using GRAB `v1.1.0` HMAC-SHA256 verification without breaking zero-secret startup on default `grab.platform.json`.
- **Lazy Commerce Sweep & Opt-In Abandoned-Checkout Hook (`scripts/commerce_sweep.grab`):** Expires overdue `pending_payment` stock/coupon holds (`payment_due_by`), marks stale carts `abandoned`, and emits `commerce:abandoned_checkout` strictly when `marketing_consent = 1` with per-site salted `email_hash` alongside additive MCP tools `list_commerce_events` and `create_coupon_draft` (`active = 0` forced).
- **Pure `Grex JS v1.0.0` Storefront & Admin Commerce Views (`public/shop/shop.js`, `public/shop/shop.css`, `public/admin/commerce.js`):** Delivered `/admin/store` (Overview, Products, Orders + Audit Trail, Coupons, Customers + GDPR Export/Anonymize, Admin-Only Settings) and storefront templates with `divCount === 0`, `innerHTMLWriteCount === 0`, and Light & Dark WCAG AA contrast (`>= 4.5:1`).
- **Verification & Release Artifacts:** Added `tests/commerce_test.py`, `tests/release_v110_test.py`, `tests/commerce_dom_audit.mjs`, `docs/releases/pdf/GrabLab-CMS-v1.1.0-Guide.pdf`, `docs/releases/pdf/GrabLab-CMS-v1.1.0-RELEASE-NOTES.md`, and `dist/grablab-cms-v1.1.0-bundle.zip`.

---

## `[v1.0.1]` — 2026-11-14 (Cross-Layer Audit & Hardening Patch)

### Added
- **Vendored `grex.elements.json` Catalog Parity (`public/grex/grex.elements.json`):** Bundled `grex.elements.json` directly alongside `grex-js-v1.0.0.js`, `grex.js`, and `tokens.css` with verified SHA-256 parity to `C:\Development\grex-js\grex.elements.json` and exposed at `/static/grex/grex.elements.json`.
- **Extended `v1.0.1` Regression Coverage (`tests/release_v100_test.py`):** Verified `/static/grex/grex.elements.json` serving, JSON-RPC `-32602` error metadata on `422` validation failures, `SPEC-100` parameter aliases on `create_entry_draft` and `update_entry_layout`, WCAG AA contrast ratio (`GREX-A11Y-001`) and focus outline (`GREX-A11Y-005`) enforcement on `styles.base`, `Image` `decorative: true`, expanded semantic tags (`blockquote`, `time`, etc.), and `list_menus` `location` filtering.
- **Plain-English Patch Release Guide (`docs/releases/pdf/GrabLab-v1.0.1-Guide.pdf`):** Generated via `docs/releases/generate_v101_guide.py`.

### Fixed & Hardened
- **`grab mcp` `SPEC-100` Contract Parity & JSON-RPC `-32602` Metadata (`src/app.grab`):**
  - `query_entries` now forwards `content_type_slug`, `field_key`, `field_op`, `field_value`, `sort_by`, `sort_dir`, `page`, and `per_page` consistently (and filters/paginates properly for `author` callers).
  - `create_entry_draft` now supports `content_type_slug`, `body`, `excerpt`, and optional `grex_layout` / `layout` (validating layouts through `audit_grex_tree_walk` and rejecting violations with `422` / `-32602` while strictly enforcing `status: "draft"`).
  - `update_entry_layout` now accepts both `layout` and `grex_layout` and returns `code: -32602` + `mcp_error` metadata on `422` validation errors; JSON-RPC `POST /api/mcp` includes `errorCode: -32602` on `422` and `400` `tools/call` errors.
  - `list_menus` now honors the optional `location` filter.
- **`Grex Theme Builder v1.0.0` & WCAG AA Schema Parity (`src/app.grab`):** Expanded `is_allowed_grex_tag` to cover all `grex.elements.json` semantic tags (`small`, `strong`, `em`, `blockquote`, `time`, `code`, `svg`, `dialog`, `details`, `summary`, `textarea`, `tbody`, `figure`, `figcaption`); added `"type"` node alias and `"decorative": true` image support; enforced security checks on `attrs`, `srcdoc` (`GREX-SEC-SRCDOC`), `poster`/`cite` URLs, and CSS expressions (`GREX-SEC-CSS`); added WCAG AA contrast (`4.5:1` / `3.0:1` large text, `GREX-A11Y-001`) across inherited backgrounds and focus outline checks (`GREX-A11Y-005`) inside `styles` / `styles.base`.
- **`301` Self-Loop & Reserved-Target Guard (`src/app.grab`):** Guarded `resolve_public_path` against issuing `301` redirects where `target_path == norm_path` or targets a reserved system prefix.

---

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
