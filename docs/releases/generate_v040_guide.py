#!/usr/bin/env python3
"""
GrabLab CMS v0.4.0 Plain-English Walkthrough Guide Generator
Generates docs/releases/html/GrabLab-v0.4.0-Guide.html and renders
docs/releases/pdf/GrabLab-v0.4.0-Guide.pdf via headless Chrome.
"""

import os
import subprocess
import sys

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_DIR = os.path.join(BASE_DIR, "html")
PDF_DIR = os.path.join(BASE_DIR, "pdf")
HTML_PATH = os.path.join(HTML_DIR, "GrabLab-v0.4.0-Guide.html")
PDF_PATH = os.path.join(PDF_DIR, "GrabLab-v0.4.0-Guide.pdf")

HTML_DOC = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>GrabLab CMS v0.4.0 — Plain-English Walkthrough Guide</title>
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
    <span class="badge">Release Walkthrough Guide &middot; Milestone v0.4.0</span>
    <h1>GrabLab CMS v0.4.0: Media Library, Navigation Menus, Taxonomies &amp; AI CMS Tools</h1>
    <p>Pure <code>.grab</code> and <code>.grab.html</code> modules powered by GRAB v1.1.0 and Grex JS v1.0.0 — zero plugins, isolated uploads, zero wrapper <code>&lt;div&gt;</code> tags, and WCAG AA accessibility guardrails.</p>
  </header>

  <section class="card">
    <h2>1. What Was Built in v0.4.0 (Plain English)</h2>
    <p>GrabLab CMS v0.4.0 gives site owners, editors, and theme designers the everyday publishing tools expected from a complete website platform while keeping every file, route, and layout strictly verified:</p>
    <ul>
      <li><strong>Media Library &amp; Safe Upload Pipeline (<code>/admin/media</code>):</strong> Upload PNG, JPEG, WebP, GIF images, and PDF documents cleanly in the browser. GrabLab inspects real file bytes (not just file extensions), blocks SVGs, HTML files, scripts, and path-traversal names, extracts image width &amp; height, generates random unguessable storage filenames inside an isolated <code>uploads/</code> folder, and requires accessible <code>alt</code> text (or an explicit decorative flag) before saving.</li>
      <li><strong>Navigation Menus &amp; Menu Builder (<code>/admin/menus</code>):</strong> Build header (<code>primary</code>), <code>footer</code>, and <code>mobile</code> menus visually. Reorder or nest items up to 4 levels using mouse drag-and-drop or keyboard buttons (<em>Up / Down / Indent / Outdent / Remove</em>). Links pointing to posts or pages automatically update their URLs whenever you rename a slug.</li>
      <li><strong>Taxonomies, Categories &amp; Tags (<code>/admin/taxonomies</code>):</strong> Organize content with built-in <code>category</code> (hierarchical) and <code>tag</code> (flat) taxonomies or create your own custom taxonomies attached to specific content types. Public archive pages (such as <code>/category/news</code> or <code>/tag/grab</code>) and theme Query Loops update automatically with smart cache invalidation.</li>
      <li><strong>Capability-Gated <code>grab mcp</code> CMS Tools (<code>/api/mcp</code>):</strong> Connect AI coding and content assistants safely using a signed-in user's role-scoped MCP Bearer token. AI tools can inspect content types, query entries, create drafts (always forced to <code>draft</code> status), list media/menus, and compose Grex layouts that pass automatic schema and WCAG AA accessibility checks before saving.</li>
    </ul>
  </section>

  <section class="card">
    <h2>2. Media Library: How Uploads Stay Safe &amp; Accessible</h2>
    <p>For site owners, uploading media feels effortless in <strong>Admin &rarr; Media Library</strong>, while GrabLab enforces strong safety guardrails behind the scenes:</p>
    <table>
      <thead>
        <tr>
          <th>Protection</th>
          <th>How It Works</th>
          <th>Behavior When Violated</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Magic-Byte Inspection</strong></td>
          <td>Decodes uploaded payload and verifies actual PNG, JPEG, WebP, GIF, or PDF byte headers &amp; pixel dimensions.</td>
          <td>Rejects mismatched or corrupt files, SVGs, HTML, and executables with HTTP <code>415</code> or <code>400</code>.</td>
        </tr>
        <tr>
          <td><strong>Sandboxed Storage</strong></td>
          <td>Only GRAB's <code>--allow-write uploads</code> folder is writable; every saved file gets a randomized <code>crypto.random_hex</code> name and never preserves raw disk paths.</td>
          <td>Filenames containing <code>..</code>, slashes, or control bytes return HTTP <code>400</code>.</td>
        </tr>
        <tr>
          <td><strong>Required Alt Text</strong></td>
          <td>Every image upload or metadata edit requires descriptive <code>alt_text</code> unless explicitly marked <code>is_decorative: true</code>.</td>
          <td>Returns HTTP <code>422 Unprocessable Entity</code> until accessibility metadata is supplied.</td>
        </tr>
        <tr>
          <td><strong>Safe Delivery</strong></td>
          <td>Served via <code>GET /media/{id}/{filename}</code> with <code>X-Content-Type-Options: nosniff</code>, <code>Content-Security-Policy: default-src 'none'</code>, and immutable <code>ETag</code> / <code>304 Not Modified</code> caching.</td>
          <td>Never executes embedded scripts and supports fast browser caching.</td>
        </tr>
      </tbody>
    </table>
  </section>

  <section class="card">
    <h2>3. Navigation Menus &amp; Theme Integration (Zero Wrapper <code>&lt;div&gt;</code>s)</h2>
    <p>Each theme exposes standard named menu locations: <code>primary</code>, <code>footer</code>, and <code>mobile</code>. Assigning a menu to a slot atomically clears that slot from any previous menu and immediately refreshes cached navigation HTML.</p>
    <ul>
      <li><strong>Dynamic Entry Permalinks:</strong> Internal menu items store an <code>entry_id</code> rather than a frozen URL. When you edit an entry's slug (e.g., from <code>/blog/menu-target</code> to <code>/blog/menu-target-v2</code>), GrabLab invalidates menu caches and every rendered <code>&lt;nav&gt;</code> link updates right away.</li>
      <li><strong>Clean Semantic HTML:</strong> Menus render strictly using <code>&lt;nav&gt;</code>, <code>&lt;ul&gt;</code>, <code>&lt;li&gt;</code>, and <code>&lt;a&gt;</code> with <code>aria-current="page"</code> on the active route and zero wrapper <code>&lt;div&gt;</code> elements.</li>
      <li><strong>Theme Placeholders:</strong> Coded themes use <code>&lt;!-- @menu:primary --&gt;</code> or <code>&lt;!-- @menu:footer --&gt;</code>; Grex visual themes consume <code>GET /api/menus/:location</code> via Grex <code>Nav</code> elements.</li>
    </ul>
  </section>

  <section class="card">
    <h2>4. Taxonomies, Query Loops &amp; Archive Routes</h2>
    <p>GrabLab seeds <strong>Categories</strong> (<code>/category/:slug</code>) and <strong>Tags</strong> (<code>/tag/:slug</code>) alongside default category <em>Uncategorized</em>. Admins and Editors can create additional custom taxonomies in <strong>Admin &rarr; Taxonomies</strong>:</p>
    <ul>
      <li><strong>Reserved Prefix Protection:</strong> Custom taxonomy <code>archive_slug</code> values cannot collide with system prefixes (<code>/admin</code>, <code>/api</code>, <code>/media</code>, <code>/login</code>, <code>/logout</code>, <code>/setup</code>, <code>/static</code>, <code>/search</code>) or existing content-type archive paths (HTTP <code>409 Conflict</code>).</li>
      <li><strong>Hierarchical Query Filtering:</strong> Theme Query Loops and public APIs accept <code>filter_by_term: {taxonomy, term_slug, include_children}</code>, automatically returning descendant term entries when <code>include_children</code> is true and clearing cache buckets when terms or entry assignments change.</li>
    </ul>
  </section>

  <section class="card">
    <h2>5. AI Assistant Safety: Capability-Gated <code>grab mcp</code> Tools</h2>
    <p>Signed-in CMS team members (<code>author</code>, <code>editor</code>, <code>admin</code>) can generate an MCP Bearer token via <code>POST /api/auth/mcp-token</code> and connect external assistants to <code>POST /api/mcp</code> (JSON-RPC 2.0) or <code>POST /api/mcp/tools/{name}</code>:</p>
    <table>
      <thead>
        <tr>
          <th>MCP Tool Name</th>
          <th>Required Capability &amp; Guardrails</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><code>list_content_types</code></td>
          <td>Requires <code>entries:create</code> / admin+author+editor access. Returns non-secret content-type &amp; field definitions.</td>
        </tr>
        <tr>
          <td><code>query_entries</code></td>
          <td>Published entries for CMS tool users; drafts/private entries strictly require <code>entries:read_all</code> (Editor/Admin). Filters by <code>term_slug</code> &amp; <code>taxonomy</code>.</td>
        </tr>
        <tr>
          <td><code>create_entry_draft</code></td>
          <td>Requires <code>entries:create</code>. <strong>Always</strong> forces <code>status = "draft"</code> even if an AI assistant requests <code>"published"</code>.</td>
        </tr>
        <tr>
          <td><code>update_entry_layout</code></td>
          <td>Validates ownership (Authors can edit only their own entries), checks <code>grex.elements.json</code> allowlist, blocks <code>&lt;div&gt;</code>, <code>&lt;script&gt;</code>, inline events, and bad URLs, and runs WCAG AA heading-order / image-<code>alt</code> checks — returning HTTP <code>422</code> with structured diagnostics if any check fails.</td>
        </tr>
        <tr>
          <td><code>list_media</code> / <code>list_menus</code></td>
          <td>Read-only catalog lookups gated by <code>media:read</code> and <code>entries:create</code>, guaranteeing zero passwords, CSRF secrets, or OAuth secrets ever leave the server.</td>
        </tr>
      </tbody>
    </table>
  </section>

  <section class="card">
    <h2>6. How to Upgrade, Run &amp; Verify (GRAB v1.1.0)</h2>
    <p>Apply the additive <code>003_v04_schema.grab</code> migration (works on both existing v0.3 sites and fresh installs) and start the server with isolated write access limited to <code>uploads/</code>:</p>
    <pre>grab migrate --db-config grab.data.json --allow-db main:migrate migrations/003_v04_schema.grab
grab run --db-config grab.data.json --allow-db main:read-write --allow-env GRABLAB_ADMIN_EMAIL,GRABLAB_ADMIN_PASSWORD,GRABLAB_ADMIN_NAME migrations/seed.grab
grab check --db-config grab.data.json --platform-config grab.platform.json src/app.grab

# Start server (writes permitted ONLY inside uploads/)
grab serve --addr 127.0.0.1:8080 --allow-scripts --db-config grab.data.json --allow-db main:read-write --platform-config grab.platform.json --allow-cache cms:read-write --allow-cache cms:limit --allow-env GRABLAB_MASTER_KEY,GRABLAB_UPLOAD_DIR,GRABLAB_MAX_UPLOAD_BYTES --allow-read . --allow-write uploads --static public --max-body-bytes 15728640 src/app.grab

# Run full automated v0.1 - v0.4 integration test suite (13 test stages, 100% pass required)
python tests/integration_test.py</pre>
  </section>

  <p class="footer-note">GrabLab CMS v0.4.0 &middot; Built on GRAB v1.1.0 &amp; Grex JS v1.0.0 &middot; Repository: urbanspress/grablab-cms</p>
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
