# GRABLAB-SPEC-110: `v1.1.0` — Zero-Plugin E-Commerce Core

**Status:** Approved target; specification in review (no implementation code until the project owner approves this document)
**Baseline:** GrabLab CMS `v1.0.1` (frozen `GRABLAB-SPEC-100`), GRAB `v1.1.0`, Grex JS `v1.0.0`, Grex Theme Builder `v1.0.0`
**SemVer Tier:** `MINOR 1.x.0 — Backwards-Compatible Feature Release` (additive migration + new endpoints only)
**Interoperates With:** `Groxy AI v1.4.0` (cart-recovery), `Plotific Press` (book storefront)

---

## 1. Purpose, Scope & Non-Goals

Adds native store capability to GrabLab with **no plugin loader** (`GRABLAB-EXPERT.md` §1): products, carts, coupons, checkout, orders, customers, and a signed payment webhook, all in `.grab`, `.grab.html`, SQL migrations and static assets.

**In scope:** content types, migration `004`, four commerce endpoints, abandoned-checkout event, admin views, tests.
**Non-goals (deferred to `v1.2.0`):** multi-provider webhook adapters (Stripe/PayPal/LemonSqueezy/Paddle), subscriptions, refunds ledger, `email_outbox`. `v1.1.0` ships one generic, provider-agnostic signed webhook that `v1.2.0` extends.
**Never in scope:** storing card numbers (PAN/CVV). Payment happens on the external provider's HTTPS page; GrabLab only holds the provider reference.

### 1.1 Compatibility Guarantees
- Migrations `001`–`003` and all `SPEC-100` routes, MCP tools, and schemas are **unchanged**. A `v1.0.1` site upgrades by running migration `004` only.
- Commerce is **off by default** (`commerce_enabled = 0` in `site_settings`); until enabled, all `/api/commerce/*` routes return `404` and the admin menu shows no store items.

---

## 2. Exact-Number Wire Rules (`ADR-025c`)

| Concept | Wire type | Example | Rule |
|---|---|---|---|
| Money amounts (`price`, `subtotal`, `discount_total`, `tax_total`, `shipping_total`, `total`) | `GrabDecimal` string, exactly 2 fraction digits | `"19.99"` | Regex `^(0|[1-9][0-9]{0,9})\.[0-9]{2}$`. |
| Quantities, stock, weights (grams), percentages in basis points | `GrabInteger` | `3`, `450`, `1500` (= 15.00%) | Whole JSON integer or base-10 string; no fraction/exponent. |
| Currency | ISO-4217 string | `"USD"` | Single store currency in `v1.1.0` (`site_settings.currency`). |

1. **JS floats are rejected.** Any JSON number with a fraction or exponent in a money/quantity field (e.g. `19.99`, `1e2`) → HTTP `422` `{error: "commerce_validation_failed", field, reason: "float_not_allowed"}`. Money must be sent as a string.
2. All arithmetic uses **integer cents** internally (`GrabInteger`), converted to `GrabDecimal` only at the wire. No IEEE‑754 value is ever computed or stored.
3. **Rounding:** tax and percentage discounts use round-half-up to the cent, applied once to each computed amount (discount, tax) on the whole cart (documented so tests are deterministic).
4. Responses echo money as strings. Negative totals are impossible: discounts are capped at the subtotal.

---

## 3. Native Commerce Content Types & Migration `004` (`ADR-024f`)

### 3.1 Migration Files (additive, idempotent)
| File | Schema Versions | Target |
|---|---|---|
| `migrations/004_commerce_schema.grab` | `[1, 2, 3, 4]` | SQLite (primary) |
| `migrations/004_commerce_schema_postgres.grab` | `[1, 2, 3, 4]` | PostgreSQL |
| `migrations/004_commerce_schema_mariadb.grab` | `[1, 2, 3, 4]` | MariaDB |

Each uses `data.migrate`, creates only new tables (`IF NOT EXISTS`), never alters or drops tables from `001`–`003`, and records the version bump. Money columns are stored as integer cents (`*_cents` `INTEGER`/`BIGINT`) with a `currency` text column; the engine-neutral `GrabDecimal` string is produced at the API boundary. `seed.grab` is **not** modified; commerce seeds live in `seed_commerce.grab` (opt-in).

### 3.2 Tables
| Table | Key columns | Notes |
|---|---|---|
| `products` | `id`, `entry_id` (FK → `entries`, `content_type = product`), `sku` (unique), `kind` (`physical` \| `digital`), `price_cents`, `compare_at_cents`, `currency`, `stock_qty` (nullable = unlimited), `weight_g`, `tax_class`, `active` | A product **is** an entry of the built-in `product` content type, so it inherits slugs, `slug_history`, drafts, RBAC, themes and caching. |
| `product_digital_files` | `id`, `product_id`, `media_id` (FK → `media`), `download_limit`, `expiry_hours` | Digital delivery via signed, expiring, single-order download links. |
| `product_fulfillment` | `product_id`, `carrier` (`usps` \| `lulu_direct`), `lulu_sku`, `usps_service`, `max_weight_g`, `ships_from_country` | Physical-goods constraints (§3.4). |
| `customers` | `id`, `user_id` (nullable FK → `users`), `email` (unique, lower-cased), `display_name`, `marketing_consent` (0/1), `created_at` | Guest checkout allowed; linked to a `users` row when logged in. |
| `carts` | `id` (opaque random), `customer_id` nullable, `status` (`open` \| `checked_out` \| `abandoned`), `currency`, `coupon_code`, `last_activity_at`, `created_at` | |
| `cart_items` | `id`, `cart_id`, `product_id`, `qty`, `unit_price_cents` (snapshot) | One row per product per cart. |
| `coupons` | `id`, `code` (unique, upper-cased), `type` (`percent_bp` \| `fixed_cents`), `value`, `min_subtotal_cents`, `max_redemptions`, `redeemed_count`, `starts_at`, `ends_at`, `active` | |
| `coupon_redemptions` | `id`, `coupon_id`, `order_id`, `created_at` | Unique per `(coupon_id, order_id)`. |
| `orders` | `id`, `number` (unique, e.g. `GL-000123`), `cart_id`, `customer_id`, `status` (`pending_payment` \| `paid` \| `fulfilling` \| `shipped` \| `delivered` \| `cancelled`), `subtotal_cents`, `discount_cents`, `tax_cents`, `shipping_cents`, `total_cents`, `currency`, `payment_ref`, `shipping_address_json`, `created_at`, `paid_at` | Totals are frozen at checkout. |
| `order_items` | `id`, `order_id`, `product_id`, `sku`, `title`, `qty`, `unit_price_cents` | Immutable snapshot. |
| `idempotency_keys` | `key`, `scope`, `request_hash`, `response_json`, `status_code`, `created_at` | Unique on `(scope, key)`. |
| `payment_events` | `event_id` (unique), `order_id`, `payload_hash`, `received_at` | Webhook replay protection. |
| `commerce_events` | `id`, `name`, `payload_json`, `created_at`, `delivered_at` | Outbox for §6 events. |

Indexes: `idx_products_sku`, `idx_cart_items_cart`, `idx_orders_customer`, `idx_orders_status`, `idx_carts_activity`, `idx_coupons_code`.

### 3.3 Content Types & Custom Fields
`product` is registered as a built-in content type (`/shop/:slug` permalink pattern) via the existing `content_types` / `field_definitions` registry with typed fields: `price` (`decimal`), `sku` (`string`), `kind` (`string`), `stock_qty` (`integer`), `weight_g` (`integer`). The `decimal` field type already exists in `SPEC-100`; its validation is tightened for this type to the §2 regex. The other four (`Cart`, `Order`, `Coupon`, `Customer`) are **table-backed system types**, managed only through commerce routes and admin views, never published as public entries.
`create_entry_draft` for `product` keeps `status_enforced: "draft"` (unchanged AI safety rule).

### 3.4 Physical vs. Digital Constraints
- **Digital:** no shipping line; `weight_g` ignored; checkout skips address collection; fulfilment = download link emailed/shown after `paid`.
- **Physical:** requires a `product_fulfillment` row; checkout requires a valid address.
  - `carrier = usps`: `usps_service` ∈ allowlist (`ground_advantage`, `priority`, `media_mail`); parcel weight ≤ `max_weight_g` (default 31 751 g / 70 lb) else `422 weight_exceeds_carrier_limit`. `media_mail` only permitted if **every** physical item is flagged `media_mail_eligible` (books).
  - `carrier = lulu_direct`: requires non-empty `lulu_sku`; printing/shipping is handled by Lulu out of band. GrabLab only records the order and exposes it for fulfilment; **no outbound call to Lulu is made in `v1.1.0`** (preserves zero-network default). Mixed carts of `usps` + `lulu_direct` items produce one order with per-item carrier tags.
- Shipping cost = flat-rate table in `site_settings` (`shipping_rates_json`, `GrabDecimal` strings per carrier/service); no live carrier-rate API in `v1.1.0`.
- Oversell guard: stock decrement happens inside the checkout transaction; shortfall → `409 out_of_stock`.

---

## 4. Commerce Endpoints

All routes live under `/api/commerce/`, speak JSON, and return the error envelope `{error, message, field?}`.

### 4.1 Common Security Rules
1. **CSRF:** every `POST` from a browser session requires a matching `X-CSRF-Token` (missing/invalid → `403 commerce_csrf_invalid`). Anonymous shoppers receive a signed, `HttpOnly; SameSite=Lax; Secure` `gl_cart` cookie and a paired CSRF secret from `GET /api/commerce/session`, so guest checkout is still protected. `/webhooks/payment` is exempt from CSRF (machine caller) but has stronger authentication (§4.5).
2. **RBAC:** shoppers need no role. Admin endpoints (`/api/admin/commerce/*`) require `commerce:manage` (new capability, `admin` and `editor` only) + CSRF.
3. **Rate limit:** cart/coupon endpoints use `use cache` counters (default 60 req/min/IP; `429`). Coupon attempts: 10/min/cart.
4. Server recomputes **all** prices from the database; client-sent prices are ignored (a client-sent `unit_price` field → `422 client_price_not_allowed`).
5. Bodies > 64 KiB → `413`.

### 4.2 `POST /api/commerce/cart`
Actions in body `{action: "add" | "set_qty" | "remove" | "get", product_id, qty}`.
- `qty` is a `GrabInteger` 0–999 (float → `422`).
- Product must be `published` and `active`; unknown → `404`; draft → `404` (no existence leak).
- Returns `200` with `{cart_id, items[], subtotal, discount_total, tax_total, shipping_total, total, currency}` (all money strings).
- Updates `last_activity_at` (feeds §6).

### 4.3 `POST /api/commerce/coupon/apply`
Body `{code}` (or `{code: ""}` to remove).
- Validations: exists, `active`, within `starts_at`/`ends_at`, under `max_redemptions`, subtotal ≥ `min_subtotal_cents`. Failure → `422 coupon_invalid` with machine `reason` (`expired`, `exhausted`, `min_subtotal`, `unknown`). Unknown vs. expired return the same HTTP status to limit enumeration.
- `percent_bp` coupons: `discount = round_half_up(subtotal * bp / 10000)`; `fixed_cents`: `min(value, subtotal)`.
- One coupon per cart in `v1.1.0` (stacking is out of scope).
- Redemption is **counted at order creation**, not at apply, inside the same transaction as stock decrement.

### 4.4 `POST /api/commerce/checkout`
Requires header `Idempotency-Key` (16–64 chars `[A-Za-z0-9_-]`; missing → `400`).
1. Validate cart non-empty, stock, carrier constraints, address (physical), customer email.
2. Compute totals (§5); create `orders` (`pending_payment`) + `order_items`; mark cart `checked_out`; redeem coupon; decrement stock — **one transaction**.
3. Build the external payment URL from `site_settings.payment_redirect_base` + order reference.
4. Response `201 Created` `{order_number, total, currency, redirect_url}` for the **first** request with a key.
5. **Idempotency:** a sequential retry after completion is handled by the replay rule below. Same key + different body → `422 idempotency_key_reuse`. A **concurrent duplicate** (same key while the first is still in flight) → `409 idempotency_conflict`. Exactly one concurrent request wins `201`; all others get `409` (verified by test, §9). No second order is ever created.
6. **Redirect allowlist (`GRAB-E402`):** `redirect_url` must be `https://`, host in `site_settings.payment_redirect_allowlist` (exact host match, no wildcards in `v1.1.0`), no userinfo, no non-443 port, no fragments carrying credentials. Anything else — including `http:`, `javascript:`, `data:`, redirect-chain hosts — raises `GRAB-E402` and returns `502 payment_redirect_blocked`; the order is rolled back. Allowlist empty (default) → checkout disabled with `503 payment_not_configured`.
7. Grisp `--allow-net` is **not** needed: GrabLab only emits a redirect URL; the browser navigates.

*Idempotency replay rule:* to keep the "`201` winner / `409` duplicate" contract simple and testable, a sequential retry after completion also returns **`409 idempotency_conflict`** with `{order_number, redirect_url}` of the original order in the body so clients can recover without creating a duplicate.

### 4.5 `POST /api/commerce/webhooks/payment`
Generic provider-agnostic webhook (provider adapters arrive in `v1.2.0`).
- Headers: `X-GrabLab-Signature: t=<unix_seconds>,v1=<hex>`; signature = `HMAC-SHA256(secret, t + "." + raw_body)` computed with `use crypto`, compared in **constant time**. Secret from env `GRABLAB_PAYMENT_WEBHOOK_SECRET` (never in DB or Git; added to `--allow-env`).
- Reject: missing/malformed header or bad signature → `401 webhook_signature_invalid`; timestamp older/newer than 300 s → `401 webhook_timestamp_out_of_window`; raw body used exactly as received (no re-serialization).
- Body `{event_id, type: "payment.succeeded" | "payment.failed", order_number, amount: "<GrabDecimal>", currency}`.
- `amount`/`currency` must equal the stored order total, else `422 amount_mismatch` and order stays `pending_payment`.
- Replay: `event_id` already in `payment_events` → `200 {status:"duplicate_ignored"}` (provider retries are safe, no double processing).
- `payment.succeeded` → order `paid`, `paid_at` set, digital links issued, `commerce:purchase_completed` queued in `commerce_events` for `v1.2.0` consumers. Unknown order → `404`.
- Unconfigured secret → `503`; never accepts unsigned events.

---

## 5. Totals Algorithm (deterministic)

```
lines     = sum(qty * unit_price_cents)                              -> subtotal_cents
discount  = coupon rule, capped at subtotal_cents                    -> discount_cents
taxable   = subtotal_cents - discount_cents
tax       = round_half_up(taxable * tax_rate_bp / 10000)             -> tax_cents  (store-wide rate, digital+physical per tax_class table)
shipping  = 0 if no physical items else flat rate for carrier/service -> shipping_cents
total     = taxable + tax + shipping                                 -> total_cents
```
- `tax_rate_bp` is a `GrabInteger` basis-point setting per `tax_class` (`standard`, `digital`, `exempt`); no external tax API in `v1.1.0`.
- Test vectors (must pass exactly): `[$19.99 × 3, coupon 15%] → subtotal 59.97, discount 9.00 (8.9955→9.00), tax@8.25% on 50.97 = 4.21, total 55.18` plus ten more vectors in `tests/commerce_vectors.json` including `0.01`, `999999.99`, and half-cent boundaries.

---

## 6. Abandoned-Checkout Hook & Ecosystem Interoperability

### 6.1 Event
A scheduled sweep (Grisp worker tick, default every 5 min; configurable `abandoned_after_minutes`, default 60) marks `open` carts with items, a known customer email, and `last_activity_at` older than the threshold as `abandoned` and writes **one** event per cart (unique on `cart_id`) to `commerce_events`:

```json
{
  "name": "commerce:abandoned_checkout",
  "version": 1,
  "cart_id": "…",
  "email_hash": "sha256:…",
  "marketing_consent": 1,
  "currency": "USD",
  "subtotal": "59.97",
  "items": [{"sku": "BOOK-001", "title": "…", "qty": 3, "unit_price": "19.99", "url": "/shop/book-001"}],
  "last_activity_at": "2026-11-17T18:00:00Z"
}
```
- Raw email is **not** in the event (hash only); the recovery email itself is a `v1.2.0` outbox concern and requires `marketing_consent = 1`.
- The hook is also emitted through the native hook registry (`source: "core"`), so themes cannot spoof it (`GRAB-E401` rule from `SPEC-100` §4).

### 6.2 `Groxy AI v1.4.0` Consumption
- Groxy reads events through a new read-only MCP tool `list_commerce_events` (`commerce:manage`, Bearer MCP token) — additive to the `SPEC-100` registry.
- Groxy responds at its own endpoint `POST /api/groxy/commerce/recovery` (defined in Groxy's spec, not here). Any resulting copy/offer returns **only** through `create_entry_draft` (`status_enforced: "draft"`) or a coupon **draft** (`active = 0`) requiring human activation. Groxy can never activate a coupon, change a price, or refund.

### 6.3 `Plotific Press` Interop
- Book products use `kind=physical` + `carrier=lulu_direct` or `kind=digital` and carry `isbn_13` as a `string` field; price remains `GrabDecimal` (no float drift into `schema.org/Offer` `price`).
- Product pages emit `schema.org/Product`/`Offer` JSON-LD with `price` as the exact string; escaped via existing XSS-safe serializers.
- **`slug_history` 301s are preserved:** renaming a product slug writes `slug_history` exactly as for other entries; `/shop/<old>` → `301 /shop/<new>`; carts and order items reference `product_id`, never the URL, so redirects cannot break open carts.

---

## 7. Commerce Admin Views (pure `Grex JS v1.0.0`)

New `.grab.html` views, using only the 20 Grex elements and semantic HTML5:
`/admin/store` (dashboard), `/admin/store/products`, `/admin/store/orders` (+ detail), `/admin/store/coupons`, `/admin/store/customers`, `/admin/store/settings` (currency, tax rates, shipping rates, payment redirect allowlist, abandoned threshold — webhook secret is **shown as set/unset only**, never displayed).
- Tables built with `Grid`/`ForEach`; forms with `Form`/`Input`/`Select`; destructive actions in `Modal` confirmation.
- Orders are **never silently edited**: status changes require a CSRF-protected action with an audit row; totals are read-only.
- Order/customer pages show email partially masked unless the role has `commerce:manage`.
- Money inputs are text inputs (`inputmode="decimal"`) submitted as strings, never `type="number"` coerced via JS floats.
- No `innerHTML` writes; all text via `textContent`/Grex bindings; unsafe URL schemes rejected.
- Light and Dark themes via `data-grex-theme`, tokens meet WCAG AA.

---

## 8. Security, Privacy & Deployment Notes
- **PII:** customer email/address stored only for orders; `GET /api/admin/commerce/customers/:id/export` and `DELETE …` (anonymize) support GDPR requests; deletion keeps order totals but nulls identifying columns.
- **Logging:** never log full webhook bodies, secrets, tokens or addresses.
- **Container:** unchanged `--read-only` profile; digital files live in the existing writable `uploads/` mount, served by signed time-limited links (HMAC with `GRABLAB_MASTER_KEY`-derived key, order-bound, `download_limit` enforced).
- **New env var:** `GRABLAB_PAYMENT_WEBHOOK_SECRET` (added to documented `--allow-env`).
- **Cache:** product, price and settings changes invalidate existing `use cache` entry/route keys plus new `commerce:product:<id>` keys; carts/orders are never cached.
- **Stable branch:** this milestone ships to `origin` only until fully verified; `stable` stays at `v1.0.1`.

---

## 9. Section 9 Acceptance Gates (all must pass 100%)

1. **`grab check`** zero errors on every `.grab` and `.grab.html` file (including new migrations and views).
2. **Canonical format:** `grab format <file>` stdout byte-identical to on-disk bytes for every `.grab` file.
3. **Zero-DOM-debt:** `divCount === 0` and `innerHTMLWriteCount === 0` across all commerce views and starter-theme product/cart templates; zero `eval`/`new Function`; zero unsafe URL schemes.
4. **Accessibility:** `auditAccessibility()` passes 100%; Light **and** Dark contrast `>= 4.5:1` (normal text), `>= 3.0:1` (large text).
5. **Numeric fidelity (`422`):** floats/exponents in any money or quantity field rejected with `422`; `"19.99"` strings round-trip byte-exact through API → DB → API on SQLite, PostgreSQL and MariaDB; all §5 vectors exact.
6. **Authorization (`403`):** missing/invalid `X-CSRF-Token` → `403` on cart, coupon, checkout and admin routes; shopper hitting `/api/admin/commerce/*` → `403`; `author`/`viewer` without `commerce:manage` → `403`.
7. **Concurrency (`409`):** 20 parallel checkouts with one `Idempotency-Key` → exactly one `201`, nineteen `409`, exactly one order row; two parallel checkouts for the last unit of stock → one success, one `409 out_of_stock`; duplicate webhook `event_id` → single state transition.
8. **Webhook security:** bad signature, stale timestamp, tampered body, amount mismatch, and missing secret each rejected with the specified codes; constant-time comparison confirmed by code review/test double.
9. **Redirect safety (`GRAB-E402`):** `http:`, `javascript:`, `data:`, userinfo, non-allowlisted host, and non-443 port all blocked, order rolled back.
10. **Carrier rules:** USPS weight/service limits and `lulu_direct` SKU requirement enforced; digital items skip shipping.
11. **Abandoned-checkout event:** exactly one `commerce:abandoned_checkout` per qualifying cart, no raw email, consumable by a Groxy-style MCP client; Groxy can only create **draft** output.
12. **`slug_history`:** renamed product slug returns `301` to the new URL and open carts remain valid.
13. **Regression:** existing `tests/integration_test.py` (13/13) and `tests/release_v100_test.py` (5/5) still pass unchanged; a `v1.0.1` database upgrades via migration `004` with zero data loss; commerce disabled by default returns `404`.
14. **New suites:** `tests/commerce_test.py` (API, security, concurrency, vectors) and `tests/release_v110_test.py` (fresh install → store setup → checkout → webhook → paid order E2E, Light/Dark audit) pass **100%**.

---

## 10. Implementation Order (after approval)
1. Migration `004` ×3 engines + `seed_commerce.grab`.
2. Totals engine + numeric validators + vectors.
3. Cart / coupon endpoints.
4. Checkout + idempotency + redirect allowlist.
5. Payment webhook.
6. Abandoned sweep + `commerce_events` + MCP `list_commerce_events`.
7. Admin views + starter-theme product/cart templates.
8. Tests, gates, walkthrough PDF, release notes with compatibility matrix.

## 11. Open Questions For The Project Owner
1. **Roadmap slot:** the old `v1.1.0` (SEO Redirect Manager + Groxy SEO Assist) was re-slotted with its version number left open — confirm where it should go.
2. **Single currency** (USD) in `v1.1.0` — acceptable?
3. **Flat-rate shipping and store-wide tax tables** (no live USPS/Lulu/tax APIs) — acceptable for the first release?
4. **Guest checkout** enabled by default — confirm.
