# GrabLab CMS v0.3 Specification (`GRABLAB-SPEC-003`)

**Status:** Draft / In Review (`Approved target; specification in review`)  
**Target Milestone:** `grablab-cms v0.3.0`  
**Owner:** Project Owner (`urbanspress`) · **Author:** Google Antigravity  
**Platform Baseline:** GRAB `v1.0.1` (`use data`, `use cache`, `use server`, `server.asset`, `grab mcp`) & Grex JS `v1.0.0` (`grex.elements.json`, `createTheme`, `createClassManager`, `ForEach`, `useQuery`, `Form`, `Input`, `Select`, `Tabs`, `Modal`, `Nav`)

> **Approval Gate:** No `GrabLab` `v0.3.0` application code (`.grab`, `.grab.html`, `.js`, or SQL migrations) may be written until the project owner explicitly approves this specification.

---

## 1. Purpose & Architectural Principles

GrabLab CMS `v0.3.0` adds **authentication, role-based access control, optional OAuth2/PKCE social login, and the CSRF-protected Admin Dashboard** on top of the `v0.1.0` data/routing core and `v0.2.0` Exclusive Theme Engine:

1. **Zero-Plugin Security Boundary:** Authentication, roles/capabilities, CSRF protection, and social login are built directly into core `.grab` modules. There is no third-party auth plugin loader or arbitrary code execution.
2. **Deny-by-Default Access Control:** Every `/admin/*` route and every mutating `/api/*` endpoint (`POST`, `PUT`, `PATCH`, `DELETE`) requires an authenticated session, a valid capability check for the user's role, and a verified per-session `X-CSRF-Token`.
3. **Disabled-by-Default Social Login:** Built-in OAuth2/PKCE providers (**Google**, **GitHub**, **Discord**, **Apple**) are **off by default**. Until an administrator explicitly enables a provider in Admin Settings, `/login` renders zero social login buttons and GrabLab makes zero outbound OAuth network requests.
4. **Exclusive Theme Control From `/admin/themes`:** Site owners can switch between installed coded themes and the **Grex Theme Builder** visual theme (`mode: "visual"`) in one click, atomically deactivating the prior theme with zero overlap or style leakage.
5. **GRAB `v1.0.1` Precision & Compatibility:** All migrations (`002_auth_schema*.grab`) remain compatible with SQLite, MariaDB, and PostgreSQL, use literal prepared SQL (`use data`), exact `GrabInteger` timestamps/counters, and deterministic `use cache` keys compatible with `--read-only` containers.

---

## 2. Database Schema & Migrations (`use data`)

New tables are introduced in `migrations/002_auth_schema.grab` (SQLite), `migrations/002_auth_schema_mariadb.grab` (MariaDB), and `migrations/002_auth_schema_postgres.grab` (PostgreSQL), plus an `author_id` column on `entries` (nullable for legacy `v0.1`/`v0.2` seeded rows, populated for new entries).

### 2.1 `users`
Stores local and social-linked user accounts.

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY` | Auto-increment / sequence |
| `email` | `TEXT` (`VARCHAR(255)`) | `UNIQUE NOT NULL` | Normalized lowercase trimmed email |
| `display_name` | `TEXT` (`VARCHAR(120)`) | `NOT NULL` | Shown in Admin UI and author attribution |
| `role` | `TEXT` (`VARCHAR(32)`) | `NOT NULL DEFAULT 'viewer'` | `admin` \| `editor` \| `author` \| `viewer` |
| `password_hash` | `TEXT` | `NULL` | `argon2id` (preferred) or `bcrypt` PHC hash; `NULL` only for OAuth-only users until password is set |
| `email_verified` | `INTEGER` | `NOT NULL DEFAULT 0` | `1` = verified, `0` = unverified |
| `is_active` | `INTEGER` | `NOT NULL DEFAULT 1` | `1` = enabled, `0` = suspended |
| `last_login_at` | `TEXT` | `NULL` | ISO-8601 UTC |
| `created_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |
| `updated_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |

### 2.2 `sessions`
Stores server-side authenticated sessions. Only a cryptographic hash of the session token is stored in the database (`token_hash = sha256(raw_token)`), never the raw cookie value.

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `id` | `TEXT` (`VARCHAR(64)`) | `PRIMARY KEY` | Random UUID/hex session identifier |
| `user_id` | `INTEGER` | `NOT NULL REFERENCES users(id) ON DELETE CASCADE` | Owning user |
| `token_hash` | `TEXT` (`VARCHAR(128)`) | `UNIQUE NOT NULL` | SHA-256 hex digest of the cookie secret |
| `csrf_secret` | `TEXT` (`VARCHAR(128)`) | `NOT NULL` | Per-session random secret used to derive/verify `X-CSRF-Token` |
| `ip_hash` | `TEXT` (`VARCHAR(64)`) | `NOT NULL DEFAULT ''` | Privacy-preserving SHA-256 of client IP + app salt |
| `user_agent` | `TEXT` | `NOT NULL DEFAULT ''` | Truncated UA string (max 255 chars) |
| `expires_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |
| `created_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |
| `last_seen_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |

### 2.3 `oauth_accounts`
Links external OAuth2/PKCE identities to `users`.

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY` | Auto-increment |
| `user_id` | `INTEGER` | `NOT NULL REFERENCES users(id) ON DELETE CASCADE` | Linked GrabLab user |
| `provider` | `TEXT` (`VARCHAR(32)`) | `NOT NULL` | `google` \| `github` \| `discord` \| `apple` |
| `provider_user_id` | `TEXT` (`VARCHAR(190)`) | `NOT NULL` | Immutable `sub` / provider numeric ID |
| `provider_email` | `TEXT` (`VARCHAR(255)`) | `NOT NULL` | Normalized verified email from provider |
| `created_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |
| `updated_at` | `TEXT` | `NOT NULL` | ISO-8601 UTC |
| **Constraint** | `UNIQUE(provider, provider_user_id)` | | Prevents duplicate links to the same external account |

### 2.4 `entries.author_id` Migration & Initial Admin Bootstrap
- Add nullable `author_id INTEGER NULL REFERENCES users(id) ON DELETE SET NULL` to `entries` so `author` capability checks (`entries:update_own`, `entries:delete_own`) can verify ownership.
- **First-Run Bootstrap:** If `users` has `0` rows on startup or `grab run` / `/admin` first visit, `/setup` (or CLI seed `GRABLAB_ADMIN_EMAIL` + `GRABLAB_ADMIN_PASSWORD`) creates the initial `admin` user. Once at least one `admin` exists, `/setup` is permanently disabled (`404` / `403`).

---

## 3. Roles, Capabilities & Authentication Security

### 3.1 Built-In Roles & Capability Matrix
Roles are fixed, core-defined tiers. Every `/admin/*` page and `/api/*` mutation checks the required capability before executing any handler logic:

| Capability | `admin` | `editor` | `author` | `viewer` |
| --- | --- | --- | --- | --- |
| `admin:access` (view `/admin`) | Yes | Yes | Yes | No (`403`) |
| `entries:read_all` (drafts/archived) | Yes | Yes | Own only | No |
| `entries:create` | Yes | Yes | Yes | No |
| `entries:update_own` | Yes | Yes | Yes | No |
| `entries:update_any` | Yes | Yes | No | No |
| `entries:publish` | Yes | Yes | No (draft only) | No |
| `entries:delete_own` | Yes | Yes | Yes | No |
| `entries:delete_any` | Yes | Yes | No | No |
| `types:manage` (content types & fields) | Yes | No | No | No |
| `themes:manage` (switch/import themes) | Yes | No | No | No |
| `settings:manage` (site & OAuth settings) | Yes | No | No | No |
| `users:manage` (create/edit/suspend users) | Yes | No | No | No |

### 3.2 Password Hashing, Session Cookies & Session Rotation
1. **Password Hashing:**
   - Passwords must be at least 10 characters (max 128) and hashed using `argon2id` (recommended baseline: `m=65536, t=3, p=1`) or `bcrypt` (cost `>= 12`) when `argon2id` is unavailable in the runtime environment. Never store plaintext passwords or reversible encryption.
   - Verification uses constant-time comparison.
2. **Session Cookie Contract (`grablab_session`):**
   - `HttpOnly`: Always `true` (never readable by client JavaScript).
   - `SameSite`: `Lax` (required so OAuth2 top-level redirects return the session cleanly while blocking cross-site POSTs).
   - `Secure`: `true` when served over HTTPS / `GRABLAB_SECURE_COOKIES=true` (auto-detected from `X-Forwarded-Proto: https` or TLS listener).
   - `Path`: `/`.
   - Default TTL: `7` days (sliding renewal at 50% lifetime), invalidated immediately on logout or user suspension (`is_active = 0`).
3. **Session Rotation on Login & Privilege Escalation:**
   - Every successful login (password or OAuth2) and password change **destroys any pre-existing session ID** in `sessions`, generates a fresh cryptographic session ID + `token_hash` + `csrf_secret`, and sets a new `Set-Cookie: grablab_session=...` header (preventing session fixation).

### 3.3 Brute-Force Rate Limiting (`use cache`)
All authentication endpoints (`POST /api/auth/login`, `POST /api/auth/oauth/:provider/callback`) enforce `use cache`-backed sliding/fixed-window rate limits:
- **Per IP + Email key:** `ratelimit:login:<ip_hash>:<email_hash>` — maximum `5` failed attempts per `15` minutes. Exceeding the limit returns HTTP `429 Too Many Requests` with `Retry-After` header.
- **Per IP global key:** `ratelimit:auth_ip:<ip_hash>` — maximum `20` auth attempts per `15` minutes.
- Successful login clears the per-IP+Email failure counter.

---

## 4. Optional Built-In OAuth2 / PKCE Social Login Toggle

### 4.1 Disabled-by-Default Invariant
- All four built-in providers (**Google**, **GitHub**, **Discord**, **Apple**) start **disabled** (`enabled: false`) in `site_settings`.
- **Zero UI Footprint When Disabled:** When no provider is enabled, `/login` renders **only** the standard email + password form—zero social login buttons, zero OAuth JS, and zero `<link>`/`<img>` references to provider domains.
- **Zero Outbound Network Calls When Disabled:** Calling `/api/auth/oauth/:provider/start` or `/api/auth/oauth/:provider/callback` for a disabled provider immediately returns `404 Not Found` (or `403 Provider Disabled`) without touching the network.

### 4.2 Per-Provider Admin Configuration & Secret Protection
Administrators configure each provider individually in **Admin -> Settings -> Social Login** (`site_settings` key `oauth_providers_json` or env overrides):
- Per-provider fields:
  - `enabled`: `boolean` (default `false`)
  - `client_id`: `string`
  - `client_secret`: stored encrypted at rest (AEAD `AES-256-GCM` keyed by `GRABLAB_MASTER_KEY` env var) OR referenced via environment variable (`GRABLAB_OAUTH_<PROVIDER>_CLIENT_SECRET`).
  - `allowed_domains` (optional): restrict auto-linking/login to specific email domains if desired.
- **Never Exposed to Templates or Public APIs:** `client_secret` (and encrypted ciphertext) is **never** included in public API responses, `/login` HTML, Grex JS props, or `GET /api/admin/settings` responses (Admin UI receives only `has_secret: true|false` and masked hint `••••1234`).

### 4.3 OAuth2 Authorization Code + PKCE Flow & Strict Allowlists
When a provider is enabled:
1. **Start (`GET /api/auth/oauth/:provider/start`):**
   - Generates cryptographically random `state` (32 bytes) and PKCE `code_verifier` (64 bytes, URL-safe), computes `code_challenge = BASE64URL(SHA256(code_verifier))` (`code_challenge_method=S256`).
   - Stores `{ provider, code_verifier, redirect_after, created_at }` in `use cache` under `oauth:state:<state>` with a `300`-second (5-minute) TTL.
   - Redirects (`302`) to the provider's hardcoded authorization endpoint.
2. **Callback (`GET /api/auth/oauth/:provider/callback`):**
   - Validates `state` against `use cache` (`oauth:state:<state>`), immediately deletes it (single-use anti-CSRF/replay), and verifies `provider` matches.
   - Exchanges `code` + `code_verifier` via server-to-server `POST` to the provider's token endpoint.
3. **Verified-Email Account Linking Policy:**
   - **Rule 1 (Existing `oauth_accounts` link):** Look up `(provider, provider_user_id)`. If found and `user.is_active = 1`, rotate session and log in.
   - **Rule 2 (Verified Email Match):** Require `email_verified == true` from the provider (`Google` `email_verified`, `GitHub` primary verified email via `/user/emails`, `Discord` `verified == true`, `Apple` verified `id_token` claim). **Unverified emails MUST be rejected (`403`)** to prevent account takeover.
   - If a local `users` row exists with that verified email and `is_active = 1`, link the `oauth_accounts` row and log in.
   - If no user exists, **auto-registration is disabled by default** (`oauth_allow_signup = false`), returning a clear message unless an admin explicitly enables self-signup (in which case new users receive the lowest-privilege `viewer` role, never `admin`).
4. **Strict Grisp `--allow-net` Domain Allowlist:**
   All outbound OAuth2 HTTP calls are strictly confined to the hardcoded per-provider host allowlist (never user-supplied URLs, preventing SSRF):
   - **Google:** `accounts.google.com`, `oauth2.googleapis.com`, `openidconnect.googleapis.com`
   - **GitHub:** `github.com`, `api.github.com`
   - **Discord:** `discord.com`
   - **Apple:** `appleid.apple.com`

---

## 5. CSRF-Protected Admin Dashboard (`Grex JS v1.0.0`)

### 5.1 Mandatory `X-CSRF-Token` Validation
- Every authenticated session has a per-session `csrf_secret` stored in `sessions`.
- On `/admin/*` page loads (and `GET /api/auth/session`), the server provides the session's CSRF token via `<meta name="grablab-csrf" content="...">` and JSON `csrf_token` field.
- Every state-changing request (`POST`, `PUT`, `PATCH`, `DELETE`) under `/admin/*` and `/api/*` (except `/api/auth/login` and `/api/auth/oauth/*` which use `state`+PKCE) MUST include a matching `X-CSRF-Token` HTTP header (or `_csrf` form field for progressive-enhancement forms).
- Missing or mismatched tokens return **`403 Forbidden`** (`{ "error": "csrf_invalid" }`) before any DB write or state mutation occurs.

### 5.2 Admin Routes & `Grex JS v1.0.0` UI Architecture
The Admin Dashboard is a core GrabLab module served under `/admin/*` (never overridden by active frontend themes, preserving the Exclusive Active Theme boundary for public routes). It uses `Grex JS v1.0.0` (`Form`, `Input`, `Select`, `Tabs`, `Modal`, `Nav`, `ForEach`, `useQuery`, `createTheme`):

| Route | Required Capability | Purpose & Grex Components |
| --- | --- | --- |
| `/login` | Public | Email + password `Form` (`Input`, submit button). Renders enabled social buttons **only** if `>= 1` provider is enabled. |
| `/admin` | `admin:access` | Overview dashboard: content counts, active theme badge, recent entries (`ForEach`), quick actions, and navigation (`Nav`). |
| `/admin/entries` | `entries:read_all` (or own) | Filterable entry list (`ForEach` + `useQuery`), status filter (`Select`), create/edit entry editor (`Form`, `Input`, `Select`, custom fields, slug preview, `slug_history` 301 redirect inspector). |
| `/admin/types` | `types:manage` | Content Type & Custom Field manager (`ForEach`, `Modal` to add/edit `content_types` and `field_definitions` with `integer`/`decimal`/`url`/`json` types). |
| `/admin/themes` | `themes:manage` | **1-Click Exclusive Theme & Grex Theme Builder Switcher** (see Section 5.3). |
| `/admin/settings` | `settings:manage` | `Tabs` for **General** (`site_title`, `home_entry_id`), **Social Login** (per-provider enable toggle, Client ID, masked Secret, `--allow-net` domain checklist), and **Users & Roles** (`users:manage` tab to invite/edit/suspend users). |

### 5.3 1-Click Exclusive Theme & Grex Theme Builder Switcher (`/admin/themes`)
- Lists all validated themes from `themes/` (`default-starter` coded theme, any imported coded themes, and the **Grex Theme Builder** visual theme `mode: "visual"` when installed).
- Each theme card displays: `name`, `version`, `mode` badge (`Coded Theme` vs `Grex Visual Builder`), `author`, and `Active` status indicator.
- Clicking **Activate** sends `POST /api/admin/themes/activate` with `{ "slug": "<target>" }` and `X-CSRF-Token`:
  1. Calls `activate_theme(slug)` inside a `use data` transaction (`is_active = 0` on all themes, `is_active = 1` on target, updates `site_settings.active_theme_slug`).
  2. Purges non-core hooks, reloads active theme hooks/parts, and invalidates `use cache` (`theme:active`, `theme:parts:*`, `route:*`, `query:*`).
  3. Updates the UI immediately so only one theme shows as active, and all public routes (`/`, `/blog`, `/:slug`) render 100% from the newly active theme.

---

## 6. Acceptance & Test Gates

Milestone `v0.3.0` cannot be marked complete until all gates pass **100%**:

1. **GRAB Compiler & Format Gate:**
   - `grab check` passes on all `.grab` and `.grab.html` files with zero errors.
   - `grab format --check` confirms canonical formatting across all `.grab` files.
2. **Database & Migration Gate:**
   - `002_auth_schema` migrations run idempotently on SQLite (and pass schema parity checks for MariaDB/PostgreSQL).
3. **Authentication, Session Rotation & Rate-Limit Tests:**
   - Password hashing uses `argon2id` or `bcrypt` (never plaintext).
   - Login sets `HttpOnly`, `SameSite=Lax` cookie; session ID rotates on login (old session token is invalidated).
   - 6th failed login attempt within 15 minutes returns `429 Too Many Requests` via `use cache` rate limiter.
4. **Role & Capability Enforcement Tests:**
   - `viewer` receives `403` on `/admin` and all `/api/admin/*` mutations.
   - `author` can create/edit/delete own drafts, cannot publish (`403`), cannot edit another user's entry (`403`), and cannot access `/admin/types`, `/admin/themes`, or `/admin/settings` (`403`).
   - `editor` can publish/edit any entry, cannot manage types/themes/settings/users (`403`).
   - `admin` has full access.
5. **CSRF Protection Tests:**
   - Every `POST`/`PUT`/`PATCH`/`DELETE` to `/api/admin/*` and `/api/entries*` without `X-CSRF-Token` or with a wrong token is rejected with `403 Forbidden`.
6. **Disabled-by-Default & OAuth2/PKCE Social Login Tests:**
   - With all providers disabled (default): `/login` HTML contains zero social login buttons/links, and `/api/auth/oauth/google/start` returns `404`/`403` with zero outbound network calls.
   - With a test provider enabled: `/api/auth/oauth/:provider/start` issues a `state` + `S256` PKCE `code_challenge`, `/callback` rejects mismatched `state` (`403`), rejects unverified emails (`403`), links verified emails cleanly, rotates session, and never leaks `client_secret` in any template or API response.
7. **Admin Dashboard & 1-Click Theme Switcher Tests:**
   - `/admin`, `/admin/entries`, `/admin/types`, `/admin/themes`, and `/admin/settings` render with valid Grex JS `v1.0.0` components (`Form`, `Input`, `Select`, `Tabs`, `Modal`, `Nav`, `ForEach`) and zero `securityRules` violations.
   - Activating a theme via `POST /api/admin/themes/activate` atomically deactivates the prior theme (`is_active = 0`) and switches public rendering 100% to the new theme.
8. **Release Guide Gate:**
   - `docs/releases/pdf/GrabLab-v0.3.0-Guide.pdf` plain-English walkthrough guide is generated upon milestone completion.
