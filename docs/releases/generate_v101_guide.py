#!/usr/bin/env python3
"""Generate GrabLab CMS v1.0.1 Plain-English Cross-Layer Audit & Release Guide."""

import os
import shutil
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HTML_OUT = os.path.join(ROOT, "docs", "releases", "html", "GrabLab-v1.0.1-Guide.html")
PDF_OUT = os.path.join(ROOT, "docs", "releases", "pdf", "GrabLab-v1.0.1-Guide.pdf")


HTML_DOC = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>GrabLab CMS v1.0.1 — Cross-Layer Audit &amp; Maintenance Release Guide</title>
  <style>
    @page {
      size: A4;
      margin: 16mm 16mm 18mm 16mm;
    }
    * { box-sizing: border-box; }
    body {
      font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
      color: #0f172a;
      line-height: 1.55;
      font-size: 10.2pt;
      margin: 0;
      padding: 0;
      background: #ffffff;
    }
    .hero {
      background: linear-gradient(135deg, #0f172a 0%, #0f766e 100%);
      color: #ffffff;
      padding: 26px 28px;
      border-radius: 12px;
      margin-bottom: 20px;
    }
    .eyebrow {
      font-size: 8.5pt;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: #99f6e4;
      font-weight: 700;
      margin: 0 0 6px 0;
    }
    .hero h1 {
      margin: 0 0 8px 0;
      font-size: 20.5pt;
      line-height: 1.18;
      letter-spacing: -0.02em;
    }
    .hero p {
      margin: 0;
      color: #e2e8f0;
      font-size: 10.4pt;
    }
    .pill-row {
      margin-top: 14px;
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .pill {
      display: inline-block;
      background: rgba(255, 255, 255, 0.16);
      border: 1px solid rgba(255, 255, 255, 0.28);
      color: #ffffff;
      padding: 3px 10px;
      border-radius: 999px;
      font-size: 8.5pt;
      font-weight: 600;
    }
    h2 {
      font-size: 13.5pt;
      color: #0f766e;
      border-bottom: 2px solid #ccfbf1;
      padding-bottom: 4px;
      margin: 22px 0 10px 0;
      page-break-after: avoid;
    }
    h3 {
      font-size: 11pt;
      color: #0f172a;
      margin: 14px 0 6px 0;
      page-break-after: avoid;
    }
    p { margin: 0 0 9px 0; }
    ul, ol { margin: 0 0 10px 0; padding-left: 20px; }
    li { margin-bottom: 4px; }
    .grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 12px;
    }
    .card {
      border: 1px solid #e2e8f0;
      background: #f8fafc;
      border-radius: 9px;
      padding: 12px 14px;
      break-inside: avoid;
    }
    .card h3 {
      margin-top: 0;
      color: #0f766e;
      font-size: 10.5pt;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 8px 0 14px 0;
      font-size: 9.2pt;
      break-inside: avoid;
    }
    th, td {
      border: 1px solid #cbd5e1;
      padding: 7px 9px;
      text-align: left;
      vertical-align: top;
    }
    th {
      background: #f1f5f9;
      color: #0f172a;
      font-weight: 700;
    }
    code {
      font-family: "Cascadia Mono", Consolas, "Courier New", monospace;
      font-size: 8.8pt;
      background: #f1f5f9;
      color: #0f172a;
      padding: 1px 4px;
      border-radius: 4px;
    }
    pre {
      background: #0f172a;
      color: #e2e8f0;
      padding: 11px 13px;
      border-radius: 8px;
      font-family: "Cascadia Mono", Consolas, "Courier New", monospace;
      font-size: 8.4pt;
      line-height: 1.45;
      overflow-x: auto;
      margin: 6px 0 12px 0;
      white-space: pre-wrap;
      word-break: break-word;
      break-inside: avoid;
    }
    .callout {
      border-left: 4px solid #0f766e;
      background: #f0fdfa;
      padding: 10px 13px;
      border-radius: 0 8px 8px 0;
      margin: 10px 0 14px 0;
      font-size: 9.6pt;
      break-inside: avoid;
    }
    .footer-note {
      margin-top: 18px;
      padding-top: 10px;
      border-top: 1px solid #e2e8f0;
      font-size: 8.5pt;
      color: #64748b;
      text-align: center;
    }
  </style>
</head>
<body>

  <header class="hero">
    <p class="eyebrow">GrabLab CMS &bull; Official Maintenance Release Guide</p>
    <h1>GrabLab CMS v1.0.1 — Cross-Layer Audit &amp; Hardening</h1>
    <p>Backward-compatible security, accessibility, and Grex Theme Builder / MCP contract polish clearing the launchpad for Step 4 (<code>groxy-ai</code>).</p>
    <section class="pill-row" aria-label="Release highlights">
      <span class="pill">100% v1.x Compatible</span>
      <span class="pill">Zero Wrapper &lt;div&gt; Verified</span>
      <span class="pill">Grex v1.0.0 SHA-256 Parity</span>
      <span class="pill">Step 4 (groxy-ai) Ready</span>
    </section>
  </header>

  <h2>1. Why We Released GrabLab CMS v1.0.1</h2>
  <p>Before launching <strong>Step 4 (<code>groxy-ai</code> — Autonomous Design &amp; SEO Agent)</strong> on top of <strong>GRAB v1.1.0</strong>, <strong>Grex JS v1.0.0</strong>, <strong>GrabLab CMS</strong>, and <strong>Grex Theme Builder v1.0.0</strong>, we ran a full second-opinion production audit across every core template, Admin script, API endpoint, container mount, and cross-repository asset.</p>
  <p>Zero breaking issues or XSS/wrapper-<code>&lt;div&gt;</code> regressions were found. However, we uncovered four subtle interoperability and guardrail polish opportunities between <code>GRABLAB-SPEC-100</code>, <code>Grex Theme Builder v1.0.0</code>, and external MCP AI callers — all fixed cleanly in <code>v1.0.1</code> with zero breaking changes.</p>

  <h2>2. Summary of Audit Verification &amp; v1.0.1 Improvements</h2>

  <table>
    <thead>
      <tr>
        <th>Audit Area</th>
        <th>Finding &amp; What Changed in <code>v1.0.1</code></th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Semantic DOM &amp; XSS Audit</strong></td>
        <td>Verified zero wrapper <code>&lt;div&gt;</code> elements, zero <code>eval()</code> / <code>new Function()</code>, and zero <code>.innerHTML</code> / unsafe URLs across <code>src/app.grab</code>, all 12 <code>.grab.html</code> templates, and <code>public/admin/admin.js</code>.</td>
      </tr>
      <tr>
        <td><strong>Grex JS v1.0.0 Parity</strong></td>
        <td>Confirmed 100% SHA-256 byte-for-byte parity between <code>C:\Development\grex-js\dist\</code> and <code>public/grex/</code>, and vendored <code>grex.elements.json</code> directly to <code>public/grex/grex.elements.json</code> (<code>/static/grex/grex.elements.json</code>).</td>
      </tr>
      <tr>
        <td><strong><code>grab mcp</code> SPEC-100 Parity</strong></td>
        <td>Added full parameter alias support for <code>create_entry_draft</code> (<code>content_type_slug</code>, <code>body</code>, <code>excerpt</code>, and WCAG/Grex-checked <code>grex_layout</code>), <code>update_entry_layout</code> (<code>grex_layout</code> alias), <code>query_entries</code> (<code>field_key</code>, <code>field_op</code>, <code>field_value</code>, <code>sort_by</code>, <code>sort_dir</code>, <code>page</code>, <code>per_page</code>, author filtering), <code>list_menus</code> (<code>location</code> filter), and JSON-RPC <code>-32602</code> error metadata on <code>422</code>/<code>400</code> tool failures.</td>
      </tr>
      <tr>
        <td><strong>Grex Builder &amp; WCAG AA</strong></td>
        <td>Expanded semantic tag allowlist (<code>blockquote</code>, <code>time</code>, <code>code</code>, <code>small</code>, <code>strong</code>, <code>em</code>, <code>svg</code>, <code>dialog</code>, <code>details</code>, <code>summary</code>, <code>textarea</code>, <code>tbody</code>, <code>figure</code>, <code>figcaption</code>), added contrast ratio checks across inherited backgrounds (<code>GREX-A11Y-001</code>), focus outline blocking (<code>GREX-A11Y-005</code>), CSS expression checks, <code>srcdoc</code> blocking, and <code>decorative: true</code> support.</td>
      </tr>
      <tr>
        <td><strong>Redirect &amp; Read-Only Safety</strong></td>
        <td>Added explicit self-loop and reserved-prefix target guards in <code>301</code> redirect resolution and re-verified <code>/_health</code>, <code>/_ready</code>, magic-byte media uploads, and <code>deploy/docker-compose.yml</code> <code>--read-only</code> mounts.</td>
      </tr>
    </tbody>
  </table>

  <section class="callout">
    <strong>Ecosystem Launchpad Status — 4/4 Foundational Layers Verified:</strong><br>
    <code>GRAB v1.1.0</code> + <code>Grex JS v1.0.0</code> + <code>GrabLab CMS v1.0.1</code> + <code>Grex Theme Builder v1.0.0</code> are tested, synchronized, and ready for <strong>Step 4 (<code>groxy-ai</code>)</strong>.
  </section>

  <h2>3. Verification Run Results</h2>
  <ul>
    <li><code>grab check --platform-config grab.platform.json</code> &amp; canonical <code>grab format</code>: <strong>0 errors across all 11 <code>.grab</code> files and 12 <code>.grab.html</code> templates</strong></li>
    <li><code>tests/integration_test.py</code>: <strong>13/13 stages passed (100%)</strong></li>
    <li><code>tests/release_v100_test.py</code>: <strong>5/5 production release stages passed (100%)</strong> (including new <code>v1.0.1</code> MCP/SPEC-100/WCAG/elements regression assertions)</li>
  </ul>

  <pre>python tests/integration_test.py
python tests/release_v100_test.py</pre>

  <footer class="footer-note">
    GrabLab CMS v1.0.1 &bull; urbanspress/grablab-cms &bull; Built on GRAB v1.1.0, Grisp, and Grex JS v1.0.0
  </footer>

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
