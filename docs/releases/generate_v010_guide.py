#!/usr/bin/env python3
"""
GrabLab CMS v0.1.0 Plain-English Walkthrough Guide Generator
Generates docs/releases/html/GRABLAB-v0.1.0-Guide.html and renders
docs/releases/pdf/GRABLAB-v0.1.0-Guide.pdf via headless Chrome.
"""

import os
import subprocess
import sys

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_DIR = os.path.join(BASE_DIR, "html")
PDF_DIR = os.path.join(BASE_DIR, "pdf")
HTML_PATH = os.path.join(HTML_DIR, "GRABLAB-v0.1.0-Guide.html")
PDF_PATH = os.path.join(PDF_DIR, "GRABLAB-v0.1.0-Guide.pdf")

HTML_DOC = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>GrabLab CMS v0.1.0 — Plain-English Walkthrough Guide</title>
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
      --amber: #b45309;
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
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #0d9488 100%);
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
    h3 { margin: 10px 0 4px; font-size: 13.5px; color: var(--blue); }
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
    code, pre {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 11.5px;
      background: #f1f5f9;
      border-radius: 4px;
    }
    code { padding: 1px 4px; }
    pre {
      padding: 10px 12px;
      border: 1px solid var(--line);
      overflow-x: auto;
      white-space: pre-wrap;
      margin: 8px 0 0;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .pill-ok {
      display: inline-block;
      background: #dcfce7;
      color: #166534;
      font-weight: 700;
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 999px;
    }
    .page-break { page-break-before: always; }
    .footer-note {
      margin-top: 12px;
      font-size: 11.5px;
      color: var(--muted);
      text-align: center;
    }
  </style>
</head>
<body>
  <section class="hero">
    <span class="badge">GrabLab CMS &middot; Release v0.1.0</span>
    <h1>GrabLab CMS v0.1.0 Plain-English Walkthrough Guide</h1>
    <p>Foundation release on GRAB v1.0.1 &amp; Grex JS v1.0.0: Content Types, Typed Custom Fields, Pretty Permalinks, Automatic 301 Slug History, and Exclusive Active Theme Switching.</p>
  </section>

  <section class="card">
    <h2>1. What Was Built in v0.1.0</h2>
    <p><strong>GrabLab CMS</strong> is a fast, zero-plugin Content Management System built directly on <strong>GRAB v1.0.1</strong> and <strong>Grex JS v1.0.0</strong>. Instead of bolting on third-party plugins that conflict or slow down your site, every core capability lives cleanly inside verified <code>.grab</code> and <code>.grab.html</code> modules.</p>
    <div class="grid">
      <div>
        <h3>Core Data &amp; Content Engine</h3>
        <ul>
          <li><strong>Idempotent Database Schema:</strong> Six structured tables (<code>site_settings</code>, <code>content_types</code>, <code>field_definitions</code>, <code>entries</code>, <code>slug_history</code>, <code>themes</code>) powered by prepared SQL (<code>use data</code>).</li>
          <li><strong>Built-In &amp; Custom Types:</strong> Seeded with <code>page</code> (<code>/:slug</code>) and <code>post</code> (<code>/blog/:slug</code>), plus APIs to register custom types like <code>product</code> (<code>/shop/:slug</code>).</li>
          <li><strong>8 Typed Custom Fields:</strong> Strict validation for <code>text</code>, <code>rich_text</code>, <code>integer</code>, <code>decimal</code> (exact base-10 strings—no float rounding bugs), <code>boolean</code>, <code>date</code>, <code>url</code>, and <code>json</code> (including Grex JS v1.0.0 layouts).</li>
        </ul>
      </div>
      <div>
        <h3>Routing, SEO &amp; Theme Safety</h3>
        <ul>
          <li><strong>Pretty Permalinks:</strong> Clean URLs (<code>/about</code>, <code>/blog</code>, <code>/blog/hello-world</code>) with system prefix protection so content can never hijack <code>/admin</code>, <code>/api</code>, <code>/static</code>, <code>/_health</code>, or <code>/_ready</code>.</li>
          <li><strong>Automatic 301 Redirects:</strong> Renaming a published page or post automatically saves the old path in <code>slug_history</code> and serves a <code>301 Moved Permanently</code> redirect—while cleaning up old entries if you ever revert a slug so redirect loops cannot happen.</li>
          <li><strong>Exclusive Active Theme:</strong> Only one theme is active at a time. Switching themes validates <code>theme.json</code>, blocks path traversal or unsafe capabilities, and atomically deactivates the prior theme across <code>use cache</code>.</li>
        </ul>
      </div>
    </div>
  </section>

  <section class="card">
    <h2>2. How It Works for Site Owners &amp; Designers</h2>
    <table>
      <thead>
        <tr>
          <th>Role</th>
          <th>How GrabLab v0.1.0 Helps You</th>
          <th>Where It Lives</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Site Owner</strong></td>
          <td>Create pages, posts, or custom catalog items with guaranteed price/number accuracy (<code>GrabDecimal</code> strings like <code>"19.9500"</code>) and rename URLs without losing search engine links thanks to automatic <code>301</code> history.</td>
          <td><code>src/app.grab</code> &amp; <code>migrations/</code></td>
        </tr>
        <tr>
          <td><strong>Theme Designer</strong></td>
          <td>Build semantic HTML5 templates in <code>themes/&lt;slug&gt;/</code> with <code>theme.json</code>, zero wrapper <code>&lt;div&gt;</code> bloat, and <code>Grex JS v1.0.0</code> design tokens served with SHA-256 cache busting (<code>server.asset</code>).</td>
          <td><code>themes/default-starter/</code> &amp; <code>public/grex/</code></td>
        </tr>
        <tr>
          <td><strong>Operator / Host</strong></td>
          <td>Run a single self-contained GRAB server binary with default-deny file/database permissions, prepared SQL injection immunity, and SQLite/PostgreSQL/MariaDB schema parity.</td>
          <td><code>grab.data.json</code> &amp; <code>grab.platform.json</code></td>
        </tr>
      </tbody>
    </table>
  </section>

  <section class="card page-break">
    <h2>3. How to Run GrabLab CMS v0.1.0 Locally</h2>
    <p>All commands run from the <code>grablab-cms</code> repository root using the <strong>GRAB v1.0.1</strong> CLI (<code>grab</code>):</p>
    <pre># 1. Verify syntax, routes, and templates
grab check --platform-config grab.platform.json src/app.grab

# 2. Apply database schema migrations and seed starter content
grab migrate --db-config grab.data.json --allow-db main:migrate migrations/001_schema.grab
grab run --db-config grab.data.json --allow-db main:read-write --allow-read . migrations/seed.grab

# 3. Start the GrabLab CMS server
grab serve --addr 127.0.0.1:8080 --db-config grab.data.json --allow-db main:read-write ^
  --platform-config grab.platform.json --allow-cache cms:read-write ^
  --allow-read . --static public src/app.grab</pre>
    <p>Once started, open <code>http://127.0.0.1:8080/</code>, <code>/about</code>, <code>/blog</code>, <code>/blog/hello-world</code>, or inspect JSON endpoints at <code>/api/content-types</code>, <code>/api/entries</code>, <code>/api/redirects</code>, and <code>/api/themes</code>.</p>
  </section>

  <section class="card">
    <h2>4. Verified Security &amp; Quality Gates <span class="pill-ok">100% PASSING</span></h2>
    <table>
      <thead>
        <tr>
          <th>Gate / Feature</th>
          <th>Verification Coverage</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><code>grab check</code> &amp; <code>grab format</code></td>
          <td>Zero errors and canonical formatting verified across <code>src/app.grab</code>, all <code>migrations/*.grab</code>, and every <code>.grab.html</code> template in <code>themes/default-starter/</code>.</td>
        </tr>
        <tr>
          <td>Custom Field &amp; Grex Layout Validation</td>
          <td>All 8 types verified; exact <code>GrabDecimal</code> strings (<code>"19.9500"</code>) preserved; unsafe <code>javascript:</code>/<code>data:</code> URLs, <code>&lt;script&gt;</code> tags, wrapper <code>&lt;div&gt;</code> tags, and <code>on*</code> props rejected with HTTP <code>400</code>.</td>
        </tr>
        <tr>
          <td>Pretty Permalinks &amp; 301 Loop Prevention</td>
          <td><code>/</code>, <code>/:slug</code>, <code>/:type_prefix/:slug</code>, archives, <code>404</code>, reserved-prefix protection, automatic <code>301</code> on rename, and clean <code>200</code> + history cleanup on slug revert verified.</td>
        </tr>
        <tr>
          <td>Exclusive Theme Switching</td>
          <td>Path traversal (<code>..</code>) and unauthorized <code>capabilities</code> rejected with <code>GRAB-E401</code>; atomic switch activates one theme, deactivates all others, and invalidates <code>use cache</code> immediately.</td>
        </tr>
      </tbody>
    </table>
  </section>

  <p class="footer-note">GrabLab CMS v0.1.0 &middot; Built on GRAB v1.0.1 &amp; Grex JS v1.0.0 &middot; Repository: urbanspress/grablab-cms</p>
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
