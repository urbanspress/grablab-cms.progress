/**
 * GrabLab CMS v1.4.0 Author Mode DOM, Grex JS v1.0.0, Keyboard/Focus & Light/Dark WCAG AA Contrast Audit
 * Usage: node tests/author_dom_audit.mjs
 */

import fs from "node:fs";
import assert from "node:assert/strict";

let divCount = 0;
let innerHTMLWriteCount = 0;
const createdElements = [];
let activeEl = null;

function makeFakeElement(tag) {
  const tagLower = String(tag).toLowerCase();
  if (tagLower === "div") divCount += 1;
  const attrs = new Map();
  const children = [];
  const listeners = new Map();
  let textVal = "";
  const el = {
    tagName: tagLower.toUpperCase(),
    nodeName: tagLower.toUpperCase(),
    nodeType: 1,
    hidden: false,
    disabled: false,
    checked: false,
    open: false,
    value: "",
    children,
    childNodes: children,
    style: {},
    dataset: {},
    classList: {
      add: () => {},
      remove: () => {},
      contains: () => false,
    },
    get firstChild() {
      return children[0] || null;
    },
    get textContent() {
      return textVal;
    },
    set textContent(v) {
      textVal = String(v);
    },
    get innerHTML() {
      return "";
    },
    set innerHTML(_v) {
      innerHTMLWriteCount += 1;
      throw new Error("innerHTML writes are strictly forbidden");
    },
    get className() {
      return attrs.get("class") || "";
    },
    set className(v) {
      attrs.set("class", String(v));
    },
    setAttribute(k, v) {
      attrs.set(k, String(v));
    },
    getAttribute(k) {
      return attrs.has(k) ? attrs.get(k) : null;
    },
    hasAttribute(k) {
      return attrs.has(k);
    },
    removeAttribute(k) {
      attrs.delete(k);
    },
    appendChild(ch) {
      children.push(ch);
      return ch;
    },
    removeChild(ch) {
      const idx = children.indexOf(ch);
      if (idx >= 0) children.splice(idx, 1);
      return ch;
    },
    insertBefore(ch, ref) {
      const idx = children.indexOf(ref);
      if (idx >= 0) children.splice(idx, 0, ch);
      else children.push(ch);
      return ch;
    },
    focus() {
      activeEl = el;
    },
    showModal() {
      el.open = true;
    },
    close() {
      el.open = false;
    },
    click() {
      const fns = listeners.get("click") || [];
      for (const fn of fns) fn({ type: "click", target: el, preventDefault() {} });
    },
    addEventListener(evName, fn) {
      if (!listeners.has(evName)) listeners.set(evName, []);
      listeners.get(evName).push(fn);
    },
    removeEventListener(evName, fn) {
      const arr = listeners.get(evName) || [];
      const i = arr.indexOf(fn);
      if (i >= 0) arr.splice(i, 1);
    },
    dispatchEvent(ev) {
      const fns = listeners.get(ev.type) || [];
      for (const fn of fns) fn(ev);
    },
    querySelectorAll(sel) {
      const out = [];
      const walk = (n) => {
        if (!n || typeof n !== "object") return;
        if (sel === "div" && n.tagName === "DIV") out.push(n);
        if (sel.includes("button") && ["BUTTON", "A", "INPUT", "SELECT", "TEXTAREA"].includes(n.tagName) && !n.disabled) {
          out.push(n);
        }
        for (const c of n.children || []) walk(c);
      };
      walk(el);
      return out;
    },
    querySelector() {
      return null;
    },
  };
  createdElements.push(el);
  return el;
}

const docAttrs = new Map();
globalThis.document = {
  documentElement: {
    setAttribute: (k, v) => docAttrs.set(k, String(v)),
    getAttribute: (k) => (docAttrs.has(k) ? docAttrs.get(k) : null),
  },
  get activeElement() {
    return activeEl;
  },
  head: makeFakeElement("head"),
  body: makeFakeElement("body"),
  createElement: (tag) => makeFakeElement(tag),
  createTextNode: (t) => ({ nodeType: 3, textContent: String(t), children: [] }),
  createComment: (t) => ({ nodeType: 8, textContent: String(t), children: [] }),
  getElementById: () => null,
  querySelectorAll: (sel) => (sel === "div" ? createdElements.filter((e) => e.tagName === "DIV") : []),
};

const { auditAccessibility, isExactGrabWireString, computeContrastRatio } = await import("../public/grex/grex.js");
const authorMod = await import("../public/admin/author.js");
const readerMod = await import("../public/author/reader.js");

function countDivsInTree(root) {
  let count = root.tagName === "DIV" ? 1 : 0;
  for (const ch of root.children || []) {
    count += countDivsInTree(ch);
  }
  return count;
}

// 1. Static hygiene audit on Author JS sources
const jsFiles = [
  "public/admin/author.js",
  "public/author/reader.js",
  "public/admin/admin.js",
];
for (const rel of jsFiles) {
  const src = fs.readFileSync(rel, "utf8");
  assert.equal(/\.innerHTML\s*=/.test(src), false, `${rel} contains forbidden .innerHTML assignment`);
  assert.equal(/\beval\s*\(|new\s+Function\s*\(/.test(src), false, `${rel} contains eval/new Function`);
  assert.equal(/createElement\(\s*["']div["']\s*\)/.test(src), false, `${rel} creates forbidden <div>`);
  assert.equal(/type:\s*["']number["']/.test(src), false, `${rel} uses forbidden float-prone type="number"`);
}

// 2. Render pure Grex Author & Reader trees
const subnavView = authorMod.buildAuthorSubnav("author_radar");
const dashView = authorMod.createAuthorDashboardSpec({
  enabled: true,
  counts: { authors: 1, series: 1, books: 2, chapters: 4, radar_imports: 1 },
  recent_books: [{ id: 1, title: "Night Ledger", list_price: "14.99", currency: "USD", edition_format: "paperback", isbn_13: "9780306406157", product_id: 2 }],
});
const readerCtrl = readerMod.buildReaderControls("light", "md");

for (const v of [subnavView, dashView, readerCtrl.element]) {
  assert.equal(countDivsInTree(v), 0, "Expected 0 <div> tags in rendered Author/Reader tree");
}

// 3. Keyboard Enter/Space & Escape + Focus Restoration on Radar Modal
const triggerBtn = makeFakeElement("button");
triggerBtn.focus();
assert.equal(document.activeElement, triggerBtn);

const proposalSig = { peek: () => ({ radar_plan_id: "rplan-1234", genre_slug: "urban-fiction", selected_price_tier_usd: "14.99" }) };
const modalCtrl = authorMod.createRadarConfirmationDialog(
  {
    _v: null,
    peek() {
      return this._v;
    },
    set(v) {
      this._v = v;
    },
  },
  async () => {}
);
modalCtrl.openForProposal(proposalSig.peek());
assert.equal(modalCtrl.modal.element.open, true, "Radar confirmation dialog must open");
assert.equal(countDivsInTree(modalCtrl.modal.element), 0, "Modal must contain 0 <div> tags");

// Pressing Escape closes modal and restores focus to triggerBtn
modalCtrl.modal.element.dispatchEvent({ type: "keydown", key: "Escape", preventDefault() {} });
assert.equal(modalCtrl.modal.element.open, false, "Escape must close confirmation dialog");
assert.equal(document.activeElement, triggerBtn, "Escape must restore focus to triggering button");

// Reader keyboard Enter/Space toggles theme Light -> Dark -> Light
const themeBtn = readerCtrl.element.children[0];
assert.equal(readerCtrl.theme.peek(), "light");
themeBtn.dispatchEvent({ type: "keydown", key: "Enter", preventDefault() {} });
assert.equal(readerCtrl.theme.peek(), "dark", "Enter must toggle reader theme to dark");
themeBtn.dispatchEvent({ type: "keydown", key: " ", preventDefault() {} });
assert.equal(readerCtrl.theme.peek(), "light", "Space must toggle reader theme back to light");

assert.equal(divCount, 0, "Expected global divCount === 0");
assert.equal(innerHTMLWriteCount, 0, "Expected innerHTMLWriteCount === 0");

// 4. Exact GrabDecimal wire string check
assert.equal(isExactGrabWireString("14.99"), true);
assert.equal(isExactGrabWireString("70.00"), true);
assert.equal(isExactGrabWireString("1e2"), false);
assert.equal(isExactGrabWireString(14.99), false);

// 5. Grex auditAccessibility check
const treeAudit = auditAccessibility({
  type: "Section",
  children: [
    { type: "Heading", props: { level: 1, text: "Author Mode Studio" }, styles: { color: "#0f172a", backgroundColor: "#ffffff" } },
    { type: "Text", props: { text: "List Price: $14.99 USD · Royalty: 70.00%" }, styles: { color: "#0f172a", backgroundColor: "#ffffff" } },
    { type: "Button", props: { text: "Import Draft Outline" }, styles: { color: "#ffffff", backgroundColor: "#0f766e" } },
    { type: "Link", props: { href: "/books/night-ledger", text: "Read Sample" }, styles: { color: "#1d4ed8", backgroundColor: "#ffffff" } },
  ],
});
assert.equal(treeAudit.ok, true, `Grex auditAccessibility failed: ${JSON.stringify(treeAudit.issues)}`);

// 6. Light & Dark WCAG AA contrast pairs from reader.css & admin.css (>= 4.5:1)
const contrastPairs = [
  ["light-reader-body", "#0f172a", "#ffffff", 4.5],
  ["light-reader-surface", "#0f172a", "#f8fafc", 4.5],
  ["light-reader-muted", "#475569", "#f8fafc", 4.5],
  ["light-reader-link", "#1d4ed8", "#ffffff", 4.5],
  ["light-reader-accent", "#ffffff", "#0f766e", 4.5],
  ["light-reader-badge", "#ffffff", "#0f172a", 4.5],
  ["dark-reader-body", "#f8fafc", "#0b1120", 4.5],
  ["dark-reader-surface", "#f8fafc", "#111827", 4.5],
  ["dark-reader-muted", "#cbd5e1", "#111827", 4.5],
  ["dark-reader-link", "#93c5fd", "#0b1120", 4.5],
  ["dark-reader-accent", "#ffffff", "#0f766e", 4.5],
  ["dark-reader-badge", "#0f172a", "#e2e8f0", 4.5],
];

for (const [label, fg, bg, minRatio] of contrastPairs) {
  const ratio = computeContrastRatio(fg, bg);
  assert.ok(ratio >= minRatio, `WCAG AA contrast failed for ${label}: ${ratio.toFixed(2)} < ${minRatio}`);
}

// 7. Static .grab.html template zero-<div> & zero inline handler audit
const htmlTargets = [
  "src/views/author/reader.grab.html",
  "themes/default-starter/templates/books.grab.html",
  "themes/default-starter/templates/book.grab.html",
  "themes/default-starter/templates/series.grab.html",
];
for (const rel of htmlTargets) {
  const html = fs.readFileSync(rel, "utf8").toLowerCase();
  assert.equal(html.includes("<div"), false, `Found <div> in ${rel}`);
  assert.equal(/\bon[a-z]+\s*=/.test(html), false, `Found inline handler in ${rel}`);
}

console.log(
  JSON.stringify({
    ok: true,
    divCount,
    innerHTMLWriteCount,
    contrastPairsVerified: contrastPairs.length,
    auditAccessibilityPassed: treeAudit.ok,
    templatesChecked: htmlTargets.length,
    keyboardFocusRestored: true,
  })
);
