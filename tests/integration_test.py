#!/usr/bin/env python3
"""
GrabLab CMS v0.2.0 Comprehensive Integration Test Suite
Tests:
1. grab check & grab format parity on all .grab and .grab.html files (including card/sidebar parts)
2. Database schema migration idempotency & initial seed
3. Content type registration, 8 typed custom fields, GrabDecimal/GrabInteger string fidelity, Grex JS v1.0.0 layout validation
4. Pretty permalink resolution (/, /search, /:slug, /:type_prefix/:slug, archives, 404, XSS escaping)
5. Reserved system route protection (/admin, /api, /static, /_health, /_ready)
6. Atomic slug change, 301 Moved Permanently redirects, and redirect-loop cleanup on slug revert
7. Safe theme import/package validation (rejecting path traversal, disallowed executables, unauthorized capabilities)
8. Exclusive active theme switching (coded <-> Grex Theme Builder visual mode), template parts with zero wrapper-<div> bloat
9. Native hooks & filters priority ordering, zero-plugin active-theme isolation, and lifecycle hooks
10. Query Loop Engine (/api/query) filtering, pagination, SQL injection/bad-arg rejection, and use cache invalidation
"""

import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GRAB_BIN = os.environ.get("GRAB_BIN", r"C:\Development\GRAB\dist\grab-windows-amd64.exe")
DB_PATH = os.path.join(ROOT, "storage", "grablab.db")


def run_cmd(args, cwd=ROOT, check=True):
    res = subprocess.run(
        [GRAB_BIN] + args,
        cwd=cwd,
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
    conn.close()
    parsed = None
    if "application/json" in resp_headers.get("content-type", ""):
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = None
    return resp.status, resp_headers, raw, parsed


def test_checks_and_formatting():
    print("[1/7] Running grab check and grab format verification...")
    grab_files = [
        "migrations/001_schema.grab",
        "migrations/001_schema_postgres.grab",
        "migrations/001_schema_mariadb.grab",
        "migrations/seed.grab",
    ]
    for gf in grab_files:
        run_cmd(["check", gf])
        fmt = run_cmd(["format", gf])
        with open(os.path.join(ROOT, gf), "r", encoding="utf-8") as f:
            actual = f.read()
        assert fmt.stdout == actual, f"{gf} is not canonically formatted"

    run_cmd(["check", "--platform-config", "grab.platform.json", "src/app.grab"])
    fmt_app = run_cmd(["format", "src/app.grab"])
    with open(os.path.join(ROOT, "src", "app.grab"), "r", encoding="utf-8") as f:
        assert fmt_app.stdout == f.read(), "src/app.grab is not canonically formatted"

    # Verify all .grab.html templates parse cleanly under grab check
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
        ]
        probe = os.path.join(tmp_dir, "tmpl_check.grab")
        for rel_tmpl, data_expr in templates:
            with open(probe, "w", encoding="utf-8") as f:
                f.write(
                    'use server\nroute "GET" "/"\n'
                    f'  give back server.html using "../{rel_tmpl}", {data_expr}\n'
                    "end\n"
                )
            run_cmd(["check", "tmp/tmpl_check.grab"])
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    print("  OK: All .grab and .grab.html files passed grab check and canonical format.")


def test_migrations_and_seed():
    print("[2/7] Testing database migrations & seed idempotency...")
    for suffix in ("", "-journal", "-wal", "-shm"):
        p = DB_PATH + suffix
        if os.path.exists(p):
            os.remove(p)

    m1 = run_cmd(["migrate", "--db-config", "grab.data.json", "--allow-db", "main:migrate", "migrations/001_schema.grab"])
    assert "applied: [1]" in m1.stdout, f"Expected initial migration applied: {m1.stdout}"

    m2 = run_cmd(["migrate", "--db-config", "grab.data.json", "--allow-db", "main:migrate", "migrations/001_schema.grab"])
    assert "applied: []" in m2.stdout, f"Expected idempotent second migration: {m2.stdout}"

    s1 = run_cmd(["run", "--db-config", "grab.data.json", "--allow-db", "main:read-write", "--allow-read", ".", "migrations/seed.grab"])
    assert "seed completed" in s1.stdout
    s2 = run_cmd(["run", "--db-config", "grab.data.json", "--allow-db", "main:read-write", "--allow-read", ".", "migrations/seed.grab"])
    assert "seed completed" in s2.stdout
    print("  OK: Schema migrations and initial seed are idempotent.")


def start_server(port):
    log_path = os.path.join(ROOT, "storage", "test_server.log")
    log_file = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [
            GRAB_BIN,
            "serve",
            "--addr",
            f"127.0.0.1:{port}",
            "--db-config",
            "grab.data.json",
            "--allow-db",
            "main:read-write",
            "--platform-config",
            "grab.platform.json",
            "--allow-cache",
            "cms:read-write",
            "--allow-read",
            ".",
            "--static",
            "public",
            "src/app.grab",
        ],
        cwd=ROOT,
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
            st, _, _, js = http_req(port, "GET", "/_health")
            if st == 200 and js and js.get("status") == "ok":
                return proc, log_file, log_path
        except Exception:
            time.sleep(0.15)
    proc.terminate()
    log_file.close()
    raise AssertionError("Timed out waiting for GrabLab CMS server /_health")


def run_http_tests(port):
    print("[3/7] Testing health probes, static Grex JS v1.0.0 assets, and reserved routes...")
    st, _, _, js = http_req(port, "GET", "/_ready")
    assert st == 200 and js["status"] == "ready"

    st, hdrs, raw, _ = http_req(port, "GET", "/static/grex/grex.js")
    assert st == 200 and len(raw) > 10000, "Grex JS v1.0.0 runtime asset missing"

    st, _, raw, _ = http_req(port, "GET", "/static/grex/tokens.css")
    assert st == 200 and "--grex-" in raw, "Grex tokens CSS missing"

    st, _, raw, js = http_req(port, "GET", "/admin")
    assert st == 200 and js["status"] == "reserved-admin-prefix"

    st, _, _, js = http_req(port, "GET", "/admin/settings")
    assert st == 404 and "Reserved admin route" in js["error"]

    st, _, _, js = http_req(port, "GET", "/api/nonexistent")
    assert st == 404 and "Unknown API endpoint" in js["error"]

    # Seeded public routes + Template Parts + Zero wrapper-<div> verification
    st, _, html, _ = http_req(port, "GET", "/")
    assert st == 200 and "Default Starter" in html and "/static/grex/tokens.css?v=" in html
    assert '<header class="cms-header"' in html and '<aside class="cms-sidebar"' in html and '<article class="cms-card"' in html and '<footer class="cms-footer"' in html
    assert "<div" not in html.lower(), "Unexpected wrapper <div> found on /"
    assert '<meta name="generator" content="GrabLab CMS v0.2.0 (default-starter)">' in html

    st, _, html, _ = http_req(port, "GET", "/about")
    assert st == 200 and "About GrabLab CMS" in html and "<div" not in html.lower()
    st, _, html, _ = http_req(port, "GET", "/blog")
    assert st == 200 and "Posts" in html and "Hello, GrabLab CMS" in html and '<article class="cms-card"' in html and "<div" not in html.lower()
    st, _, html, _ = http_req(port, "GET", "/blog/hello-world")
    assert st == 200 and "Hello, GrabLab CMS" in html and "<div" not in html.lower()
    st, _, html, _ = http_req(port, "GET", "/search?q=Hello")
    assert st == 200 and "Hello, GrabLab CMS" in html and '<article class="cms-card"' in html and "<div" not in html.lower()
    st, _, html, _ = http_req(port, "GET", "/does-not-exist")
    assert st == 404 and "Page Not Found" in html and "<div" not in html.lower()
    print("  OK: System probes, static Grex JS v1.0.0 assets, template parts, zero-div HTML, and seeded routes verified.")

    print("[4/7] Testing Content Type, 8 Custom Field types, GrabDecimal precision & Grex layout validation...")
    st, _, _, js = http_req(port, "GET", "/api/content-types")
    assert st == 200
    slugs = [ct["slug"] for ct in js["content_types"]]
    assert "page" in slugs and "post" in slugs

    # Reject reserved prefix in content type
    st, _, _, js = http_req(port, "POST", "/api/content-types", {
        "slug": "admin_trap", "label_singular": "Trap", "label_plural": "Traps",
        "permalink_pattern": "/admin/:slug", "has_archive": False
    })
    assert st == 400 and "reserved" in js["error"].lower()

    st, _, _, js = http_req(port, "POST", "/api/content-types", {
        "slug": "api_trap", "label_singular": "Trap", "label_plural": "Traps",
        "permalink_pattern": "/traps/:slug", "has_archive": True, "archive_slug": "api"
    })
    assert st == 400 and "reserved" in js["error"].lower()

    # Register valid custom content type: product -> /shop/:slug
    st, _, _, js = http_req(port, "POST", "/api/content-types", {
        "slug": "product", "label_singular": "Product", "label_plural": "Products",
        "permalink_pattern": "/shop/:slug", "has_archive": True, "archive_slug": "shop"
    })
    assert st == 201 and js["content_type"]["slug"] == "product"

    # Attach all 8 supported field types
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
        st, _, _, js = http_req(port, "POST", "/api/content-types/product/fields", fs)
        assert st == 201, f"Failed creating field {fs['field_key']}: {js}"

    # Reserved slug collision on page (/admin)
    st, _, _, js = http_req(port, "POST", "/api/entries", {
        "content_type": "page", "slug": "admin", "title": "Hijack Admin", "status": "published"
    })
    assert st == 400 and "reserved" in js["error"].lower()

    # Missing required field
    st, _, _, js = http_req(port, "POST", "/api/entries", {
        "content_type": "product", "slug": "beanie", "title": "Beanie", "status": "published",
        "custom_fields": {"sku": "BN-01", "stock": "10"}
    })
    assert st == 400 and "price" in js["error"]

    # Invalid decimal
    st, _, _, js = http_req(port, "POST", "/api/entries", {
        "content_type": "product", "slug": "beanie", "title": "Beanie", "status": "published",
        "custom_fields": {"sku": "BN-01", "stock": "10", "price": "not-a-decimal"}
    })
    assert st == 400 and "decimal" in js["error"].lower()

    # Unsafe javascript: URL
    st, _, _, js = http_req(port, "POST", "/api/entries", {
        "content_type": "product", "slug": "beanie", "title": "Beanie", "status": "published",
        "custom_fields": {"sku": "BN-01", "stock": "10", "price": "19.9500", "spec_url": "javascript:alert(1)"}
    })
    assert st == 400 and "url" in js["error"].lower()

    # Unsafe Grex layout (wrapper div & inline onclick)
    st, _, _, js = http_req(port, "POST", "/api/entries", {
        "content_type": "product", "slug": "beanie", "title": "Beanie", "status": "published",
        "custom_fields": {
            "sku": "BN-01", "stock": "10", "price": "19.9500",
            "layout": {"element": "Section", "tag": "div"}
        }
    })
    assert st == 400 and "div" in js["error"].lower()

    st, _, _, js = http_req(port, "POST", "/api/entries", {
        "content_type": "product", "slug": "beanie", "title": "Beanie", "status": "published",
        "custom_fields": {
            "sku": "BN-01", "stock": "10", "price": "19.9500",
            "layout": {"element": "Button", "props": {"onclick": "hack()"}}
        }
    })
    assert st == 400 and "event handler" in js["error"].lower()

    # Valid entry preserving exact GrabDecimal "19.9500" and Grex JS v1.0.0 layout
    st, _, _, js = http_req(port, "POST", "/api/entries", {
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
    assert st == 201, f"Failed creating valid product: {js}"
    beanie = js["entry"]
    beanie_id = beanie["id"]
    cf_saved = json.loads(beanie["custom_fields_json"])
    assert cf_saved["price"] == "19.9500", f"Expected exact decimal string '19.9500', got {cf_saved['price']!r}"
    assert cf_saved["stock"] == "42"
    assert cf_saved["in_stock"] is True

    # Render product & archive, verify XSS escaping
    st, _, html, _ = http_req(port, "GET", "/shop/merino-beanie")
    assert st == 200
    assert "&lt;script&gt;xss&lt;/script&gt;" in html, "Expected XSS escaping in .grab.html"
    assert "19.9500" in html

    st, _, html, _ = http_req(port, "GET", "/shop")
    assert st == 200 and "Products" in html
    print("  OK: Content types, 8 custom field types, exact decimals, Grex layouts, and XSS escaping verified.")

    print("[5/7] Testing atomic slug changes, 301 redirects, and redirect-loop cleanup...")
    # Change slug merino-beanie -> wool-beanie
    st, _, _, js = http_req(port, "PUT", f"/api/entries/{beanie_id}", {"slug": "wool-beanie"})
    assert st == 200 and js["entry"]["full_path"] == "/shop/wool-beanie"

    # Old path must return 301 Moved Permanently -> /shop/wool-beanie
    st, hdrs, _, _ = http_req(port, "GET", "/shop/merino-beanie")
    assert st == 301 and hdrs.get("location") == "/shop/wool-beanie", f"Expected 301 to /shop/wool-beanie, got {st} {hdrs}"

    # New path returns 200
    st, _, html, _ = http_req(port, "GET", "/shop/wool-beanie")
    assert st == 200 and "Merino Wool Beanie" in html

    # Revert slug back wool-beanie -> merino-beanie (must delete old /shop/merino-beanie history to prevent loop!)
    st, _, _, js = http_req(port, "PUT", f"/api/entries/{beanie_id}", {"slug": "merino-beanie"})
    assert st == 200 and js["entry"]["full_path"] == "/shop/merino-beanie"

    st, _, html, _ = http_req(port, "GET", "/shop/merino-beanie")
    assert st == 200, f"Redirect loop or failure on reverted slug: got {st}"

    st, hdrs, _, _ = http_req(port, "GET", "/shop/wool-beanie")
    assert st == 301 and hdrs.get("location") == "/shop/merino-beanie"

    st, _, _, js = http_req(port, "GET", "/api/redirects")
    old_paths = [r["old_path"] for r in js["redirects"]]
    assert "/shop/merino-beanie" not in old_paths and "/shop/wool-beanie" in old_paths
    print("  OK: 301 redirects and loop-free slug revert verified.")

    print("[6/7] Testing theme.json security validation & atomic exclusive theme switching...")
    bad_theme_dir = os.path.join(ROOT, "themes", "_test-bad-theme")
    alt_theme_dir = os.path.join(ROOT, "themes", "_test-alt-theme")
    try:
        os.makedirs(bad_theme_dir, exist_ok=True)
        with open(os.path.join(bad_theme_dir, "theme.json"), "w", encoding="utf-8") as f:
            json.dump({
                "schemaVersion": "1.0.0",
                "slug": "_test-bad-theme",
                "name": "Evil Theme",
                "version": "1.0.0",
                "engine": "coded",
                "templates": {
                    "home": "../../etc/passwd.grab.html",
                    "single": "templates/single.grab.html",
                    "archive": "templates/archive.grab.html",
                    "404": "templates/404.grab.html"
                }
            }, f)

        # wait: _test-bad-theme has underscore which is rejected by [a-z0-9-]+, let's also test valid slug with .. traversal!
        bad_slug_dir = os.path.join(ROOT, "themes", "test-bad-traversal")
        os.makedirs(bad_slug_dir, exist_ok=True)
        with open(os.path.join(bad_slug_dir, "theme.json"), "w", encoding="utf-8") as f:
            json.dump({
                "schemaVersion": "1.0.0",
                "slug": "test-bad-traversal",
                "name": "Evil Theme",
                "version": "1.0.0",
                "engine": "coded",
                "templates": {
                    "home": "../default-starter/templates/home.grab.html",
                    "single": "templates/single.grab.html",
                    "archive": "templates/archive.grab.html",
                    "404": "templates/404.grab.html"
                }
            }, f)

        st, _, _, js = http_req(port, "POST", "/api/themes/activate", {"slug": "test-bad-traversal"})
        assert st == 400 and "GRAB-E401" in js["error"], f"Expected path traversal block, got {st} {js}"

        # Test unauthorized capabilities block
        with open(os.path.join(bad_slug_dir, "theme.json"), "w", encoding="utf-8") as f:
            json.dump({
                "schemaVersion": "1.0.0",
                "slug": "test-bad-traversal",
                "name": "Evil Cap Theme",
                "version": "1.0.0",
                "engine": "coded",
                "capabilities": ["shell"],
                "templates": {
                    "home": "templates/home.grab.html",
                    "single": "templates/single.grab.html",
                    "archive": "templates/archive.grab.html",
                    "404": "templates/404.grab.html"
                }
            }, f)
        st, _, _, js = http_req(port, "POST", "/api/themes/activate", {"slug": "test-bad-traversal"})
        assert st == 400 and "GRAB-E401" in js["error"]

        # Test disallowed executable extension in theme directory
        bad_exec_dir = os.path.join(ROOT, "themes", "test-bad-exec")
        os.makedirs(os.path.join(bad_exec_dir, "templates"), exist_ok=True)
        with open(os.path.join(bad_exec_dir, "theme.json"), "w", encoding="utf-8") as f:
            json.dump({
                "schemaVersion": "1.0.0",
                "slug": "test-bad-exec",
                "name": "Evil Exec Theme",
                "version": "1.0.0",
                "mode": "coded",
                "templates": {
                    "home": "templates/home.grab.html",
                    "single": "templates/single.grab.html",
                    "archive": "templates/archive.grab.html",
                    "404": "templates/404.grab.html"
                }
            }, f)
        for slot in ("home", "single", "archive", "404"):
            with open(os.path.join(bad_exec_dir, "templates", f"{slot}.grab.html"), "w", encoding="utf-8") as f:
                f.write("<!doctype html><html><body><p>ok</p></body></html>\n")
        with open(os.path.join(bad_exec_dir, "payload.sh"), "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\nid\n")
        st, _, _, js = http_req(port, "POST", "/api/themes/activate", {"slug": "test-bad-exec"})
        assert st == 400 and "GRAB-E401" in js["error"], f"Expected executable rejection, got {st} {js}"

        # Test theme package bundle validator rejections
        st, _, _, js = http_req(port, "POST", "/api/themes/validate-package", {
            "slug": "pkg-bad",
            "manifest": {"schemaVersion": "1.0.0", "slug": "pkg-bad", "name": "Bad", "version": "1.0.0", "mode": "coded", "templates": {"home": "templates/home.grab.html", "single": "templates/single.grab.html", "archive": "templates/archive.grab.html", "404": "templates/404.grab.html"}},
            "files": [{"path": "../escape.txt", "content": "x"}]
        })
        assert st == 400 and "GRAB-E401" in js["error"]

        st, _, _, js = http_req(port, "POST", "/api/themes/validate-package", {
            "slug": "pkg-bad-php",
            "manifest": {"schemaVersion": "1.0.0", "slug": "pkg-bad-php", "name": "Bad", "version": "1.0.0", "mode": "coded", "templates": {"home": "templates/home.grab.html", "single": "templates/single.grab.html", "archive": "templates/archive.grab.html", "404": "templates/404.grab.html"}},
            "files": [{"path": "backdoor.php", "content": "<?php ?>"}]
        })
        assert st == 400 and "GRAB-E401" in js["error"]

        # Create valid second coded theme test-alt-theme
        alt_dir = os.path.join(ROOT, "themes", "test-alt-theme")
        os.makedirs(os.path.join(alt_dir, "templates"), exist_ok=True)
        with open(os.path.join(alt_dir, "theme.json"), "w", encoding="utf-8") as f:
            json.dump({
                "schemaVersion": "1.0.0",
                "slug": "test-alt-theme",
                "name": "Alt Exclusive Theme",
                "version": "1.0.0",
                "engine": "coded",
                "templates": {
                    "home": "templates/home.grab.html",
                    "single": "templates/single.grab.html",
                    "archive": "templates/archive.grab.html",
                    "404": "templates/404.grab.html"
                }
            }, f)
        for slot in ("home", "single", "archive", "404"):
            with open(os.path.join(alt_dir, "templates", f"{slot}.grab.html"), "w", encoding="utf-8") as f:
                f.write(f"<!doctype html><html><head><title>ALT</title></head><body><h1>ALT-EXCLUSIVE-{slot.upper()}</h1><p>{{theme_slug}}</p></body></html>\n")

        # Activate test-alt-theme
        st, _, _, js = http_req(port, "POST", "/api/themes/activate", {"slug": "test-alt-theme"})
        assert st == 200 and js["active_theme"]["slug"] == "test-alt-theme"

        # Verify exclusive single active theme invariant
        st, _, _, js = http_req(port, "GET", "/api/themes")
        assert js["active_theme_slug"] == "test-alt-theme"
        active_rows = [t["slug"] for t in js["themes"] if t["is_active"] == 1]
        assert active_rows == ["test-alt-theme"], f"Expected only 1 active theme, got {active_rows}"

        # Verify cache invalidation immediately rendered ALT-EXCLUSIVE-HOME
        st, _, html, _ = http_req(port, "GET", "/")
        assert st == 200 and "ALT-EXCLUSIVE-HOME" in html and "Default Starter" not in html

        # Create & activate first-class Grex Visual Theme (mode: "visual")
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
                "themeHooks": [
                    {"hook": "theme:head_meta", "priority": 5, "handler": "theme_meta_brand"}
                ]
            }, f)
        with open(os.path.join(vis_dir, "grex.elements.json"), "w", encoding="utf-8") as f:
            json.dump({
                "parts": {
                    "header": {"element": "Nav", "props": {"class": "grex-nav", "aria-label": "Visual Nav"}, "children": [{"element": "Link", "props": {"href": "/", "text": "{site_title}"}}]},
                    "footer": {"element": "Section", "tag": "footer", "props": {"class": "grex-footer"}, "children": [{"element": "Text", "props": {"text": "Visual Footer: {theme_slug}"}}]},
                    "card": {"element": "Card", "props": {"class": "grex-card"}, "children": [{"element": "Heading", "props": {"level": 3, "text": "{title}"}}, {"element": "Link", "props": {"href": "{full_path}", "text": "Read more"}}]},
                    "sidebar": {"element": "Section", "tag": "aside", "props": {"class": "grex-sidebar"}, "children": [{"element": "Text", "props": {"text": "Visual Sidebar ({published_count})"}}]}
                },
                "templates": {
                    "home": {"element": "Fragment", "children": [
                        {"element": "TemplatePart", "props": {"name": "header"}},
                        {"element": "Container", "tag": "main", "children": [
                            {"element": "Heading", "props": {"level": 1, "text": "GREX-VISUAL-HOME: {site_title}"}},
                            {"element": "ForEach", "props": {"class": "grex-loop", "query": {"content_type": "post", "per_page": "5"}}},
                            {"element": "TemplatePart", "props": {"name": "sidebar"}}
                        ]},
                        {"element": "TemplatePart", "props": {"name": "footer"}}
                    ]},
                    "single": {"element": "Section", "tag": "main", "children": [{"element": "Heading", "props": {"level": 1, "text": "{title}"}}]},
                    "archive": {"element": "Section", "tag": "main", "children": [{"element": "Heading", "props": {"level": 1, "text": "{archive_label}"}}]},
                    "404": {"element": "Section", "tag": "main", "children": [{"element": "Heading", "props": {"level": 1, "text": "Visual 404"}}]}
                }
            }, f)

        st, _, _, js = http_req(port, "POST", "/api/themes/activate", {"slug": "test-grex-visual"})
        assert st == 200 and js["active_theme"]["slug"] == "test-grex-visual" and js["mode"] == "visual", f"Failed activating visual theme: {js}"

        st, _, html, _ = http_req(port, "GET", "/")
        assert st == 200 and "GREX-VISUAL-HOME:" in html and "Visual Sidebar" in html and "Visual Footer: test-grex-visual" in html
        assert 'data-grex-foreach="query"' in html and "/static/grex/grex.js?v=" in html
        assert '<meta name="theme-name" content="Grex Visual Fixture">' in html
        assert "default-starter" not in html and "<div" not in html.lower()

        # Verify /api/hooks isolated strictly to core + test-grex-visual (no default-starter hooks)
        st, _, _, js = http_req(port, "GET", "/api/hooks")
        assert st == 200 and js["active_theme_slug"] == "test-grex-visual"
        head_meta_regs = js["filters"]["theme:head_meta"]
        assert [r["source"] for r in head_meta_regs] == ["theme:test-grex-visual", "core"]
        assert [r["priority"] for r in head_meta_regs] == [5, 10]

        # Switch back to default-starter
        st, _, _, js = http_req(port, "POST", "/api/themes/activate", {"slug": "default-starter"})
        assert st == 200 and js["active_theme"]["slug"] == "default-starter"
        st, _, _, js = http_req(port, "GET", "/api/themes")
        active_rows = [t["slug"] for t in js["themes"] if t["is_active"] == 1]
        assert active_rows == ["default-starter"]
        st, _, html, _ = http_req(port, "GET", "/")
        assert st == 200 and "Default Starter" in html and "GREX-VISUAL-HOME" not in html
    finally:
        for d in ("_test-bad-theme", "test-bad-traversal", "test-bad-exec", "_test-alt-theme", "test-alt-theme", "test-grex-visual"):
            p = os.path.join(ROOT, "themes", d)
            if os.path.exists(p):
                shutil.rmtree(p, ignore_errors=True)
    print("  OK: Theme security validation, Grex visual mode, template parts, and exclusive switching verified.")

    print("[7/8] Testing native hooks/filters priority order, zero-plugin isolation & Query Loop cache invalidation...")
    # Zero-plugin isolation: reject inactive theme or plugin source
    st, _, _, js = http_req(port, "POST", "/api/hooks/register-check", {
        "registrations": [{"kind": "hook", "name": "theme:before_render", "source": "plugin:evil", "priority": 1, "handler": "theme_before_render_badge"}]
    })
    assert st == 403 and "GRAB-E401" in js["error"]

    st, _, _, js = http_req(port, "POST", "/api/hooks/register-check", {
        "registrations": [{"kind": "filter", "name": "theme:head_meta", "source": "theme:inactive-theme", "priority": 1, "handler": "theme_meta_brand"}]
    })
    assert st == 403 and "GRAB-E401" in js["error"]

    # Priority ordering: 50, 1, 10, 10 -> sorted [1, 10(first), 10(second), 50]
    st, _, _, js = http_req(port, "POST", "/api/hooks/register-check", {
        "registrations": [
            {"kind": "filter", "name": "theme:head_meta", "source": "theme:default-starter", "priority": 50, "handler": "theme_meta_brand"},
            {"kind": "filter", "name": "theme:head_meta", "source": "theme:default-starter", "priority": 1, "handler": "theme_meta_generator"},
            {"kind": "filter", "name": "theme:head_meta", "source": "core", "priority": 10, "handler": "core_default_head_meta"},
            {"kind": "filter", "name": "theme:head_meta", "source": "theme:default-starter", "priority": 10, "handler": "theme_meta_brand"}
        ]
    })
    assert st == 200
    ordered = js["filters"]["theme:head_meta"]
    assert [(r["priority"], r["handler"]) for r in ordered] == [
        (1, "theme_meta_generator"),
        (10, "core_default_head_meta"),
        (10, "theme_meta_brand"),
        (50, "theme_meta_brand"),
    ], f"Unexpected hook priority ordering: {ordered}"

    # Query Loop Engine: reject unsafe sort_by / field_op / out-of-range per_page
    st, _, _, js = http_req(port, "GET", "/api/query?sort_by=id%20DROP%20TABLE%20entries")
    assert st == 400
    st, _, _, js = http_req(port, "GET", "/api/query?sort_by=unknown_col")
    assert st == 400
    st, _, _, js = http_req(port, "GET", "/api/query?field_op=like_raw")
    assert st == 400
    st, _, _, js = http_req(port, "GET", "/api/query?per_page=500")
    assert st == 400

    # Query Loop custom field filter + cache hit/miss
    st, _, _, js1 = http_req(port, "GET", "/api/query?content_type=product&field_key=sku&field_op=eq&field_value=BN-100")
    assert st == 200 and js1["cache"]["hit"] is False and len(js1["items"]) == 1
    assert js1["items"][0]["custom_fields"]["price"] == "19.9500"

    st, _, _, js2 = http_req(port, "GET", "/api/query?content_type=product&field_key=sku&field_op=eq&field_value=BN-100")
    assert st == 200 and js2["cache"]["hit"] is True and len(js2["items"]) == 1

    # Query pagination before & after publishing a second product (tests content:after_publish cache invalidation)
    st, _, _, q_before = http_req(port, "GET", "/api/query?content_type=product&sort_by=id&sort_dir=desc&page=1&per_page=1")
    assert st == 200 and q_before["pagination"]["total_items"] == 1 and q_before["cache"]["hit"] is False

    st, _, _, q_before_hit = http_req(port, "GET", "/api/query?content_type=product&sort_by=id&sort_dir=desc&page=1&per_page=1")
    assert st == 200 and q_before_hit["cache"]["hit"] is True

    # Publish second product (omits meta_title to verify content:before_save filter auto-fills it!)
    st, _, _, created_p2 = http_req(port, "POST", "/api/entries", {
        "content_type": "product",
        "slug": "alpaca-scarf",
        "title": "  Alpaca Winter Scarf  ",
        "status": "published",
        "body_html": "Soft brushed alpaca scarf.",
        "custom_fields": {"sku": "SC-200", "stock": "15", "price": "34.5000"}
    })
    assert st == 201 and created_p2["entry"]["title"] == "Alpaca Winter Scarf"
    assert created_p2["entry"]["meta_title"] == "Alpaca Winter Scarf"

    # Immediately query again: cache MUST be invalidated (hit == False) and total_items == 2!
    st, _, _, q_after = http_req(port, "GET", "/api/query?content_type=product&sort_by=id&sort_dir=desc&page=1&per_page=1")
    assert st == 200 and q_after["cache"]["hit"] is False, f"Expected query cache invalidation on publish: {q_after}"
    assert q_after["pagination"]["total_items"] == 2 and q_after["pagination"]["total_pages"] == 2
    assert q_after["pagination"]["has_next"] is True and q_after["pagination"]["has_prev"] is False
    assert q_after["items"][0]["slug"] == "alpaca-scarf"

    st, _, _, q_page2 = http_req(port, "GET", "/api/query?content_type=product&sort_by=id&sort_dir=desc&page=2&per_page=1")
    assert st == 200 and q_page2["pagination"]["has_prev"] is True and q_page2["pagination"]["has_next"] is False
    assert q_page2["items"][0]["slug"] == "merino-beanie"
    print("  OK: Native hooks/filters priority, zero-plugin isolation, and Query Loop cache invalidation verified.")


def main():
    test_checks_and_formatting()
    test_migrations_and_seed()
    port = pick_free_port()
    proc, log_file, log_path = start_server(port)
    try:
        run_http_tests(port)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_file.close()
        if os.path.exists(log_path):
            os.remove(log_path)

    # Reset storage/grablab.db back to clean seeded baseline after tests
    print("[8/8] Restoring clean migrated & seeded storage/grablab.db baseline...")
    test_migrations_and_seed()
    print("\nALL GRABLAB CMS v0.2.0 INTEGRATION TESTS PASSED (100%)!")


if __name__ == "__main__":
    main()
