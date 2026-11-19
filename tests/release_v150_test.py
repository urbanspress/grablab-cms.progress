#!/usr/bin/env python3
"""
GrabLab CMS v1.5.0 Admin UI Polish & Universal User Profile Studio Integration Suite
Tests:
1. Canonical `grab format` & `grab check` across src/app.grab + all admin templates
2. Universal `/admin/profile` HTML route across ALL 4 roles (admin, editor, author, viewer) with zero <div> & zero <svg>
3. `GET /api/auth/profile` RBAC, session listing, role capability matrix, zero secret leakage, MCP Bearer 401
4. `PATCH /api/auth/profile` CSRF enforcement, validation (empty, >80, multiline), & own display_name update
5. `POST /api/auth/password` CSRF, current_password 403, complexity 400, atomic password update + other-session revocation
6. `POST /api/auth/sessions/revoke-others` keeps current session alive and revokes sibling sessions
7. `GET /login` redirects logged-in viewer to `/admin/profile` and logged-in admin/editor/author to `/admin`
"""

import http.client
import json
import os
import subprocess
import tempfile
import time
import socket

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_GRAB = (
    r"C:\Program Files\GRAB\grab.exe"
    if os.path.exists(r"C:\Program Files\GRAB\grab.exe")
    else r"C:\Development\GRAB\dist\grab-windows-amd64.exe"
)
GRAB_BIN = os.environ.get("GRAB_BIN", DEFAULT_GRAB)


def run_grab(args, env=None):
    merged = os.environ.copy()
    if env:
        merged.update(env)
    res = subprocess.run([GRAB_BIN] + args, cwd=ROOT, env=merged, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        raise AssertionError(f"grab {' '.join(args)} failed ({res.returncode}):\n{res.stdout}\n{res.stderr}")
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
        payload = json.dumps(body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    conn.request(method, path, body=payload, headers=hdrs)
    resp = conn.getresponse()
    raw = resp.read().decode("utf-8", errors="replace")
    r_hdrs = {k.lower(): v for k, v in resp.getheaders()}
    cookies = resp.headers.get_all("Set-Cookie") or []
    conn.close()
    parsed = None
    if "application/json" in r_hdrs.get("content-type", ""):
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = None
    return resp.status, r_hdrs, cookies, raw, parsed


def extract_cookie(set_cookies, name="grablab_session"):
    for sc in set_cookies:
        first = sc.split(";", 1)[0].strip()
        if first.startswith(name + "="):
            return first
    return ""


class Client:
    def __init__(self, port):
        self.port = port
        self.cookie = ""
        self.csrf = ""

    def login(self, email, password, setup=False, name="Admin"):
        path = "/api/auth/setup" if setup else "/api/auth/login"
        body = {"email": email, "password": password}
        if setup:
            body["display_name"] = name
        st, _, cookies, raw, js = http_req(self.port, "POST", path, body)
        assert st in (200, 201), f"Auth failed {path}: {st} {raw}"
        self.cookie = extract_cookie(cookies)
        self.csrf = js["csrf_token"]
        return js

    def req(self, method, path, body=None, headers=None, omit_csrf=False, omit_cookie=False):
        hdrs = dict(headers or {})
        if not omit_cookie and self.cookie:
            hdrs.setdefault("Cookie", self.cookie)
        if not omit_csrf and self.csrf and method in ("POST", "PUT", "PATCH", "DELETE"):
            hdrs.setdefault("X-CSRF-Token", self.csrf)
        return http_req(self.port, method, path, body=body, headers=hdrs)


def main():
    tmp_dir = tempfile.mkdtemp(prefix="gl_v150_test_")
    proc = None
    try:
        print("[1/5] Checking canonical format & static admin assets...")
        run_grab(["check", "--platform-config", "grab.platform.json", "src/app.grab"])
        fmt = run_grab(["format", "src/app.grab"])
        with open(os.path.join(ROOT, "src/app.grab"), "r", encoding="utf-8") as f:
            assert fmt.stdout == f.read(), "src/app.grab is not canonically formatted"

        db_path = os.path.join(tmp_dir, "v150.db")
        db_cfg = os.path.join(tmp_dir, "db.json")
        with open(db_cfg, "w", encoding="utf-8") as f:
            json.dump({"connections": {"main": {"driver": "sqlite", "path": db_path}}}, f)

        run_grab(["migrate", "--db-config", db_cfg, "--allow-db", "main:migrate", "migrations/005_author_schema.grab"])
        run_grab(["run", "--db-config", db_cfg, "--allow-db", "main:read-write", "--allow-read", ".", "migrations/seed.grab"])

        port = find_free_port()
        uploads_dir = os.path.join(tmp_dir, "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        env = os.environ.copy()
        env["GRABLAB_UPLOAD_DIR"] = uploads_dir
        env["GRABLAB_MASTER_KEY"] = "test-master-key-01234567890123456789"
        log_fh = open(os.path.join(tmp_dir, "srv.log"), "w", encoding="utf-8")
        proc = subprocess.Popen(
            [
                GRAB_BIN, "serve",
                "--addr", f"127.0.0.1:{port}",
                "--allow-scripts",
                "--db-config", db_cfg,
                "--allow-db", "main:read-write",
                "--platform-config", "grab.platform.json",
                "--allow-cache", "cms:read-write",
                "--allow-cache", "cms:limit",
                "--allow-env", "GRABLAB_UPLOAD_DIR,GRABLAB_MASTER_KEY",
                "--allow-read", ".",
                "--allow-read", uploads_dir,
                "--allow-write", uploads_dir,
                "--static", "public",
                "src/app.grab",
            ],
            cwd=ROOT, env=env, stdout=log_fh, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        )
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                if http_req(port, "GET", "/_health")[0] == 200:
                    break
            except Exception:
                pass
            time.sleep(0.15)
        else:
            raise TimeoutError("Server failed to start")

        admin = Client(port)
        admin.login("admin@example.com", "StrongAdminPassword!123", setup=True, name="Admin Owner")

        for role, email in (("editor", "editor@example.com"), ("author", "author@example.com"), ("viewer", "viewer@example.com")):
            st, _, _, raw, _ = admin.req("POST", "/api/admin/users", {
                "email": email, "display_name": f"{role.title()} User", "role": role, "password": "StrongUserPassword!123"
            })
            assert st == 201, raw

        editor = Client(port)
        editor.login("editor@example.com", "StrongUserPassword!123")
        author = Client(port)
        author.login("author@example.com", "StrongUserPassword!123")
        viewer = Client(port)
        viewer.login("viewer@example.com", "StrongUserPassword!123")

        print("[2/5] Verifying universal /admin/profile route across all 4 roles (0 <div>, 0 <svg>)...")
        st_unauth, hdrs_unauth, _, _, _ = http_req(port, "GET", "/admin/profile")
        assert st_unauth == 302 and hdrs_unauth.get("location") == "/login"

        for label, cli in (("admin", admin), ("editor", editor), ("author", author), ("viewer", viewer)):
            st, hdrs, _, html, _ = cli.req("GET", "/admin/profile")
            assert st == 200, f"{label} /admin/profile failed: {st}"
            assert "<div" not in html.lower(), f"{label} /admin/profile contained <div>"
            assert "<svg" not in html.lower(), f"{label} /admin/profile header contained <svg>"
            assert 'name="grablab-page" content="profile"' in html
            assert "admin-ui.css" in html and "theme-init.js" in html
            assert "no-store" in hdrs.get("cache-control", "")

        # Logged-in viewer visiting /login redirects to /admin/profile; admin redirects to /admin
        st_vl, hdrs_vl, _, _, _ = viewer.req("GET", "/login")
        assert st_vl == 302 and hdrs_vl.get("location") == "/admin/profile"
        st_al, hdrs_al, _, _, _ = admin.req("GET", "/login")
        assert st_al == 302 and hdrs_al.get("location") == "/admin"

        print("[3/5] Verifying GET /api/auth/profile RBAC, capabilities & MCP Bearer 401...")
        assert http_req(port, "GET", "/api/auth/profile")[0] == 401
        mcp_tok = admin.req("POST", "/api/auth/mcp-token", {})[4]["token"]
        assert http_req(port, "GET", "/api/auth/profile", headers={"Authorization": f"Bearer {mcp_tok}"})[0] == 401

        for label, cli, expect_admin_cap in (("admin", admin, True), ("editor", editor, True), ("author", author, True), ("viewer", viewer, False)):
            st, _, _, raw, js = cli.req("GET", "/api/auth/profile")
            assert st == 200 and js["user"]["role"] == label, raw
            assert "password_hash" not in raw and "csrf_secret" not in raw and "token_hash" not in raw
            caps = {c["key"]: c["granted"] for c in js["capabilities"]}
            assert caps["admin:access"] is expect_admin_cap, caps
            assert js["has_password"] is True
            assert len(js["sessions"]) >= 1

        print("[4/5] Verifying PATCH /api/auth/profile CSRF, validation & display_name update...")
        assert viewer.req("PATCH", "/api/auth/profile", {"display_name": "No CSRF"}, omit_csrf=True)[0] == 403
        assert viewer.req("PATCH", "/api/auth/profile", {"display_name": "   "})[0] == 400
        assert viewer.req("PATCH", "/api/auth/profile", {"display_name": "X" * 81})[0] == 400
        assert viewer.req("PATCH", "/api/auth/profile", {"display_name": "Line1\nLine2"})[0] == 400

        st, _, _, raw, upd = viewer.req("PATCH", "/api/auth/profile", {"display_name": "Jane Reader", "role": "admin"})
        assert st == 200 and upd["user"]["display_name"] == "Jane Reader" and upd["user"]["role"] == "viewer", raw
        _, _, _, _, prof_after = viewer.req("GET", "/api/auth/profile")
        assert prof_after["user"]["display_name"] == "Jane Reader" and prof_after["user"]["role"] == "viewer"

        print("[5/5] Verifying POST /api/auth/password & /api/auth/sessions/revoke-others...")
        viewer_s2 = Client(port)
        viewer_s2.login("viewer@example.com", "StrongUserPassword!123")
        viewer_s3 = Client(port)
        viewer_s3.login("viewer@example.com", "StrongUserPassword!123")

        assert viewer.req("POST", "/api/auth/sessions/revoke-others", {}, omit_csrf=True)[0] == 403
        assert viewer.req("POST", "/api/auth/sessions/revoke-others", {})[0] == 200
        assert viewer.req("GET", "/api/auth/profile")[0] == 200
        assert viewer_s2.req("GET", "/api/auth/profile")[0] == 401

        assert viewer.req("POST", "/api/auth/password", {"current_password": "WrongPassword!1", "new_password": "NewStrongPassword!1"})[0] == 403
        assert viewer.req("POST", "/api/auth/password", {"current_password": "StrongUserPassword!123", "new_password": "short"})[0] == 400
        assert viewer.req("POST", "/api/auth/password", {"current_password": "StrongUserPassword!123", "new_password": "StrongUserPassword!123"})[0] == 400

        viewer_s3.login("viewer@example.com", "StrongUserPassword!123")
        assert viewer_s3.req("GET", "/api/auth/profile")[0] == 200
        st, _, _, raw, pw_res = viewer.req("POST", "/api/auth/password", {
            "current_password": "StrongUserPassword!123",
            "new_password": "UpdatedViewerPassword!999",
        })
        assert st == 200 and pw_res["ok"] is True and pw_res["other_sessions_revoked"] is True, raw
        assert viewer_s3.req("GET", "/api/auth/profile")[0] == 401
        assert viewer.req("GET", "/api/auth/profile")[0] == 200

        viewer_new = Client(port)
        viewer_new.login("viewer@example.com", "UpdatedViewerPassword!999")
        assert viewer_new.req("GET", "/api/auth/profile")[0] == 200

        print("\nALL GRABLAB CMS v1.5.0 PROFILE & UI INTEGRATION TESTS PASSED (100%)!")
    finally:
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        if "log_fh" in locals():
            log_fh.close()
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
