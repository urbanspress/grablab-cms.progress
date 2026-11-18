#!/usr/bin/env python3
"""GrabLab CMS v1.4.0 End-to-End Release Readiness Verification Suite."""

import base64
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import time
from http.server import HTTPServer

import author_test as at
import commerce_test as ct

ROOT = ct.ROOT


def check_sibling_repos_clean():
    parent = os.path.dirname(ROOT)
    checked = 0
    for entry in sorted(os.listdir(parent)):
        if entry == os.path.basename(ROOT):
            continue
        p = os.path.join(parent, entry)
        if os.path.isdir(os.path.join(p, ".git")):
            res = subprocess.run(["git", "-C", p, "status", "--short"], capture_output=True, text=True)
            assert res.returncode == 0 and res.stdout.strip() == "", f"Sibling repo {entry} is dirty:\n{res.stdout}"
            checked += 1
    assert checked >= 9, f"Expected >= 9 sibling git repos, checked {checked}"
    return checked


def extract_author_tables_and_indexes(path):
    with open(path, "r", encoding="utf-8") as fh:
        txt = fh.read()
    tables = set(re.findall(r"CREATE TABLE IF NOT EXISTS\s+([a-z_]+)", txt, flags=re.IGNORECASE))
    indexes = set(re.findall(r"\bINDEX\s+(?:IF NOT EXISTS\s+)?([a-z_]+)", txt, flags=re.IGNORECASE))
    return tables, indexes


def main():
    tmp_dir = tempfile.mkdtemp(prefix="gl_v140_rel_")
    proc = None
    groxy_srv = None
    try:
        print("[1/5] Verifying `grab check` & canonical `grab format` parity across v1.4.0 files...")
        ct.run_grab(["check", "--platform-config", "grab.platform.json", "src/app.grab"])
        ct.run_grab(["check", "--platform-config", "deploy/grab.platform.commerce.json", "src/app.grab"])
        ct.run_grab(["connect", "lock", "--platform-config", "deploy/grab.platform.commerce.json"])
        insp = ct.run_grab(["connect", "inspect", "--platform-config", "deploy/grab.platform.commerce.json"])
        assert "grablab_payment" in insp.stdout, insp.stdout

        format_files = (
            "src/app.grab",
            "migrations/seed.grab",
            "migrations/seed_author.grab",
            "migrations/005_author_schema.grab",
            "migrations/005_author_schema_postgres.grab",
            "migrations/005_author_schema_mariadb.grab",
        )
        for gf in format_files:
            if gf != "src/app.grab":
                ct.run_grab(["check", gf])
            fmt = ct.run_grab(["format", gf])
            with open(os.path.join(ROOT, gf), "r", encoding="utf-8") as fh:
                assert fmt.stdout == fh.read(), f"{gf} format drift"
        print("  OK: Platform configs, connector lock, grab check, and canonical formatting verified.")

        print("[2/5] Testing sequential (001..005) & direct (005) SQLite installs, Postgres/MariaDB dialect parity & seed idempotency...")
        seq_db, seq_cfg = ct.init_db_config(tmp_dir, "seq.db")
        for mig in (
            "migrations/001_schema.grab",
            "migrations/002_auth_schema.grab",
            "migrations/003_v04_schema.grab",
            "migrations/004_commerce_schema.grab",
            "migrations/005_author_schema.grab",
        ):
            ct.run_grab(["migrate", "--db-config", seq_cfg, "--allow-db", "main:migrate", mig])
        ct.run_grab(["run", "--db-config", seq_cfg, "--allow-db", "main:read-write", "--allow-read", ".", "migrations/seed.grab"])
        ct.run_grab(["run", "--db-config", seq_cfg, "--allow-db", "main:read-write", "--allow-read", ".", "migrations/seed_commerce.grab"])
        ct.run_grab(["run", "--db-config", seq_cfg, "--allow-db", "main:read-write", "--allow-read", ".", "migrations/seed_author.grab"])
        ct.run_grab(["run", "--db-config", seq_cfg, "--allow-db", "main:read-write", "--allow-read", ".", "migrations/seed_author.grab"])

        dir_db, dir_cfg = ct.init_db_config(tmp_dir, "direct.db")
        rd = ct.run_grab(["migrate", "--db-config", dir_cfg, "--allow-db", "main:migrate", "migrations/005_author_schema.grab"])
        assert "applied: [1, 2, 3, 4, 5]" in rd.stdout, rd.stdout

        expected_tables = {
            "content_types", "field_definitions", "entries", "slug_history", "themes", "site_settings",
            "users", "sessions", "oauth_accounts", "media", "menus", "menu_items", "taxonomies", "terms", "entry_terms",
            "products", "product_fulfillment", "product_digital_files", "customers", "carts", "cart_items",
            "coupons", "coupon_redemptions", "orders", "order_items", "order_audit", "download_grants",
            "idempotency_keys", "payment_events", "commerce_events",
            "authors", "series", "books", "chapters", "author_radar_imports",
        }
        assert len(expected_tables) == 35
        for pth in (seq_db, dir_db):
            con = sqlite3.connect(pth)
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            con.close()
            assert expected_tables.issubset(tables), f"Missing tables in {pth}: {expected_tables - tables}"

        sql_t, sql_i = extract_author_tables_and_indexes(os.path.join(ROOT, "migrations/005_author_schema.grab"))
        pg_t, pg_i = extract_author_tables_and_indexes(os.path.join(ROOT, "migrations/005_author_schema_postgres.grab"))
        ma_t, ma_i = extract_author_tables_and_indexes(os.path.join(ROOT, "migrations/005_author_schema_mariadb.grab"))
        assert sql_t == pg_t == ma_t == expected_tables, "Dialect table mismatch across SQLite/Postgres/MariaDB"
        assert sql_i == pg_i == ma_i and len(sql_i) > 0, "Dialect index mismatch across SQLite/Postgres/MariaDB"
        print("  OK: 35 tables & indexes verified across SQLite/Postgres/MariaDB + idempotent seed_author.grab.")

        print("[3/5] Running full E2E v1.4.0 lifecycle (Radar -> Book -> Sample Reader -> Commerce Digital Webhook)...")
        groxy_port = ct.find_free_port()
        groxy_srv = HTTPServer(("127.0.0.1", groxy_port), at.MockGroxyHandler)
        groxy_thr = threading.Thread(target=groxy_srv.serve_forever, daemon=True)
        groxy_thr.start()

        secret = "release_v140_webhook_secret_32bytes!!"
        ct.run_grab([
            "migrate", "--platform-config", "deploy/grab.platform.commerce.json",
            "--db-config", seq_cfg, "--events-store", "commerce",
            "--allow-db", "main:migrate", "--allow-events", "commerce:work",
        ])
        port, proc = at.start_author_server(seq_cfg, tmp_dir, groxy_port, secret)

        admin = ct.SessionClient(port)
        admin.setup_or_login("owner@example.com", "StrongRelease140!Pass", setup=True, name="Release Author Owner")
        st, _, _, raw, _ = admin.req("PUT", "/api/admin/author/settings", {
            "author_mode_enabled": True,
            "groxy_ai_origin": f"http://127.0.0.1:{groxy_port}",
        })
        assert st == 200, raw

        st, _, _, raw, r_res = admin.req("POST", "/api/admin/author/radar/query", {
            "genre_slug": "sci-fi-thriller",
            "price_tier_usd": "6.99",
        })
        assert st == 200 and r_res["ok"] is True, raw

        st, _, _, raw, imp = admin.req("POST", "/api/admin/author/radar/import", {
            "radar_plan_id": r_res["radar_plan_id"],
            "genre_slug": r_res["genre_slug"],
            "target_type": "book",
            "approval_token": r_res["approval_token"],
            "payload_sha256": r_res["payload_sha256"],
            "title": "Orbital Horizon Radar Brief",
        })
        assert st == 201 and imp["status_enforced"] == "draft" and imp["entry"]["status"] == "draft", raw

        st, _, _, raw, a_res = admin.req("POST", "/api/admin/author/authors", {
            "pen_name": "Elena Vance",
            "slug": "elena-vance",
            "status": "published",
        })
        assert st == 201, raw

        st, _, _, raw, b_res = admin.req("POST", "/api/admin/author/books", {
            "author_id": a_res["author"]["id"],
            "title": "Orbital Horizon",
            "slug": "orbital-horizon",
            "status": "published",
            "isbn_13": "9780306406157",
            "asin": "B09XYZ1234",
            "list_price": "6.99",
            "royalty_rate": "70.00",
            "blurb": "Deep orbit suspense.",
        })
        assert st == 201, raw
        book_id = b_res["book"]["id"]

        st, _, _, raw, _ = admin.req("POST", "/api/admin/author/chapters", {
            "book_id": book_id,
            "title": "Chapter 1: Signal",
            "slug": "ch-1-signal",
            "chapter_number": 1,
            "is_sample": True,
            "status": "published",
            "body_html": "<p>First transmission arrived at midnight.</p>",
        })
        assert st == 201, raw

        st, _, _, b_html, _ = ct.http_req(port, "GET", "/books/orbital-horizon")
        assert st == 200 and "schema.org" in b_html and "Book" in b_html and "<div" not in b_html.lower(), b_html
        st, _, _, rd_html, _ = ct.http_req(port, "GET", "/books/orbital-horizon/sample/ch-1-signal")
        assert st == 200 and "First transmission arrived at midnight." in rd_html and "<div" not in rd_html.lower(), rd_html

        st, _, _, raw, _ = admin.req("PUT", "/api/admin/commerce/settings", {
            "commerce_enabled": True,
            "currency": "USD",
            "guest_checkout": True,
            "payment_redirect_allowlist": "payments.example.com",
            "payment_redirect_template": "https://payments.example.com/pay?o={order_number}&a={amount}&c={currency}&r={return_url}",
        })
        assert st == 200, raw
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
        st, _, _, raw, mres = admin.req("POST", "/api/media/upload", {
            "filename": "orbital-horizon.pdf",
            "mime_type": "application/pdf",
            "data_base64": base64.b64encode(pdf_bytes).decode("ascii"),
            "alt_text": "Orbital Horizon eBook",
            "is_decorative": False,
        })
        assert st == 201, raw
        st, _, _, raw, sres = admin.req("POST", f"/api/admin/author/books/{book_id}/sync-product", {
            "kind": "digital",
            "digital_media_id": mres["media"]["id"],
            "download_limit": 2,
            "expiry_hours": 48,
        })
        assert st == 200 and sres["product"]["price"] == "6.99", raw

        sh = ct.ShopperClient(port)
        sh.init_session()
        sh.post("/api/commerce/cart", {"action": "add", "product_id": sres["product"]["id"], "qty": 1})
        st, _, _, raw, chk = sh.post("/api/commerce/checkout", {
            "email": "rel140buyer@example.com",
            "display_name": "Rel140 Buyer",
        }, headers={"Idempotency-Key": "rel_v140_chk_0001"})
        assert st == 201 and chk["total"] == "6.99", raw

        ev_body = json.dumps({"type": "payment.succeeded", "order_number": chk["order_number"], "amount": "6.99", "currency": "USD", "payment_ref": "pay_rel_140"})
        st, _, _, raw, _ = ct.http_req(port, "POST", "/api/commerce/webhooks/payment", raw_body=ev_body, headers=ct.sign_webhook(secret, "evt_rel_140", int(time.time()), ev_body))
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
        assert st == 200 and base64.b64decode(d_raw) == pdf_bytes
        print("  OK: Full E2E v1.4.0 lifecycle verified.")

        print("[4/5] Running Node Grex JS DOM + Light/Dark WCAG AA audits...")
        for audit_script in ("tests/commerce_dom_audit.mjs", "tests/author_dom_audit.mjs"):
            node_res = subprocess.run(["node", audit_script], cwd=ROOT, capture_output=True, text=True)
            assert node_res.returncode == 0, node_res.stdout + "\n" + node_res.stderr
            print(f"  OK: {audit_script}:", node_res.stdout.strip())

        print("[5/5] Checking sibling repositories are untouched (`git status --short` clean)...")
        checked_siblings = check_sibling_repos_clean()
        print(f"  OK: {checked_siblings} sibling repositories verified clean.")

        print("\nALL GRABLAB CMS v1.4.0 RELEASE READINESS GATES PASSED (100%)!")
    finally:
        ct.stop_server(proc)
        if groxy_srv is not None:
            groxy_srv.shutdown()
            groxy_srv.server_close()
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
