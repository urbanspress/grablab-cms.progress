#!/usr/bin/env python3
"""Generate GrabLab CMS v1.4.1 Plain-English PostgreSQL 18 Search Compatibility Patch Guide."""

import os
import shutil
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HTML_OUT = os.path.join(ROOT, "docs", "releases", "html", "GrabLab-CMS-v1.4.1-Guide.html")
PDF_OUT = os.path.join(ROOT, "docs", "releases", "pdf", "GrabLab-CMS-v1.4.1-Guide.pdf")

HTML_DOC = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>GrabLab CMS v1.4.1 &mdash; PostgreSQL 18 Taxonomy Search Compatibility Patch</title>
  <style>
    @page { size: A4; margin: 16mm 16mm 18mm 16mm; }
    * { box-sizing: border-box; }
    body {
      font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
      color: #0f172a; line-height: 1.55; font-size: 10.2pt; margin: 0; padding: 0; background: #ffffff;
    }
    .hero {
      background: linear-gradient(135deg, #0f172a 0%, #0d9488 100%);
      color: #ffffff; padding: 26px 28px; border-radius: 12px; margin-bottom: 20px;
    }
    .eyebrow {
      font-size: 8.5pt; text-transform: uppercase; letter-spacing: 0.12em;
      color: #99f6e4; font-weight: 700; margin: 0 0 6px 0;
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
      font-size: 13.5pt; color: #0f766e; border-bottom: 2px solid #ccfbf1;
      padding-bottom: 4px; margin: 22px 0 10px 0; page-break-after: avoid;
    }
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
    <p class="eyebrow">GrabLab CMS &middot; Patch Release Walkthrough</p>
    <h1>GrabLab CMS v1.4.1 &mdash; PostgreSQL 18 Taxonomy Query Patch</h1>
    <p>Drop-in backwards-compatible PATCH release replacing <code>SELECT DISTINCT ... ORDER BY COALESCE(...)</code> in <code>stmt_query_entries_by_term</code> with a cleaner, PostgreSQL 18 compliant <code>WHERE EXISTS (...)</code> subquery.</p>
    <section class="pill-row">
      <span class="pill">Status: Complete</span>
      <span class="pill">SemVer: 1.4.1 (Drop-In Patch)</span>
      <span class="pill">GRAB v1.1.0 + Grex JS v1.0.0</span>
      <span class="pill">SQLite / MariaDB / PostgreSQL 18</span>
    </section>
  </section>

  <h2>1. What Fixed in Plain English</h2>
  <section class="card">
    <ul>
      <li><strong>PostgreSQL 18 Strict `ORDER BY` Compliance (`stmt_query_entries_by_term` in `src/app.grab`):</strong> Previously, filtering public or archive posts/pages by taxonomy terms used <code>SELECT DISTINCT ... ORDER BY COALESCE(e.published_at, e.created_at) DESC, e.id DESC</code> across a join to <code>entry_terms</code>. PostgreSQL 18 rejects <code>SELECT DISTINCT</code> queries whose <code>ORDER BY</code> expression (<code>COALESCE(...)</code>) is not literally listed in the <code>SELECT</code> output list.</li>
      <li><strong>Clean `EXISTS (...)` Fix with Zero Duplicate Rows:</strong> Rewrote <code>stmt_query_entries_by_term</code> to query <code>entries</code> once using <code>WHERE EXISTS (SELECT 1 FROM entry_terms et WHERE et.entry_id = e.id AND et.term_id IN (...))</code>. Multi-term parent/child category queries return each matching entry exactly once on SQLite, MariaDB, and PostgreSQL 18—with zero database schema changes required.</li>
      <li><strong>Regression Test Coverage (`tests/release_v140_test.py`):</strong> Added automated verification asserting both the prepared SQL structure and multi-term parent+child deduplication without needing any database workaround.</li>
    </ul>
  </section>

  <h2>2. Upgrading</h2>
  <ol>
    <li>Replace <code>src/app.grab</code> with the <code>v1.4.1</code> release (no database migrations are needed beyond <code>v1.4.0</code>).</li>
    <li>Run <code>grab check --platform-config grab.platform.json src/app.grab</code> and gracefully restart your Grisp workers.</li>
  </ol>

  <footer>GrabLab CMS v1.4.1 &middot; SemVer PATCH Release &middot; Built on GRAB v1.1.0 &amp; Grex JS v1.0.0</footer>
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
