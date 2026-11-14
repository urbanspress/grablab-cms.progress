#!/usr/bin/env python3
"""
GrabLab CMS v0.4.0 Comprehensive Integration Test Suite
Tests:
1. grab check & grab format parity on all .grab and .grab.html files (including admin Grex views)
2. Database schema v0.1 -> v0.3 -> v0.4 upgrade & fresh migration idempotency + v0.4 seed (SQLite/MariaDB/Postgres parity)
3. Initial /setup lock, native argon2id auth, HttpOnly SameSite=Lax cookies, session rotation & logout
4. Brute-force protection via use cache (cache.limit -> 429 Too Many Requests + epoch reset)
5. CSRF protection (X-CSRF-Token) & RBAC enforcement (admin, editor, author, viewer)
6. Optional Built-In OAuth2/PKCE social login (disabled by default, AES-256-GCM encryption via
   GRABLAB_MASTER_KEY, S256 PKCE + state nonce, verified-email linking, strict allowlists)
7. Content type registration, 8 typed custom fields, GrabDecimal string fidelity, Grex layout checks
8. Pretty permalink resolution, 301 redirects & loop-free slug revert, XSS escaping, CSP headers
9. 1-click exclusive theme switching (/api/admin/themes/activate), Grex visual mode, zero-<div> HTML
10. Native hooks/filters priority ordering & Query Loop cache invalidation
11. v0.4.0 Media Library & Safe Upload Pipeline (magic-byte sniffing, SVG/HTML rejection, path traversal, dimensions, WCAG alt, hardening headers)
12. v0.4.0 Navigation Menus (atomic slot assignment, depth<=4/cycle check, URL allowlist, auto permalink resolution, semantic <nav>)
13. v0.4.0 Taxonomies, Hierarchical Terms, Query Loop filter_by_term & pretty archive routes (/category/:slug, /tag/:slug, /:archive/:slug)
14. v0.4.0 Capability-gated grab mcp CMS tools (JSON-RPC & REST, draft-only create_entry_draft, Grex + auditAccessibility 422 gate, zero secrets)
"""

import base64
import hashlib
import http.client
import http.server
import json
import os
import shutil
import socket
import sqlite3
import struct
import subprocess
import tempfile
import threading
import time
import urllib.parse
import zlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_GRAB = (
    r"C:\Program Files\GRAB\grab.exe"
    if os.path.exists(r"C:\Program Files\GRAB\grab.exe")
    else r"C:\Development\GRAB\dist\grab-windows-amd64.exe"
)
GRAB_BIN = os.environ.get("GRAB_BIN", DEFAULT_GRAB)
DB_PATH = os.path.join(ROOT, "storage", "grablab.db")
TEST_MASTER_KEY = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


def run_cmd(args, cwd=ROOT, check=True, env=None):
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    res = subprocess.run(
        [GRAB_BIN] + args,
        cwd=cwd,
        env=merged_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and res.returncode != 0:
        raise AssertionError(
            f"Command failed ({res.returncode}): grab {' '.join(args)}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )
    return res


def pick_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def http_req(port, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    hdrs = dict(headers or {})
    payload = None
    if body is not None:
        if isinstance(body, (dict, list)):
            payload = json.dumps(body).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")
        else:
            payload = body.encode("utf-8") if isinstance(body, str) else body
    conn.request(method, path, body=payload, headers=hdrs)
    resp = conn.getresponse()
    raw = resp.read().decode("utf-8", errors="replace")
    resp_headers = {k.lower(): v for k, v in resp.getheaders()}
    set_cookies = resp.headers.get_all("Set-Cookie") or []
    conn.close()
    parsed = None
    if "application/json" in resp_headers.get("content-type", ""):
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = None
    return resp.status, resp_headers, set_cookies, raw, parsed


def extract_cookie_pair(set_cookies, name):
    for sc in set_cookies:
        first = sc.split(";", 1)[0].strip()
        if first.startswith(name + "="):
            return first
    return ""


class SessionClient:
    def __init__(self, port):
        self.port = port
        self.cookie = ""
        self.csrf_token = ""

    def request(self, method, path, body=None, extra_headers=None, send_csrf=True, use_cookie=True):
        hdrs = dict(extra_headers or {})
        if use_cookie and self.cookie:
            hdrs.setdefault("Cookie", self.cookie)
        if send_csrf and self.csrf_token and method in ("POST", "PUT", "PATCH", "DELETE"):
            hdrs.setdefault("X-CSRF-Token", self.csrf_token)
        return http_req(self.port, method, path, body=body, headers=hdrs)

    def apply_login_result(self, set_cookies, js):
        pair = extract_cookie_pair(set_cookies, "grablab_session")
        if pair:
            self.cookie = pair
        if js and "csrf_token" in js:
            self.csrf_token = js["csrf_token"]


class MockOAuthState:
    def __init__(self):
        self.hits = 0
        self.challenges = {}
        self.tokens = {}
        self.next_profile = {
            "sub": "google-uid-42",
            "email": "editor@example.com",
            "email_verified": True,
            "name": "OAuth Editor",
        }


def start_mock_oauth_server():
    state = MockOAuthState()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def do_POST(self):
            state.hits += 1
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            params = urllib.parse.parse_qs(raw)
            if self.path == "/google/token":
                code = params.get("code", [""])[0]
                verifier = params.get("code_verifier", [""])[0]
                secret = params.get("client_secret", [""])[0]
                expected_challenge = state.challenges.get(code, "")
                computed = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("utf-8")).digest()).decode("ascii").rstrip("=")
                if not expected_challenge or computed != expected_challenge or secret != "super-secret-value-1234":
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "invalid_grant"}).encode("utf-8"))
                    return
                tok = f"mock-access-{code}"
                state.tokens[tok] = dict(state.next_profile)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"access_token": tok, "token_type": "Bearer"}).encode("utf-8"))
                return
            self.send_response(404)
            self.end_headers()

        def do_GET(self):
            state.hits += 1
            if self.path == "/google/userinfo":
                auth = self.headers.get("Authorization", "")
                tok = auth.replace("Bearer ", "").strip()
                prof = state.tokens.get(tok)
                if not prof:
                    self.send_response(401)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(prof).encode("utf-8"))
                return
            self.send_response(404)
            self.end_headers()

    port = pick_free_port()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return port, srv, state


def test_checks_and_formatting():
    print("[1/13] Running grab check and grab format verification...")
    grab_files = [
        "migrations/001_schema.grab",
        "migrations/001_schema_postgres.grab",
        "migrations/001_schema_mariadb.grab",
        "migrations/002_auth_schema.grab",
        "migrations/002_auth_schema_postgres.grab",
        "migrations/002_auth_schema_mariadb.grab",
        "migrations/003_v04_schema.grab",
        "migrations/003_v04_schema_postgres.grab",
        "migrations/003_v04_schema_mariadb.grab",
        "migrations/seed.grab",
    ]
    for gf in grab_files:
        run_cmd(["check", "--platform-config", "grab.platform.json", gf])
        fmt = run_cmd(["format", gf])
        with open(os.path.join(ROOT, gf), "r", encoding="utf-8") as f:
            actual = f.read()
        assert fmt.stdout == actual, f"{gf} is not canonically formatted"

    run_cmd(["check", "--platform-config", "grab.platform.json", "src/app.grab"])
    fmt_app = run_cmd(["format", "src/app.grab"])
    with open(os.path.join(ROOT, "src", "app.grab"), "r", encoding="utf-8") as f:
        assert fmt_app.stdout == f.read(), "src/app.grab is not canonically formatted"

    tmp_dir = os.path.join(ROOT, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    try:
        templates = [
            ("themes/default-starter/templates/home.grab.html", 'record {site_title: "T", page_title: "H", meta_description: "D", tokens_css_url: "/s", theme_css_url: "/t", theme_name: "N", site_tagline: "G", published_count: "0", entries_summary: "E", theme_slug: "default-starter"}'),
            ("themes/default-starter/templates/single.grab.html", 'record {site_title: "T", meta_title: "M", meta_description: "D", tokens_css_url: "/s", theme_css_url: "/t", content_type_label: "Page", title: "Ti", full_path: "/about", published_at: "2026-01-01", body_text: "B", custom_fields_summary: "{}", theme_slug: "default-starter"}'),
            ("themes/default-starter/templates/archive.grab.html", 'record {site_title: "T", archive_label: "Posts", meta_description: "D", tokens_css_url: "/s", theme_css_url: "/t", entry_count: "1", archive_slug: "blog", entries_summary: "E", theme_slug: "default-starter"}'),
            ("themes/default-starter/templates/404.grab.html", 'record {site_title: "T", tokens_css_url: "/s", theme_css_url: "/t", requested_path: "/x", theme_slug: "default-starter"}'),
            ("themes/default-starter/templates/search.grab.html", 'record {site_title: "T", tokens_css_url: "/s", theme_css_url: "/t", query: "q", results_summary: "R", theme_slug: "default-starter"}'),
            ("themes/default-starter/templates/parts/header.grab.html", 'record {site_title: "T"}'),
            ("themes/default-starter/templates/parts/footer.grab.html", 'record {theme_slug: "default-starter"}'),
            ("themes/default-starter/templates/parts/card.grab.html", 'record {content_type_label: "Post", full_path: "/blog/hello", title: "Hello", published_at: "2026-11-13", excerpt: "Hi"}'),
            ("themes/default-starter/templates/parts/sidebar.grab.html", 'record {site_title: "T", site_tagline: "G", published_count: "2", theme_name: "Default Starter"}'),
            ("src/views/admin/login.grab.html", 'record {site_title: "T", tokens_css_url: "/s", admin_css_url: "/c", grex_js_url: "/g", admin_js_url: "/a"}'),
            ("src/views/admin/setup.grab.html", 'record {site_title: "T", tokens_css_url: "/s", admin_css_url: "/c", grex_js_url: "/g", admin_js_url: "/a"}'),
            ("src/views/admin/dashboard.grab.html", 'record {csrf_token: "x", admin_page: "overview", user_role: "admin", user_email: "a@b.c", user_name: "A", user_id: "1", site_title: "T", active_theme_slug: "default-starter", page_title: "D", page_subtitle: "S", tokens_css_url: "/s", admin_css_url: "/c", grex_js_url: "/g", admin_js_url: "/a"}'),
        ]
        probe = os.path.join(tmp_dir, "tmpl_check.grab")
        for rel_tmpl, data_expr in templates:
            with open(os.path.join(ROOT, rel_tmpl), "r", encoding="utf-8") as tf:
                assert "<div" not in tf.read().lower(), f"Wrapper <div> prohibited in {rel_tmpl}"
            with open(probe, "w", encoding="utf-8") as f:
                f.write(
                    'use server\nroute "GET" "/"\n'
                    f'  give back server.html using "../{rel_tmpl}", {data_expr}\n'
                    "end\n"
                )
            run_cmd(["check", "tmp/tmpl_check.grab"])
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    print("  OK: All .grab and .grab.html files passed grab check, canonical format, and zero-<div> check.")


def test_migrations_and_seed():
    print("[2/13] Testing v0.1->v0.3->v0.4 upgrade migration, fresh v0.4 migration, dialect parity, and idempotent seed...")
    for suffix in ("", "-journal", "-wal", "-shm"):
        p = DB_PATH + suffix
        if os.path.exists(p):
            os.remove(p)

    # Clean uploads dir before baseline
    up_dir = os.path.join(ROOT, "uploads")
    os.makedirs(up_dir, exist_ok=True)
    for fn in os.listdir(up_dir):
        if fn != ".gitkeep":
            fp = os.path.join(up_dir, fn)
            if os.path.isfile(fp):
                os.remove(fp)

    # 1) Upgrade path: v0.1 -> v0.3 -> v0.4
    m1 = run_cmd(["migrate", "--db-config", "grab.data.json", "--allow-db", "main:migrate", "migrations/001_schema.grab"])
    assert "applied: [1]" in m1.stdout, f"Expected v0.1 applied: {m1.stdout}"
    m2 = run_cmd(["migrate", "--db-config", "grab.data.json", "--allow-db", "main:migrate", "migrations/002_auth_schema.grab"])
    assert "applied: [2]" in m2.stdout, f"Expected v0.3 upgrade [2] applied: {m2.stdout}"
    m3 = run_cmd(["migrate", "--db-config", "grab.data.json", "--allow-db", "main:migrate", "migrations/003_v04_schema.grab"])
    assert "applied: [3]" in m3.stdout, f"Expected v0.4 upgrade [3] applied: {m3.stdout}"
    m4 = run_cmd(["migrate", "--db-config", "grab.data.json", "--allow-db", "main:migrate", "migrations/003_v04_schema.grab"])
    assert "applied: []" in m4.stdout, f"Expected idempotent v0.4 run: {m4.stdout}"

    # 2) Fresh install path in isolated temp db
    fresh_dir = os.path.join(ROOT, "storage", "_fresh_test")
    os.makedirs(fresh_dir, exist_ok=True)
    try:
        cfg_path = os.path.join(fresh_dir, "data.json")
        with open(cfg_path, "w", encoding="utf-8") as cf:
            json.dump({"connections": {"main": {"driver": "sqlite", "path": "fresh.db"}}}, cf)
        mf = run_cmd(["migrate", "--db-config", cfg_path, "--allow-db", "main:migrate", "migrations/003_v04_schema.grab"])
        assert "applied: [1, 2, 3]" in mf.stdout, f"Expected fresh [1, 2, 3] applied: {mf.stdout}"
    finally:
        shutil.rmtree(fresh_dir, ignore_errors=True)

    # 3) Schema parity check across MariaDB and PostgreSQL v0.4 migration files
    for fname in ("migrations/003_v04_schema_mariadb.grab", "migrations/003_v04_schema_postgres.grab"):
        txt = open(os.path.join(ROOT, fname), encoding="utf-8").read()
        for tbl in ("media", "menus", "menu_items", "taxonomies", "terms", "entry_terms"):
            assert f"CREATE TABLE IF NOT EXISTS {tbl}" in txt, f"Missing {tbl} in {fname}"

    # 4) Seed main DB twice (idempotent) & verify v0.4 defaults
    s1 = run_cmd(["run", "--db-config", "grab.data.json", "--allow-db", "main:read-write", "--allow-read", ".", "migrations/seed.grab"])
    assert "seed completed" in s1.stdout
    s2 = run_cmd(["run", "--db-config", "grab.data.json", "--allow-db", "main:read-write", "--allow-read", ".", "migrations/seed.grab"])
    assert "seed completed" in s2.stdout

    con = sqlite3.connect(DB_PATH)
    tax_slugs = {r[0] for r in con.execute("SELECT slug FROM taxonomies").fetchall()}
    assert {"category", "post_tag"}.issubset(tax_slugs), f"Missing built-in taxonomies: {tax_slugs}"
    term_slugs = {r[0] for r in con.execute("SELECT slug FROM terms").fetchall()}
    assert "uncategorized" in term_slugs
    menu_rows = con.execute("SELECT slug, location FROM menus").fetchall()
    assert ("main-nav", "primary") in menu_rows
    con.close()
    print("  OK: Upgrade & fresh v0.4 migrations, MariaDB/PostgreSQL parity, and seed verified.")


def start_server(port, oauth_port, upload_dir=None, max_upload_bytes=None):
    log_path = os.path.join(ROOT, "storage", "test_server.log")
    log_file = open(log_path, "w", encoding="utf-8")
    env = os.environ.copy()
    env["GRABLAB_MASTER_KEY"] = TEST_MASTER_KEY
    env["GRABLAB_OAUTH_TEST_BASE_URL"] = f"http://127.0.0.1:{oauth_port}"
    write_dir = upload_dir or "uploads"
    if upload_dir:
        env["GRABLAB_UPLOAD_DIR"] = upload_dir
    if max_upload_bytes is not None:
        env["GRABLAB_MAX_UPLOAD_BYTES"] = str(max_upload_bytes)
    proc = subprocess.Popen(
        [
            GRAB_BIN,
            "serve",
            "--addr",
            f"127.0.0.1:{port}",
            "--allow-scripts",
            "--max-body-bytes",
            "15728640",
            "--db-config",
            "grab.data.json",
            "--allow-db",
            "main:read-write",
            "--platform-config",
            "grab.platform.json",
            "--allow-cache",
            "cms:read-write",
            "--allow-cache",
            "cms:limit",
            "--allow-env",
            "GRABLAB_MASTER_KEY,GRABLAB_OAUTH_TEST_BASE_URL,GRABLAB_UPLOAD_DIR,GRABLAB_MAX_UPLOAD_BYTES",
            "--allow-net",
            f"127.0.0.1:{oauth_port}",
            "--allow-read",
            ".",
            "--allow-write",
            write_dir,
            "--static",
            "public",
            "src/app.grab",
        ],
        cwd=ROOT,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    deadline = time.time() + 15
    while time.time() < deadline:
        if proc.poll() is not None:
            log_file.close()
            with open(log_path, "r", encoding="utf-8", errors="replace") as lf:
                raise AssertionError(f"Server exited early ({proc.returncode}):\n{lf.read()}")
        try:
            st, _, _, _, js = http_req(port, "GET", "/_health")
            if st == 200 and js and js.get("status") == "ok":
                return proc, log_file, log_path
        except Exception:
            time.sleep(0.15)
    proc.terminate()
    log_file.close()
    raise AssertionError("Timed out waiting for GrabLab CMS server /_health")


def run_http_tests(port, oauth_port, oauth_state):
    print("[3/10] Testing health probes, CSP (--allow-scripts), Grex admin assets, and first-run /setup lock...")
    st, hdrs, _, _, js = http_req(port, "GET", "/_ready")
    assert st == 200 and js["status"] == "ready"
    csp = hdrs.get("content-security-policy", "")
    assert "script-src 'self'" in csp, f"Expected --allow-scripts CSP header, got: {csp!r}"

    st, _, _, raw, _ = http_req(port, "GET", "/static/grex/grex.js")
    assert st == 200 and len(raw) > 10000
    st, _, _, raw, _ = http_req(port, "GET", "/static/admin/admin.js")
    assert st == 200 and "createGrabClient" in raw
    st, _, _, raw, _ = http_req(port, "GET", "/static/admin/admin.css")
    assert st == 200 and ".cms-admin-shell" in raw or ".cms-admin-topbar" in raw

    # Before first user exists, /admin and /login redirect to /setup
    st, hdrs, _, _, _ = http_req(port, "GET", "/admin")
    assert st == 302 and hdrs.get("location") == "/setup"
    st, hdrs, _, _, _ = http_req(port, "GET", "/login")
    assert st == 302 and hdrs.get("location") == "/setup"

    st, hdrs, _, html, _ = http_req(port, "GET", "/setup")
    assert st == 200 and "Create Primary Administrator" in html and "<div" not in html.lower()
    assert "no-store" in hdrs.get("cache-control", "")

    # Public routes & Grex CSS tokens still render cleanly with zero-<div>
    st, _, _, html, _ = http_req(port, "GET", "/")
    assert st == 200 and '<meta name="generator" content="GrabLab CMS v1.0.0 (default-starter)">' in html and "<div" not in html.lower()

    # Complete initial setup
    admin = SessionClient(port)
    st, hdrs, cookies, _, js = http_req(port, "POST", "/api/auth/setup", {
        "email": "admin@example.com",
        "display_name": "Site Owner",
        "password": "StrongAdminPassword!123",
    })
    assert st == 201 and js["user"]["role"] == "admin" and js.get("csrf_token"), f"Setup failed: {st} {js}"
    raw_sc = "; ".join(cookies)
    assert "HttpOnly" in raw_sc and "SameSite=Lax" in raw_sc, f"Missing HttpOnly/SameSite=Lax: {raw_sc}"
    admin.apply_login_result(cookies, js)

    # Verify argon2id password hash stored in SQLite (never plaintext)
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT password_hash FROM users WHERE email = ?", ("admin@example.com",)).fetchone()
    assert row and row[0].startswith("$argon2id$"), f"Expected $argon2id$ hash, got {row}"
    con.close()

    # /setup must now lock permanently (POST -> 403, GET -> 302 /login)
    st, _, _, _, js = http_req(port, "POST", "/api/auth/setup", {
        "email": "evil@example.com", "display_name": "Evil", "password": "EvilPassword!123"
    })
    assert st == 403
    st, hdrs, _, _, _ = http_req(port, "GET", "/setup")
    assert st == 302 and hdrs.get("location") == "/login"
    print("  OK: CSP, initial /setup lock, argon2id hashing, and secure cookie flags verified.")

    print("[4/10] Testing session rotation on login, logout revocation, and cache.limit brute-force blocking...")
    # Log in again while sending old cookie -> server MUST issue a new session cookie & invalidate old cookie
    old_cookie = admin.cookie
    st, _, cookies2, _, js2 = http_req(port, "POST", "/api/auth/login", {
        "email": "admin@example.com", "password": "StrongAdminPassword!123"
    }, headers={"Cookie": old_cookie})
    assert st == 200 and js2.get("csrf_token")
    new_cookie = extract_cookie_pair(cookies2, "grablab_session")
    assert new_cookie and new_cookie != old_cookie, "Session token did not rotate on login!"

    # Old cookie must be invalidated (401)
    st, _, _, _, _ = http_req(port, "GET", "/api/auth/session", headers={"Cookie": old_cookie})
    assert st == 401, f"Old session token survived login rotation: {st}"

    # Update admin client to new rotated session
    admin.apply_login_result(cookies2, js2)
    st, _, _, _, sess_js = admin.request("GET", "/api/auth/session")
    assert st == 200 and sess_js["authenticated"] is True and sess_js["user"]["role"] == "admin"

    # Brute-force rate limit test on temporary client/user email (5 failures -> 401, 6th -> 429)
    for i in range(5):
        st, _, _, _, _ = http_req(port, "POST", "/api/auth/login", {
            "email": "bruteforce@example.com", "password": f"WrongPassword_{i}"
        })
        assert st == 401, f"Expected 401 on attempt {i+1}, got {st}"
    st, hdrs, _, _, js_rl = http_req(port, "POST", "/api/auth/login", {
        "email": "bruteforce@example.com", "password": "WrongPassword_6"
    })
    assert st == 429 and hdrs.get("retry-after"), f"Expected 429 Too Many Requests on 6th attempt, got {st} {hdrs} {js_rl}"

    # Verify successful login resets failure epoch counter (3 fails + success + 3 more fails allowed)
    for i in range(3):
        st, _, _, _, _ = http_req(port, "POST", "/api/auth/login", {
            "email": "admin@example.com", "password": f"WrongAdmin_{i}"
        })
        assert st == 401
    st, _, _, _, _ = http_req(port, "POST", "/api/auth/login", {
        "email": "admin@example.com", "password": "StrongAdminPassword!123"
    })
    assert st == 200
    for i in range(3):
        st, _, _, _, _ = http_req(port, "POST", "/api/auth/login", {
            "email": "admin@example.com", "password": f"WrongAdminAfterReset_{i}"
        })
        assert st == 401, f"Expected 401 after rate-limit epoch reset, got {st}"
    st, _, c_res, _, js_res = http_req(port, "POST", "/api/auth/login", {
        "email": "admin@example.com", "password": "StrongAdminPassword!123"
    })
    assert st == 200
    admin.apply_login_result(c_res, js_res)

    # Verify logout clears cookie and revokes session
    temp_cli = SessionClient(port)
    st, _, c_tmp, _, js_tmp = http_req(port, "POST", "/api/auth/login", {
        "email": "admin@example.com", "password": "StrongAdminPassword!123"
    })
    assert st == 200
    temp_cli.apply_login_result(c_tmp, js_tmp)
    st, _, c_out, _, _ = temp_cli.request("POST", "/api/auth/logout", {})
    assert st == 200 and "Max-Age=0" in "; ".join(c_out)
    st, _, _, _, _ = temp_cli.request("GET", "/api/auth/session")
    assert st == 401, "Logged out session still active!"
    print("  OK: Session rotation, logout revocation, and 6th-attempt 429 brute-force block verified.")

    print("[5/10] Testing CSRF rejection & role-based capability enforcement (viewer/author/editor/admin)...")
    # Unauthenticated mutation/admin requests rejected (401)
    for m, p, b in [
        ("POST", "/api/content-types", {"slug": "x", "label_singular": "X", "label_plural": "Xs", "permalink_pattern": "/x/:slug"}),
        ("POST", "/api/entries", {"content_type": "post", "slug": "x", "title": "X"}),
        ("GET", "/api/admin/settings", None),
        ("GET", "/api/redirects", None),
        ("POST", "/api/themes/activate", {"slug": "default-starter"}),
    ]:
        st, _, _, _, _ = http_req(port, m, p, b)
        assert st == 401, f"Expected 401 unauthenticated for {m} {p}, got {st}"

    # Valid admin cookie WITHOUT CSRF or WRONG CSRF -> 403
    st, _, _, _, js = admin.request("POST", "/api/content-types", {
        "slug": "nope", "label_singular": "N", "label_plural": "Ns", "permalink_pattern": "/nope/:slug"
    }, send_csrf=False)
    assert st == 403 and "csrf" in js["error"].lower()
    st, _, _, _, js = admin.request("POST", "/api/content-types", {
        "slug": "nope", "label_singular": "N", "label_plural": "Ns", "permalink_pattern": "/nope/:slug"
    }, extra_headers={"X-CSRF-Token": "wrong-token"}, send_csrf=False)
    assert st == 403 and "csrf" in js["error"].lower()

    # Create editor, author1, author2, viewer
    role_users = [
        ("editor@example.com", "Lead Editor", "editor", "EditorPassword!123"),
        ("author@example.com", "Staff Author", "author", "AuthorPassword!123"),
        ("author2@example.com", "Second Author", "author", "Author2Password!123"),
        ("viewer@example.com", "Reader Viewer", "viewer", "ViewerPassword!123"),
    ]
    for em, nm, rl, pw in role_users:
        st, _, _, _, js = admin.request("POST", "/api/admin/users", {
            "email": em, "display_name": nm, "role": rl, "password": pw
        })
        assert st == 201 and js["user"]["role"] == rl, f"Failed creating user {em}: {st} {js}"
        assert "password_hash" not in js["user"]

    # Ensure GET /api/admin/users omits password_hash
    st, _, _, _, ulist = admin.request("GET", "/api/admin/users")
    assert st == 200 and len(ulist["users"]) == 5
    for u in ulist["users"]:
        assert "password_hash" not in u

    # Login helper
    def login_as(email, password):
        cli = SessionClient(port)
        st_l, _, ck, _, js_l = http_req(port, "POST", "/api/auth/login", {"email": email, "password": password})
        assert st_l == 200, f"Login failed for {email}: {st_l} {js_l}"
        cli.apply_login_result(ck, js_l)
        return cli

    viewer = login_as("viewer@example.com", "ViewerPassword!123")
    author1 = login_as("author@example.com", "AuthorPassword!123")
    author2 = login_as("author2@example.com", "Author2Password!123")
    editor = login_as("editor@example.com", "EditorPassword!123")

    # Viewer cannot access /admin or /api/entries
    st, _, _, _, _ = viewer.request("GET", "/admin")
    assert st == 403
    st, _, _, _, _ = viewer.request("GET", "/api/entries")
    assert st == 403

    # Author: can create own draft, edit own draft, CANNOT publish, CANNOT edit other's draft, CANNOT manage types/settings
    st, _, _, _, js_pub_block = author1.request("POST", "/api/entries", {
        "content_type": "post", "slug": "author-pub-attempt", "title": "Attempt", "status": "published"
    })
    assert st == 403

    st, _, _, _, js_a1 = author1.request("POST", "/api/entries", {
        "content_type": "post", "slug": "author1-draft", "title": "Author 1 Draft", "status": "draft", "body_html": "Draft content"
    })
    assert st == 201 and js_a1["entry"]["status"] == "draft"
    a1_id = js_a1["entry"]["id"]

    st, _, _, _, _ = author1.request("PUT", f"/api/entries/{a1_id}", {"title": "Author 1 Draft Edited"})
    assert st == 200
    st, _, _, _, _ = author2.request("PUT", f"/api/entries/{a1_id}", {"title": "Hijacked"})
    assert st == 403
    st, _, _, _, _ = author2.request("DELETE", f"/api/entries/{a1_id}")
    assert st == 403
    st, _, _, _, _ = author1.request("GET", "/api/admin/settings")
    assert st == 403
    st, _, _, _, _ = author1.request("DELETE", f"/api/entries/{a1_id}")
    assert st == 200

    # Editor: can publish entry, CANNOT access /api/admin/settings or /api/themes/activate or /api/content-types
    st, _, _, _, js_ed = editor.request("POST", "/api/entries", {
        "content_type": "post", "slug": "editor-story", "title": "Editor Story", "status": "published", "body_html": "Published by editor"
    })
    assert st == 201 and js_ed["entry"]["status"] == "published"
    ed_entry_id = js_ed["entry"]["id"]
    st, _, _, _, _ = editor.request("GET", "/api/admin/settings")
    assert st == 403
    st, _, _, _, _ = editor.request("POST", "/api/themes/activate", {"slug": "default-starter"})
    assert st == 403
    st, _, _, _, _ = admin.request("DELETE", f"/api/entries/{ed_entry_id}")
    assert st == 200
    print("  OK: CSRF protection and viewer/author/editor/admin capability enforcement verified.")

    print("[6/13] Verifying authenticated Grex JS v1.0.0 admin dashboard routes (including v0.4 panels)...")
    for adm_path in ("/admin", "/admin/entries", "/admin/media", "/admin/menus", "/admin/taxonomies", "/admin/types", "/admin/themes", "/admin/settings"):
        st, hdrs, _, html, _ = admin.request("GET", adm_path)
        assert st == 200, f"Expected 200 on {adm_path}, got {st}"
        assert "<div" not in html.lower(), f"Prohibited wrapper <div> on {adm_path}"
        assert 'name="grablab-csrf"' in html and "/static/grex/grex.js" in html and "/static/admin/admin.js" in html
        assert "no-store" in hdrs.get("cache-control", "")
    # RBAC checks for v0.4 admin routes
    assert viewer.request("GET", "/admin/media")[0] == 403
    assert author1.request("GET", "/admin/media")[0] == 200
    assert author1.request("GET", "/admin/menus")[0] == 403
    assert author1.request("GET", "/admin/taxonomies")[0] == 403
    assert editor.request("GET", "/admin/menus")[0] == 200
    assert editor.request("GET", "/admin/taxonomies")[0] == 200
    # Unknown admin subpath returns 404 when authenticated
    st, _, _, _, _ = admin.request("GET", "/admin/nonexistent-panel")
    assert st == 404
    print("  OK: Semantic Grex admin routes + v0.4 RBAC verified with zero <div> tags.")

    print("[7/10] Testing disabled-by-default OAuth2/PKCE, AES-256-GCM secrets, & S256 social login flow...")
    # Step A: Disabled by default -> zero social buttons, /start 404, 0 outbound calls
    st, _, _, login_html, _ = http_req(port, "GET", "/login")
    assert st == 200 and "Continue with" not in login_html and "/api/auth/oauth/" not in login_html and "<div" not in login_html.lower()
    st, _, _, _, _ = http_req(port, "GET", "/api/auth/oauth/google/start")
    assert st == 404
    assert oauth_state.hits == 0, f"Unexpected outbound OAuth call while disabled: {oauth_state.hits}"

    # Step B: Configure & enable Google provider via admin API -> encrypted at rest via AES-256-GCM
    st, _, _, _, oauth_save = admin.request("PUT", "/api/admin/settings/oauth", {
        "oauth_allow_signup": False,
        "providers": {
            "google": {
                "enabled": True,
                "client_id": "mock-google-client-id",
                "client_secret": "super-secret-value-1234",
                "allowed_domains": "example.com"
            }
        }
    })
    assert st == 200 and oauth_save["oauth_providers"]["google"]["has_secret"] is True
    assert oauth_save["oauth_providers"]["google"]["secret_hint"] == "****1234"
    assert "super-secret-value-1234" not in json.dumps(oauth_save)

    # Confirm ciphertext prefix v1: in SQLite and zero plaintext leak
    con = sqlite3.connect(DB_PATH)
    raw_oauth_setting = con.execute("SELECT value FROM site_settings WHERE key = 'oauth_providers_json'").fetchone()[0]
    con.close()
    assert "super-secret-value-1234" not in raw_oauth_setting
    assert json.loads(raw_oauth_setting)["google"]["client_secret_enc"].startswith("v1:")

    # /login now shows Google button
    st, _, _, login_html2, _ = http_req(port, "GET", "/login")
    assert st == 200 and "/api/auth/oauth/google/start" in login_html2 and "Continue with Google" in login_html2 and "<div" not in login_html2.lower()

    # Step C: OAuth start -> PKCE S256 & state + tx cookie
    st, hdrs, oauth_cookies, _, _ = http_req(port, "GET", "/api/auth/oauth/google/start")
    assert st == 302
    loc = hdrs.get("location", "")
    assert loc.startswith(f"http://127.0.0.1:{oauth_port}/google/authorize?"), f"Unexpected authorize URL: {loc}"
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query)
    assert qs.get("code_challenge_method") == ["S256"]
    state_val = qs["state"][0]
    challenge_val = qs["code_challenge"][0]
    tx_cookie = extract_cookie_pair(oauth_cookies, "grablab_oauth_tx")
    assert tx_cookie, "Missing grablab_oauth_tx cookie"

    # Bad state or missing cookie -> 403
    st, _, _, raw1, js1 = http_req(port, "GET", f"/api/auth/oauth/google/callback?state=tampered&code=c1", headers={"Cookie": tx_cookie})
    assert st == 403, f"Bad state expected 403, got {st} {raw1} {js1}"
    st, _, _, raw2, js2 = http_req(port, "GET", f"/api/auth/oauth/google/callback?state={state_val}&code=c1")
    assert st == 403, f"Missing cookie expected 403, got {st} {raw2} {js2}"

    # Unverified email -> 403
    oauth_state.challenges["code-unverified"] = challenge_val
    oauth_state.next_profile = {"sub": "g-unv", "email": "editor@example.com", "email_verified": False, "name": "No"}
    st, _, _, _, js_unv = http_req(port, "GET", f"/api/auth/oauth/google/callback?state={state_val}&code=code-unverified", headers={"Cookie": tx_cookie})
    assert st == 403, f"Expected 403 for unverified email, got {st} {js_unv}"

    # Start fresh tx & complete verified email OAuth2/PKCE link to existing editor@example.com!
    st, hdrs, oauth_cookies, _, _ = http_req(port, "GET", "/api/auth/oauth/google/start")
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(hdrs["location"]).query)
    state_val = qs["state"][0]
    challenge_val = qs["code_challenge"][0]
    tx_cookie = extract_cookie_pair(oauth_cookies, "grablab_oauth_tx")
    oauth_state.challenges["code-valid"] = challenge_val
    oauth_state.next_profile = {"sub": "google-uid-42", "email": "editor@example.com", "email_verified": True, "name": "OAuth Editor"}

    st, hdrs, cb_cookies, _, _ = http_req(port, "GET", f"/api/auth/oauth/google/callback?state={state_val}&code=code-valid", headers={"Cookie": tx_cookie})
    assert st == 302 and hdrs.get("location") == "/admin", f"Expected OAuth redirect to /admin, got {st} {hdrs}"
    oauth_sess_cookie = extract_cookie_pair(cb_cookies, "grablab_session")
    assert oauth_sess_cookie
    st, _, _, _, s_js = http_req(port, "GET", "/api/auth/session", headers={"Cookie": oauth_sess_cookie})
    assert st == 200 and s_js["user"]["email"] == "editor@example.com" and s_js["user"]["role"] == "editor"

    # With oauth_allow_signup enabled, a new verified user gets lowest-privilege 'viewer' role
    st, _, _, _, _ = admin.request("PUT", "/api/admin/settings/oauth", {
        "oauth_allow_signup": True,
        "providers": {"google": {"enabled": True, "client_id": "mock-google-client-id", "client_secret": "", "allowed_domains": "example.com"}}
    })
    assert st == 200
    st, hdrs, oauth_cookies, _, _ = http_req(port, "GET", "/api/auth/oauth/google/start")
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(hdrs["location"]).query)
    state_val = qs["state"][0]
    tx_cookie = extract_cookie_pair(oauth_cookies, "grablab_oauth_tx")
    oauth_state.challenges["code-new-viewer"] = qs["code_challenge"][0]
    oauth_state.next_profile = {"sub": "google-uid-999", "email": "newreader@example.com", "email_verified": True, "name": "New Reader"}
    st, hdrs, cb_cookies2, raw_v, js_v = http_req(port, "GET", f"/api/auth/oauth/google/callback?state={state_val}&code=code-new-viewer", headers={"Cookie": tx_cookie})
    assert st == 302 and hdrs.get("location") == "/", f"Expected 302 -> /, got {st} {hdrs} {raw_v} {js_v}"
    new_viewer_cookie = extract_cookie_pair(cb_cookies2, "grablab_session")
    st, _, _, _, sv_js = http_req(port, "GET", "/api/auth/session", headers={"Cookie": new_viewer_cookie})
    assert st == 200 and sv_js["user"]["role"] == "viewer" and sv_js["user"]["email"] == "newreader@example.com"

    # Disable Google again -> back to disabled-by-default behavior
    st, _, _, _, _ = admin.request("PUT", "/api/admin/settings/oauth", {
        "oauth_allow_signup": False,
        "providers": {"google": {"enabled": False, "client_id": "mock-google-client-id", "client_secret": "", "allowed_domains": "example.com"}}
    })
    assert st == 200
    st, _, _, _, _ = http_req(port, "GET", "/api/auth/oauth/google/start")
    assert st == 404
    print("  OK: Disabled-by-default OAuth, AES-256-GCM encryption, PKCE S256, and verified-email linking verified.")

    print("[8/10] Testing Content Type, 8 Custom Fields, GrabDecimal fidelity, XSS escaping, and 301 redirects...")
    st, _, _, _, js = admin.request("POST", "/api/content-types", {
        "slug": "product", "label_singular": "Product", "label_plural": "Products",
        "permalink_pattern": "/shop/:slug", "has_archive": True, "archive_slug": "shop"
    })
    assert st == 201 and js["content_type"]["slug"] == "product"

    field_specs = [
        {"field_key": "sku", "label": "SKU", "field_type": "text", "is_required": True, "sort_order": 1},
        {"field_key": "details", "label": "Details", "field_type": "rich_text", "is_required": False, "sort_order": 2},
        {"field_key": "stock", "label": "Stock", "field_type": "integer", "is_required": True, "sort_order": 3},
        {"field_key": "price", "label": "Price", "field_type": "decimal", "is_required": True, "sort_order": 4},
        {"field_key": "in_stock", "label": "In Stock", "field_type": "boolean", "is_required": False, "default_value": "yes", "sort_order": 5},
        {"field_key": "launch_date", "label": "Launch Date", "field_type": "date", "is_required": False, "sort_order": 6},
        {"field_key": "spec_url", "label": "Spec URL", "field_type": "url", "is_required": False, "sort_order": 7},
        {"field_key": "layout", "label": "Grex Layout", "field_type": "json", "is_required": False, "sort_order": 8},
    ]
    for fs in field_specs:
        st, _, _, _, js = admin.request("POST", "/api/content-types/product/fields", fs)
        assert st == 201

    st, _, _, _, js = admin.request("POST", "/api/entries", {
        "content_type": "product",
        "slug": "merino-beanie",
        "title": "Merino Wool Beanie <script>xss</script>",
        "status": "published",
        "body_html": "Warm winter knit beanie.",
        "custom_fields": {
            "sku": "BN-100",
            "details": "<p>100% merino wool</p>",
            "stock": "42",
            "price": "19.9500",
            "launch_date": "2026-11-13",
            "spec_url": "https://example.com/specs/merino-beanie",
            "layout": {
                "element": "Section",
                "tag": "section",
                "children": [
                    {"element": "Heading", "props": {"level": 2, "text": "Merino Wool Beanie"}},
                    {"element": "Link", "props": {"href": "/shop/merino-beanie"}}
                ]
            }
        }
    })
    assert st == 201
    beanie_id = js["entry"]["id"]
    assert json.loads(js["entry"]["custom_fields_json"])["price"] == "19.9500"

    st, _, _, html, _ = http_req(port, "GET", "/shop/merino-beanie")
    assert st == 200 and "&lt;script&gt;xss&lt;/script&gt;" in html and "19.9500" in html

    # Atomic slug change -> 301 -> loop-free revert
    st, _, _, _, js = admin.request("PUT", f"/api/entries/{beanie_id}", {"slug": "wool-beanie"})
    assert st == 200 and js["entry"]["full_path"] == "/shop/wool-beanie"
    st, hdrs, _, _, _ = http_req(port, "GET", "/shop/merino-beanie")
    assert st == 301 and hdrs.get("location") == "/shop/wool-beanie"
    st, _, _, _, js = admin.request("PUT", f"/api/entries/{beanie_id}", {"slug": "merino-beanie"})
    assert st == 200
    st, _, _, _, _ = http_req(port, "GET", "/shop/merino-beanie")
    assert st == 200
    st, hdrs, _, _, _ = http_req(port, "GET", "/shop/wool-beanie")
    assert st == 301 and hdrs.get("location") == "/shop/merino-beanie"
    print("  OK: Content types, custom fields, exact decimals, XSS escaping, and 301 redirects verified.")

    print("[9/10] Testing 1-click exclusive theme switching (/api/admin/themes/activate), Grex visual mode & Query Loop...")
    try:
        vis_dir = os.path.join(ROOT, "themes", "test-grex-visual")
        os.makedirs(vis_dir, exist_ok=True)
        with open(os.path.join(vis_dir, "theme.json"), "w", encoding="utf-8") as f:
            json.dump({
                "schemaVersion": "1.0.0",
                "slug": "test-grex-visual",
                "name": "Grex Visual Fixture",
                "version": "1.0.0",
                "mode": "visual",
                "engine": "grex-visual",
                "capabilities": ["grex:visual", "parts", "hooks:theme"],
                "themeHooks": [{"hook": "theme:head_meta", "priority": 5, "handler": "theme_meta_brand"}]
            }, f)
        with open(os.path.join(vis_dir, "grex.elements.json"), "w", encoding="utf-8") as f:
            json.dump({
                "parts": {
                    "header": {"element": "Nav", "props": {"class": "grex-nav", "aria-label": "Visual Nav"}, "children": [{"element": "Link", "props": {"href": "/", "text": "{site_title}"}}]},
                    "footer": {"element": "Section", "tag": "footer", "props": {"class": "grex-footer"}, "children": [{"element": "Text", "props": {"text": "Visual Footer: {theme_slug}"}}]},
                    "card": {"element": "Card", "props": {"class": "grex-card"}, "children": [{"element": "Heading", "props": {"level": 3, "text": "{title}"}}]},
                    "sidebar": {"element": "Section", "tag": "aside", "props": {"class": "grex-sidebar"}, "children": [{"element": "Text", "props": {"text": "Visual Sidebar ({published_count})"}}]}
                },
                "templates": {
                    "home": {"element": "Fragment", "children": [
                        {"element": "TemplatePart", "props": {"name": "header"}},
                        {"element": "Container", "tag": "main", "children": [{"element": "Heading", "props": {"level": 1, "text": "GREX-VISUAL-HOME: {site_title}"}}]},
                        {"element": "TemplatePart", "props": {"name": "footer"}}
                    ]},
                    "single": {"element": "Section", "tag": "main", "children": [{"element": "Heading", "props": {"level": 1, "text": "{title}"}}]},
                    "archive": {"element": "Section", "tag": "main", "children": [{"element": "Heading", "props": {"level": 1, "text": "{archive_label}"}}]},
                    "404": {"element": "Section", "tag": "main", "children": [{"element": "Heading", "props": {"level": 1, "text": "Visual 404"}}]}
                }
            }, f)

        # 1-click switch via /api/admin/themes/activate
        st, _, _, _, js = admin.request("POST", "/api/admin/themes/activate", {"slug": "test-grex-visual"})
        assert st == 200 and js["active_theme"]["slug"] == "test-grex-visual" and js["mode"] == "visual"
        st, _, _, _, js = http_req(port, "GET", "/api/themes")
        assert [t["slug"] for t in js["themes"] if t["is_active"] == 1] == ["test-grex-visual"]
        st, _, _, html, _ = http_req(port, "GET", "/")
        assert st == 200 and "GREX-VISUAL-HOME:" in html and "default-starter" not in html and "<div" not in html.lower()

        # Switch back atomically
        st, _, _, _, js = admin.request("POST", "/api/admin/themes/activate", {"slug": "default-starter"})
        assert st == 200 and js["active_theme"]["slug"] == "default-starter"
        st, _, _, html, _ = http_req(port, "GET", "/")
        assert st == 200 and "Default Starter" in html and "GREX-VISUAL-HOME" not in html
    finally:
        shutil.rmtree(os.path.join(ROOT, "themes", "test-grex-visual"), ignore_errors=True)

    # Hook isolation & Query Loop cache invalidation on publish
    st, _, _, _, js = admin.request("POST", "/api/hooks/register-check", {
        "registrations": [{"kind": "hook", "name": "theme:before_render", "source": "plugin:evil", "priority": 1, "handler": "theme_before_render_badge"}]
    })
    assert st == 403 and "GRAB-E401" in js["error"]

    st, _, _, _, q1 = http_req(port, "GET", "/api/query?content_type=product&page=1&per_page=1")
    assert st == 200 and q1["cache"]["hit"] is False and q1["pagination"]["total_items"] == 1
    st, _, _, _, q2 = http_req(port, "GET", "/api/query?content_type=product&page=1&per_page=1")
    assert st == 200 and q2["cache"]["hit"] is True

    st, _, _, _, p2 = admin.request("POST", "/api/entries", {
        "content_type": "product", "slug": "alpaca-scarf", "title": "  Alpaca Winter Scarf  ", "status": "published",
        "body_html": "Soft scarf", "custom_fields": {"sku": "SC-200", "stock": "15", "price": "34.5000"}
    })
    assert st == 201 and p2["entry"]["meta_title"] == "Alpaca Winter Scarf"
    st, _, _, _, q3 = http_req(port, "GET", "/api/query?content_type=product&page=1&per_page=1")
    assert st == 200 and q3["cache"]["hit"] is False and q3["pagination"]["total_items"] == 2
    print("  OK: 1-click exclusive theme switching, hooks isolation, and Query Loop cache invalidation verified.")

    run_v04_tests(port, admin, editor, author1, author2, viewer)


def make_test_png(width=4, height=3):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw_rows = b"".join(b"\x00" + (b"\x10\x80\xc0" * width) for _ in range(height))
    idat = zlib.compress(raw_rows)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def run_v04_tests(port, admin, editor, author1, author2, viewer):
    print("[10/13] Testing v0.4.0 Media Library & Safe Upload Pipeline...")
    png_bytes = make_test_png(12, 8)
    png_b64 = base64.b64encode(png_bytes).decode("ascii")

    # Viewer forbidden & missing CSRF rejected
    assert viewer.request("POST", "/api/admin/media/upload", {"filename": "v.png", "mime_type": "image/png", "data_base64": png_b64, "alt_text": "no"})[0] == 403
    assert author1.request("POST", "/api/admin/media/upload", {"filename": "v.png", "mime_type": "image/png", "data_base64": png_b64, "alt_text": "no"}, send_csrf=False)[0] == 403

    # Reject missing alt text on images (422)
    st, _, _, _, js = author1.request("POST", "/api/admin/media/upload", {
        "original_name": "hero.png", "mime_type": "image/png", "data_base64": png_b64, "alt_text": "", "is_decorative": False
    })
    assert st == 422 and js["error"] == "alt_text_required", f"Expected 422 alt_text_required, got {st} {js}"

    # Reject SVG & spoofed .png with HTML/SVG payload (415)
    svg_b64 = base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>').decode("ascii")
    assert author1.request("POST", "/api/admin/media/upload", {"filename": "bad.svg", "mime_type": "image/svg+xml", "data_base64": svg_b64, "alt_text": "bad"})[0] == 415
    assert author1.request("POST", "/api/admin/media/upload", {"filename": "spoof.png", "mime_type": "image/png", "data_base64": svg_b64, "alt_text": "bad"})[0] == 415

    # Reject corrupt/truncated PNG (400)
    corrupt_png_b64 = base64.b64encode(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x05corrupt").decode("ascii")
    assert author1.request("POST", "/api/admin/media/upload", {"filename": "broken.png", "mime_type": "image/png", "data_base64": corrupt_png_b64, "alt_text": "broken"})[0] == 400

    # Reject path traversal filenames (400)
    assert author1.request("POST", "/api/admin/media/upload", {"filename": "../../etc/passwd", "mime_type": "image/png", "data_base64": png_b64, "alt_text": "x"})[0] == 400
    assert author1.request("POST", "/api/admin/media/upload", {"filename": "..\\evil.png", "mime_type": "image/png", "data_base64": png_b64, "alt_text": "x"})[0] == 400

    # Reject > 10 MiB payload limit cleanly (413)
    oversize_b64 = "A" * 14000004
    assert author1.request("POST", "/api/admin/media/upload", {"filename": "huge.png", "mime_type": "image/png", "data_base64": oversize_b64, "alt_text": "big"})[0] == 413

    # Valid PNG upload by author1 (also verify alias /api/media/upload works cleanly)
    st, _, _, _, m_up = author1.request("POST", "/api/media/upload", {
        "original_name": "Product Banner.png",
        "mime_type": "image/png",
        "data_base64": "data:image/png;base64," + png_b64,
        "alt_text": "Teal grablab showcase banner",
        "caption": "Hero banner",
    })
    assert st == 201, f"Expected 201 upload, got {st} {m_up}"
    media1 = m_up["media"]
    assert media1["mime_type"] == "image/png" and media1["width"] == 12 and media1["height"] == 8
    assert media1["filename"].endswith(".png") and len(media1["filename"]) == 36
    assert os.path.exists(os.path.join(ROOT, "uploads", media1["filename"] + ".b64"))

    # Valid PDF upload + decorative GIF upload
    pdf_b64 = base64.b64encode(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n").decode("ascii")
    st, _, _, _, m_pdf = editor.request("POST", "/api/admin/media/upload", {
        "filename": "guide.pdf", "mime_type": "application/pdf", "data_base64": pdf_b64
    })
    assert st == 201 and m_pdf["media"]["width"] is None

    gif_b64 = base64.b64encode(b"GIF89a\x02\x00\x02\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x02\x00\x02\x00\x00\x02\x02D\x01\x00;").decode("ascii")
    st, _, _, _, m_gif = author1.request("POST", "/api/admin/media/upload", {
        "filename": "spacer.gif", "mime_type": "image/gif", "data_base64": gif_b64, "alt_text": "", "is_decorative": True
    })
    assert st == 201 and m_gif["media"]["is_decorative"] is True and m_gif["media"]["width"] == 2

    # Safe media serving headers, ETag / 304, & unknown filename 404
    st, hdrs, _, body, _ = http_req(port, "GET", media1["url"])
    assert st == 200
    assert hdrs.get("content-type") == "image/png"
    assert hdrs.get("x-content-type-options") == "nosniff"
    assert "immutable" in hdrs.get("cache-control", "")
    assert hdrs.get("etag")
    assert http_req(port, "GET", media1["url"], headers={"If-None-Match": hdrs["etag"]})[0] == 304
    assert http_req(port, "GET", f"/media/{media1['id']}/wrong-name.png")[0] == 404

    # Ownership enforcement: author2 cannot PATCH/DELETE author1's media; editor CAN update
    assert author2.request("PATCH", f"/api/admin/media/{media1['id']}", {"alt_text": "Hijacked"})[0] == 403
    assert author2.request("DELETE", f"/api/admin/media/{media1['id']}")[0] == 403
    assert editor.request("PATCH", f"/api/admin/media/{media1['id']}", {"alt_text": "Updated teal showcase banner"})[0] == 200
    assert author1.request("DELETE", f"/api/admin/media/{m_gif['media']['id']}")[0] == 200
    print("  OK: Media magic-byte sniffing, SVG/traversal/422-alt blocks, dimensions, ETag/nosniff, & ownership verified.")

    print("[11/13] Testing v0.4.0 Navigation Menus, Atomic Slot Assignment, & Semantic <nav> Rendering...")
    # Seeded primary menu works on GET /api/menus/primary and renders in GET / without wrapper <div>
    st, _, _, _, pm = http_req(port, "GET", "/api/menus/primary")
    assert st == 200 and pm["menu"]["slug"] == "main-nav"
    st, _, _, home_html, _ = http_req(port, "GET", "/")
    assert st == 200 and "<nav" in home_html and 'aria-current="page"' in home_html and "<div" not in home_html.lower()

    # Author forbidden on menu management
    assert author1.request("POST", "/api/admin/menus", {"slug": "no-auth", "name": "No", "location": "footer"})[0] == 403

    # Create footer menu & new primary menu -> verify atomic location takeover & cache invalidation
    st, _, _, _, m_foot = editor.request("POST", "/api/admin/menus", {"slug": "footer-nav", "name": "Footer Links", "location": "footer"})
    assert st == 201
    st, _, _, _, m_alt = editor.request("POST", "/api/admin/menus", {"slug": "alt-nav", "name": "Custom Header Nav", "location": "primary"})
    assert st == 201
    alt_id = m_alt["menu"]["id"]
    st, _, _, _, pm2 = http_req(port, "GET", "/api/menus/primary")
    assert st == 200 and pm2["menu"]["slug"] == "alt-nav"

    # Reject javascript:/data:// protocol external URLs, cycle, and depth > 4
    assert editor.request("POST", f"/api/admin/menus/{alt_id}/items", {
        "label": "XSS", "link_type": "external", "external_url": "javascript:alert(1)"
    })[0] == 400
    assert editor.request("POST", f"/api/admin/menus/{alt_id}/items", {
        "label": "ProtoRel", "link_type": "external", "external_url": "//evil.example/phish"
    })[0] == 400
    assert editor.request("PUT", f"/api/admin/menus/{alt_id}/items", {"items": [
        {"client_id": "a", "parent_key": "b", "label": "A", "link_type": "external", "external_url": "https://example.com"},
        {"client_id": "b", "parent_key": "a", "label": "B", "link_type": "external", "external_url": "https://example.com/b"},
    ]})[0] == 400
    assert editor.request("PUT", f"/api/admin/menus/{alt_id}/items", {"items": [
        {"client_id": "d1", "parent_key": "", "label": "L1", "link_type": "external", "external_url": "https://example.com/1"},
        {"client_id": "d2", "parent_key": "d1", "label": "L2", "link_type": "external", "external_url": "https://example.com/2"},
        {"client_id": "d3", "parent_key": "d2", "label": "L3", "link_type": "external", "external_url": "https://example.com/3"},
        {"client_id": "d4", "parent_key": "d3", "label": "L4", "link_type": "external", "external_url": "https://example.com/4"},
        {"client_id": "d5", "parent_key": "d4", "label": "L5", "link_type": "external", "external_url": "https://example.com/5"},
    ]})[0] == 400

    # Create target entry -> link in alt-nav -> rename entry slug -> menu auto-resolves new full_path!
    st, _, _, _, m_entry_res = editor.request("POST", "/api/entries", {
        "content_type": "post", "slug": "menu-target", "title": "Menu Target", "status": "published", "body_html": "Target body"
    })
    assert st == 201
    target_eid = m_entry_res["entry"]["id"]
    st, _, _, m_put_raw, m_put_res = editor.request("PUT", f"/api/admin/menus/{alt_id}/items", {"items": [
        {"client_id": "home", "parent_key": "", "label": "Home", "link_type": "external", "external_url": "/"},
        {"client_id": "targ", "parent_key": "home", "label": "Target", "link_type": "entry", "entry_id": target_eid},
        {"client_id": "ext", "parent_key": "", "label": "GRAB Docs", "link_type": "external", "external_url": "https://grab-lang.org", "target_blank": True},
    ]})
    assert st == 200, f"PUT menu items failed: {st} {m_put_raw} {m_put_res}"
    st, _, _, _, pm3 = http_req(port, "GET", "/api/menus/primary")
    assert pm3["menu"]["items"][0]["children"][0]["url"] == "/blog/menu-target"

    # Rename entry slug -> menu cache invalidated & resolved URL updates automatically!
    assert editor.request("PUT", f"/api/entries/{target_eid}", {"slug": "menu-target-v2"})[0] == 200
    st, _, _, _, pm4 = http_req(port, "GET", "/api/menus/primary")
    assert pm4["menu"]["items"][0]["children"][0]["url"] == "/blog/menu-target-v2"
    st, _, _, home_nav_html, _ = http_req(port, "GET", "/")
    assert 'href="/blog/menu-target-v2"' in home_nav_html and "<div" not in home_nav_html.lower()
    print("  OK: Menus atomic slot assignment, cycle/depth-4/URL validation, slug auto-resolution, & <nav> verified.")

    print("[12/13] Testing v0.4.0 Taxonomies, Terms, query_entries filter_by_term & Archives...")
    # Reserved prefix & content-type archive_slug collisions -> 409 Conflict
    assert editor.request("POST", "/api/admin/taxonomies", {
        "slug": "admin-tax", "label_singular": "X", "label_plural": "Xs", "archive_slug": "media"
    })[0] == 409
    assert editor.request("POST", "/api/admin/taxonomies", {
        "slug": "blog-tax", "label_singular": "B", "label_plural": "Bs", "archive_slug": "blog"
    })[0] == 409

    # Create hierarchical custom taxonomy `topic` + parent term `grab` + child term `cms`
    st, _, _, _, tx_res = editor.request("POST", "/api/admin/taxonomies", {
        "slug": "topic", "label_singular": "Topic", "label_plural": "Topics",
        "is_hierarchical": True, "archive_slug": "topic", "content_type_slugs": ["post"]
    })
    assert st == 201
    st, _, _, _, t_par = editor.request("POST", "/api/admin/taxonomies/topic/terms", {"slug": "grab", "name": "GRAB Language"})
    assert st == 201
    grab_tid = t_par["term"]["id"]
    st, _, _, _, t_ch = editor.request("POST", "/api/admin/taxonomies/topic/terms", {"slug": "cms", "name": "CMS Architecture", "parent_id": grab_tid})
    assert st == 201
    cms_tid = t_ch["term"]["id"]

    # Flat taxonomy `post_tag` must reject parent_id (400)
    st, _, _, _, t_tag1 = editor.request("POST", "/api/admin/taxonomies/post_tag/terms", {"slug": "v04", "name": "v0.4"})
    assert st == 201
    assert editor.request("POST", "/api/admin/taxonomies/post_tag/terms", {"slug": "subtag", "name": "Subtag", "parent_id": t_tag1["term"]["id"]})[0] == 400

    # Query empty child archive, then assign target entry -> verify cache invalidation & include_children expansion
    q_empty1 = http_req(port, "GET", "/api/query?taxonomy=topic&term_slug=grab&include_children=true")[4]
    assert q_empty1["pagination"]["total_items"] == 0 and q_empty1["cache"]["hit"] is False
    q_empty2 = http_req(port, "GET", "/api/query?taxonomy=topic&term_slug=grab&include_children=true")[4]
    assert q_empty2["cache"]["hit"] is True

    st, _, _, _, _ = editor.request("PUT", f"/api/admin/entries/{target_eid}/terms", {"term_ids": [cms_tid, t_tag1["term"]["id"]]})
    assert st == 200
    q_after = http_req(port, "GET", "/api/query?taxonomy=topic&term_slug=grab&include_children=true")[4]
    assert q_after["cache"]["hit"] is False and q_after["pagination"]["total_items"] == 1
    assert q_after["items"][0]["id"] == target_eid
    q_strict = http_req(port, "GET", "/api/query?taxonomy=topic&term_slug=grab&include_children=false")[4]
    assert q_strict["pagination"]["total_items"] == 0

    # Public archive routes (/category/uncategorized, /topic/cms, /tag/v04, 404 unknown)
    for ok_arch, expect_txt in (("/category/uncategorized", "Hello, GrabLab CMS"), ("/topic/cms", "Menu Target"), ("/tag/v04", "Menu Target")):
        st, _, _, html, _ = http_req(port, "GET", ok_arch)
        assert st == 200 and expect_txt in html and "<div" not in html.lower(), f"Failed archive {ok_arch}: {st}"
    assert http_req(port, "GET", "/category/missing-term-xyz")[0] == 404
    print("  OK: Taxonomies, reserved prefix 409, include_children, query cache invalidation, & archives verified.")

    print("[13/13] Testing v0.4.0 Capability-Gated grab mcp CMS Tools & Grex/WCAG AI Guardrails...")
    # Mint MCP Bearer tokens for admin, author1, viewer
    admin_mcp = admin.request("POST", "/api/auth/mcp-token", {})[4]["token"]
    author_mcp = author1.request("POST", "/api/auth/mcp-token", {})[4]["token"]
    viewer_mcp = viewer.request("POST", "/api/auth/mcp-token", {})[4]["token"]

    def mcp_call(tok, tool_name, args=None):
        hdrs = {"Authorization": f"Bearer {tok}"} if tok else {}
        return http_req(port, "POST", f"/api/mcp/tools/{tool_name}", {"arguments": args or {}}, headers=hdrs)

    # Unauthenticated & viewer RBAC denials
    assert mcp_call("", "list_content_types")[0] == 401
    assert mcp_call(viewer_mcp, "list_content_types")[0] == 403
    assert mcp_call(viewer_mcp, "create_entry_draft", {"content_type": "post", "slug": "v-draft", "title": "V"})[0] == 403
    assert mcp_call(viewer_mcp, "query_entries", {"status": "draft"})[0] == 403
    assert mcp_call(viewer_mcp, "list_media")[0] == 403
    assert mcp_call(viewer_mcp, "list_menus")[0] == 403

    # JSON-RPC initialize & tools/list
    st, _, _, _, rpc_init = http_req(port, "POST", "/api/mcp", {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}, headers={"Authorization": f"Bearer {admin_mcp}"})
    assert st == 200 and rpc_init["result"]["serverInfo"]["name"] == "grablab-cms-mcp"
    st, _, _, _, rpc_list = http_req(port, "POST", "/api/mcp", {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, headers={"Authorization": f"Bearer {admin_mcp}"})
    assert {t["name"] for t in rpc_list["result"]["tools"]} == {"list_content_types", "query_entries", "create_entry_draft", "update_entry_layout", "list_media", "list_menus"}

    # Read tools omit all secrets
    for tname in ("list_content_types", "query_entries", "list_media", "list_menus"):
        st, _, _, raw_body, _ = mcp_call(admin_mcp, tname, {})
        assert st == 200
        for secret_key in ("password_hash", "csrf_secret", "client_secret", TEST_MASTER_KEY):
            assert secret_key not in raw_body, f"Secret leaked in {tname}"

    # create_entry_draft ALWAYS forces status='draft' even if status='published' passed
    st, _, _, _, draft_res = mcp_call(author_mcp, "create_entry_draft", {
        "content_type": "post",
        "slug": "ai-mcp-draft",
        "title": "AI Draft Post",
        "status": "published",
        "term_ids": [cms_tid],
    })
    assert st == 201 and draft_res["entry"]["status"] == "draft" and draft_res["status_enforced"] == "draft"
    ai_entry_id = draft_res["entry"]["id"]

    # update_entry_layout MUST reject: wrapper <div>, <script>, javascript: URL, missing alt, skipped heading h1->h3
    bad_layout = {
        "element": "Section",
        "tag": "div",
        "children": [
            {"element": "Heading", "props": {"level": 1, "text": "Intro"}},
            {"element": "Heading", "props": {"level": 3, "text": "Skipped H2"}},
            {"element": "Image", "props": {"src": f"/media/{media1['id']}/{media1['filename']}"}},
            {"element": "Link", "props": {"href": "javascript:alert(1)", "text": "Bad Link"}},
            {"element": "Text", "props": {"text": "<script>evil()</script>"}},
        ],
    }
    st, _, _, bad_raw, bad_res = mcp_call(author_mcp, "update_entry_layout", {"entry_id": ai_entry_id, "layout": bad_layout})
    assert st == 422 and isinstance(bad_res, dict) and bad_res.get("error") == "grex_validation_failed", f"got {st}: {bad_raw} {bad_res}"
    rules_hit = {v["rule"] for v in bad_res["violations"]}
    assert {"no-wrapper-div", "a11y-heading-order", "a11y-image-alt", "url-protocol-check", "csp-safe"}.issubset(rules_hit), f"Missing violations: {rules_hit}"

    # Ownership check: author1 cannot update editor's entry layout
    assert mcp_call(author_mcp, "update_entry_layout", {"entry_id": target_eid, "layout": {"element": "Heading", "props": {"level": 1, "text": "Hijack"}}})[0] == 403

    # Valid semantic WCAG AA layout succeeds
    good_layout = {
        "element": "Section",
        "tag": "article",
        "children": [
            {"element": "Heading", "props": {"level": 1, "text": "Accessible AI Showcase"}},
            {"element": "Heading", "props": {"level": 2, "text": "Media Section"}},
            {"element": "Image", "props": {"media_id": media1["id"]}},
            {"element": "Text", "props": {"text": "Built cleanly with Grex JS and WCAG AA validation."}},
        ],
    }
    st, _, _, good_raw, good_res = mcp_call(author_mcp, "update_entry_layout", {"entry_id": ai_entry_id, "layout": good_layout})
    assert st == 200 and isinstance(good_res, dict) and "<article>" in good_res.get("body_html", "") and "<h1>Accessible AI Showcase</h1>" in good_res.get("body_html", "") and "<div" not in good_res.get("body_html", "").lower(), f"good_layout failed: {st} {good_raw} {good_res}"
    print("  OK: grab mcp CMS tools, Bearer RBAC, draft enforcement, Grex + WCAG AA 422 gate, & secret safety verified.")


def main():
    test_checks_and_formatting()
    test_migrations_and_seed()
    oauth_port, oauth_srv, oauth_state = start_mock_oauth_server()
    port = pick_free_port()
    proc, log_file, log_path = start_server(port, oauth_port)
    try:
        run_http_tests(port, oauth_port, oauth_state)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_file.close()
        oauth_srv.shutdown()
        if os.path.exists(log_path):
            os.remove(log_path)

    print("[13/13] Restoring clean migrated & seeded storage/grablab.db baseline...")
    test_migrations_and_seed()
    print("\nALL GRABLAB CMS v0.4.0 INTEGRATION TESTS PASSED (100%)!")


if __name__ == "__main__":
    main()
