#!/usr/bin/env python3
"""Generate GrabLab CMS v1.4.0 Plain-English Author Mode & Bestseller Radar Guide."""

import os
import shutil
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HTML_OUT = os.path.join(ROOT, "docs", "releases", "html", "GrabLab-CMS-v1.4.0-Guide.html")
PDF_OUT = os.path.join(ROOT, "docs", "releases", "pdf", "GrabLab-CMS-v1.4.0-Guide.pdf")

HTML_DOC = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>GrabLab CMS v1.4.0 — Author Mode Book &amp; Series Publishing + Bestseller Radar Guide</title>
  <style>
    @page { size: A4; margin: 16mm 16mm 18mm 16mm; }
    * { box-sizing: border-box; }
    body {
      font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
      color: #0f172a; line-height: 1.55; font-size: 10.2pt; margin: 0; padding: 0; background: #ffffff;
    }
    .hero {
      background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 100%);
      color: #ffffff; padding: 26px 28px; border-radius: 12px; margin-bottom: 20px;
    }
    .eyebrow {
      font-size: 8.5pt; text-transform: uppercase; letter-spacing: 0.12em;
      color: #bfdbfe; font-weight: 700; margin: 0 0 6px 0;
    }
    .hero h1 { margin: 0 0 8px 0; font-size: 20pt; line-height: 1.18; }
    .hero p { margin: 0; color: #e2e8f0; font-size: 10.3pt; }
    .pill-row { margin-top: 14px; display: flex; gap: 8px; flex-wrap: wrap; }
    .pill {
      display: inline-block; background: rgba(255,255,255,0.16);
      border: 1px solid rgba(255,255,255,0.28); color: #ffffff;
      padding: 3px 10px; border-radius: 999px; font-size: 8.5pt; font-weight: 600;
    }
    h2 {
      font-size: 13.5pt; color: #1d4ed8; border-bottom: 2px solid #dbeafe;
      padding-bottom: 4px; margin: 22px 0 10px 0; page-break-after: avoid;
    }
    h3 { font-size: 11pt; color: #0f172a; margin: 14px 0 6px 0; page-break-after: avoid; }
    p, li { margin-bottom: 6px; }
    .card {
      border: 1px solid #cbd5e1; background: #f8fafc;
      border-radius: 8px; padding: 12px 14px; margin-bottom: 12px;
    }
    table { width: 100%; border-collapse: collapse; margin: 10px 0 14px 0; font-size: 9.2pt; }
    th, td { border: 1px solid #cbd5e1; padding: 6px 8px; text-align: left; }
    th { background: #f1f5f9; font-weight: 700; }
    code { background: #f1f5f9; padding: 1px 4px; border-radius: 4px; font-size: 9pt; }
    footer { margin-top: 24px; font-size: 8.5pt; color: #475569; border-top: 1px solid #cbd5e1; padding-top: 8px; }
  </style>
</head>
<body>
  <section class="hero">
    <p class="eyebrow">GrabLab CMS &middot; Release Walkthrough</p>
    <h1>GrabLab CMS v1.4.0 &mdash; Author Mode &amp; Bestseller Radar</h1>
    <p>Zero-plugin book &amp; series publishing, distraction-free sample Web Reader, direct v1.1.0 EPUB/PDF &amp; Lulu/USPS store linkage, and an embedded Groxy AI Bestseller Radar built natively into GrabLab CMS.</p>
    <section class="pill-row">
      <span class="pill">Status: Complete</span>
      <span class="pill">SemVer: 1.4.0 (Minor Feature)</span>
      <span class="pill">GRAB v1.1.0 + Grex JS v1.0.0</span>
      <span class="pill">Zero-Plugin Core</span>
    </section>
  </section>

  <h2>1. What Changed in Plain English</h2>
  <section class="card">
    <ul>
      <li><strong>Built-In Author Mode (Disabled by Default):</strong> Upgrading existing CMS sites adds five new database tables (<code>authors</code>, <code>series</code>, <code>books</code>, <code>chapters</code>, <code>author_radar_imports</code>) with zero data loss and keeps all Author &amp; Reader routes (<code>/admin/author*</code>, <code>/books*</code>, <code>/series*</code>) safely hidden (<code>404</code>) until an administrator enables Author Mode.</li>
      <li><strong>Series Reading Order &amp; Sample Web Reader:</strong> Authors can organize books into multi-book series, drag or click to reorder books and chapters, mark sample chapters (<code>is_sample = 1</code>), and offer visitors a clean Light/Dark Web Reader at <code>/books/&lt;slug&gt;/sample/&lt;chapter&gt;</code>.</li>
      <li><strong>Direct Storefront &amp; Fulfillment Sync (<code>v1.1.0</code>):</strong> One click syncs a book to a store product for either DRM-free EPUB/PDF instant download grants or matte paperback fulfillment via <strong>Lulu Direct (<code>LULU-USPS-001</code>)</strong> and <strong>USPS-only</strong> mail rules—while keeping open customer carts protected against surprise price changes (<code>409 price_changed</code>).</li>
      <li><strong>Embedded Bestseller Radar &amp; Readability Auditor:</strong> From <strong>Admin &rarr; Author Mode &rarr; Bestseller Radar</strong>, authors can query <strong>Groxy AI</strong> (<code>v1.7.0</code> + <code>v1.8.0</code>) for genre profit estimates and readability checks, then import suggested outlines strictly as safe <code>draft</code> entries for human editing.</li>
    </ul>
  </section>

  <h2>2. Security, Precision &amp; SEO Safeguards</h2>
  <table>
    <thead><tr><th>Safeguard</th><th>How It Works in v1.4.0</th></tr></thead>
    <tbody>
      <tr><td><strong>Exact Money &amp; Identifiers (<code>ADR-025c</code>)</strong></td><td>List prices and royalty rates require exact USD/percentage text strings (<code>"14.99"</code>, <code>"70.00"</code>); raw floats/exponents, bad GS1 <code>ISBN-13</code> check digits, and malformed <code>ASIN</code>s are rejected with HTTP <code>422</code>.</td></tr>
      <tr><td><strong>Allowlisted AI Bridge (<code>GRAB-E402</code>)</strong></td><td>Only administrators can configure <code>groxy_ai_origin</code> (public <code>https://</code> or loopback <code>http://127.0.0.1</code>); private network and cloud metadata IPs (<code>169.254.169.254</code>) are blocked on save and before every request.</td></tr>
      <tr><td><strong>No Duplicate Radar Imports (<code>409</code>)</strong></td><td>Each Radar approval token and plan ID is atomically claimed inside a database transaction: concurrent or repeated imports yield one <code>201</code> winner and <code>409</code> for all replays, always landing as <code>status: "draft"</code>.</td></tr>
      <tr><td><strong>XSS-Safe Book JSON-LD &amp; 301s</strong></td><td>Public <code>schema.org/Book</code> and <code>BookSeries</code> metadata escapes <code>&lt;/script&gt;</code> and angle brackets automatically; renaming slugs records <code>slug_history</code> <code>301</code> redirects and clears cache keys cleanly.</td></tr>
      <tr><td><strong>Zero-DOM-Debt &amp; WCAG AA</strong></td><td>All Author Admin and Sample Web Reader templates use pure <code>Grex JS v1.0.0</code> semantic elements (<code>divCount === 0</code>, <code>innerHTMLWriteCount === 0</code>) with verified Light &amp; Dark contrast (<code>&gt;= 4.5:1</code>).</td></tr>
    </tbody>
  </table>

  <h2>3. Upgrading &amp; Enabling Author Mode</h2>
  <ol>
    <li>Apply additive migration <code>migrations/005_author_schema.grab</code> (or PostgreSQL/MariaDB equivalent).</li>
    <li>Optionally run <code>migrations/seed_author.grab</code> to register native defaults safely (idempotent).</li>
    <li>Sign in as an Administrator, open <strong>Admin &rarr; Author Mode &rarr; Settings</strong>, enable Author Mode, and optionally enter your allowlisted Groxy AI origin URL (<code>https://...</code> or <code>http://127.0.0.1:&lt;port&gt;</code>).</li>
    <li>Create authors, series, books, and sample chapters under <strong>Admin &rarr; Author Mode</strong>, or click <strong>Sync Store Product</strong> to sell digital EPUB/PDF or Lulu/USPS print editions through your existing <code>v1.1.0</code> storefront.</li>
  </ol>

  <h2>4. Verification Summary</h2>
  <p>Stage 4 Cross-Layer Security &amp; Contract Sign-Off passed 100% across <code>grab check</code> (default and commerce profiles), byte-for-byte canonical <code>grab format</code> across all 20 <code>.grab</code> files, Node Grex JS DOM &amp; Light/Dark WCAG AA audits (<code>tests/author_dom_audit.mjs</code> and <code>tests/commerce_dom_audit.mjs</code>), <code>tests/author_test.py</code> (10/10), <code>tests/release_v140_test.py</code> (5/5), and full regression suites (<code>tests/commerce_test.py</code> 9/9, <code>tests/release_v110_test.py</code> 5/5, <code>tests/integration_test.py</code> 13/13, <code>tests/release_v100_test.py</code> 5/5).</p>

  <footer>GrabLab CMS v1.4.0 &middot; Specification: GRABLAB-SPEC-140 &middot; Built on GRAB v1.1.0 &amp; Grex JS v1.0.0</footer>
</body>
</html>
"""


def find_chrome():
    for path in (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        shutil.which("chrome"),
        shutil.which("msedge"),
    ):
        if path and os.path.exists(path):
            return path
    raise RuntimeError("Chrome/Edge executable not found for headless PDF generation")


def main():
    os.makedirs(os.path.dirname(HTML_OUT), exist_ok=True)
    os.makedirs(os.path.dirname(PDF_OUT), exist_ok=True)
    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(HTML_DOC)
    chrome = find_chrome()
    html_uri = "file:///" + HTML_OUT.replace("\\", "/")
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={PDF_OUT}",
        html_uri,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0 or not os.path.exists(PDF_OUT) or os.path.getsize(PDF_OUT) < 10000:
        raise RuntimeError(f"PDF generation failed ({res.returncode}):\n{res.stdout}\n{res.stderr}")
    print(f"Generated {HTML_OUT}")
    print(f"Generated {PDF_OUT} ({os.path.getsize(PDF_OUT)} bytes)")


if __name__ == "__main__":
    main()
