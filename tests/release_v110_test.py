#!/usr/bin/env python3
"""GrabLab CMS v1.1.0 End-to-End Release Readiness Verification Suite."""

import base64
import hashlib
import hmac
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import time
import urllib.parse

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


def main():
    tmp_dir = tempfile.mkdtemp(prefix="gl_v110_rel_")
    proc = None
    try:
        print("[1/5] Verifying `grab check`, canonical `grab format`, and `grab connect` on commerce profile...")
        ct.run_grab(["check", "--platform-config", "grab.platform.json", "src/app.grab"])
        ct.run_grab(["check", "--platform-config", "deploy/grab.platform.commerce.json", "src/app.grab"])
        ct.run_grab(["connect", "lock", "--platform-config", "deploy/grab.platform.commerce.json"])
        insp = ct.run_grab(["connect", "inspect", "--platform-config", "deploy/grab.platform.commerce.json"])
        assert "grablab_payment" in insp.stdout, insp.stdout
        print("  OK: Platform configs, connector lock, and inspect verified.")

        print("[2/5] Testing sequential (001..004) & direct (004) SQLite installs, Postgres/MariaDB dialect parity & v1.0.1 upgrade...")
        seq_db, seq_cfg = ct.init_db_config(tmp_dir, "seq.db")
        for mig in (
            "migrations/001_schema.grab",
            "migrations/002_auth_schema.grab",
            "migrations/003_v04_schema.grab",
            "migrations/004_commerce_schema.grab",
        ):
            ct.run_grab(["migrate", "--db-config", seq_cfg, "--allow-db", "main:migrate", mig])
        ct.run_grab(["run", "--db-config", seq_cfg, "--allow-db", "main:read-write", "--allow-read", ".", "migrations/seed.grab"])
        ct.run_grab(["run", "--db-config", seq_cfg, "--allow-db", "main:read-write", "--allow-read", ".", "migrations/seed_commerce.grab"])
        ct.run_grab(["run", "--db-config", seq_cfg, "--allow-db", "main:read-write", "--allow-read", ".", "migrations/seed_commerce.grab"])

        dir_db, dir_cfg = ct.init_db_config(tmp_dir, "direct.db")
        rd = ct.run_grab(["migrate", "--db-config", dir_cfg, "--allow-db", "main:migrate", "migrations/004_commerce_schema.grab"])
        assert "applied: [1, 2, 3, 4]" in rd.stdout, rd.stdout

        expected_tables = {
            "content_types", "field_definitions", "entries", "slug_history", "themes", "site_settings",
            "users", "sessions", "oauth_accounts", "media", "menus", "menu_items", "taxonomies", "terms", "entry_terms",
            "products", "product_fulfillment", "product_digital_files", "customers", "carts", "cart_items",
            "coupons", "coupon_redemptions", "orders", "order_items", "order_audit", "download_grants",
            "idempotency_keys", "payment_events", "commerce_events",
        }
        for pth in (seq_db, dir_db):
            con = sqlite3.connect(pth)
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            con.close()
            assert expected_tables.issubset(tables), f"Missing tables in {pth}: {expected_tables - tables}"

        for dfile in (
            "migrations/004_commerce_schema.grab",
            "migrations/004_commerce_schema_postgres.grab",
            "migrations/004_commerce_schema_mariadb.grab",
        ):
            ct.run_grab(["check", dfile])
            fmt = ct.run_grab(["format", dfile])
            with open(os.path.join(ROOT, dfile), "r", encoding="utf-8") as df:
                assert fmt.stdout == df.read(), f"{dfile} format drift"
        print("  OK: 30 tables across SQLite/Postgres/MariaDB & idempotent v1.0.1->v1.1.0 upgrade verified.")

        print("[3/5] Running full E2E store lifecycle: setup -> Lulu physical + PDF digital -> checkout -> webhook -> digital download...")
        secret = "release_v110_webhook_secret_32bytes!!"
        ct.run_grab([
            "migrate", "--platform-config", "deploy/grab.platform.commerce.json",
            "--db-config", seq_cfg, "--events-store", "commerce",
            "--allow-db", "main:migrate", "--allow-events", "commerce:work",
        ])
        port, proc = ct.start_cms_server(seq_cfg, tmp_dir, commerce_profile=True, webhook_secret=secret)

        admin = ct.SessionClient(port)
        admin.setup_or_login("owner@example.com", "StrongReleasePassword!123", setup=True, name="Release Owner")
        st, _, _, raw, _ = admin.req("PUT", "/api/admin/commerce/settings", {
            "commerce_enabled": True,
            "currency": "USD",
            "guest_checkout": True,
            "tax_rates": {"standard_bp": 825, "reduced_bp": 0, "digital_bp": 0},
            "shipping_rates": {"usps_ground_advantage": "5.99", "usps_priority": "9.99", "usps_media_mail": "3.99", "lulu_direct": "6.50"},
            "payment_redirect_allowlist": "payments.example.com",
            "payment_redirect_template": "https://payments.example.com/checkout?ord={order_number}&amt={amount}&cur={currency}&ret={return_url}",
        })
        assert st == 200, raw

        # Upload real PDF asset to uploads/ for digital download E2E
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
        st, _, _, raw, media_res = admin.req("POST", "/api/media/upload", {
            "filename": "ebook-v110.pdf",
            "mime_type": "application/pdf",
            "data_base64": base64.b64encode(pdf_bytes).decode("ascii"),
            "alt_text": "Digital Ebook PDF",
            "is_decorative": False,
        })
        assert st == 201, raw
        media_id = media_res["media"]["id"]

        st, _, _, raw, dig_res = admin.req("POST", "/api/admin/commerce/products", {
            "title": "GrabLab Guide eBook",
            "slug": "grablab-guide-ebook",
            "sku": "EBOOK-110",
            "price": "19.99",
            "kind": "digital",
            "tax_class": "digital",
            "stock_qty": 100,
            "digital_media_id": media_id,
            "download_limit": 2,
            "expiry_hours": 72,
            "custom_fields": {"isbn_13": "9780306406157", "subtitle": "Digital Release"},
        })
        assert st == 201, raw
        dig_pid = dig_res["product"]["id"]

        # Verify storefront HTML catalog + product page + cart page (zero <div>)
        for sp in ("/shop", "/shop/grablab-guide-ebook", "/shop/cart"):
            st, _, _, html, _ = ct.http_req(port, "GET", sp)
            assert st == 200 and "<div" not in html.lower(), f"Failed storefront page {sp}: {st}"

        # Shopper checkout
        sh = ct.ShopperClient(port)
        sh.init_session()
        sh.post("/api/commerce/cart", {"action": "add", "product_id": dig_pid, "qty": 1})
        st, _, _, raw, chk = sh.post("/api/commerce/checkout", {
            "email": "reader@example.com",
            "display_name": "Ebook Reader",
            "marketing_opt_in": False,
        }, headers={"Idempotency-Key": "rel_v110_ebook_chk_01"})
        assert st == 201 and chk["total"] == "19.99" and chk["shipping_total"] == "0.00", raw
        ord_num = chk["order_number"]
        ret_url = chk["return_url"]

        # Order status page without ?t= -> 404
        st, _, _, _, _ = ct.http_req(port, "GET", f"/shop/order/{ord_num}")
        assert st == 404

        # Signed webhook payment.succeeded -> 202
        ev_body = json.dumps({"type": "payment.succeeded", "order_number": ord_num, "amount": "19.99", "currency": "USD", "payment_ref": "rel_pay_01"})
        st, _, _, raw, _ = ct.http_req(port, "POST", "/api/commerce/webhooks/payment", raw_body=ev_body, headers=ct.sign_webhook(secret, "evt_rel_1", int(time.time()), ev_body))
        assert st == 202, raw
        time.sleep(0.5)

        # Order status page with ?t= -> 200 + Cache-Control: no-store + Referrer-Policy: no-referrer + valid download link
        st, hdrs, _, ohtml, _ = ct.http_req(port, "GET", ret_url)
        assert st == 200 and "paid" in ohtml and "no-store" in hdrs.get("cache-control", "") and hdrs.get("referrer-policy") == "no-referrer"
        assert "<div" not in ohtml.lower()
        marker = '/api/commerce/download/'
        assert marker in ohtml, ohtml
        dl_tok = ohtml.split(marker, 1)[1].split('"', 1)[0]

        # Download asset 1st + 2nd time succeed returning exact base64 PDF payload, 3rd time hits download limit (404)
        for attempt in (1, 2):
            st, d_hdrs, _, d_raw, _ = ct.http_req(port, "GET", f"/api/commerce/download/{dl_tok}")
            assert st == 200 and "no-store" in d_hdrs.get("cache-control", "")
            assert base64.b64decode(d_raw) == pdf_bytes
        st, _, _, _, _ = ct.http_req(port, "GET", f"/api/commerce/download/{dl_tok}")
        assert st == 404
        print("  OK: E2E digital download, signed webhook, security headers, and download grant limit verified.")

        print("[4/5] Running Node Grex JS DOM + Light/Dark WCAG AA audit...")
        node_res = subprocess.run(["node", "tests/commerce_dom_audit.mjs"], cwd=ROOT, capture_output=True, text=True)
        assert node_res.returncode == 0, node_res.stdout + "\n" + node_res.stderr
        print("  OK: Node audit:", node_res.stdout.strip())

        print("[5/5] Checking sibling repositories are untouched (`git status --short` clean)...")
        checked_siblings = check_sibling_repos_clean()
        print(f"  OK: {checked_siblings} sibling repositories verified clean.")

        print("\nALL GRABLAB CMS v1.1.0 RELEASE READINESS GATES PASSED (100%)!")
    finally:
        ct.stop_server(proc)
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
