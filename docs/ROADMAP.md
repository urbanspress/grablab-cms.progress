# GrabLab CMS Roadmap

**Repositories:** `urbanspress/grablab-cms.progress` (active development) / `urbanspress/grablab-cms.stable` (verified releases)  
**Platform Runtimes:** GRAB `v1.1.0` + Grex JS `v1.0.0`

**Status Labels:**
- **Draft / In Review** — Specification drafted; awaiting owner approval before code implementation.
- **Approved** — Authorized by project owner for implementation.
- **Complete** — Implemented, `grab check` clean, 100% tests passing, and walkthrough guide generated.
- **Planned** — Upcoming milestone in the GrabLab CMS sequence.

---

## `v0.1` — Core Content Types, Custom Fields, Pretty Permalinks & 301 Slug History

**Status:** Complete (`specifications/GRABLAB-SPEC-001.md`)

Scope:
- `use data` schema & migrations for `site_settings`, `content_types`, `field_definitions`, `entries`, `slug_history`, and `themes` (SQLite-first, MariaDB/PostgreSQL-compatible, exact `GrabDecimal`/`GrabInteger` types).
- Content Type & Custom Field registry (built-in `page` and `post` plus user-defined types and typed custom fields).
- WordPress-style pretty permalink router (`/:slug` and type patterns like `/blog/:slug`) with reserved system-prefix protection (`/admin`, `/api`, `/static`, `/_health`, `/_ready`) and automatic `301 Moved Permanently` redirect history on slug changes.
- `theme.json` exclusive theme manifest contract & atomic single-active-theme switching.
- `use cache` invalidation keys for entries, routes, and active theme state.

---

## `v0.2` — Exclusive Theme Engine, Template Parts, Native Hooks/Filters & Query Loop Engine

**Status:** Complete (`specifications/GRABLAB-SPEC-002.md`)

Scope:
- **Exclusive Theme Engine:**
  - Safe coded theme import (`.grab` + `.grab.html` + `Grex JS v1.0.0` static assets via `server.asset` and `themes/<slug>/theme.json` validation).
  - First-class **Grex Visual Theme Contract** so **Step 3 (Grex Theme Builder)** installs as a selectable theme that disables any prior theme and takes 100% exclusive template rendering control (`home`, `single`, `archive`, `header`, `footer`, `404`, `search`).
- **Template Parts:** Reusable `header`, `footer`, `sidebar`, and partial `.grab.html` / Grex sections.
- **Native Hooks & Filters:** Deterministic core `.grab` lifecycle hooks/filters (e.g., `before_render`, `after_save_entry`, `head_meta`, `footer_scripts`) without third-party plugins.
- **Query Loop Engine:** Declarative, prepared-SQL query loops for archives, recent posts, filtered custom content types, and pagination.

---

## `v0.3` — Users, Roles/Capabilities, Auth & CSRF-Protected Admin Dashboard

**Status:** Complete (`specifications/GRABLAB-SPEC-003.md`)

Scope:
- `users`, `sessions`, and role/capability tables (`admin`, `editor`, `author`, `viewer`) with secure password hashing and session cookies (`HttpOnly`, `SameSite=Lax`, `Secure`).
- CSRF-protected Admin Dashboard built with `.grab.html` and `Grex JS v1.0.0` reactive components (`ForEach`, `Form`, `Tabs`, `Modal`, `createTheme`).
- **1-Click Theme / Grex Switcher:** Visual Themes dashboard allowing site owners to switch between installed coded themes and the **Grex Theme Builder** visual theme with instant atomic deactivation of the prior theme.
- **Optional Built-In OAuth2/PKCE Social Login Toggle:** Disabled by default (`0` social buttons rendered and `0` outbound network calls until enabled); administrators can toggle individual providers (**Google**, **GitHub**, **Discord**, **Apple**) in Admin Settings with encrypted/env-backed Client ID & Secret, `state` + PKCE verifier protection, verified email account linking, and strict Grisp `--allow-net` domain allowlists.
- Content editor, custom type/field manager, and permalink/redirect inspector.

---

## `v0.4` — Media Library, Menus, Taxonomies & `grab mcp` CMS Tools

**Status:** Complete (`v0.4.0`, `specifications/GRABLAB-SPEC-004.md`)

Scope:
- **Media Library:** Confined uploads under writable media mounts, MIME/extension allowlists, metadata (`alt`, dimensions), and cache-busted serving (`--read-only` root compatible).
- **Navigation Menus:** Ordered multi-level menu builder bound to active theme `header`/`footer` slots.
- **Taxonomies:** Categories, tags, and custom hierarchical/flat taxonomies with pretty archive permalinks.
- **`grab mcp` CMS Tools:** Schema/content-type/route inspection helpers so **Step 4 (`groxy-ai`)** can scaffold content types, entries, and Grex layouts safely.

---

## `v1.0.0` — Production CMS Release (`v1.0.1` Hardening Patch Current)

**Status:** Complete (`v1.0.1`, `specifications/GRABLAB-SPEC-100.md`)

Scope:
- `v1.x` contract stability freeze across `001`–`003` database migrations (SQLite, PostgreSQL, and MariaDB parity), `theme.json` Exclusive Active Theme manifests (`coded` & `visual`), native Hooks & Filters API, `query_entries` + `use cache` invalidation, `grab mcp` CMS tool schemas, and `--read-only` container deployment.
- Full `v1.0.0` end-to-end production hardening & release verification (`tests/release_v100_test.py`): fresh clean SQLite install (`001 -> 002 -> 003` & direct `003`), `seed.grab`, `/setup` lock, full content/decimal/media/taxonomy/301-history/menu/cache/MCP/exclusive-theme-switch lifecycle, repo-wide `grab check` + canonical `grab format`, and zero wrapper-`<div>` validation.
- Hardened `--read-only` Docker Compose / Grisp production deployment template (`deploy/docker-compose.yml` + `deploy/README.md`) with scoped writable `storage/`, `uploads/`, and `/static/grex/` mounts (`--allow-scripts`, `--allow-env`, `--allow-write`, `--workers` scaling docs), zero-secrets Git hygiene, and `docs/releases/pdf/GrabLab-v1.0.0-Guide.pdf`.
- **`v1.0.1` Pre-Step-4 Cross-Layer Audit Patch:** Added `/static/grex/grex.elements.json` parity bundle, `SPEC-100` MCP parameter aliases (`content_type_slug`, `body`, `excerpt`, `grex_layout`, `field_*`, `sort_*`, `page`/`per_page`, `location`) & JSON-RPC `-32602` codes, Grex Builder WCAG AA contrast/outline/CSS/tag parity, `301` redirect loop/reserved guards, and `docs/releases/pdf/GrabLab-v1.0.1-Guide.pdf`.

---

## `v1.1.0` — Zero-Plugin E-Commerce Core

**Status:** Approved & Frozen — Complete (`v1.1.0`, `specifications/GRABLAB-SPEC-110.md`, Revision 2; Stage 4 Pre-Release Cross-Layer Security & Contract Sign-Off `PASS`)

Scope:
- **Native Commerce Content Types & Additive Migration `004`:** `Product`, `Cart`, `Order`, `Coupon`, `Customer` with USD only (`"USD"`) using exact base-10 `ADR-025c` `GrabDecimal` (`"0.00"`) / `GrabInteger` wire types; physical (preserving USPS-only carrier rules for facility book shipments, plus out-of-band `lulu_direct`) and digital-download products; guest checkout enabled by default (with optional account creation).
- **Flat-Rate Shipping & Configurable Tax:** Store-configurable flat-rate shipping and basis-point tax tables (no live carrier/tax APIs; shipping untaxed in `v1.1.0`).
- **Commerce API & Native GRAB `v1.1.0` Security:** `POST /api/commerce/cart`, `/coupon/apply`, `/checkout`, and `/api/commerce/webhooks/payment` with CSRF, cart-scoped idempotency keys, GRAB `v1.1.0`'s native signed webhook verification (`deploy/grab.platform.commerce.json`), and `GRAB-E402` allowlisted HTTPS payment redirects without modifying frozen GRAB `v1.1.0`.
- **Abandoned-Checkout Hook:** `commerce:abandoned_checkout` event emitted only with explicit marketing opt-in (`marketing_opt_in: true` / `marketing_consent = 1`) for `Groxy AI v1.4.0` (`POST /api/groxy/commerce/recovery`) and `Plotific Press`; existing `v1.0.1` SEO/redirect core and product `slug_history` `301` redirects preserved intact.
- **Pure `Grex JS v1.0.0` Commerce Admin Views** (`divCount === 0`, `innerHTMLWriteCount === 0`, Light & Dark WCAG AA).
- *Note:* Stage 3 implementation and Stage 4 Pre-Release Cross-Layer Security & Contract Sign-Off (`PASS`) are complete; `v1.2.0` below extends this core with provider-specific webhook adapters and the email outbox.

### Re-Slotted Prior Scope (Version Slot To Be Decided By Project Owner)
**Status:** Planned (Specification Pending Approval) — formerly labeled `v1.1.0`.

Scope:
- **SEO Redirect Manager (`/admin/redirects`):**
  - Capability-gated admin UI and `/api/admin/redirects` CRUD endpoints (`X-CSRF-Token` + RBAC) to inspect all automatic `301 Moved Permanently` redirects generated from `slug_history` on slug renames.
  - Create, edit, toggle, and delete custom manual `301` / `302` redirects with strict cycle/loop prevention, reserved path protection (`/admin`, `/api`, `/static`, `/_health`, `/_ready`), and instant `use cache` invalidation.
- **Built-In Per-Entry & Per-Image Groxy AI SEO Assist Toggle (`groxy_assist_enabled`):**
  - Native toggle baked into every content type editor (Posts, Products, Pages, Custom Types) and every Media Library image item.
  - When toggled ON, clicking **Publish** opens a **Pre-Publish SEO & Performance Grade Review Screen** before making the entry live, displaying `A+`–`F` / `0–100` scores across **On-Page SEO**, **Content & WCAG Accessibility**, **Performance & Clean DOM**, and **Off-Page / Internal Linking Readiness**, with two explicit actions:
    - **"Make This Live"**: Publishes the entry immediately as-is.
    - **🚀 "Let Groxy Boost This"** *(rocket icon button)*: Calls **Groxy AI** via `grab mcp` to automatically resolve flagged SEO, copy, internal-linking, `schema.org`, and missing `alt`-text issues, then shows a side-by-side diff + refreshed grades so the author always reviews and clicks **"Approve & Make This Live"** before anything goes public.
  - Authors can also trigger **Audit with Groxy** (or post-publish non-blocking `content:after_publish` checks) to receive safe, reviewable suggestions/draft diffs without silently overwriting live human copy.

---

## `v1.2.0` — Universal Commerce Webhooks (Stripe, PayPal, LemonSqueezy, Paddle) & Event-Triggered Email Queue

**Status:** Planned — Backwards-Compatible Minor Feature

Scope:
- **Universal Commerce Webhooks:** Signed ingestion endpoints for **Stripe**, **PayPal**, **LemonSqueezy**, and **Paddle** using constant-time HMAC-SHA256 verification (`use crypto`) and strict `event_id` idempotency against replay or duplicate processing.
- **Exact Money & Order Ledger (`ADR-025c`):** Records purchases, subscriptions, and refunds in a SQLite/PostgreSQL/MariaDB-compatible order/refund ledger using exact base-10 `GrabDecimal` amounts (zero floating-point drift).
- **Consent & Compliance Guardrails:** Enforces CAN-SPAM / GDPR unsubscribe tokens, explicit marketing consent flags, and suppression checks before queuing non-transactional messages.
- **Event-Triggered Transactional `email_outbox`:** Persistent outbox worker and lifecycle triggers for `commerce:purchase_completed`, `commerce:abandoned_checkout`, `commerce:subscription_renewed`, and `commerce:refund_issued`, pairing cleanly with Grex Theme Builder (`mode: "email"`) and Groxy AI (`v1.3.0`).

---

## `v1.3.0` — Opt-In "Talk to Groxy" Database & Store Consultant Tab (`groxy_db_consultant_enabled`)

**Status:** Planned — Backwards-Compatible Minor Feature

Scope:
- **Opt-In Consultant Tab (`groxy_db_consultant_enabled`):** Disabled by default; when enabled by a site administrator, exposes read-only live schema & dependency inspection (`SCHEMA-CONTEXT.md`, table/column metadata, row counts, active `ForEach` Query Loops, `slug_history` redirects, and order ledger references) to **Groxy AI** (`v1.5.0`).
- **Human-in-the-Loop Impact & Snapshot Gate:** Any schema migration or data adjustment proposed by the consultant requires an explicit plain-English **Impact & Risk Assessment** preview, single-use `approval_token` + `X-CSRF-Token` confirmation, and an automatic pre-migration snapshot before execution.

---

## `v1.4.0` — Author Mode Book & Series Publishing Module + Embedded Bestseller Radar

**Status:** Approved & Frozen — Complete (`v1.4.0`, [`specifications/GRABLAB-SPEC-140.md`](../specifications/GRABLAB-SPEC-140.md); Owner approved 2026-11-17; Stage 2 & Stage 4 Cross-Layer Security & Contract Sign-Off `PASS`) — *Backwards-Compatible Minor Feature*

Scope:
- **Additive Migration `005` & Native Author Content Types:** First-class `Author`, `Series`, `Book`, and `Chapter` schemas (`SQLite`, `PostgreSQL`, `MariaDB` parity) with exact `ADR-025c` `GrabDecimal` (`"0.00"`) / `GrabInteger` wire types, validated `ISBN-13` / `ASIN` identifiers, series reading-order indexing, sample chapter previews, and direct linkage to `v1.1.0` `products` + `product_digital_files` (DRM-free EPUB/PDF hashed `download_grants`) and `product_fulfillment` (`LULU-USPS-001` matte paperback + USPS-only carrier rules).
- **XSS-Safe `schema.org/Book` & `BookSeries` JSON-LD + `slug_history` 301 Redirects:** Automatic `</script>`-escaped `schema.org/Book` and `BookSeries` JSON-LD rendering on public `/books/:slug` and `/series/:slug` pages, preserving `slug_history` `301` redirects and `use cache` invalidation on title/slug edits.
- **Embedded Bestseller Radar & Genre Profit Panel (`Groxy AI v1.7.0` + `v1.8.0` Bridge):** Native `/admin/author/radar` view embedding `Groxy AI v1.8.0`'s Bestseller Radar (`POST /api/groxy/research/bestseller-radar`) and `Groxy AI v1.7.0`'s Multi-Genre Storytelling Brain + Hemingway Readability Auditor (`POST /api/groxy/author/generate` & `/readability-audit`) over `GRAB-E402` allowlisted origins so browser CMS authors can research high-margin genres, evaluate unit economics, and import draft `Series`/`Book`/`Chapter` outlines (`status: "draft"`) in one click.
- **Pure `Grex JS v1.0.0` Author & Reader Views:** Zero wrapper-`<div>` (`divCount === 0`, `innerHTMLWriteCount === 0`), Light & Dark WCAG AA (`>= 4.5:1`) admin dashboard + distraction-free Web Reader.
