# GrabLab CMS — Tandem Ownership & Handoff Log

**Current Owner:** Google Antigravity  
**Last Completed Milestone:** `v0.4.0` — Media Library, Navigation Menus, Taxonomies & `grab mcp` CMS Tools (`Complete`)  
**Next Milestone:** `v1.0.0` — Production CMS Release (`Planned`)  
**Specification Status:** `specifications/GRABLAB-SPEC-001.md` (`v0.1.0`), `specifications/GRABLAB-SPEC-002.md` (`v0.2.0`), `specifications/GRABLAB-SPEC-003.md` (`v0.3.0`), and `specifications/GRABLAB-SPEC-004.md` (`v0.4.0`) complete.

---

## Pending Tasks
1. **Milestone `v1.0.0` Spec-First Gate:** Draft and review `specifications/GRABLAB-SPEC-005.md` (multi-worker Grisp, Redis `use cache`, PostgreSQL/MariaDB parity runs, full security audit, and `grabtaculous` packaging) when requested by the project owner.

---

## Handoff History
- **2026-11-14 (`v0.4.0` Complete):** Implemented idempotent `003_v04_schema*.grab` migrations (SQLite, PostgreSQL, MariaDB) and seeds (`category`, `post_tag`, `Uncategorized`, `main-nav`), Media Library safe upload pipeline (`crypto.random_hex` isolated storage under `--allow-write uploads`, magic-byte sniffing + PNG/JPEG/WebP/GIF pixel dimensions, SVG/HTML/executable & traversal rejection, mandatory `alt_text`/`is_decorative` `422` gate, `X-Content-Type-Options: nosniff` + `CSP: default-src 'none'` + immutable `ETag`), Navigation Menus builder (atomic `primary`/`footer`/`mobile` slot assignment, depth<=4 & cycle checks, dynamic entry permalink resolution on slug rename, keyboard + drag-and-drop Grex Admin UI, zero-wrapper-`<div>` `<nav><ul><li><a>`), hierarchical & flat Taxonomies/Terms with reserved-prefix `409` protection, `query_entries` `filter_by_term` + epoch cache invalidation + `/category/:slug`, `/tag/:slug`, `/<archive_slug>/:slug` archives, and capability-gated `grab mcp` CMS tools (`list_content_types`, `query_entries`, `create_entry_draft`, `update_entry_layout` with `grex.elements.json` & WCAG AA `422` checks, `list_media`, `list_menus`); verified 100% pass across `grab check`, `grab format`, and `tests/integration_test.py`, and generated `docs/releases/pdf/GrabLab-v0.4.0-Guide.pdf`.
- **2026-11-14 (`v0.3.0` Complete):** Implemented idempotent `002_auth_schema*.grab` migrations (SQLite, PostgreSQL, MariaDB), native `use crypto` (`argon2id`, `random_urlsafe`, `sha256_hex`, `AES-256-GCM` `encrypt_aead`/`decrypt_aead`), `use env` (`--allow-env`), `cache.limit` brute-force blocking, RBAC (`admin`, `editor`, `author`, `viewer`), CSRF (`X-CSRF-Token`), disabled-by-default OAuth2/PKCE (`S256` + `state`), semantic Grex JS `v1.0.0` Admin Dashboard (`--allow-scripts`, zero wrapper-`<div>` tags), and 1-click exclusive theme switching; verified 100% pass across `grab check`, `grab format`, and `tests/integration_test.py`, and generated `docs/releases/pdf/GrabLab-v0.3.0-Guide.pdf`.
- **2026-11-13 (`v0.2.0` Complete):** Implemented Exclusive Theme Engine (`mode: "coded"` and `mode: "visual"` Grex contract), safe directory & package validation (`GRAB-E401`), reusable template parts (`header`, `footer`, `card`, `sidebar`) with zero wrapper-`<div>` bloat, priority-ordered zero-plugin native hooks & filters, and prepared-SQL `query_entries` + `use cache` epoch invalidation; verified 100% pass across `grab check`, `grab format`, and `tests/integration_test.py`, and generated `docs/releases/pdf/GrabLab-v0.2.0-Guide.pdf`.
- **2026-11-13 (`v0.1.0` Complete):** Implemented pure `.grab` and `.grab.html` modules (`migrations/`, `src/app.grab`, `themes/default-starter/`, `public/grex/`), verified 100% pass across `grab check`, `grab format`, and `tests/integration_test.py`, and generated `docs/releases/pdf/GRABLAB-v0.1.0-Guide.pdf`.
- **2026-11-13:** Repository bootstrapped by Google Antigravity with `GRABLAB-EXPERT.md`, `AGENTS.md`, `docs/ROADMAP.md`, `specifications/GRABLAB-SPEC-001.md`, `README.md`, and `LICENSE`.
