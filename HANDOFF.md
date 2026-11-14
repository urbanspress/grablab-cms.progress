# GrabLab CMS — Tandem Ownership & Handoff Log

**Current Owner:** Google Antigravity  
**Last Completed Milestone:** `v0.3.0` — Users, Roles/Capabilities, Auth, Optional OAuth2/PKCE & Grex Admin Dashboard (`Complete`)  
**Next Milestone:** `v0.4.0` — Media Library, Navigation Menus, Taxonomies & `grab mcp` CMS Tools (`Approved target; specification in review`)  
**Specification Status:** `specifications/GRABLAB-SPEC-001.md`, `specifications/GRABLAB-SPEC-002.md`, and `specifications/GRABLAB-SPEC-003.md` complete; `specifications/GRABLAB-SPEC-004.md` drafted and awaiting owner approval.

---

## Pending Tasks
1. **Milestone `v0.4.0` Spec-First Gate:** Owner review and approval of `specifications/GRABLAB-SPEC-004.md` before starting `v0.4.0` implementation.

---

## Handoff History
- **2026-11-14 (`v0.3.0` Complete):** Implemented idempotent `002_auth_schema*.grab` migrations (SQLite, PostgreSQL, MariaDB), native `use crypto` (`argon2id`, `random_urlsafe`, `sha256_hex`, `AES-256-GCM` `encrypt_aead`/`decrypt_aead`), `use env` (`--allow-env`), `cache.limit` brute-force blocking, RBAC (`admin`, `editor`, `author`, `viewer`), CSRF (`X-CSRF-Token`), disabled-by-default OAuth2/PKCE (`S256` + `state`), semantic Grex JS `v1.0.0` Admin Dashboard (`--allow-scripts`, zero wrapper-`<div>` tags), and 1-click exclusive theme switching; verified 100% pass across `grab check`, `grab format`, and `tests/integration_test.py`, and generated `docs/releases/pdf/GrabLab-v0.3.0-Guide.pdf`.
- **2026-11-13 (`v0.2.0` Complete):** Implemented Exclusive Theme Engine (`mode: "coded"` and `mode: "visual"` Grex contract), safe directory & package validation (`GRAB-E401`), reusable template parts (`header`, `footer`, `card`, `sidebar`) with zero wrapper-`<div>` bloat, priority-ordered zero-plugin native hooks & filters, and prepared-SQL `query_entries` + `use cache` epoch invalidation; verified 100% pass across `grab check`, `grab format`, and `tests/integration_test.py`, and generated `docs/releases/pdf/GrabLab-v0.2.0-Guide.pdf`.
- **2026-11-13 (`v0.1.0` Complete):** Implemented pure `.grab` and `.grab.html` modules (`migrations/`, `src/app.grab`, `themes/default-starter/`, `public/grex/`), verified 100% pass across `grab check`, `grab format`, and `tests/integration_test.py`, and generated `docs/releases/pdf/GRABLAB-v0.1.0-Guide.pdf`.
- **2026-11-13:** Repository bootstrapped by Google Antigravity with `GRABLAB-EXPERT.md`, `AGENTS.md`, `docs/ROADMAP.md`, `specifications/GRABLAB-SPEC-001.md`, `README.md`, and `LICENSE`.
