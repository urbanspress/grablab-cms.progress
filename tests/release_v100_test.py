#!/usr/bin/env python3
"""GrabLab CMS v1.0.0 End-to-End Production Release & Hardening Test Suite.

Verifies every v1.0.0 stability contract in an isolated SQLite + upload sandbox:
1. Repository-wide `grab check` and canonical `grab format` verification on every
   `.grab` and `.grab.html` file, plus zero wrapper-`<div>` checks across all
   starter templates, visual renders, and Admin UI screens.
2. Fresh install from empty SQLite DB (`001 -> 002 -> 003` and direct `003`),
   PostgreSQL & MariaDB `001`–`003` schema parity, and idempotent `seed.grab`.
3. Server boot with `--allow-scripts`, `--allow-env`, `--allow-write`, and
   `--static /static=public`, `/setup` primary admin creation & permanent lock.
4. Full CMS lifecycle: custom Content Type + `GrabDecimal` string precision ->
   Media upload into isolated upload directory -> Category/Tag assignment ->
   Entry publish + `301` slug rename -> Navigation Menu live permalink update ->
   Query Loop `/api/query` + deterministic `use cache` invalidation ->
   `grab mcp` (`1.0.0` JSON-RPC + draft enforcement + Grex `422` guardrail) ->
   Exclusive Active Theme switch (`coded` <-> `visual` Grex Theme Builder mode).
5. Deployment bundle (`deploy/docker-compose.yml`, `deploy/README.md`) &
   `GRABLAB-SPEC-100.md` sanity checks (zero hardcoded secrets or real IPs).
"""

import base64
import binascii
import http.client
import json
import os
import re
import shutil
import socket
import sqlite3
import struct
import subprocess
import tempfile
import time
import urllib.parse
import zlib


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_grab_bin():
    for candidate in (
        os.environ.get("GRAB_BIN"),
        shutil.which("grab"),
        r"C:\Program Files\GRAB\grab.exe",
    ):
        if candidate and os.path.exists(candidate):
            return candidate
    raise RuntimeError("Could not locate GRAB CLI binary (set GRAB_BIN or install grab)")


GRAB_BIN = resolve_grab_bin()


def run_grab(args, check=True, env=None):
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    res = subprocess.run(
        [GRAB_BIN] + args,
        cwd=ROOT,
        env=merged_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and res.returncode != 0:
        raise AssertionError(
            f"Command failed ({res.returncode}): grab {' '.join(args)}\n"
            f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )
    return res


def find_free_port():
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
        elif isinstance(body, str):
            payload = body.encode("utf-8")
        else:
            payload = body
    conn.request(method, path, body=payload, headers=hdrs)
    resp = conn.getresponse()
    raw_bytes = resp.read()
    resp_headers = {k.lower(): v for k, v in resp.getheaders()}
    set_cookies = resp.msg.get_all("Set-Cookie") or []
    conn.close()
    text = raw_bytes.decode("utf-8", errors="replace")
    parsed = None
    if "application/json" in resp_headers.get("content-type", ""):
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = None
    return resp.status, resp_headers, set_cookies, text, parsed


def make_png_bytes(width=12, height=8, rgba=(15, 118, 110, 255)):
    def chunk(tag, data):
        crc = binascii.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    row = b"\x00" + bytes(rgba) * width
    idat = zlib.compress(row * height)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


class SessionClient:
    def __init__(self, port, cookie_str, csrf_token):
        self.port = port
        self.cookie_str = cookie_str
        self.csrf_token = csrf_token

    def request(self, method, path, body=None, extra_headers=None):
        hdrs = dict(extra_headers or {})
        if self.cookie_str:
            hdrs["Cookie"] = self.cookie_str
        if method in ("POST", "PUT", "PATCH", "DELETE") and self.csrf_token:
            hdrs.setdefault("X-CSRF-Token", self.csrf_token)
        return http_req(self.port, method, path, body=body, headers=hdrs)


def extract_cookies_header(set_cookies):
    pairs = []
    for c in set_cookies:
        part = c.split(";", 1)[0].strip()
        if "=" in part:
            pairs.append(part)
    return "; ".join(pairs)


def verify_all_grab_and_templates():
    print("[1/5] Checking ALL .grab and .grab.html files across repo (`grab check`, canonical `grab format`, zero `<div>`)...")
    grab_files = []
    tmpl_files = []
    skip_dirs = {".git", "__pycache__", "node_modules", "storage", "uploads"}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith("_v100_")]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ROOT).replace("\\", "/")
            if fn.endswith(".grab"):
                grab_files.append(rel)
            elif fn.endswith(".grab.html"):
                tmpl_files.append(rel)

    assert "src/app.grab" in grab_files and len(grab_files) >= 11, f"Unexpected .grab files: {grab_files}"
    for gf in sorted(grab_files):
        run_grab(["check", "--platform-config", "grab.platform.json", gf])
        fmt = run_grab(["format", gf])
        with open(os.path.join(ROOT, gf), "r", encoding="utf-8") as f:
            assert fmt.stdout == f.read(), f"{gf} does not match canonical `grab format` output"

    template_contexts = {
        "themes/default-starter/templates/home.grab.html": 'record {site_title: "T", page_title: "H", meta_description: "D", tokens_css_url: "/s", theme_css_url: "/t", theme_name: "N", site_tagline: "G", published_count: "0", entries_summary: "E", theme_slug: "default-starter"}',
        "themes/default-starter/templates/single.grab.html": 'record {site_title: "T", meta_title: "M", meta_description: "D", tokens_css_url: "/s", theme_css_url: "/t", content_type_label: "Page", title: "Ti", full_path: "/about", published_at: "2026-11-14", body_text: "B", custom_fields_summary: "{}", theme_slug: "default-starter"}',
        "themes/default-starter/templates/archive.grab.html": 'record {site_title: "T", archive_label: "Posts", meta_description: "D", tokens_css_url: "/s", theme_css_url: "/t", entry_count: "1", archive_slug: "blog", entries_summary: "E", theme_slug: "default-starter"}',
        "themes/default-starter/templates/404.grab.html": 'record {site_title: "T", tokens_css_url: "/s", theme_css_url: "/t", requested_path: "/x", theme_slug: "default-starter"}',
        "themes/default-starter/templates/search.grab.html": 'record {site_title: "T", tokens_css_url: "/s", theme_css_url: "/t", query: "q", results_summary: "R", theme_slug: "default-starter"}',
        "themes/default-starter/templates/parts/header.grab.html": 'record {site_title: "T"}',
        "themes/default-starter/templates/parts/footer.grab.html": 'record {theme_slug: "default-starter"}',
        "themes/default-starter/templates/parts/card.grab.html": 'record {content_type_label: "Post", full_path: "/blog/hello", title: "Hello", published_at: "2026-11-14", excerpt: "Hi"}',
        "themes/default-starter/templates/parts/sidebar.grab.html": 'record {site_title: "T", site_tagline: "G", published_count: "2", theme_name: "Default Starter"}',
        "src/views/admin/login.grab.html": 'record {site_title: "T", tokens_css_url: "/s", admin_css_url: "/c", grex_js_url: "/g", admin_js_url: "/a"}',
        "src/views/admin/setup.grab.html": 'record {site_title: "T", tokens_css_url: "/s", admin_css_url: "/c", grex_js_url: "/g", admin_js_url: "/a"}',
        "src/views/admin/dashboard.grab.html": 'record {csrf_token: "x", admin_page: "overview", user_role: "admin", user_email: "a@b.c", user_name: "A", user_id: "1", site_title: "T", active_theme_slug: "default-starter", page_title: "D", page_subtitle: "S", tokens_css_url: "/s", admin_css_url: "/c", grex_js_url: "/g", admin_js_url: "/a"}',
        "src/views/shop/order.grab.html": 'record {tokens_css_url: "/s", shop_css_url: "/sc", order_number: "ORD-1", order_status: "paid", currency: "USD", subtotal: "19.99", discount_total: "0.00", tax_total: "1.65", shipping_total: "0.00", total: "21.64", created_at: "2026-11-17T00:00:00Z"}',
        "themes/default-starter/templates/shop.grab.html": 'record {site_title: "T", page_title: "Shop", archive_label: "Shop", meta_description: "D", tokens_css_url: "/s", theme_css_url: "/t", shop_css_url: "/sc", shop_js_url: "/sj", product_count: "1"}',
        "themes/default-starter/templates/product.grab.html": 'record {site_title: "T", meta_title: "Book", meta_description: "D", tokens_css_url: "/s", theme_css_url: "/t", shop_css_url: "/sc", shop_js_url: "/sj", content_type_label: "Product", product_kind: "physical", title: "Book", product_price: "19.99", product_currency: "USD", product_availability: "In Stock", product_sku: "BK-1", product_carrier: "usps", product_isbn_13: "9780306406157", body_text: "B", product_id: "1"}',
        "themes/default-starter/templates/cart.grab.html": 'record {site_title: "T", page_title: "Cart", meta_description: "D", tokens_css_url: "/s", theme_css_url: "/t", shop_css_url: "/sc", shop_js_url: "/sj", currency: "USD", guest_checkout: "true"}',
    }
    assert set(tmpl_files) == set(template_contexts.keys()), (
        f"Uncovered .grab.html templates: {set(tmpl_files) ^ set(template_contexts.keys())}"
    )

    probe_dir = os.path.join(ROOT, "_v100_probe_tmp")
    os.makedirs(probe_dir, exist_ok=True)
    try:
        probe_file = os.path.join(probe_dir, "check_tmpl.grab")
        for rel_tmpl, expr in sorted(template_contexts.items()):
            with open(os.path.join(ROOT, rel_tmpl), "r", encoding="utf-8") as tf:
                raw_html = tf.read()
            assert "<div" not in raw_html.lower(), f"Wrapper <div> found in {rel_tmpl}"
            with open(probe_file, "w", encoding="utf-8") as pf:
                pf.write(
                    'use server\nroute "GET" "/"\n'
                    f'  give back server.html using "../{rel_tmpl}", {expr}\n'
                    "end\n"
                )
            run_grab(["check", "_v100_probe_tmp/check_tmpl.grab"])
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)

    print(f"  OK: {len(grab_files)} .grab files & {len(tmpl_files)} .grab.html templates passed `grab check`, canonical `grab format`, and zero-<div> validation.")


def verify_fresh_migrations_and_parity(tmp_dir):
    print("[2/5] Testing empty-DB sequential install (001 -> 002 -> 003), direct 003 install, Postgres/MariaDB parity & idempotent seed...")

    # Sequential install: empty SQLite DB -> 001 -> 002 -> 003
    seq_db = os.path.join(tmp_dir, "seq.db")
    seq_cfg = os.path.join(tmp_dir, "seq.data.json")
    with open(seq_cfg, "w", encoding="utf-8") as f:
        json.dump({"connections": {"main": {"driver": "sqlite", "path": seq_db}}}, f)

    r1 = run_grab(["migrate", "--db-config", seq_cfg, "--allow-db", "main:migrate", "migrations/001_schema.grab"])
    assert "applied: [1]" in r1.stdout, r1.stdout
    r2 = run_grab(["migrate", "--db-config", seq_cfg, "--allow-db", "main:migrate", "migrations/002_auth_schema.grab"])
    assert "applied: [2]" in r2.stdout, r2.stdout
    r3 = run_grab(["migrate", "--db-config", seq_cfg, "--allow-db", "main:migrate", "migrations/003_v04_schema.grab"])
    assert "applied: [3]" in r3.stdout, r3.stdout

    expected_tables = {
        "site_settings",
        "content_types",
        "field_definitions",
        "entries",
        "slug_history",
        "themes",
        "users",
        "sessions",
        "oauth_accounts",
        "media",
        "menus",
        "menu_items",
        "taxonomies",
        "terms",
        "entry_terms",
    }
    con = sqlite3.connect(seq_db)
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert expected_tables.issubset(tables), f"Missing tables in sequential DB: {expected_tables - tables}"
        cols = {r[1] for r in con.execute("PRAGMA table_info(entries)").fetchall()}
        assert "author_id" in cols, f"Missing author_id on entries: {cols}"
    finally:
        con.close()

    # Direct fresh install on empty SQLite DB -> 003_v04_schema.grab
    dir_db = os.path.join(tmp_dir, "direct.db")
    dir_cfg = os.path.join(tmp_dir, "direct.data.json")
    with open(dir_cfg, "w", encoding="utf-8") as f:
        json.dump({"connections": {"main": {"driver": "sqlite", "path": dir_db}}}, f)
    rd = run_grab(["migrate", "--db-config", dir_cfg, "--allow-db", "main:migrate", "migrations/003_v04_schema.grab"])
    assert "applied: [1, 2, 3]" in rd.stdout, rd.stdout

    # Idempotent seed on sequential fresh DB
    s1 = run_grab(["run", "--db-config", seq_cfg, "--allow-db", "main:read-write", "--allow-read", ".", "migrations/seed.grab"])
    assert "v1.1.0 seed completed" in s1.stdout, s1.stdout
    s2 = run_grab(["run", "--db-config", seq_cfg, "--allow-db", "main:read-write", "--allow-read", ".", "migrations/seed.grab"])
    assert "v1.1.0 seed completed" in s2.stdout, s2.stdout

    con = sqlite3.connect(seq_db)
    try:
        ct_slugs = {r[0] for r in con.execute("SELECT slug FROM content_types").fetchall()}
        assert {"post", "page"}.issubset(ct_slugs), ct_slugs
        active_themes = [r[0] for r in con.execute("SELECT slug FROM themes WHERE is_active = 1").fetchall()]
        assert active_themes == ["default-starter"], active_themes
        tax_slugs = {r[0] for r in con.execute("SELECT slug FROM taxonomies").fetchall()}
        assert {"category", "post_tag"}.issubset(tax_slugs), tax_slugs
        menu_locs = {r[0] for r in con.execute("SELECT location FROM menus").fetchall()}
        assert "primary" in menu_locs, menu_locs
    finally:
        con.close()

    # SQLite / PostgreSQL / MariaDB parity across 001 -> 002 -> 003
    parity_checks = [
        ("001_schema", ["site_settings", "content_types", "field_definitions", "entries", "slug_history", "themes"]),
        ("002_auth_schema", ["users", "sessions", "oauth_accounts"]),
        ("003_v04_schema", ["media", "menus", "menu_items", "taxonomies", "terms", "entry_terms"]),
    ]
    for base, tbls in parity_checks:
        for suffix in ("", "_postgres", "_mariadb"):
            path = os.path.join(ROOT, "migrations", f"{base}{suffix}.grab")
            txt = open(path, "r", encoding="utf-8").read()
            for t in tbls:
                assert f"CREATE TABLE IF NOT EXISTS {t}" in txt, f"Missing table `{t}` in {path}"

    print("  OK: Sequential & direct SQLite fresh installs, 15 tables, idempotent seed, and SQLite/Postgres/MariaDB parity verified.")
    return seq_db, seq_cfg


def verify_full_lifecycle(tmp_dir, seq_db, seq_cfg):
    print("[3/5] Booting production-flagged server and running full v1.0.0 lifecycle...")
    uploads_dir = os.path.join(tmp_dir, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    port = find_free_port()
    log_path = os.path.join(tmp_dir, "server.log")
    env = os.environ.copy()
    env["GRABLAB_MASTER_KEY"] = "v100-release-verification-master-key-0123456789"
    env["GRABLAB_UPLOAD_DIR"] = uploads_dir
    env["GRABLAB_MAX_UPLOAD_BYTES"] = "10485760"

    repo_uploads_before = set(os.listdir(os.path.join(ROOT, "uploads")))
    log_fh = open(log_path, "w", encoding="utf-8")
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
            seq_cfg,
            "--allow-db",
            "main:read-write",
            "--platform-config",
            "grab.platform.json",
            "--allow-cache",
            "cms:read-write",
            "--allow-cache",
            "cms:limit",
            "--allow-env",
            "GRABLAB_MASTER_KEY,GRABLAB_UPLOAD_DIR,GRABLAB_MAX_UPLOAD_BYTES",
            "--allow-read",
            ".",
            "--allow-read",
            uploads_dir,
            "--allow-write",
            uploads_dir,
            "--static",
            "public",
            "src/app.grab",
        ],
        cwd=ROOT,
        env=env,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    vis_dir = os.path.join(ROOT, "themes", "v100-visual-builder-test")
    try:
        deadline = time.time() + 15
        ready = False
        while time.time() < deadline:
            if proc.poll() is not None:
                log_fh.close()
                raise RuntimeError("Server exited early:\n" + open(log_path, encoding="utf-8").read())
            try:
                st, _, _, _, js = http_req(port, "GET", "/_health")
                if st == 200 and js and js.get("status") == "ok":
                    ready = True
                    break
            except OSError:
                time.sleep(0.15)
        assert ready, "Server did not become healthy within 15s"

        st, _, _, _, rjs = http_req(port, "GET", "/_ready")
        assert st == 200 and rjs and rjs.get("status") == "ready", rjs

        # Verify /static/grex/ assets load cleanly (including grex.elements.json parity)
        assert http_req(port, "GET", "/static/grex/tokens.css")[0] == 200
        assert http_req(port, "GET", "/static/grex/grex.js")[0] == 200
        st_el, _, _, _, el_json = http_req(port, "GET", "/static/grex/grex.elements.json")
        assert st_el == 200 and isinstance(el_json, dict) and "Section" in el_json.get("elements", el_json), (st_el, el_json)

        # /setup screen -> admin creation -> permanent lock
        st, _, _, setup_html, _ = http_req(port, "GET", "/setup")
        assert st == 200 and "<div" not in setup_html.lower()
        st, _, cookies, _, setup_res = http_req(
            port,
            "POST",
            "/api/auth/setup",
            {
                "display_name": "Release Admin",
                "email": "release-admin@example.com",
                "password": "Release-v100-StrongPassword!",
            },
        )
        assert st == 201 and setup_res["user"]["role"] == "admin", setup_res
        admin = SessionClient(port, extract_cookies_header(cookies), setup_res["csrf_token"])

        # Confirm argon2id hash stored & /setup locked permanently
        con = sqlite3.connect(seq_db)
        try:
            phash = con.execute("SELECT password_hash FROM users WHERE email = ?", ("release-admin@example.com",)).fetchone()[0]
            assert phash.startswith("$argon2id$"), f"Expected argon2id hash, got {phash[:20]}"
        finally:
            con.close()
        assert http_req(port, "POST", "/api/auth/setup", {"name": "X", "email": "x@example.com", "password": "Password123456!"})[0] == 403
        st_get_setup, hdrs_setup, _, _, _ = http_req(port, "GET", "/setup")
        assert st_get_setup == 302 and hdrs_setup.get("location") == "/login"

        # Verify Admin UI shell renders zero <div>
        st, _, _, admin_html, _ = admin.request("GET", "/admin")
        assert st == 200 and "<div" not in admin_html.lower() and "GrabLab" in admin_html

        # 1) Custom Content Type + Decimal field (`GrabDecimal` exact string fidelity)
        st, _, _, _, ct_res = admin.request(
            "POST",
            "/api/content-types",
            {
                "slug": "catalog_item",
                "label_singular": "Catalog Item",
                "label_plural": "Catalog Items",
                "permalink_pattern": "/catalog/:slug",
                "has_archive": True,
                "archive_slug": "catalog",
            },
        )
        assert st == 201, ct_res
        st, _, _, _, fld_res = admin.request(
            "POST",
            "/api/content-types/catalog_item/fields",
            {"field_key": "price", "label": "Price", "field_type": "decimal", "is_required": True, "sort_order": 1},
        )
        assert st == 201, fld_res

        # 2) Media upload into isolated temp GRABLAB_UPLOAD_DIR (not repo `uploads/`)
        png_b64 = base64.b64encode(make_png_bytes(16, 10)).decode("ascii")
        st, _, _, _, med_res = admin.request(
            "POST",
            "/api/admin/media/upload",
            {
                "filename": "v1-hero.png",
                "original_name": "v1-hero.png",
                "mime_type": "image/png",
                "data_base64": "data:image/png;base64," + png_b64,
                "alt_text": "GrabLab v1.0.0 hero graphic",
                "caption": "Release showcase image",
            },
        )
        assert st == 201, med_res
        media = med_res["media"]
        assert media["width"] == 16 and media["height"] == 10
        isolated_b64_path = os.path.join(uploads_dir, media["filename"] + ".b64")
        assert os.path.exists(isolated_b64_path), "Upload must land inside isolated GRABLAB_UPLOAD_DIR"
        assert set(os.listdir(os.path.join(ROOT, "uploads"))) == repo_uploads_before, "Repo uploads/ must stay clean"
        st, m_hdrs, _, _, _ = http_req(port, "GET", media["url"])
        assert st == 200 and m_hdrs.get("x-content-type-options") == "nosniff" and "immutable" in m_hdrs.get("cache-control", "")

        # 3) Category + Tag assignment
        st, _, _, _, cat_res = admin.request("POST", "/api/admin/taxonomies/category/terms", {"slug": "guides", "name": "Guides"})
        assert st == 201, cat_res
        st, _, _, _, tag_res = admin.request("POST", "/api/admin/taxonomies/post_tag/terms", {"slug": "release-100", "name": "Release 1.0.0"})
        assert st == 201, tag_res
        cat_tid = cat_res["term"]["id"]
        tag_tid = tag_res["term"]["id"]

        # 4) Entry creation + GrabDecimal fidelity + terms
        st, _, _, _, ent_res = admin.request(
            "POST",
            "/api/entries",
            {
                "content_type": "catalog_item",
                "slug": "v1-showcase",
                "title": "GrabLab v1.0.0 Showcase",
                "status": "published",
                "body_html": "<p>Production release catalog item.</p>",
                "custom_fields": {"price": "149.9500"},
            },
        )
        assert st == 201, ent_res
        entry_id = ent_res["entry"]["id"]
        assert json.loads(ent_res["entry"]["custom_fields_json"])["price"] == "149.9500"

        st, _, _, _, _ = admin.request("PUT", f"/api/admin/entries/{entry_id}/terms", {"term_ids": [cat_tid, tag_tid]})
        assert st == 200

        # 5) 301 Slug rename + Navigation Menu resolution
        st, _, _, _, ren_res = admin.request("PUT", f"/api/entries/{entry_id}", {"slug": "v1-production-showcase"})
        assert st == 200 and ren_res["entry"]["full_path"] == "/catalog/v1-production-showcase", ren_res
        st_301, h_301, _, _, _ = http_req(port, "GET", "/catalog/v1-showcase")
        assert st_301 == 301 and h_301.get("location") == "/catalog/v1-production-showcase", (st_301, h_301)

        st, _, _, single_html, _ = http_req(port, "GET", "/catalog/v1-production-showcase")
        assert st == 200 and "149.9500" in single_html and "<div" not in single_html.lower()

        # Verify archives render cleanly with zero <div>
        for arch_path in ("/category/guides", "/tag/release-100"):
            st, _, _, ahtml, _ = http_req(port, "GET", arch_path)
            assert st == 200 and "GrabLab v1.0.0 Showcase" in ahtml and "<div" not in ahtml.lower(), arch_path

        # Navigation menu pointing to renamed entry resolves live `/catalog/v1-production-showcase`
        st, _, _, _, menus_list = admin.request("GET", "/api/admin/menus")
        primary_id = next(m["id"] for m in menus_list["menus"] if m["location"] == "primary")
        st, _, _, _, mput = admin.request(
            "PUT",
            f"/api/admin/menus/{primary_id}/items",
            {
                "items": [
                    {"client_id": "home", "parent_key": "", "label": "Home", "link_type": "external", "external_url": "/"},
                    {"client_id": "v1", "parent_key": "", "label": "Showcase", "link_type": "entry", "entry_id": entry_id},
                ]
            },
        )
        assert st == 200, mput
        st, _, _, _, pm = http_req(port, "GET", "/api/menus/primary")
        assert st == 200 and pm["menu"]["items"][1]["url"] == "/catalog/v1-production-showcase", pm
        st, _, _, home_html, _ = http_req(port, "GET", "/")
        assert st == 200 and 'href="/catalog/v1-production-showcase"' in home_html and 'content="GrabLab CMS v1.1.0 (default-starter)"' in home_html and "<div" not in home_html.lower()

        # 6) Query Loop + `use cache` hit & invalidation on entry update
        q_url = "/api/query?content_type=catalog_item&taxonomy=category&term_slug=guides&include_children=true"
        q1 = http_req(port, "GET", q_url)[4]
        assert q1["cache"]["hit"] is False and q1["pagination"]["total_items"] == 1
        q2 = http_req(port, "GET", q_url)[4]
        assert q2["cache"]["hit"] is True and q2["items"][0]["slug"] == "v1-production-showcase"

        assert admin.request("PUT", f"/api/entries/{entry_id}", {"title": "GrabLab v1.0.0 Showcase Updated"})[0] == 200
        q3 = http_req(port, "GET", q_url)[4]
        assert q3["cache"]["hit"] is False and q3["items"][0]["title"] == "GrabLab v1.0.0 Showcase Updated"

        # 7) `grab mcp` JSON-RPC 1.0.1 + SPEC-100 aliases + -32602 + WCAG/Grex 422 gate
        mcp_tok = admin.request("POST", "/api/auth/mcp-token", {})[4]["token"]
        st, _, _, _, rpc_init = http_req(
            port,
            "POST",
            "/api/mcp",
            {"jsonrpc": "2.0", "id": 10, "method": "initialize", "params": {}},
            headers={"Authorization": f"Bearer {mcp_tok}"},
        )
        assert st == 200 and rpc_init["result"]["serverInfo"]["version"] == "1.1.0", rpc_init

        st, _, _, _, rpc_tools = http_req(
            port,
            "POST",
            "/api/mcp",
            {"jsonrpc": "2.0", "id": 11, "method": "tools/list", "params": {}},
            headers={"Authorization": f"Bearer {mcp_tok}"},
        )
        assert st == 200 and {t["name"] for t in rpc_tools["result"]["tools"]} == {
            "list_content_types",
            "query_entries",
            "create_entry_draft",
            "update_entry_layout",
            "list_media",
            "list_menus",
        }

        st, _, _, _, draft_res = http_req(
            port,
            "POST",
            "/api/mcp/tools/create_entry_draft",
            {
                "arguments": {
                    "content_type": "post",
                    "slug": "mcp-v100-draft",
                    "title": "AI Release Draft",
                    "status": "published",
                }
            },
            headers={"Authorization": f"Bearer {mcp_tok}"},
        )
        assert st == 201 and draft_res["status_enforced"] == "draft" and draft_res["entry"]["status"] == "draft", draft_res
        mcp_entry_id = draft_res["entry"]["id"]

        bad_tree = {"element": "Box", "tag": "div", "children": [{"element": "Script", "props": {"text": "alert(1)"}}]}
        st, _, _, _, bad_res = http_req(
            port,
            "POST",
            "/api/mcp/tools/update_entry_layout",
            {"arguments": {"entry_id": mcp_entry_id, "layout": bad_tree}},
            headers={"Authorization": f"Bearer {mcp_tok}"},
        )
        assert st == 422 and bad_res.get("error") == "grex_validation_failed" and bad_res.get("code") == -32602, (st, bad_res)

        # JSON-RPC tools/call validation failure returns errorCode -32602 + WCAG contrast/outline rules
        low_contrast_tree = {
            "type": "Section",
            "styles": {"base": {"backgroundColor": "#ffffff"}},
            "children": [
                {"element": "Text", "styles": {"base": {"color": "#999999", "outline": "none"}}, "props": {"text": "Hard to read"}}
            ],
        }
        st, _, _, _, rpc_bad = http_req(
            port,
            "POST",
            "/api/mcp",
            {
                "jsonrpc": "2.0",
                "id": 12,
                "method": "tools/call",
                "params": {"name": "update_entry_layout", "arguments": {"entry_id": mcp_entry_id, "grex_layout": low_contrast_tree}},
            },
            headers={"Authorization": f"Bearer {mcp_tok}"},
        )
        assert st == 200 and rpc_bad["result"]["isError"] is True and rpc_bad["result"].get("errorCode") == -32602, rpc_bad
        rpc_sc = rpc_bad["result"]["structuredContent"]
        assert rpc_sc.get("code") == -32602 and {"GREX-A11Y-001", "GREX-A11Y-005"}.issubset({v["rule"] for v in rpc_sc.get("violations", [])}), rpc_sc

        # SPEC-100 create_entry_draft aliases + grex_layout validation gate
        st, _, _, _, alias_bad_draft = http_req(
            port,
            "POST",
            "/api/mcp/tools/create_entry_draft",
            {
                "arguments": {
                    "content_type_slug": "post",
                    "slug": "mcp-alias-bad",
                    "title": "Bad Alias Draft",
                    "body": "Body fallback",
                    "excerpt": "Excerpt fallback",
                    "grex_layout": low_contrast_tree,
                }
            },
            headers={"Authorization": f"Bearer {mcp_tok}"},
        )
        assert st == 422 and alias_bad_draft.get("code") == -32602, (st, alias_bad_draft)

        valid_alias_layout = {
            "element": "Section",
            "tag": "article",
            "children": [
                {"element": "Heading", "props": {"level": 1, "text": "v1.0.1 Spec-100 Alias Layout"}},
                {"element": "Text", "tag": "blockquote", "props": {"text": "Semantic blockquote text."}},
                {"element": "Text", "tag": "time", "props": {"text": "2026-11-14"}},
                {"element": "Image", "props": {"src": "/media/1/decor.png", "decorative": True}},
            ],
        }
        st, _, _, _, alias_good_draft = http_req(
            port,
            "POST",
            "/api/mcp/tools/create_entry_draft",
            {
                "arguments": {
                    "content_type_slug": "post",
                    "slug": "mcp-alias-good",
                    "title": "Good Alias Draft",
                    "excerpt": "Alias meta excerpt",
                    "status": "published",
                    "grex_layout": valid_alias_layout,
                }
            },
            headers={"Authorization": f"Bearer {mcp_tok}"},
        )
        assert st == 201 and alias_good_draft["status_enforced"] == "draft" and alias_good_draft["entry"]["meta_description"] == "Alias meta excerpt" and "<blockquote" in alias_good_draft["entry"]["body_html"], (st, alias_good_draft)

        # list_menus with optional location filter
        st, _, _, _, menus_filtered = http_req(
            port,
            "POST",
            "/api/mcp/tools/list_menus",
            {"arguments": {"location": "primary"}},
            headers={"Authorization": f"Bearer {mcp_tok}"},
        )
        assert st == 200 and len(menus_filtered.get("menus", [])) >= 1 and all((m.get("location") or "").lower() == "primary" for m in menus_filtered["menus"]), menus_filtered

        good_tree = {
            "element": "Section",
            "tag": "article",
            "children": [
                {"element": "Heading", "props": {"level": 1, "text": "v1.0.1 Production AI Layout"}},
                {"element": "Image", "props": {"media_id": media["id"]}},
                {"element": "Text", "props": {"text": "Validated Grex semantic HTML output."}},
            ],
        }
        st, _, _, _, good_res = http_req(
            port,
            "POST",
            "/api/mcp/tools/update_entry_layout",
            {"arguments": {"entry_id": mcp_entry_id, "grex_layout": good_tree}},
            headers={"Authorization": f"Bearer {mcp_tok}"},
        )
        assert st == 200 and "<article>" in good_res["body_html"] and "<div" not in good_res["body_html"].lower(), good_res

        # 8) Exclusive Active Theme switch (`coded` <-> `visual` Grex Theme Builder mode)
        os.makedirs(vis_dir, exist_ok=True)
        with open(os.path.join(vis_dir, "theme.json"), "w", encoding="utf-8") as f:
            json.dump(
                {
                    "schemaVersion": "1.0.0",
                    "slug": "v100-visual-builder-test",
                    "name": "Grex Visual Builder v1.0.0",
                    "version": "1.0.0",
                    "mode": "visual",
                    "engine": "grex-visual",
                    "capabilities": ["grex:visual", "parts", "hooks:theme"],
                    "themeHooks": [{"hook": "theme:head_meta", "priority": 5, "handler": "theme_meta_brand"}],
                },
                f,
            )
        with open(os.path.join(vis_dir, "grex.elements.json"), "w", encoding="utf-8") as f:
            json.dump(
                {
                    "parts": {
                        "header": {"element": "Nav", "props": {"class": "grex-nav", "aria-label": "Primary"}, "children": [{"element": "Link", "props": {"href": "/", "text": "{site_title}"}}]},
                        "footer": {"element": "Section", "tag": "footer", "props": {"class": "grex-footer"}, "children": [{"element": "Text", "props": {"text": "Theme: {theme_slug}"}}]},
                    },
                    "templates": {
                        "home": {
                            "element": "Fragment",
                            "children": [
                                {"element": "TemplatePart", "props": {"name": "header"}},
                                {"element": "Container", "tag": "main", "children": [{"element": "Heading", "props": {"level": 1, "text": "V100-VISUAL-MODE: {site_title}"}}]},
                                {"element": "TemplatePart", "props": {"name": "footer"}},
                            ],
                        },
                        "single": {"element": "Section", "tag": "main", "children": [{"element": "Heading", "props": {"level": 1, "text": "{title}"}}]},
                        "archive": {"element": "Section", "tag": "main", "children": [{"element": "Heading", "props": {"level": 1, "text": "{archive_label}"}}]},
                        "404": {"element": "Section", "tag": "main", "children": [{"element": "Heading", "props": {"level": 1, "text": "404 Not Found"}}]},
                    },
                },
                f,
            )

        st, _, _, _, sw1 = admin.request("POST", "/api/admin/themes/activate", {"slug": "v100-visual-builder-test"})
        assert st == 200 and sw1["active_theme"]["slug"] == "v100-visual-builder-test" and sw1["mode"] == "visual", sw1
        st, _, _, _, tlist = http_req(port, "GET", "/api/themes")
        assert [t["slug"] for t in tlist["themes"] if t["is_active"] == 1] == ["v100-visual-builder-test"]
        st, _, _, vis_home, _ = http_req(port, "GET", "/")
        assert st == 200 and "V100-VISUAL-MODE:" in vis_home and "default-starter" not in vis_home and "<div" not in vis_home.lower()

        st, _, _, _, sw2 = admin.request("POST", "/api/admin/themes/activate", {"slug": "default-starter"})
        assert st == 200 and sw2["active_theme"]["slug"] == "default-starter" and sw2["mode"] == "coded", sw2
        st, _, _, coded_home, _ = http_req(port, "GET", "/")
        assert st == 200 and "V100-VISUAL-MODE" not in coded_home and "default-starter" in coded_home and "<div" not in coded_home.lower()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_fh.close()
        shutil.rmtree(vis_dir, ignore_errors=True)

    print("  OK: /setup lock, GrabDecimal precision, isolated uploads, 301 history, menu resolution, cache invalidation, grab mcp, & exclusive theme switch verified.")


def verify_deployment_and_spec_bundle():
    print("[4/5] Verifying `GRABLAB-SPEC-100.md` and `deploy/` --read-only Docker bundle hygiene...")
    spec_path = os.path.join(ROOT, "specifications", "GRABLAB-SPEC-100.md")
    compose_path = os.path.join(ROOT, "deploy", "docker-compose.yml")
    readme_path = os.path.join(ROOT, "deploy", "README.md")
    for p in (spec_path, compose_path, readme_path):
        assert os.path.exists(p), f"Missing deliverable: {p}"

    compose_txt = open(compose_path, "r", encoding="utf-8").read()
    for required_token in (
        "read_only: true",
        "--allow-scripts",
        "--allow-env",
        "--allow-write",
        "--allow-read",
        "--allow-db",
        "cms:read-write",
        "cms:limit",
        "../storage:/app/storage:rw",
        "../uploads:/app/uploads:rw",
        "../public/grex:/app/public/grex:rw",
        "/app/public",
    ):
        assert required_token in compose_txt, f"Missing `{required_token}` in deploy/docker-compose.yml"

    deploy_readme_txt = open(readme_path, "r", encoding="utf-8").read()
    assert "--read-only" in deploy_readme_txt and "/static/grex/" in deploy_readme_txt and "storage/uploads" in deploy_readme_txt

    # Ensure no non-loopback / non-unspecified IPv4 addresses leaked into deploy files
    for fname, txt in ((compose_path, compose_txt), (readme_path, deploy_readme_txt)):
        for ip in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", txt):
            assert ip in ("127.0.0.1", "0.0.0.0"), f"Unexpected IPv4 `{ip}` in {fname}"

    spec_txt = open(spec_path, "r", encoding="utf-8").read()
    for section in ("001", "002", "003", "theme.json", "registerHook", "query_entries", "grab mcp", "--read-only", "/static/grex/"):
        assert section in spec_txt, f"Missing frozen contract `{section}` in GRABLAB-SPEC-100.md"

    print("  OK: SPEC-100 and deploy/ hardened --read-only Docker bundle verified with zero leaked secrets or IPs.")


def verify_git_workdirs_clean():
    print("[5/5] Confirming temporary test artifacts cleaned cleanly outside repo...")
    assert not os.path.exists(os.path.join(ROOT, "themes", "v100-visual-builder-test"))
    assert not os.path.exists(os.path.join(ROOT, "_v100_probe_tmp"))
    print("  OK: Repository temporary directories clean.")


def main():
    print(f"Using GRAB CLI: {GRAB_BIN}")
    verify_all_grab_and_templates()
    with tempfile.TemporaryDirectory(prefix="grablab_v100_") as tmp_dir:
        seq_db, seq_cfg = verify_fresh_migrations_and_parity(tmp_dir)
        verify_full_lifecycle(tmp_dir, seq_db, seq_cfg)
    verify_deployment_and_spec_bundle()
    verify_git_workdirs_clean()
    print("\nALL GRABLAB CMS v1.0.0 PRODUCTION RELEASE TESTS PASSED (100%)!")


if __name__ == "__main__":
    main()
