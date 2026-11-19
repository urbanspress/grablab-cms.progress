# GRABLAB-SPEC-150 · GrabLab CMS v1.5.0

**Approved & Frozen — Complete** · 2026-11-19 · MINOR under ADR-027c

The owner reviewed the live profile in Light and Dark modes and approved the six-tab layout and the two header-link icons. This release builds on CMS v1.4.1, GRAB v1.1.0 and Grex JS v1.0.0. Existing databases and neighboring runtimes remain compatible.

## Admin shell and profile

- **Header navigation.** Keep visible text on every menu link. Posts and Pages are the two owner-approved exceptions with decorative WordPress-style SVGs. The viewer menu contains only the text link to Profile.
- **Universal profile.** All four authenticated roles share six vertical tabs on `/admin/profile`: My Profile, Security, Notifications, Billing & Subscriptions, Data Export, and Delete Account. Each selected panel uses the responsive card grid. The two-tier admin header stays sticky. The cards expand in place without an internal scrollbar.
- The dark `.cms-fleetyu-header` runs from gold (`#d18700`) to plum (`#61022e`). Light mode uses the light header tokens. The locally hosted Urbanist family provides four weights with system sans-serif fallbacks.
- Each `tab` activates one `tabpanel`. Arrow keys navigate the vertical tablist. The selection is reflected in `?section=` and initial hash links resolve to the corresponding tab. Panels share `.cms-profile-grid`, which uses two columns on wide screens.
- My Profile displays the signed-in user's identity, account activity, capabilities and sign-in methods. Edit changes the display name on the server and selects one of six PNG portraits in `public/admin/avatars/` for this browser.
- Security provides password strength feedback and session controls. Notifications stores browser-local preferences. Billing describes the self-hosted edition and links authorized roles to Commerce. Data Export downloads account data as JSON. Delete Account directs the user to an administrator for removal.
- Expandable cards respond to click, Enter or Space, animate their height and respect reduced-motion settings. Escape dismisses the edit dialog and restores focus.

## Universal User Profile Backend Contracts (`src/app.grab`)

Profile API endpoints authenticate strictly via `grablab_session` cookie (`resolve_session`, rejecting unauthenticated calls with `401` and rejecting MCP Bearer tokens with `401`). All mutating endpoints require a valid `X-CSRF-Token` (`403` on missing/invalid CSRF).

| Method & Route | Auth / Cap | Behavior & Security Guardrails |
|---|---|---|
| `GET /admin/profile` | Any authenticated role | Renders `views/admin/dashboard.grab.html` with `admin_page: "profile"` for `admin`, `editor`, `author`, and `viewer`; unauthenticated redirects `302 -> /login`. |
| `GET /login` | Public | If already signed in: redirects `302 -> /admin` (`admin:access`) or `302 -> /admin/profile` (`viewer`). |
| `GET /api/auth/profile` | Session cookie | Returns `{ user, has_password, sessions, oauth_accounts, capabilities, stats }` (`Cache-Control: no-store`). Never leaks `password_hash`, `token_hash`, or `csrf_secret`. |
| `PATCH /api/auth/profile` | Session + CSRF | Updates the signed-in user's own `display_name` (trimmed, non-empty, `<= 80` chars, single-line). Cannot escalate `role`, `is_active`, or `email_verified`. |
| `POST /api/auth/password` | Session + CSRF | Rate-limited (`check_login_rate_limit`). Verifies `current_password` via `crypto.verify_password` (`403` on mismatch; `409` if OAuth-only), enforces `10..1024` chars and `new != current`, hashes with `argon2id`, atomically updates `password_hash` after checking the previously verified hash still matches and revokes all other sessions (`keep_id = current session`) inside `data.begin` transaction. |
| `POST /api/auth/sessions/revoke-others` | Session + CSRF | Deletes all rows in `sessions` for `user_id` except the caller's current `session_id`. |

---

## Verification and release decision

**Stage 4 Pre-Release Cross-Layer Security & Contract Sign-Off (`PASS`).** Both platform profiles passed static checking. All 20 GRAB sources matched canonical formatter output byte for byte and all 20 templates passed the release checks. The profile, author and commerce DOM audits passed with zero wrapper divs and zero innerHTML writes. The audits exercised 40, 12 and 21 contrast pairs respectively.

All seven Python suites passed, including the 20-way checkout and 10-way author import concurrency gates. Sign-off covers the four-role profile routes, cookie authentication, CSRF, account-scoped data, password updates and sibling session revocation, existing MCP contracts, migrations and commerce protections. A signed-in browser check exercised profile and security navigation in both modes.
