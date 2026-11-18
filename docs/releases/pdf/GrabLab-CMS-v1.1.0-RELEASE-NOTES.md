# GrabLab CMS `v1.1.0` — Zero-Plugin E-Commerce Core

### Release Type & Affected Layers
- **Release Version & SemVer Tier:** `v1.1.0` (`MINOR 1.x.0 — Backwards-Compatible Feature Release`)
- **Affected Layer(s):** `Flagship Zero-Plugin CMS` (`urbanspress/grablab-cms`)
- **Neighboring Layer Upgrade Required?** `No — 100% drop-in compatible` with frozen GRAB `v1.1.0` and Grex JS `v1.0.0` (additively consumes GRAB `v1.1.0` native signed webhooks and prepares hooks for `Groxy AI v1.4.0` recovery campaigns)

| Ecosystem Layer | Repository | Required Version Range | Touched in This Release? | Neighbor Upgrade Required? |
|---|---|---|---|---|
| **Core Language, Bytecode VM & Grisp Server** | `urbanspress/grab` | `>= v1.1.0 (< v2.0.0)` | `No` | `No` |
| **Reactive Frontend Runtime & 20-Element Library** | `urbanspress/grex-js` | `>= v1.0.0 (< v2.0.0)` | `No` | `No` |
| **Flagship Zero-Plugin CMS** | `urbanspress/grablab-cms` | `>= v1.1.0 (< v2.0.0)` | `Yes` | `No` |
| **Exclusive `mode: "visual"` Theme & Studio** | `urbanspress/grex-builder` | `>= v1.0.0 (< v2.0.0)` | `No` | `No` |
| **Autonomous Design, Content & SEO Agent** | `urbanspress/groxy-ai` | `>= v0.1.0` | `No` | `No` |

---

## Summary of Changes

- **Additive Migration `004` (`migrations/004_commerce_schema*.grab`, `migrations/seed_commerce.grab`):** Adds `products`, `product_digital_files`, `product_fulfillment`, `customers`, `carts`, `cart_items`, `coupons`, `coupon_redemptions`, `orders`, `order_items`, `order_audit`, `download_grants`, `idempotency_keys`, `payment_events`, and `commerce_events` with SQLite, PostgreSQL, and MariaDB parity while keeping `001`–`003` schemas, content entries, and `slug_history` `301` redirects intact. Commerce is disabled by default (`404`) after upgrade.
- **`ADR-025c` Exact USD Money & Totals (`src/app.grab`, `tests/commerce_vectors.json`):** Stores money in integer cents, requires exact `"0.00"` `GrabDecimal` / `GrabInteger` wire values (rejecting floats and scientific notation with `422`), enforces a `$99,999,999.99` cap, and matches all 13 deterministic Section 5 rounding and tax/shipping vectors.
- **Storefront, Cart, Guest-First Checkout & Fulfillment:** Supports opaque hashed cart tokens (`gl_cart`) with login rotation, cart-scoped `Idempotency-Key` concurrency guards (`201` / `409` / `403` / `422`), conditional stock/coupon decrements, price-change detection (`409 price_changed`), USPS-only physical mail rules (`ground_advantage`, `priority`, `media_mail`, weight `<= 31751 g`) plus `lulu_direct` fulfillment (`LULU-USPS-001`), validated ISBN-13 metadata + `schema.org/Product` JSON-LD, `GRAB-E402` allowlisted HTTPS payment redirects, and hashed digital download tokens.
- **Opt-In Signed Payment Webhooks (`deploy/grab.platform.commerce.json`, `deploy/connectors/grablab-payment/`):** Leverages GRAB `v1.1.0`'s native HMAC-SHA256 webhook verification (`POST /api/commerce/webhooks/payment` -> `receive_payment_event`) without breaking zero-secret startup on default `grab.platform.json`.
- **Lazy Commerce Sweep, Opt-In Abandoned Checkout & MCP Tools (`scripts/commerce_sweep.grab`):** Expires overdue `pending_payment` stock/coupon holds, marks stale open carts `abandoned`, emits salted `commerce:abandoned_checkout` events strictly when `marketing_consent = 1`, and exposes `list_commerce_events` + `create_coupon_draft` (`active = 0` forced) to authenticated MCP callers while excluding MCP Bearer tokens from `/api/admin/commerce/*`.
- **Pure `Grex JS v1.0.0` Admin & Storefront Views:** Zero `<div>` elements, zero `innerHTML` writes, zero dynamic eval, exact decimal text inputs, and Light + Dark WCAG AA contrast compliance (`>= 4.5:1`).

## Verification & Bundle Checksums

- **All §9 Acceptance Gates Passed (`100%`):** `grab check` (default + commerce profiles), canonical `grab format`, `grab connect inspect`, `node tests/commerce_dom_audit.mjs`, `python tests/integration_test.py`, `python tests/release_v100_test.py`, `python tests/commerce_test.py`, and `python tests/release_v110_test.py`.
- **Walkthrough PDF:** `docs/releases/pdf/GrabLab-CMS-v1.1.0-Guide.pdf`
- **Release Bundle:** `dist/grablab-cms-v1.1.0-bundle.zip` (SHA-256 recorded in `dist/SHA256SUMS.txt`)
