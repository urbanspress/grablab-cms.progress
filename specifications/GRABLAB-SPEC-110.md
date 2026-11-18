# GRABLAB-SPEC-110: `v1.1.0` — Zero-Plugin E-Commerce Core

**Status:** Approved & Frozen — Complete — **Revision 2 (Owner approved 2026-11-17; Stage 2 security & contract audit + Stage 4 Pre-Release Cross-Layer Security & Contract Sign-Off `PASS`)**.
**Baseline:** GrabLab CMS `v1.0.1` (frozen `GRABLAB-SPEC-100`), GRAB `v1.1.0`, Grex JS `v1.0.0`, Grex Theme Builder `v1.0.0`
**SemVer Tier:** `MINOR 1.x.0 — Backwards-Compatible Feature Release` (additive migration + new endpoints + two additive MCP tools)
**Interoperates With:** `Groxy AI v1.4.0` (cart-recovery), `Plotific Press` (book storefront)
**GRAB core changes required:** **None.** Every capability below uses GRAB `v1.1.0` features verified in `C:\Development\GRAB` (`use data` transactions, `use cache` limits, `use crypto` random/hash, platform `webhooks` + `use events`). See §12 for the runtime facts this revision relies on.

---

## 1. Purpose, Scope & Non-Goals

Adds native store capability to GrabLab with **no plugin loader** (`GRABLAB-EXPERT.md` §1): products, carts, coupons, checkout, orders, customers, and a signed payment webhook, all in `.grab`, `.grab.html`, SQL migrations, static assets and declarative platform configuration.

**In scope:** content types, migration `004`, four commerce endpoints (+ session bootstrap and order-status page), abandoned-checkout event, two MCP tools, admin views, tests.
**Non-goals (deferred to `v1.2.0`):** provider-specific webhook adapters (Stripe/PayPal/LemonSqueezy/Paddle), subscriptions, refunds ledger, `email_outbox`. `v1.1.0` ships one generic signed webhook using GRAB's native reference signature profile, which `v1.2.0` extends.
**Never in scope:** storing card numbers (PAN/CVV). Payment happens on the external provider's HTTPS page; GrabLab only holds the provider reference.

### 1.1 Compatibility Guarantees
- Migrations `001`–`003` and all `SPEC-100` routes, MCP tools, and schemas are **unchanged**. A `v1.0.1` site upgrades by running migration `004` only.
- Commerce is **off by default** (`commerce_enabled = 0` in `site_settings`); until enabled, all `/api/commerce/*` routes and `/shop/*` pages return `404` and the admin menu shows no store items.
- The default `grab.platform.json` is **unchanged**. The payment webhook lives in an opt-in platform profile (§4.5), so a site that never enables payments never needs the webhook secret and cannot fail to start because of it.

---

## 2. Exact-Number Wire Rules (`ADR-025c`)

| Concept | Wire type | Example | Rule |
|---|---|---|---|
| Unit prices & coupon fixed amounts (input) | `GrabDecimal` string, exactly 2 fraction digits | `"19.99"` | Regex `^(0|[1-9][0-9]{0,6})\.[0-9]{2}$` (max `9999999.99`). |
| Computed money (`subtotal`, `discount_total`, `tax_total`, `shipping_total`, `total`) | `GrabDecimal` string, exactly 2 fraction digits | `"55.18"` | Cart total capped at `99999999.99`; above → `422 cart_total_exceeds_limit`. |
| Quantities, stock, weights (grams), percentages in basis points | `GrabInteger` | `3`, `450`, `1500` (= 15.00%) | Whole JSON integer or base-10 string; no fraction/exponent. |
| Currency | ISO-4217 string | `"USD"` | Single store currency in `v1.1.0` (`site_settings.currency`). Currency cannot be changed while any `open` cart or non-terminal order exists. |

1. **JS floats are rejected.** GRAB's lossless `json.parse` decodes `19.99` as `decimal` and `3` as `integer`. Any `decimal`-kind or exponent value in a money/quantity field → HTTP `422` `{error: "commerce_validation_failed", field, reason: "float_not_allowed"}`. Money must be sent as a string.
2. All arithmetic uses **integer cents** internally (`GrabInteger`), converted to `GrabDecimal` only at the wire. No IEEE‑754 value is ever computed or stored. The caps above keep every intermediate product (`cents × basis points`) far inside signed 64-bit range, so `BIGINT` columns on all three engines never overflow.
3. **Rounding:** round-half-up to the cent, applied once per computed amount as defined in §5.
4. Responses echo money as strings. Negative totals are impossible: discounts are capped at the subtotal.

---

## 3. Native Commerce Content Types & Migration `004` (`ADR-024f`)

### 3.1 Migration Files (additive, idempotent)
| File | Schema Versions | Target |
|---|---|---|
| `migrations/004_commerce_schema.grab` | `[1, 2, 3, 4]` | SQLite (primary) |
| `migrations/004_commerce_schema_postgres.grab` | `[1, 2, 3, 4]` | PostgreSQL |
| `migrations/004_commerce_schema_mariadb.grab` | `[1, 2, 3, 4]` | MariaDB |

Each uses `data.migrate`, creates only new tables (`IF NOT EXISTS`), never alters or drops tables from `001`–`003`, and records the version bump. Money columns are stored as integer cents (`*_cents` `INTEGER`/`BIGINT`) with a `currency` text column; the engine-neutral `GrabDecimal` string is produced at the API boundary. `seed.grab` is **not** modified; commerce seeds live in `seed_commerce.grab` (opt-in). Running `004` directly on an empty database equals `001 → 002 → 003 → 004` (same guarantee as `SPEC-100` §2).

GRAB's internal event-store tables (§4.5) are created by GRAB's own `grab migrate --events-store` command, never by `004`, and are never touched by application SQL.

### 3.2 Tables
| Table | Key columns | Notes |
|---|---|---|
| `products` | `id`, `entry_id` (unique FK → `entries`, `content_type = product`), `sku` (unique), `kind` (`physical` \| `digital`), `price_cents`, `compare_at_cents`, `currency`, `stock_qty` (nullable = unlimited), `weight_g`, `tax_class` (`standard` \| `digital` \| `exempt`), `active` | A product **is** an entry of the built-in `product` content type, so it inherits slugs, `slug_history`, drafts, RBAC, themes and caching. **`products` is the single source of truth for price, SKU, stock and weight** (see §3.3). |
| `product_digital_files` | `id`, `product_id`, `media_id` (FK → `media`), `download_limit`, `expiry_hours` | |
| `product_fulfillment` | `product_id`, `carrier` (`usps` \| `lulu_direct`), `lulu_sku`, `usps_service`, `max_weight_g`, `media_mail_eligible` (0/1), `ships_from_country` | Physical-goods constraints (§3.4). |
| `customers` | `id`, `user_id` (nullable FK → `users`), `email` (lower-cased), `display_name`, `marketing_consent` (0/1, default 0), `created_at` | Guest checkout allowed. See §8 for account-linking rules. |
| `carts` | `id` (public opaque id, `crypto.random_urlsafe 24`), `token_hash` (unique, `sha256_hex` of the cookie token), `csrf_secret`, `customer_id` nullable, `status` (`open` \| `checked_out` \| `abandoned`), `currency`, `coupon_code`, `last_activity_at`, `created_at` | The cookie token is **never** stored in clear and is **never** the same value as `id`. Only `id` ever leaves the server in events. |
| `cart_items` | `id`, `cart_id`, `product_id`, `qty`, `unit_price_cents` (display snapshot) | Unique `(cart_id, product_id)`. |
| `coupons` | `id`, `code` (unique, upper-cased), `type` (`percent_bp` \| `fixed_cents`), `value`, `min_subtotal_cents`, `max_redemptions`, `redeemed_count`, `starts_at`, `ends_at`, `active`, `created_by` (`user:<id>` \| `mcp:<id>`) | |
| `coupon_redemptions` | `id`, `coupon_id`, `order_id`, `created_at` | Unique per `(coupon_id, order_id)`. |
| `orders` | `id`, `number` (unique, e.g. `GL-000123`), `cart_id`, `customer_id`, `status` (see §4.6), `subtotal_cents`, `discount_cents`, `tax_cents`, `shipping_cents`, `total_cents`, `currency`, `payment_ref`, `access_token_hash`, `shipping_address_json`, `needs_review` (0/1), `created_at`, `payment_due_by`, `paid_at` | Totals are frozen at checkout. |
| `order_items` | `id`, `order_id`, `product_id`, `sku`, `title`, `qty`, `unit_price_cents`, `carrier` | Immutable snapshot. |
| `order_audit` | `id`, `order_id`, `actor` (`user:<id>` \| `webhook` \| `system`), `from_status`, `to_status`, `reason`, `created_at` | Every status change writes one row. |
| `download_grants` | `id`, `order_item_id`, `token_hash` (unique), `expires_at`, `remaining` | Digital delivery (§8). |
| `idempotency_keys` | `scope`, `key`, `request_hash`, `state` (`in_flight` \| `done`), `order_id`, `created_at` | Unique on `(scope, key)`; `scope` = cart `id`. |
| `payment_events` | `event_id` (unique), `order_id`, `outcome`, `payload_hash`, `received_at` | Business-level replay protection that outlives GRAB inbox purges. |
| `commerce_events` | `id` (monotonic), `name`, `subject_id` , `payload_json`, `created_at` | Outbox for §6 events. Unique `(name, subject_id)`. |

Indexes: `idx_products_sku`, `idx_cart_items_cart`, `idx_carts_token`, `idx_carts_activity`, `idx_orders_customer`, `idx_orders_status_due`, `idx_coupons_code`, `idx_download_grants_token`, `idx_commerce_events_id`.

### 3.3 Content Types & Custom Fields
`product` is registered as a built-in content type (`/shop/:slug` permalink pattern) via the existing `content_types` / `field_definitions` registry. Price, SKU, kind, stock and weight live **only** in the `products` row and are edited through the product editor panel / admin commerce routes; they are **not** duplicated as entry custom fields, so there is exactly one place a price can come from. Optional entry custom fields: `isbn_13` (`string`, validated 13 digits + ISBN checksum), `subtitle` (`string`). The other four (`Cart`, `Order`, `Coupon`, `Customer`) are **table-backed system types**, managed only through commerce routes and admin views, never published as public entries.
`create_entry_draft` for `product` keeps `status_enforced: "draft"` (unchanged AI safety rule) and cannot set price/stock (those fields are ignored on that tool).

### 3.4 Physical vs. Digital Constraints
- **Digital:** no shipping line; `weight_g` ignored; checkout skips address collection; fulfilment = download link shown on the order-status page after `paid` (email delivery is `v1.2.0`).
- **Physical:** requires a `product_fulfillment` row; checkout requires a valid address.
  - `carrier = usps`: `usps_service` ∈ allowlist (`ground_advantage`, `priority`, `media_mail`); parcel weight ≤ `max_weight_g` (default 31 751 g / 70 lb) else `422 weight_exceeds_carrier_limit`. `media_mail` only permitted if **every** USPS item has `media_mail_eligible = 1`.
  - `carrier = lulu_direct`: requires non-empty `lulu_sku`; printing/shipping is handled by Lulu out of band. GrabLab only records the order and exposes it for fulfilment; **no outbound call to Lulu is made in `v1.1.0`** (preserves zero-network default). Mixed carts of `usps` + `lulu_direct` items produce one order with per-item `carrier` tags.
- Shipping cost = flat-rate table in `site_settings` (`shipping_rates_json`, `GrabDecimal` strings per carrier/service; one charge per carrier group present in the order); no live carrier-rate API in `v1.1.0`.
- **Oversell guard:** stock is decremented inside the checkout transaction with a conditional update (`UPDATE products SET stock_qty = stock_qty - :q WHERE id = :id AND stock_qty >= :q`); zero rows affected → whole transaction rolls back → `409 out_of_stock`.
- **Stock hold expiry:** a `pending_payment` order holds stock only until `payment_due_by` (`created_at + pending_payment_ttl_minutes`, default 60). The commerce sweep (§6.1) moves overdue orders to `expired`, restores stock and reverses the coupon redemption in one transaction.

---

## 4. Commerce Endpoints

All routes live under `/api/commerce/`, speak JSON, and return the error envelope `{error, message, field?}`.

### 4.1 Common Security Rules
1. **Shopper session & CSRF:** `GET /api/commerce/session` issues a `gl_cart` cookie (`HttpOnly; Secure; SameSite=Lax; Path=/`) holding a random token from `crypto.random_urlsafe 32`, stores only its `sha256_hex` in `carts.token_hash` (same pattern as admin `sessions`), and returns a per-cart `csrf_token`. No HMAC is needed or used. Every commerce `POST` requires a matching `X-CSRF-Token`, compared with the existing hash-then-compare `csrf_matches` pattern (missing/invalid → `403 commerce_csrf_invalid`). When a shopper logs in or out, the cart token and CSRF secret are **rotated** (session-fixation guard).
2. **RBAC:** shoppers need no role. Two new capabilities:
   - `commerce:manage` (`admin`, `editor`) — products, orders, coupons, customers, and `list_commerce_events`.
   - `commerce:settings` (`admin` only) — currency, tax, shipping, **payment redirect base/allowlist**, enable/disable store. Editors can never change where money is sent.
   Admin endpoints (`/api/admin/commerce/*`) accept **only** an authenticated session cookie + CSRF; MCP Bearer tokens are rejected there with `401` (so an AI token can never reach store management outside the two MCP tools in §6.2).
3. **Rate limits** (`cache.limit`): cart/coupon/checkout 60 req/min per client IP (`429`); coupon attempts 10/min per cart **and** 30/10 min per IP (stops cart-hopping brute force).
4. Server recomputes **all** prices from `products`; a client-sent `unit_price`/`price`/`total` field → `422 client_price_not_allowed`.
5. Bodies > 64 KiB → `413`.

### 4.2 `POST /api/commerce/cart`
Actions in body `{action: "add" | "set_qty" | "remove" | "get" | "set_customer", ...}`.
- `add` / `set_qty` / `remove`: `product_id`, `qty` (`GrabInteger` 0–999; float → `422`). Product must be `published` and `active`; unknown or draft → `404` (no existence leak).
- `set_customer`: `email` (validated, lower-cased), optional `display_name`, `marketing_consent` (`GrabInteger` 0/1, **defaults to 0**; must be an explicit opt-in checkbox in the theme). This is what makes a cart eligible for §6.
- Returns `200` with `{cart_id, items[], subtotal, discount_total, tax_total, shipping_total, total, currency}` (all money strings).
- Updates `last_activity_at`.

### 4.3 `POST /api/commerce/coupon/apply`
Body `{code}` (or `{code: ""}` to remove).
- Validations: exists, `active`, within `starts_at`/`ends_at`, `redeemed_count < max_redemptions`, subtotal ≥ `min_subtotal_cents`. Failure → `422 coupon_invalid` with machine `reason` (`expired`, `exhausted`, `min_subtotal`, `unknown`). Unknown vs. expired return the same HTTP status to limit enumeration.
- `percent_bp`: `discount = round_half_up(subtotal_cents × bp / 10000)`; `fixed_cents`: `min(value, subtotal_cents)`.
- One coupon per cart in `v1.1.0` (stacking is out of scope).
- Redemption is **counted at order creation** with a conditional update (`UPDATE coupons SET redeemed_count = redeemed_count + 1 WHERE id = :id AND active = 1 AND redeemed_count < max_redemptions`); zero rows → rollback → `409 coupon_exhausted`.

### 4.4 `POST /api/commerce/checkout`
Requires header `Idempotency-Key` (16–64 chars `[A-Za-z0-9_-]`; missing/malformed → `400 idempotency_key_required`). Requires `commerce_enabled = 1`, a non-empty payment allowlist (else `503 payment_not_configured`).

**Step A — claim the key (own short transaction, committed first).** `INSERT INTO idempotency_keys (scope = cart id, key, request_hash = sha256 of canonical body, state = 'in_flight')`.
- Insert succeeds → continue to Step B.
- Unique violation or engine busy/serialization error on this insert:
  - existing row `in_flight` → `409 idempotency_conflict` (concurrent duplicate).
  - existing row `done`, same `request_hash` → `409 idempotency_conflict` with body `{order_number, redirect_url}` of the original order (safe recovery, no duplicate).
  - existing row, different `request_hash` → `422 idempotency_key_reuse`.
- Keys are scoped to the cart, so one shopper's key can never reveal another shopper's order. `in_flight` rows older than 60 s are treated as abandoned and may be reclaimed. `done` rows are retained 24 h.

**Step B — create the order (one `data.begin` transaction, GRAB default `serializable`).**
1. Re-validate: cart `open` and non-empty, every product still `published` + `active`, carrier constraints, address (physical), customer email present.
2. **Price-change guard:** if any current `products.price_cents` differs from the cart's displayed snapshot → rollback → `409 price_changed` with the refreshed cart (shopper confirms the new price; nobody is charged a price they did not see).
3. Compute totals (§5); insert `orders` (`pending_payment`, `payment_due_by`) + `order_items` + `order_audit`; conditional stock decrement (§3.4); conditional coupon redemption (§4.3); mark cart `checked_out`; generate the order access token (`random_urlsafe 32`, store hash).
4. Build `redirect_url` from `site_settings.payment_redirect_template` by substituting **only** the percent-encoded placeholders `{order_number}`, `{amount}`, `{currency}`, `{return_url}`; then apply the allowlist check (rule 6). On failure → rollback.
5. Commit; mark the key `done` with `order_id`. Response `201 Created` `{order_number, total, currency, redirect_url}`.
6. **Redirect allowlist (`GRAB-E402`, reused here with its GRAB meaning "blocked outbound target"):** `redirect_url` must parse as `https://`, host in `site_settings.payment_redirect_allowlist` (exact, case-insensitive host match, no wildcards), no userinfo, port absent or `443`, no fragment. Anything else — `http:`, `javascript:`, `data:`, protocol-relative, IDN/look-alike not exactly listed — raises `GRAB-E402`, rolls back, and returns `502 payment_redirect_blocked`. The template and allowlist are also validated when an admin saves them (`422` at save time), so a bad setting is caught before any shopper hits it.
7. Any failure in Step B **deletes** the `in_flight` key row so the shopper can fix the cart and retry; no order exists, so this is safe.
8. GRAB `--allow-net` is **not** needed: GrabLab only emits a redirect URL; the browser navigates.

**Return page:** `{return_url}` = `/shop/order/<order_number>?t=<access token>` — a `.grab.html` order-status page (status, items, totals, digital download links once `paid`). Without a valid token → `404`. Responses are `Cache-Control: no-store` and `Referrer-Policy: no-referrer`.

### 4.5 Payment Webhook — GRAB Native Signed Webhook Profile
GrabLab does **not** implement its own signature code (GRAB `v1.1.0` `use crypto` exposes no HMAC or constant-time primitive). It uses GRAB's built-in verified webhook acceptance (`C:\Development\GRAB\docs\INTEGRATIONS.md`, `internal/connect/webhook.go`), which already performs HMAC-SHA256 with constant-time comparison.

- **Opt-in platform profile:** `deploy/grab.platform.commerce.json` (= default `grab.platform.json` + one `events` store + one `webhooks` entry). Operators switch to it only when enabling payments. It declares exact path `POST /api/commerce/webhooks/payment`, a data-only connector package `connectors/grablab-payment/` (manifest + JSON contract only; locked by `grab connect lock`; no code), event store `commerce`, handler `receive_payment_event`, and keys `GRABLAB_PAYMENT_WEBHOOK_SECRET` (+ optional `GRABLAB_PAYMENT_WEBHOOK_SECRET_NEXT` for zero-downtime rotation). Secrets come from env only; GRAB fails closed (`GRAB-E210`) if they are missing, which is why this profile is opt-in.
- **Signature (enforced by GRAB before any GrabLab code runs):** headers `Grab-Event-Id`, `Grab-Event-Time` (Unix seconds), `Grab-Signature: v1=<lowercase hex HMAC-SHA256>` over `event_id + "." + timestamp + "." + exact raw body bytes`; ±300 s window; duplicate headers / content-encoding / malformed values rejected.
- **HTTP results (GRAB host):** bad/missing signature or stale timestamp → `401`; body > 1 MiB → `413`; verified + committed to inbox → `202`; identical replay → `200`; same `event_id` with different bytes → `409`; store full/outage → `503`. Unsigned events are never admitted.
- **Body contract:** `{type: "payment.succeeded" | "payment.failed", order_number, amount: "<GrabDecimal>", currency, payment_ref}`.
- **Handler `receive_payment_event` (runs inside GRAB's host-owned transaction; business rows + completion commit together):**
  1. `event.id` already in `payment_events` → complete as `duplicate_ignored` (lasting protection even after GRAB inbox purge).
  2. Commerce disabled or unknown order → record outcome `ignored_unknown_order` / `ignored_commerce_disabled`.
  3. `amount`/`currency` ≠ stored order total → outcome `amount_mismatch`, order stays `pending_payment`, `needs_review = 1`. (The provider already received `202`; mismatch is surfaced in the admin Orders view, not as an HTTP code.)
  4. `payment.succeeded` on `pending_payment` → `paid`, `paid_at`, `payment_ref`, download grants issued, `commerce:purchase_completed` written to `commerce_events`.
  5. `payment.succeeded` on `expired`/`cancelled` → **not** auto-resurrected: outcome `late_payment`, `needs_review = 1` (merchant refunds or re-reserves manually).
  6. `payment.failed` on `pending_payment` → `payment_failed`, stock and coupon released.
- **Deployment note:** GRAB's SQLite event store is single-process. Production stores accepting payments on multiple Grisp workers must use PostgreSQL or MariaDB for the event store (documented in `deploy/README.md`).
- **Provider reality:** this profile is GRAB's generic format, **not** Stripe/PayPal native signing. In `v1.1.0` a merchant needs either a provider that can send this format or a small relay. Native provider adapters are `v1.2.0` (see §11 Q5).

### 4.6 Order State Machine
`pending_payment → paid | payment_failed | expired | cancelled`; `paid → fulfilling → shipped → delivered`; `paid | fulfilling → cancelled` (admin only, `needs_review` refund note). Any other transition → `409 invalid_transition`. Every transition writes `order_audit`. Totals are never editable.

---

## 5. Totals Algorithm (deterministic)

```
subtotal  = Σ qty × unit_price_cents                                    -> subtotal_cents
discount  = coupon rule (§4.3), capped at subtotal                      -> discount_cents
per tax_class c:  line_c = Σ lines in class c
                  disc_c = discount allocated pro rata to line_c (largest-remainder, ties → lowest product_id)
                  tax_c  = round_half_up((line_c − disc_c) × rate_bp[c] / 10000)
tax       = Σ tax_c                                                      -> tax_cents
shipping  = Σ flat rate per carrier group present (0 if no physical)    -> shipping_cents (not taxed in v1.1.0)
total     = subtotal − discount + tax + shipping                        -> total_cents
```
- `rate_bp[c]` is a `GrabInteger` basis-point setting per `tax_class` (`standard`, `digital`, `exempt` = 0); no external tax API in `v1.1.0`. With one class in the cart this reduces to a single rounding on the whole cart.
- Test vectors (must pass exactly): `[$19.99 × 3, coupon 15%, standard 8.25%] → subtotal 59.97, discount 9.00 (8.9955→9.00), tax on 50.97 = 4.21 (4.205025→4.21), total 55.18`, plus at least twelve more in `tests/commerce_vectors.json` including `0.01`, `9999999.99`, mixed tax classes, discount allocation remainders, fixed coupon > subtotal, and half-cent boundaries.

---

## 6. Abandoned-Checkout Hook & Ecosystem Interoperability

### 6.1 Commerce Sweep (no scheduler required)
GRAB has no general scheduler, so the sweep is **lazy and idempotent**: it runs at the start of any commerce request, admin store page load, or `list_commerce_events` call, at most once per 5 min across all workers (guarded by `cache.limit` key `commerce:sweep`, limit 1 per 300 000 ms). Operators may also run `grab run scripts/commerce_sweep.grab` from an external cron. Each run (bounded to 500 rows):
1. Expires overdue `pending_payment` orders (§3.4).
2. Marks `open` carts with items, a customer email and `last_activity_at` older than `abandoned_after_minutes` (default 60) as `abandoned`, and — **only if `marketing_consent = 1`** — writes one event per cart (unique `(name, subject_id = cart id)`):

```json
{
  "name": "commerce:abandoned_checkout",
  "version": 1,
  "cart_id": "<public cart id, never the cookie token>",
  "email_hash": "sha256:<hex of commerce_email_salt + email>",
  "marketing_consent": 1,
  "currency": "USD",
  "subtotal": "59.97",
  "items": [{"sku": "BOOK-001", "title": "…", "qty": 3, "unit_price": "19.99", "url": "/shop/book-001"}],
  "last_activity_at": "2026-11-17T18:00:00Z"
}
```
- Raw email is **not** in the event. `commerce_email_salt` is a per-site random value (`random_hex 32`) created when commerce is first enabled, so hashes cannot be reversed with a public email list or correlated across sites.
- The recovery email itself is a `v1.2.0` outbox concern.
- The hook is also emitted through the native hook registry (`source: "core"`), so themes cannot spoof it (`GRAB-E401` rule from `SPEC-100` §4).

### 6.2 `Groxy AI v1.4.0` Consumption (two additive MCP tools)
| Tool | Permission | Input | Safety behavior |
|---|---|---|---|
| `list_commerce_events` | `commerce:manage` | `name?`, `after_id` (cursor), `limit` 1–100 | Read-only; returns events in ascending `id`. |
| `create_coupon_draft` | `commerce:manage` | `code`, `type`, `value`, `min_subtotal`, `max_redemptions`, `starts_at`, `ends_at` | **Always inserts `active = 0`** and returns `active_enforced: 0`, `created_by: "mcp:<id>"`; `max_redemptions` required and ≤ 1000; percent ≤ 5000 bp. Activation only via a human admin session + CSRF. |
- Groxy responds at its own endpoint `POST /api/groxy/commerce/recovery` (defined in Groxy's spec, not here). Copy returns only via `create_entry_draft` (`status_enforced: "draft"`); offers only via `create_coupon_draft`. No MCP tool can activate a coupon, change a price, change stock, change settings, or refund.
- Both tools are additive to the frozen `SPEC-100` registry; existing tools are unchanged.

### 6.3 `Plotific Press` Interop
- Book products use `kind=physical` + `carrier=lulu_direct` or `kind=digital`, and carry `isbn_13` as a validated `string` field; price remains `GrabDecimal` (no float drift into `schema.org/Offer` `price`).
- Product pages emit `schema.org/Product`/`Offer` JSON-LD with `price` as the exact string; escaped via existing XSS-safe serializers.
- **`slug_history` 301s are preserved:** renaming a product slug writes `slug_history` exactly as for other entries; `/shop/<old>` → `301 /shop/<new>`; carts and order items reference `product_id`, never the URL, so redirects cannot break open carts.

---

## 7. Commerce Admin Views (pure `Grex JS v1.0.0`)

New `.grab.html` views, using only the 20 Grex elements and semantic HTML5:
`/admin/store` (dashboard incl. "needs review" queue), `/admin/store/products`, `/admin/store/orders` (+ detail with audit trail), `/admin/store/coupons` (drafts from Groxy clearly labelled), `/admin/store/customers`, `/admin/store/settings` (`commerce:settings` only: enable store, currency, tax rates, shipping rates, payment redirect template + allowlist, pending-payment TTL, abandoned threshold — webhook secrets are **shown as set/unset only**, never displayed).
- Tables built with `Grid`/`ForEach`; forms with `Form`/`Input`/`Select`; destructive actions in `Modal` confirmation.
- Orders are **never silently edited**: status changes follow §4.6 and write `order_audit`; totals are read-only.
- Customer email/address shown partially masked except to `commerce:manage`.
- Money inputs are text inputs (`inputmode="decimal"`) submitted as strings, never `type="number"` coerced via JS floats.
- No `innerHTML` writes; all text via `textContent`/Grex bindings; unsafe URL schemes rejected.
- Light and Dark themes via `data-grex-theme`, tokens meet WCAG AA.

---

## 8. Security, Privacy & Deployment Notes
- **Account linking:** a guest order is linked to a `users` row only when placed from that user's logged-in session. Typing a registered user's email at guest checkout never attaches the order to that account or reveals that account's history.
- **Digital delivery:** `download_grants` tokens are `random_urlsafe 32`, stored as `sha256_hex`, bound to one order item, expire after `expiry_hours`, and decrement `remaining`; files stream from the existing writable `uploads/` mount with `Cache-Control: no-store`. No HMAC/master-key derivation is needed.
- **PII:** customer email/address stored only for orders; `GET /api/admin/commerce/customers/:id/export` and `DELETE …` (anonymize) support GDPR requests; deletion keeps order totals but nulls identifying columns.
- **Logging:** never log full webhook bodies, secrets, cookie/CSRF/download/access tokens, or addresses.
- **Container:** unchanged `--read-only` profile; the commerce platform profile adds `--allow-env GRABLAB_PAYMENT_WEBHOOK_SECRET,GRABLAB_PAYMENT_WEBHOOK_SECRET_NEXT` and the GRAB event grants (`--allow-events commerce:accept`, `commerce:work`).
- **Cache:** product, price and settings changes invalidate existing `use cache` entry/route keys plus new `commerce:product:<id>` keys; carts, orders, order-status pages and downloads are never cached.
- **Stable branch:** this milestone ships to `origin` only until fully verified; `stable` stays at `v1.0.1`.

---

## 9. Section 9 Acceptance Gates (all must pass 100%)

1. **`grab check`** zero errors on every `.grab` and `.grab.html` file (including new migrations, handler and views); `grab connect lock` / `inspect` clean for `connectors/grablab-payment/`.
2. **Canonical format:** `grab format <file>` stdout byte-identical to on-disk bytes for every `.grab` file.
3. **Zero-DOM-debt:** `divCount === 0` and `innerHTMLWriteCount === 0` across all commerce views, order-status page and starter-theme product/cart templates; zero `eval`/`new Function`; zero unsafe URL schemes.
4. **Accessibility:** `auditAccessibility()` passes 100%; Light **and** Dark contrast `>= 4.5:1` (normal text), `>= 3.0:1` (large text).
5. **Numeric fidelity (`422`):** floats/exponents in any money or quantity field rejected with `422`; `"19.99"` round-trips byte-exact through API → DB → API on SQLite, PostgreSQL and MariaDB; all §5 vectors exact; caps enforced.
6. **Authorization (`401`/`403`):** missing/invalid `X-CSRF-Token` → `403` on cart, coupon, checkout and admin routes; shopper on `/api/admin/commerce/*` → `403`; `author`/`viewer` → `403`; `editor` on settings → `403`; MCP Bearer token on `/api/admin/commerce/*` → `401`; cart token rotates on login.
7. **Concurrency (`409`):** 20 parallel checkouts with one `Idempotency-Key` → exactly one `201`, nineteen `409`, exactly one order row; sequential retry → `409` with original `order_number`; same key from a different cart → independent; two parallel checkouts for the last unit → one success, one `409 out_of_stock`; last coupon redemption raced → one success, one `409 coupon_exhausted`; duplicate webhook `event_id` → single state transition.
8. **Webhook security:** bad signature, stale timestamp, tampered body, duplicate headers → `401`; replay → `200` no-op; same id/different body → `409`; amount mismatch → order unchanged + `needs_review`; late payment on expired order → not resurrected; site with default platform profile starts without any webhook secret.
9. **Redirect safety (`GRAB-E402`):** `http:`, `javascript:`, `data:`, protocol-relative, userinfo, non-allowlisted / look-alike host, non-443 port, fragment all blocked at save time and at checkout, order rolled back.
10. **Carrier & stock rules:** USPS weight/service/media-mail limits and `lulu_direct` SKU requirement enforced; digital items skip shipping; overdue `pending_payment` orders expire and restore stock + coupon; price change → `409 price_changed`.
11. **Abandoned-checkout event:** exactly one event per qualifying consented cart, none for non-consented carts, no raw email, no cookie token, salted hash; sweep runs without any scheduler; `list_commerce_events` cursor works; `create_coupon_draft` always yields `active = 0`.
12. **`slug_history`:** renamed product slug returns `301` to the new URL and open carts remain valid.
13. **Regression:** existing `tests/integration_test.py` (13/13) and `tests/release_v100_test.py` (5/5) still pass unchanged; a `v1.0.1` database upgrades via migration `004` with zero data loss; commerce disabled by default returns `404`.
14. **New suites:** `tests/commerce_test.py` (API, security, concurrency, vectors, webhook handler) and `tests/release_v110_test.py` (fresh install → store setup → checkout → signed webhook → paid order → download E2E, Light/Dark audit) pass **100%**.

---

## 10. Implementation Order (after approval)
1. Migration `004` ×3 engines + `seed_commerce.grab`.
2. Totals engine + numeric validators + vectors.
3. Shopper session/CSRF + cart / coupon endpoints.
4. Checkout + idempotency + redirect allowlist + order-status page.
5. Commerce platform profile + data-only connector + `receive_payment_event` handler.
6. Commerce sweep + `commerce_events` + MCP `list_commerce_events` / `create_coupon_draft`.
7. Admin views + starter-theme product/cart templates.
8. Tests, gates, walkthrough PDF, release notes with compatibility matrix.

## 11. Confirmed Owner Decisions (Q1–Q6, Approved 2026-11-17)
1. **Scope & roadmap slot:** Keep existing `v1.0.1` SEO/redirect core intact; `v1.1.0` focuses strictly on the Zero-Plugin E-Commerce Core. (The previously re-slotted SEO Redirect Manager + Groxy SEO Assist scope remains planned for a future version slot TBD by the project owner.)
2. **Currency & numeric format:** USD only (`"USD"`) using exact `ADR-025c` base-10 `GrabDecimal` wire strings (`"0.00"`).
3. **Shipping & tax:** Flat-rate shipping and configurable tax tables for `v1.1.0` (shipping not taxed; no live carrier or tax APIs), preserving USPS-only carrier rules for facility book shipments.
4. **Guest checkout:** Enabled by default (with optional account creation / logged-in linking per §8).
5. **Payment verification & redirects:** Approved as scoped in Revision 2 — use GRAB `v1.1.0`'s native signed webhook verification (`deploy/grab.platform.commerce.json`) + `GRAB-E402` allowlisted checkout redirects without modifying frozen GRAB `v1.1.0`. (Provider-specific webhook adapters for Stripe/PayPal/LemonSqueezy/Paddle remain `v1.2.0`.)
6. **Abandoned-checkout consent gate:** Require explicit marketing opt-in (`marketing_opt_in: true` / `marketing_consent = 1`) before emitting `commerce:abandoned_checkout` reminders.

## 12. Runtime Facts Verified for This Revision (GRAB `v1.1.0`)
| Fact | Source | Effect on this spec |
|---|---|---|
| `use crypto` = `hash_password`, `verify_password`, `random_urlsafe`, `random_hex`, `sha256_hex`, `sha256_base64url`, `encrypt_aead`, `decrypt_aead` — **no HMAC, no constant-time compare** | `internal/interpreter/crypto.go` | Cookies, downloads and order access use random tokens stored hashed; webhook uses GRAB native verification. |
| Native verified webhooks: HMAC-SHA256, `hmac.Equal`, ±300 s, 2 rotating keys, inbox replay 200/409, host-owned handler transaction | `internal/connect/webhook.go`, `docs/INTEGRATIONS.md` | §4.5. |
| Missing platform credential → `GRAB-E210` fail-closed at serve preparation | `internal/platform/config.go` | Webhook lives in opt-in platform profile. |
| SQLite event store is single-process | `docs/INTEGRATIONS.md` | Multi-worker payment sites need PostgreSQL/MariaDB event store. |
| No general cron/job scheduler | `specifications/GRAB-SCALE-SPEC-008.md` | Lazy sweep (§6.1). |
| `data.begin` default isolation `serializable` | `internal/interpreter/data.go` | Checkout transaction; busy/serialization errors on key claim map to `409`. |
| Lossless `json.parse` keeps `integer` vs `decimal` | `docs/ROADMAP.md` (GRAB) | Float detection in §2. |
| `GRAB-E402` = blocked outbound/SSRF target | GRAB `docs/ROADMAP.md` | Reused with the same meaning for payment redirects. |
