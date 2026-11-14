# GRABLAB-EXPERT.md — Non-Negotiable Invariants Checklist

**Scope:** `grablab-cms` (`urbanspress/grablab-cms`) — Step 2 of the GRAB Post-1.0 Ecosystem.  
**Platform Runtimes (Already Unlocked):**
- **GRAB `v1.0.1`** (`grab` CLI, `Grisp` persistent multi-worker server, `use data`, `use cache`, `server.asset`, `grab mcp`)
- **Grex JS `v1.0.0`** (`grex.elements.json`, `createTheme`, `createClassManager`, `ForEach`, `useQuery`)

Never touch or duplicate core Go compiler internals or `grex-js` source code inside this repository. All CMS features live in native `.grab`, `.grab.html`, SQL migrations, and static/runtime assets.

---

## 1. Zero-Plugin Core Architecture
- **No third-party plugin system:** GrabLab CMS MUST NEVER include a plugin loader, arbitrary code-eval hook, or runtime monkey-patching registry.
- **All CMS capabilities live in core `.grab` modules:** Content types, custom fields, SEO/pretty permalinks, 301 redirect history, media library, roles/capabilities, navigation menus, native hooks/filters, and query loops are first-class core modules.
- **No mystery shortcodes:** Content renders from structured fields, sanitized HTML/rich-text, or validated `grex.elements.json` trees—never unescaped inline scripts or arbitrary code evaluation.

## 2. Exclusive Active Theme Ownership & Safe Theme Import
- **Single Active Theme Invariant:** Exactly **one** theme is active at any time (stored atomically in site settings + `use cache`).
- **Automatic Deactivation on Switch:** Activating any theme—whether a coded `.grab`/`.grab.html` theme or the installable **Grex Builder** visual theme (`grex-builder`)—MUST atomically deactivate the previous theme and hand **100% exclusive template rendering control** (`home`, `single`, `archive`, `header`, `footer`, `404`, `search`) to the newly active theme.
- **No Theme Fighting:** Inactive themes have zero active routes, zero injected stylesheets, and zero active hooks.
- **Safe Theme Import (`themes/<slug>/theme.json`):**
  - Theme ZIP/directory imports MUST validate `theme.json` strictly before registration.
  - Reject path traversal (`..`, symlinks escaping theme root, backslashes), sensitive paths (`.git`, `.env`, `.ssh`, `*.pem`, `*.key`), oversized files, and unauthorized capabilities (`GRAB-E401`).
  - Themes are data + `.grab.html` templates + static assets (`/static/themes/<slug>/...` via `server.asset`)—never arbitrary native binaries or unverified OS commands.

## 3. GRAB 1.0 Security, Precision & Runtime Rules
- **Exact Numeric Integrity:** All prices, counts, weights, and sort orders use GRAB `integer` (`GrabInteger`) and exact base-10 `decimal` (`GrabDecimal`) stored as SQLite `TEXT` or MariaDB/PostgreSQL `DECIMAL`/`NUMERIC`. Never coerce currency or IDs to binary64 `float`.
- **Mandatory Prepared SQL (`use data`):** Every database query uses literal prepared SQL with parameterized bindings. Never concatenate user input, slugs, or table names into raw SQL strings.
- **Cache Invalidation (`use cache`):** Content publishes, slug edits, menu updates, and theme switches MUST deterministically invalidate affected cache keys across workers.
- **CSRF & XSS Guards:**
  - All state-changing admin/auth POST/PUT/DELETE routes MUST verify a per-session CSRF token and enforce role/capability checks.
  - All HTML output in `.grab.html` relies on GRAB's context-aware escaping; Grex JS elements enforce `securityRules` (`no-wrapper-div`, `csp-safe`, no `eval`/`innerHTML`).
- **`--read-only` Container Compatibility:** Static assets and uploaded media/theme mounts stay strictly under configured writable volume paths; core code and `PreparedApp` never write temp files to the root filesystem (`server.asset` hashes in memory).
- **Pretty Permalinks & 301 History:** Reserved system prefixes (`/admin`, `/api`, `/static`, `/_health`, `/_ready`) MUST be protected from slug collisions. Changing a published item's slug records the old slug in `slug_history` and serves an automatic `301 Moved Permanently` to the new canonical URL.
