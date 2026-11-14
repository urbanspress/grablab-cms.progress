# GrabLab CMS — Tandem Ownership & Handoff Log

**Current Owner:** Google Antigravity  
**Active Milestone:** `v0.1.0` — Core Content Types, Custom Fields, Pretty Permalinks & 301 Slug History  
**Specification Status:** `specifications/GRABLAB-SPEC-001.md` drafted; awaiting project owner approval before writing application code.

---

## Pending Tasks
1. **Owner Review:** Review and approve `specifications/GRABLAB-SPEC-001.md`.
2. **Upon Approval (`v0.1.0` Implementation):**
   - Implement SQLite-first (MariaDB/PostgreSQL-compatible) `use data` schema & migrations (`sites`, `content_types`, `field_definitions`, `entries`, `slug_history`, `themes`).
   - Implement Content Type & Custom Field registry + validation.
   - Implement `/:slug` pretty permalink router, reserved-prefix protection, and automatic `301 Moved Permanently` redirect history.
   - Implement `theme.json` exclusive theme manifest validator & single-active-theme switcher contract.
   - Write full `grab check` + HTTP integration test suite and generate `v0.1.0` plain-English walkthrough guide.

---

## Handoff History
- **2026-11-13:** Repository bootstrapped by Google Antigravity with `GRABLAB-EXPERT.md`, `AGENTS.md`, `docs/ROADMAP.md`, `specifications/GRABLAB-SPEC-001.md`, `README.md`, and `LICENSE`.
