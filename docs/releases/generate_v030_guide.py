#!/usr/bin/env python3
"""
GrabLab CMS v0.3.0 Plain-English Walkthrough Guide Generator
Generates docs/releases/html/GrabLab-v0.3.0-Guide.html and renders
docs/releases/pdf/GrabLab-v0.3.0-Guide.pdf via headless Chrome.
"""

import os
import subprocess
import sys

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_DIR = os.path.join(BASE_DIR, "html")
PDF_DIR = os.path.join(BASE_DIR, "pdf")
HTML_PATH = os.path.join(HTML_DIR, "GrabLab-v0.3.0-Guide.html")
PDF_PATH = os.path.join(PDF_DIR, "GrabLab-v0.3.0-Guide.pdf")

HTML_DOC = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>GrabLab CMS v0.3.0 — Plain-English Walkthrough Guide</title>
  <style>
    :root {
      --ink: #0f172a;
      --muted: #475569;
      --line: #cbd5e1;
      --bg: #f8fafc;
      --surface: #ffffff;
      --teal: #0d9488;
      --blue: #0284c7;
      --green: #15803d;
    }
    * { box-sizing: border-box; }
    @page { size: A4; margin: 13mm 14mm 14mm 14mm; }
    body {
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: var(--ink);
      background: var(--bg);
      font-size: 13px;
      line-height: 1.55;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
    .hero {
      background: linear-gradient(135deg, #0f172a 0%, #0f766e 60%, #0284c7 100%);
      color: #ffffff;
      border-radius: 12px;
      padding: 22px 26px;
      margin-bottom: 18px;
    }
    .badge {
      display: inline-block;
      background: rgba(255,255,255,0.16);
      border: 1px solid rgba(255,255,255,0.28);
      padding: 3px 10px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.4px;
      text-transform: uppercase;
      margin-bottom: 8px;
    }
    h1 { margin: 0 0 6px; font-size: 24px; line-height: 1.2; }
    .hero p { margin: 0; color: #e2e8f0; font-size: 13.5px; }
    .card {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 16px 18px;
      margin-bottom: 14px;
      page-break-inside: avoid;
    }
    h2 {
      margin: 0 0 8px;
      font-size: 16px;
      color: var(--ink);
      border-bottom: 1px solid #e2e8f0;
      padding-bottom: 5px;
    }
    h3 { margin: 10px 0 4px; font-size: 13.5px; color: var(--teal); }
    p { margin: 6px 0; }
    ul { margin: 6px 0 6px 18px; padding: 0; }
    li { margin-bottom: 4px; }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 8px;
      font-size: 12px;
    }
    th, td {
      border: 1px solid var(--line);
      padding: 6px 8px;
      text-align: left;
      vertical-align: top;
    }
    th { background: #f1f5f9; font-weight: 700; }
    code {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      background: #f1f5f9;
      padding: 1px 4px;
      border-radius: 4px;
      font-size: 11.5px;
    }
    pre {
      margin: 8px 0 0;
      background: #0f172a;
      color: #e2e8f0;
      padding: 10px 12px;
      border-radius: 8px;
      font-size: 11px;
      overflow-x: auto;
      line-height: 1.45;
    }
    .footer-note {
      text-align: center;
      color: var(--muted);
      font-size: 11.5px;
      margin-top: 10px;
    }
  </style>
</head>
<body>
  <header class="hero">
    <span class="badge">Release Walkthrough Guide · Milestone v0.3.0</span>
    <h1>GrabLab CMS v0.3.0: Native Security, Auth &amp; Grex Admin</h1>
    <p>Built natively on GRAB v1.1.0 (<code>use crypto</code>, <code>use env</code>, <code>cache.limit</code>, <code>--allow-scripts</code>) and Grex JS v1.0.0 — zero plugins, clean semantic HTML, and strict tenant safety.</p>
  </header>

  <section class="card">
    <h2>1. What Was Built in v0.3.0 (Plain English)</h2>
    <p>GrabLab CMS v0.3.0 adds a complete, password-hardened authentication system and a point-and-click Admin Dashboard so site owners, editors, authors, and theme designers can manage everything visually in a browser — without any third-party auth or security plugins.</p>
    <ul>
      <li><strong>First-Run Admin Setup (<code>/setup</code>):</strong> On a brand-new site with zero users, visiting <code>/admin</code> or <code>/login</code> guides you to <code>/setup</code> to create the first administrator. As soon as that account is created, <code>/setup</code> locks permanently.</li>
      <li><strong>Modern Password &amp; Session Security:</strong> Passwords are protected with GRAB v1.1.0's native <strong>Argon2id</strong> hashing (never stored in readable text). Browser sessions use random tokens stored only as SHA-256 hashes, wrapped in <code>HttpOnly</code> + <code>SameSite=Lax</code> cookies that automatically rotate on every login.</li>
      <li><strong>Brute-Force Protection:</strong> Using GRAB's sliding-window rate limiter (<code>cache.limit</code>), 5 failed sign-in attempts automatically block repeated guesses for 15 minutes with HTTP <code>429 Too Many Requests</code>.</li>
      <li><strong>Semantic Grex JS v1.0.0 Admin Dashboard:</strong> Manage Entries, Content Types &amp; Fields, Exclusive Themes, Site Settings, and Users under <code>/admin/*</code> with strict Content-Security-Policy (<code>script-src 'self'</code>), zero inline scripts, zero wrapper-<code>&lt;div&gt;</code> tags, and mandatory <code>X-CSRF-Token</code> checks on every save or delete.</li>
    </ul>
  </section>

  <section class="card">
    <h2>2. User Roles &amp; Permissions Matrix</h2>
    <p>Site owners can invite team members and assign one of four built-in roles in <strong>Admin &rarr; Settings &amp; Users</strong>:</p>
    <table>
      <thead>
        <tr>
          <th>Role</th>
          <th>Allowed Actions</th>
          <th>Restricted Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>admin</strong></td>
          <td>Full control: manage users &amp; roles, edit site/OAuth settings, manage content types, activate themes, publish/delete any entry.</td>
          <td>Cannot accidentally demote or deactivate own active admin account.</td>
        </tr>
        <tr>
          <td><strong>editor</strong></td>
          <td>Create, edit, publish, unpublish, and delete any post or page via Admin &rarr; Entries.</td>
          <td>Cannot change site settings, OAuth secrets, users, content types, or active theme.</td>
        </tr>
        <tr>
          <td><strong>author</strong></td>
          <td>Create draft entries; edit and delete only their own drafts.</td>
          <td>Cannot publish entries, edit others' work, or manage site settings/themes/types.</td>
        </tr>
        <tr>
          <td><strong>viewer</strong></td>
          <td>Read-only signed-in viewer account (lowest privilege, also default for new social signups when enabled).</td>
          <td>Blocked (<code>403 Forbidden</code>) from <code>/admin</code> and all CMS write APIs.</td>
        </tr>
      </tbody>
    </table>
  </section>

  <section class="card">
    <h2>3. Optional Built-In Social Login (OAuth2 + PKCE)</h2>
    <p>GrabLab CMS includes optional OAuth2 + PKCE (<code>S256</code>) support for <strong>Google</strong>, <strong>GitHub</strong>, <strong>Discord</strong>, and <strong>Apple</strong>:</p>
    <ul>
      <li><strong>Disabled by Default:</strong> By default, zero social login buttons appear on <code>/login</code> and zero outbound network requests can happen.</li>
      <li><strong>Encrypted Secrets at Rest:</strong> When you paste a provider Client Secret in <code>/admin/settings</code>, GrabLab encrypts it immediately using <strong>AES-256-GCM</strong> (<code>crypto.encrypt_aead</code>) with your server's <code>GRABLAB_MASTER_KEY</code> environment variable (gated by <code>--allow-env</code>). Secrets are never returned to the browser or saved in plaintext.</li>
      <li><strong>Verified Email &amp; Strict Domain Allowlist:</strong> Social login verifies single-use <code>state</code> + PKCE <code>code_verifier</code>, rejects unverified emails, and optionally restricts sign-in to specific company email domains.</li>
    </ul>
  </section>

  <section class="card">
    <h2>4. Admin Dashboard &amp; 1-Click Exclusive Theme Switching</h2>
    <ul>
      <li><strong><code>/admin/entries</code>:</strong> Create, draft, publish, edit, and delete entries with live dynamic custom field inputs and Grex <code>ForEach</code> / <code>useQuery</code> updates.</li>
      <li><strong><code>/admin/types</code>:</strong> Register custom content types (with reserved prefix protection for <code>/admin</code>, <code>/api</code>, <code>/login</code>, <code>/setup</code>, <code>/static</code>) and typed custom fields.</li>
      <li><strong><code>/admin/themes</code>:</strong> View all registered coded and Grex Visual Builder themes and click <strong>Activate</strong> to atomically deactivate the old theme, invalidate route/query caches, and hand 100% rendering control to the chosen theme.</li>
    </ul>
  </section>

  <section class="card">
    <h2>5. How to Upgrade, Run &amp; Verify (GRAB v1.1.0)</h2>
    <p>Use <code>002_auth_schema.grab</code> (safe both on upgrades from v0.1/v0.2 and on brand-new installations) and start the server with GRAB v1.1.0 capability flags:</p>
    <pre>grab migrate --db-config grab.data.json --allow-db main:migrate migrations/002_auth_schema.grab
grab run --db-config grab.data.json --allow-db main:read-write --allow-env GRABLAB_ADMIN_EMAIL,GRABLAB_ADMIN_PASSWORD,GRABLAB_ADMIN_NAME migrations/seed.grab
grab check --platform-config grab.platform.json src/app.grab

# Start server (set GRABLAB_MASTER_KEY in environment before using encrypted OAuth settings)
grab serve --addr 127.0.0.1:8080 --allow-scripts --db-config grab.data.json --allow-db main:read-write --platform-config grab.platform.json --allow-cache cms:read-write --allow-cache cms:limit --allow-env GRABLAB_MASTER_KEY --allow-read . --static public src/app.grab

# Run full automated security &amp; feature test suite (10 test groups)
python tests/integration_test.py</pre>
  </section>

  <p class="footer-note">GrabLab CMS v0.3.0 &middot; Built on GRAB v1.1.0 &amp; Grex JS v1.0.0 &middot; Repository: urbanspress/grablab-cms</p>
</body>
</html>
"""


def main():
    os.makedirs(HTML_DIR, exist_ok=True)
    os.makedirs(PDF_DIR, exist_ok=True)
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(HTML_DOC)

    if not os.path.exists(CHROME_PATH):
        print(f"Chrome not found at {CHROME_PATH}", file=sys.stderr)
        sys.exit(1)

    cmd = [
        CHROME_PATH,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={PDF_PATH}",
        HTML_PATH,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not os.path.exists(PDF_PATH):
        print("PDF generation failed:", res.stderr, file=sys.stderr)
        sys.exit(1)
    print(f"Generated {PDF_PATH} ({os.path.getsize(PDF_PATH)} bytes)")


if __name__ == "__main__":
    main()
