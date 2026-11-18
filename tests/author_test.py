#!/usr/bin/env python3
"""GrabLab CMS v1.4.0 Comprehensive Author Mode, Security, Commerce Linkage & Radar Race Test Suite."""

import base64
import concurrent.futures
import hashlib
import http.server
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import time

import commerce_test as ct

ROOT = ct.ROOT


class MockGroxyHandler(http.server.BaseHTTPRequestHandler):
    csrf_token = "groxy_mock_csrf_1234567890abcdef"
    last_radar_req = None
    last_radar_csrf = ""

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        if self.path == "/groxy":
            body = f'<!doctype html><html><head><meta name="groxy-csrf" content="{self.csrf_token}"></head><body>Groxy Mock</body></html>'.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/groxy/author/genres":
            out = json.dumps({"ok": True, "count": 2, "genres": [{"genre_slug": "urban-fiction", "display_name": "Urban Fiction"}]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        data = json.loads(raw) if raw else {}
        csrf_hdr = self.headers.get("X-CSRF-Token", "")
        if csrf_hdr != self.csrf_token:
            out = json.dumps({"ok": False, "code": "CSRF_INVALID"}).encode("utf-8")
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
            return
        if self.path == "/api/groxy/research/bestseller-radar":
            MockGroxyHandler.last_radar_req = data
            MockGroxyHandler.last_radar_csrf = csrf_hdr
            plan_id = "rplan-" + ("a1b2c3d4" * 4)
            tok = "rtok_res_" + ("0123456789abcdef" * 4)
            canonical = json.dumps({"radar_plan_id": plan_id, "genre_slug": data.get("genre_slug", "urban-fiction"), "price_tier_usd": data.get("price_tier_usd", "14.99")}, separators=(",", ":"), sort_keys=True)
            sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            out = json.dumps({
                "ok": True,
                "schema_version": "1.8.0",
                "radar_plan_id": plan_id,
                "genre_slug": data.get("genre_slug", "urban-fiction"),
                "target_consumer": data.get("target_consumer"),
                "selected_price_tier_usd": data.get("price_tier_usd", "14.99"),
                "payload_sha256": sha,
                "canonical_payload": canonical,
                "approval_required": True,
                "approval_token": tok,
                "brief": {"display_name": "Urban Fiction", "demand_signal_score": 92, "competition_index": 38, "selected_price_tier_usd": data.get("price_tier_usd", "14.99")},
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
            return
        if self.path == "/api/groxy/author/readability-audit":
            out = json.dumps({"ok": True, "clarity_score": 88, "grade_label": "Grade 6 (Crisp)"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
            return
        self.send_response(404)
        self.end_headers()


def start_author_server(db_cfg, work_dir, groxy_port, webhook_secret):
    port = ct.find_free_port()
    uploads_dir = os.path.join(work_dir, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    env = os.environ.copy()
    env["GRABLAB_UPLOAD_DIR"] = uploads_dir
    env["GRABLAB_MASTER_KEY"] = "test-master-key-01234567890123456789"
    env["GRABLAB_PAYMENT_WEBHOOK_SECRET"] = webhook_secret
    args = [
        ct.GRAB_BIN,
        "serve",
        "--addr",
        f"127.0.0.1:{port}",
        "--allow-scripts",
        "--max-body-bytes",
        "15728640",
        "--db-config",
        db_cfg,
        "--allow-db",
        "main:read-write",
        "--platform-config",
        "deploy/grab.platform.commerce.json",
        "--allow-cache",
        "cms:read-write",
        "--allow-cache",
        "cms:limit",
        "--allow-env",
        "GRABLAB_UPLOAD_DIR,GRABLAB_MASTER_KEY,GRABLAB_PAYMENT_WEBHOOK_SECRET",
        "--allow-net",
        f"127.0.0.1:{groxy_port}",
        "--allow-read",
        ".",
        "--allow-read",
        uploads_dir,
        "--allow-write",
        uploads_dir,
        "--allow-events",
        "commerce:accept",
        "--allow-events",
        "commerce:work",
        "--static",
        "public",
        "src/app.grab",
    ]
    log_path = os.path.join(work_dir, f"author_srv_{port}.log")
    log_fh = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(args, cwd=ROOT, env=env, stdout=log_fh, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            st, _, _, _, _ = ct.http_req(port, "GET", "/_health")
            if st == 200:
                return port, proc
        except Exception:
            if proc.poll() is not None:
                log_fh.close()
                raise RuntimeError("Author test server exited early:\n" + open(log_path, encoding="utf-8").read())
        time.sleep(0.15)
    proc.terminate()
    raise TimeoutError("Timed out starting Author test server")


def main():
    tmp_dir = tempfile.mkdtemp(prefix="gl_v140_test_")
    proc = None
    mock_srv = None
    try:
        groxy_port = ct.find_free_port()
        mock_srv = http.server.ThreadingHTTPServer(("127.0.0.1", groxy_port), MockGroxyHandler)
        t_mock = threading.Thread(target=mock_srv.serve_forever, daemon=True)
        t_mock.start()

        print("[1/10] Migrating 005_author_schema (SQLite) & running seed_author.grab...")
        db_path, db_cfg = ct.init_db_config(tmp_dir, "author.db")
        ct.run_grab(["migrate", "--db-config", db_cfg, "--allow-db", "main:migrate", "migrations/005_author_schema.grab"])
        ct.run_grab(["migrate", "--platform-config", "deploy/grab.platform.commerce.json", "--db-config", db_cfg, "--events-store", "commerce", "--allow-db", "main:migrate", "--allow-events", "commerce:work"])
        ct.run_grab(["run", "--db-config", db_cfg, "--allow-db", "main:read-write", "--allow-read", ".", "migrations/seed.grab"])
        ct.run_grab(["run", "--db-config", db_cfg, "--allow-db", "main:read-write", "--allow-read", ".", "migrations/seed_commerce.grab"])
        ct.run_grab(["run", "--db-config", db_cfg, "--allow-db", "main:read-write", "--allow-read", ".", "migrations/seed_author.grab"])
        ct.run_grab(["run", "--db-config", db_cfg, "--allow-db", "main:read-write", "--allow-read", ".", "migrations/seed_author.grab"])

        secret = "author_test_webhook_secret_32bytes!!"
        port, proc = start_author_server(db_cfg, tmp_dir, groxy_port, secret)

        admin = ct.SessionClient(port)
        admin.setup_or_login("admin@example.com", "StrongAdminPassword!123", setup=True, name="Admin Owner")

        print("[2/10] Testing default-off 404 gate (author_mode_enabled = 0)...")
        for p in ("/books", "/series", "/authors/anyone"):
            assert ct.http_req(port, "GET", p)[0] == 404, f"Expected 404 on {p} when disabled"
        for ap in ("/admin/author", "/admin/author/radar", "/api/admin/author/books"):
            assert admin.req("GET", ap)[0] == 404, f"Expected 404 on {ap} when disabled"
        st, _, _, _, status_res = admin.req("GET", "/api/admin/author/status")
        assert st == 200 and status_res["ready"] is True and status_res["enabled"] is False, status_res
        print("  OK: Default-off 404 gate verified across admin & public author routes.")

        print("[3/10] Testing GRAB-E402 origin allowlist, SSRF blocks, CSRF 403, RBAC 403 & MCP Bearer 401...")
        bad_origins = [
            "file:///etc/passwd",
            "javascript:alert(1)",
            "http://example.com",
            "https://169.254.169.254",
            "https://127.0.0.1",
            "https://localhost",
            "https://user@groxy.example.com",
            "https://10.0.0.1",
            "https://192.168.1.1",
            "https://groxy.example.com/extra/path",
        ]
        for bo in bad_origins:
            st, _, _, raw, _ = admin.req("POST", "/api/admin/author/settings", {"author_mode_enabled": True, "groxy_ai_origin": bo})
            assert st == 422 and "GRAB-E402" in raw, f"Expected GRAB-E402 422 for {bo}, got {st} {raw}"

        # Missing CSRF -> 403
        st, _, _, _, _ = admin.req("POST", "/api/admin/author/settings", {"author_mode_enabled": True}, omit_csrf=True)
        assert st == 403

        # Create editor, author, viewer users + MCP Bearer token
        for email, role in (("editor@example.com", "editor"), ("author@example.com", "author"), ("viewer@example.com", "viewer")):
            st, _, _, raw, _ = admin.req("POST", "/api/admin/users", {"email": email, "display_name": role.title(), "role": role, "password": "StrongUserPassword!123"})
            assert st == 201, raw

        editor = ct.SessionClient(port)
        editor.setup_or_login("editor@example.com", "StrongUserPassword!123")
        author_u = ct.SessionClient(port)
        author_u.setup_or_login("author@example.com", "StrongUserPassword!123")
        viewer = ct.SessionClient(port)
        viewer.setup_or_login("viewer@example.com", "StrongUserPassword!123")

        # Editor & Author blocked from /api/admin/author/settings (403)
        assert editor.req("POST", "/api/admin/author/settings", {"author_mode_enabled": True})[0] == 403
        assert author_u.req("POST", "/api/admin/author/settings", {"author_mode_enabled": True})[0] == 403

        # Admin enables Author Mode + valid local Groxy worker origin
        st, _, _, raw, set_res = admin.req("POST", "/api/admin/author/settings", {
            "author_mode_enabled": True,
            "groxy_ai_origin": f"http://127.0.0.1:{groxy_port}",
        })
        assert st == 200 and set_res["author_mode_enabled"] is True, raw

        # MCP Bearer token rejected with 401 on /api/admin/author/*
        st, _, _, _, tok_res = admin.req("POST", "/api/auth/mcp-token", {"label": "author-mcp"})
        assert st == 201 and tok_res.get("token"), raw
        mcp_tok = tok_res["token"]
        for m_method, m_path in (("GET", "/api/admin/author/books"), ("POST", "/api/admin/author/settings"), ("POST", "/api/admin/author/radar/import")):
            st, _, _, _, _ = ct.http_req(port, m_method, m_path, body={}, headers={"Authorization": f"Bearer {mcp_tok}"})
            assert st == 401, f"Expected 401 for MCP Bearer on {m_path}, got {st}"

        # Viewer rejected with 403 on author routes
        assert viewer.req("GET", "/api/admin/author/books")[0] == 403
        assert viewer.req("POST", "/api/admin/author/books", {"title": "X", "slug": "x"})[0] == 403
        print("  OK: GRAB-E402, CSRF 403, RBAC 403, and MCP Bearer 401 verified.")

        print("[4/10] Testing ADR-025c 422 float/exponent guards, ISBN-13, ASIN, and reserved prefix 409...")
        st, _, _, raw, a_res = admin.req("POST", "/api/admin/author/authors", {
            "pen_name": "Marcus Vance",
            "slug": "marcus-vance",
            "bio_summary": "Crime & thriller novelist.",
            "website_url": "https://marcusvance.example.com",
            "status": "published",
        })
        assert st == 201, raw
        author_id = a_res["author"]["id"]

        # Reject floats & scientific notation
        for bad_field, bad_val in (
            ("list_price", 14.99),
            ("list_price", "1.49e1"),
            ("royalty_rate", 70.5),
            ("royalty_rate", "100.01"),
            ("page_count", 284.5),
            ("word_count", "7e4"),
        ):
            payload = {"title": "Bad Num", "slug": "bad-num", "author_id": author_id, "list_price": "14.99", "royalty_rate": "70.00"}
            payload[bad_field] = bad_val
            st, _, _, raw, js = admin.req("POST", "/api/admin/author/books", payload)
            assert st == 422 and js["error"] == "author_validation_failed", (bad_field, bad_val, st, raw)

        # Reject invalid ISBN-13 & ASIN
        st, _, _, raw, js = admin.req("POST", "/api/admin/author/books", {
            "title": "Bad ISBN", "slug": "bad-isbn", "author_id": author_id, "isbn_13": "9780306406158", "list_price": "14.99"
        })
        assert st == 422 and js["reason"] == "invalid_isbn_13", raw
        for bad_asin in ("b0drtest01", "B0DRTEST0", "B0DRTEST0!"):
            st, _, _, raw, js = admin.req("POST", "/api/admin/author/books", {
                "title": "Bad ASIN", "slug": "bad-asin", "author_id": author_id, "asin": bad_asin, "list_price": "14.99"
            })
            assert st == 422 and js["reason"] == "invalid_asin", (bad_asin, raw)

        # Reserved prefix collision -> 409
        for res_slug in ("admin", "shop", "api", "_health", "_ready"):
            st, _, _, raw, _ = admin.req("POST", "/api/admin/author/books", {
                "title": "Reserved", "slug": res_slug, "author_id": author_id, "list_price": "14.99"
            })
            assert st == 409, (res_slug, st, raw)
        print("  OK: ADR-025c 422 float/exponent/ISBN-13/ASIN guards & reserved prefix 409 verified.")

        print("[5/10] Testing Series, Book, Chapter CRUD, atomic reordering & XSS-safe JSON-LD...")
        st, _, _, raw, ser_res = admin.req("POST", "/api/admin/author/series", {
            "title": "Iron District </script><script>alert(1)</script>",
            "slug": "iron-district",
            "author_id": author_id,
            "genre_slug": "urban-fiction",
            "reading_order_mode": "chronological",
            "total_planned_books": 3,
            "status": "published",
        })
        assert st == 201, raw
        series_id = ser_res["series"]["id"]

        st, _, _, raw, b1_res = admin.req("POST", "/api/admin/author/books", {
            "title": "Night Ledger </script><script>alert(1)</script>",
            "slug": "night-ledger",
            "author_id": author_id,
            "series_id": series_id,
            "series_position": 2,
            "subtitle": "Book One",
            "isbn_13": "978-0-306-40615-7",
            "asin": "B0DRTEST01",
            "edition_format": "paperback",
            "page_count": 284,
            "word_count": 72000,
            "genre_slug": "urban-fiction",
            "blurb": "Street thriller </script> safe blurb.",
            "list_price": "14.99",
            "royalty_rate": "70.00",
            "status": "published",
        })
        assert st == 201, raw
        b1 = b1_res["book"]
        assert b1["list_price"] == "14.99" and b1["royalty_rate"] == "70.00" and b1["isbn_13"] == "9780306406157"

        st, _, _, raw, b2_res = admin.req("POST", "/api/admin/author/books", {
            "title": "Cold Pavement",
            "slug": "cold-pavement",
            "author_id": author_id,
            "series_id": series_id,
            "series_position": 1,
            "edition_format": "ebook",
            "list_price": "4.99",
            "royalty_rate": "70.00",
            "status": "published",
        })
        assert st == 201, raw
        b2 = b2_res["book"]

        # Atomic series reorder: b1 -> pos 1, b2 -> pos 2
        st, _, _, raw, ro_res = admin.req("POST", "/api/admin/author/series/reorder", {
            "series_id": series_id,
            "book_ids": [b1["id"], b2["id"]],
        })
        assert st == 200 and ro_res["books"][0]["id"] == b1["id"] and ro_res["books"][0]["series_position"] == 1, raw

        # XSS-safe JSON-LD on /books/night-ledger & /series/iron-district
        st, _, _, b_html, _ = ct.http_req(port, "GET", "/books/night-ledger")
        assert st == 200 and "<div" not in b_html.lower()
        assert "</script><script>alert(1)</script>" not in b_html
        assert '\\u003c/script\\u003e' in b_html and '"price":"14.99"' in b_html, b_html[:800]

        st, _, _, s_html, _ = ct.http_req(port, "GET", "/series/iron-district")
        assert st == 200 and "<div" not in s_html.lower()
        assert "</script><script>alert(1)</script>" not in s_html
        assert '"@type":"BookSeries"' in s_html and '"price":"14.99"' in s_html, s_html[:800]
        print("  OK: XSS-safe schema.org/Book & BookSeries JSON-LD and atomic series reorder verified.")

        print("[6/10] Testing sample Web Reader (is_sample=1 vs 0) & chapter reorder...")
        st, _, _, raw, c1_res = admin.req("POST", "/api/admin/author/chapters", {
            "book_id": b1["id"],
            "title": "Chapter One: Rain on 5th",
            "slug": "rain-on-5th",
            "chapter_number": 1,
            "is_sample": True,
            "word_count": 1800,
            "reading_minutes": 7,
            "cliffhanger_hook": "The vault was already open.",
            "body_html": "Rain hammered the alley concrete.",
            "status": "published",
        })
        assert st == 201, raw
        st, _, _, raw, c2_res = admin.req("POST", "/api/admin/author/chapters", {
            "book_id": b1["id"],
            "title": "Chapter Two: Locked Door",
            "slug": "locked-door",
            "chapter_number": 2,
            "is_sample": False,
            "body_html": "Private chapter.",
            "status": "published",
        })
        assert st == 201, raw

        st, _, _, r_html, _ = ct.http_req(port, "GET", "/books/night-ledger/sample/rain-on-5th")
        assert st == 200 and "Rain hammered the alley concrete." in r_html and "<div" not in r_html.lower(), r_html
        assert ct.http_req(port, "GET", "/books/night-ledger/sample/locked-door")[0] == 404
        print("  OK: Sample Web Reader & non-sample 404 isolation verified.")

        print("[7/10] Testing slug_history 301 redirect & use cache invalidation...")
        st, _, _, raw, _ = admin.req("PUT", f"/api/admin/author/books/{b1['id']}", {"slug": "night-ledger-v2"})
        assert st == 200, raw
        st, hdrs, _, _, _ = ct.http_req(port, "GET", "/books/night-ledger")
        assert st == 301 and hdrs.get("location") == "/books/night-ledger-v2", (st, hdrs)
        st, _, _, b2_html, _ = ct.http_req(port, "GET", "/books/night-ledger-v2")
        assert st == 200 and '"price":"14.99"' in b2_html
        print("  OK: slug_history 301 redirect & cache invalidation verified.")

        print("[8/10] Testing direct v1.1.0 Commerce linkage (LULU-USPS-001, download_grants & 409 price_changed)...")
        # Author role lacks commerce:manage -> 403
        assert author_u.req("POST", f"/api/admin/author/books/{b1['id']}/sync-product", {})[0] == 403
        # Disallowed carrier UPS -> 422 LULU-USPS-001
        st, _, _, raw, _ = admin.req("POST", f"/api/admin/author/books/{b1['id']}/sync-product", {"carrier": "ups"})
        assert st == 422 and "LULU-USPS-001" in raw, raw
        # Valid LULU-USPS-001 sync -> 200
        st, _, _, raw, sync_phys = admin.req("POST", f"/api/admin/author/books/{b1['id']}/sync-product", {
            "carrier": "lulu_direct", "lulu_sku": "LULU-USPS-001", "weight_g": 360, "stock_qty": 20
        })
        assert st == 200 and sync_phys["product"]["price"] == "14.99" and sync_phys["product"]["lulu_sku"] == "LULU-USPS-001", raw

        # Enable commerce & upload PDF for digital ebook b2
        st, _, _, raw, _ = admin.req("PUT", "/api/admin/commerce/settings", {
            "commerce_enabled": True,
            "currency": "USD",
            "guest_checkout": True,
            "payment_redirect_allowlist": "payments.example.com",
            "payment_redirect_template": "https://payments.example.com/pay?o={order_number}&a={amount}&c={currency}&r={return_url}",
        })
        assert st == 200, raw
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
        st, _, _, raw, med_res = admin.req("POST", "/api/media/upload", {
            "filename": "cold-pavement.pdf", "mime_type": "application/pdf",
            "data_base64": base64.b64encode(pdf_bytes).decode("ascii"),
            "alt_text": "Cold Pavement eBook", "is_decorative": False,
        })
        assert st == 201, raw
        st, _, _, raw, sync_dig = admin.req("POST", f"/api/admin/author/books/{b2['id']}/sync-product", {
            "kind": "digital", "digital_media_id": med_res["media"]["id"], "download_limit": 2, "expiry_hours": 48,
        })
        assert st == 200 and sync_dig["product"]["kind"] == "digital" and sync_dig["product"]["price"] == "4.99", raw
        dig_pid = sync_dig["product"]["id"]

        # Shopper checkout -> webhook -> hashed download_grant + no-store
        sh = ct.ShopperClient(port)
        sh.init_session()
        sh.post("/api/commerce/cart", {"action": "add", "product_id": dig_pid, "qty": 1})
        st, _, _, raw, chk = sh.post("/api/commerce/checkout", {"email": "buyer@example.com", "display_name": "Buyer"}, headers={"Idempotency-Key": "author_dig_chk_001"})
        assert st == 201 and chk["total"] == "4.99", raw
        ev_body = json.dumps({"type": "payment.succeeded", "order_number": chk["order_number"], "amount": "4.99", "currency": "USD", "payment_ref": "pay_auth_1"})
        st, _, _, raw, _ = ct.http_req(port, "POST", "/api/commerce/webhooks/payment", raw_body=ev_body, headers=ct.sign_webhook(secret, "evt_auth_1", int(time.time()), ev_body))
        assert st == 202, raw
        ohtml = ""
        hdrs = {}
        for _ in range(20):
            time.sleep(0.2)
            st, hdrs, _, ohtml, _ = ct.http_req(port, "GET", chk["return_url"])
            if st == 200 and "/api/commerce/download/" in ohtml:
                break
        assert st == 200 and "/api/commerce/download/" in ohtml and "no-store" in hdrs.get("cache-control", ""), ohtml
        dl_tok = ohtml.split("/api/commerce/download/", 1)[1].split('"', 1)[0]
        st, dhdrs, _, d_raw, _ = ct.http_req(port, "GET", f"/api/commerce/download/{dl_tok}")
        assert st == 200 and "no-store" in dhdrs.get("cache-control", "") and base64.b64decode(d_raw) == pdf_bytes

        # Price-change protection: add b2 to a new cart at 4.99, raise book price to 6.99 + sync-product -> checkout gets 409 price_changed
        sh2 = ct.ShopperClient(port)
        sh2.init_session()
        sh2.post("/api/commerce/cart", {"action": "add", "product_id": dig_pid, "qty": 1})
        assert admin.req("PUT", f"/api/admin/author/books/{b2['id']}", {"list_price": "6.99"})[0] == 200
        assert admin.req("POST", f"/api/admin/author/books/{b2['id']}/sync-product", {"kind": "digital", "digital_media_id": med_res["media"]["id"]})[0] == 200
        st, _, _, raw, _ = sh2.post("/api/commerce/checkout", {"email": "buyer2@example.com"}, headers={"Idempotency-Key": "author_price_chg_01"})
        assert st == 409 and "price_changed" in raw, raw
        print("  OK: LULU-USPS-001, digital download_grants, and 409 price_changed verified.")

        print("[9/10] Testing Bestseller Radar bridge, 10-way concurrent import race (1x 201, 9x 409) & readability audit...")
        st, _, _, raw, rq = admin.req("POST", "/api/admin/author/radar/query", {"genre_slug": "urban-fiction", "price_tier_usd": "14.99"})
        assert st == 200 and rq["radar_plan_id"].startswith("rplan-") and MockGroxyHandler.last_radar_req["target_consumer"] == "grablab_cms", raw

        import_payload = {
            "radar_plan_id": rq["radar_plan_id"],
            "approval_token": rq["approval_token"],
            "payload_sha256": rq["payload_sha256"],
            "canonical_payload": rq["canonical_payload"],
            "genre_slug": "urban-fiction",
            "target_type": "book",
            "title": "Radar Imported Book",
            "slug": "radar-imported-book",
            "list_price": "14.99",
            "status": "published",  # Must be ignored/overridden to draft!
        }

        def fire_import():
            return admin.req("POST", "/api/admin/author/radar/import", import_payload)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            futs = [ex.submit(fire_import) for _ in range(10)]
            results = [f.result() for f in futs]

        statuses = [r[0] for r in results]
        assert statuses.count(201) == 1 and statuses.count(409) == 9, f"Expected 1x 201 + 9x 409, got {statuses}"
        winner = [r[4] for r in results if r[0] == 201][0]
        assert winner["status_enforced"] == "draft" and winner["entry"]["status"] == "draft", winner

        # Replay after completion -> 409
        assert admin.req("POST", "/api/admin/author/radar/import", import_payload)[0] == 409

        # Readability audit bridge
        st, _, _, raw, ra = admin.req("POST", "/api/admin/author/readability-audit", {
            "prose": "He walked fast. The rain fell hard.",
            "genre_slug": "urban-fiction",
            "chapter_id": c1_res["chapter"]["id"],
        })
        assert st == 200 and ra["clarity_score"] == 88, raw
        print("  OK: Radar bridge, 10-way atomic 201/409 import race, draft enforcement & readability audit verified.")

        print("[10/10] Testing additive MCP tools (`list_author_catalog`, `create_book_draft`)...")
        st, _, _, raw, tools_js = ct.http_req(port, "GET", "/api/mcp/tools", headers={"Authorization": f"Bearer {mcp_tok}"})
        assert st == 200
        tool_names = {t["name"] for t in tools_js["tools"]}
        assert {"list_author_catalog", "create_book_draft"}.issubset(tool_names), tool_names

        st, _, _, raw, cat_js = ct.http_req(port, "POST", "/api/mcp/tools/list_author_catalog", body={}, headers={"Authorization": f"Bearer {mcp_tok}"})
        assert st == 200 and len(cat_js["books"]) >= 2, raw

        # MCP create_book_draft float rejected via JSON-RPC with -32602
        st, _, _, raw, rpc_err = ct.http_req(port, "POST", "/api/mcp", body={
            "jsonrpc": "2.0", "id": 99, "method": "tools/call",
            "params": {"name": "create_book_draft", "arguments": {"title": "Float MCP", "slug": "float-mcp", "list_price": 12.99}},
        }, headers={"Authorization": f"Bearer {mcp_tok}"})
        assert st == 200 and rpc_err["result"]["isError"] is True and rpc_err["result"]["errorCode"] == -32602, raw

        st, _, _, raw, mcp_bk = ct.http_req(port, "POST", "/api/mcp/tools/create_book_draft", body={
            "title": "MCP Draft Novel",
            "slug": "mcp-draft-novel",
            "list_price": "9.99",
            "royalty_rate": "70.00",
            "isbn_13": "9780306406157",
            "asin": "B0MCP00001",
            "chapters": [{"title": "Opening", "slug": "mcp-open", "chapter_number": 1, "is_sample": True}],
        }, headers={"Authorization": f"Bearer {mcp_tok}"})
        assert st == 201 and mcp_bk["status_enforced"] == "draft" and mcp_bk["book"]["status"] == "draft" and mcp_bk["chapters"][0]["status"] == "draft", raw
        print("  OK: Additive MCP tools & draft enforcement verified.")

        print("\nALL GRABLAB CMS v1.4.0 AUTHOR MODE TESTS PASSED (100%)!")
    finally:
        ct.stop_server(proc)
        if mock_srv:
            mock_srv.shutdown()
            mock_srv.server_close()
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
