# GrabLab CMS `v1.4.0` — Author Mode Book & Series Publishing Module + Embedded Bestseller Radar

### Release Type & Affected Layers
- **Release Version & SemVer Tier:** `v1.4.0` (`MINOR 1.x.0 — Backwards-Compatible Feature Release`)
- **Affected Layer(s):** `Flagship Zero-Plugin CMS` (`urbanspress/grablab-cms`)
- **Neighboring Layer Upgrade Required?** `No — 100% drop-in compatible` with frozen GRAB `v1.1.0` and Grex JS `v1.0.0` (additively integrates with `Groxy AI v1.7.0` + `v1.8.0` over `GRAB-E402` allowlisted origins when Author Mode and a Groxy AI origin are configured; disabled by default returning `404`)

| Ecosystem Layer | Repository | Required Version Range | Touched in This Release? | Neighbor Upgrade Required? |
|---|---|---|---|---|
| **Core Language, Bytecode VM & Grisp Server** | `urbanspress/grab` | `>= v1.1.0 (< v2.0.0)` | `No` | `No` |
| **Reactive Frontend Runtime & 20-Element Library** | `urbanspress/grex-js` | `>= v1.0.0 (< v2.0.0)` | `No` | `No` |
| **Flagship Zero-Plugin CMS** | `urbanspress/grablab-cms` | `>= v1.4.0 (< v2.0.0)` | `Yes` | `No` |
| **Exclusive `mode: "visual"` Theme & Studio** | `urbanspress/grex-builder` | `>= v1.0.0 (< v2.0.0)` | `No` | `No` |
| **Autonomous Design, Content & SEO Agent** | `urbanspress/groxy-ai` | `>= v0.1.0` (Optional Embedded Radar & Co-Writer: `>= v1.8.0`) | `No` | `No` |

---

## Summary of Changes

- **Additive Migration `005` & Native Author Content Types (`migrations/005_author_schema*.grab`, `migrations/seed_author.grab`):** Adds `authors`, `series`, `books`, `chapters`, and `author_radar_imports` across SQLite, PostgreSQL, and MariaDB parity while keeping `001`–`004` schemas, existing entries, and `slug_history` `301` redirects intact. Author Mode is disabled by default (`author_mode_enabled = "0"` returning `404`).
- **`ADR-025c` Exact Money/Royalty & Identifier Validation (`src/app.grab`):** Stores prices in integer cents and royalties in basis points (`0..10000`), enforces exact base-10 `GrabDecimal` (`"0.00"`) and `GrabInteger` wire values (rejecting raw floats and scientific notation with `422`), validates GS1 `ISBN-13` check digits and `^[A-Z0-9]{10}$` `ASIN` identifiers (`422`), and blocks reserved system prefixes (`409`).
- **Direct `v1.1.0` Commerce & Fulfillment Linkage (`POST /api/admin/author/books/:id/sync-product`):** Links digital books (`ebook`) to `products` + `product_digital_files` (DRM-free EPUB/PDF via hashed `download_grants` with `Cache-Control: no-store`) and physical books (`paperback` / `hardcover`) to `product_fulfillment` enforcing `LULU-USPS-001` matte paperback or USPS-only carrier rules (`ground_advantage`, `priority`, `media_mail`, weight `<= 31751 g`), preserving `products` as the checkout source of truth and `409 price_changed` open-cart safety.
- **XSS-Safe `schema.org/Book` & `BookSeries` JSON-LD + `slug_history` `301`s:** Escapes `</script>`, `<`, `>`, `&`, `U+2028`, and `U+2029` inside `<script type="application/ld+json">` on public `/books/:slug` and `/series/:slug` pages, records slug renames in `slug_history` for `301` redirects, and deterministically invalidates `use cache` keys.
- **Embedded Bestseller Radar & Readability Bridges + Additive MCP Tools:** Connects `/api/admin/author/radar/query`, `/radar/import`, and `/readability-audit` to `Groxy AI v1.7.0` + `v1.8.0` over `GRAB-E402` allowlisted origins (`admin`-only `author:settings`, CSRF `403`, MCP Bearer `401` on `/api/admin/author/*`), guarantees single-winner `201`/`409` claiming on `author_radar_imports.radar_plan_id` (`status_enforced: "draft"`), and adds `list_author_catalog` + `create_book_draft` (`status_enforced: "draft"`) to `grab mcp`.
- **Pure `Grex JS v1.0.0` Author Admin & Sample Web Reader Views (`public/admin/author.js`, `public/author/reader.js`, `public/author/reader.css`, `src/views/author/reader.grab.html`, `themes/default-starter/templates/{books,book,series}.grab.html`):** Zero `<div>` elements, zero `innerHTML` writes, zero `eval()`/`new Function()`, keyboard `Escape`/focus restoration, and Light + Dark WCAG AA contrast (`>= 4.5:1`).

## Verification & Bundle Checksums

- **Stage 4 Pre-Release Cross-Layer Sign-Off (`PASS`):** `grab check` (default + commerce profiles), canonical byte-for-byte `grab format` across all 20 `.grab` files, `grab connect lock`/`inspect`, `node tests/author_dom_audit.mjs`, `node tests/commerce_dom_audit.mjs`, `python tests/author_test.py` (`10/10`), `python tests/release_v140_test.py` (`5/5`), `python tests/commerce_test.py` (`9/9`), `python tests/release_v110_test.py` (`5/5`), `python tests/integration_test.py` (`13/13`), and `python tests/release_v100_test.py` (`5/5`).
- **Walkthrough PDF:** `docs/releases/pdf/GrabLab-CMS-v1.4.0-Guide.pdf`
- **Release Bundle:** `dist/grablab-cms-v1.4.0-bundle.zip` (SHA-256 recorded in `dist/SHA256SUMS.txt`)
