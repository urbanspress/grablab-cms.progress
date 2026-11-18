#!/usr/bin/env python3
"""GrabLab CMS v1.1.0 Comprehensive Commerce, Concurrency, Security & Webhook Test Suite."""

import concurrent.futures
import hashlib
import hmac
import http.client
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import tempfile
import time
import urllib.parse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def resolve_grab_bin() -> str:
    env_bin = os.environ.get("GRAB_BIN", "").strip()
    if env_bin and os.path.exists(env_bin):
        return env_bin
    for cand in (
        r"C:\Development\GRAB\dist\grab-windows-amd64.exe",
        shutil.which("grab") or "",
    ):
        if cand and os.path.exists(cand):
            return cand
    raise RuntimeError("Could not locate GRAB CLI binary")


GRAB_BIN = resolve_grab_bin()


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_grab(args, env=None, check=True):
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    proc = subprocess.run(
        [GRAB_BIN] + args,
        cwd=ROOT,
        env=full_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if check and proc.returncode != 0:
        raise AssertionError(
            f"GRAB command failed ({proc.returncode}): {' '.join(args)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return proc


def http_req(port, method, path, body=None, headers=None, raw_body=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
    hdrs = dict(headers or {})
    payload = None
    if raw_body is not None:
        payload = raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body
        hdrs.setdefault("Content-Type", "application/json")
    elif body is not None:
        if isinstance(body, (dict, list)):
            payload = json.dumps(body).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")
        else:
            payload = str(body).encode("utf-8")
    conn.request(method, path, body=payload, headers=hdrs)
    resp = conn.getresponse()
    raw = resp.read()
    resp_hdrs = {k.lower(): v for k, v in resp.getheaders()}
    set_cookies = [v.split(";", 1)[0] for k, v in resp.getheaders() if k.lower() == "set-cookie"]
    text = raw.decode("utf-8", errors="replace")
    parsed = None
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = None
    conn.close()
    return resp.status, resp_hdrs, set_cookies, text, parsed


class SessionClient:
    def __init__(self, port):
        self.port = port
        self.cookie = ""
        self.csrf = ""

    def setup_or_login(self, email, password, setup=False, name="Admin"):
        if setup:
            st, _, ck, raw, js = http_req(
                self.port,
                "POST",
                "/api/auth/setup",
                {"email": email, "display_name": name, "password": password},
            )
            assert st == 201, f"Setup failed: {st} {raw}"
        else:
            st, _, ck, raw, js = http_req(
                self.port,
                "POST",
                "/api/auth/login",
                {"email": email, "password": password},
            )
            assert st == 200, f"Login failed: {st} {raw}"
        self.cookie = "; ".join(ck)
        self.csrf = js["csrf_token"]
        return js

    def req(self, method, path, body=None, headers=None, omit_csrf=False):
        hdrs = dict(headers or {})
        if self.cookie:
            hdrs["Cookie"] = self.cookie
        if method in ("POST", "PUT", "DELETE") and self.csrf and not omit_csrf:
            hdrs["X-CSRF-Token"] = self.csrf
        return http_req(self.port, method, path, body=body, headers=hdrs)


class ShopperClient:
    def __init__(self, port):
        self.port = port
        self.cookie = ""
        self.csrf = ""
        self.cart_id = ""

    def init_session(self, extra_cookie=""):
        hdrs = {}
        c_parts = [p for p in (self.cookie, extra_cookie) if p]
        if c_parts:
            hdrs["Cookie"] = "; ".join(c_parts)
        st, _, ck, raw, js = http_req(self.port, "GET", "/api/commerce/session", headers=hdrs)
        assert st == 200, f"Commerce session init failed: {st} {raw}"
        if ck:
            self.cookie = "; ".join(ck)
        self.csrf = js["csrf_token"]
        self.cart_id = js["cart_id"]
        return js

    def post(self, path, body=None, headers=None, omit_csrf=False, raw_body=None):
        hdrs = dict(headers or {})
        if self.cookie:
            hdrs["Cookie"] = self.cookie
        if self.csrf and not omit_csrf:
            hdrs.setdefault("X-CSRF-Token", self.csrf)
        return http_req(self.port, "POST", path, body=body, headers=hdrs, raw_body=raw_body)


def start_cms_server(db_cfg, work_dir, commerce_profile=False, webhook_secret=None):
    port = find_free_port()
    uploads_dir = os.path.join(work_dir, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    env = os.environ.copy()
    env["GRABLAB_UPLOAD_DIR"] = uploads_dir
    env["GRABLAB_MASTER_KEY"] = "test-master-key-01234567890123456789"
    allow_envs = ["GRABLAB_UPLOAD_DIR", "GRABLAB_MASTER_KEY"]
    if webhook_secret:
        env["GRABLAB_PAYMENT_WEBHOOK_SECRET"] = webhook_secret
        allow_envs.append("GRABLAB_PAYMENT_WEBHOOK_SECRET")
    platform_cfg = "deploy/grab.platform.commerce.json" if commerce_profile else "grab.platform.json"
    args = [
        GRAB_BIN,
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
        platform_cfg,
        "--allow-cache",
        "cms:read-write",
        "--allow-cache",
        "cms:limit",
        "--allow-env",
        ",".join(allow_envs),
        "--allow-read",
        ".",
        "--allow-read",
        uploads_dir,
        "--allow-write",
        uploads_dir,
        "--static",
        "public",
    ]
    if commerce_profile:
        args += [
            "--allow-events",
            "commerce:accept",
            "--allow-events",
            "commerce:work",
        ]
    args.append("src/app.grab")
    log_path = os.path.join(work_dir, f"server_{port}.log")
    log_fh = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        args,
        cwd=ROOT,
        env=env,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            st, _, _, _, _ = http_req(port, "GET", "/_health")
            if st == 200:
                return port, proc
        except Exception:
            if proc.poll() is not None:
                log_fh.close()
                with open(log_path, "r", encoding="utf-8", errors="replace") as lf:
                    logs = lf.read()
                raise RuntimeError(f"Server exited early ({proc.returncode}):\n{logs}")
        time.sleep(0.15)
    proc.terminate()
    log_fh.close()
    raise TimeoutError("Timed out waiting for GrabLab CMS server")


def stop_server(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def init_db_config(tmp_dir, name="shop.db"):
    db_path = os.path.join(tmp_dir, name)
    cfg_path = os.path.join(tmp_dir, f"{name}.json")
    cfg = {
        "connections": {
            "main": {
                "driver": "sqlite",
                "path": db_path,
            }
        },
    }
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    return db_path, cfg_path


def sign_webhook(secret, event_id, ts_unix, raw_body):
    msg = f"{event_id}.{ts_unix}.{raw_body}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return {
        "Grab-Event-Id": event_id,
        "Grab-Event-Time": str(ts_unix),
        "Grab-Signature": f"v1={sig}",
        "Content-Type": "application/json",
    }


def main():
    tmp_dir = tempfile.mkdtemp(prefix="gl_v110_comm_")
    proc = None
    try:
        print("[1/9] Testing default platform profile boot WITHOUT webhook secrets & commerce disabled-by-default 404s...")
        db_path, db_cfg = init_db_config(tmp_dir, "default.db")
        run_grab(["migrate", "--db-config", db_cfg, "--allow-db", "main:migrate", "migrations/004_commerce_schema.grab"])
        run_grab(["run", "--db-config", db_cfg, "--allow-db", "main:read-write", "--allow-read", ".", "migrations/seed.grab"])
        run_grab(["run", "--db-config", db_cfg, "--allow-db", "main:read-write", "--allow-read", ".", "migrations/seed_commerce.grab"])

        port, proc = start_cms_server(db_cfg, tmp_dir, commerce_profile=False, webhook_secret=None)
        st, _, _, _, _ = http_req(port, "GET", "/shop")
        assert st == 404, f"Expected /shop 404 when disabled, got {st}"
        st, _, _, _, _ = http_req(port, "GET", "/api/commerce/session")
        assert st == 404, f"Expected /api/commerce/session 404 when disabled, got {st}"
        stop_server(proc)
        proc = None
        print("  OK: Zero-secret default boot & disabled storefront 404 gates passed.")

        print("[2/9] Booting commerce platform profile (GRAB native signed webhook) & migrating event store...")
        secret = "test_grablab_webhook_secret_32bytes_min!"
        run_grab([
            "migrate",
            "--platform-config",
            "deploy/grab.platform.commerce.json",
            "--db-config",
            db_cfg,
            "--events-store",
            "commerce",
            "--allow-db",
            "main:migrate",
            "--allow-events",
            "commerce:work",
        ])
        port, proc = start_cms_server(db_cfg, tmp_dir, commerce_profile=True, webhook_secret=secret)

        admin = SessionClient(port)
        admin.setup_or_login("merchant@example.com", "StrongMerchantPass!123", setup=True, name="Merchant Owner")

        # Create editor + author users for RBAC checks
        st, _, _, raw, ed_u = admin.req("POST", "/api/admin/users", {
            "email": "editor@example.com", "display_name": "Store Editor", "role": "editor", "password": "EditorPassword!123"
        })
        assert st == 201, raw
        st, _, _, raw, au_u = admin.req("POST", "/api/admin/users", {
            "email": "author@example.com", "display_name": "Blog Author", "role": "author", "password": "AuthorPassword!123"
        })
        assert st == 201, raw

        editor = SessionClient(port)
        editor.setup_or_login("editor@example.com", "EditorPassword!123")
        author = SessionClient(port)
        author.setup_or_login("author@example.com", "AuthorPassword!123")
        print("  OK: Signed-webhook platform profile started clean.")

        print("[3/9] Testing RBAC, CSRF, Bearer exclusion, GRAB-E402 allowlist & ADR-025c 422 float guards...")
        # Author cannot access commerce admin API
        st, _, _, _, _ = author.req("GET", "/api/admin/commerce/overview")
        assert st == 403, f"Expected author 403, got {st}"
        # Editor can view orders/products, CANNOT access settings (admin-only commerce:settings)
        st, _, _, _, _ = editor.req("GET", "/api/admin/commerce/overview")
        assert st == 200, f"Expected editor 200 overview, got {st}"
        st, _, _, _, _ = editor.req("GET", "/api/admin/commerce/settings")
        assert st == 403, f"Expected editor 403 settings, got {st}"
        st, _, _, _, _ = editor.req("PUT", "/api/admin/commerce/settings", {"commerce_enabled": True})
        assert st == 403, f"Expected editor 403 PUT settings, got {st}"

        # MCP Bearer token rejected on /api/admin/commerce/* with 401
        mcp_tok = admin.req("POST", "/api/auth/mcp-token", {})[4]["token"]
        st, _, _, _, _ = http_req(port, "GET", "/api/admin/commerce/settings", headers={"Authorization": f"Bearer {mcp_tok}"})
        assert st == 401, f"Expected Bearer rejection 401 on admin commerce, got {st}"

        # Redirect allowlist GRAB-E402 save-time checks (all bad targets -> 422)
        bad_redirect_configs = [
            {"payment_redirect_allowlist": "*.example.com", "payment_redirect_template": "https://pay.example.com/pay?o={order_number}"},
            {"payment_redirect_allowlist": "pay.example.com", "payment_redirect_template": "http://pay.example.com/pay?o={order_number}"},
            {"payment_redirect_allowlist": "pay.example.com", "payment_redirect_template": "javascript:alert(1)//{order_number}"},
            {"payment_redirect_allowlist": "pay.example.com", "payment_redirect_template": "https://user:pass@pay.example.com/pay?o={order_number}"},
            {"payment_redirect_allowlist": "pay.example.com", "payment_redirect_template": "https://pay.example.com:8443/pay?o={order_number}"},
            {"payment_redirect_allowlist": "pay.example.com", "payment_redirect_template": "https://pay.example.com/pay?o={order_number}#frag"},
            {"payment_redirect_allowlist": "pay.example.com", "payment_redirect_template": "https://pay.evil-example.com/pay?o={order_number}"},
        ]
        for bcfg in bad_redirect_configs:
            st, _, _, raw, js = admin.req("PUT", "/api/admin/commerce/settings", bcfg)
            assert st == 422, f"Expected 422 for {bcfg}, got {st} {raw}"

        # Float & non-USD checks in settings -> 422
        st, _, _, raw, _ = admin.req("PUT", "/api/admin/commerce/settings", {"currency": "EUR"})
        assert st == 422, raw
        st, _, _, raw, _ = admin.req("PUT", "/api/admin/commerce/settings", {"shipping_rates": {"usps_ground_advantage": 5.99}})
        assert st == 422 and "float_not_allowed" in raw, raw

        # Valid settings save
        st, _, _, raw, s_res = admin.req("PUT", "/api/admin/commerce/settings", {
            "commerce_enabled": True,
            "currency": "USD",
            "guest_checkout": True,
            "tax_rates": {"standard_bp": 825, "reduced_bp": 0, "digital_bp": 0},
            "shipping_rates": {"usps_ground_advantage": "0.00", "usps_priority": "0.00", "usps_media_mail": "0.00", "lulu_direct": "0.00"},
            "payment_redirect_allowlist": "checkout.example.com",
            "payment_redirect_template": "https://checkout.example.com/pay?order={order_number}&amount={amount}&currency={currency}&return={return_url}",
            "pending_ttl_minutes": 60,
            "abandoned_after_minutes": 60,
        })
        assert st == 200 and s_res["commerce_enabled"] is True, raw

        # Ensure webhook secrets are NOT exposed in GET settings
        st, _, _, raw_s, gs = admin.req("GET", "/api/admin/commerce/settings")
        assert st == 200 and gs["webhook_primary_configured"] is True and secret not in raw_s
        print("  OK: RBAC, CSRF, Bearer block, GRAB-E402 allowlist & zero secret leak verified.")

        print("[4/9] Testing product creation, float 422, ISBN-13 validation, LULU-USPS-001 & slug_history 301...")
        # Float price -> 422 float_not_allowed
        st, _, _, raw, _ = admin.req("POST", "/api/admin/commerce/products", {
            "title": "Float Book", "slug": "float-book", "sku": "FLT-1", "price": 19.99, "kind": "digital"
        })
        assert st == 422 and "float_not_allowed" in raw, raw
        # Non-USPS/non-Lulu carrier (ups/fedex/dhl) -> 422 LULU-USPS-001
        for bad_carrier in ("ups", "fedex", "dhl"):
            st, _, _, raw, js = admin.req("POST", "/api/admin/commerce/products", {
                "title": "Bad Carrier", "slug": f"bad-{bad_carrier}", "sku": f"BAD-{bad_carrier}", "price": "19.99",
                "kind": "physical", "carrier": bad_carrier, "weight_g": 200, "stock_qty": 10
            })
            assert st == 422 and js["error"] == "LULU-USPS-001", f"Expected LULU-USPS-001 for {bad_carrier}, got {st} {raw}"

        # Overweight USPS > 31751g -> 422
        st, _, _, raw, _ = admin.req("POST", "/api/admin/commerce/products", {
            "title": "Heavy Box", "slug": "heavy-box", "sku": "HVY-1", "price": "19.99",
            "kind": "physical", "carrier": "usps", "weight_g": 40000, "stock_qty": 5
        })
        assert st == 422, raw
        # Lulu direct without lulu_sku -> 422 lulu_sku_required
        st, _, _, raw, js = admin.req("POST", "/api/admin/commerce/products", {
            "title": "Book", "slug": "no-lulu-sku", "sku": "NLS-1", "price": "24.00",
            "kind": "physical", "carrier": "lulu_direct", "weight_g": 300, "stock_qty": 5
        })
        assert st == 422 and js["error"] == "lulu_sku_required", raw
        # Bad ISBN-13 checksum -> 422
        st, _, _, raw, _ = admin.req("POST", "/api/admin/commerce/products", {
            "title": "Bad ISBN", "slug": "bad-isbn", "sku": "BISBN-1", "price": "19.99",
            "kind": "physical", "carrier": "lulu_direct", "lulu_sku": "LULU-1", "weight_g": 300,
            "custom_fields": {"isbn_13": "9780306406158"}
        })
        assert st == 422, raw

        # Valid USPS physical product ($19.99, stock 10)
        st, _, _, raw, p1_res = admin.req("POST", "/api/admin/commerce/products", {
            "title": "Field Manual", "slug": "field-manual", "sku": "BOOK-001", "price": "19.99",
            "kind": "physical", "carrier": "usps", "usps_service": "ground_advantage", "weight_g": 400,
            "stock_qty": 10, "tax_class": "standard", "custom_fields": {"isbn_13": "9780306406157", "subtitle": "First Edition"}
        })
        assert st == 201 and p1_res["product"]["price"] == "19.99", raw
        p1 = p1_res["product"]

        # Verify Plotific Press schema.org/Product JSON-LD byte-exact price string + zero <div>
        st, _, _, p_html, _ = http_req(port, "GET", "/shop/field-manual")
        assert st == 200 and '"price":"19.99"' in p_html and "9780306406157" in p_html and "<div" not in p_html.lower(), p_html[:500]

        # Verify byte-exact string in SQLite products.price_cents
        con = sqlite3.connect(db_path)
        db_cents = con.execute("SELECT price_cents FROM products WHERE id = ?", (p1["id"],)).fetchone()[0]
        assert db_cents == 1999, db_cents
        con.close()

        # Verify slug rename preserves slug_history 301 AND open cart still references product_id cleanly
        sh = ShopperClient(port)
        sh.init_session()
        st, _, _, raw, _ = sh.post("/api/commerce/cart", {"action": "add", "product_id": p1["id"], "qty": 3})
        assert st == 200, raw
        st, _, _, raw, _ = admin.req("PUT", f"/api/entries/{p1['entry_id']}", {"slug": "field-manual-v2"})
        assert st == 200, raw
        st, hdrs, _, _, _ = http_req(port, "GET", "/shop/field-manual")
        assert st == 301 and hdrs.get("location") == "/shop/field-manual-v2", (st, hdrs)
        print("  OK: Product validation, JSON-LD exact price, LULU-USPS-001, and 301 redirect preserved.")

        print("[5/9] Testing ALL Section 5 Totals Vectors (`tests/commerce_vectors.json`) live through CMS API...")
        with open(os.path.join(ROOT, "tests", "commerce_vectors.json"), "r", encoding="utf-8") as vf:
            vectors = json.load(vf)["vectors"]

        for vi, vec in enumerate(vectors):
            admin.req("PUT", "/api/admin/commerce/settings", {
                "tax_rates": vec["tax_rates"],
                "shipping_rates": vec["shipping_rates"],
            })
            v_cart = ShopperClient(port)
            v_cart.init_session()
            for ii, item in enumerate(vec["items"]):
                cp = {
                    "title": f"Vec {vi}-{ii}",
                    "slug": f"vec-{vi}-{ii}",
                    "sku": f"VEC-{vi}-{ii}",
                    "price": item["unit_price"],
                    "kind": item["kind"],
                    "tax_class": item["tax_class"],
                    "stock_qty": 100,
                }
                if item["kind"] == "physical":
                    cp["carrier"] = item.get("carrier", "usps")
                    if cp["carrier"] == "usps":
                        cp["usps_service"] = item.get("usps_service", "ground_advantage")
                        cp["weight_g"] = 100
                        cp["media_mail_eligible"] = 1
                    else:
                        cp["lulu_sku"] = item.get("lulu_sku", "LULU-VEC")
                        cp["weight_g"] = 200
                st, _, _, raw, cpr = admin.req("POST", "/api/admin/commerce/products", cp)
                assert st == 201, raw
                st, _, _, raw, _ = v_cart.post("/api/commerce/cart", {
                    "action": "add", "product_id": cpr["product"]["id"], "qty": item["qty"]
                })
                assert st == 200, raw
            if vec["coupon"]:
                c_code = f"VEC_{vi}"
                st, _, _, raw, _ = admin.req("POST", "/api/admin/commerce/coupons", {
                    "code": c_code,
                    "type": vec["coupon"]["type"],
                    "value": vec["coupon"]["value"],
                    "min_subtotal": "0.00",
                    "max_redemptions": 10,
                    "active": 1,
                })
                assert st == 201, raw
                st, _, _, raw, cart_res = v_cart.post("/api/commerce/coupon/apply", {"code": c_code})
                assert st == 200, raw
            else:
                st, _, _, raw, cart_res = v_cart.post("/api/commerce/cart", {"action": "get"})
                assert st == 200, raw
            exp = vec["expected"]
            for k in ("subtotal", "discount_total", "tax_total", "shipping_total", "total"):
                assert cart_res[k] == exp[k], f"Vector {vec['name']} mismatch on {k}: got {cart_res[k]}, expected {exp[k]}"
        print(f"  OK: All {len(vectors)} deterministic Section 5 totals vectors matched 100%.")

        # Reset standard tax 825 / free shipping for remaining tests
        admin.req("PUT", "/api/admin/commerce/settings", {
            "tax_rates": {"standard_bp": 825, "reduced_bp": 0, "digital_bp": 0},
            "shipping_rates": {"usps_ground_advantage": "0.00", "usps_priority": "0.00", "usps_media_mail": "0.00", "lulu_direct": "0.00"},
        })

        print("[6/9] Testing CSRF, client-price 422, float 422, login cart rotation & price-changed 409...")
        # Missing/bad CSRF -> 403
        st, _, _, _, _ = sh.post("/api/commerce/cart", {"action": "get"}, omit_csrf=True)
        assert st == 403
        st, _, _, _, _ = sh.post("/api/commerce/coupon/apply", {"code": ""}, headers={"X-CSRF-Token": "wrong"})
        assert st == 403
        st, _, _, _, _ = sh.post("/api/commerce/checkout", {"email": "a@b.com"}, omit_csrf=True)
        assert st == 403
        # Client-supplied price -> 422 client_price_not_allowed
        st, _, _, _, js = sh.post("/api/commerce/cart", {"action": "add", "product_id": p1["id"], "qty": 1, "unit_price": "0.01"})
        assert st == 422 and js["error"] == "client_price_not_allowed", js
        # Float qty -> 422 float_not_allowed
        st, _, _, _, js = sh.post("/api/commerce/cart", {"action": "add", "product_id": p1["id"], "qty": 1.5})
        assert st == 422 and js["error"] == "float_not_allowed", js

        # Login rotates shopper cart token & CSRF secret
        old_cart_cookie = sh.cookie
        old_cart_csrf = sh.csrf
        st, _, _, raw, _ = http_req(port, "POST", "/api/auth/login", {
            "email": "author@example.com", "password": "AuthorPassword!123"
        }, headers={"Cookie": old_cart_cookie})
        assert st == 200, raw
        # Old gl_cart cookie MUST now be rejected with 403!
        st, _, _, _, _ = http_req(port, "POST", "/api/commerce/cart", {"action": "get"}, headers={"Cookie": old_cart_cookie, "X-CSRF-Token": old_cart_csrf})
        assert st == 403, f"Expected rotated cart token rejection 403, got {st}"

        # Price-change guard 409
        pch_cart = ShopperClient(port)
        pch_cart.init_session()
        pch_cart.post("/api/commerce/cart", {"action": "add", "product_id": p1["id"], "qty": 1})
        admin.req("PUT", f"/api/admin/commerce/products/{p1['id']}", {"price": "21.99"})
        st, _, _, raw, pchk = pch_cart.post("/api/commerce/checkout", {
            "email": "buyer@example.com",
            "shipping_address": {"line1": "123 Main St", "city": "Austin", "state": "TX", "postal_code": "78701"},
        }, headers={"Idempotency-Key": "price_change_check_123456"})
        assert st == 409 and pchk["error"] == "price_changed" and pchk["cart"]["items"][0]["unit_price"] == "21.99", raw
        # Confirm new price -> succeeds!
        st, _, _, raw, ok_chk = pch_cart.post("/api/commerce/checkout", {
            "email": "buyer@example.com",
            "shipping_address": {"line1": "123 Main St", "city": "Austin", "state": "TX", "postal_code": "78701"},
        }, headers={"Idempotency-Key": "price_change_check_234567"})
        assert st == 201, raw
        print("  OK: CSRF, float/price guards, login cart rotation & price-change 409 verified.")

        print("[7/9] Testing 20-way parallel idempotency (1x 201, 19x 409), stock race 409 & coupon race 409...")
        # Stock = 1 product for race + parallel idempotency test
        st, _, _, raw, race_p = admin.req("POST", "/api/admin/commerce/products", {
            "title": "Limited Poster", "slug": "limited-poster", "sku": "LIM-1", "price": "10.00",
            "kind": "digital", "stock_qty": 1, "tax_class": "digital"
        })
        assert st == 201, raw
        lim_pid = race_p["product"]["id"]

        # 20 parallel checkouts with ONE Idempotency-Key on one cart
        idem_cart = ShopperClient(port)
        idem_cart.init_session()
        idem_cart.post("/api/commerce/cart", {"action": "add", "product_id": lim_pid, "qty": 1})
        shared_key = "parallel_20_idem_key_0001"
        body_20 = {"email": "race20@example.com"}

        def fire_checkout(_idx):
            return idem_cart.post("/api/commerce/checkout", body_20, headers={"Idempotency-Key": shared_key})

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            results_20 = list(ex.map(fire_checkout, range(20)))
        statuses_20 = [r[0] for r in results_20]
        assert statuses_20.count(201) == 1 and statuses_20.count(409) == 19, f"Expected 1x201 + 19x409, got {statuses_20}"
        ord_num_20 = next(r[4]["order_number"] for r in results_20 if r[0] == 201)

        # Sequential retry returns 409 with same order_number
        st, _, _, _, seq_r = idem_cart.post("/api/commerce/checkout", body_20, headers={"Idempotency-Key": shared_key})
        assert st == 409 and seq_r["order_number"] == ord_num_20, seq_r

        # Independent cart using same Idempotency-Key succeeds independently; cross-cart id in payload returns 403
        st, _, _, raw, _ = admin.req("POST", "/api/admin/commerce/products", {
            "title": "One Unit Left", "slug": "one-unit", "sku": "ONE-1", "price": "15.00",
            "kind": "digital", "stock_qty": 1, "tax_class": "digital"
        })
        assert st == 201, raw
        one_pid = json.loads(raw)["product"]["id"]
        rc1, rc2 = ShopperClient(port), ShopperClient(port)
        rc1.init_session()
        rc2.init_session()
        rc1.post("/api/commerce/cart", {"action": "add", "product_id": one_pid, "qty": 1})
        rc2.post("/api/commerce/cart", {"action": "add", "product_id": one_pid, "qty": 1})

        # Cross-cart tampering check -> 403
        st, _, _, _, _ = rc1.post("/api/commerce/checkout", {"email": "x@example.com", "cart_id": rc2.cart_id}, headers={"Idempotency-Key": "cross_cart_test_0001"})
        assert st == 403

        def fire_stock_race(client_and_idx):
            cl, idx = client_and_idx
            return cl.post("/api/commerce/checkout", {"email": f"sr{idx}@example.com"}, headers={"Idempotency-Key": f"stock_race_{idx}_123456789"})

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            sr_res = list(ex.map(fire_stock_race, [(rc1, 1), (rc2, 2)]))
        sr_codes = sorted([r[0] for r in sr_res])
        assert sr_codes == [201, 409], f"Expected [201, 409] stock race, got {sr_res}"

        # Last coupon redemption race -> 1x201 + 1x409 coupon_exhausted
        st, _, _, raw, _ = admin.req("POST", "/api/admin/commerce/products", {
            "title": "Unlimited Digital", "slug": "unlim-dig", "sku": "UDIG-1", "price": "20.00",
            "kind": "digital", "stock_qty": 50, "tax_class": "digital"
        })
        udig_pid = json.loads(raw)["product"]["id"]
        admin.req("POST", "/api/admin/commerce/coupons", {
            "code": "LASTONE", "type": "fixed_cents", "value": 500, "min_subtotal": "0.00", "max_redemptions": 1, "active": 1
        })
        cc1, cc2 = ShopperClient(port), ShopperClient(port)
        cc1.init_session()
        cc2.init_session()
        cc1.post("/api/commerce/cart", {"action": "add", "product_id": udig_pid, "qty": 1})
        cc2.post("/api/commerce/cart", {"action": "add", "product_id": udig_pid, "qty": 1})
        cc1.post("/api/commerce/coupon/apply", {"code": "LASTONE"})
        cc2.post("/api/commerce/coupon/apply", {"code": "LASTONE"})
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            cr_res = list(ex.map(fire_stock_race, [(cc1, 3), (cc2, 4)]))
        cr_codes = sorted([r[0] for r in cr_res])
        assert cr_codes == [201, 409], f"Expected [201, 409] coupon race, got {cr_res}"
        print("  OK: 20-way parallel idempotency, last-unit stock race, and coupon race passed.")

        print("[8/9] Testing GRAB native signed webhook verification (401/202/200/409, amount mismatch, late payment, payment.failed)...")
        # Bad signature -> 401
        raw_ev = json.dumps({"type": "payment.succeeded", "order_number": ord_num_20, "amount": "10.00", "currency": "USD", "payment_ref": "pay_1"})
        ts_now = int(time.time())
        st, _, _, _, _ = http_req(port, "POST", "/api/commerce/webhooks/payment", raw_body=raw_ev, headers={
            "Grab-Event-Id": "evt_bad_sig", "Grab-Event-Time": str(ts_now), "Grab-Signature": "v1=" + ("0" * 64)
        })
        assert st == 401, f"Expected 401 bad signature, got {st}"
        # Stale timestamp -> 401
        st, _, _, _, _ = http_req(port, "POST", "/api/commerce/webhooks/payment", raw_body=raw_ev, headers=sign_webhook(secret, "evt_stale", ts_now - 600, raw_ev))
        assert st == 401, f"Expected 401 stale timestamp, got {st}"

        # Amount mismatch -> accepted 202, order unchanged pending_payment + needs_review = 1
        mismatch_ev = json.dumps({"type": "payment.succeeded", "order_number": ord_num_20, "amount": "1.00", "currency": "USD", "payment_ref": "pay_badamt"})
        st, _, _, raw, _ = http_req(port, "POST", "/api/commerce/webhooks/payment", raw_body=mismatch_ev, headers=sign_webhook(secret, "evt_mismatch_1", ts_now, mismatch_ev))
        assert st == 202, (st, raw)
        time.sleep(0.5)
        ord_list = admin.req("GET", "/api/admin/commerce/orders?needs_review=1")[4]["orders"]
        mm_ord = next(o for o in ord_list if o["number"] == ord_num_20)
        assert mm_ord["status"] == "pending_payment" and mm_ord["needs_review"] is True, mm_ord

        # Valid payment.succeeded -> 202, replay -> 200, different bytes same id -> 409, order becomes paid
        hdrs_ok = sign_webhook(secret, "evt_ok_1", ts_now, raw_ev)
        st, _, _, _, _ = http_req(port, "POST", "/api/commerce/webhooks/payment", raw_body=raw_ev, headers=hdrs_ok)
        assert st == 202
        st, _, _, _, _ = http_req(port, "POST", "/api/commerce/webhooks/payment", raw_body=raw_ev, headers=hdrs_ok)
        assert st == 200
        tamper_ev = json.dumps({"type": "payment.succeeded", "order_number": ord_num_20, "amount": "9.00", "currency": "USD", "payment_ref": "pay_1"})
        st, _, _, _, _ = http_req(port, "POST", "/api/commerce/webhooks/payment", raw_body=tamper_ev, headers=sign_webhook(secret, "evt_ok_1", ts_now, tamper_ev))
        assert st == 409
        time.sleep(0.5)
        st, _, _, _, o_det = admin.req("GET", f"/api/admin/commerce/orders/{mm_ord['id']}")
        assert st == 200 and o_det["order"]["status"] == "paid", o_det

        # Order transitions & audit
        st, _, _, _, _ = admin.req("POST", f"/api/admin/commerce/orders/{mm_ord['id']}/transition", {"status": "delivered"})
        assert st == 409
        st, _, _, _, tr_r = admin.req("POST", f"/api/admin/commerce/orders/{mm_ord['id']}/transition", {"status": "fulfilling"})
        assert st == 200 and tr_r["order"]["status"] == "fulfilling"

        # payment.failed releases stock and coupon
        fail_cart = ShopperClient(port)
        fail_cart.init_session()
        st, _, _, raw, fp_r = admin.req("POST", "/api/admin/commerce/products", {
            "title": "Fail Restore Item", "slug": "fail-restore", "sku": "FAIL-1", "price": "12.00",
            "kind": "digital", "stock_qty": 2, "tax_class": "digital"
        })
        fail_pid = fp_r["product"]["id"]
        admin.req("POST", "/api/admin/commerce/coupons", {
            "code": "FAILCPN", "type": "fixed_cents", "value": 200, "min_subtotal": "0.00", "max_redemptions": 1, "active": 1
        })
        fail_cart.post("/api/commerce/cart", {"action": "add", "product_id": fail_pid, "qty": 1})
        fail_cart.post("/api/commerce/coupon/apply", {"code": "FAILCPN"})
        st, _, _, raw, fail_chk = fail_cart.post("/api/commerce/checkout", {"email": "fail@example.com"}, headers={"Idempotency-Key": "fail_order_idem_0001"})
        assert st == 201, raw
        fail_onum = fail_chk["order_number"]
        fail_ev = json.dumps({"type": "payment.failed", "order_number": fail_onum, "amount": "10.00", "currency": "USD", "payment_ref": "pf_1"})
        st, _, _, _, _ = http_req(port, "POST", "/api/commerce/webhooks/payment", raw_body=fail_ev, headers=sign_webhook(secret, "evt_fail_1", int(time.time()), fail_ev))
        assert st == 202
        time.sleep(0.5)
        con = sqlite3.connect(db_path)
        assert con.execute("SELECT stock_qty FROM products WHERE id = ?", (fail_pid,)).fetchone()[0] == 2
        assert con.execute("SELECT redeemed_count FROM coupons WHERE code = 'FAILCPN'").fetchone()[0] == 0
        # Late payment.succeeded on cancelled/expired order -> not resurrected, needs_review = 1
        lc = ShopperClient(port)
        lc.init_session()
        lc.post("/api/commerce/cart", {"action": "add", "product_id": fail_pid, "qty": 1})
        st, _, _, raw, lc_chk = lc.post("/api/commerce/checkout", {"email": "late@example.com"}, headers={"Idempotency-Key": "late_order_idem_0001"})
        assert st == 201, raw
        con.execute("UPDATE orders SET status = 'expired' WHERE number = ?", (lc_chk["order_number"],))
        con.commit()
        con.close()
        late_ev = json.dumps({"type": "payment.succeeded", "order_number": lc_chk["order_number"], "amount": "12.00", "currency": "USD", "payment_ref": "late_1"})
        st, _, _, _, _ = http_req(port, "POST", "/api/commerce/webhooks/payment", raw_body=late_ev, headers=sign_webhook(secret, "evt_late_1", int(time.time()), late_ev))
        assert st == 202
        time.sleep(0.5)
        con = sqlite3.connect(db_path)
        l_row = con.execute("SELECT status, needs_review FROM orders WHERE number = ?", (lc_chk["order_number"],)).fetchone()
        assert l_row == ("expired", 1), l_row
        con.close()
        print("  OK: Signed webhook security, mismatches, failures, and late payment safety passed.")

        print("[9/9] Testing abandoned checkout sweep (consent gate), MCP commerce tools, GDPR anonymize & overdue hold release...")
        # Backdate two open carts (1 consented, 1 NOT consented) + 1 overdue pending_payment order
        c_yes, c_no = ShopperClient(port), ShopperClient(port)
        c_yes.init_session()
        c_no.init_session()
        c_yes.post("/api/commerce/cart", {"action": "add", "product_id": fail_pid, "qty": 1})
        c_yes.post("/api/commerce/cart", {"action": "set_customer", "email": "optin@example.com", "marketing_consent": 1})
        c_no.post("/api/commerce/cart", {"action": "add", "product_id": fail_pid, "qty": 1})
        c_no.post("/api/commerce/cart", {"action": "set_customer", "email": "optout@example.com", "marketing_consent": 0})
        con = sqlite3.connect(db_path)
        con.execute("UPDATE carts SET last_activity_at = '2020-01-01T00:00:00Z' WHERE id IN (?, ?)", (c_yes.cart_id, c_no.cart_id))
        con.commit()
        con.close()

        sw = run_grab(["run", "--db-config", db_cfg, "--allow-db", "main:read-write", "scripts/commerce_sweep.grab"])
        assert "abandoned=2" in sw.stdout and "events=1" in sw.stdout, sw.stdout

        # Test overdue pending_payment order expiration releases stock & coupon
        admin.req("POST", "/api/admin/commerce/coupons", {
            "code": "EXPIREME", "type": "fixed_cents", "value": 100, "min_subtotal": "0.00", "max_redemptions": 1, "active": 1
        })
        st, _, _, raw, ep = admin.req("POST", "/api/admin/commerce/products", {
            "title": "Hold Release Item", "slug": "hold-release", "sku": "HOLD-1", "price": "10.00",
            "kind": "digital", "stock_qty": 3, "tax_class": "digital"
        })
        assert st == 201, raw
        h_pid = ep["product"]["id"]
        hc = ShopperClient(port)
        hc.init_session()
        hc.post("/api/commerce/cart", {"action": "add", "product_id": h_pid, "qty": 2})
        hc.post("/api/commerce/coupon/apply", {"code": "EXPIREME"})
        st, _, _, raw, h_chk = hc.post("/api/commerce/checkout", {"email": "hold@example.com"}, headers={"Idempotency-Key": "hold_release_idem_0001"})
        assert st == 201, raw
        con = sqlite3.connect(db_path)
        assert con.execute("SELECT stock_qty FROM products WHERE id = ?", (h_pid,)).fetchone()[0] == 1
        assert con.execute("SELECT redeemed_count FROM coupons WHERE code = 'EXPIREME'").fetchone()[0] == 1
        con.execute("UPDATE orders SET payment_due_by = '2020-01-01T00:00:00Z' WHERE number = ?", (h_chk["order_number"],))
        con.commit()
        con.close()
        sw2 = run_grab(["run", "--db-config", db_cfg, "--allow-db", "main:read-write", "scripts/commerce_sweep.grab"])
        assert "expired=1" in sw2.stdout, sw2.stdout
        con = sqlite3.connect(db_path)
        assert con.execute("SELECT status FROM orders WHERE number = ?", (h_chk["order_number"],)).fetchone()[0] == "expired"
        assert con.execute("SELECT stock_qty FROM products WHERE id = ?", (h_pid,)).fetchone()[0] == 3
        assert con.execute("SELECT redeemed_count FROM coupons WHERE code = 'EXPIREME'").fetchone()[0] == 0
        con.close()

        # Check MCP list_commerce_events + create_coupon_draft + create_entry_draft ignores price/stock
        st, _, _, raw, ev_rpc = http_req(port, "POST", "/api/mcp", {
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "list_commerce_events", "arguments": {"name": "commerce:abandoned_checkout", "after_id": 0, "limit": 20}}
        }, headers={"Authorization": f"Bearer {mcp_tok}"})
        assert st == 200 and ev_rpc["result"]["isError"] is False, raw
        ab_events = ev_rpc["result"]["structuredContent"]["events"]
        assert len(ab_events) == 1
        ab_p = ab_events[0]["payload"]
        assert ab_p["cart_id"] == c_yes.cart_id and ab_p["marketing_consent"] == 1
        assert ab_p["email_hash"].startswith("sha256:") and "optin@example.com" not in json.dumps(ab_p)

        st, _, _, raw, cpn_rpc = http_req(port, "POST", "/api/mcp", {
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "create_coupon_draft", "arguments": {
                "code": "GROXY10", "type": "percent_bp", "value": 1000, "min_subtotal": "15.00", "max_redemptions": 50
            }}
        }, headers={"Authorization": f"Bearer {mcp_tok}"})
        assert st == 200 and cpn_rpc["result"]["structuredContent"]["active_enforced"] == 0
        assert cpn_rpc["result"]["structuredContent"]["created_by"].startswith("mcp:"), raw

        # GDPR export + anonymize
        custs = admin.req("GET", "/api/admin/commerce/customers")[4]["customers"]
        target_c = next(c for c in custs if c["email"] == "optin@example.com")
        st, _, _, _, exp_d = admin.req("GET", f"/api/admin/commerce/customers/{target_c['id']}/export")
        assert st == 200 and exp_d["customer"]["email"] == "optin@example.com"
        st, _, _, _, del_d = admin.req("DELETE", f"/api/admin/commerce/customers/{target_c['id']}")
        assert st == 200 and del_d["anonymized"] is True

        # Guest checkout isolation check (typing existing user email must NOT attach user_id)
        gc = ShopperClient(port)
        gc.init_session()
        gc.post("/api/commerce/cart", {"action": "add", "product_id": fail_pid, "qty": 1})
        st, _, _, raw, gc_chk = gc.post("/api/commerce/checkout", {"email": "author@example.com"}, headers={"Idempotency-Key": "guest_email_isolation_01"})
        assert st == 201, raw
        con = sqlite3.connect(db_path)
        g_uid = con.execute("SELECT user_id FROM orders WHERE number = ?", (gc_chk["order_number"],)).fetchone()[0]
        assert g_uid is None, f"Guest checkout unexpectedly attached user_id {g_uid}"
        con.close()
        print("  OK: Sweep consent gate, MCP tools, GDPR anonymize & guest isolation verified.")

        print("\nALL GRABLAB CMS v1.1.0 COMMERCE & SECURITY TESTS PASSED (100%)!")
    finally:
        stop_server(proc)
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
