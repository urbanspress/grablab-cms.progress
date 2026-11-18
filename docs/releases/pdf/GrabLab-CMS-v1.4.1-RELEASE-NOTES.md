# GrabLab CMS `v1.4.1` — PostgreSQL 18 Taxonomy Query Compatibility Patch

### Release Type & Affected Layers
- **Release Version & SemVer Tier:** `v1.4.1` (`PATCH 1.4.x — Non-Breaking Bug/Compatibility Patch`)
- **Affected Layer(s):** `Flagship Zero-Plugin CMS` (`urbanspress/grablab-cms`)
- **Neighboring Layer Upgrade Required?** `No — 100% drop-in compatible` with frozen GRAB `v1.1.0`, Grex JS `v1.0.0`, Grex Theme Builder `v1.0.0`, and Groxy AI (`>= v0.1.0`)

| Ecosystem Layer | Repository | Required Version Range | Touched in This Release? | Neighbor Upgrade Required? |
|---|---|---|---|---|
| **Core Language, Bytecode VM & Grisp Server** | `urbanspress/grab` | `>= v1.1.0 (< v2.0.0)` | `No` | `No` |
| **Reactive Frontend Runtime & 20-Element Library** | `urbanspress/grex-js` | `>= v1.0.0 (< v2.0.0)` | `No` | `No` |
| **Flagship Zero-Plugin CMS** | `urbanspress/grablab-cms` | `>= v1.4.1 (< v2.0.0)` | `Yes` (`src/app.grab`, `tests/release_v140_test.py`) | `No` |
| **Exclusive `mode: "visual"` Theme & Studio** | `urbanspress/grex-builder` | `>= v1.0.0 (< v2.0.0)` | `No` | `No` |
| **Autonomous Design, Content & SEO Agent** | `urbanspress/groxy-ai` | `>= v0.1.0` | `No` | `No` |

---

## Summary of Fix

- **PostgreSQL 18 Strict `DISTINCT` + `ORDER BY COALESCE(...)` Compatibility (`src/app.grab`):**
  - Updated `stmt_query_entries_by_term` to filter via `WHERE EXISTS (SELECT 1 FROM entry_terms et WHERE et.entry_id = e.id AND et.term_id IN (:t0, ..., :t15))` instead of `SELECT DISTINCT ... INNER JOIN entry_terms ... ORDER BY COALESCE(e.published_at, e.created_at) DESC, e.id DESC`.
  - Eliminates PostgreSQL 18's `ORDER BY expressions must appear in select list` failure on taxonomy archives and filtered queries while preserving multi-term parent/child deduplication across SQLite, MariaDB, and PostgreSQL 18 with zero database schema changes.
- **Regression Verification (`tests/release_v140_test.py`):**
  - Added automated checks asserting the `EXISTS (...)` prepared SQL query structure and verifying that entries tagged under multiple matching terms (`pg18-parent` + `pg18-child`) are returned once.

## Verification & Bundle Checksums

- **Full Automated Verification (`PASS`):** `grab check` (`grab.platform.json` + `deploy/grab.platform.commerce.json`), canonical `grab format --write src/app.grab`, `tests/integration_test.py`, `tests/release_v100_test.py`, `tests/commerce_test.py`, `tests/release_v110_test.py`, `tests/author_test.py`, `tests/release_v140_test.py`, `node tests/author_dom_audit.mjs`, and `node tests/commerce_dom_audit.mjs`.
- **Walkthrough PDF:** `docs/releases/pdf/GrabLab-CMS-v1.4.1-Guide.pdf`
- **Release Bundle:** `dist/grablab-cms-v1.4.1-bundle.zip` (SHA-256 recorded in `dist/SHA256SUMS.txt`)
