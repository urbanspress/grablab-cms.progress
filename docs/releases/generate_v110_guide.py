#!/usr/bin/env python3
"""Generate GrabLab CMS v1.1.0 Plain-English Zero-Plugin E-Commerce Core Guide."""

import os
import shutil
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HTML_OUT = os.path.join(ROOT, "docs", "releases", "html", "GrabLab-CMS-v1.1.0-Guide.html")
PDF_OUT = os.path.join(ROOT, "docs", "releases", "pdf", "GrabLab-CMS-v1.1.0-Guide.pdf")

HTML_DOC = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>GrabLab CMS v1.1.0 — Zero-Plugin E-Commerce Core Guide</title>
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
    .hero h1 { margin: 0 0 8px 0; font-size: 20.5pt; line-height: 1.18; }
    .hero p { margin: 0; color: #e2e8f0; font-size: 10.4pt; }
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
    <h1>GrabLab CMS v1.1.0 &mdash; Zero-Plugin E-Commerce Core</h1>
    <p>Native online store, exact-penny USD pricing, USPS &amp; Lulu Direct fulfillment, signed payment webhooks, and opt-in abandoned-checkout reminders built directly into GrabLab CMS.</p>
    <section class="pill-row">
      <span class="pill">Status: Complete</span>
      <span class="pill">SemVer: 1.1.0 (Minor Feature)</span>
      <span class="pill">GRAB v1.1.0 + Grex JS v1.0.0</span>
      <span class="pill">Zero-Plugin Core</span>
    </section>
  </section>

  <h2>1. What Changed in Plain English</h2>
  <section class="card">
    <ul>
      <li><strong>Built-In Storefront (Disabled by Default):</strong> Upgrading existing CMS sites adds database tables safely with zero data loss and keeps storefront routes (<code>/shop</code>, <code>/api/commerce/*</code>) disabled (<code>404</code>) until an administrator explicitly enables Commerce in <strong>Store Settings</strong>.</li>
      <li><strong>No Penny Rounding Errors (ADR-025c):</strong> Every product price, coupon discount, tax calculation, shipping charge, and order total is stored as exact integer cents and sent over the web as exact USD text strings (<code>"19.99"</code>). Raw decimal numbers and floating-point guesses are automatically blocked with HTTP <code>422</code>.</li>
      <li><strong>Guest-First Checkout &amp; Privacy:</strong> Customers can check out in seconds without creating an account, or opt into account creation if they are not signed in. Marketing recovery emails and cart reminders require an explicit unchecked opt-in box (<code>marketing_consent = 1</code>).</li>
      <li><strong>Bookstore &amp; Digital Ready:</strong> Supports <strong>USPS-only</strong> physical mail services (<code>ground_advantage</code>, <code>priority</code>, <code>media_mail</code> with weight caps) plus <strong>Lulu Direct</strong> print-on-demand book SKUs and validated <strong>ISBN-13</strong> metadata, alongside instant protected digital file downloads once payment is verified.</li>
    </ul>
  </section>

  <h2>2. Store Security &amp; Reliability Safeguards</h2>
  <table>
    <thead><tr><th>Safeguard</th><th>How It Works in v1.1.0</th></tr></thead>
    <tbody>
      <tr><td><strong>Signed Payment Webhooks</strong></td><td>Opt-in platform profile (<code>deploy/grab.platform.commerce.json</code>) delegates cryptographic HMAC-SHA256 verification and replay protection directly to GRAB <code>v1.1.0</code> before GrabLab updates order status.</td></tr>
      <tr><td><strong>HTTPS Payment Redirects (<code>GRAB-E402</code>)</strong></td><td>Administrators must configure an exact allowlist of <code>https://</code> payment hostnames; invalid schemes, ports, wildcards, or unknown hosts are blocked on save and at checkout.</td></tr>
      <tr><td><strong>Duplicate-Charge Protection</strong></td><td>Each checkout requires an <code>Idempotency-Key</code> scoped strictly to that shopper's cart. Simultaneous clicks cannot create duplicate orders.</td></tr>
      <tr><td><strong>No Overselling &amp; 60-Minute Hold Release</strong></td><td>Stock and coupon usage are atomically reserved at checkout and automatically returned if an unpaid order passes its 60-minute payment window.</td></tr>
      <tr><td><strong>Admin &amp; AI Separation</strong></td><td>MCP AI tokens (for Groxy AI) can inspect commerce events and save <em>inactive</em> coupon drafts (<code>active = 0</code>), but cannot activate coupons, change prices, or view payment settings.</td></tr>
    </tbody>
  </table>

  <h2>3. Upgrading &amp; Enabling Commerce</h2>
  <ol>
    <li>Apply additive migration <code>migrations/004_commerce_schema.grab</code> (or Postgres/MariaDB equivalent).</li>
    <li>Run <code>migrations/seed_commerce.grab</code> to register the <code>product</code> content type and safe defaults.</li>
    <li>When ready to accept live payments, migrate the GRAB event store (<code>grab migrate --platform-config deploy/grab.platform.commerce.json --db-config grab.data.json --events-store commerce --allow-db main:migrate --allow-events commerce:work</code>), set <code>GRABLAB_PAYMENT_WEBHOOK_SECRET</code>, and launch using <code>deploy/grab.platform.commerce.json</code>.</li>
    <li>Sign in as an Administrator, visit <strong>Admin &rarr; Store / Commerce &rarr; Settings</strong>, set your tax rates, flat shipping rates, and allowlisted HTTPS payment host, and flip Storefront Status to Enabled.</li>
  </ol>

  <h2>4. Verification Summary</h2>
  <p>Verified 100% across <code>grab check</code> (both default and commerce platform profiles), canonical <code>grab format</code> byte-for-byte checks, Node Grex JS DOM/WCAG AA Light &amp; Dark contrast audits (<code>divCount === 0</code>, <code>innerHTMLWriteCount === 0</code>), <code>tests/integration_test.py</code>, <code>tests/release_v100_test.py</code>, <code>tests/commerce_test.py</code>, and <code>tests/release_v110_test.py</code>.</p>

  <footer>GrabLab CMS v1.1.0 &middot; Specification: GRABLAB-SPEC-110 (Revision 2) &middot; Built on GRAB v1.1.0 &amp; Grex JS v1.0.0</footer>
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
