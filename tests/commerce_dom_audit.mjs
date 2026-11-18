/**
 * GrabLab CMS v1.1.0 DOM, Grex JS v1.0.0 & Light/Dark WCAG AA Contrast Audit
 * Usage: node tests/commerce_dom_audit.mjs
 */

import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";

let divCount = 0;
let innerHTMLWriteCount = 0;
const createdElements = [];

function makeFakeElement(tag) {
  const tagLower = String(tag).toLowerCase();
  if (tagLower === "div") divCount += 1;
  const attrs = new Map();
  const children = [];
  let textVal = "";
  const el = {
    tagName: tagLower.toUpperCase(),
    nodeName: tagLower.toUpperCase(),
    nodeType: 1,
    hidden: false,
    disabled: false,
    checked: false,
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
    addEventListener() {},
    removeEventListener() {},
    querySelectorAll(sel) {
      const out = [];
      const walk = (n) => {
        if (!n || typeof n !== "object") return;
        if (sel === "div" && n.tagName === "DIV") out.push(n);
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
  head: makeFakeElement("head"),
  body: makeFakeElement("body"),
  createElement: (tag) => makeFakeElement(tag),
  createTextNode: (t) => ({ nodeType: 3, textContent: String(t), children: [] }),
  createComment: (t) => ({ nodeType: 8, textContent: String(t), children: [] }),
  getElementById: () => null,
  querySelectorAll: (sel) => (sel === "div" ? createdElements.filter((e) => e.tagName === "DIV") : []),
};

const { auditAccessibility, isExactGrabWireString, computeContrastRatio } = await import("../public/grex/grex.js");
const shopMod = await import("../public/shop/shop.js");
const commMod = await import("../public/admin/commerce.js");

function countDivsInTree(root) {
  let count = root.tagName === "DIV" ? 1 : 0;
  for (const ch of root.children || []) {
    count += countDivsInTree(ch);
  }
  return count;
}

// 1. Audit JS sources for static hygiene
const jsFiles = [
  "public/shop/shop.js",
  "public/admin/commerce.js",
  "public/admin/admin.js",
];
for (const rel of jsFiles) {
  const src = fs.readFileSync(rel, "utf8");
  assert.equal(/\.innerHTML\s*=/.test(src), false, `${rel} contains forbidden .innerHTML assignment`);
  assert.equal(/\beval\s*\(|new\s+Function\s*\(/.test(src), false, `${rel} contains eval/new Function`);
  assert.equal(/createElement\(\s*["']div["']\s*\)/.test(src), false, `${rel} creates forbidden <div>`);
  assert.equal(/type:\s*["']number["']/.test(src), false, `${rel} uses forbidden float-prone type="number"`);
}

// 2. Audit rendered Grex commerce trees
const prodView = shopMod.buildProductActionView({ id: 1, title: "Book", price: "19.99" }, async () => ({ total: "19.99", currency: "USD" }));
const cartView = shopMod.buildCartCheckoutView(
  {
    cart_id: "crt_1",
    currency: "USD",
    coupon_code: "SAVE15",
    has_physical: true,
    items: [{ product_id: 1, sku: "BK-1", title: "Book", unit_price: "19.99", qty: 3, line_total: "59.97" }],
    subtotal: "59.97",
    discount_total: "9.00",
    tax_total: "4.21",
    shipping_total: "5.00",
    total: "60.18",
  },
  { onRemove: async () => {}, onCoupon: async () => {}, onCheckout: async () => ({ order_number: "ORD-1" }) }
);
const subnavView = commMod.buildStoreSubnav("store_orders", true);
const dashView = commMod.createStoreDashboardSpec({
  enabled: true,
  counts: { products: 2, orders: 1, needs_review: 1, coupons: 1, customers: 1 },
  needs_review_orders: [{ number: "ORD-1", status: "pending_payment", total: "55.18", review_note: "Mismatch" }],
});

for (const v of [prodView, cartView, subnavView, dashView]) {
  assert.equal(countDivsInTree(v), 0, "Expected 0 <div> tags in rendered tree");
}
assert.equal(divCount, 0, "Expected global divCount === 0");
assert.equal(innerHTMLWriteCount, 0, "Expected innerHTMLWriteCount === 0");

// Verify marketing opt-in checkbox exists and defaults UNCHECKED
function findInputs(el, out = []) {
  if (el.tagName === "INPUT") out.push(el);
  for (const c of el.children || []) findInputs(c, out);
  return out;
}
const chkInputs = findInputs(cartView);
const mktCheckbox = chkInputs.find((i) => i.getAttribute("id") === "chk-marketing");
assert.ok(mktCheckbox, "Expected marketing opt-in checkbox in checkout view");
assert.equal(mktCheckbox.checked, false, "Marketing consent checkbox MUST default unchecked");

// 3. Audit Grex wire format checker
assert.equal(isExactGrabWireString("19.99"), true);
assert.equal(isExactGrabWireString("99999999.99"), true);
assert.equal(isExactGrabWireString("1e2"), false);
assert.equal(isExactGrabWireString(19.99), false);

// 4. Audit accessibility tree helper from Grex JS v1.0.0
const treeAudit = auditAccessibility({
  type: "Section",
  children: [
    { type: "Heading", props: { level: 1, text: "GrabLab Store" }, styles: { color: "#0f172a", backgroundColor: "#ffffff" } },
    { type: "Text", props: { text: "Exact decimal pricing ($19.99 USD)." }, styles: { color: "#0f172a", backgroundColor: "#ffffff" } },
    { type: "Button", props: { text: "Add to Cart" }, styles: { color: "#ffffff", backgroundColor: "#1d4ed8" } },
    { type: "Link", props: { href: "/shop/cart", text: "Checkout" }, styles: { color: "#1d4ed8", backgroundColor: "#ffffff" } },
  ],
});
assert.equal(treeAudit.ok, true, `Grex auditAccessibility failed: ${JSON.stringify(treeAudit.issues)}`);

// 5. Audit Light & Dark WCAG AA contrast pairs from shop.css and admin.css (>= 4.5:1 normal text, >= 3.0:1 large)
const contrastPairs = [
  // Light Shop & Admin
  ["light-body", "#0f172a", "#ffffff", 4.5],
  ["light-surface", "#0f172a", "#f8fafc", 4.5],
  ["light-muted", "#475569", "#f8fafc", 4.5],
  ["light-link", "#1d4ed8", "#ffffff", 4.5],
  ["light-btn", "#ffffff", "#1d4ed8", 4.5],
  ["light-badge", "#ffffff", "#0f172a", 4.5],
  ["light-danger", "#991b1b", "#fef2f2", 4.5],
  ["light-ok", "#065f46", "#ecfdf5", 4.5],
  ["light-admin-danger", "#b91c1c", "#fef2f2", 4.5],
  ["light-admin-ok", "#15803d", "#f0fdf4", 4.5],
  ["light-admin-info", "#0369a1", "#f0f9ff", 4.5],
  // Dark Shop & Admin
  ["dark-body", "#f8fafc", "#0b1120", 4.5],
  ["dark-surface", "#f8fafc", "#111827", 4.5],
  ["dark-muted", "#cbd5e1", "#111827", 4.5],
  ["dark-link", "#93c5fd", "#0b1120", 4.5],
  ["dark-btn", "#ffffff", "#2563eb", 4.5],
  ["dark-badge", "#0f172a", "#e2e8f0", 4.5],
  ["dark-danger", "#fecaca", "#450a0a", 4.5],
  ["dark-ok", "#a7f3d0", "#064e3b", 4.5],
  ["dark-admin-info", "#93c5fd", "#1e3a8a", 4.5],
  ["dark-admin-btn-danger", "#0b1120", "#fecaca", 4.5],
];

for (const [label, fg, bg, minRatio] of contrastPairs) {
  const ratio = computeContrastRatio(fg, bg);
  assert.ok(ratio >= minRatio, `WCAG AA contrast failed for ${label}: ${ratio.toFixed(2)} < ${minRatio}`);
}

// 6. Verify static .grab.html templates contain zero <div> and zero inline handlers
const htmlTargets = [
  "src/views/shop/order.grab.html",
  "themes/default-starter/templates/shop.grab.html",
  "themes/default-starter/templates/product.grab.html",
  "themes/default-starter/templates/cart.grab.html",
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
  })
);
